from html import escape
from html.parser import HTMLParser

from django.template.defaultfilters import linebreaks

PARAGRAPH_STYLE = "margin: 0 0 8px; line-height: 1.4;"
EDITOR_STYLE = f"body {{ font: 14px/1.4 sans-serif; }} p {{ {PARAGRAPH_STYLE} }}"


class _BodyParser(HTMLParser):
    """Locate paragraph start tags without rewriting the rest of the author's HTML."""

    def __init__(self, body: str):
        super().__init__(convert_charrefs=False)
        self.has_html = False
        self.paragraphs: list[tuple[int, int, str]] = []
        self.line_offsets = [0]
        for line in body.split("\n"):
            self.line_offsets.append(self.line_offsets[-1] + len(line) + 1)

    def handle_starttag(self, tag, attrs):
        self.has_html = True
        if tag != "p":
            return
        attributes = dict(attrs)
        attributes["style"] = f"{PARAGRAPH_STYLE} {attributes.get('style') or ''}".strip()
        rendered_attrs = "".join(
            f' {name}="{escape(value, quote=True)}"' if value is not None else f" {name}"
            for name, value in attributes.items()
        )
        line, column = self.getpos()
        start = self.line_offsets[line - 1] + column
        self.paragraphs.append((start, start + len(self.get_starttag_text()), f"<p{rendered_attrs}>"))

    def handle_startendtag(self, tag, attrs):
        self.has_html = True


def render_body(body: str) -> str:
    parser = _BodyParser(body)
    parser.feed(body)
    parser.close()
    if not parser.has_html:
        body = linebreaks(body, autoescape=True)
        parser = _BodyParser(body)
        parser.feed(body)
        parser.close()
    for start, end, replacement in reversed(parser.paragraphs):
        body = body[:start] + replacement + body[end:]
    return body
