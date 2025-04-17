# services/parser.py

def parse_task_text(text: str) -> tuple[str, str]:
    """
    Parses markdown-style task text into (summary, description).
    
    - Summary: First non-empty line, stripped of '#' prefix.
    - Description: Everything after an empty line or second line onward.
    """
    lines = text.strip().splitlines()

    summary = ""
    description_lines = []

    for i, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue
        if not summary:
            summary = clean.lstrip("#").strip()
        else:
            description_lines = lines[i:]
            break

    description = "\n".join(description_lines).strip()
    return summary, description
