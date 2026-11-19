"""Offline ingestion of the pinned dataset release, without executing test sources."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile


REVISION = "0dfb049d5c9bfd0d8c98d23c22af7d02ee6865a3"
UPSTREAM = "e45454602b53e8e572b179ccf1c91093ec9f4ed7"
# Published release checksums inspected in the dataset-v1.1 SHA256SUMS file.
EXPECTED = {
    "full.jsonl.zst": "6d94eba1dceed95b2e62fa3df41643c59a80b54c56d8452e01cba417e8df6b80",
    "full.jsonl": "070cd399a565eb40434190e55f8a31854186db26a5bbcad20e2156db606def43",
    "gt_tests.tar.zst": "9db81fbc1bac5404ac4c2c2c623d24024cf8d9f6b4cd139e766e377ffc575ff3",
    "gt_tests/python-docx.jsonl": "2092016283e9a9ea0c100e3556024368d484b26ae72aa00a20c21cdfe4b030a2",
}


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_release(release):
    declared = {}
    for line in (release / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            name = name.lstrip("*")
            if name in declared:
                raise ValueError("Duplicate checksum entry: " + name)
            declared[name] = digest
    for name, expected in EXPECTED.items():
        if declared.get(name) != expected:
            raise ValueError("Release checksum declaration differs from pinned value: " + name)
    for name in ("full.jsonl.zst", "gt_tests.tar.zst"):
        if digest_file(release / name) != EXPECTED[name]:
            raise ValueError("Checksum mismatch: " + name)


def read_main(release, zstd):
    selected, seen = {}, set()
    digest = hashlib.sha256()
    with (release / "full.jsonl.zst").open("rb") as source:
        with zstd.ZstdDecompressor().stream_reader(source) as stream:
            with io.BufferedReader(stream) as lines:
                for raw in lines:
                    digest.update(raw)
                    row = json.loads(raw)
                    identity = row["instance_id"]
                    if identity in seen:
                        raise ValueError("Duplicate scenario ID: " + identity)
                    seen.add(identity)
                    if row["project"] == "python-docx":
                        if row["base_commit"] != UPSTREAM or row["feature_commit"] != UPSTREAM:
                            raise ValueError("Unexpected python-docx source commit")
                        if row["repo_url"] != "https://github.com/python-openxml/python-docx":
                            raise ValueError("Unexpected upstream repository")
                        selected[identity] = row
    if digest.hexdigest() != EXPECTED["full.jsonl"]:
        raise ValueError("Uncompressed main records checksum mismatch")
    if not selected:
        raise ValueError("No python-docx scenarios found")
    return selected, len(seen)


def read_sidecar(release, zstd):
    target = "gt_tests/python-docx.jsonl"
    result = None
    with (release / "gt_tests.tar.zst").open("rb") as source:
        with zstd.ZstdDecompressor().stream_reader(source) as stream:
            with tarfile.open(fileobj=stream, mode="r|") as archive:
                for member in archive:
                    if member.name.removeprefix("./") != target:
                        continue
                    if result is not None:
                        raise ValueError("Duplicate python-docx sidecar member")
                    if not member.isfile() or member.size > 64 * 1024 * 1024:
                        raise ValueError("Invalid or oversized python-docx sidecar")
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise ValueError("Cannot read sidecar")
                    raw = handle.read()
                    if hashlib.sha256(raw).hexdigest() != EXPECTED[target]:
                        raise ValueError("Sidecar checksum mismatch")
                    result = {}
                    for line in raw.decode("utf-8").splitlines():
                        row = json.loads(line)
                        identity = row["instance_id"]
                        if identity in result:
                            raise ValueError("Duplicate sidecar ID: " + identity)
                        result[identity] = row
    if result is None:
        raise ValueError("python-docx sidecar not found")
    return result


def join_records(main, sidecar):
    if set(main) != set(sidecar):
        raise ValueError("Scenario and test sidecar IDs do not match")
    sources, records = {}, []
    for identity, row in sorted(main.items()):
        files = sidecar[identity]["files"]
        paths = [item["path"] for item in files]
        if paths != row["gt_test_files"] or len(paths) != len(set(paths)):
            raise ValueError("Test paths do not match or are duplicated: " + identity)
        references = []
        for item in files:
            path, content = item["path"], item["content"]
            relative = PurePosixPath(path)
            if not path or relative.is_absolute() or ".." in relative.parts or "\\" in path:
                raise ValueError("Unsafe source path: " + path)
            if not isinstance(content, str):
                raise ValueError("Missing UTF-8 source content: " + path)
            key = (row["base_commit"], path)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if key in sources and sources[key]["content"] != content:
                raise ValueError("Conflicting content at same revision and path: " + path)
            sources[key] = {"source_id": row["base_commit"] + ":" + path,
                            "project": "python-docx", "revision": row["base_commit"],
                            "path": path, "sha256": digest, "content": content}
            references.append(sources[key]["source_id"])
        records.append({"instance_id": identity, "dataset_revision": REVISION,
                        "source_record": row, "test_source_ids": references,
                        "annotation_status": "not_labelled"})
    return records, [sources[key] for key in sorted(sources)]


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def ingest(raw_root, output):
    try:
        import zstandard as zstd
    except ImportError as error:
        raise ValueError("Install ingestion dependencies: python -m pip install -e '.[ingest]'") from error
    if output.exists():
        raise ValueError("Output already exists; preserve it and choose a new --output directory")
    release = raw_root / "releases/dataset-v1.1"
    verify_release(release)
    main, total = read_main(release, zstd)
    sidecar = read_sidecar(release, zstd)
    records, sources = join_records(main, sidecar)
    summary = {
        "status": "ingestion_completed", "dataset_revision": REVISION,
        "upstream_commit": UPSTREAM, "total_release_records": total,
        "python_docx_scenarios": len(records), "unique_scenario_ids": len(main),
        "benchmark_eval_scenarios": sum(row["in_eval_split"] for row in main.values()),
        "unique_test_source_files": len(sources), "verified_sha256": EXPECTED,
        "automatic_alignment_labels": False, "test_execution_performed": False,
        "licence_notices_reviewed": False,
        "note": "Benchmark eval membership is metadata, not the thesis held-out partition. Linked test files are candidates, not proof of assertion sufficiency.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ingest-", dir=str(output.parent)))
    try:
        write_jsonl(staging / "scenarios.jsonl", records)
        write_jsonl(staging / "test_sources.jsonl", sources)
        summary["outputs_sha256"] = {name: digest_file(staging / name)
                                    for name in ("scenarios.jsonl", "test_sources.jsonl")}
        (staging / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary
