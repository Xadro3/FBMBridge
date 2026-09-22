from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

import discord_connector
import fbm_connector


def test_build_embed_includes_listing_fields():
    listing = {
        "title": "Vintage bicycle",
        "url": "https://www.facebook.com/marketplace/item/123456789",
        "description": {"text": "Lightly used, pickup preferred."},
        "price": "$150",
        "location": "Austin, TX",
        "status": "Live",
        "delivery": "In Person, Shipping",
        "seller": "Alex",
        "image_url": "https://example.com/bike.jpg",
    }

    embed = discord_connector.build_embed(listing)

    assert embed.title == "Vintage bicycle"
    assert embed.url == listing["url"]
    assert embed.description == "Lightly used, pickup preferred."
    assert embed.color.value == 0x1877F2
    assert embed.footer.text == "Facebook Marketplace"
    assert embed.image.url == "https://example.com/bike.jpg"

    fields = {field.name: field.value for field in embed.fields}
    assert fields == {
        "Price": "$150",
        "Location": "Austin, TX",
        "Status": "Live",
        "Delivery": "In Person, Shipping",
        "Seller": "Alex",
    }


def test_build_embed_omits_optional_fields_and_truncates_description():
    listing = {
        "title": "Chair",
        "url": "https://www.facebook.com/marketplace/item/9",
        "description": {"text": "x" * 5000},
    }

    embed = discord_connector.build_embed(listing)

    assert embed.description == "x" * 4096
    assert embed.fields == []
    assert embed.image.url is None


@pytest.mark.asyncio
async def test_on_message_ignores_bots_and_messages_without_facebook_urls():
    bot_message = MagicMock()
    bot_message.author.bot = True
    bot_message.channel.send = AsyncMock()

    await discord_connector.on_message(bot_message)
    bot_message.channel.send.assert_not_called()

    human_message = MagicMock()
    human_message.author.bot = False
    human_message.content = "just chatting"
    human_message.channel.send = AsyncMock()

    await discord_connector.on_message(human_message)
    human_message.channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_sends_embed_for_scraped_listing(monkeypatch):
    listing = {
        "title": "Lamp",
        "url": "https://www.facebook.com/marketplace/item/1",
        "description": {"text": "Works"},
        "price": "$20",
        "location": None,
        "status": None,
        "delivery": None,
        "seller": None,
        "image_url": None,
    }
    monkeypatch.setattr(
        fbm_connector,
        "scrape_listing",
        AsyncMock(return_value=listing),
    )

    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    message = MagicMock()
    message.author.bot = False
    message.content = "see https://www.facebook.com/marketplace/item/1"
    message.channel.typing.return_value = typing_cm
    message.channel.send = AsyncMock()

    await discord_connector.on_message(message)

    message.channel.send.assert_awaited_once()
    kwargs = message.channel.send.await_args.kwargs
    assert kwargs["embed"].title == "Lamp"


@pytest.mark.asyncio
async def test_on_message_reports_http_errors_and_empty_results(monkeypatch):
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    http_error = aiohttp.ClientResponseError(
        request_info=None,
        history=(),
        status=502,
        message="Bad Gateway",
    )

    async def scrape(url: str):
        if "item/1" in url:
            raise http_error
        if "item/2" in url:
            return None
        raise RuntimeError("boom")

    monkeypatch.setattr(fbm_connector, "scrape_listing", scrape)

    message = MagicMock()
    message.author.bot = False
    message.content = (
        "https://www.facebook.com/marketplace/item/1 "
        "https://www.facebook.com/marketplace/item/2 "
        "https://www.facebook.com/marketplace/item/3"
    )
    message.channel.typing.return_value = typing_cm
    message.channel.send = AsyncMock()

    await discord_connector.on_message(message)

    texts = [call.args[0] for call in message.channel.send.await_args_list]
    assert texts[0].startswith("Failed to scrape listing (502):")
    assert texts[1].startswith("No listing data found for:")
    assert texts[2].startswith("Failed to scrape listing: boom")
