"""Prepare neutral human-review materials from verified ingestion, without labels."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import tempfile
import argparse

INSTANCE = "python-docx/features/api-open-document.feature:13"
CONDITION = "Calling docx.Document() without arguments returns a Document object."


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_verified(data, summary, name):
    raw = (data / name).read_bytes()
    if sha(raw) != summary["outputs_sha256"][name]:
        raise ValueError("Processed input hash mismatch: " + name)
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def prepare(data, output):
    if output.exists():
        raise ValueError("Output exists; choose a new --output to preserve previous annotations")
    summary = json.loads((data / "summary.json").read_text(encoding="utf-8"))
    rows = load_verified(data, summary, "scenarios.jsonl")
    sources = load_verified(data, summary, "test_sources.jsonl")
    selected = [r for r in rows if r["instance_id"] == INSTANCE]
    if len(selected) != 1:
        raise ValueError("Expected exactly one target scenario")
    record = selected[0]
    raw = record["source_record"]
    paths = set()
    for source in sources:
        path = PurePosixPath(source["path"])
        if path.is_absolute() or ".." in path.parts or "\\" in source["path"] or not path.parts:
            raise ValueError("Unsafe source path")
        if source["path"] in paths:
            raise ValueError("Duplicate source path")
        paths.add(source["path"])
        if source["revision"] != raw["base_commit"]:
            raise ValueError("Unexpected source revision")
        if sha(source["content"].encode("utf-8")) != source["sha256"]:
            raise ValueError("Source content hash mismatch")
    identity = {"dataset_revision": record["dataset_revision"],
                "upstream_commit": raw["base_commit"],
                "scenarios_sha256": summary["outputs_sha256"]["scenarios.jsonl"],
                "test_sources_sha256": summary["outputs_sha256"]["test_sources.jsonl"],
                "source_files": [{k: s[k] for k in ("source_id", "path", "revision", "sha256")} for s in sources]}
    collection_id = sha(json.dumps(identity, sort_keys=True).encode("utf-8"))
    sheet = {
        "schema": "aligntrace.human-review/1", "case_id": INSTANCE + "#condition-1",
        "instance_id": INSTANCE, "case_origin": "natural_unchanged",
        "condition": {"text": CONDITION, "status": "researcher_proposed_not_confirmed",
                      "reviewer_agrees_with_condition": None,
                      "condition_revision_reason": None,
                      "precondition_text": "I have python-docx installed",
                      "action_text": "I call docx.Document() with no arguments",
                      "outcome_text": "document is a Document object",
                      "numerical_constraints": [],
                      "source": {"path": raw["feature"]["file_path"],
                                 "scenario_header_line": raw["scenario"]["line"],
                                 "feature_commit": raw["feature_commit"]}},
        "collection_id": collection_id,
        "annotation": {"annotator_id": None, "status": "not_started", "started_at": None,
                       "completed_at": None, "minutes_spent": None,
                       "precondition_assessment": None, "action_assessment": None,
                       "outcome_assessment": None, "completeness": None,
                       "evidence_route": None, "conflict": None,
                       "supporting_evidence": [], "conflicting_evidence": [],
                       "files_reviewed": [], "search_method": None,
                       "collection_review_complete": False, "unresolved_dependencies": [],
                       "rationale": None, "uncertainty_reason": None},
        "independence": {"other_annotator_labels_seen": False, "framework_findings_seen": False,
                         "prior_assistant_assessment_seen": False,
                         "disclosure": None},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".review-", dir=str(output.parent)))
    try:
        shared = staging / "shared"
        shared.mkdir()
        (shared / "collection_manifest.json").write_text(json.dumps(dict(identity, collection_id=collection_id), indent=2) + "\n")
        (shared / "requirement.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for source in sources:
            target = shared / "sources" / source["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source["content"].encode("utf-8"))
        for role in ("researcher", "reviewer"):
            folder = staging / role
            folder.mkdir()
            (folder / "review.json").write_text(json.dumps(sheet, indent=2) + "\n")
        (staging / "START_HERE.md").write_text(
            "# First human review\n\n"
            "The condition is researcher-proposed and must be checked against shared/requirement.json. "
            "Both initial label sheets are blank. No alignment finding or candidate assertion is prefilled.\n\n"
            "Researcher: complete researcher/review.json. Reviewer: receive only a separate copy of "
            "shared/, reviewer/review.json and docs/first_human_review.md. Do not send the researcher labels, "
            "generated evidence packet, framework warnings or earlier assistant assessment. Confirm reviewer availability first.\n\n"
            "All ingested test sources are under shared/sources/. Inspect setup, action, assertions and applicable helpers. "
            "Record exact paths, revisions, lines and source hashes from collection_manifest.json. "
            "Missing files or deeper unresolved dependencies must remain visible.\n\n"
            "The researcher has already seen an assistant interpretation and a static packet in this workflow. "
            "Record that exposure honestly in independence; it cannot be undone. An unexposed reviewer can still "
            "label independently. This first pilot exercise is not a blinded benchmark result.\n\n"
            "These files contain upstream source content. Review licence notices before redistributing. "
            "Do not commit the source bundle or completed personal review sheets to the public repository.\n",
            encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"status": "review_materials_prepared", "case_id": sheet["case_id"],
            "source_files": len(sources), "collection_id": collection_id,
            "support_labels_assigned": False, "output": str(output.resolve())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed/python-docx-v1"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/reviews/api-open-document-13"))
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.data_dir, args.output), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, "Review preparation failed: " + str(error) + "\n")
