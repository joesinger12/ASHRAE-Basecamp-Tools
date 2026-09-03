from ashrae_basecamp.content import document_brief, extract_links, html_to_text, text_to_html


HTML = (
    "<div><strong>Agenda</strong><br>"
    'See the <a href="https://3.basecamp.com/3106353/buckets/352581/documents/1">charter</a> '
    'and <a href="https://example.com/notes">notes</a>.'
    "<br>Also the charter again: "
    '<a href="https://3.basecamp.com/3106353/buckets/352581/documents/1">duplicate</a>.'
    "</div>"
)


def test_extract_links_unique_by_href():
    links = extract_links(HTML)
    assert [link.href for link in links] == [
        "https://3.basecamp.com/3106353/buckets/352581/documents/1",
        "https://example.com/notes",
    ]
    assert links[0].text == "charter"
    assert links[1].text == "notes"


def test_html_to_text_strips_tags():
    assert "Agenda" in html_to_text(HTML)
    assert "<a" not in html_to_text(HTML)


def test_text_to_html_escapes_and_breaks():
    assert text_to_html("a <b>\nc") == "a &lt;b&gt;<br>c"


def test_document_brief_includes_title_url_and_links():
    brief = document_brief(
        {
            "title": "Test AI page",
            "app_url": "https://3.basecamp.com/3106353/buckets/352581/documents/10269026711",
            "content": HTML,
        }
    )
    assert "Title: Test AI page" in brief
    assert "https://3.basecamp.com/3106353/buckets/352581/documents/10269026711" in brief
    assert "charter: https://3.basecamp.com/3106353/buckets/352581/documents/1" in brief
