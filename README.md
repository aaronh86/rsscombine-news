# rsscombine-news

A tiny podcast-feed aggregator intended to recreate the old Google Assistant **Play my news** experience.

It fetches several publisher podcast RSS feeds, selects only the newest audio item from each source, and exposes them as one podcast-compatible RSS feed. Audio is **not downloaded, proxied, transcoded, or concatenated**: each `<enclosure>` points directly to the publisher's original audio URL.

## Default order

1. ABC News Australia
2. Sky News Australia
3. Al Jazeera
4. BBC World Service
5. CNN 5 Things
6. The Economist (optional private feed)

The service assigns synthetic publication timestamps a few seconds apart so podcast clients that sort by date retain this configured order. The original publication time is included in each episode description.

## Run with Docker

```yaml
services:
  rsscombine-news:
    image: ghcr.io/aaronh86/rsscombine-news:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
```

Then subscribe your podcast client to:

```text
http://YOUR-TRUENAS-IP:8080/feed.xml
```

Health check:

```text
http://YOUR-TRUENAS-IP:8080/health
```

## The Economist

If you have an Economist Podcasts+ private RSS URL, pass it only at runtime so the private token is not committed to GitHub:

```yaml
environment:
  ECONOMIST_RSS_URL: "YOUR_PRIVATE_RSS_URL"
```

It will be appended as the sixth source.

## Configuration

The public sources are stored in `feeds.json`. Change their order there to change briefing order.

Environment variables:

- `ECONOMIST_RSS_URL` - optional private Economist RSS URL
- `FETCH_TIMEOUT_SECONDS` - upstream request timeout, default 20
- `PORT` - HTTP port inside the container, default 8080
- `CONFIG_PATH` - path to feeds JSON, default `/app/feeds.json`

## Endpoints

- `/feed.xml` - combined podcast RSS
- `/health` - health endpoint
- `/` - basic status page

## Container builds

GitHub Actions builds `linux/amd64` and `linux/arm64` images and publishes them to GitHub Container Registry as:

```text
ghcr.io/aaronh86/rsscombine-news:latest
```

The repository/package may be private by default. If TrueNAS is to pull without GHCR credentials, change the package visibility to public in GitHub package settings.

## Acknowledgements

Inspired by **RSS Combine**, created by **Chase Seibert**:
https://github.com/chase-seibert/rsscombine

RSS Combine provided the inspiration for the feed-combining approach used by this project. This implementation is independently written and purpose-built for podcast feeds, including preservation of the publishers' original podcast audio enclosure URLs.
