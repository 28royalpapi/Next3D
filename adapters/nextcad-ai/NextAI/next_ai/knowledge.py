"""Compact local retrieval over native FreeCAD manuals and NextAI skill packs.

The knowledge files are references, not a second CAD/BIM engine. They add no model
weights and are searched locally; native APIs and validators remain authoritative.
"""
from __future__ import annotations

from pathlib import Path
import re

TEXT_SUFFIXES = {".md", ".rst", ".txt"}
SOURCE_DOCS = {"Arch.py", "Draft.py", "Part.py", "TechDraw.py", "Sketcher.py"}
IGNORED_PARTS = {
    ".git", "build", "dist", "tests", "test", "examples", "translations",
    "vendor", "thirdparty", "third_party", "node_modules", "__pycache__",
}
MAX_FILES_PER_ROOT = 650
MAX_FILE_BYTES = 350_000
MAX_PASSAGE_CHARS = 1400
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}")


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(token.lower() for token in TOKEN_RE.findall(query)))


def _mod_root() -> Path:
    # Installed layout: FreeCAD/Mod/NextAI/next_ai/knowledge.py
    return Path(__file__).resolve().parents[2]


def _skill_pack_root() -> Path:
    # Installed layout: FreeCAD/Mod/NextAI/knowledge_packs/
    return Path(__file__).resolve().parents[1] / "knowledge_packs"


def _candidate_files(mod_root: Path):
    seen = set()
    count = 0
    for module in sorted(mod_root.iterdir()) if mod_root.is_dir() else ():
        if not module.is_dir() or module.name == "NextAI" or module.name.startswith("."):
            continue
        candidates = []
        for name in ("README.md", "README.rst", "README.txt"):
            path = module / name
            if path.is_file():
                candidates.append(path)
        for name in ("docs", "doc", "Documentation", "Docs"):
            folder = module / name
            if folder.is_dir():
                candidates.extend(
                    path for path in folder.rglob("*")
                    if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
                    and not any(part.lower() in IGNORED_PARTS for part in path.parts)
                )
        for name in SOURCE_DOCS:
            path = module / name
            if path.is_file():
                candidates.append(path)
        for path in candidates:
            try:
                resolved = path.absolute()
                if resolved in seen or resolved.stat().st_size > MAX_FILE_BYTES:
                    continue
                seen.add(resolved)
                yield resolved
                count += 1
                if count >= MAX_FILES_PER_ROOT:
                    return
            except OSError:
                continue


def _skill_files(root: Path):
    if not root.is_dir():
        return
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part.lower() in IGNORED_PARTS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            yield path
            count += 1
            if count >= MAX_FILES_PER_ROOT:
                return
        except OSError:
            continue


def _passages(text: str):
    # Keep paragraphs and code examples together; split long sections safely.
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= MAX_PASSAGE_CHARS:
            yield paragraph
        else:
            for offset in range(0, len(paragraph), MAX_PASSAGE_CHARS):
                yield paragraph[offset:offset + MAX_PASSAGE_CHARS]


def search(query: str, mod_root: Path | None = None, limit: int = 6):
    """Return matching excerpts from the live native manuals and bundled skill packs."""
    terms = _terms(query)
    if not terms:
        return []

    native_root = (Path(mod_root) if mod_root is not None else _mod_root()).absolute()
    roots = [
        ("native", native_root, _candidate_files(native_root)),
        ("nextai", _skill_pack_root(), _skill_files(_skill_pack_root())),
    ]
    results = []
    for label, root, paths in roots:
        if not root.is_dir():
            continue
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            best = None
            for passage in _passages(text):
                lower = passage.lower()
                hit_count = sum(lower.count(term) for term in terms)
                if hit_count == 0:
                    continue
                coverage = sum(1 for term in terms if term in lower)
                score = hit_count + coverage * 2
                if best is None or score > best[0]:
                    best = (score, passage)
            if best is not None:
                try:
                    relative = str(path.relative_to(root))
                except ValueError:
                    relative = path.name
                results.append({
                    "score": best[0],
                    "source": f"{label}/{relative}",
                    "excerpt": best[1],
                })
    results.sort(key=lambda item: (-item["score"], item["source"]))
    return results[:max(1, min(int(limit), 10))]
