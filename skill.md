# SKILL.md — Automation SaaS

## Project overview

Build a modular, fully automated social media marketing system.
The system runs on a cron schedule with zero manual intervention.
The owner sets topics once. The system generates content, publishes it,
tracks engagement, and logs leads — completely autonomously.

This is both an internal tool (to market other products) and a
monetizable SaaS ($5–15/month for solo builders with no marketing budget).

---

## Stack

- Language: Python 3.11+
- Framework: FastAPI
- AI: OpenRouter API (free models — mistralai/mistral-7b-instruct or meta-llama/llama-3-8b-instruct)
- Scheduler: APScheduler (in-process) or system cron via shell
- Database: PostgreSQL (same Railway instance as other projects)
- Queue: Simple DB table (no Redis needed at MVP stage)
- Deployment: Railway (free tier)
- Env vars: .env file via python-dotenv

---

## Folder structure

automation-saas/
  main.py                  # FastAPI app entry point
  scheduler.py             # APScheduler setup, registers all jobs
  .env                     # API keys and config (never commit)
  requirements.txt
  modules/
    content_generator.py   # Calls OpenRouter, returns post text
    x_publisher.py         # Posts to X via free write-only API
    linkedin_publisher.py  # Posts to LinkedIn via official API
    engagement_tracker.py  # Reads own post stats, stores to DB
    lead_logger.py         # Logs users who engage, flags as leads
  db/
    models.py              # SQLAlchemy models
    session.py             # DB session factory
  utils/
    logger.py              # Structured logging
    config.py              # Loads and validates env vars

---

## Module specifications

### 1. content_generator.py

Purpose: Generate platform-appropriate post text from a topic.

Input:
  - topic: str (e.g. "AI agent failures in production")
  - platform: str ("x" | "linkedin")
  - tone: str ("technical" | "founder" | "casual") — default "founder"

Process:
  - Call OpenRouter chat completion endpoint
  - Use model: mistralai/mistral-7b-instruct (free)
  - System prompt sets platform constraints:
    - X: max 280 chars, punchy, no hashtag spam, hook in first line
    - LinkedIn: 150–300 words, insight-driven, ends with question or CTA
  - Return generated post text as string

Config needed in .env:
  OPENROUTER_API_KEY=
  OPENROUTER_MODEL=mistralai/mistral-7b-instruct

Error handling:
  - Retry once on API timeout
  - Log failure, skip post on second failure (do not crash scheduler)

---

### 2. x_publisher.py

Purpose: Publish a post to X (Twitter) using the free write-only API.

X free tier limits:
  - 500 posts/month (~16/day max — use max 2/day to stay safe)
  - Write-only: cannot read timeline or replies on free tier

Input:
  - text: str (max 280 chars — truncate with ellipsis if over)

Process:
  - Use tweepy library with OAuth 1.0a authentication
  - Call client.create_tweet(text=text)
  - Store post_id and timestamp to DB on success

Config needed in .env:
  X_API_KEY=
  X_API_SECRET=
  X_ACCESS_TOKEN=
  X_ACCESS_TOKEN_SECRET=

Error handling:
  - On 429 (rate limit): log and skip, do not retry same day
  - On auth error: log and alert via console, halt X publishing
  - Never raise unhandled exceptions — always catch and log

---

### 3. linkedin_publisher.py

Purpose: Publish a post to a LinkedIn profile using the official API.

LinkedIn free tier:
  - Official API is free for personal profiles via OAuth 2.0
  - Use the ugcPosts endpoint to create a text post

Input:
  - text: str

Process:
  - Authenticate via OAuth 2.0 (access token stored in .env)
  - Get user URN: GET https://api.linkedin.com/v2/me
  - Post content: POST https://api.linkedin.com/v2/ugcPosts
  - Payload format:
      {
        "author": "urn:li:person:{id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
          "com.linkedin.ugc.ShareContent": {
            "shareCommentary": { "text": text },
            "shareMediaCategory": "NONE"
          }
        },
        "visibility": { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
      }
  - Store post_id and timestamp to DB on success

Config needed in .env:
  LINKEDIN_ACCESS_TOKEN=
  LINKEDIN_PERSON_ID=

Error handling:
  - On 401: log token expiry, halt LinkedIn publishing, alert via console
  - On 429: log and skip, resume next scheduled run

---

### 4. engagement_tracker.py

Purpose: Track performance of published posts. Store metrics to DB.

For X:
  - Free tier does NOT support reading tweet metrics
  - Store what is available: post_id, timestamp, platform
  - Future: upgrade to Basic tier ($200/mo) to unlock metrics

For LinkedIn:
  - Use GET https://api.linkedin.com/v2/socialActions/{postId}
  - Fetch: numLikes, numComments
  - Store to post_metrics table

Run schedule: Once daily, 6 hours after last publish window

---

### 5. lead_logger.py

Purpose: Log users who engage with posts as potential leads.

For LinkedIn:
  - GET https://api.linkedin.com/v2/socialActions/{postId}/likes
  - GET https://api.linkedin.com/v2/socialActions/{postId}/comments
  - For each user: store name, profile URL, post_id, action_type, timestamp

For X:
  - Not available on free tier
  - Leave as stub, implement when API tier is upgraded

Output:
  - leads table in PostgreSQL
  - Columns: id, name, profile_url, platform, post_id, action, created_at

---

## Database schema

Table: posts
  id            UUID PRIMARY KEY
  platform      VARCHAR(20)   -- "x" | "linkedin"
  content       TEXT
  post_id       VARCHAR(100)  -- platform-assigned ID
  published_at  TIMESTAMP
  status        VARCHAR(20)   -- "published" | "failed" | "pending"

Table: post_metrics
  id            UUID PRIMARY KEY
  post_id       UUID REFERENCES posts(id)
  likes         INT DEFAULT 0
  comments      INT DEFAULT 0
  checked_at    TIMESTAMP

Table: leads
  id            UUID PRIMARY KEY
  name          VARCHAR(200)
  profile_url   TEXT
  platform      VARCHAR(20)
  post_id       UUID REFERENCES posts(id)
  action        VARCHAR(50)   -- "like" | "comment"
  created_at    TIMESTAMP

Table: topics
  id            UUID PRIMARY KEY
  topic         TEXT
  platform      VARCHAR(20)
  tone          VARCHAR(20)
  active        BOOLEAN DEFAULT TRUE
  created_at    TIMESTAMP

---

## Scheduler (scheduler.py)

Use APScheduler with BackgroundScheduler.

Jobs:
  1. generate_and_publish_x
     Schedule: Every day at 09:00 WAT (08:00 UTC)
     Action: Pick random active topic from DB → generate X post → publish

  2. generate_and_publish_linkedin
     Schedule: Every day at 10:00 WAT (09:00 UTC)
     Action: Pick random active topic from DB → generate LinkedIn post → publish

  3. track_engagement
     Schedule: Every day at 16:00 WAT (15:00 UTC)
     Action: Run engagement_tracker for all posts from last 7 days

  4. log_leads
     Schedule: Every day at 17:00 WAT (16:00 UTC)
     Action: Run lead_logger for all posts from last 7 days

All jobs:
  - Wrapped in try/except
  - Failures logged, never crash the scheduler

---

## FastAPI endpoints (main.py)

GET  /health                  — Returns {"status": "ok"}
GET  /posts                   — List all published posts
GET  /leads                   — List all logged leads
POST /topics                  — Add a new topic
PUT  /topics/{id}/toggle      — Activate or deactivate a topic
POST /publish/now             — Manually trigger a publish cycle (admin)

All endpoints require a simple API key header:
  X-API-Key: {ADMIN_API_KEY from .env}

---

## Environment variables (.env)

OPENROUTER_API_KEY=
OPENROUTER_MODEL=mistralai/mistral-7b-instruct

X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

LINKEDIN_ACCESS_TOKEN=
LINKEDIN_PERSON_ID=

DATABASE_URL=postgresql://user:pass@host:5432/dbname

ADMIN_API_KEY=

TIMEZONE=Africa/Lagos

---

## Build order

1. Set up FastAPI skeleton + DB connection + models
2. Build content_generator.py and test with OpenRouter
3. Build x_publisher.py and test with a real post
4. Build linkedin_publisher.py and test with a real post
5. Wire scheduler.py with jobs 1 and 2
6. Add topics table + POST /topics endpoint
7. Build engagement_tracker.py
8. Build lead_logger.py
9. Wire scheduler jobs 3 and 4
10. Add GET /leads and GET /posts endpoints
11. Deploy to Railway
12. Add 5 starter topics and verify first automated run

---

## Key constraints

- Never use paid APIs at MVP stage
- Never hardcode API keys — always use .env
- Never let one module failure crash the whole scheduler
- Keep each module under 150 lines — single responsibility only
- Log every publish, every failure, every lead to DB
- Timezone for all scheduling: Africa/Lagos (WAT, UTC+1)

---

## Future modules (post-MVP)

- slack_publisher.py — post to relevant Slack communities via webhooks
- analytics_dashboard.py — simple HTML dashboard showing post performance
- multi_account.py — support multiple X/LinkedIn accounts (SaaS feature)
- webhook_alerts.py — ping owner on Telegram/WhatsApp when a lead is logged
