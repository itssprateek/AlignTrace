"""Persist already validated records; this is not a decision engine."""
from pathlib import Path
import json
import sqlite3
from .records import Finding


def save_finding(database: Path, finding: Finding, source_root: Path) -> None:
    finding.validate(source_root)
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(database)) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS findings (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO findings VALUES (?, ?) ON CONFLICT(case_id) DO UPDATE SET payload=excluded.payload",
            (finding.case_id, json.dumps(finding.to_dict(), sort_keys=True)),
        )
