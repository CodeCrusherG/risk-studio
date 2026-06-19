"""Real evidence reconciliation and corruption checks for the public case study."""
from pathlib import Path
from types import SimpleNamespace
import json
import shutil

from fastapi import FastAPI
from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

from marvis.credit_case_api import router, verified_artifact
from marvis.credit_case_study import (
    FEATURES, PARTITIONS, REFERENCE_MODEL, TARGET, load_source, metrics, partition_rows,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "credit-default"


@pytest.fixture(scope="module")
def observed():
    return load_source(ROOT / "data/public/uci_credit_default", offline=True)[0]


def test_pinned_observed_source_contract(observed):
    assert len(observed) == 30_000
    assert observed[TARGET].sum() == 6636
    assert observed.ID.is_unique
    assert not observed.isna().any().any()
    assert not set(["ID", "SEX", "EDUCATION", "MARRIAGE", "AGE", TARGET]) & set(FEATURES)


def test_corrupt_source_fails_closed(tmp_path):
    (tmp_path / "source.zip").write_bytes(b"unexpected replacement data")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_source(tmp_path, offline=True)


def test_offline_missing_source_does_not_fabricate(tmp_path):
    with pytest.raises(FileNotFoundError, match="No cached UCI"):
        load_source(tmp_path, offline=True)


def test_grouped_splits_are_disjoint_and_deterministic(observed):
    partitions, groups = partition_rows(observed)
    again, _ = partition_rows(observed)
    np.testing.assert_array_equal(partitions, again)
    assert set(partitions) == set(PARTITIONS)
    grouped = pd.DataFrame({"group": groups, "partition": partitions}).groupby("group").partition.nunique()
    assert grouped.max() == 1
    assert len(np.unique(groups)) == 29183
    assert all((partitions == name).sum() >= 5900 for name in PARTITIONS)


def test_platform_metrics_reconcile_with_independent_tie_aware_statistics():
    labels = np.array([0, 1, 1, 0, 1, 0, 0, 1])
    scores = np.array([.1, .1, .4, .4, .7, .7, .7, .9])
    actual = metrics(labels, scores)
    assert actual["auc"] == pytest.approx(roc_auc_score(labels, scores))
    assert actual["ks"] == pytest.approx(ks_2samp(scores[labels == 1], scores[labels == 0]).statistic)
    assert actual["brier"] == pytest.approx(np.mean((labels - scores)**2))
    assert sum(b["count"] for b in actual["reliability"]) == len(labels)
    assert all(0 <= b["wilson_95_low"] <= b["observed_default_rate"] <= b["wilson_95_high"] <= 1 for b in actual["reliability"])


def test_persisted_predictions_reconcile_to_observed_source_and_report(observed):
    report = json.loads((EVIDENCE / "report.json").read_text())
    predicted = pd.read_csv(EVIDENCE / "predictions.csv")
    joined = predicted.merge(observed[["ID", TARGET]], left_on="source_id", right_on="ID", validate="one_to_one")
    assert len(joined) == 30_000
    assert (joined.observed_default == joined[TARGET]).all()
    assert joined.groupby("predictor_group").partition.nunique().max() == 1
    for name, model in report["models"].items():
        for partition in PARTITIONS:
            rows = joined[joined.partition == partition]
            y = rows.observed_default.to_numpy()
            p = rows[name].to_numpy()
            assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
            assert model[partition]["auc"] == pytest.approx(roc_auc_score(y, p), abs=1e-12)
            assert model[partition]["brier"] == pytest.approx(np.mean((y - p)**2), abs=1e-12)
            assert model[partition]["defaults"] == y.sum()
    assert report["protocol"]["oot_available"] is False
    assert report["governance"]["approved_for_production"] is False
    assert report["reference_model"] == REFERENCE_MODEL


def test_artifact_manifest_checks_every_public_download():
    manifest = json.loads((EVIDENCE / "artifact_manifest.json").read_text())
    for name in manifest["artifacts"]:
        assert verified_artifact(EVIDENCE, name).is_file()


def test_api_serves_actual_evidence_and_rejects_corruption(tmp_path):
    copied = tmp_path / "case-studies/credit-default"
    shutil.copytree(EVIDENCE, copied)
    app = FastAPI()
    app.state.settings = SimpleNamespace(workspace=tmp_path)
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/api/risk-studio/credit-case-study")
        assert response.status_code == 200
        assert response.json()["data_quality"]["rows"] == 30_000
        downloaded = client.get("/api/risk-studio/credit-case-study/artifacts/predictions.csv")
        assert downloaded.status_code == 200
        assert b"source_id,partition,predictor_group,observed_default" in downloaded.content
        assert client.get("/api/risk-studio/credit-case-study/artifacts/private.key").status_code == 404
        (copied / "report.json").write_text('{"tampered":true}')
        assert client.get("/api/risk-studio/credit-case-study").status_code == 409


def test_symlink_artifact_cannot_escape_evidence_directory(tmp_path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "private.txt").write_text("not a public artifact")
    (tmp_path / "evidence/report.json").symlink_to(tmp_path / "private.txt")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        verified_artifact(tmp_path / "evidence", "report.json")
    assert exc.value.status_code == 404
