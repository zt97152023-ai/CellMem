"""Frozen reference-only marker selection and per-sample LOTO gate."""
from functools import lru_cache
from importlib.resources import files
import hashlib
import json

from . import _frozen_core as core
import numpy as np

RULE_HASH = "7236d73d324ad253bd5f6121b1a65754fccb7e25da4d092c00b1fb2f89feb5ac"
RULE_VERSION = "person433-frozen-20261125"
MIN_DONORS = 2
MIN_MARKERS = 8


@lru_cache(maxsize=1)
def thresholds():
    raw = files("axisprec").joinpath("frozen_rule.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != RULE_HASH:
        raise ValueError("Packaged presence-rule hash does not match the frozen protocol")
    a = json.loads(raw)
    return a["quantity_threshold"], a["gain_cutoff"], a["consistency_cutoff"]


def markers(reference):
    F, codes, people, genes, types = (reference.F, reference.column_type, reference.donor_labels,
                                      reference.genes, reference.types)
    centres = np.column_stack([F[:, codes == k].mean(1) for k in range(len(types))])
    panels = []
    for k in range(len(types)):
        ix = np.flatnonzero(codes == k)
        rivals = np.arange(len(types)) != k
        ranked = []
        if len(ix) >= MIN_DONORS and rivals.any():
            pooled = centres[:, rivals].max(1)
            profiles = []
            for j in ix:
                other = (people == people[j]) & (codes != k)
                maximum = np.maximum(pooled, F[:, other].max(1)) if other.any() else pooled
                profiles.append(np.log2((F[:, j] + 1e-8) / (maximum + 1e-8)))
            lower = np.quantile(profiles, .25, axis=0)
            eligible = np.flatnonzero((lower > 0) & ((F[:, ix] > 0).sum(1) >= MIN_DONORS))
            ranked = sorted(eligible, key=lambda i: (-lower[i], genes[i]))[:64]
        panels.append(np.asarray(ranked, dtype=int))
    return panels


def _holdout(P, y, codes, panel):
    fit = np.ones(len(y), bool)
    fit[panel] = False
    # The explicit all-column mask preserves the storage order used by the historical gate.
    matrix = P[fit][:, np.ones(len(codes), bool)]
    mass = matrix.sum(0)
    matrix = matrix / mass
    depth = float(y[fit].sum())
    q = y[fit] / depth
    x0, d0 = core.solve(matrix, q)
    mean, variance = np.zeros(len(q)), np.zeros(len(q))
    for k in np.unique(codes):
        columns = codes == k
        group = matrix[:, columns]
        fraction = x0[columns].sum()
        mean += fraction * group.mean(1)
        if group.shape[1] >= MIN_DONORS:
            variance += fraction**2 * group.var(1, ddof=1) / group.shape[1]
    return matrix, mass, depth, q, mean / (mean + depth * variance), d0


def _full_axis_weights(coefficients, mass):
    x = coefficients / mass
    return x / x.sum()


def presence(P, y, codes, k, panel, quantity):
    threshold, gain_cutoff, consistency_cutoff = thresholds()
    row = dict(call="ABSTAIN", reason="", evidence_detail="", loto_gain=None, gene_consistency=None,
               identity_support=None, max_positive_gene_share=None, mechanism_certified=None)
    if quantity < threshold:
        return dict(row, call="ABSENT", reason="BELOW_FIXED_THRESHOLD")
    if len(panel) < MIN_MARKERS or np.count_nonzero(codes == k) < MIN_DONORS:
        return dict(row, reason="ABSTAIN_REF_UNQUALIFIED", evidence_detail="INSUFFICIENT_REFERENCE_MARKERS_OR_DONORS")
    depth = y.sum() - y[panel].sum()
    if depth <= 0:
        return dict(row, reason="ABSTAIN_WEAK_EVIDENCE", evidence_detail="NO_COUNTS_OUTSIDE_HELD_MARKERS")
    keep = codes != k
    matrix, mass, depth, q, w, d0 = _holdout(P, y, codes, panel)
    xf, d1 = core.solve(matrix, q, w)
    xd, d2 = core.solve(matrix[:, keep], q, w)
    if not all(d["numeric_certified"] for d in (d0, d1, d2)):
        return dict(row, reason="ABSTAIN_FIT_FAILED", evidence_detail="UNCERTIFIED_MECHANISM_FIT", mechanism_certified=False)

    x = _full_axis_weights(xf, mass)
    z = _full_axis_weights(xd, mass[keep])
    mu = P[panel] @ x * depth / (mass @ x)
    null = P[panel][:, keep] @ z * depth / (mass[keep] @ z)
    scores = null - mu + y[panel] * (np.log(mu) - np.log(null))
    support = float(np.mean(y[panel] > null))
    positive = np.maximum(scores, 0.)
    max_share = float(positive.max() / positive.sum()) if positive.sum() > 0 else 1.
    gain = float(scores.sum() / (1 + y[panel].sum()))
    consistency = support * (1 - max_share)
    passed_gain, passed_consistency = gain > gain_cutoff, consistency >= consistency_cutoff
    diagnostics = dict(loto_gain=gain, gene_consistency=consistency, identity_support=support,
                       max_positive_gene_share=max_share, mechanism_certified=True)
    if passed_gain and passed_consistency:
        return dict(row, **diagnostics, call="PRESENT", reason="BOTH_MECHANISM_CHECKS_PASS")
    detail = "BOTH_BELOW" if not (passed_gain or passed_consistency) else "GAIN_BELOW" if not passed_gain else "CONSISTENCY_BELOW"
    return dict(row, **diagnostics, reason="ABSTAIN_WEAK_EVIDENCE", evidence_detail=detail)
