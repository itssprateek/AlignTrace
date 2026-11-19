# AlignTrace

Prateek Kumar Verma — MSc Big Data and AI, SRH University Berlin.

Build and evaluate a framework that assesses individual requirement conditions against a fixed collection of test evidence. Scope: general software systems, initially English Gherkin and Python Behave sources. The central experiment measures how one-hop helper evidence affects missing-support warnings.

## Current implementation

This starter provides validated evidence records, source-span and SHA-256 verification, SQLite persistence, and an offline command-line demonstration. It does not yet parse Gherkin, resolve Behave steps, retrieve tests, call an LLM, assess support automatically or perform thesis evaluation. The demo uses an explicitly artificial fixture; its findings are supplied examples, not model predictions or research results.

The `ingest` command now verifies the pinned dataset release, joins scenario records to reference test files and deduplicates shared source content. It preserves the original Gherkin text without yet parsing individual step bindings. See `docs/ingestion.md` for inputs and outputs.

After ingestion, `python -m alignment packet` creates the first static evidence packet with literal step candidates, exact function and assertion spans, one-hop helper candidates and blank human-review fields. See `docs/evidence_packets.md` for supported cases and limits. Static candidate matching does not establish runtime binding or support sufficiency.

## Run locally

Python 3.9 or newer. No third-party packages or API keys are needed for the starter.

```bash
git clone https://github.com/itssprateek/AlignTrace.git
cd AlignTrace
python3 -m venv .venv
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m alignment doctor
python -m alignment demo
python -m unittest discover -s tests -v
```

The demo writes `reports/demo.json`, `reports/demo.md` and `data/processed/demo.sqlite`. It validates exact source spans before storing the example. Repeated execution replaces the same demo record, rather than inventing additional cases. Outputs are clearly marked artificial. Real raw data is not downloaded by these commands.

## Research safeguards

- Completeness, evidence route and conflict are separate fields.
- A definitive no-support or partial-support record requires a completed collection review.
- Incomplete context remains uncertain. An assertion's presence is not proof of sufficient validation or successful execution.
- One explicit helper hop is the proposed analysis boundary; arbitrary dependency analysis is out of scope.
- Pilot cases remain outside held-out evaluation. Related variants and assertion logic must remain grouped.
- Researcher and one independent classmate reviewer label the pilot separately. Reviewer availability is not yet confirmed.
- Natural, constructed and historical cases require separate results. Drift remains conditional on verified earlier alignment and later mismatch.

## Next milestone

Verify pinned data and licences, recover the ten pilot case identifiers, then implement Gherkin ingestion against the actual source format. See `docs/pilot_checklist.md`, `docs/architecture.md`, `docs/decision_log.md` and `manifests/sources.json`. The recorded revisions are unverified planning inputs, not completed acquisitions.

Release ingestion was verified on 19 November 2026: 5,086 release records, 239 unique python-docx scenarios and 22 unique linked test files. This supersedes the initial acquisition status above; licence-notice review, step-to-assertion mapping and human annotation remain pending. Generated verification evidence is stored in each ingestion run's `summary.json`.

## Project layout

`src/alignment` holds the initial code; `tests` protects evidence and decision invariants; `manifests` records provenance; `data/raw` is for unchanged sources; `data/annotations` is for human labels; `configs`, `prompts` and `experiments` will hold versioned experiment settings; `reports/weekly` tracks actual progress; `thesis` holds chapters, figures and references.

Do not commit credentials, virtual environments or restricted source material. The project repository is https://github.com/itssprateek/AlignTrace.
