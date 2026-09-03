from ashrae_basecamp.documents import _project_id, append_content


def test_append_concatenates_fragment():
    assert append_content("<div>existing</div>", "<div>note</div>") == (
        "<div>existing</div><div>note</div>"
    )


def test_append_treats_missing_content_as_empty():
    assert append_content(None, "<div>note</div>") == "<div>note</div>"


def test_project_id_from_url():
    assert _project_id(
        "https://3.basecamp.com/3106353/buckets/352581/documents/10269026711"
    ) == "352581"


def test_project_id_from_document_bucket():
    assert _project_id("10269026711", {"bucket": {"id": 99}}) == "99"
