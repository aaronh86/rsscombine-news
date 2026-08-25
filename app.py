import html
import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from flask import Flask, Response, jsonify
import feedparser
import requests

app = Flask(__name__)

CONFIG_PATH = os.getenv("CONFIG_PATH", "/app/feeds.json")
TIMEOUT = int(os.getenv("FETCH_TIMEOUT_SECONDS", "20"))
USER_AGENT = os.getenv("USER_AGENT", "rsscombine-news/1.0")


def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    economist = os.getenv("ECONOMIST_RSS_URL", "").strip()
    if economist:
        sources.append({"name": "The Economist", "url": economist})
    return sources


def fetch_latest(source):
    r = requests.get(
        source["url"],
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    if not parsed.entries:
        raise RuntimeError("feed has no entries")

    entry = parsed.entries[0]
    enclosures = entry.get("enclosures", [])
    if not enclosures:
        raise RuntimeError("latest entry has no audio enclosure")

    enclosure = enclosures[0]
    audio_url = enclosure.get("href") or enclosure.get("url")
    if not audio_url:
        raise RuntimeError("audio enclosure has no URL")

    guid = entry.get("id") or entry.get("guid") or entry.get("link") or audio_url
    title = entry.get("title") or source["name"]
    description = entry.get("summary") or entry.get("description") or ""
    link = entry.get("link") or source["url"]
    mime = enclosure.get("type") or "audio/mpeg"
    length = enclosure.get("length") or "0"

    actual_date = None
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            actual_date = datetime(*value[:6], tzinfo=timezone.utc)
            break

    return {
        "source": source["name"],
        "title": title,
        "description": description,
        "link": link,
        "guid": str(guid),
        "audio_url": audio_url,
        "mime": mime,
        "length": str(length),
        "actual_date": actual_date,
    }


def cdata(text):
    return "<![CDATA[" + str(text).replace("]]>", "]]]]><![CDATA[>") + "]]>")


def build_feed():
    sources = load_sources()
    items = []
    errors = []

    for source in sources:
        try:
            items.append(fetch_latest(source))
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}")

    # Podcast apps often sort by pubDate. Assign synthetic dates a few seconds apart
    # so the configured source order is preserved, while keeping the real source
    # publication time in each item's description.
    now = datetime.now(timezone.utc)
    xml_items = []
    for idx, item in enumerate(items):
        synthetic_date = now - timedelta(seconds=idx)
        actual = (
            item["actual_date"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if item["actual_date"]
            else "unknown"
        )
        description = f"Source: {item['source']} | Original publication: {actual}<br/><br/>{item['description']}"
        xml_items.append(f"""
    <item>
      <title>{html.escape(item['source'] + ' — ' + item['title'])}</title>
      <link>{html.escape(item['link'])}</link>
      <guid isPermaLink=\"false\">{html.escape(item['guid'])}</guid>
      <pubDate>{format_datetime(synthetic_date)}</pubDate>
      <description>{cdata(description)}</description>
      <enclosure url=\"{html.escape(item['audio_url'], quote=True)}\" length=\"{html.escape(item['length'], quote=True)}\" type=\"{html.escape(item['mime'], quote=True)}\" />
    </item>""")

    warning = ""
    if errors:
        warning = "<!-- " + " | ".join(errors).replace("--", "—") + " -->"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">
  <channel>
    <title>My News Briefing</title>
    <link>http://localhost/feed.xml</link>
    <description>Latest audio bulletin from each configured news provider.</description>
    <language>en-au</language>
    <itunes:author>rsscombine-news</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    {warning}
    {''.join(xml_items)}
  </channel>
</rss>
"""


@app.get("/feed.xml")
def feed():
    return Response(build_feed(), mimetype="application/rss+xml")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "sources": len(load_sources())})


@app.get("/")
def index():
    return (
        "rsscombine-news is running. Subscribe your podcast app to /feed.xml",
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
