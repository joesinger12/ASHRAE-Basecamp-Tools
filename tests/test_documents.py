from ashrae_basecamp.documents import append_content, merge_document


CURRENT = {
    "title": "Test AI page",
    "content": "<div>existing</div>",
}


def test_merge_keeps_omitted_fields():
    assert merge_document(CURRENT) == {
        "title": "Test AI page",
        "content": "<div>existing</div>",
    }


def test_merge_replaces_only_passed_fields():
    assert merge_document(CURRENT, title="New title")["title"] == "New title"
    assert merge_document(CURRENT, title="New title")["content"] == "<div>existing</div>"
    assert merge_document(CURRENT, content="<p>next</p>")["title"] == "Test AI page"


def test_merge_missing_content_becomes_empty_string():
    payload = merge_document({"title": "Only title"})
    assert payload == {"title": "Only title", "content": ""}


def test_append_concatenates_fragment():
    assert append_content("<div>existing</div>", "<div>note</div>") == (
        "<div>existing</div><div>note</div>"
    )


def test_append_treats_missing_content_as_empty():
    assert append_content(None, "<div>note</div>") == "<div>note</div>"
