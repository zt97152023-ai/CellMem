"""Thin wrapper around the archived quantitative implementation."""
from . import _frozen_core
from ._frozen_api import predict

import numpy as np

METHOD = "FULL_DONOR_PRECISION_FROZEN_20261116"


def solve(reference, bulk):
    result = predict(reference.F, reference.reference_count_sums, bulk.Y,
                     reference.column_type, n_types=len(reference.types))
    values = result["prediction"]
    # The historical release closed this already simplex-constrained result once more.
    return values / values.sum(axis=1)[:, None], result["diagnostics"]


def smoothed_reference(reference):
    return _frozen_core.prepare(reference.F, reference.reference_count_sums, np.empty(0, dtype=int))[0]["FULL_COUNT"]
