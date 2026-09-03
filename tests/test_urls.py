from ashrae_basecamp.urls import BasecampRef, UrlError, document_id_from, parse_basecamp_url
import pytest


def test_parse_app_document_url():
    ref = parse_basecamp_url(
        "https://3.basecamp.com/3106353/buckets/352581/documents/10269026711"
    )
    assert ref == BasecampRef(
        account_id=3106353,
        bucket_id=352581,
        kind="documents",
        resource_id=10269026711,
    )


def test_parse_api_flat_url():
    ref = parse_basecamp_url(
        "https://3.basecampapi.com/3106353/documents/10269026711.json"
    )
    assert ref.account_id == 3106353
    assert ref.bucket_id is None
    assert ref.kind == "documents"
    assert ref.resource_id == 10269026711


def test_parse_api_scoped_url():
    ref = parse_basecamp_url(
        "https://3.basecampapi.com/3106353/buckets/352581/documents/10269026711.json"
    )
    assert ref.bucket_id == 352581
    assert ref.resource_id == 10269026711


def test_parse_numeric_id():
    ref = parse_basecamp_url("10269026711")
    assert ref == BasecampRef(
        account_id=None, bucket_id=None, kind=None, resource_id=10269026711
    )


def test_document_id_from_rejects_other_kinds():
    with pytest.raises(UrlError, match="Expected a document"):
        document_id_from("https://3.basecamp.com/1/buckets/2/messages/3")


def test_parse_rejects_unknown_host():
    with pytest.raises(UrlError):
        parse_basecamp_url("https://example.com/3106353/buckets/1/documents/2")
