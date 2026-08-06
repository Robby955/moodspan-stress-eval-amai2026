// The deployment's bootstrap routine, copied verbatim from
// scripts/lib/eval-utils.ts:27-66.
//
// This is the procedure behind the i.i.d. confidence intervals stored in the
// artefact and reported in the paper's Table 1: a nonparametric percentile
// bootstrap, 2000 resamples by default, unstratified, drawing individual query
// scores with replacement over the flat array, with no seed and no cluster
// structure. Every call site in the harness uses the defaults. The paper's
// cluster analysis exists because this routine ignores the 20-by-5 design.
//
// Nothing below is edited.

// ─── scripts/lib/eval-utils.ts:27-66 ────────────────────────────────────────

// ── Bootstrap CI ──────────────────────────────────────────────────────────

export interface BootstrapResult {
  mean: number;
  ci_lower: number;
  ci_upper: number;
}

export function bootstrapCI(
  values: number[],
  nBoot: number = 2000,
  alpha: number = 0.05,
): BootstrapResult {
  const n = values.length;
  if (n === 0) return { mean: 0, ci_lower: 0, ci_upper: 0 };

  const means: number[] = [];
  for (let b = 0; b < nBoot; b++) {
    let sum = 0;
    for (let i = 0; i < n; i++) {
      sum += values[Math.floor(Math.random() * n)];
    }
    means.push(sum / n);
  }
  means.sort((a, b) => a - b);

  const lo = Math.floor((alpha / 2) * nBoot);
  const hi = Math.floor((1 - alpha / 2) * nBoot);

  return {
    mean: values.reduce((a, b) => a + b, 0) / n,
    ci_lower: means[lo],
    ci_upper: means[hi],
  };
}

export function fmtCI(ci: BootstrapResult, scale: number = 1, decimals: number = 2): string {
  const s = scale;
  return `${(ci.mean * s).toFixed(decimals)} [${(ci.ci_lower * s).toFixed(decimals)}, ${(ci.ci_upper * s).toFixed(decimals)}]`;
}
