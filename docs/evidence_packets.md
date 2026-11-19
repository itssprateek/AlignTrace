# Static scenario evidence packets

After ingestion, run from the project root:

```bash
python -m alignment packet
```

The default case is `python-docx/features/api-open-document.feature:13`. Outputs are `packet.json` and `packet.md` under `data/processed/evidence/api-open-document-13`. Read the Markdown in VS Code. Human review fields remain blank; conditions must be annotated separately.

The command verifies generated input hashes against the ingestion summary, verifies linked source hashes and revisions, parses Python without executing it, and identifies literal step candidates inside linked source files. It records decorated function spans, direct Python assert statements, pass-only bodies, one-hop helper candidates and unresolved calls. Assertions inside nested definitions or unrelated neighbouring functions are excluded.

This is a deliberately limited static matcher, not a complete Behave resolver. Parameterised and regular-expression patterns, example interpolation, dynamic bindings, attribute calls and global registration are not resolved. An exact match is a candidate, not confirmation of runtime binding. Helpers may contain conditional assertions; source presence does not prove execution, reachability, sufficient validation or correct argument flow. Unknown calls remain visible. No completeness, route or conflict label is inferred.

Existing output directories are refused. For another case use `--instance-id '...' --output data/processed/evidence/another-case`. Keep generated packets out of Git until upstream licence notices have been reviewed. Never feed framework decisions to an independent annotator as reference labels.
