"""Read-only access to locally reproduced public case-study evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/risk-studio/credit-case-study", tags=["risk-studio"])
ARTIFACT_NAMES = frozenset({"report.json", "report.md", "source_manifest.json", "predictions.csv",
                            "observed_clients.csv", "feature_dictionary.csv", "validation.png"})


def evidence_directory(request: Request) -> Path:
    workspace = request.app.state.settings.workspace
    local = workspace / "case-studies" / "credit-default"
    bundled = Path(__file__).resolve().parents[1] / "evidence" / "credit-default"
    path = local if local.exists() else bundled
    if not (path / "artifact_manifest.json").is_file():
        raise HTTPException(404, "Public case study has not been built. Run scripts/run_public_credit_case_study.py.")
    return path


def verified_artifact(directory: Path, name: str) -> Path:
    if name not in ARTIFACT_NAMES:
        raise HTTPException(404, "Unknown case-study artifact")
    path = directory / name
    if not path.is_file() or path.resolve().parent != directory.resolve():
        raise HTTPException(404, "Case-study artifact is unavailable")
    try:
        manifest = json.loads((directory / "artifact_manifest.json").read_text())
        expected = manifest["artifacts"][name]["sha256"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "Case-study manifest is invalid; reproduce the case study.") from exc
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise HTTPException(409, "Case-study artifact checksum failed; reproduce the case study.")
    return path


@router.get("")
def credit_case_study(request: Request) -> dict:
    directory = evidence_directory(request)
    path = verified_artifact(directory, "report.json")
    report = json.loads(path.read_text())
    report["artifact_urls"] = {name: f"/api/risk-studio/credit-case-study/artifacts/{name}" for name in sorted(ARTIFACT_NAMES)}
    report["integrity"] = "Report checksum verified against local artifact manifest; not a digital signature or independent sign-off."
    return report


@router.get("/artifacts/{name}")
def credit_case_artifact(request: Request, name: str) -> FileResponse:
    path = verified_artifact(evidence_directory(request), name)
    return FileResponse(path, filename=name, content_disposition_type="inline" if name == "validation.png" else "attachment")
