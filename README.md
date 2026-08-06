# Reproducibility archive: pre-deployment stress testing of a source-grounded mental-health assistant

> R Sneiderman. *Pre-Deployment Stress Testing of Source-Grounded
> Conversational AI in Non-Imaging Mental-Health Contexts: A 100-Query,
> 20-Risk-Category Methodology with Grounded-Refusal Contracts.*
> Fifth Workshop on Applications of Medical AI (AMAI 2026), a MICCAI 2026
> satellite event. Springer LNCS.

It holds the query split, the prompts, the scoring code, the per-query results,
and the statistical script behind every number in the paper's results section.
Section 3.4 of the paper describes this archive; the contents below are what
that description promises.

The evaluated system is Kira, the retrieval-grounded assistant inside MoodSpan,
a consumer mental-health web application built and operated by the author.

## What is in here

    data/mental_health_stress_qa.jsonl   The 100-query stress split, verbatim.
                                         20 categories, 5 queries each, with
                                         expected facts, expected answer
                                         summary, and difficulty label.

    data/per_query_results.csv           The 100-row per-query table: four axis
    data/per_query_results.jsonl         scores, hallucination flag and detail,
                                         judge explanation, critique verdict and
                                         violations, safety level, and the
                                         grounding-contract decision with its
                                         reasons and caveats. Same rows in both
                                         formats. Three rows (stress_035,
                                         stress_058, stress_060) were classified
                                         crisis and routed to the crisis path,
                                         which bypasses the grounding-contract
                                         filter; their contract fields are
                                         empty. Contract decisions on the other
                                         97: 94 warn, 2 pass, 1 refuse.

    data/judge_scores.json               Scores-only view of the stored
                                         evaluation artefact: timestamp, run
                                         config, the artefact's own aggregate,
                                         by_category and by_difficulty blocks,
                                         and per-query id, category, difficulty,
                                         and judge scores. This is the input to
                                         cluster_bootstrap.py.

    code/judge_prompts.ts                buildJudgePrompt (the main rubric used
                                         for all 100 rows), buildSafetyJudgePrompt
                                         (the safety-variant rubric, which no row
                                         matched), and parseJudgeResponse, all
                                         verbatim.

    code/critique_prompt.ts              The nine constitutional principles,
                                         buildPrinciplesBlock, buildCritiquePrompt,
                                         and parseCritiqueResponse, verbatim.

    code/judge_call_sites.ts             The generation, contract, judge, and
                                         critique call sites, verbatim. These fix
                                         the decoding parameters: generation at
                                         temperature 0.3 with a 2048-token cap,
                                         judge and critique at temperature 0.1
                                         with a 512-token cap, one call each.

    code/eval_utils_bootstrap.ts         The deployment's own bootstrap routine,
                                         verbatim. Nonparametric percentile
                                         bootstrap, 2000 resamples, unstratified,
                                         unseeded, no cluster structure.

    code/cluster_bootstrap.py            The seeded cluster-bootstrap and
                                         permutation script. Reproduces every
                                         number in the paper's results section.

    code/build_per_query_table.py        Derives data/per_query_results.* and
                                         data/judge_scores.json from the stored
                                         artefact, and documents exactly which
                                         fields are dropped.

    prompts/eval_system_prompt.txt       The evaluation-side system prompt as the
                                         harness assembled it at run time: the
                                         prompt body, the constitutional
                                         principles block, and the canonical
                                         safety-context block, 10,988 characters.

    prompts/eval_system_prompt_source.ts The builder that produces it, verbatim.
    prompts/canonical_safety_context.ts  The safety-context block, verbatim.

    manifests/corpus-manifest.json       Metadata about the retrieval corpus:
                                         quarantine status, review status,
                                         promotion policy, and the corpus gate.

    manifests/source_manifest.scored.json  The 38 external sources that govern
                                         article authoring: title, URL, source
                                         type, tier, licence class, quality
                                         score, access date. Metadata only, no
                                         source text.

    manifests/source-quality-criteria-2026-06-04.md
                                         The written source-selection criteria,
                                         dated one day after the reported run.

    results/cluster_bootstrap_output.txt The output of running
                                         code/cluster_bootstrap.py in this
                                         archive.

## Reproducing the numbers

Every number in the paper's results section comes from one command:

    cd code
    python3 cluster_bootstrap.py

The run takes about a minute and writes to stdout. `results/cluster_bootstrap_output.txt`
is a stored copy of that output. The script is seeded (`SEED = 20260806`, numpy
`default_rng`), so repeated runs give identical results.

What the output covers, in order:

- The stored aggregate intervals, which are the i.i.d. column of Table 1:
  completeness 3.24 [3.04, 3.43], grounding 4.78 [4.68, 4.87], correctness
  4.05 [3.89, 4.21], safety compliance 4.60 [4.48, 4.72], hallucination rate
  0.00, constitutional pass rate 0.97.
- Part 1, the score distributions: the completeness histogram 6, 12, 43, 30, 9
  from 1/5 to 5/5, the 18 responses at or below 2/5, the 85 in the 2-to-4 band,
  and the single sign change in the first differences that makes it unimodal.
- Part 2, the intraclass correlations (completeness -0.041, correctness -0.053,
  grounding +0.018, safety compliance +0.010) and the design effects.
- Part 3, the four-axis intervals under five methods. Table 1's cluster column
  is method D, the two-stage cluster bootstrap: completeness [3.00, 3.48],
  grounding [4.64, 4.89], correctness [3.84, 4.24], safety compliance
  [4.42, 4.75].
- Parts 4 and 5, the contract verdict under every method, and the worst-case
  margins to the 4.00 floor: completeness upper 3.48, margin 0.52; grounding
  lower 4.64, margin 0.64.
- Part 6, the 20 category means for completeness, spread 2.6 to 4.2, standard
  deviation 0.403, with 2 of 20 at or above 4.00.
- Part 7, the permutation test on 10,000 shuffles: F(19,80) of 0.805, 1.089,
  0.746, 1.053 with p of 0.688, 0.377, 0.775, 0.431.

To rebuild the derived tables from the stored artefact, which requires access to
the deployment repository, run `python3 code/build_per_query_table.py` with the
artefact path as its argument.

Three edits separate `code/cluster_bootstrap.py` from the script that was run
against the deployment repository, and each is marked in the source: it resolves
the artefact path inside this archive rather than in the repository; the
replicate count for the deployment's own bootstrap is 2000 rather than 1000,
which is the implementation default and the figure the paper reports; and it
also prints the artefact's stored intervals, since Table 1's i.i.d. column is
read from the artefact rather than recomputed. No computation changed.

## Software versions

- Python 3.13.13, numpy 2.4.4. These are the only requirements for
  `cluster_bootstrap.py` and `build_per_query_table.py`.
- The TypeScript files are excerpts for inspection, not a runnable harness. In
  the deployment they run under Node 26.0.0 with tsx 4.21.0 and TypeScript 5.
- Run platform for the stored output: macOS 26.4.1, arm64.
- The evaluated run itself, on 2026-06-03, used `llama-3.3-70b-versatile`
  through the Groq API for both generation (temperature 0.3, 2048-token cap) and
  judging (temperature 0.1, 512-token cap), with `all-MiniLM-L6-v2` embeddings
  in 384 dimensions for dense retrieval. The run configuration is preserved in
  `data/judge_scores.json` under `config`.

## What is excluded, and why

**The retrieval corpus.** The corpus manifest records it as retrieval-only,
excluded from public indexing, and not clinician reviewed
(`manifests/corpus-manifest.json`, `retrievalQuarantine.reviewStatus`), and its
promotion policy forbids publishing it without a source and review checklist.
Publishing unreviewed generated clinical text as a research corpus would
contradict the deployment's own governance posture. `manifests/` therefore
carries metadata about the sources and no source text. This exclusion also
removes the per-query retrieved chunks from the released table, and with them
the split-specific support cards described in Section 3.1; the counts in that
section (71 stress, 6 condition, 12 comparison cards, retrieved by 81 of 100
queries) stand as reported and are not independently checkable from this
archive. It also removes the generated answers themselves, which are text over
that corpus. The judge's per-row explanation of each answer is retained in
`data/per_query_results.*`.

**The production system prompt.** It carries the live safety configuration of a
consumer mental-health product, including its security block, and publishing it
would publish a jailbreak target. The evaluation-side prompt is released instead
because it is the prompt that produced the evaluated text. The two are separate
copies that have diverged: 13,021 characters against 8,799 for the evaluation
copy, measured as source template literals before the principles block is
interpolated. The production copy carries a tool-use block, a separate citation
section, and a diagnostic-ambiguity section that the evaluation copy lacks, and
the two specify different follow-up formats.

Nothing in this archive contains user data, conversation logs, or personal
health information. The 100 queries were hand-authored for this evaluation, not
drawn from usage; Section 3.1 of the paper records the cross-check against the
deployment's six other evaluation splits and twelve retained usage logs, which
found no overlap. No API key, token, or credential appears in any file.

## Known limits of this archive

- The numbers are in-sample for the grounding-contract layer. The split was
  frozen before the reported run but was also used during development to harden
  that layer, so this is a contract check on a frozen split, not a held-out
  generalisation estimate. Section 3.1 of the paper states this.
- The judge is the same model that generated the responses. Self-preference is
  not excluded, and one judge call per query leaves judge variance unmeasured.
- The 4.00 floor is a reporting threshold chosen for the paper, not a gate
  pre-committed in the deployment repository. The sensitivity analysis in the
  results section covers it: moving the floor anywhere in [3.5, 4.5] changes
  neither verdict.
- No clinician verification was performed, on the split, the taxonomy, or the
  corpus.

## Licence and citation

Released under CC BY 4.0. See `LICENSE`, and `CITATION.md` for how to cite.
