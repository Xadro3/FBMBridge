import os

import aiohttp
import pytest

import fbm_connector


def test_extract_facebook_urls_finds_marketplace_and_share_links():
    content = (
        "Check this out https://www.facebook.com/marketplace/item/111 "
        "and also https://m.facebook.com/share/abc-def "
        "plus http://facebook.com/marketplace/item/222?ref=share "
        "but not https://example.com/marketplace/item/333"
    )

    urls = fbm_connector.extract_facebook_urls(content)

    assert urls == [
        "https://www.facebook.com/marketplace/item/111",
        "https://m.facebook.com/share/abc-def",
        "http://facebook.com/marketplace/item/222?ref=share",
    ]


def test_extract_facebook_urls_returns_empty_for_unrelated_text():
    assert fbm_connector.extract_facebook_urls("hello world") == []


def test_parse_listing_maps_apify_fields(apify_item):
    listing = fbm_connector.parse_listing(apify_item)

    assert listing["title"] == "Vintage bicycle"
    assert listing["url"] == "https://www.facebook.com/marketplace/item/123456789"
    assert listing["price"] == "$150"
    assert listing["location"] == "Austin, TX"
    assert listing["description"] == {"text": "Lightly used, pickup preferred."}
    assert listing["image_url"] == "https://example.com/bike.jpg"
    assert listing["status"] == "Live"
    assert listing["delivery"] == "In Person, Shipping"
    assert listing["seller"] == "Alex"


def test_parse_listing_uses_fallbacks_and_default_title():
    listing = fbm_connector.parse_listing(
        {
            "share_uri": "https://www.facebook.com/share/xyz",
            "listing_price": {"amount": "40"},
            "location": {"reverse_geocode": {"city": "Denver"}},
            "is_sold": True,
        }
    )

    assert listing["title"] == "Facebook Marketplace Listing"
    assert listing["url"] == "https://www.facebook.com/share/xyz"
    assert listing["price"] == "40"
    assert listing["location"] == "Denver"
    assert listing["status"] == "Sold"
    assert listing["delivery"] is None
    assert listing["seller"] is None
    assert listing["image_url"] is None
    assert listing["description"] is None


def test_status_priority_pending_over_live():
    assert fbm_connector._status({"is_pending": True, "is_live": True}) == "Pending"
    assert fbm_connector._status({"is_hidden": True}) == "Hidden"
    assert fbm_connector._status({}) is None


@pytest.mark.asyncio
async def test_scrape_listing_posts_to_apify_and_parses_first_item(monkeypatch, apify_item):
    captured = {}

    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        async def json(self):
            return [apify_item]

    class FakeSession:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def post(self, url, params=None, json=None):
            captured["url"] = url
            captured["params"] = params
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setenv("APIFY_TOKEN", "test-token")
    monkeypatch.setattr(fbm_connector.aiohttp, "ClientSession", FakeSession)

    listing = await fbm_connector.scrape_listing(
        "https://www.facebook.com/marketplace/item/123456789"
    )

    assert listing["title"] == "Vintage bicycle"
    assert captured["url"] == fbm_connector.APIFY_ACTOR_URL
    assert captured["params"] == {"token": "test-token"}
    assert captured["json"]["startUrls"] == [
        {"url": "https://www.facebook.com/marketplace/item/123456789"}
    ]
    assert captured["json"]["resultsLimit"] == 1


@pytest.mark.asyncio
async def test_scrape_listing_returns_none_when_apify_dataset_is_empty(monkeypatch):
    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        async def json(self):
            return []

    class FakeSession:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setenv("APIFY_TOKEN", "test-token")
    monkeypatch.setattr(fbm_connector.aiohttp, "ClientSession", FakeSession)

    assert await fbm_connector.scrape_listing("https://facebook.com/marketplace/item/1") is None


@pytest.mark.asyncio
async def test_scrape_listing_requires_apify_token(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)

    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        await fbm_connector.scrape_listing("https://facebook.com/marketplace/item/1")


@pytest.mark.asyncio
async def test_scrape_listing_raises_on_http_error(monkeypatch):
    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=401,
                message="Unauthorized",
            )

    class FakeSession:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setenv("APIFY_TOKEN", "bad-token")
    monkeypatch.setattr(fbm_connector.aiohttp, "ClientSession", FakeSession)

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await fbm_connector.scrape_listing("https://facebook.com/marketplace/item/1")

    assert exc.value.status == 401
