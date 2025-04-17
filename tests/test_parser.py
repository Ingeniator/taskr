
# tests/test_parser.py

from services.parser import parse_task_text

def test_basic_parsing():
    assert parse_task_text("# Title\n\nDetails here") == ("Title", "Details here")

def test_empty_input():
    assert parse_task_text("") == ("", "")

def test_no_description():
    assert parse_task_text("Just a summary") == ("Just a summary", "")

def test_multiline_description():
    assert parse_task_text("## Title\nLine1\nLine2") == ("Title", "Line1\nLine2")