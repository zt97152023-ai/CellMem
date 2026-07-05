# CellMem Innovation Claims And Experiment Plan

Date: 2026-07-05
Prepared by: Mac Codex
Input source: Windows Codex handoff in `inbox/to-mac.md`, plus existing local CellMem benchmark planning workbook.

## 1. Recommended Positioning

CellMem should not be framed as "another deconvolution method that predicts more accurate cell fractions." That framing puts it directly against BayesPrism, BLEND, MuSiC/SCDC, SQUID, SECRET, ARTdeConv, EnsDeconv, and omnideconv, where each competitor already owns a strong methodological niche.

The stronger framing is:

> CellMem learns a trainable cellular evidence space from heterogeneous deconvolution, marker, reference, and metadata-derived outputs, then performs reference-aware and disagreement-aware calibration of cellular composition evidence.

In Chinese:

> CellMem 不是把单一去卷积结果作为终点，而是把多方法、多参考、多标记和样本上下文产生的细胞组成证据组织成可学习的 evidence tokens，并在 reference shift、细胞类型缺失和方法分歧条件下进行选择性校准。

This makes the method's object of innovation the evidence representation and reliability calibration layer, not only final fraction accuracy.

## 2. Core Innovation Claims

### Innovation 1: Structured Cellular Evidence Tokens

**Claim.** CellMem converts heterogeneous outputs from deconvolution methods, marker scores, reference metadata, sample metadata, and method identities into structured cellular evidence tokens.

**Why it matters.** Existing methods usually treat a method output as either the final answer or a stacking input. CellMem instead keeps method identity, reference identity, cell-type mapping, marker evidence, and data provenance visible to the model, allowing it to learn which evidence is trustworthy under which biological and technical contexts.

**Necessary proof.**

- Token ablation: remove method id, reference id, marker token, metadata token, and provenance token separately.
- Show degradation specifically under reference shift and method-disagreement strata, not only on average.
- Show the learned token space clusters by cell family, reference source, and method bias in interpretable ways.

### Innovation 2: Trainable Cellular Evidence Space

**Claim.** CellMem learns an evidence space that encodes biological context, reference context, and reliability context across datasets.

**Why it matters.** The method is not only a neural fraction predictor. It learns a reusable representation of cellular evidence, so cross-method disagreement and reference mismatch become learnable signals rather than noise to average away.

**Necessary proof.**

- Latent probing: predict reference source, tissue/cancer type, cell family, method family, and error magnitude from CellMem embeddings.
- Cross-dataset transfer: train on one group of references or cancers, test on held-out references or cancers.
- Visualization: UMAP/CCA of evidence embeddings colored by reference, method, cell type, and error magnitude.

### Innovation 3: Selective Correction Instead Of Blind Correction

**Claim.** CellMem should correct only when evidence is unreliable, contradictory, or reference-shifted; it should avoid changing already-consistent evidence.

**Why it matters.** Strict mean and simple ensemble baselines can be hard to beat in low-noise settings. A credible CellMem claim must show "do-no-harm" behavior: no unnecessary neural correction when evidence agreement is already high, and measurable gains when evidence disagreement is high.

**Necessary proof.**

- Disagreement-stratified evaluation: low, medium, high method variance / entropy / label conflict.
- Report correction rate, harm rate, and net benefit.
- Low-disagreement samples should match strict mean or weighted mean; high-disagreement samples should improve over strict mean, ridge, stacking, and EnsDeconv-style aggregations.

### Innovation 4: Reference-Aware Calibration Under Shift

**Claim.** CellMem uses reference identity and reference-derived evidence to calibrate estimates under tissue, platform, donor, cancer type, and missing-cell-type shifts.

**Why it matters.** This is the main bridge between the data asset plan and the method claim. TCGA/GDC, GSE115469 anchors, SECRET, DeSide, BLEND, ARTdeConv, omnideconv, and GTEx each stress a different kind of reference mismatch. The asset plan should be used to make CellMem's robustness claim precise.

**Necessary proof.**

- Explicit reference-shift splits: train/reference source and test target separated by donor, condition, platform, cancer type, or tissue.
- Compare against MuSiC2, SQUID, BLEND, BayesPrism, SECRET, ARTdeConv, and EnsDeconv/stacking baselines.
- Report not only global RMSE/MAE but shift-layered bias and robustness.

### Innovation 5: Evidence-Driven Real-Tumor Interpretation

**Claim.** CellMem improves the reliability and interpretability of real tumor deconvolution evidence in TCGA-scale applications.

**Why it matters.** TCGA/WSI/clinical linkage should not be used only as a large unlabeled showcase. It should validate whether calibrated cellular evidence improves tumor purity, immune infiltration, histology association, survival stratification, subtype stability, and downstream biological interpretation.

**Necessary proof.**

- TCGA STAR counts and TPM linkage as primary real-bulk inputs.
- WSI and clinical linkage as independent downstream validation.
- Compare biological stability and clinical association against BayesPrism, DeSide, Kassandra outputs if available, EPIC/quanTIseq/MuSiC/SCDC, and strict ensemble baselines.

## 3. Experiment Architecture

The experiment plan should be organized into three layers:

1. Evidence construction experiments: prove CellMem's tokenization and evidence space are meaningful.
2. Controlled benchmark experiments: prove CellMem improves under the exact failure modes it claims to address.
3. Real-world validation experiments: prove the calibrated evidence supports stronger biological and clinical interpretation.

## 4. Main Experiment Matrix

| Exp ID | Purpose | Primary Assets | Baselines | Metrics | Success Standard |
|---|---|---|---|---|---|
| E1 | Smoke-test evidence pipeline | DeSide mini example; omnideconv/deconvData processed examples; CellMem all tokens | NNLS, strict mean, ridge/stacking | Pipeline completion, label mapping consistency, missingness report | End-to-end reproducible run with frozen schema and no silent cell-label drift |
| E2 | Matched pseudo-bulk accuracy | GSE115469 / CellMem anchors; omnideconv processed benchmarks; DeSide public GEO | NNLS, MuSiC/SCDC, BayesPrism, SQUID, strict mean, stacking | MAE, RMSE, Pearson, Spearman, CCC | CellMem is competitive with the strongest baseline and not only better than weak baselines |
| E3 | Reference-shift robustness | TCGA/GDC STAR counts with external scRNA references; GSE115469 anchors; BLEND multi-reference assets; GTEx later | MuSiC2, SQUID, BLEND, BayesPrism, EnsDeconv/stacking | Shift-stratified MAE/RMSE, bias, CCC, robustness ratio | Gains appear in high-shift strata while low-shift strata are not harmed |
| E4 | Method-disagreement selective correction | CellMem all tokens with retained method/reference/marker outputs | strict mean, weighted mean, ridge, xgboost/MLP stacking, EnsDeconv-style ensemble | Disagreement-stratified RMSE, correction rate, harm rate, net benefit | Low disagreement: no harm; high disagreement: clear improvement over strict mean and stacking |
| E5 | Missing-cell-type and partial-reference stress test | SECRET public GEO; ARTdeConv assets; simulated deletion from references | SECRET, ARTdeConv, EPIC/quanTIseq, BayesPrism, NNLS | Known-cell MAE, unknown leakage, compositional error, bias | Reduced leakage from missing cell types into known cell types |
| E6 | Deep-learning tumor benchmark | DeSide public GEO, DeSide Figshare when downloaded, TCGA 19 cancer TPM | DeSide, BayesPrism, Kassandra if available, EPIC/quanTIseq | Tumor purity correlation, TME fraction error where truth exists, downstream marker enrichment | CellMem provides stronger reliability/calibration under model disagreement, not just marginal fraction gains |
| E7 | Real TCGA downstream validation | TCGA STAR counts, TCGA TPM + WSI linkage, TCGA clinical/WSI linkage | BayesPrism, DeSide, EPIC/quanTIseq, MuSiC/SCDC, strict ensemble | WSI purity correlation, subtype stability, survival HR/C-index, immune marker enrichment | Calibrated evidence improves biological interpretability and downstream robustness |
| E8 | Ablation and interpretability | All P0 assets after schema freeze | Full CellMem vs no method token, no reference token, no marker token, no metadata token, no reliability memory | Delta MAE/RMSE, embedding probing accuracy, risk-coverage curve | Each claimed component has measurable value in its intended failure mode |

## 5. Recommended Build Order

### Phase 0: Freeze Schema

Freeze the evidence-token schema before running large benchmarks.

Minimum required fields:

- sample_id
- dataset_id
- tissue_or_cancer_type
- cell_type
- cell_family
- method_id
- reference_id
- evidence_value
- evidence_type
- data_scale
- provenance
- truth_fraction if available
- shift_label
- disagreement_features
- metadata_features

Deliverables:

- `cellmem_token_schema.tsv`
- `cell_type_mapping.tsv`
- `reference_registry.tsv`
- `method_registry.tsv`
- `dataset_registry.tsv`

### Phase 1: Connect P0 Real And Anchor Assets

Priority assets:

- TCGA/GDC STAR counts.
- TCGA TPM + WSI linkage.
- TCGA clinical/WSI linkage.
- GSE115469 / CellMem anchors.
- CellMem all tokens.

Purpose:

- Create the main real-bulk application layer.
- Preserve the anchor/truth layer needed for supervised calibration and sanity checks.

### Phase 2: Standardize Failure-Mode Benchmarks

Priority assets:

- SECRET public GEO for missing-cell-type/reference-shift benchmark.
- DeSide public GEO and mini example for deep-learning tumor benchmark.
- Official R published method outputs for fair method-comparison layer.

Purpose:

- Turn innovation claims into stress tests.
- Ensure comparisons are not limited to easy matched pseudo-bulk settings.

### Phase 3: Extend Strong Competitor And Generalization Assets

Priority assets:

- BLEND for multi-reference and individualized-reference competition.
- ARTdeConv for partial-reference and prior-based competition.
- omnideconv/deconvData for standardized benchmark ecosystem.
- GTEx for later cross-tissue real-bulk extension.

Purpose:

- Strengthen external validity.
- Show CellMem's evidence-space framing still holds when compared against the strongest recent reference-adaptive and benchmark-oriented methods.

## 6. Paper-Ready Contribution Paragraph

CellMem introduces a trainable cellular evidence space for bulk transcriptomic deconvolution. Instead of treating individual deconvolution outputs as final estimates, CellMem represents heterogeneous signals from multiple methods, references, marker scores, and sample-level metadata as structured evidence tokens. This representation enables the model to learn reliability patterns associated with reference source, method identity, biological context, and evidence disagreement. On this basis, CellMem performs selective calibration: it preserves stable estimates when independent evidence agrees, while correcting estimates under reference shift, missing-cell-type stress, and high method disagreement. We evaluate CellMem across matched pseudo-bulk benchmarks, reference-shift benchmarks, missing-reference benchmarks, and TCGA-scale real-tumor applications with WSI and clinical linkage, demonstrating that the method improves not only fraction estimation but also the reliability and interpretability of downstream cellular evidence.

## 7. Claims To Avoid

- Avoid: "CellMem is the most accurate deconvolution method."
- Avoid: "CellMem replaces BayesPrism/BLEND/SECRET/DeSide."
- Avoid: "Deep learning alone improves deconvolution."
- Avoid: reporting only global RMSE/MAE without shift/disagreement stratification.

Use instead:

- "CellMem learns a reusable evidence representation."
- "CellMem calibrates heterogeneous cellular evidence under reference shift and method disagreement."
- "CellMem provides do-no-harm selective correction."
- "CellMem improves downstream interpretability in real tumor cohorts."

## 8. Immediate Requests For Windows Codex

Please upload the full data asset artifacts into the shared repository:

- `artifacts/cellmem_data_asset_decision_table.tsv`
- `artifacts/cellmem_data_asset_decision_report.md`

The current Mac-side plan uses the summary in `inbox/to-mac.md`. Once the full TSV/report are available, the experiment matrix should be refined row by row using the actual `asset_id`, `readiness`, `decision`, `next_action`, and `caveats` columns.

