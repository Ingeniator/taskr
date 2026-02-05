
# tests/test_parser.py

import pytest
from services.parser import parse_task_text


class TestBasicParsing:
    def test_markdown_title_with_description(self):
        assert parse_task_text("# Title\n\nDetails here") == ("Title", "Details here")

    def test_h2_title_with_multiline_description(self):
        assert parse_task_text("## Title\nLine1\nLine2") == ("Title", "Line1\nLine2")

    def test_plain_summary_no_description(self):
        assert parse_task_text("Just a summary") == ("Just a summary", "")

    def test_empty_input(self):
        assert parse_task_text("") == ("", "")

    def test_whitespace_only(self):
        assert parse_task_text("   \n  \n   ") == ("", "")


class TestSummaryExtraction:
    def test_strips_single_hash(self):
        summary, _ = parse_task_text("# Fix login bug")
        assert summary == "Fix login bug"

    def test_strips_multiple_hashes(self):
        summary, _ = parse_task_text("### Deep heading")
        assert summary == "Deep heading"

    def test_strips_leading_whitespace(self):
        summary, _ = parse_task_text("   Fix login bug")
        assert summary == "Fix login bug"

    def test_strips_hash_and_whitespace(self):
        summary, _ = parse_task_text("#   Spaced heading  ")
        assert summary == "Spaced heading"

    def test_skips_empty_lines_to_find_summary(self):
        summary, _ = parse_task_text("\n\n\n# Real title\nDesc")
        assert summary == "Real title"

    def test_plain_text_summary(self):
        summary, _ = parse_task_text("No markdown here")
        assert summary == "No markdown here"


class TestDescriptionExtraction:
    def test_description_after_blank_line(self):
        _, desc = parse_task_text("# Title\n\nFirst paragraph\nSecond line")
        assert "First paragraph" in desc
        assert "Second line" in desc

    def test_description_starts_at_second_line(self):
        _, desc = parse_task_text("Title\nDescription line")
        assert desc == "Description line"

    def test_multiline_description_preserved(self):
        text = "# Title\nLine 1\nLine 2\nLine 3"
        _, desc = parse_task_text(text)
        assert desc == "Line 1\nLine 2\nLine 3"

    def test_description_with_blank_lines_inside(self):
        text = "# Title\nParagraph 1\n\nParagraph 2"
        _, desc = parse_task_text(text)
        assert "Paragraph 1" in desc
        assert "Paragraph 2" in desc

    def test_description_strips_trailing_whitespace(self):
        text = "# Title\nDesc   \n   "
        _, desc = parse_task_text(text)
        assert desc == "Desc"


class TestEdgeCases:
    def test_only_hashes(self):
        summary, desc = parse_task_text("###")
        assert summary == ""
        assert desc == ""

    def test_single_newline_between_lines(self):
        summary, desc = parse_task_text("Summary\nDescription")
        assert summary == "Summary"
        assert desc == "Description"

    def test_very_long_input(self):
        lines = ["# Title"] + [f"Line {i}" for i in range(100)]
        text = "\n".join(lines)
        summary, desc = parse_task_text(text)
        assert summary == "Title"
        assert "Line 0" in desc
        assert "Line 99" in desc

    def test_special_characters_in_summary(self):
        summary, _ = parse_task_text("# Fix bug: API returns 500 (urgent!)")
        assert summary == "Fix bug: API returns 500 (urgent!)"

    def test_unicode_content(self):
        summary, desc = parse_task_text("# Исправить баг\nОписание задачи")
        assert summary == "Исправить баг"
        assert desc == "Описание задачи"

    def test_tabs_in_content(self):
        summary, desc = parse_task_text("# Title\n\tTabbed description")
        assert summary == "Title"
        assert "Tabbed description" in desc
