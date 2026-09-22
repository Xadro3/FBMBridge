import os
import dotenv
import aiohttp
import discord

import fbm_connector

intents = discord.Intents.default()
intents.message_content = True
dotenv.load_dotenv()

client = discord.Client(intents=intents)


def build_embed(listing: dict) -> discord.Embed:
    embed = discord.Embed(
        title=listing["title"],
        url=listing["url"],
        color=0x1877F2,
    )

    print("Type:", type(listing["description"]))
    print("Content:", listing["description"])

    if listing.get("description"):
        tempdict = listing["description"]
        embed.description = tempdict["text"][:4096]

    if listing.get("price"):
        embed.add_field(name="Price", value=listing["price"], inline=True)

    if listing.get("location"):
        embed.add_field(name="Location", value=listing["location"], inline=True)

    if listing.get("status"):
        embed.add_field(name="Status", value=listing["status"], inline=True)

    if listing.get("delivery"):
        embed.add_field(name="Delivery", value=listing["delivery"], inline=True)

    if listing.get("seller"):
        embed.add_field(name="Seller", value=listing["seller"], inline=True)

    if listing.get("image_url"):
        embed.set_image(url=listing["image_url"])

    embed.set_footer(text="Facebook Marketplace")
    return embed


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    urls = fbm_connector.extract_facebook_urls(message.content)
    if not urls:
        return

    async with message.channel.typing():
        for url in urls:
            try:
                listing = await fbm_connector.scrape_listing(url)
            except aiohttp.ClientResponseError as exc:
                await message.channel.send(
                    f"Failed to scrape listing ({exc.status}): {url}"
                )
                continue
            except Exception as exc:
                await message.channel.send(f"Failed to scrape listing: {exc}")
                continue

            if not listing:
                await message.channel.send(f"No listing data found for: {url}")
                continue

            await message.channel.send(embed=build_embed(listing))


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN environment variable is not set")
    client.run(token)
