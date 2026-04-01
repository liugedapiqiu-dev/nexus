# SSOT NOTE: This registry is discovery/metadata only. It is not a system source of truth for execution state, runtime status, or final verification.
#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from runtime.adapters.openclaw_cli import list_skills, skill_info, normalize_skill_list_payload, normalize_skill_info_payload


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
_NAME_RE = re.compile(r"^name:\s*(.+)$", re.M)
_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M)


@dataclass
class SkillInfo:
    name: str
    description: str
    path: str
    source: str = "unknown"
    eligible: bool = True
    disabled: bool = False
    missing: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OpenClawSkillRegistry:
    def __init__(self) -> None:
        self.skills: Dict[str, SkillInfo] = {}
        self._loaded = False

    def _candidate_roots(self) -> List[Path]:
        home = Path.home()
        return [
            home / ".openclaw" / "workspace" / "skills",
            Path("/home/user/.openclaw/workspace/skills"),
            home / ".openclaw" / "skills",
            home / ".npm-global" / "lib" / "node_modules" / "openclaw" / "skills",
            home / ".npm-global" / "lib" / "node_modules" / "openclaw" / "extensions",
        ]

    def _infer_source(self, path: Path) -> str:
        p = str(path)
        if "/workspace/skills/" in p:
            return "workspace"
        if "/openclaw/skills/" in p and "/node_modules/" in p:
            return "bundled"
        if "/extensions/" in p:
            return "extension"
        return "local"

    def _parse_skill_file(self, skill_md: Path) -> Optional[SkillInfo]:
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        name = skill_md.parent.name
        description = ""

        m = _FRONTMATTER_RE.search(text)
        if m:
            fm = m.group(1)
            nm = _NAME_RE.search(fm)
            dm = _DESC_RE.search(fm)
            if nm:
                name = nm.group(1).strip().strip('"\'')
            if dm:
                description = dm.group(1).strip().strip('"\'')

        if not description:
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                description = line
                break

        return SkillInfo(
            name=name,
            description=description or f"Skill at {skill_md}",
            path=str(skill_md),
            source=self._infer_source(skill_md),
        )

    def _load_from_filesystem(self) -> Dict[str, SkillInfo]:
        skills: Dict[str, SkillInfo] = {}
        for root in self._candidate_roots():
            if not root.exists():
                continue
            candidates = root.glob("*/skills/*/SKILL.md") if root.name == "extensions" else root.glob("*/SKILL.md")
            for skill_md in candidates:
                try:
                    info = self._parse_skill_file(skill_md)
                    if info and info.name not in skills:
                        skills[info.name] = info
                except Exception:
                    continue
        return skills

    def _attach_cli_skill_metadata(self, skills: Dict[str, SkillInfo]) -> None:
        try:
            res = list_skills(eligible_only=False, timeout=60)
            payload = res.get("json")
            for entry in normalize_skill_list_payload(payload):
                name = entry.get("name")
                if not name:
                    continue
                existing = skills.get(name)
                if existing:
                    existing.eligible = bool(entry.get("eligible", True))
                    existing.disabled = bool(entry.get("disabled", False))
                    existing.missing = entry.get("missing") if isinstance(entry.get("missing"), dict) else None
                    if entry.get("source"):
                        existing.source = str(entry.get("source"))
                    continue

                # CLI knows a skill that our filesystem scan did not.
                info_res = skill_info(name, timeout=60)
                info = normalize_skill_info_payload(info_res.get("json"), fallback_name=name)
                path = str(info.get("path") or "")
                skills[name] = SkillInfo(
                    name=name,
                    description=str(entry.get("description") or info.get("description") or ""),
                    path=path,
                    source=str(entry.get("source") or "openclaw"),
                    eligible=bool(entry.get("eligible", True)),
                    disabled=bool(entry.get("disabled", False)),
                    missing=entry.get("missing") if isinstance(entry.get("missing"), dict) else None,
                )
        except Exception:
            return

    def load(self, *, force: bool = False) -> None:
        if self._loaded and not force:
            return
        self.skills = self._load_from_filesystem()
        self._attach_cli_skill_metadata(self.skills)
        self._loaded = True

    def list(self) -> List[SkillInfo]:
        self.load()
        return sorted(self.skills.values(), key=lambda x: x.name.lower())

    def get(self, name: str) -> Optional[SkillInfo]:
        self.load()
        if name in self.skills:
            return self.skills[name]
        for k, v in self.skills.items():
            if k.lower() == name.lower():
                return v
        return None

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (text or "").lower()).strip()

    def match_task(self, title: str, description: str = "") -> Optional[SkillInfo]:
        self.load()
        hay = self._norm(f"{title} {description}")
        if not hay:
            return None

        best = None
        best_score = -1.0
        hay_tokens = set(hay.split())

        for skill in self.list():
            name_norm = self._norm(skill.name)
            desc_norm = self._norm(skill.description)
            if not name_norm and not desc_norm:
                continue

            score = 0.0
            if name_norm and (f" {name_norm} " in f" {hay} " or hay == name_norm):
                score += 10.0

            name_tokens = [t for t in name_norm.split() if len(t) >= 2]
            desc_tokens = [t for t in desc_norm.split() if len(t) >= 3]

            score += sum(2.5 for t in name_tokens if t in hay_tokens)
            score += sum(1.0 for t in desc_tokens if t in hay_tokens)

            if skill.eligible:
                score += 0.5
            if skill.disabled:
                score -= 3.0
            if skill.missing:
                missing_count = sum(len(v) for v in skill.missing.values() if isinstance(v, list))
                score -= min(2.0, 0.25 * missing_count)

            if score > best_score and score >= 2.5:
                best = skill
                best_score = score

        return best

    def rank_task(self, title: str, description: str = "", *, limit: int = 5) -> List[Dict[str, Any]]:
        self.load()
        hay = self._norm(f"{title} {description}")
        hay_tokens = set(hay.split())
        ranked: List[Dict[str, Any]] = []

        for skill in self.list():
            name_norm = self._norm(skill.name)
            desc_norm = self._norm(skill.description)
            score = 0.0
            reasons: List[str] = []

            if name_norm and (f" {name_norm} " in f" {hay} " or hay == name_norm):
                score += 10.0
                reasons.append("exact_name_match")

            name_hits = [t for t in name_norm.split() if len(t) >= 2 and t in hay_tokens]
            desc_hits = [t for t in desc_norm.split() if len(t) >= 3 and t in hay_tokens]
            if name_hits:
                score += 2.5 * len(name_hits)
                reasons.append(f"name_tokens={','.join(sorted(set(name_hits)))}")
            if desc_hits:
                score += 1.0 * len(desc_hits)
                reasons.append(f"desc_tokens={','.join(sorted(set(desc_hits)))}")
            if skill.eligible:
                score += 0.5
            if skill.disabled:
                score -= 3.0
                reasons.append("disabled")

            ranked.append({"score": round(score, 3), "reasons": reasons, "skill": skill.to_dict()})

        ranked.sort(key=lambda x: (-x["score"], x["skill"]["name"].lower()))
        return ranked[:max(1, limit)]

    def to_json(self) -> Dict[str, Any]:
        self.load()
        return {
            "skills": len(self.skills),
            "skill_list": [s.to_dict() for s in self.list()],
        }


skill_registry = OpenClawSkillRegistry()
