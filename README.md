# FBMBridge

Discord bot that watches for Facebook Marketplace links and replies with a rich embed. Listing data is fetched through [Apify](https://apify.com)'s [Facebook Marketplace scraper](https://apify.com/crawlerbros/facebook-marketplace-scraper).

```
Discord message with marketplace URL
        -> extract Facebook URLs
        -> Apify actor scrape
        -> Discord embed (title, price, location, photo, …)
```

## Requirements

- Python 3.10+
- A Discord bot token with the **Message Content Intent** enabled
- An Apify API token with access to the `crawlerbros~facebook-marketplace-scraper` actor

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env   # Windows
# cp .env.example .env  # macOS / Linux
```

Fill in `.env`:

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Discord bot token from the [developer portal](https://discord.com/developers/applications) |
| `APIFY_TOKEN` | Apify API token |

Invite the bot to your server with permission to **Read Messages**, **Send Messages**, and **Embed Links**. In the Discord developer portal, enable **Message Content Intent** so the bot can see URLs in messages.

## Run

```bash
python discord_connector.py
```

When a non-bot user posts a `facebook.com/marketplace/…` or `facebook.com/share/…` URL, the bot types in the channel, scrapes the listing, and posts an embed. HTTP and scrape failures are reported as a short text reply instead of an embed.

## Project layout

| File | Role |
| --- | --- |
| `discord_connector.py` | Discord client, embed builder, message handler |
| `fbm_connector.py` | URL extraction, Apify request, listing field mapping |
| `tests/` | Unit tests with mocked Apify and Discord I/O |

## Tests

```bash
pytest
```

Tests do not call Discord or Apify. They cover URL matching, Apify JSON mapping, embed construction, and the `on_message` error paths.

## Notes

- Apify runs can take a while; the HTTP timeout is 300 seconds.
- The scraper is configured with Apify residential proxies (`RESIDENTIAL`).
- Discord embed descriptions are truncated to 4096 characters.
