import aiohttp
from urllib.parse import urljoin, urlparse 


COMMON_SITEMAP_PATHS = [
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap/",
    "sitemap1.xml",
    "sitemap_index.xml"
]



async def fetch_url(session: aiohttp.ClientSession, url: str) -> str | None:
    """Return text content from a URL or None on failure."""
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        return None
    return None


async def fetch_sitemap(official_url: str) -> str | None:
    """
    Attempts to retrieve a sitemap XML for a given official website URL.
    Returns the sitemap content or None if not found.
    """

    # Normalize the base URL
    parsed = urlparse(official_url)
    base = f"{parsed.scheme}://{parsed.netloc}/"

    async with aiohttp.ClientSession() as session:

        # ---------------------------------------------------
        # 1. Try common sitemap paths
        # ---------------------------------------------------
        for path in COMMON_SITEMAP_PATHS:
            sitemap_url = urljoin(base, path)
            content = await fetch_url(session, sitemap_url)
            if content:
                return content

        # ---------------------------------------------------
        # 2. Check robots.txt for sitemap declarations
        # ---------------------------------------------------
        robots_url = urljoin(base, "robots.txt")
        robots_txt = await fetch_url(session, robots_url)

        if robots_txt:
            for line in robots_txt.splitlines():
                if "sitemap:" in line.lower():
                    sitemap_line = line.split(":", 1)[1].strip()
                    # Could be multiple sitemap declarations
                    maybe_sitemap = await fetch_url(session, sitemap_line)
                    if maybe_sitemap:
                        return maybe_sitemap

        # ---------------------------------------------------
        # 3. No sitemap found
        # ---------------------------------------------------
        return None