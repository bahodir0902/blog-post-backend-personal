def extract_text_from_json_content(content: dict) -> str:
    if not content:
        return ""

    blocks = content.get("blocks", [])
    text_fragments = []
    for block in blocks:
        items = block.get("content", [])
        for item in items:
            text = item.get("text")
            if text:
                text_fragments.append(text.strip())

    return "".join(text_fragments) if text_fragments else ""


def calculate_read_time(text: str, wpm: int = 225) -> int:
    if not text:
        return 0
    words = len(text.split())
    minutes = max(1, int(words / wpm))
    return minutes
