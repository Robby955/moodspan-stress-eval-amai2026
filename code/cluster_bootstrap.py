#!/usr/bin/env python3
"""
Cluster bootstrap for the AMAI 2026 stress-split results.

Reviewer 8hDb: the 100 queries are nested in 20 risk categories of 5 each, so an
i.i.d. bootstrap over the flat set of 100 treats correlated observations as
independent and may understate uncertainty. This script recomputes the four-axis
confidence intervals with the category as the resampling unit and reports the
intraclass correlation and design effect that quantify how much it matters.

Deterministic: fixed seed, pure numpy PRNG, no wall-clock or hash dependence.

Usage:
  python3 cluster_bootstrap.py
"""

import json
import math
import os
import sys
from collections import OrderedDict, defaultdict

import numpy as np

# Archive edit 1 of 3. The original read the stored artefact from its path in
# the MoodSpan repository. Here it reads data/judge_scores.json, which carries
# the same timestamp, config, aggregate, by_category, by_difficulty, and
# per-query id / category / judge-score fields, and drops the retrieved chunk
# text that is excluded from this archive (see README.md). The script touches
# none of the dropped fields, so every number below is unchanged. Pass a path
# on the command line to point it at the full artefact instead.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.normpath(
    os.path.join(_HERE, os.pardir, "data", "judge_scores.json"))
RESULTS = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT
RESULTS_LABEL = ("data/judge_scores.json (this archive)"
                 if RESULTS == _DEFAULT else RESULTS)

AXES = ["completeness", "grounding", "correctness", "safety_compliance"]
FLOOR = 4.00
SEED = 20260806
B = 10000          # bootstrap replicates for the new intervals
# Archive edit 2 of 3. Was 1000, here, in the PART 3 legend, and in the two
# labels that called method A the published one. The
# deployment's bootstrap default is 2000 (scripts/lib/eval-utils.ts
# bootstrapCI), which is the count the camera-ready reports in Section 3.4;
# every call site in the harness uses the default.
B_PAPER = 2000     # replicate count of the deployment's own bootstrap
ALPHA = 0.05


def load():
    with open(RESULTS) as fh:
        doc = json.load(fh)
    rows = []
    for q in doc["queries"]:
        js = q["judge_scores"]
        rows.append({
            "id": q["id"],
            "category": q["category"],
            **{ax: float(js[ax]) for ax in AXES},
        })
    return doc, rows


def group(rows):
    g = OrderedDict()
    for r in rows:
        g.setdefault(r["category"], []).append(r)
    return g


def pct_ci(draws, alpha=ALPHA):
    lo = float(np.percentile(draws, 100 * alpha / 2))
    hi = float(np.percentile(draws, 100 * (1 - alpha / 2)))
    return lo, hi


def iid_bootstrap(x, rng, B):
    n = len(x)
    idx = rng.integers(0, n, size=(B, n))
    return x[idx].mean(axis=1)


def cluster_bootstrap(by_cat, axis, rng, B, two_stage):
    """Resample the 20 categories with replacement.

    two_stage=False: take each drawn category's 5 queries whole (cluster
    bootstrap proper -- the standard choice when clusters are the sampling unit
    and within-cluster size is fixed by design).
    two_stage=True: additionally resample the 5 queries inside each drawn
    category with replacement, mirroring a two-stage sampling design.
    """
    cats = list(by_cat.keys())
    mat = np.array([[r[axis] for r in by_cat[c]] for c in cats], dtype=float)
    G, m = mat.shape
    out = np.empty(B, dtype=float)
    for b in range(B):
        pick = rng.integers(0, G, size=G)
        block = mat[pick]
        if two_stage:
            inner = rng.integers(0, m, size=(G, m))
            block = np.take_along_axis(block, inner, axis=1)
        out[b] = block.mean()
    return out


def icc_oneway(by_cat, axis):
    """One-way random-effects ICC(1) from the balanced ANOVA decomposition."""
    cats = list(by_cat.keys())
    mat = np.array([[r[axis] for r in by_cat[c]] for c in cats], dtype=float)
    G, m = mat.shape
    grand = mat.mean()
    cat_means = mat.mean(axis=1)
    ss_between = m * ((cat_means - grand) ** 2).sum()
    ss_within = ((mat - cat_means[:, None]) ** 2).sum()
    ms_between = ss_between / (G - 1)
    ms_within = ss_within / (G * (m - 1))
    if ms_between + (m - 1) * ms_within == 0:
        return 0.0, 1.0, ms_between, ms_within
    icc = (ms_between - ms_within) / (ms_between + (m - 1) * ms_within)
    deff = 1 + (m - 1) * icc
    return float(icc), float(deff), float(ms_between), float(ms_within)


def cluster_robust_t(by_cat, axis, alpha=ALPHA):
    """Analytic cluster-robust interval: SE from the spread of cluster means,
    Student-t with G-1 degrees of freedom. Balanced design, so the cluster mean
    of means equals the overall mean."""
    cats = list(by_cat.keys())
    cat_means = np.array([np.mean([r[axis] for r in by_cat[c]]) for c in cats])
    G = len(cat_means)
    mean = float(cat_means.mean())
    se = float(cat_means.std(ddof=1) / math.sqrt(G))
    # t_{0.975, 19} = 2.093024054
    tcrit = 2.093024054
    return mean, se, mean - tcrit * se, mean + tcrit * se


def naive_se(x):
    return float(np.std(x, ddof=1) / math.sqrt(len(x)))


def main():
    doc, rows = load()
    by_cat = group(rows)
    cfg = doc["config"]

    print("=" * 78)
    print("CLUSTER BOOTSTRAP -- AMAI 2026 stress split")
    print("=" * 78)
    print(f"artifact          : {RESULTS_LABEL}")
    print(f"artifact timestamp: {doc['timestamp']}")
    print(f"system under test : {cfg['model']} via {cfg['generation_backend']}"
          f" (temperature {cfg['temperature']})")
    print(f"judge             : {cfg['judge_model']} via {cfg['judge_backend']}"
          f" (temperature {cfg['judge_temperature']})")
    print(f"queries           : {len(rows)}")
    print(f"categories        : {len(by_cat)}"
          f"  sizes {sorted(set(len(v) for v in by_cat.values()))}")
    print(f"seed              : {SEED}   replicates: {B} "
          f"(deployment bootstrap uses {B_PAPER})")
    print()

    # Archive edit 3 of 3. The i.i.d. column of the paper's Table 1 is read from
    # the artefact rather than recomputed, so it is printed here directly. The
    # methods below re-run the resampling and will land near, not exactly on,
    # these endpoints, the bootstrap being unseeded in the deployment.
    print("stored aggregate intervals (the paper's Table 1 i.i.d. column):")
    for ax in AXES:
        a = doc["aggregate"][ax]
        print(f"  {ax:18s} mean {a['mean']:.2f}  "
              f"95% CI [{a['ci_lower']:.2f}, {a['ci_upper']:.2f}]")
    print(f"  hallucination rate {doc['aggregate']['hallucination_rate']['mean']:.2f}"
          f"   constitutional pass rate "
          f"{doc['aggregate']['constitutional_pass_rate']:.2f}")
    print()

    # ---------------------------------------------------------------- part 1
    print("-" * 78)
    print("PART 1  Score distributions (verification of the published counts)")
    print("-" * 78)
    for ax in AXES:
        counts = defaultdict(int)
        for r in rows:
            counts[int(r[ax])] += 1
        line = "  ".join(f"{s}/5:{counts.get(s, 0):3d}" for s in range(1, 6))
        vals = np.array([r[ax] for r in rows])
        # mode, and whether the histogram is unimodal (monotone up then down)
        seq = [counts.get(s, 0) for s in range(1, 6)]
        peak = int(np.argmax(seq))
        up = all(seq[i] <= seq[i + 1] for i in range(peak))
        down = all(seq[i] >= seq[i + 1] for i in range(peak, 4))
        shape = "unimodal" if (up and down) else "NOT unimodal"
        print(f"{ax:18s} {line}   mean {vals.mean():.2f}  median "
              f"{np.median(vals):.1f}  mode {peak + 1}/5  {shape}")
    print()
    comp = [0] * 6
    for r in rows:
        comp[int(r["completeness"])] += 1
    print("completeness detail: 1/5 n=%d, 2/5 n=%d, 3/5 n=%d, 4/5 n=%d, 5/5 n=%d"
          % (comp[1], comp[2], comp[3], comp[4], comp[5]))
    print("  mass at the modal score 3/5 and its neighbours (2-4): %d/100"
          % (comp[2] + comp[3] + comp[4]))
    print("  mass at or below 2/5: %d/100 ; at or above 4/5: %d/100"
          % (comp[1] + comp[2], comp[4] + comp[5]))
    d = np.diff([comp[s] for s in range(1, 6)])
    print("  first differences of the histogram (2-1, 3-2, 4-3, 5-4): "
          + ", ".join(f"{int(v):+d}" for v in d))
    print("  sign changes in the first differences: %d  (a second mode needs "
          "at least two)" % sum(1 for i in range(3)
                                if (d[i] > 0) != (d[i + 1] > 0)))
    print()

    # ---------------------------------------------------------------- part 2
    print("-" * 78)
    print("PART 2  Intraclass correlation and design effect (m=5 per category)")
    print("-" * 78)
    icc_tab = {}
    for ax in AXES:
        icc, deff, msb, msw = icc_oneway(by_cat, ax)
        n_eff = len(rows) / deff if deff > 0 else float("nan")
        icc_tab[ax] = (icc, deff, n_eff)
        print(f"{ax:18s} MS_between {msb:6.3f}  MS_within {msw:6.3f}  "
              f"ICC(1) {icc:+.3f}  design effect {deff:.3f}  "
              f"effective n {n_eff:5.1f}")
    print()

    # ---------------------------------------------------------------- part 3
    print("-" * 78)
    print("PART 3  Confidence intervals, four methods")
    print("-" * 78)
    print("A = i.i.d. percentile bootstrap over 100 queries, %d draws "
          "(the deployment's own method and default)" % B_PAPER)
    print("B = i.i.d. percentile bootstrap over 100 queries, %d draws" % B)
    print("C = cluster percentile bootstrap, 20 categories resampled whole, "
          "%d draws" % B)
    print("D = cluster percentile bootstrap, two-stage (categories then "
          "queries), %d draws" % B)
    print("E = analytic cluster-robust t interval on the 20 category means, "
          "df=19")
    print()

    summary = {}
    for ax in AXES:
        x = np.array([r[ax] for r in rows], dtype=float)
        mean = float(x.mean())

        rng = np.random.default_rng(SEED)
        a_lo, a_hi = pct_ci(iid_bootstrap(x, rng, B_PAPER))

        rng = np.random.default_rng(SEED + 1)
        b_lo, b_hi = pct_ci(iid_bootstrap(x, rng, B))

        rng = np.random.default_rng(SEED + 2)
        c_draws = cluster_bootstrap(by_cat, ax, rng, B, two_stage=False)
        c_lo, c_hi = pct_ci(c_draws)

        rng = np.random.default_rng(SEED + 3)
        d_draws = cluster_bootstrap(by_cat, ax, rng, B, two_stage=True)
        d_lo, d_hi = pct_ci(d_draws)

        e_mean, e_se, e_lo, e_hi = cluster_robust_t(by_cat, ax)

        print(f"[{ax}]  mean {mean:.2f}   naive SE {naive_se(x):.4f}   "
              f"cluster SE {e_se:.4f}   SE ratio {e_se / naive_se(x):.3f}")
        for tag, lo, hi in (("A deployment      ", a_lo, a_hi),
                            ("B iid   %5d   " % B, b_lo, b_hi),
                            ("C cluster whole  ", c_lo, c_hi),
                            ("D cluster 2-stage", d_lo, d_hi),
                            ("E cluster t df=19", e_lo, e_hi)):
            width = hi - lo
            rel = "" if tag.startswith("A") else ""
            print(f"    {tag}  [{lo:5.2f}, {hi:5.2f}]  width {width:.3f}{rel}")
        widen_c = (c_hi - c_lo) / (a_hi - a_lo)
        widen_e = (e_hi - e_lo) / (a_hi - a_lo)
        print(f"    width ratio vs published: cluster {widen_c:.2f}x, "
              f"cluster-t {widen_e:.2f}x")
        summary[ax] = dict(mean=mean, a=(a_lo, a_hi), b=(b_lo, b_hi),
                           c=(c_lo, c_hi), d=(d_lo, d_hi), e=(e_lo, e_hi),
                           icc=icc_tab[ax][0], deff=icc_tab[ax][1])
        print()

    # ---------------------------------------------------------------- part 4
    print("-" * 78)
    print("PART 4  Contract verdicts against the 4.00 floor under every method")
    print("-" * 78)
    print("completeness clause: reject if the whole interval lies below 4.00")
    print("grounding clause   : pass if the whole interval lies above 4.00")
    print()
    for ax in AXES:
        s = summary[ax]
        for tag, key in (("A deployment", "a"), ("B iid long", "b"),
                         ("C cluster", "c"), ("D cluster 2-stage", "d"),
                         ("E cluster t", "e")):
            lo, hi = s[key]
            if hi < FLOOR:
                verdict = "entirely BELOW 4.00"
            elif lo > FLOOR:
                verdict = "entirely ABOVE 4.00"
            else:
                verdict = "SPANS 4.00"
            print(f"{ax:18s} {tag:18s} [{lo:5.2f}, {hi:5.2f}]  {verdict}")
        print()

    print("-" * 78)
    print("PART 5  Does any headline conclusion change?")
    print("-" * 78)
    checks = []
    for key, tag in (("c", "cluster whole"), ("d", "cluster 2-stage"),
                     ("e", "cluster t df=19")):
        comp_hi = summary["completeness"][key][1]
        gr_lo = summary["grounding"][key][0]
        sf_lo = summary["safety_compliance"][key][0]
        ok = comp_hi < FLOOR and gr_lo > FLOOR
        checks.append(ok)
        print(f"{tag:18s} completeness upper {comp_hi:.2f} < 4.00 : "
              f"{comp_hi < FLOOR} | grounding lower {gr_lo:.2f} > 4.00 : "
              f"{gr_lo > FLOOR} | safety lower {sf_lo:.2f} > 4.00 : "
              f"{sf_lo > FLOOR}")
    print()
    print("separation preserved under every cluster method: %s"
          % ("YES" if all(checks) else "NO"))
    print()

    # margin to the floor, worst case across methods
    worst_comp = max(summary["completeness"][k][1] for k in "abcde")
    worst_gr = min(summary["grounding"][k][0] for k in "abcde")
    print(f"worst-case completeness upper across all five methods: "
          f"{worst_comp:.2f}  (margin to floor {FLOOR - worst_comp:+.2f})")
    print(f"worst-case grounding lower across all five methods:    "
          f"{worst_gr:.2f}  (margin to floor {worst_gr - FLOOR:+.2f})")
    print()
    print("-" * 78)
    print("PART 6  Category means, completeness (the clustering that matters)")
    print("-" * 78)
    cms = sorted(((float(np.mean([r["completeness"] for r in v])), k)
                  for k, v in by_cat.items()))
    for m, k in cms:
        print(f"  {k:26s} {m:.1f}")
    arr = np.array([m for m, _ in cms])
    print(f"  spread of the 20 category means: min {arr.min():.1f} "
          f"max {arr.max():.1f} sd {arr.std(ddof=1):.3f}")
    print(f"  category means at or above the 4.00 floor: "
          f"{int((arr >= FLOOR).sum())}/20")
    print()

    # ---------------------------------------------------------------- part 7
    print("-" * 78)
    print("PART 7  Is there any detectable between-category clustering at all?")
    print("-" * 78)
    print("One-way ANOVA F = MS_between / MS_within, df = (19, 80).")
    print("Exact permutation test: category labels shuffled across the 100")
    print("queries, %d permutations, seed %d. p = share of permutations with"
          % (B, SEED + 7))
    print("F at least as large as observed. Large p means the observed")
    print("between-category spread is what label-free resampling produces.")
    print()
    for ax in AXES:
        cats = list(by_cat.keys())
        mat = np.array([[r[ax] for r in by_cat[c]] for c in cats], dtype=float)
        G, m = mat.shape

        def fstat(a):
            grand = a.mean()
            cm = a.mean(axis=1)
            msb = m * ((cm - grand) ** 2).sum() / (G - 1)
            msw = ((a - cm[:, None]) ** 2).sum() / (G * (m - 1))
            return msb / msw if msw > 0 else float("inf")

        f_obs = fstat(mat)
        flat = mat.reshape(-1).copy()
        rng = np.random.default_rng(SEED + 7)
        ge = 0
        for b in range(B):
            perm = rng.permutation(flat).reshape(G, m)
            if fstat(perm) >= f_obs:
                ge += 1
        p = (ge + 1) / (B + 1)
        print(f"{ax:18s} F(19,80) = {f_obs:5.3f}   permutation p = {p:.3f}"
              f"   {'no detectable clustering' if p > 0.05 else 'CLUSTERING DETECTED'}")
    print()
    print("done.")


if __name__ == "__main__":
    main()
