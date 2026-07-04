"""Пост-обработка сырого OCR-текста → читаемый Markdown.

Эвристики для отчётов со схемами (BCL и аналоги):
- склейка разорванных строк в абзацы;
- выделение подписей к рисункам;
- группировка коротких меток схем;
- удаление колонтитулов (год, номер страницы).
"""
from __future__ import annotations

import re
from typing import Literal

LineKind = Literal["header_meta", "figure_caption", "diagram_label", "heading", "body", "blank"]

# Подпись к рисунку
_FIGURE_CAPTION_RE = re.compile(
    r"^(?:Рис\.|Рисунок|Fig\.|Figure)\s*\d+[\.\)]?\s*",
    re.IGNORECASE,
)

# Колонтитул: год
_YEAR_HEADER_RE = re.compile(r"^\d{4}\s*г\.?\s*$", re.IGNORECASE)

# Номер страницы (1–3 цифры, отдельная строка)
_PAGE_NUM_RE = re.compile(r"^\d{1,3}$")

# Нумерованный раздел
_NUMBERED_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$")

# Заголовок ALL CAPS (кириллица/латиница, ≥4 символов)
_ALL_CAPS_RE = re.compile(r"^[A-ZА-ЯЁ\s\d\-–—]{4,}$")

# Конец предложения / абзаца
_SENTENCE_END_RE = re.compile(r"[.!?;:»\"]\s*$")

# Начало предложения (предлог/наречие) — проверяется через startswith
_SENTENCE_PREFIXES = (
    "с ", "С ", "c ", "C ",
    "в ", "В ", "v ", "V ",
    "на ", "На ", "по ", "По ",
    "из ", "Из ", "от ", "От ",
    "для ", "Для ", "при ", "При ",
    "к ", "К ", "о ", "О ", "об ", "Об ",
    "со ", "Со ", "во ", "Во ",
    "the ", "The ", "a ", "A ", "an ", "An ",
    "in ", "In ", "on ", "On ", "at ", "At ", "from ", "From ",
)

# Окончания глаголов (рус.)
_RU_VERB_END_RE = re.compile(
    r"(?:"
    r"ает|яет|ует|ёет|ит|ат|ют|ся|"
    r"ал|ала|али|лся|лась|лись|"
    r"ем|им|ать|ять|ить|еть|уть|"
    r"ыва|ива|овал"
    r")\b",
    re.IGNORECASE,
)

_PROSE_WORDS = frozenset(
    {
        "ещё", "еще", "это", "этот", "эта", "эти", "который", "которая", "которые",
        "может", "можно", "был", "была", "были", "быть", "будет", "один", "одна",
        "the", "this", "that", "these", "those", "with", "from", "which",
    }
)

_DIAGRAM_MAX_LEN = 40


def _normalize_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return lines


def _dedupe_consecutive(lines: list[str]) -> list[str]:
    """Убрать подряд идущие дубликаты («в строй в строй»)."""
    out: list[str] = []
    prev = ""
    for ln in lines:
        if not ln:
            out.append(ln)
            prev = ""
            continue
        norm = re.sub(r"\s+", " ", ln.lower())
        if norm == prev:
            continue
        out.append(ln)
        prev = norm
    return out


def _dedupe_phrase_repeats(line: str) -> str:
    """Склеить повтор фразы в одной строке: «в строй в строй» → «в строй»."""
    words = line.split()
    if len(words) < 4:
        return line
    half = len(words) // 2
    if half >= 2 and words[:half] == words[half : half * 2]:
        return " ".join(words[:half])
    return line


def _classify_line(line: str) -> LineKind:
    if not line.strip():
        return "blank"
    if _YEAR_HEADER_RE.match(line) or _PAGE_NUM_RE.match(line):
        return "header_meta"
    if _FIGURE_CAPTION_RE.match(line):
        return "figure_caption"
    if _NUMBERED_SECTION_RE.match(line) or _ALL_CAPS_RE.match(line.strip()):
        return "heading"
    if _is_diagram_label(line):
        return "diagram_label"
    return "body"


def _is_diagram_label(line: str) -> bool:
    """Короткая строка без знаков конца предложения — вероятная метка схемы."""
    s = line.strip()
    if not s or len(s) > _DIAGRAM_MAX_LEN:
        return False
    if _FIGURE_CAPTION_RE.match(s):
        return False
    if _SENTENCE_END_RE.search(s):
        return False
    if s.startswith(_SENTENCE_PREFIXES):
        return False
    if _RU_VERB_END_RE.search(s):
        return False
    if s.count(".") > 1 or s.count(",") > 1:
        return False
    words = s.split()
    if len(words) > 5:
        return False
    lower_words = {w.lower().strip(".,;:") for w in words}
    if lower_words & _PROSE_WORDS:
        return False
    if any(len(w) >= 8 for w in words):
        return False
    if len(s) > 28 and " " in s and any(ch in s for ch in ",.;:"):
        return False
    return True


def _should_merge_lines(prev: str, nxt: str) -> bool:
    """Склеить разорванную строку OCR в абзац."""
    if not prev or not nxt:
        return False
    if _classify_line(prev) != "body" or _classify_line(nxt) != "body":
        return False
    if _SENTENCE_END_RE.search(prev.rstrip()):
        return False
    # Следующая строка начинается со строчной (ru/en)
    if nxt[0].islower():
        return True
    # Предыдущая обрывается на запятой или дефисе
    if prev.rstrip().endswith((",", "-", "–", "—")):
        return True
    return False


def _merge_body_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln:
            out.append(ln)
            i += 1
            continue
        merged = _dedupe_phrase_repeats(ln)
        while i + 1 < len(lines) and _should_merge_lines(merged, lines[i + 1]):
            i += 1
            merged = f"{merged.rstrip()} {lines[i].strip()}"
        out.append(merged)
        i += 1
    return out


def _format_heading(line: str) -> str:
    m = _NUMBERED_SECTION_RE.match(line)
    if m:
        return f"## {m.group(1)}. {m.group(2).strip()}"
    if _ALL_CAPS_RE.match(line.strip()):
        title = line.strip().title() if len(line) > 6 else line.strip()
        return f"## {title}"
    return f"## {line.strip()}"


def _format_figure_caption(line: str) -> str:
    return f"### {line.strip()}"


def _format_diagram_block(labels: list[str]) -> str:
    if not labels:
        return ""
    items = "\n".join(f"- {lbl.strip()}" for lbl in labels if lbl.strip())
    return (
        "<details>\n"
        "<summary>Элементы схемы</summary>\n\n"
        f"{items}\n\n"
        "</details>"
    )


def _remove_repeated_headers(lines: list[str]) -> list[str]:
    """Убрать часто повторяющиеся колонтитулы (≥3 раз)."""
    counts: dict[str, int] = {}
    for ln in lines:
        s = ln.strip()
        if not s or len(s) > 60:
            continue
        key = s.lower()
        counts[key] = counts.get(key, 0) + 1
    repeated = {k for k, v in counts.items() if v >= 3 and len(k) < 50}
    out: list[str] = []
    for ln in lines:
        if ln.strip().lower() in repeated and _classify_line(ln) in {"header_meta", "body"}:
            if len(ln.strip()) < 30 and not _SENTENCE_END_RE.search(ln):
                continue
        out.append(ln)
    return out


def clean_ocr_markdown(text: str) -> str:
    """Нормализовать сырой OCR в читаемый Markdown."""
    if not text or not text.strip():
        return text

    lines = _normalize_lines(text)
    lines = _dedupe_consecutive(lines)
    lines = _remove_repeated_headers(lines)
    lines = _merge_body_lines(lines)

    blocks: list[str] = []
    diagram_buf: list[str] = []
    meta_buf: list[str] = []

    def flush_diagram() -> None:
        nonlocal diagram_buf
        if diagram_buf:
            blocks.append(_format_diagram_block(diagram_buf))
            diagram_buf = []

    def flush_meta() -> None:
        nonlocal meta_buf
        if meta_buf:
            blocks.append(f"<!-- {' · '.join(meta_buf)} -->")
            meta_buf = []

    for ln in lines:
        if not ln:
            flush_diagram()
            flush_meta()
            blocks.append("")
            continue

        kind = _classify_line(ln)

        if kind == "header_meta":
            flush_diagram()
            meta_buf.append(ln.strip())
            continue

        flush_meta()

        if kind == "diagram_label":
            diagram_buf.append(ln)
            continue

        flush_diagram()

        if kind == "figure_caption":
            blocks.append(_format_figure_caption(ln))
        elif kind == "heading":
            blocks.append(_format_heading(ln))
        else:
            blocks.append(ln)

    flush_diagram()
    flush_meta()

    result = "\n\n".join(b for b in blocks if b is not None)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n" if result.strip() else ""
