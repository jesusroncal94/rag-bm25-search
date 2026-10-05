import argparse
import json
import sys
import time

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from rag.api import app
from rag.config import RETRIEVAL_FLOOR

DATASET = Path(__file__).resolve().parent / "dataset.jsonl"
BASELINE = Path(__file__).resolve().parent / "baseline.json"

client = TestClient(app)


def load(split: str) -> list[dict]:
    lines = DATASET.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line]

    return [row for row in rows if row["split"] == split]


def ask(question: str) -> dict:
    return client.post("/ask", json={"question": question}).json()


def answer(rows: list[dict], pace: float = 0.0) -> list[tuple[dict, dict]]:
    pairs = []

    for row in rows:
        if pace:
            time.sleep(pace)

        pairs.append((row, ask(row["question"])))

    return pairs


def measure(rows: list[dict], pace: float = 0.0) -> dict:
    return tally(answer(rows, pace))


def tally(pairs: list[tuple[dict, dict]]) -> dict:
    answered = declined = retrieved_gold = answerable = unanswerable = unavailable = 0
    failures: list[str] = []

    for row, body in pairs:
        if body["reason"] == "model_unavailable":
            unavailable += 1
            failures.append(f"provider unavailable: {row['question']}")

            continue

        if row["answerable"]:
            answerable += 1

            if row["gold"] in [source["id"] for source in body["sources"]]:
                retrieved_gold += 1

            if body["grounded"]:
                answered += 1
            else:
                failures.append(
                    f"declined an answerable question [{body['reason']}] "
                    f"(confidence {body['retrieval_confidence']}): {row['question']}"
                )
        else:
            unanswerable += 1

            if body["grounded"]:
                failures.append(f"answered an unanswerable question: {row['question']}")
            else:
                declined += 1

    return {
        "answered": answered,
        "answerable": answerable,
        "declined": declined,
        "unanswerable": unanswerable,
        "retrieved_gold": retrieved_gold,
        "unavailable": unavailable,
        "failures": failures,
    }


def report(split: str, result: dict) -> None:
    print(f"{split}")
    print(f"   gold chunk retrieved   {result['retrieved_gold']:2d} of {result['answerable']:2d}")
    print(f"   answered when it could {result['answered']:2d} of {result['answerable']:2d}")
    print(f"   declined when it must  {result['declined']:2d} of {result['unanswerable']:2d}")

    if result["unavailable"]:
        print(f"   provider unavailable   {result['unavailable']:2d}, excluded from the counts above")

    for failure in result["failures"]:
        print(f"      {failure}")

    print()


def sweep() -> None:
    print(f"{'floor':>6}   {'dev answered':>14}  {'dev declined':>14}"
          f"  {'holdout answered':>18}  {'holdout declined':>18}")

    for floor in [0.20, 0.25, 0.30, 0.35, 0.40]:
        with patch("rag.api.RETRIEVAL_FLOOR", floor):
            dev, holdout = measure(load("dev")), measure(load("holdout"))

        mark = " <- current" if floor == RETRIEVAL_FLOOR else ""

        print(f"{floor:>6.2f}   {dev['answered']:>7d} of {dev['answerable']:<4d}"
              f"  {dev['declined']:>7d} of {dev['unanswerable']:<4d}"
              f"  {holdout['answered']:>11d} of {holdout['answerable']:<4d}"
              f"  {holdout['declined']:>11d} of {holdout['unanswerable']:<4d}{mark}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", action="store_true", help="try other retrieval floors")
    parser.add_argument("--record", action="store_true", help="save these numbers as the baseline")
    parser.add_argument("--pace", type=float, default=0.0,
                        help="seconds between questions, to stay under a provider rate limit")
    args = parser.parse_args()

    if args.sweep:
        sweep()

        return 0

    print(f"retrieval floor {RETRIEVAL_FLOOR}\n")

    answers = {split: answer(load(split), args.pace) for split in ("dev", "holdout")}
    results = {split: tally(pairs) for split, pairs in answers.items()}

    for split, result in results.items():
        report(split, result)

    for split, pairs in answers.items():
        for style in ("terse", "natural"):
            subset = [(row, body) for row, body in pairs if row.get("style", "terse") == style]

            if subset:
                report(f"{split}, {style} phrasing", tally(subset))

    holdout = results["holdout"]
    measured = {
        "retrieved_gold_rate": round(holdout["retrieved_gold"] / holdout["answerable"], 3),
        "answered_rate": round(holdout["answered"] / holdout["answerable"], 3),
        "declined_rate": round(holdout["declined"] / holdout["unanswerable"], 3),
    }
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}

    absolute = {
        "gold chunk retrieved for at least 80%": measured["retrieved_gold_rate"] >= 0.8,
    }
    regressions = {
        f"{name} no worse than {baseline[name]}": value >= baseline[name]
        for name, value in measured.items()
        if name in baseline
    }
    open_targets = {
        "declines every unanswerable question": holdout["declined"] == holdout["unanswerable"],
        "answers every answerable question": holdout["answered"] == holdout["answerable"],
    }

    if holdout["unavailable"]:
        print(f"measurement invalid: the provider was unavailable for "
              f"{holdout['unavailable']} of {len(load('holdout'))} holdout questions.")
        print("re-run with --pace 2.5 to stay under the rate limit.")

        return 2

    print("gate, on the holdout split")

    for name, ok in {**absolute, **regressions}.items():
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")

    if not regressions:
        print("   (no baseline recorded; run with --record)")

    for name, met in open_targets.items():
        print(f"   {'MET ' if met else 'OPEN'}  {name}")

    if args.record:
        BASELINE.write_text(json.dumps(measured, indent=2))
        print(f"\nbaseline recorded: {measured}")

    return 0 if all(absolute.values()) and all(regressions.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
