"""Local, progressive engineering-skill retrieval for the NextAI student.

Skills teach what an engineering object is, what information to request, and
how to stage a native workflow. They never execute code or authorize tools.
The native capability registry and typed adapter remain the authority for
what the running FreeCAD build can actually do.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re

MAX_SKILLS = 500
MAX_SKILL_BYTES = 80_000
MAX_REFERENCE_BYTES = 80_000
MAX_SELECTED_SKILLS = 3
MAX_CONTEXT_CHARS = 22_000
_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}")
_STOP = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could",
    "do", "does", "for", "from", "has", "have", "how", "i", "if", "in",
    "into", "is", "it", "its", "me", "my", "need", "of", "on", "or",
    "our", "please", "that", "the", "this", "to", "use", "want", "we",
    "what", "when", "which", "with", "would", "you", "your",
})
_SYNONYMS = {
    "home": {"house", "residential", "bungalow", "duplex"},
    "house": {"home", "residential", "bungalow", "duplex"},
    "bedroom": {"bedrooms", "room", "residential", "floorplan"},
    "floorplan": {"floor", "plan", "architecture", "bedroom"},
    "gear": {"gears", "spur", "involute", "tooth", "teeth", "mechanical"},
    "teeth": {"tooth", "gear", "spur", "involute"},
    "wash": {"water", "tank", "tower"},
    "water": {"wash", "tank", "tower", "hydraulic"},
    "tower": {"water", "wash", "tank", "structure"},
    "car": {"vehicle", "automotive", "chassis"},
    "vehicle": {"car", "automotive", "chassis"},
    "panel": {"electrical", "cabinet", "switchgear", "control"},
    "wiring": {"electrical", "circuit", "cable", "panel"},
    "drainage": {"stormwater", "culvert", "road", "pipe"},
}


@dataclass(frozen=True)
class EngineeringSkill:
    name: str
    description: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    body: str
    directory: Path
    references: tuple[str, ...]


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"" + "'":
        return value[1:-1]
    return value


def _list_value(value: str) -> tuple[str, ...]:
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return tuple(
        part.strip().strip("\"'").strip()
        for part in raw.split(",")
        if part.strip().strip("\"'").strip()
    )


def _parse_skill(content: str) -> tuple[dict, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must begin with a frontmatter delimiter.")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ValueError("SKILL.md frontmatter is not closed.") from exc
    metadata = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = _scalar(value)
    body = "\n".join(lines[end + 1:]).strip()
    return metadata, body


def _tokens(text: str) -> set[str]:
    result = set()
    for token in _TOKEN.findall(str(text).lower()):
        if token in _STOP:
            continue
        result.add(token)
        result.update(_SYNONYMS.get(token, ()))
    return result


def _read_references(directory: Path) -> tuple[str, ...]:
    folder = directory / "references"
    if not folder.is_dir() or folder.is_symlink():
        return ()
    found = []
    try:
        for item in sorted(folder.iterdir(), key=lambda path: path.name.casefold()):
            if item.is_file() and not item.is_symlink() and item.suffix.lower() == ".md":
                resolved = item.resolve()
                if resolved.parent == folder.resolve() and resolved.stat().st_size <= MAX_REFERENCE_BYTES:
                    found.append("references/" + item.name)
    except OSError:
        return ()
    return tuple(found[:40])


class EngineeringSkillRegistry:
    """Load local Markdown skills and reveal only those relevant to a task.

    The format is intentionally small: frontmatter name/description/tags/aliases
    plus a Markdown body and optional Markdown references. No handler.py or
    script execution is supported.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else (
            Path(__file__).resolve().parents[1] / "knowledge_packs" / "skills"
        )
        self._skills = self._load()

    def _load(self) -> dict[str, EngineeringSkill]:
        skills = {}
        if not self.root.is_dir() or self.root.is_symlink():
            return skills
        root = self.root.resolve()
        try:
            directories = sorted(self.root.iterdir(), key=lambda path: path.name.casefold())
        except OSError:
            return skills
        for directory in directories[:MAX_SKILLS]:
            if not directory.is_dir() or directory.is_symlink():
                continue
            try:
                resolved = directory.resolve()
                skill_path = directory / "SKILL.md"
                if root not in resolved.parents or not skill_path.is_file() or skill_path.is_symlink():
                    continue
                if skill_path.stat().st_size > MAX_SKILL_BYTES:
                    continue
                raw = skill_path.read_text(encoding="utf-8")
                metadata, body = _parse_skill(raw)
                name = str(metadata.get("name", directory.name)).strip()
                description = str(metadata.get("description", "")).strip()
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", name) or not description or not body:
                    continue
                if name in skills:
                    continue
                tags = _list_value(str(metadata.get("tags", "")))
                aliases = _list_value(str(metadata.get("aliases", "")))
                skills[name] = EngineeringSkill(
                    name=name,
                    description=description[:1024],
                    tags=tags,
                    aliases=aliases,
                    body=body,
                    directory=resolved,
                    references=_read_references(resolved),
                )
            except (OSError, UnicodeError, ValueError):
                continue
        return skills

    def catalog(self) -> list[dict]:
        return [
            {"name": skill.name, "description": skill.description,
             "tags": list(skill.tags), "aliases": list(skill.aliases)}
            for skill in sorted(self._skills.values(), key=lambda item: item.name)
        ]

    def _rank(self, query: str) -> list[tuple[float, EngineeringSkill]]:
        query_tokens = _tokens(query)
        if not query_tokens or not self._skills:
            return []
        skills = list(self._skills.values())
        token_sets = [
            _tokens(skill.name.replace("-", " ") + " " + skill.description + " "
                    + " ".join(skill.tags) + " " + " ".join(skill.aliases) + " " + skill.body[:2000])
            for skill in skills
        ]
        document_frequency = {}
        for token_set in token_sets:
            for token in token_set:
                document_frequency[token] = document_frequency.get(token, 0) + 1
        ranked = []
        for skill, tokens in zip(skills, token_sets):
            overlap = query_tokens.intersection(tokens)
            score = sum(math.log((len(skills) + 1) / (document_frequency.get(token, 0) + 1)) + 1
                        for token in overlap)
            # Tags and aliases are an explicit intent map, so give them a small
            # boost without making unrelated skills appear relevant.
            metadata_tokens = _tokens(" ".join(skill.tags) + " " + " ".join(skill.aliases))
            score += 1.5 * len(query_tokens.intersection(metadata_tokens))
            if score > 0:
                ranked.append((score, skill))
        ranked.sort(key=lambda item: (-item[0], item[1].name))
        return ranked

    def retrieve(self, query: str, max_skills: int = MAX_SELECTED_SKILLS) -> dict:
        """Return the compact directory and the full bodies of the best matches."""
        limit = max(0, min(int(max_skills), MAX_SELECTED_SKILLS))
        ranked = self._rank(query)
        selected = []
        total_chars = 0
        for score, skill in ranked[:limit]:
            references = list(skill.references)
            block = {
                "name": skill.name,
                "description": skill.description,
                "relevance_score": round(score, 3),
                "instructions": skill.body,
                "available_references": references,
                "reference_rule": (
                    "References are local documents. Request them by exact relative path; "
                    "never infer dimensions, standards or verified results from their titles."
                ) if references else "",
            }
            size = len(block["instructions"])
            if total_chars + size > MAX_CONTEXT_CHARS:
                remaining = max(0, MAX_CONTEXT_CHARS - total_chars)
                if remaining < 1200:
                    break
                block["instructions"] = block["instructions"][:remaining] + "\n\n[skill excerpt truncated]"
                size = len(block["instructions"])
            selected.append(block)
            total_chars += size
        return {
            "catalog": self.catalog(),
            "selected": selected,
            "selected_count": len(selected),
            "available_count": len(self._skills),
            "progressive_disclosure": "Only matching skill bodies are loaded; references stay on disk until needed.",
        }

    def read_reference(self, name: str, resource: str) -> dict:
        skill = self._skills.get(str(name))
        if skill is None:
            return {"error": f"Unknown engineering skill: {name}"}
        requested = str(resource).replace("\\", "/").strip()
        while requested.startswith("./"):
            requested = requested[2:]
        if requested not in skill.references:
            return {"error": f"Reference '{resource}' is not in the skill's Markdown allow-list."}
        path = (skill.directory / requested).resolve()
        if skill.directory not in path.parents or path.is_symlink():
            return {"error": "Reference path is outside the skill directory."}
        try:
            raw = path.read_bytes()
        except OSError as exc:
            return {"error": f"Could not read reference: {exc}"}
        if len(raw) > MAX_REFERENCE_BYTES:
            return {"error": "Reference exceeds the configured size limit."}
        try:
            return {"output": raw.decode("utf-8")}
        except UnicodeDecodeError:
            return {"error": "Reference is not UTF-8 Markdown."}
