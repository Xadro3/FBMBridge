import os
import re

import aiohttp

APIFY_ACTOR_URL = (
    "https://api.apify.com/v2/actors/crawlerbros~facebook-marketplace-scraper/"
    "run-sync-get-dataset-items"
)

FACEBOOK_URL_PATTERN = re.compile(
    r"https?://(?:www\.|m\.)?facebook\.com/(?:marketplace|share)/[^\s<>\"']+",
    re.IGNORECASE,
)


def extract_facebook_urls(content: str) -> list[str]:
    return FACEBOOK_URL_PATTERN.findall(content)


def _price(listing: dict) -> str | None:
    price = listing.get("listing_price") or {}
    return price.get("formatted_amount") or price.get("amount")


def _location(listing: dict) -> str | None:
    location = listing.get("location") or {}
    reverse_geocode = location.get("reverse_geocode") or {}
    city_page = reverse_geocode.get("city_page") or {}
    return city_page.get("display_name") or reverse_geocode.get("city")


def _image_url(listing: dict) -> str | None:
    photo = listing.get("primary_listing_photo") or {}
    image = photo.get("image") or {}
    return image.get("uri")


def _status(listing: dict) -> str | None:
    if listing.get("is_sold"):
        return "Sold"
    if listing.get("is_pending"):
        return "Pending"
    if listing.get("is_hidden"):
        return "Hidden"
    if listing.get("is_live"):
        return "Live"
    return None


def _delivery_types(listing: dict) -> str | None:
    types = listing.get("delivery_types")
    if not types:
        return None
    return ", ".join(t.replace("_", " ").title() for t in types)


def parse_listing(listing: dict) -> dict:
    return {
        "title": listing.get("marketplace_listing_title") or "Facebook Marketplace Listing",
        "url": listing.get("listingUrl") or listing.get("share_uri") or listing.get("facebookUrl"),
        "price": _price(listing),
        "location": _location(listing),
        "description": listing.get("redacted_description"),
        "image_url": _image_url(listing),
        "status": _status(listing),
        "delivery": _delivery_types(listing),
        "seller": (listing.get("marketplace_listing_seller") or {}).get("name"),
    }


async def scrape_listing(url: str) -> dict | None:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ValueError("APIFY_TOKEN environment variable is not set")

    payload = {
        "startUrls": [{"url": url}],
        "resultsLimit": 1,
        "includeListingDetails": True,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            APIFY_ACTOR_URL,
            params={"token": token},
            json=payload,
        ) as response:
            response.raise_for_status()
            items = await response.json()

    if not items:
        return None
    return parse_listing(items[0])
