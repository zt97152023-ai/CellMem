"""Command-line entry points for reference audit and single-sample inference."""
import argparse
import json
from pathlib import Path
import platform
import sys

from . import __version__
from .solver import METHOD, smoothed_reference, solve
from . import audit, gate, schema
import numpy as np
import scipy


AUDIT_FIELDS = ("cell_type", "reference_donors", "identity_genes", "reference_eligible", "lodo_folds",
                "lodo_wins", "lodo_win_rate", "lodo_status")
QUANTITY_FIELDS = ("sample_id", "cell_type", "rna_fraction")
PRESENCE_FIELDS = (*QUANTITY_FIELDS, "reference_donors", "identity_genes", "quantity_certified", "call", "reason",
                   "evidence_detail", "loto_gain", "gene_consistency", "identity_support", "max_positive_gene_share",
                   "mechanism_certified")


def output_dir(path):
    path = Path(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError("Output directory must be new or empty")
    path.mkdir(parents=True, exist_ok=True)
    return path


def audit_command(args):
    ref = audit.reference_from_file(args.reference, args.metadata, count_layer=args.count_layer,
                                    donor_column=args.donor_column, type_column=args.type_column)
    bulk = schema.Bulk.load(args.bulk) if args.bulk else None
    report, eligibility = audit.audit_reference(ref, gate.markers(ref), bulk)
    output = output_dir(args.out_dir)
    ref.save(output / "reference.npz")
    schema.table_file(output / "reference_eligibility.tsv", AUDIT_FIELDS, eligibility)
    report.update(package_version=__version__, reference_capsule_sha256=schema.digest(output / "reference.npz"),
                  input_sha256={name:schema.digest(path) for name,path in
                                (("reference",args.reference),("metadata",args.metadata),("bulk",args.bulk)) if path})
    schema.json_file(output / "audit_report.json", report)


def load_reference_capsule(path):
    path = Path(path)
    if path.is_dir():
        capsule = path / "reference.npz"
        report = json.loads((path / "audit_report.json").read_text(encoding="utf-8"))
        if schema.digest(capsule) != report["reference_capsule_sha256"]:
            raise ValueError("Reference capsule disagrees with the audit report hash")
    else:
        capsule = path
    return schema.Reference.load(capsule), capsule


def failed_call(detail):
    return dict(call="ABSTAIN", reason="ABSTAIN_FIT_FAILED", evidence_detail=detail, loto_gain=None,
                gene_consistency=None, identity_support=None, max_positive_gene_share=None, mechanism_certified=False)


def deconvolve(reference, bulk):
    bulk = bulk.align(reference.genes)
    panels = gate.markers(reference)
    P = smoothed_reference(reference)
    support = np.bincount(reference.column_type, minlength=len(reference.types))
    quantity_rows, presence_rows, numerical = [], [], []
    for j, sample in enumerate(bulk.ids):
        column = schema.Bulk(bulk.genes, bulk.ids[j:j + 1], bulk.Y[:, j:j + 1])
        failure = None
        try:
            values, diagnostics = solve(reference, column)
            q = [float(x) for x in values[0]]
            d = diagnostics[0]
            if not np.isfinite(q).all() or abs(sum(q) - 1) > 1e-8 or min(q) < 0:
                raise FloatingPointError("Invalid fitted composition")
        except (ValueError, ArithmeticError, RuntimeError, np.linalg.LinAlgError) as exc:
            failure = str(exc)
            q = [None] * len(reference.types)
            d = {"numeric_certified": False, "global_simplex_gap": None, "initial_gap": None}
        numerical.append(dict(sample_id=str(sample), quantity_certified=d["numeric_certified"],
                              initial_gap=d["initial_gap"], weighted_gap=d["global_simplex_gap"], quantity_error=failure))
        for k, (label, fraction) in enumerate(zip(reference.types, q, strict=True)):
            row = dict(sample_id=str(sample), cell_type=str(label), rna_fraction=fraction)
            quantity_rows.append(row)
            if failure is not None:
                state = failed_call("QUANTITY_FIT_FAILED")
            else:
                try:
                    state = gate.presence(P, bulk.Y[:, j], reference.column_type, k, panels[k], fraction)
                except (ValueError, ArithmeticError, RuntimeError, np.linalg.LinAlgError) as exc:
                    state = failed_call(str(exc))
            presence_rows.append(dict(row, reference_donors=int(support[k]), identity_genes=len(panels[k]),
                                      quantity_certified=d["numeric_certified"], **state))
    return quantity_rows, presence_rows, numerical


def deconvolve_command(args):
    reference, capsule = load_reference_capsule(args.reference)
    bulk = schema.Bulk.load(args.bulk)
    gate.thresholds()
    q, calls, numerical = deconvolve(reference, bulk)
    output = output_dir(args.out_dir)
    schema.table_file(output / "proportions.tsv", QUANTITY_FIELDS, q)
    schema.table_file(output / "presence_calls.tsv", PRESENCE_FIELDS, calls)
    schema.json_file(output / "run_receipt.json", dict(
        package_version=__version__, python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        method=METHOD, numeric_core_sha256=schema.digest(Path(__file__).with_name("_frozen_core.py")),
        rule_version=gate.RULE_VERSION, rule_sha256=gate.RULE_HASH,
        gene_axis_sha256=schema.axis_digest(reference.genes), reference_sha256=schema.digest(capsule), bulk_sha256=schema.digest(args.bulk),
        samples=len(bulk.ids), candidate_types=len(reference.types), numerical=numerical,
        presence_fit_failed_sites=sum(r["reason"] == "ABSTAIN_FIT_FAILED" for r in calls),
        output_sha256={name:schema.digest(output / name) for name in ("proportions.tsv","presence_calls.tsv")}))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="axisprec", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    stages = parser.add_subparsers(dest="command", required=True)
    p = stages.add_parser("audit", help="Build and audit a reference capsule")
    p.add_argument("--reference", required=True, help="Reference count TSV, H5AD, or donor-by-type NPZ")
    p.add_argument("--metadata", help="Cell metadata TSV for count TSV references")
    p.add_argument("--bulk", help="Optional bulk TSV or NPZ for gene-axis checks")
    p.add_argument("--count-layer", default="counts", help="Raw-count H5AD layer, or X when it contains raw counts")
    p.add_argument("--donor-column", default="donor_id")
    p.add_argument("--type-column", default="cell_type")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(run=audit_command)
    p = stages.add_parser("deconvolve", help="Estimate RNA fractions and apply frozen selective calls")
    p.add_argument("--reference", required=True, help="Audit output directory or reference NPZ")
    p.add_argument("--bulk", required=True, help="Bulk count TSV or NPZ")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(run=deconvolve_command)
    args = parser.parse_args(argv)
    try:
        args.run(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"axisprec: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
