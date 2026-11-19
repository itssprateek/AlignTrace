"""Offline starter commands. No external requests or automatic support decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
from .records import Finding, SourceSpan
from .store import save_finding


def demo(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / "artificial_demo_source.txt"
    fixture.write_text("Requirement: return the number 3.\nAssertion: assert result == 3\n", encoding="utf-8")
    raw = fixture.read_bytes()
    span = SourceSpan(fixture.name, "artificial-demo-v1", hashlib.sha256(raw).hexdigest(),
                      2, 2, "Assertion: assert result == 3")
    finding = Finding(
        case_id="artificial-demo-001", condition_id="artificial-condition-001",
        collection_version="artificial-demo-v1", completeness="uncertain",
        evidence_route="unknown", conflict="uncertain", origin="artificial_demo",
        search_complete=False, evidence=[span],
        reason="Supplied demonstration of an assertion source reference; no automatic comparison was performed.",
        uncertainty_reason="Setup, action and the complete eligible collection have not been assessed.",
    )
    save_finding(output.parent / "data/processed/demo.sqlite", finding, output)
    payload = {"notice": "ARTIFICIAL DEMO ONLY — not a dataset case or research result", "finding": finding.to_dict()}
    (output / "demo.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (output / "demo.md").write_text(
        "# Artificial demonstration\n\nNot a dataset case or research result. No model was called.\n\n"
        "Completeness: uncertain\n\n" + finding.reason + "\n\n" + finding.uncertainty_reason + "\n",
        encoding="utf-8")
    print(json.dumps({"status": "demo_completed", "report": str((output / "demo.md").resolve()),
                      "research_results": False}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Inspect the starter runtime")
    command = sub.add_parser("demo", help="Run the artificial offline evidence demonstration")
    command.add_argument("--output", type=Path, default=Path("reports"))
    command = sub.add_parser("ingest", help="Verify and join the downloaded pinned python-docx dataset")
    command.add_argument("--raw-root", type=Path, default=Path("data/raw/req2test-bench"))
    command.add_argument("--output", type=Path, default=Path("data/processed/python-docx-v1"))
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps({"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                          "dataset_verified": None,
                          "dataset_status": "Run ingest for checksum verification and saved counts",
                          "llm_configured": False}, indent=2))
    elif args.command == "ingest":
        from .ingest import ingest
        try:
            print(json.dumps(ingest(args.raw_root, args.output), indent=2))
        except (ValueError, OSError, KeyError) as error:
            parser.exit(1, "Ingestion failed: " + str(error) + "\n")
    else:
        demo(args.output)


if __name__ == "__main__":
    main()
