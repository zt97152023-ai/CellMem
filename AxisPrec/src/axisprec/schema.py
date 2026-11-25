"""Strict raw-count inputs, reference capsules, and output serialization."""
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

REFERENCE_KEYS = {"F", "reference_count_sums", "column_type", "types", "genes", "donor_labels"}
BULK_KEYS = {"Y", "genes", "ids"}


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def axis_digest(genes):
    payload = json.dumps(list(genes), ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def json_file(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def table_file(path, fields, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def strings(values, name, *, unique=True):
    arr = np.asarray(values)
    if arr.ndim != 1 or arr.dtype.kind not in "US" or not len(arr):
        raise ValueError(f"{name} must be a nonempty one-dimensional string array")
    if any(not s.strip() or any(c in s for c in "\t\r\n") for s in arr.astype(str)):
        raise ValueError(f"{name} contain blank or multiline identifiers")
    arr = arr.astype(str)
    if unique and len(set(arr)) != len(arr):
        raise ValueError(f"{name} contain duplicate identifiers")
    return arr


def counts(value, shape, name):
    a = np.asarray(value, dtype=float)
    if a.shape != shape or not np.isfinite(a).all() or np.any(a < 0) or np.any(a != np.floor(a)):
        raise ValueError(f"{name} must have shape {shape} and contain finite nonnegative integer counts")
    if np.any(~np.isfinite(a.sum(axis=0))) or np.any(a.sum(axis=0) == 0):
        raise ValueError(f"{name} contains an empty or invalid library")
    return a


@dataclass(frozen=True)
class Reference:
    genes: np.ndarray
    types: np.ndarray
    donor_labels: np.ndarray
    column_type: np.ndarray
    reference_count_sums: np.ndarray
    F: np.ndarray

    @classmethod
    def from_arrays(cls, genes, types, donor_labels, column_type, reference_count_sums, F=None):
        g = strings(genes, "Reference genes")
        t = strings(types, "Candidate types")
        d = strings(donor_labels, "Donor labels", unique=False)
        c = np.asarray(column_type)
        if c.shape != d.shape or c.dtype.kind not in "iu" or not np.array_equal(np.unique(c), np.arange(len(t))):
            raise ValueError("Every candidate type needs a valid contiguous integer column code")
        if len(set(zip(d, c))) != len(c):
            raise ValueError("Reference columns must represent distinct donor–type pairs")
        x = counts(reference_count_sums, (len(g), len(d)), "Reference counts")
        normalized = x / x.sum(0)
        a = normalized if F is None else np.asarray(F, dtype=float)
        if a.shape != normalized.shape or not np.allclose(a, normalized, atol=1e-12, rtol=0):
            raise ValueError("Stored reference profiles disagree with normalized count columns")
        return cls(g, t, d, c, x, a)

    @classmethod
    def load(cls, path):
        return cls.from_arrays(**read_npz(path, REFERENCE_KEYS))

    def save(self, path):
        np.savez_compressed(path, **{name: getattr(self, name) for name in REFERENCE_KEYS})


@dataclass(frozen=True)
class Bulk:
    genes: np.ndarray
    ids: np.ndarray
    Y: np.ndarray

    @classmethod
    def from_arrays(cls, genes, ids, Y):
        g = strings(genes, "Bulk genes")
        s = strings(ids, "Bulk sample IDs")
        return cls(g, s, counts(Y, (len(g), len(s)), "Bulk counts"))

    @classmethod
    def load(cls, path):
        if Path(path).suffix.lower() == ".npz":
            return cls.from_arrays(**read_npz(path, BULK_KEYS))
        return cls.from_arrays(*read_count_tsv(path))

    def align(self, genes):
        index = {g: i for i, g in enumerate(self.genes)}
        missing = set(genes) - index.keys()
        extra = index.keys() - set(genes)
        if missing or extra:
            raise ValueError(f"Bulk and reference gene sets differ: {len(missing)} missing, {len(extra)} extra; see axisprec audit")
        if np.array_equal(self.genes, genes):
            return self
        return Bulk(np.asarray(genes), self.ids, self.Y[[index[g] for g in genes]])


def read_npz(path, required):
    with np.load(path, allow_pickle=False) as z:
        missing = required - set(z.files)
        extra = set(z.files) - required
        legacy_fields = {"n_cells", "reference_library_per_cell", "reference_observed", "identity_indices",
                         "reference_slot_ids", "Y_library_size", "reference_zero_count_mass", "reference_zero_RNA_mass"}
        allowed = legacy_fields if required == REFERENCE_KEYS else legacy_fields | REFERENCE_KEYS
        if missing or extra - allowed:
            raise ValueError(f"NPZ input fields do not match the contract: missing {sorted(missing)}, unrecognized {sorted(extra - allowed)}")
        return {k: z[k] for k in required}


def read_count_tsv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = csv.reader(f, delimiter="\t")
        head = next(rows, [])
        if len(head) < 2 or head[0] != "gene_id":
            raise ValueError("Count TSV must begin with gene_id followed by cell or sample identifiers")
        genes, matrix = [], []
        for line, row in enumerate(rows, 2):
            if len(row) != len(head):
                raise ValueError(f"Count TSV line {line} has {len(row)} fields, expected {len(head)}")
            genes.append(row[0])
            matrix.append([float(x) for x in row[1:]])
    return genes, head[1:], matrix
