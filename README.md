# Requirement test alignment research

Prateek Kumar Verma — MSc Big Data and AI, SRH University Berlin.

Build and evaluate a framework that assesses individual requirement conditions against a fixed collection of test evidence. Scope: general software systems, initially English Gherkin and Python Behave sources. The central experiment measures how one-hop helper evidence affects missing-support warnings.

## Current implementation

This starter provides validated evidence records, source-span and SHA-256 verification, SQLite persistence, and an offline command-line demonstration. It does not yet parse Gherkin, resolve Behave steps, retrieve tests, call an LLM, assess support automatically or perform thesis evaluation. The demo uses an explicitly artificial fixture; its findings are supplied examples, not model predictions or research results.

## Run locally

Python 3.9 or newer. No third-party packages or API keys are needed for the starter.

```bash
cd /Users/prateek/Documents/Codex/2026-11-15/new-chat-3/thesis-alignment
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

## Project layout

`src/alignment` holds the initial code; `tests` protects evidence and decision invariants; `manifests` records provenance; `data/raw` is for unchanged sources; `data/annotations` is for human labels; `configs`, `prompts` and `experiments` will hold versioned experiment settings; `reports/weekly` tracks actual progress; `thesis` holds chapters, figures and references.

Do not commit credentials, virtual environments or restricted source material. No remote repository or publishing has been configured.
