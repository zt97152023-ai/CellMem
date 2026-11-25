"""Exercise the installed CLI against five original, locked person433 samples."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from axisprec import schema
import numpy as np


PACKAGE = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("AXISPREC_PARITY_WORKSPACE", PACKAGE.parent))
SAMPLES = {
    "0778269a08bc790e6eaf": "Kotliarov2020",
    "06d727e0773bfe99d602": "GSE190992",
    "7f40e0bffda283a30a75": "GSE115469",
    "0b5827cd94777484bf1e": "E-MTAB-8142",
    "01e420b0d27536859364": "TabulaSapiens2",
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def table(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def cli(*args):
    return subprocess.run([sys.executable, "-B", "-m", "axisprec.cli", *map(str, args)],
                          text=True, capture_output=True, check=False)


class CliTests(unittest.TestCase):
    def test_tiny_demo(self):
        demo = PACKAGE / "examples/tiny_pbmc_demo"
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            a = cli("audit", "--reference", demo/"reference_counts.tsv", "--metadata", demo/"cells.tsv",
                    "--bulk", demo/"bulk.tsv", "--out-dir", out/"audit")
            self.assertEqual(a.returncode, 0, a.stderr)
            report = read(out/"audit/audit_report.json")
            self.assertTrue(report["bulk_gene_coverage"]["exact_gene_set"])
            self.assertEqual([int(r["lodo_wins"]) for r in table(out/"audit/reference_eligibility.tsv")], [3, 3])
            b = cli("deconvolve", "--reference", out/"audit", "--bulk", demo/"bulk.tsv", "--out-dir", out/"result")
            self.assertEqual(b.returncode, 0, b.stderr)
            rows = table(out/"result/presence_calls.tsv")
            self.assertEqual(len(rows), 2)
            self.assertAlmostEqual(sum(float(r["rna_fraction"]) for r in rows), 1)
            self.assertIn("PRESENT", {r["call"] for r in rows})
            self.assertTrue(read(out/"result/run_receipt.json")["numerical"][0]["quantity_certified"])
            bad = out/"bad.tsv"
            bad.write_text((demo/"bulk.tsv").read_text().replace("B01\t", "NEW_GENE\t"), encoding="utf-8")
            mismatch = cli("deconvolve", "--reference", out/"audit", "--bulk", bad, "--out-dir", out/"mismatch")
            self.assertEqual(mismatch.returncode, 2, mismatch.stderr)
            self.assertIn("gene sets differ", mismatch.stderr)
            self.assertFalse((out/"mismatch").exists())

            original = schema.Bulk.load(demo/"bulk.tsv")
            batch = out/"batch.npz"
            np.savez_compressed(batch, genes=original.genes, ids=["other", "mixture_001"],
                                Y=np.column_stack([original.Y[:, 0] * 2, original.Y[:, 0]]))
            b = cli("deconvolve", "--reference", out/"audit", "--bulk", batch, "--out-dir", out/"batched")
            self.assertEqual(b.returncode, 0, b.stderr)
            self.assertEqual(rows, [v for v in table(out/"batched/presence_calls.tsv") if v["sample_id"] == "mixture_001"])

    @unittest.skipUnless(importlib.util.find_spec("anndata"), "Install the h5ad extra to exercise H5AD parity")
    def test_sparse_h5ad_matches_tsv(self):
        import anndata
        import pandas as pd
        from scipy import sparse

        demo = PACKAGE / "examples/tiny_pbmc_demo"
        genes, ids, x = schema.read_count_tsv(demo/"reference_counts.tsv")
        meta = {r["cell_id"]:r for r in table(demo/"cells.tsv")}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            matrix = sparse.csr_matrix(np.array(x).T)
            a = anndata.AnnData(X=matrix)
            # Use the portable string-index and categorical encoding of count H5AD files.
            a.var_names, a.obs_names = pd.Index(genes, dtype=object), pd.Index(ids, dtype=object)
            a.obs["donor_id"] = pd.Categorical([meta[i]["donor_id"] for i in ids], categories=pd.Index(sorted({meta[i]["donor_id"] for i in ids}), dtype=object))
            a.obs["cell_type"] = pd.Categorical([meta[i]["cell_type"] for i in ids], categories=pd.Index(sorted({meta[i]["cell_type"] for i in ids}), dtype=object))
            a.layers["counts"] = matrix.copy()
            ref = out/"reference.h5ad"
            a.write_h5ad(ref)
            c = cli("audit", "--reference", ref, "--out-dir", out/"h5ad-audit")
            self.assertEqual(c.returncode, 0, c.stderr)
            t = cli("audit", "--reference", demo/"reference_counts.tsv", "--metadata", demo/"cells.tsv",
                    "--out-dir", out/"tsv-audit")
            self.assertEqual(t.returncode, 0, t.stderr)
            lhs = schema.Reference.load(out/"h5ad-audit/reference.npz")
            rhs = schema.Reference.load(out/"tsv-audit/reference.npz")
            for key in schema.REFERENCE_KEYS:
                np.testing.assert_array_equal(getattr(lhs, key), getattr(rhs, key))

    def test_installed_frozen_core_matches_archive(self):
        core = Path(schema.__file__).with_name("_frozen_core.py")
        api = core.with_name("_frozen_api.py")
        self.assertEqual(schema.digest(core), "47eaaa4fd87ed5513575cce025592824dcd1f5f8bbfb5f61c83389a3ea9a535d")
        self.assertEqual(schema.digest(api), "6820371a468a22d5ab5f022da169ece5775bda71f317df24a0b0809afbd13928")


class HistoricalParityTests(unittest.TestCase):
    def test_five_mixtures(self):
        root = WORKSPACE / "outputs"
        frozen = root / "axisprec_loto_selective_20261125/person433_frozen_validation"
        sealed = root / "axisprec_sealed_test_20261124"
        if not (frozen/"PREDICTION_LOCK.json").is_file() or not (sealed/"PREDICTION_INPUTS.json").is_file():
            self.skipTest("Historical input-only archives are available in the original workspace")
        lock = read(frozen/"PREDICTION_LOCK.json")
        seal = read(sealed/"SEALED_SET_LOCK.json")
        self.assertEqual(schema.digest(frozen/"PREDICTIONS.tsv"), lock["files"]["PREDICTIONS.tsv"])
        self.assertEqual(schema.digest(sealed/"PREDICTION_INPUTS.json"), seal["outputs"]["PREDICTION_INPUTS.json"])
        manifest = {v["context"]:v for v in read(sealed/"PREDICTION_INPUTS.json")["contexts"] if v["lane"]=="person433"}
        expected = {}
        for row in table(frozen/"PREDICTIONS.tsv"):
            if row["sample_id"] in SAMPLES:
                expected.setdefault(row["sample_id"], {})[row["label"]] = row
        self.assertEqual(set(expected), set(SAMPLES))
        contexts = {r["context"]:r for r in lock["contexts"]}
        diffs, compared, calls = [], 0, set()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            for sid, study in SAMPLES.items():
                with self.subTest(study=study, sample=sid):
                    gold = expected[sid]
                    ctx = next(iter(gold.values()))["context"]
                    assets = manifest[ctx]["prediction_inputs"]
                    ref = root/f"cellmem_full_all_splits_20261116/input_audit/references/old/{study}__person433__{ctx}.npz"
                    b = Path(assets["test/bulk.tsv"]["path"])
                    self.assertEqual(schema.digest(ref), contexts[ctx]["reference_sha256"])
                    self.assertEqual(schema.digest(b), contexts[ctx]["bulk_sha256"])
                    bulk = schema.Bulk.load(b)
                    i = bulk.ids.tolist().index(sid)
                    single = out/f"{sid}.npz"
                    np.savez_compressed(single, genes=bulk.genes, ids=bulk.ids[i:i+1], Y=bulk.Y[:, i:i+1])
                    one = out/sid
                    result = cli("deconvolve", "--reference", ref, "--bulk", single, "--out-dir", one)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    p = {r["cell_type"]:r for r in table(one/"proportions.tsv")}
                    q = {r["cell_type"]:r for r in table(one/"presence_calls.tsv")}
                    self.assertEqual(set(p), set(q))
                    self.assertEqual(set(q), set(gold))
                    for label, row in gold.items():
                        x, fitted = p[label], q[label]
                        delta = abs(float(x["rna_fraction"])-float(row["quantity"]))
                        diffs.append(delta)
                        self.assertLessEqual(delta, 1e-12, label)
                        self.assertEqual(fitted["call"], row["frozen_dual_mechanism"], label)
                        calls.add(fitted["call"])
                        compared += 1
                        self.assertEqual(fitted["reference_donors"], row["reference_donors"])
                        self.assertEqual(fitted["identity_genes"], row["marker_count"])
                        for field, legacy in (("loto_gain", "held_gain"), ("gene_consistency", "gene_consistency")):
                            if row[legacy]:
                                self.assertAlmostEqual(float(fitted[field]),float(row[legacy]),delta=1e-8)
                            else:
                                self.assertEqual(fitted[field], "")
        self.assertEqual(calls, {"PRESENT", "ABSENT", "ABSTAIN"})
        print(f"Frozen parity: {len(SAMPLES)} mixtures, {compared} candidate decisions, maximum RNA-fraction difference {max(diffs):.3g}")


if __name__ == "__main__":
    unittest.main()
