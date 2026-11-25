"""Construct donor-by-type count profiles and assess reference support."""
import csv
from pathlib import Path

from .schema import Reference, axis_digest, counts, read_count_tsv, strings

import numpy as np
from scipy import sparse


def from_counts(genes, ids, matrix, donors, labels):
    ids = strings(ids, "Reference cell IDs")
    donors = strings(donors, "Reference donor IDs", unique=False)
    labels = strings(labels, "Reference cell types", unique=False)
    if len(donors) != len(ids) or len(labels) != len(ids):
        raise ValueError("Each reference cell needs exactly one donor and cell-type label")
    shape = (len(genes), len(ids))
    if sparse.issparse(matrix):
        x = matrix.tocsr().astype(float)
        if (x.shape != shape or not np.isfinite(x.data).all() or np.any(x.data < 0)
                or np.any(x.data != np.floor(x.data)) or np.any(np.asarray(x.sum(axis=0)) <= 0)):
            raise ValueError("Invalid sparse reference counts or empty cell library")
    else:
        x = counts(matrix, shape, "Reference counts")
    types = sorted(set(labels))
    codes = {t: i for i, t in enumerate(types)}
    pairs = sorted(set(zip(labels, donors)))
    index = {key: i for i, key in enumerate(pairs)}
    columns = [index[key] for key in zip(labels, donors)]
    group = sparse.csr_matrix((np.ones(len(ids)), (range(len(ids)), columns)), shape=(len(ids), len(pairs)))
    aggregated = x @ group
    if sparse.issparse(aggregated):
        aggregated = aggregated.toarray()
    return Reference.from_arrays(genes, types, [d for _, d in pairs], [codes[t] for t, _ in pairs], aggregated)


def reference_from_file(path, metadata=None, *, count_layer="counts", donor_column="donor_id", type_column="cell_type"):
    path = Path(path)
    if path.suffix.lower() == ".npz":
        if metadata is not None:
            raise ValueError("A reference capsule already contains donor and cell-type metadata")
        return Reference.load(path)
    if path.suffix.lower() == ".h5ad":
        if metadata is not None:
            raise ValueError("For h5ad input, supply donor and type columns in obs")
        try:
            import anndata
        except ImportError as exc:
            raise ValueError("Install the optional h5ad dependencies: pip install '.[h5ad]'") from exc
        dataset = anndata.read_h5ad(path)
        if count_layer != "X" and count_layer not in dataset.layers:
            raise ValueError(f"Missing raw-count layer {count_layer!r}; supply --count-layer X only for raw X")
        for key in (donor_column, type_column):
            if key not in dataset.obs or dataset.obs[key].isna().any():
                raise ValueError(f"Missing or incomplete h5ad obs column {key!r}")
        matrix = dataset.X if count_layer == "X" else dataset.layers[count_layer]
        return from_counts(dataset.var_names.astype(str).to_numpy(dtype=str), dataset.obs_names.astype(str).to_numpy(dtype=str),
                           matrix.T, dataset.obs[donor_column].to_numpy(dtype=str), dataset.obs[type_column].to_numpy(dtype=str))
    if metadata is None:
        raise ValueError("Reference TSV requires --metadata with cell_id, donor_id, cell_type")
    genes, ids, matrix = read_count_tsv(path)
    with Path(metadata).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = ("cell_id", donor_column, type_column)
        if not set(fields).issubset(reader.fieldnames or []):
            raise ValueError(f"Missing reference metadata columns: {', '.join(fields)}")
        rows = list(reader)
    labels = {r["cell_id"]: (r[donor_column], r[type_column]) for r in rows}
    if len(labels) != len(rows) or set(labels) != set(ids):
        raise ValueError("Reference TSV and metadata cell IDs must match exactly and uniquely")
    donors, types = zip(*(labels[c] for c in ids))
    return from_counts(genes, ids, matrix, donors, types)


def lodo(reference):
    """Compare a held donor/type profile with other-donor type means, using a strict tie rule."""
    types, donors, codes, profiles = reference.types, reference.donor_labels, reference.column_type, reference.F
    totals = dict.fromkeys(range(len(types)), 0)
    wins = totals.copy()
    for donor in sorted(set(donors)):
        retained = donors != donor
        groups = {k: profiles[:, retained & (codes == k)].mean(1) for k in totals
                  if np.count_nonzero(retained & (codes == k)) >= 2}
        if len(groups) < 2:
            continue
        for idx in np.flatnonzero(~retained):
            k = codes[idx]
            if k not in groups:
                continue
            profile = profiles[:, idx]
            similarities = {i: float(np.sqrt(profile * mean).sum()) for i, mean in groups.items()}
            wins[k] += similarities[k] > max(v for t, v in similarities.items() if t != k)
            totals[k] += 1
    return totals, wins


def audit_reference(reference, panels, bulk=None):
    totals, wins = lodo(reference)
    eligibility = []
    for k, label in enumerate(reference.types):
        n = int(np.count_nonzero(reference.column_type == k))
        panel = panels[k]
        eligibility.append(dict(cell_type=str(label), reference_donors=n, identity_genes=len(panel),
                                reference_eligible=n >= 2 and len(panel) >= 8, lodo_folds=totals[k], lodo_wins=wins[k],
                                lodo_win_rate=float(wins[k] / totals[k]) if totals[k] else None,
                                lodo_status="SCORED" if totals[k] else "INSUFFICIENT_COMPARABLE_FOLDS"))
    messages = []
    if not all(v["reference_eligible"] for v in eligibility):
        messages.append("Some candidate types lack reference support for positive calls")
    coverage = None
    if bulk is not None:
        ref_set, bulk_set = set(reference.genes), set(bulk.genes)
        common = len(ref_set & bulk_set)
        coverage = dict(reference_genes=len(ref_set), bulk_genes=len(bulk_set), shared_genes=common,
                        reference_coverage=common / len(ref_set), missing_reference_genes=sorted(ref_set-bulk_set),
                        extra_bulk_genes=sorted(bulk_set-ref_set), exact_gene_set=ref_set==bulk_set,
                        identical_order=np.array_equal(reference.genes, bulk.genes))
        if not coverage["exact_gene_set"]:
            messages.append("Bulk gene set is not eligible for frozen deconvolution")
    report = dict(reference_gene_axis_sha256=axis_digest(reference.genes), reference_gene_count=len(reference.genes),
                  reference_donors=len(set(reference.donor_labels)), reference_profiles=len(reference.donor_labels),
                  candidate_types=reference.types.tolist(), bulk_gene_coverage=coverage, warnings=messages,
                  denominator="RNA fractions over the supplied gene axis and reference candidate menu",
                  unrepresented_type_coverage="UNKNOWN_WITHOUT_ORTHOGONAL_INFORMATION",
                  lodo_policy="Report only. Fit requires two remaining donors for the target type and each eligible rival.")
    return report, eligibility
