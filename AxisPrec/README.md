# AxisPrec

AxisPrec audits a single-cell reference, estimates bulk RNA fractions with the frozen full-axis donor-precision model, and returns a separate presence decision for each candidate type. Each bulk sample is processed independently. A positive call requires held-out marker evidence under the frozen rule.

## Quickstart

Use Python 3.11 or 3.12. Run these commands from the package root.

```sh
python -m pip install -e .
axisprec audit --reference examples/tiny_pbmc_demo/reference_counts.tsv --metadata examples/tiny_pbmc_demo/cells.tsv --bulk examples/tiny_pbmc_demo/bulk.tsv --out-dir audited
axisprec deconvolve --reference audited --bulk examples/tiny_pbmc_demo/bulk.tsv --out-dir result
```

The included data are synthetic. Output directories must be new or empty. Count TSVs have `gene_id` in the first column, gene IDs down the rows, and either cells or bulk samples across columns. A reference metadata TSV supplies one `cell_id`, `donor_id`, and `cell_type` per reference cell. Input counts must be raw, finite, nonnegative integers. Bulk and reference must contain the same gene identifiers. AxisPrec aligns their order and reports any missing or extra features in `audit`.

An `.h5ad` reference needs `python -m pip install -e '.[h5ad]'`. The default raw-count layer is `counts`. Use `--count-layer X` for a raw count `.X`. `--donor-column` and `--type-column` specify the donor and type fields in `.obs`. The audit command also accepts a donor-by-type reference NPZ. A bulk NPZ contains `Y` (genes × samples), `genes`, and `ids`.

## Outputs and decision contract

| File | Contents |
| --- | --- |
| `audit_report.json` | Reference and input hashes, reference candidate menu, and exact gene set overlap when bulk is supplied. |
| `reference_eligibility.tsv` | Per type donor and marker counts, presence eligibility, and held-donor nearest-rival discrimination counts. |
| `reference.npz` | Donor-by-type raw count sums, normalized profiles, donor and type keys, and ordered gene IDs. |
| `proportions.tsv` | `sample_id`, `cell_type`, `rna_fraction` for the frozen quantitative estimate. A failed fit leaves the quantity blank. |
| `presence_calls.tsv` | Quantity, reference support, `call`, `reason`, `evidence_detail`, raw `loto_gain` and `gene_consistency`, supporting diagnostics, and separate solver checks. |
| `run_receipt.json` | Package and numerical runtime versions, input and output hashes, the model and rule hashes, and per-sample convergence information. |

`ABSENT` retains the historical below-0.1% decision. `PRESENT` for an original positive requires at least two reference donors, at least eight qualified identity genes, numerically certified mechanism fits, a strictly positive held-out LOTO gain, and marker consistency of at least `0.19007912210331898`. `ABSTAIN` carries the cause `ABSTAIN_REF_UNQUALIFIED`, `ABSTAIN_WEAK_EVIDENCE`, or `ABSTAIN_FIT_FAILED`. LODO is a reference diagnostic. The hard presence rule uses donor and identity-gene counts and the two frozen score cutoffs. The three-state output gives operational calls on the supplied reference menu. It does not estimate out-of-menu mass or supply probability-based or biological absence guarantees. RNA fractions refer to the supplied gene axis. True cellular coverage requires an independent measurement when the reference menu is incomplete.

## Verification

```sh
python -m unittest discover -s tests -v
```

The synthetic CLI tests run from a standalone checkout. The historical parity test uses the original project workspace archives and checks five preselected mixtures against input-only historical predictions. Set `AXISPREC_PARITY_WORKSPACE` to point to that workspace if this package has been relocated. The test skips the archive-dependent check when those assets are unavailable. No historical expression or truth matrices are bundled in the distribution.
