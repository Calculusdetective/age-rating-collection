#!/usr/bin/env python3
"""Safely inspect or fill one Google Play content-rating questionnaire.

The browser workflow intentionally stops at the Summary page. It never clicks
Submit, Publish, or review-related buttons. Use this only with an authorized,
isolated draft app.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


NA = "N/A"
SCHEMA_VERSION = "1.0"
FORBIDDEN_BUTTON_WORDS = {
    "submit",
    "publish",
    "send for review",
    "roll out",
    "发布",
    "提交",
    "送审",
}


class CollectionError(RuntimeError):
    """Base error for a stopped collection run."""


class BlockerDetected(CollectionError):
    """Raised when captcha, rate limiting, or authentication blocks the run."""

    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Paths:
    output: Path
    screenshot: Path


@dataclass(frozen=True)
class BrowserSession:
    manager: Any
    context: Any
    owns_context: bool = True
    attached: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def question_by_id(questionnaire_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {question["question_id"]: question for question in questionnaire_map["questions"]}


def normalized_answer(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"answer values must be strings, got {value!r}")
    value = value.strip()
    if value.upper() == NA:
        return NA
    return value.lower()


def conditions_for(question: dict[str, Any]) -> list[dict[str, Any]]:
    condition = question.get("visible_when")
    if condition is None:
        return []
    if isinstance(condition, dict):
        return [condition]
    if isinstance(condition, list) and all(isinstance(item, dict) for item in condition):
        return condition
    raise ValueError(f"{question['question_id']}: visible_when must be null, object, or list")


def is_visible(question: dict[str, Any], resolved_answers: dict[str, str]) -> bool:
    for condition in conditions_for(question):
        parent_id = condition["parent_id"]
        actual = resolved_answers.get(parent_id)
        if "equals" in condition and actual != normalized_answer(condition["equals"]):
            return False
        if "in" in condition:
            allowed = {normalized_answer(value) for value in condition["in"]}
            if actual not in allowed:
                return False
    return True


def validate_map(
    questionnaire_map: dict[str, Any],
    *,
    require_verified: bool = False,
) -> list[str]:
    errors: list[str] = []
    questions = questionnaire_map.get("questions")
    if not isinstance(questions, list) or not questions:
        return ["questionnaire_map.json must contain a non-empty questions list"]

    seen: set[str] = set()
    for index, question in enumerate(questions):
        question_id = question.get("question_id")
        if not isinstance(question_id, str) or not question_id:
            errors.append(f"question #{index + 1}: missing question_id")
            continue
        if question_id in seen:
            errors.append(f"{question_id}: duplicate question_id")
        seen.add(question_id)
        if not question.get("prompt"):
            errors.append(f"{question_id}: missing prompt")
        options = question.get("options")
        if not isinstance(options, list) or not options:
            errors.append(f"{question_id}: missing options")
        if require_verified and not question.get("verified_in_console", False):
            errors.append(f"{question_id}: not verified in the current Play Console UI")
        if require_verified and not question.get("children_explored", False):
            errors.append(f"{question_id}: Yes/child branch exploration is not marked complete")
        for condition in conditions_for(question):
            parent_id = condition.get("parent_id")
            if not parent_id:
                errors.append(f"{question_id}: visible_when is missing parent_id")
            elif parent_id not in seen:
                errors.append(
                    f"{question_id}: parent {parent_id!r} must appear earlier in the questions list"
                )

    ids = {question.get("question_id") for question in questions}
    for question in questions:
        for child_id in question.get("children", []):
            if child_id not in ids:
                errors.append(f"{question['question_id']}: unknown child {child_id!r}")
    return errors


def resolve_answers(
    questionnaire_map: dict[str, Any],
    requested_answers: dict[str, Any],
    *,
    answer_factory: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, str]:
    """Resolve visible answers and mark hidden tree nodes as N/A."""

    resolved: dict[str, str] = {}
    known_ids = {question["question_id"] for question in questionnaire_map["questions"]}
    unknown_ids = sorted(set(requested_answers) - known_ids)
    if unknown_ids:
        raise ValueError(f"answers contain unknown question ids: {', '.join(unknown_ids)}")

    for question in questionnaire_map["questions"]:
        question_id = question["question_id"]
        if not is_visible(question, resolved):
            resolved[question_id] = NA
            continue

        value = requested_answers.get(question_id)
        if value is None and answer_factory is not None:
            value = answer_factory(question)
        if value is None:
            raise ValueError(f"missing answer for visible question: {question_id}")
        value = normalized_answer(value)
        if value == NA:
            raise ValueError(f"{question_id}: visible questions cannot be answered with {NA}")

        allowed = {normalized_answer(option) for option in question["options"]}
        if value not in allowed:
            raise ValueError(
                f"{question_id}: answer {value!r} is not one of {sorted(allowed)!r}"
            )
        resolved[question_id] = value
    return resolved


def canonical_visible_answers(resolved_answers: dict[str, str]) -> str:
    visible_answers = {
        question_id: answer
        for question_id, answer in sorted(resolved_answers.items())
        if answer != NA
    }
    return json.dumps(visible_answers, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def canonical_hash(resolved_answers: dict[str, str]) -> str:
    return hashlib.sha256(canonical_visible_answers(resolved_answers).encode("utf-8")).hexdigest()


def answer_payload(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise ValueError(f"{path}: expected an answers object")
    return payload


def result_paths(output: Path) -> Paths:
    return Paths(output=output, screenshot=output.with_suffix(".png"))


def base_result(mode: str, answers: dict[str, str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "collected_at": utc_now(),
    }
    if answers is not None:
        payload["resolved_answers"] = answers
        payload["canonical_hash"] = canonical_hash(answers)
    return payload


def run_audit(args: argparse.Namespace) -> int:
    questionnaire_map = load_json(args.questionnaire_map)
    errors = validate_map(questionnaire_map, require_verified=False)
    if errors:
        raise ValueError("invalid questionnaire map:\n- " + "\n- ".join(errors))
    payload = answer_payload(args.answers)
    answers = resolve_answers(questionnaire_map, payload["answers"])
    result = base_result("audit", answers)
    result.update(
        {
            "status": "ok",
            "sample_id": payload.get("sample_id"),
            "strategy": payload.get("strategy"),
            "note": "Offline validation only; no browser was opened.",
        }
    )
    write_json(args.output, result)
    print(f"audit ok: {args.output}")
    print(f"canonical_hash: {result['canonical_hash']}")
    return 0


def visible_locator(locator: Any) -> Any | None:
    for index in range(locator.count()):
        candidate = locator.nth(index)
        if candidate.is_visible():
            return candidate
    return None


def page_has_visible_selector(page: Any, selectors: Iterable[str]) -> str | None:
    for selector in selectors:
        locator = page.locator(selector)
        if visible_locator(locator) is not None:
            return selector
    return None


def page_contains_marker(page_text: str, markers: Iterable[str]) -> str | None:
    folded = page_text.casefold()
    for marker in markers:
        if marker.casefold() in folded:
            return marker
    return None


def page_text(page: Any) -> str:
    return page.locator("body").inner_text(timeout=10_000)


def save_screenshot(page: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)


def is_page_usable(page: Any) -> bool:
    try:
        return not page.is_closed()
    except Exception:
        return False


def choose_capture_page(context: Any, current_page: Any | None = None) -> Any:
    candidates = [page for page in context.pages if is_page_usable(page)]
    content_rating_pages = [
        page for page in candidates
        if "play.google.com/console" in getattr(page, "url", "")
        and "content-rating-iarc" in getattr(page, "url", "")
    ]
    if content_rating_pages:
        return content_rating_pages[-1]
    play_console_pages = [
        page for page in candidates
        if "play.google.com/console" in getattr(page, "url", "")
    ]
    if play_console_pages:
        return play_console_pages[-1]
    if current_page is not None and is_page_usable(current_page):
        return current_page
    if candidates:
        return candidates[-1]
    return context.new_page()


def check_blockers(page: Any, config: dict[str, Any]) -> None:
    text = page_text(page)
    captcha_selector = page_has_visible_selector(page, config["captcha_selectors"])
    captcha_marker = page_contains_marker(text, config["captcha_text_markers"])
    if captcha_selector or captcha_marker:
        raise BlockerDetected(
            "captcha_detected",
            f"captcha detected ({captcha_selector or captcha_marker}); stop for manual review",
        )

    limit_marker = page_contains_marker(text, config["rate_limit_text_markers"])
    if limit_marker:
        raise BlockerDetected(
            "rate_limited",
            f"rate-limit marker detected ({limit_marker}); stop and wait before any retry",
        )


def wait_for_manual_login(page: Any, config: dict[str, Any], timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        url = page.url.casefold()
        text = page_text(page)
        marker = page_contains_marker(text, config["login_text_markers"])
        if "accounts.google." not in url and marker is None:
            return
        if time.monotonic() >= deadline:
            raise BlockerDetected("login_timeout", "manual login did not complete before timeout")
        print("waiting for manual login in the visible browser window...")
        page.wait_for_timeout(2_000)


def prompt_locator(page: Any, prompt: str) -> Any | None:
    return visible_locator(page.get_by_text(prompt, exact=False))


def question_container(prompt_node: Any) -> Any:
    ancestor_queries = [
        "xpath=ancestor::fieldset[1]",
        "xpath=ancestor::*[@role='radiogroup'][1]",
        "xpath=ancestor::*[.//input[@type='radio'] or .//*[@role='radio']][1]",
    ]
    for query in ancestor_queries:
        locator = prompt_node.locator(query)
        candidate = visible_locator(locator)
        if candidate is not None:
            return candidate
    raise CollectionError("could not find a radio-group container near the question prompt")


def click_answer(page: Any, question: dict[str, Any], answer: str) -> None:
    custom_selector = question.get("selectors", {}).get(answer)
    if custom_selector:
        target = visible_locator(page.locator(custom_selector))
        if target is None:
            raise CollectionError(
                f"{question['question_id']}: selector for answer {answer!r} was not visible"
            )
        target.click()
        return

    prompt_node = prompt_locator(page, question["prompt"])
    if prompt_node is None:
        raise CollectionError(f"{question['question_id']}: prompt is not visible")
    container = question_container(prompt_node)
    option_pattern = re.compile(rf"^\s*{re.escape(answer)}\s*$", re.IGNORECASE)
    candidates = [
        container.get_by_role("radio", name=option_pattern),
        container.locator("label").filter(has_text=option_pattern),
        container.get_by_text(option_pattern, exact=True),
    ]
    for locator in candidates:
        target = visible_locator(locator)
        if target is not None:
            target.click()
            return
    raise CollectionError(f"{question['question_id']}: could not click answer {answer!r}")


def apply_visible_answers_by_order(
    page: Any,
    questions: list[dict[str, Any]],
    resolved_answers: dict[str, str],
    answered: set[str],
) -> list[dict[str, Any]]:
    """Click visible controls by DOM order, using the map order for alignment."""

    specs: list[dict[str, Any]] = []
    for question in questions:
        question_id = question["question_id"]
        answer = resolved_answers[question_id]
        if answer == NA or prompt_locator(page, question["prompt"]) is None:
            continue
        specs.append(
            {
                "question_id": question_id,
                "type": question.get("type", "boolean"),
                "answer": answer,
                "options": question.get("options", []),
                "skip_click": question_id in answered,
            }
        )

    if not specs:
        return []

    applied = page.evaluate(
        """
        (specs) => {
          const isVisible = (el) => !!(
            el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length)
          );
          const labelText = (control) => {
            const text = (el) => (el?.innerText || el?.textContent || "")
              .replace(/\\s+/g, " ").trim();
            const label = control.labels?.[0]
              || control.closest("label")
              || (control.id ? document.querySelector(`label[for="${control.id}"]`) : null);
            return text(label) || control.getAttribute("aria-label") || "";
          };
          const checked = (control) =>
            !!control.checked || control.getAttribute("aria-checked") === "true";
          const clickControl = (control) => {
            control.scrollIntoView({block: "center", inline: "nearest"});
            control.click();
          };
          const normalize = (value) => String(value || "").trim().toLowerCase();
          const controls = [...document.querySelectorAll(
            'input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]'
          )].filter(isVisible);
          const groups = [];
          const seenRadioGroups = new Set();
          for (const control of controls) {
            const type = control.getAttribute("type") || control.getAttribute("role") || "";
            if (type.toLowerCase().includes("checkbox")) {
              groups.push({ kind: "checkbox", controls: [control] });
              continue;
            }
            const groupKey = control.getAttribute("name")
              || control.getAttribute("aria-labelledby")
              || control.closest('[role="radiogroup"]')?.getAttribute("aria-label")
              || control.closest('[role="radiogroup"]')?.getAttribute("id")
              || `radio-${groups.length}`;
            if (seenRadioGroups.has(groupKey)) continue;
            seenRadioGroups.add(groupKey);
            const sameGroup = controls.filter((candidate) => {
              const candidateType = candidate.getAttribute("type") || candidate.getAttribute("role") || "";
              if (candidateType.toLowerCase().includes("checkbox")) return false;
              const candidateKey = candidate.getAttribute("name")
                || candidate.getAttribute("aria-labelledby")
                || candidate.closest('[role="radiogroup"]')?.getAttribute("aria-label")
                || candidate.closest('[role="radiogroup"]')?.getAttribute("id")
                || groupKey;
              return candidateKey === groupKey;
            });
            groups.push({ kind: "radio", controls: sameGroup });
          }

          const result = [];
          let groupIndex = 0;
          for (const spec of specs) {
            const group = groups[groupIndex++];
            if (!group) {
              result.push({ question_id: spec.question_id, status: "missing_control_group" });
              continue;
            }
            if (group.kind === "checkbox" || spec.type === "checkbox_boolean") {
              const desired = ["yes", "true", "checked", "1"].includes(normalize(spec.answer));
              if (checked(group.controls[0]) === desired) {
                result.push({
                  question_id: spec.question_id,
                  status: "already_desired",
                  control_kind: "checkbox",
                  answer: spec.answer,
                });
                continue;
              }
              clickControl(group.controls[0]);
              result.push({
                question_id: spec.question_id,
                status: "clicked",
                control_kind: "checkbox",
                answer: spec.answer,
              });
              break;
            }

            const targetLabel = normalize(spec.answer);
            const target = group.controls.find((control) => normalize(labelText(control)) === targetLabel)
              || group.controls[spec.options.map(normalize).indexOf(targetLabel)];
            if (!target) {
              result.push({
                question_id: spec.question_id,
                status: "missing_option",
                labels: group.controls.map(labelText),
                answer: spec.answer,
              });
              continue;
            }
            if (checked(target)) {
              result.push({
                question_id: spec.question_id,
                status: "already_desired",
                control_kind: "radio",
                answer: spec.answer,
              });
              continue;
            }
            clickControl(target);
            result.push({
              question_id: spec.question_id,
              status: "clicked",
              control_kind: "radio",
              answer: spec.answer,
            });
            break;
          }
          return result;
        }
        """,
        specs,
    )
    if not isinstance(applied, list):
        raise CollectionError("unexpected browser response while applying answers")
    missing = [item for item in applied if str(item.get("status", "")).startswith("missing")]
    if missing:
        raise CollectionError(f"could not apply all visible answers: {missing}")
    return applied


def looks_like_summary(text: str, config: dict[str, Any]) -> bool:
    matches = sum(
        1 for marker in config["summary_text_markers"] if marker.casefold() in text.casefold()
    )
    return matches >= config.get("summary_min_markers", 2)


def find_navigation_button(page: Any, config: dict[str, Any]) -> Any | None:
    for name in config["allowed_navigation_buttons"]:
        folded = name.casefold()
        if any(word in folded for word in FORBIDDEN_BUTTON_WORDS):
            raise ValueError(f"unsafe navigation button configured: {name!r}")
        pattern = re.compile(rf"^\s*{re.escape(name)}\s*$", re.IGNORECASE)
        target = visible_locator(page.get_by_role("button", name=pattern))
        if target is not None and target.is_enabled():
            return target
    return None


def find_exact_button(page: Any, name: str, *, enabled: bool | None = None) -> Any | None:
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*$", re.IGNORECASE)
    target = visible_locator(page.get_by_role("button", name=pattern))
    if target is None:
        return None
    if enabled is not None and target.is_enabled() != enabled:
        return None
    return target


def scroll_for_more_visible_content(page: Any) -> bool:
    """Move down inside the main scroll container when lazy-rendered fields are below the fold."""

    changed = page.evaluate(
        """
        () => {
          const candidates = [
            document.scrollingElement,
            document.documentElement,
            document.body,
            ...document.querySelectorAll('main, [role="main"], div')
          ].filter((el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            const scrollable = /(auto|scroll|overlay)/.test(style.overflowY);
            return el.scrollHeight > el.clientHeight + 20 && (scrollable || el === document.scrollingElement);
          });
          candidates.sort((a, b) =>
            (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight)
          );
          for (const el of candidates) {
            const before = el.scrollTop;
            const amount = Math.max(500, Math.floor((el.clientHeight || window.innerHeight) * 0.75));
            el.scrollTop = Math.min(el.scrollTop + amount, el.scrollHeight - el.clientHeight);
            if (el.scrollTop !== before) return true;
          }
          const beforeWindow = window.scrollY;
          window.scrollBy(0, Math.max(500, Math.floor(window.innerHeight * 0.75)));
          return window.scrollY !== beforeWindow;
        }
        """
    )
    return bool(changed)


def parse_summary(text: str, config: dict[str, Any]) -> dict[str, Any]:
    """Keep raw Summary text and extract conservative rating hints."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    ratings: list[dict[str, str]] = []
    authorities = config.get("rating_authorities", [])
    rating_pattern = re.compile(
        r"\b(?:rated\s+for\s+)?(?:everyone|teen|mature|adults?\s+only|"
        r"parental\s+guidance(?:\s+recommended)?|[a-z]{0,3}\s*\d{1,2}\+?|"
        r"\d{1,2}\+)\b",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        authority = next(
            (candidate for candidate in authorities if candidate.casefold() in line.casefold()),
            None,
        )
        if authority is None:
            continue
        nearby = " | ".join(lines[index : index + 5])
        match = rating_pattern.search(nearby)
        ratings.append(
            {
                "authority_hint": authority,
                "rating_hint": match.group(0) if match else "",
                "raw_context": nearby,
            }
        )
    return {
        "ratings": ratings,
        "content_descriptors": [],
        "interactive_elements": [],
        "raw_text": text,
        "parser_note": (
            "ratings are conservative hints; calibrate selectors after the first manual run "
            "and keep raw_text as the source of truth"
        ),
    }


def discover_controls(page: Any) -> dict[str, Any]:
    """Return visible form controls without interacting with the page."""

    return page.evaluate(
        """
        () => {
          const isVisible = (el) => !!(
            el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length)
          );
          const text = (el) => (el?.innerText || el?.textContent || "")
            .replace(/\\s+/g, " ").trim();
          const controls = [...document.querySelectorAll(
            'input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]'
          )].filter(isVisible);
          const groups = new Map();
          for (const control of controls) {
            const key = control.getAttribute("name")
              || control.getAttribute("aria-labelledby")
              || control.closest('[role="radiogroup"]')?.getAttribute("aria-label")
              || `ungrouped-${groups.size + 1}`;
            if (!groups.has(key)) groups.set(key, []);
            const label = control.labels?.[0]
              || control.closest("label")
              || document.querySelector(`label[for="${control.id}"]`);
            groups.get(key).push({
              type: control.getAttribute("type") || control.getAttribute("role"),
              value: control.getAttribute("value") || "",
              label: text(label) || control.getAttribute("aria-label") || "",
              checked: !!control.checked || control.getAttribute("aria-checked") === "true",
              id: control.id || "",
            });
          }
          return {
            url: location.href,
            title: document.title,
            visible_controls: [...groups.entries()].map(([group, options]) => ({ group, options })),
            visible_buttons: [...document.querySelectorAll('button, [role="button"]')]
              .filter(isVisible).map((button) => text(button)),
            page_text: text(document.body),
          };
        }
        """
    )


def browser_session(args: argparse.Namespace) -> BrowserSession:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CollectionError(
            "Playwright is missing. Install it with: python -m pip install playwright"
        ) from exc

    manager = sync_playwright().start()
    if args.connect_cdp:
        try:
            browser = manager.chromium.connect_over_cdp(args.connect_cdp)
            if not browser.contexts:
                raise CollectionError("connected Chrome did not expose any browser context")
            return BrowserSession(
                manager=manager,
                context=browser.contexts[0],
                owns_context=False,
                attached=True,
            )
        except Exception as exc:
            manager.stop()
            raise CollectionError(
                "Could not connect to Chrome remote debugging endpoint "
                f"{args.connect_cdp}. Make sure Chrome was started with "
                "--remote-debugging-port=9222 and that http://127.0.0.1:9222/json/version "
                "opens in a browser. If it does not, close all chrome.exe processes and "
                "start Chrome again with the documented command."
            ) from exc

    launch_options: dict[str, Any] = {
        "user_data_dir": str(args.profile_dir),
        "headless": args.headless,
    }
    if args.browser_channel:
        launch_options["channel"] = args.browser_channel
    if args.executable_path:
        launch_options["executable_path"] = str(args.executable_path)
    try:
        context = manager.chromium.launch_persistent_context(**launch_options)
    except Exception:
        manager.stop()
        raise
    return BrowserSession(manager=manager, context=context)


def close_browser_session(session: BrowserSession) -> None:
    try:
        if session.owns_context:
            session.context.close()
    finally:
        session.manager.stop()


def require_url(args: argparse.Namespace) -> str:
    url = args.url or os.environ.get("PLAY_CONSOLE_CONTENT_RATING_URL")
    if not url:
        raise ValueError(
            "browser modes require --url or PLAY_CONSOLE_CONTENT_RATING_URL; "
            "copy the isolated draft app questionnaire URL from Play Console"
        )
    return url


def looks_like_placeholder_url(url: str) -> bool:
    folded = url.casefold().strip()
    return (
        "粘贴" in folded
        or "当前问卷页面 url" in folded
        or "当前 summary 页面 url" in folded
        or folded in {"url", "todo", "placeholder"}
    )


def discover_start_url(args: argparse.Namespace) -> str:
    url = args.url or os.environ.get("PLAY_CONSOLE_CONTENT_RATING_URL")
    if not url or looks_like_placeholder_url(url):
        if url and looks_like_placeholder_url(url):
            print(
                "Placeholder URL detected. Opening Play Console instead; "
                "navigate manually to the target questionnaire/Summary page."
            )
        return "https://play.google.com/console"
    return url


def run_discovery(args: argparse.Namespace) -> int:
    url = discover_start_url(args)
    config = load_json(args.selectors)
    paths = result_paths(args.output)
    session = browser_session(args)
    context = session.context
    page = context.new_page() if session.attached else (context.pages[0] if context.pages else context.new_page())
    try:
        page.goto(url, wait_until="domcontentloaded")
        wait_for_manual_login(page, config, args.login_timeout)
        check_blockers(page, config)
        if args.pause_before_capture:
            print(
                "\nDiscovery pause: adjust the visible browser page to the target "
                "questionnaire or Summary state, then return here and press Enter."
            )
            input("Press Enter to capture the current page...")
            page = choose_capture_page(context, page)
            print(f"Capturing page: {page.url}")
            check_blockers(page, config)
        save_screenshot(page, paths.screenshot)
        result = base_result("discover")
        result.update(
            {
                "status": "ok",
                "note": "Read-only discovery; no questionnaire answer was clicked.",
                "discovery": discover_controls(page),
                "screenshot": str(paths.screenshot),
            }
        )
        write_json(paths.output, result)
        print(f"discovery saved: {paths.output}")
        return 0
    finally:
        close_browser_session(session)


def run_browser_collection(args: argparse.Namespace) -> int:
    if not args.confirm_authorized_test_app:
        raise ValueError(
            "--mode run requires --confirm-authorized-test-app. "
            "Use only an isolated draft app after course authorization."
        )
    config = load_json(args.selectors)
    questionnaire_map = load_json(args.questionnaire_map)
    errors = validate_map(
        questionnaire_map,
        require_verified=not args.allow_unverified_map,
    )
    if errors:
        raise ValueError("questionnaire map is not ready for browser execution:\n- " + "\n- ".join(errors))

    input_payload = answer_payload(args.answers)
    resolved = resolve_answers(questionnaire_map, input_payload["answers"])
    paths = result_paths(args.output)
    session = browser_session(args)
    context = session.context
    page = context.new_page() if session.attached else (context.pages[0] if context.pages else context.new_page())
    answered: set[str] = set()
    result = base_result("run", resolved)
    result.update(
        {
            "sample_id": input_payload.get("sample_id"),
            "strategy": input_payload.get("strategy"),
            "status": "started",
            "screenshot": str(paths.screenshot),
        }
    )
    try:
        if args.url:
            page.goto(args.url, wait_until="domcontentloaded")
        elif args.connect_cdp:
            page = choose_capture_page(context, page)
            print(f"Using current page: {page.url}")
        else:
            page.goto(require_url(args), wait_until="domcontentloaded")
        wait_for_manual_login(page, config, args.login_timeout)
        initial_text = page_text(page)
        if looks_like_summary(initial_text, config):
            back_button = find_exact_button(page, "Back", enabled=True)
            if back_button is None:
                raise CollectionError(
                    "current page is already on Summary before the requested answers were applied, "
                    "and no enabled Back button was found. Return to Questionnaire manually, then rerun."
                )
            print("Current page is Summary; clicking Back to return to Questionnaire.")
            back_button.click()
            page.wait_for_timeout(args.click_delay_ms)
            if looks_like_summary(page_text(page), config):
                raise CollectionError(
                    "still on Summary after clicking Back. Return to Questionnaire manually, then rerun."
                )
        for step in range(1, args.max_navigation_steps + 1):
            check_blockers(page, config)
            text = page_text(page)
            if looks_like_summary(text, config):
                save_screenshot(page, paths.screenshot)
                result.update(
                    {
                        "status": "summary_reached",
                        "navigation_steps": step - 1,
                        "summary": parse_summary(text, config),
                        "note": "Stopped at Summary by design. Final Submit was not clicked.",
                    }
                )
                write_json(paths.output, result)
                print(f"summary captured without final submission: {paths.output}")
                return 0

            applied = apply_visible_answers_by_order(
                page,
                questionnaire_map["questions"],
                resolved,
                answered,
            )
            newly_clicked = [
                item for item in applied
                if item.get("status") == "clicked" and item.get("question_id") not in answered
            ]
            for item in newly_clicked:
                answered.add(str(item["question_id"]))
            if newly_clicked:
                page.wait_for_timeout(args.click_delay_ms)
                continue

            navigation = find_navigation_button(page, config)
            if navigation is None:
                save_button = find_exact_button(page, "Save", enabled=True)
                disabled_next = find_exact_button(page, "Next", enabled=False)
                if save_button is not None and disabled_next is not None:
                    if args.allow_save_to_summary:
                        save_button.click()
                        page.wait_for_timeout(args.click_delay_ms)
                        continue
                    raise CollectionError(
                        "Google Play disabled Next and enabled Save after questionnaire edits. "
                        "Default automation stops here because it does not save draft changes. "
                        "If this isolated draft app is authorized for saving questionnaire probes, "
                        "rerun with --allow-save-to-summary."
                    )
                if scroll_for_more_visible_content(page):
                    page.wait_for_timeout(args.click_delay_ms)
                    continue
                raise CollectionError(
                    "page structure changed or an unmapped visible question blocked progress; "
                    "run --mode discover and update questionnaire_map.json/selectors.json"
                )
            navigation.click()
            page.wait_for_timeout(args.click_delay_ms)

        raise CollectionError(
            f"stopped after {args.max_navigation_steps} navigation steps before reaching Summary"
        )
    except BlockerDetected as exc:
        save_screenshot(page, paths.screenshot)
        result.update({"status": exc.status, "error": str(exc)})
        write_json(paths.output, result)
        print(f"stopped safely: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        save_screenshot(page, paths.screenshot)
        result.update({"status": "structure_changed", "error": str(exc)})
        write_json(paths.output, result)
        raise
    finally:
        close_browser_session(session)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("audit", "discover", "run"), default="audit")
    parser.add_argument("--answers", type=Path, help="JSON answer file; required for audit/run")
    parser.add_argument("--output", type=Path, required=True, help="result JSON path")
    parser.add_argument(
        "--questionnaire-map",
        type=Path,
        default=script_dir / "questionnaire_map.json",
    )
    parser.add_argument("--selectors", type=Path, default=script_dir / "selectors.json")
    parser.add_argument("--profile-dir", type=Path, default=script_dir / ".local/playwright-profile")
    parser.add_argument("--url", help="isolated draft-app questionnaire URL")
    parser.add_argument("--browser-channel", help="optional Playwright channel, for example chrome")
    parser.add_argument("--executable-path", type=Path, help="optional browser executable")
    parser.add_argument(
        "--connect-cdp",
        help="attach to an already-started Chrome remote debugging endpoint, for example http://127.0.0.1:9222",
    )
    parser.add_argument("--headless", action="store_true", help="not recommended for manual login")
    parser.add_argument("--login-timeout", type=int, default=300)
    parser.add_argument("--max-navigation-steps", type=int, default=50)
    parser.add_argument("--click-delay-ms", type=int, default=750)
    parser.add_argument(
        "--pause-before-capture",
        action="store_true",
        help="discover mode only: wait for Enter before reading controls and taking screenshot",
    )
    parser.add_argument("--confirm-authorized-test-app", action="store_true")
    parser.add_argument(
        "--allow-unverified-map",
        action="store_true",
        help="calibration only: allow browser run before every map node is manually verified",
    )
    parser.add_argument(
        "--allow-save-to-summary",
        action="store_true",
        help=(
            "calibration only: allow clicking Play Console's Save button when Google "
            "disables Next after questionnaire edits; this still never clicks Submit, "
            "Publish, or send-for-review controls"
        ),
    )
    args = parser.parse_args(argv)
    if args.mode in {"audit", "run"} and args.answers is None:
        parser.error(f"--answers is required for --mode {args.mode}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.mode == "audit":
            return run_audit(args)
        if args.mode == "discover":
            return run_discovery(args)
        return run_browser_collection(args)
    except (CollectionError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
