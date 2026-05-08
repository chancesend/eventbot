# eventbot

A self-hosted event recommendation service for your home server. It wakes on a schedule, uses an AI agent to search the web for upcoming events matching your interests, emails you a curated digest, and gets smarter over time through your feedback.

Supports multiple household members, each with their own preferences and schedule, plus a shared "household" mode that finds events everyone might enjoy together.

---

## How it works

```
APScheduler (cron)
      │
      ▼
Claude Sonnet agent
  ├─ generates 6–10 targeted search queries from your interests
  ├─ calls Tavily web search for each (results cached ~6h to avoid redundant calls)
  ├─ extracts & deduplicates event candidates
  └─ ranks top 10 by relevance to your preferences + feedback history
      │
      ├─► SQLite (events, recommendations, feedback, run logs)
      └─► SMTP email digest → your inbox
              │
              └─► links back to web UI for 👍/👎 feedback
```

**Preferences** are plain YAML files — one per person, hand-editable or managed via the web UI. The feedback you give on events is summarised and included in the next agent run's context, so recommendations improve without any ML infrastructure.

**Household mode** works two ways:
1. A dedicated `household.yaml` drives its own agent run searching for cross-user appeal.
2. Any event that independently appears in two or more users' runs is automatically promoted to the household feed.

---

## Requirements

- Docker + Docker Compose (TrueNAS SCALE has this built in)
- [Anthropic API key](https://console.anthropic.com/) (Claude Sonnet)
- [Tavily API key](https://tavily.com/) (free tier: 1,000 searches/month — plenty for weekly runs)
- An SMTP account to send from (Gmail with an app password works well)

---

## Setup

### 1. Prepare the data directory

Create a persistent directory on your server. On TrueNAS SCALE, create a dataset (e.g. `/mnt/pool/eventbot-data`). For local development, `./data` is used by default.

```
data/
├── .env                  # API keys and SMTP credentials
└── preferences/
    ├── alice.yaml        # one file per person
    └── household.yaml    # optional shared profile
```

### 2. Create your `.env` file

Copy `.env.example` to `data/.env` and fill in your credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com
```

> **Gmail tip:** Use an [App Password](https://myaccount.google.com/apppasswords), not your account password. Requires 2FA to be enabled.

### 3. Create preference files

Copy `data/preferences/example_alice.yaml` to `data/preferences/yourname.yaml` (the filename becomes your URL slug) and edit it:

```yaml
display_name: Alice
email: alice@example.com
location: Portland, OR
timezone: America/Los_Angeles
interests:
  - live music and concerts
  - outdoor hiking and nature events
  - local food festivals and farmers markets
  - comedy shows
blocklist:
  - country music
schedule:
  frequency: weekly
  day_of_week: monday
  hour: 8
```

The `slug` is derived from the filename — `alice.yaml` → `/u/alice/`.

### 4. Start the service

```bash
# Default: uses ./data as the data directory
docker compose up -d

# TrueNAS SCALE: point at your dataset
DATA_PATH=/mnt/pool/eventbot-data docker compose up -d
```

The web UI is available at `http://<server-ip>:8080`.

---

## User guide

### Web UI

| URL | What it does |
|---|---|
| `http://server:8080/` | User picker — choose your profile |
| `http://server:8080/u/{name}/` | Your event picks + 👍/👎 rating |
| `http://server:8080/u/{name}/preferences` | Edit your preferences and schedule |
| `http://server:8080/u/{name}/history` | Past run history and error log |
| `http://server:8080/household/` | Events your household could enjoy together |

### iOS home screen applet

Open your personal URL (`http://server:8080/u/yourname/`) in Safari, tap **Share → Add to Home Screen**. It launches as a standalone app with no browser chrome. Do the same for `/household/` to get a shared household bookmark.

### Rating events

Tap 👍 or 👎 on any event in the web UI, or use the rating links in the email digest. Ratings are stored and included as context in your next agent run — consistently thumbs-downing a genre or type of event will cause the agent to avoid it going forward.

### Triggering a run manually

Hit **▶ Run now** from your profile page. Runs in the background; refresh the page after a minute to see results. You can also trigger the household run from `/household/`.

### Adding a new user

1. Create `data/preferences/newname.yaml` (copy the example and edit)
2. Restart the container — the scheduler picks up new YAML files on startup

### Household preferences

The household profile (`preferences/household.yaml`) can be:
- **Hand-crafted** — write it yourself with interests spanning the whole household
- **Auto-generated** — click **⚡ Re-sync from user prefs** on the `/household/` page; this builds a union of everyone's interests and blocklists

The household email digest is sent to all individual users' email addresses after each household run. This is separate from each person's personal digest.

### Schedule options

```yaml
schedule:
  frequency: weekly      # daily | weekly | monthly
  day_of_week: monday    # for weekly (monday–sunday)
  day_of_month: 1        # for monthly (1–28)
  hour: 8                # 0–23, interpreted in the user's timezone
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests cover preference I/O, household synthesis, agent helpers (deduplication, hashing), and SQLAlchemy model constraints. They use an in-memory SQLite database and do not require API keys.

---

## Architecture notes

### Storage split

- **YAML files** hold user configuration (preferences, schedule, blocklist). These are intentionally human-readable and hand-editable.
- **SQLite** (`eventbot.db`) holds operational data: discovered events, per-user recommendations, feedback ratings, run history, and the search cache.

### Deduplication

Events are deduplicated globally on `(venue, event_date, title_slug)` before being stored. The `recommendations` table is a join table — an event recommended to multiple users gets multiple rows, which is how shared/household events emerge naturally from a query.

### Search cache

Tavily search results are cached in the `search_cache` table for 6 hours, keyed on a hash of the query string. When multiple users share interests and their runs happen close together, the second run hits the cache instead of making redundant API calls.

### Feedback loop

The agent receives a plain-text summary of your past ratings ("Previously liked: X, Y; disliked: A, B") as part of its system prompt. No ML, no embeddings — just context. This is enough to steer the agent's query generation and ranking.
