"""Small, dependency-free retrieval over the documentation shipped with FreeCAD.

This is deliberately lexical rather than an additional embedding model: the Qwen
weights remain the only model, and the native application's own manuals remain
the source of truth.
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
MAX_FILES = 650
MAX_FILE_BYTES = 350_000
MAX_PASSAGE_CHARS = 1400
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}")


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(token.lower() for token in TOKEN_RE.findall(query)))


def _mod_root() -> Path:
    # Installed layout: FreeCAD/Mod/NextAI/next_ai/knowledge.py
    return Path(__file__).resolve().parents[2]


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
                resolved = path.resolve()
                if resolved in seen or resolved.stat().st_size > MAX_FILE_BYTES:
                    continue
                seen.add(resolved)
                yield resolved
                count += 1
                if count >= MAX_FILES:
                    return
            except OSError:
                continue


def _passages(text: str):
    # Keep paragraphs and code examples together; long sections are split safely.
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= MAX_PASSAGE_CHARS:
            yield paragraph
        else:
            for offset in range(0, len(paragraph), MAX_PASSAGE_CHARS):
                yield paragraph[offset:offset + MAX_PASSAGE_CHARS]


def search(query: str, mod_root: Path | None = None, limit: int = 5):
    """Return the best matching local manual sections, with exact source paths."""
    terms = _terms(query)
    if not terms:
        return []
    root = Path(mod_root) if mod_root is not None else _mod_root()
    results = []
    for path in _candidate_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        file_hits = sum(text.lower().count(term) for term in terms)
        if file_hits == 0:
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
            results.append(
                {
                    "score": best[0],
                    "source": str(path.relative_to(root)),
                    "excerpt": best[1],
                }
            )
    results.sort(key=lambda item: (-item["score"], item["source"]))
    return results[:max(1, min(int(limit), 8))]
