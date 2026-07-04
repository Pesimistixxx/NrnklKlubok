"""Тесты пост-обработки OCR (паттерн BCL 2011)."""
from mkg_ingestion.ocr_postprocess import clean_ocr_markdown

BCL_SAMPLE = """2011 г
4
С самого начала завод
работал в строй в строй
труба сушильной установки
сырье для плавки
печь
конвертер
Рис. 1. Схема плавильного никелевого завода BCL
ещё один абзац текста
который был разорван
на несколько строк без точки
и продолжается здесь."""


def test_removes_page_header_metadata():
    out = clean_ocr_markdown(BCL_SAMPLE)
    assert "2011 г" not in out.split("<!--")[0] if "<!--" in out else "2011 г" not in out[:80]
    assert "<!-- 2011 г · 4 -->" in out or "2011 г" in out  # metadata comment ok


def test_merges_broken_paragraphs():
    out = clean_ocr_markdown(BCL_SAMPLE)
    assert "на несколько строк без точки и продолжается здесь." in out


def test_dedupes_phrase_in_line():
    out = clean_ocr_markdown(BCL_SAMPLE)
    assert "в строй в строй" not in out
    assert "в строй" in out


def test_figure_caption_heading():
    out = clean_ocr_markdown(BCL_SAMPLE)
    assert "### Рис. 1." in out


def test_diagram_labels_grouped():
    out = clean_ocr_markdown(BCL_SAMPLE)
    assert "<details>" in out
    assert "труба сушильной установки" in out
    assert "Элементы схемы" in out
