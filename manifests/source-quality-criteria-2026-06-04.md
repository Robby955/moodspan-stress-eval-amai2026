# MoodSpan Source-Quality Criteria

Status: active restoration gate. Public promotion is blocked until candidates pass this checklist and the Kira stress test does not regress.

## Success Metric

The restoration target is not article count. The target is that Kira returns grounded answers a clinician reviewer would respect. Article count is supporting metadata only.

## Criteria

1. License: public-domain, CC-BY, or explicit publisher open-access allowance. PubMed Central candidates require per-article `CC-BY` or public-domain verification through the PMC OA utility. Closed-access journals, DSM-5 text, and unclear rights are excluded.
2. Authority: WHO, NIMH, NIH, Cochrane, MEDLINE-indexed peer-reviewed work, JAMA-family, Springer Nature, Wiley, or validated screener methodology papers.
3. Substance: at least 500 words of clinical content. Abstract-only, table-only, single-paragraph editorials, and thin landing pages are rejected.
4. Topic fit: maps to the existing MoodSpan taxonomy: conditions, treatments, screeners, symptoms, neuroscience, or clinical glossary.
5. Recency: prevalence and treatment-efficacy claims need publication or revision within 7 years. Older sources are allowed for diagnostic classics and foundational neuroscience.
6. Reviewer defensibility: every candidate carries author, affiliation, official URL, retrieval date, and DOI or PMID when the source type provides one.

## Restoration Procedure

1. Crawl the approved lanes with `python3 scripts/corpus_restoration.py --dry-run`.
2. Require the candidate-level facet pre-screen before full eval. A candidate must expose at least two clinically useful facets such as symptoms, treatment, screeners, differential, functional impact, safety, prevalence, or comorbidity.
3. Require route-impact shadowing before full eval. A candidate section must not enter top-k retrieval for stress queries where the source title does not support the query topic or the routed section facet conflicts with the requested facet.
4. Review `data/corpus-restoration/candidates.jsonl` and `rejections.jsonl`.
5. Write review candidates outside public content with `--write-review-candidates`.
6. Promote only selected candidates with `--promote-content --allow-public-promotion`.
7. Rebuild the local index with `npm run index:rebuild`.
8. Run the 100-query Kira stress test.
9. Keep the restored subset only if every Kira stress metric maintains or improves the 0-article baseline: strict unsupported `0/100`, broad relevance `0/100`, refusal no higher than `1/100`, completeness at least `3.24`, grounding at least `4.78`, and safety at least `4.60`.

## Data Posture

Candidates are staged outside `content/` by default. That preserves the current no-public-corpus posture until Rob approves source quality and promotion.
