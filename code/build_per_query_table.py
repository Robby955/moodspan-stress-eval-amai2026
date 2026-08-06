#!/usr/bin/env python3
"""
Derive the released per-query table and the scores-only artefact from the
stored evaluation artefact.

Input (not in this archive), the stored evaluation artefact:
  data/eval/results/response-quality-2026-06-03T21-25-19-592Z.json
in the MoodSpan deployment repository. Pass its path as the only argument.

Outputs (in this archive):
  data/per_query_results.jsonl   100 rows, one JSON object per query
  data/per_query_results.csv     the same 100 rows, flat
  data/judge_scores.json         id, category, judge scores, and the artefact's
                                 own aggregate / by_category / by_difficulty
                                 blocks; this is what cluster_bootstrap.py reads

What is dropped on the way through, and why:

  grounding_contract.retrieval_sources   full text of every retrieved chunk.
  grounding_contract.source_index        titles and paths of those chunks.
      These are the retrieval corpus. The corpus manifest records it as
      retrieval-only, excluded from public indexing, and not clinician
      reviewed, so it is not published here.

  kira_response, grounding_contract.original_text, .final_text
      Generated answers over that corpus. Dropped with it.

Everything else in the artefact is carried through unchanged.

Usage:
  python3 build_per_query_table.py path/to/response-quality-2026-06-03T21-25-19-592Z.json
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.dirname(HERE)
ARTEFACT_NAME = "response-quality-2026-06-03T21-25-19-592Z.json"

AXES = ["completeness", "grounding", "correctness", "safety_compliance"]

COLUMNS = [
    "id",
    "category",
    "difficulty",
    "question",
    "safety_level",
    "guard_blocked",
    "context_chunks",
    "completeness",
    "grounding",
    "correctness",
    "safety_compliance",
    "hallucination_detected",
    "hallucination_details",
    "judge_explanation",
    "critique_pass",
    "critique_violations",
    "contract_decision",
    "contract_reasons",
    "contract_caveats",
    "contract_unsupported_rate",
    "contract_groundedness_rate",
    "contract_invalid_citation_count",
    "latency_ms_total",
]


def main():
    if len(sys.argv) != 2:
        print("usage: build_per_query_table.py path/to/%s" % ARTEFACT_NAME)
        raise SystemExit(2)
    artefact = sys.argv[1]
    with open(artefact) as fh:
        doc = json.load(fh)

    split = {}
    with open(os.path.join(ARCHIVE, "data", "mental_health_stress_qa.jsonl")) as fh:
        for line in fh:
            row = json.loads(line)
            split[row["id"]] = row

    rows = []
    scores = []
    for q in doc["queries"]:
        js = q["judge_scores"]
        gc = q.get("grounding_contract") or {}
        crit = q.get("critique") or {}
        violations = crit.get("violations") or []

        rows.append({
            "id": q["id"],
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question": split[q["id"]]["question"],
            "safety_level": q["safety_level"],
            "guard_blocked": q["guard_blocked"],
            "context_chunks": q["context_chunks"],
            "completeness": js["completeness"],
            "grounding": js["grounding"],
            "correctness": js["correctness"],
            "safety_compliance": js["safety_compliance"],
            "hallucination_detected": js["hallucination_detected"],
            "hallucination_details": js.get("hallucination_details", ""),
            "judge_explanation": js.get("explanation", ""),
            "critique_pass": crit.get("pass"),
            "critique_violations": "; ".join(
                f'{v.get("principleId") or v.get("id")}: {v.get("explanation", "")}'
                for v in violations
            ),
            "contract_decision": gc.get("decision", ""),
            "contract_reasons": "; ".join(gc.get("reasons", [])),
            "contract_caveats": "; ".join(gc.get("caveats", [])),
            "contract_unsupported_rate": gc.get("unsupported_rate", ""),
            "contract_groundedness_rate": gc.get("groundedness_rate", ""),
            "contract_invalid_citation_count": gc.get("invalid_citation_count", ""),
            "latency_ms_total": q["latency_ms"]["total"],
        })

        scores.append({
            "id": q["id"],
            "category": q["category"],
            "difficulty": q["difficulty"],
            "judge_scores": {ax: js[ax] for ax in AXES},
        })

    out_jsonl = os.path.join(ARCHIVE, "data", "per_query_results.jsonl")
    with open(out_jsonl, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    out_csv = os.path.join(ARCHIVE, "data", "per_query_results.csv")
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    out_scores = os.path.join(ARCHIVE, "data", "judge_scores.json")
    with open(out_scores, "w") as fh:
        json.dump({
            "timestamp": doc["timestamp"],
            "config": doc["config"],
            "aggregate": doc["aggregate"],
            "by_category": doc["by_category"],
            "by_difficulty": doc["by_difficulty"],
            "queries": scores,
        }, fh, indent=1)
        fh.write("\n")

    print(f"rows written        : {len(rows)}")
    print(f"per_query_results   : {out_jsonl}")
    print(f"per_query_results   : {out_csv}")
    print(f"judge_scores        : {out_scores}")
    missing = [r["id"] for r in rows if r["contract_decision"] == ""]
    print(f"rows with no contract block (crisis path): {missing}")


if __name__ == "__main__":
    main()
