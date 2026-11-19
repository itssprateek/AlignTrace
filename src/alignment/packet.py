"""Static evidence packets. Literal matches are candidates, not runtime bindings."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile


def read_rows(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Processed file checksum mismatch: " + path.name)
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def scoped_nodes(function):
    """Inspect a function body without borrowing evidence from nested definitions."""
    pending = list(reversed(function.body))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def span(source, start, end):
    lines = source["content"].splitlines()
    return {"source_id": source["source_id"], "path": source["path"],
            "revision": source["revision"], "sha256": source["sha256"],
            "start_line": start, "end_line": end,
            "text": "\n".join(lines[start - 1:end])}


def function_evidence(source, function):
    start = min([function.lineno] + [d.lineno for d in function.decorator_list])
    return {"function": function.name,
            "source": span(source, start, function.end_lineno),
            "assertions": [span(source, n.lineno, n.end_lineno)
                           for n in scoped_nodes(function) if isinstance(n, ast.Assert)],
            "body_is_pass": len(function.body) == 1 and isinstance(function.body[0], ast.Pass)}


def parse_steps(text, block):
    steps, previous = [], None
    for offset, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*(Given|When|Then|And|But)\s+(.+?)\s*$", line)
        if not match:
            continue
        keyword, value = match.groups()
        kind = keyword.lower() if keyword in {"Given", "When", "Then"} else previous
        steps.append({"keyword": keyword, "kind": kind, "text": value,
                      "block": block, "block_line": offset})
        previous = kind
    return steps


def build_packet(record, sources):
    raw = record["source_record"]
    linked_ids = record["test_source_ids"]
    if len(linked_ids) != len(set(linked_ids)):
        raise ValueError("Duplicate linked source IDs")
    linked = []
    for identity in linked_ids:
        if identity not in sources:
            raise ValueError("Missing linked test source: " + identity)
        source = sources[identity]
        actual = hashlib.sha256(source["content"].encode("utf-8")).hexdigest()
        if actual != source["sha256"]:
            raise ValueError("Source content hash mismatch: " + source["path"])
        if source["revision"] != raw["base_commit"]:
            raise ValueError("Source revision mismatch")
        linked.append(source)

    # Parse only; upstream Python is never imported or executed.
    trees = {s["source_id"]: ast.parse(s["content"], filename=s["path"]) for s in linked}
    definitions = {}
    bindings = []
    for source in linked:
        tree = trees[source["source_id"]]
        functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        definitions[source["source_id"]] = functions
        decorator_names = {"given": "given", "when": "when", "then": "then", "step": "step"}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "behave":
                for name in node.names:
                    if name.name in decorator_names:
                        decorator_names[name.asname or name.name] = name.name
        for function in functions.values():
            for decorator in function.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name):
                    continue
                kind = decorator_names.get(decorator.func.id)
                if kind and decorator.args and isinstance(decorator.args[0], ast.Constant):
                    pattern = decorator.args[0].value
                    if isinstance(pattern, str):
                        bindings.append((kind, pattern, source, function))

    warnings = ["Matches are static literal candidates within linked files; global Behave registration and matcher configuration are not verified."]
    if raw["scenario"]["kind"] != "scenario":
        warnings.append("Scenario Outline examples are not expanded by this command.")
    steps = parse_steps(raw["feature"].get("background") or "", "background")
    steps += parse_steps(raw["scenario"]["gherkin"], "scenario")
    packets = []
    for step in steps:
        candidates = [(source, function) for kind, pattern, source, function in bindings
                      if kind in {step["kind"], "step"} and pattern == step["text"]
                      and "<" not in step["text"]]
        entry = dict(step, match_status="unresolved", candidates=[])
        if len(candidates) == 1:
            entry["match_status"] = "literal_candidate"
        elif len(candidates) > 1:
            entry["match_status"] = "ambiguous"
        for source, function in candidates:
            evidence = function_evidence(source, function)
            helpers, unresolved = [], []
            tree = trees[source["source_id"]]
            imports = {}
            for node in tree.body:
                if isinstance(node, ast.ImportFrom) and node.module:
                    for name in node.names:
                        imports[name.asname or name.name] = (node.module, name.name)
            for call in (n for n in scoped_nodes(function) if isinstance(n, ast.Call)):
                if not isinstance(call.func, ast.Name):
                    unresolved.append({"expression": ast.get_source_segment(source["content"], call),
                                       "line": call.lineno, "reason": "attribute or dynamic call not resolved"})
                    continue
                name = call.func.id
                matches = []
                if name in definitions[source["source_id"]]:
                    matches = [(source, definitions[source["source_id"]][name])]
                elif name in imports:
                    module, original = imports[name]
                    suffix = module.replace(".", "/") + ".py"
                    matches = [(s, definitions[s["source_id"]][original]) for s in linked
                               if (s["path"] == suffix or s["path"].endswith("/" + suffix))
                               and original in definitions[s["source_id"]]]
                if len(matches) == 1:
                    helper_source, helper = matches[0]
                    item = function_evidence(helper_source, helper)
                    item.update({"depth": 1, "call_line": call.lineno,
                                 "resolution": "static_candidate", "deeper_calls_not_expanded": True})
                    if item not in helpers:
                        helpers.append(item)
                else:
                    unresolved.append({"expression": name, "line": call.lineno,
                                       "reason": "builtin, external, ambiguous or unavailable call"})
            evidence["helper_candidates"] = helpers
            evidence["unresolved_calls"] = unresolved
            if evidence["body_is_pass"]:
                warnings.append("Step body is pass; it does not explicitly check: " + step["text"])
            entry["candidates"].append(evidence)
        packets.append(entry)
    return {"schema": "aligntrace.evidence-packet/1", "instance_id": record["instance_id"],
            "dataset_revision": record["dataset_revision"], "upstream_commit": raw["base_commit"],
            "feature": raw["feature"], "scenario": raw["scenario"],
            "requirement_source": {"path": raw["feature"]["file_path"],
                                   "scenario_header_line": raw["scenario"]["line"],
                                   "revision": raw["feature_commit"],
                                   "text_origin": "verified benchmark record; upstream feature bytes not rechecked"},
            "linked_source_ids": linked_ids, "steps": packets, "warnings": warnings,
            "collection_review_complete": False, "test_execution_performed": False,
            "human_review": {"status": "not_labelled", "conditions": [], "completeness": None,
                             "evidence_route": None, "conflict": None, "reviewer": None, "notes": ""}}


def render_markdown(packet):
    lines = ["# Scenario evidence packet", "", packet["instance_id"], "",
             "Static source inspection only. Human labels are blank. No upstream tests were executed.",
             "", "## Feature context", "", packet["feature"].get("title", ""), "",
             packet["feature"].get("narrative") or "No feature narrative supplied.", "",
             "## Requirement", "", "```gherkin", packet["scenario"]["gherkin"], "```", ""]
    if packet["feature"].get("background"):
        lines += ["### Background", "", "```gherkin", packet["feature"]["background"], "```", ""]
    for step in packet["steps"]:
        lines += ["## " + step["keyword"] + " " + step["text"], "", "Match: " + step["match_status"], ""]
        for candidate in step["candidates"]:
            source = candidate["source"]
            lines += ["Function: " + candidate["function"], "",
                      "Source: {} lines {} to {}".format(source["path"], source["start_line"], source["end_line"]),
                      "", "```python", source["text"], "```", "",
                      "Direct assert statements: " + str(len(candidate["assertions"])),
                      "Helper candidates: " + str(len(candidate["helper_candidates"])), ""]
            for helper in candidate["helper_candidates"]:
                source = helper["source"]
                lines += ["### Helper candidate " + helper["function"], "",
                          "Source: {} lines {} to {}".format(source["path"], source["start_line"], source["end_line"]),
                          "", "```python", source["text"], "```", ""]
            if candidate["unresolved_calls"]:
                lines += ["Calls without a resolved helper candidate:", ""]
                lines += ["- Line {}: {} ({})".format(c["line"], c["expression"], c["reason"])
                          for c in candidate["unresolved_calls"]]
                lines.append("")
    lines += ["## Review limits", ""] + ["- " + w for w in packet["warnings"]]
    lines += ["", "Full eligible-collection review: incomplete.", "",
              "Completeness, evidence route and conflict: not labelled.", ""]
    return "\n".join(lines)


def create_packet(data_dir, instance_id, output):
    if output.exists():
        raise ValueError("Output exists; choose a new --output directory")
    summary = json.loads((data_dir / "summary.json").read_text(encoding="utf-8"))
    rows = read_rows(data_dir / "scenarios.jsonl", summary["outputs_sha256"]["scenarios.jsonl"])
    source_rows = read_rows(data_dir / "test_sources.jsonl", summary["outputs_sha256"]["test_sources.jsonl"])
    matches = [row for row in rows if row["instance_id"] == instance_id]
    if len(matches) != 1:
        raise ValueError("Expected exactly one scenario with requested ID")
    sources = {s["source_id"]: s for s in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("Duplicate source IDs")
    packet = build_packet(matches[0], sources)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".packet-", dir=str(output.parent)))
    try:
        (staging / "packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (staging / "packet.md").write_text(render_markdown(packet), encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    candidates = [c for step in packet["steps"] for c in step["candidates"]]
    return {"status": "packet_created", "instance_id": instance_id,
            "steps": len(packet["steps"]),
            "literal_candidate_steps": sum(s["match_status"] == "literal_candidate" for s in packet["steps"]),
            "direct_assertions": sum(len(c["assertions"]) for c in candidates),
            "helper_candidates": sum(len(c["helper_candidates"]) for c in candidates),
            "human_review_status": "not_labelled", "output": str(output.resolve())}
