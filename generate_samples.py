#!/usr/bin/env python3
"""Generate deduplicated tree-aware questionnaire answer files offline."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from fill_once import NA, canonical_hash, load_json, resolve_answers, validate_map, write_json


PROBABILITY_OF_YES = {
    "no_biased": 0.15,
    "yes_biased": 0.85,
    "balanced_random": 0.50,
}


def anchor_value(question: dict[str, Any], anchor: str) -> str:
    options = [str(option).lower() for option in question["options"]]
    preferred = "no" if anchor == "all_no" else "yes"
    if preferred in options:
        return preferred
    return options[0] if anchor == "all_no" else options[-1]


def random_value(question: dict[str, Any], strategy: str, rng: random.Random) -> str:
    options = [str(option).lower() for option in question["options"]]
    if set(options) == {"yes", "no"}:
        return "yes" if rng.random() < PROBABILITY_OF_YES[strategy] else "no"
    return rng.choice(options)


def generate_anchor(questionnaire_map: dict[str, Any], anchor: str) -> dict[str, str]:
    return resolve_answers(
        questionnaire_map,
        {},
        answer_factory=lambda question: anchor_value(question, anchor),
    )


def generate_random(
    questionnaire_map: dict[str, Any],
    strategy: str,
    rng: random.Random,
) -> dict[str, str]:
    return resolve_answers(
        questionnaire_map,
        {},
        answer_factory=lambda question: random_value(question, strategy, rng),
    )


def quota(count: int) -> list[str]:
    no_count = round(count * 0.30)
    yes_count = round(count * 0.20)
    balanced_count = count - no_count - yes_count
    return (
        ["no_biased"] * no_count
        + ["yes_biased"] * yes_count
        + ["balanced_random"] * balanced_count
    )


def quota_counts(count: int) -> Counter[str]:
    return Counter(quota(count))


def sample_payload(sample_id: str, strategy: str, seed: int, answers: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "sample_id": sample_id,
        "strategy": strategy,
        "seed": seed,
        "answers": answers,
        "canonical_hash": canonical_hash(answers),
    }


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questionnaire-map", type=Path, default=script_dir / "questionnaire_map.json")
    parser.add_argument("--out-dir", type=Path, default=script_dir / "generated_answers")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260602)
    parser.add_argument(
        "--allow-unverified-map",
        action="store_true",
        help="generate calibration samples from the starter map before manual verification",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive")
    questionnaire_map = load_json(args.questionnaire_map)
    errors = validate_map(
        questionnaire_map,
        require_verified=not args.allow_unverified_map,
    )
    if errors:
        raise SystemExit("questionnaire map is not ready:\n- " + "\n- ".join(errors))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    targets = quota_counts(args.count)
    generated_by_strategy: Counter[str] = Counter()
    seen_hashes: set[str] = set()
    emitted: list[dict[str, Any]] = []
    max_attempts = max(args.count * 100, 1000)
    attempts = 0
    while len(emitted) < args.count and attempts < max_attempts:
        strategies_with_remaining_quota = [
            strategy
            for strategy, target in targets.items()
            if generated_by_strategy[strategy] < target
        ]
        if not strategies_with_remaining_quota:
            break
        strategy = rng.choice(strategies_with_remaining_quota)
        attempts += 1
        answers = generate_random(questionnaire_map, strategy, rng)
        digest = canonical_hash(answers)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        sample_id = f"{strategy}-{len(emitted) + 1:04d}-{digest[:10]}"
        payload = sample_payload(sample_id, strategy, args.seed, answers)
        write_json(args.out_dir / f"{sample_id}.json", payload)
        emitted.append(payload)
        generated_by_strategy[strategy] += 1

    anchors: list[dict[str, Any]] = []
    for anchor in ("all_no", "all_yes"):
        answers = generate_anchor(questionnaire_map, anchor)
        payload = sample_payload(anchor, anchor, args.seed, answers)
        write_json(args.out_dir / f"{anchor}.json", payload)
        anchors.append(payload)

    manifest = {
        "schema_version": "1.0",
        "seed": args.seed,
        "requested_unique_samples": args.count,
        "generated_unique_samples": len(emitted),
        "attempts": attempts,
        "strategy_targets": dict(targets),
        "strategy_counts": dict(generated_by_strategy),
        "anchors": [sample["sample_id"] for sample in anchors],
        "warning": (
            "" if len(emitted) == args.count else
            "The verified questionnaire map does not expose enough unique reachable paths "
            "for the requested count. Expand the map or lower --count."
        ),
    }
    write_json(args.out_dir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if len(emitted) == args.count else 2


if __name__ == "__main__":
    raise SystemExit(main())
