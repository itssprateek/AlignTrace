# Offline dataset ingestion

From the project root, activate your virtual environment and install the optional dependency:

```bash
python -m pip install -e '.[ingest]'
python -m alignment ingest
```

No download, authentication or test execution occurs. The command reads the previously downloaded dataset-v1.1 release under `data/raw/req2test-bench`. Both compressed files, the uncompressed main JSONL and the python-docx sidecar are checked against pinned SHA-256 values. Scenario IDs, upstream commits, sidecar joins, paths and shared-file consistency are validated.

Outputs under `data/processed/python-docx-v1`:

- `scenarios.jsonl`: original dataset records, source IDs and unlabelled annotation status.
- `test_sources.jsonl`: deduplicated test files, exact content, paths, revisions and hashes.
- `summary.json`: verification results, counts and generated-file hashes.

Existing output directories are refused. Preserve prior runs and use `--output data/processed/python-docx-v2` for a new run. Failed validation produces no final output directory.

Ingestion does not map individual Gherkin steps, determine assertion sufficiency, establish independent reference labels, execute upstream code or verify licence notices. Those tasks remain separate. The benchmark's `in_eval_split` is not the thesis development/evaluation partition.
