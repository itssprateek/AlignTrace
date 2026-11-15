"""Source and finding contracts independent of any model provider."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List
import hashlib


@dataclass
class SourceSpan:
    path: str
    revision: str
    sha256: str
    start_line: int
    end_line: int
    text: str

    def verify(self, root: Path) -> None:
        root = root.resolve()
        relative = Path(self.path)
        path = (root / relative).resolve()
        if relative.is_absolute() or root not in path.parents:
            raise ValueError("Evidence path must stay within the source root")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("Source hash mismatch")
        lines = raw.decode("utf-8").splitlines()
        if not 1 <= self.start_line <= self.end_line <= len(lines):
            raise ValueError("Source span is out of bounds")
        if "\n".join(lines[self.start_line - 1:self.end_line]) != self.text:
            raise ValueError("Source span text mismatch")
        if not self.revision.strip():
            raise ValueError("Source revision is required")


@dataclass
class Finding:
    case_id: str
    condition_id: str
    collection_version: str
    completeness: str
    evidence_route: str
    conflict: str
    origin: str
    search_complete: bool
    reason: str
    uncertainty_reason: str = ""
    evidence: List[SourceSpan] = field(default_factory=list)

    def validate(self, root: Path) -> None:
        choices = {
            "completeness": {"sufficient", "partial", "no_support_found", "uncertain"},
            "evidence_route": {"direct", "indirect", "mixed", "not_applicable", "unknown"},
            "conflict": {"present", "absent", "uncertain"},
            "origin": {"natural", "constructed", "historical_replay", "historical_observation", "artificial_demo"},
        }
        for name, allowed in choices.items():
            if getattr(self, name) not in allowed:
                raise ValueError("Invalid " + name)
        for name in ("case_id", "condition_id", "collection_version", "reason"):
            if not getattr(self, name).strip():
                raise ValueError(name + " is required")
        if type(self.search_complete) is not bool:
            raise ValueError("search_complete must be a boolean")
        if self.completeness in {"partial", "no_support_found"} and not self.search_complete:
            raise ValueError("Absence claims require completed collection review")
        if self.completeness == "uncertain" and not self.uncertainty_reason.strip():
            raise ValueError("Uncertainty must have an explanation")
        if self.completeness in {"sufficient", "partial"}:
            if not self.evidence or self.evidence_route not in {"direct", "indirect", "mixed"}:
                raise ValueError("Supporting decisions require evidence and an evidence route")
        if self.completeness == "no_support_found" and self.evidence_route not in {"not_applicable", "unknown"}:
            raise ValueError("No-support decision cannot claim a supporting evidence route")
        if self.conflict == "present" and not self.evidence:
            raise ValueError("Conflict requires source evidence")
        for span in self.evidence:
            span.verify(root)

    def to_dict(self):
        return asdict(self)
