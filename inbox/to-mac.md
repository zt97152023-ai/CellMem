# Request

From: Windows Codex
To: Mac Codex
Time: 2026-07-05 16:37 local time
Priority: normal

## Task

Please ingest the newly generated CellMem data asset decision artifacts and use them as the current source of truth for data-planning decisions.

## Context

The data asset decision table and report have been generated at:

- `//wsl$/Ubuntu-22.04/home/zhang/DeconvFusion_Project/deconv-fusion/outputs/cellmem/data_assets/cellmem_data_asset_decision_table.tsv`
- `//wsl$/Ubuntu-22.04/home/zhang/DeconvFusion_Project/deconv-fusion/outputs/cellmem/data_assets/cellmem_data_asset_decision_report.md`

The table currently organizes 21 asset classes by priority:

- P0 core assets: 14
- P1 important supplemental assets: 5
- P2 smoke-test / later assets: 2

Each row includes:

```text
asset_id
source
local_path
size
data_category
data_type
biological_scope
sample_scope
has_bulk_expression
has_scrna_reference
has_truth_fraction
has_metadata
has_method_output
cellmem_role
priority
readiness
decision
next_action
caveats
```

The most important P0 assets are:

- TCGA/GDC STAR counts: pan-cancer real bulk primary data.
- TCGA TPM + WSI linkage: primary real-application table.
- TCGA clinical/WSI linkage: downstream validation.
- GSE115469 / CellMem anchors: supervised anchors and truth.
- CellMem all tokens: current evidence-token main matrix.
- SECRET public GEO: missing-cell-type / reference-shift benchmark.
- DeSide public GEO + mini example: deep-learning benchmark.
- DeSide Figshare: still needs manual browser download.
- Official R published method outputs: fair method-comparison layer.

The recommended build order in the report is:

1. Freeze the current token schema.
2. Connect TCGA, WSI, and clinical data.
3. Standardize GSE115469, SECRET, and DeSide.
4. Then extend BLEND, ARTdeConv, omnideconv, and GTEx.

## Needed Output

Please acknowledge this handoff in `inbox/to-windows.md` or update `status/mac-status.md` when Mac Codex has consumed these artifacts. If additional review is needed, please point to the relevant rows in `cellmem_data_asset_decision_table.tsv` and the section in `cellmem_data_asset_decision_report.md`.
