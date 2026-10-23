"""Metrics of the paper: accuracy, bootstrap intervals, exact McNemar tests, signal detection and swap consistency."""
import numpy as np
from scipy.stats import binomtest, norm


def accuracy(correct) -> float:
    """Share of correct answers in percent."""
    return float(np.mean(correct) * 100)


def bootstrap_ci(correct, n=2000, rng=None, level=0.95):
    """Percentile bootstrap interval of the accuracy in percent.

    The paper draws the intervals of all models from one generator seeded with 0, in the model order of ergosight.MODELS,
    so pass the same generator to every call to reproduce them to the decimal.
    """
    v = np.asarray(correct, dtype=float)
    rng = rng if rng is not None else np.random.default_rng(0)
    stats = [rng.choice(v, len(v)).mean() * 100 for _ in range(n)]
    lo, hi = np.percentile(stats, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def mcnemar_exact(a, b) -> float:
    """Exact McNemar p value for two paired vectors of correctness on the same questions."""
    a, b = np.asarray(a, dtype=int), np.asarray(b, dtype=int)
    f, g = int(((a == 0) & (b == 1)).sum()), int(((a == 1) & (b == 0)).sum())
    if f + g == 0:
        return 1.0
    return float(binomtest(min(f, g), f + g, 0.5).pvalue)


def signal_detection(truth_violating, judged_violating):
    """Hit rate H, false-alarm rate F (in percent), sensitivity d' and criterion c of detection answers.

    Violating elements are the signal. A reply that cannot be read counts as not judging the element violating.
    """
    t = np.asarray(truth_violating, dtype=bool); j = np.asarray(judged_violating, dtype=bool)
    h = (j & t).sum() / t.sum(); f = (j & ~t).sum() / (~t).sum()
    return float(h * 100), float(f * 100), float(norm.ppf(h) - norm.ppf(f)), float(-(norm.ppf(h) + norm.ppf(f)) / 2)


def swap_consistency(correct_by_qid: dict, pairs) -> float:
    """Share of position-swapped pairs on which a model is either right on both or wrong on both, in percent."""
    same = [correct_by_qid[a] == correct_by_qid[b] for a, b in pairs if a in correct_by_qid and b in correct_by_qid]
    return float(np.mean(same) * 100) if same else float('nan')


def cluster_bootstrap_ci(correct, clusters, n=2000, rng=None, level=0.95):
    """Percentile bootstrap interval of the accuracy in percent that resamples whole clusters, such as all questions of one page."""
    v = np.asarray(correct, dtype=float); c = np.asarray(clusters)
    keys = np.array(sorted(set(c.tolist())))
    groups = [np.where(c == k)[0] for k in keys]
    rng = rng if rng is not None else np.random.default_rng(0)
    stats = []
    for _ in range(n):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        stats.append(v[idx].mean() * 100)
    lo, hi = np.percentile(stats, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def holm(pvalues):
    """Holm-adjusted p values in the order of the input."""
    p = np.asarray(pvalues, dtype=float); order = np.argsort(p); m = len(p)
    adj = np.empty(m); running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i])); adj[i] = running
    return adj
