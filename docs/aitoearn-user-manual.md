# AiToEarn — User Manual

> **Version**: based on AiToEarn v2.5.x (open-source edition, [github.com/yikart/AiToEarn](https://github.com/yikart/AiToEarn))
> **Last updated**: 2026-07-25
> The installation steps in this manual were executed and verified end-to-end on a Linux host with Docker 29.x and Node.js 22.

---

## Table of Contents

1. [What is AiToEarn?](#1-what-is-aitoearn)
2. [Choosing How to Use AiToEarn](#2-choosing-how-to-use-aitoearn)
3. [Getting an API Key](#3-getting-an-api-key)
4. [Installation — Docker One-Click Deploy (Recommended)](#4-installation--docker-one-click-deploy-recommended)
5. [First Login](#5-first-login)
6. [Configuration](#6-configuration)
7. [Using the Web App — Feature Walkthrough](#7-using-the-web-app--feature-walkthrough)
8. [Using AiToEarn from Claude, Cursor & Other AI Assistants (MCP)](#8-using-aitoearn-from-claude-cursor--other-ai-assistants-mcp)
9. [Using AiToEarn in OpenClaw](#9-using-aitoearn-in-openclaw)
10. [Running from Source (Developers)](#10-running-from-source-developers)
11. [Day-2 Operations](#11-day-2-operations)
12. [Troubleshooting](#12-troubleshooting)
13. [Resources & Support](#13-resources--support)

---

## 1. What is AiToEarn?

AiToEarn is an open-source (MIT-licensed) **AI agent platform for content marketing**. Its motto is:

> **Monetize · Publish · Engage · Create — all in one platform.**

It helps one-person companies (OPCs), creators, brands, and marketing teams build, distribute, and monetize content with AI-powered automation across the world's most popular social platforms.

### Supported publishing channels

Douyin, Xiaohongshu (Rednote), Kuaishou, Bilibili, WeChat Channels, WeChat Official Accounts, TikTok, YouTube, Facebook, Instagram, Threads, X (Twitter), Pinterest, and LinkedIn.

### The four core capabilities

| Capability | What it does |
|---|---|
| 💰 **Monetize** | Sell content / complete brand promotion tasks. Results-driven settlement models: **CPS** (Cost Per Sale), **CPE** (Cost Per Engagement), **CPM** (Cost Per Mille / views). |
| 📢 **Publish** | One-click distribution of the same content to 10+ platforms, plus a **calendar scheduler** to plan posts across accounts. |
| 💬 **Engage** | Automated engagement via the AiToEarn browser extension: auto-like/bookmark/follow, AI smart replies to comments, comment mining (detects buying signals like "link please"), and brand monitoring. |
| 🎨 **Create** | A Content Agent that goes from idea to finished product: video generation (Grok, Veo, Seedance, …), image generation (e.g. Nano Banana), batch generation for matrix-account operations. |

### Key concept: the Content Agent

The heart of the product is the **Content Agent** — a configurable AI creator that closes the full loop of *create → adapt to each platform → publish → analyze → monetize*. You bind your social accounts once, then an Agent can keep working with them: generating drafts, adapting them per platform, scheduling and publishing.

---

## 2. Choosing How to Use AiToEarn

There are five ways to use AiToEarn. Pick the one that fits you:

| # | Option | Best for | Deployment needed? |
|---|--------|----------|--------------------|
| ① | **Hosted website** — [aitoearn.ai](https://aitoearn.ai/) (international) or [aitoearn.cn](https://aitoearn.cn/) (China) | Everyone | ❌ No |
| ② | **OpenClaw plugin** | OpenClaw users | ❌ No |
| ③ | **MCP in Claude / Cursor / any AI assistant** | AI-tool users | ❌ No |
| ④ | **Docker one-click self-host** | Teams wanting their own instance | ✅ A server |
| ⑤ | **Build from source** | Developers / contributors | ✅ Dev environment |

> 💡 Options ②, ③ and ④ require an **API Key** first — see the next section. You only need to create it once.

---

## 3. Getting an API Key

1. Open [aitoearn.ai](https://aitoearn.ai/) (international) or [aitoearn.cn](https://aitoearn.cn/) (China), sign up, and log in.
2. Click **Settings** in the left menu.
3. Open the **API Key** tab, click **Create**, and copy the generated key (keys are prefixed `ai_`).

⚠️ **Important**
- Keep the key secret — anyone holding it can act on your account.
- **Keys are environment-bound.** A key created on `aitoearn.cn` only works against `https://aitoearn.cn/api`, and a key from `aitoearn.ai` only works against `https://aitoearn.ai/api`. Mixing them up returns **HTTP 401**.

---

## 4. Installation — Docker One-Click Deploy (Recommended)

This is the fastest way to run a complete, self-hosted AiToEarn. No manual database setup is needed.

### 4.1 Prerequisites

| Requirement | Minimum |
|---|---|
| Docker | 20.10+ (with the Compose v2 plugin, 2.0+) |
| RAM | 4 GB+ recommended |
| Disk | 20 GB+ recommended (the images alone total roughly 4–5 GB) |
| Free ports | **8080** (web UI), **9000** (file uploads), and 27017 / 6379 / 9001 for MongoDB / Redis / RustFS console |

Verify Docker is working:

```bash
docker --version
docker compose version
docker info        # must succeed — if it errors, the Docker daemon isn't running
```

### 4.2 Install in three commands

```bash
git clone https://github.com/yikart/AiToEarn.git
cd AiToEarn
docker compose up -d
```

The first start pulls all images (≈ 4–5 GB) — expect a few minutes depending on your connection.

### 4.3 What gets installed

`docker compose up -d` starts this stack:

```
                         ┌──────────┐
                         │  Nginx   │
                         │  :8080   │
                         └────┬─────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────┴─────┐  ┌─────┴──────┐  ┌─────┴─────┐
        │  Web (FE) │  │  Server    │  │  AI       │
        │  :3000    │  │  :3002     │  │  :3010    │
        └───────────┘  └──────┬─────┘  └─────┬─────┘
                              │              │
                 ┌────────────┼──────────────┤
                 │            │              │
            ┌────┴─────┐ ┌───┴────┐  ┌──────┴───┐
            │ MongoDB  │ │ Redis  │  │  RustFS  │
            │ :27017   │ │ :6379  │  │ :9000/01 │
            └──────────┘ └────────┘  └──────────┘
```

| Service (container) | Role | Port |
|---|---|---|
| `aitoearn-nginx` | Reverse proxy — the single public entry point | **8080** (UI + API), **9000** (S3 upload proxy) |
| `aitoearn-web` | Next.js frontend | 3000 (internal) |
| `aitoearn-server` | NestJS main backend API | 3002 (internal) |
| `aitoearn-ai` | NestJS AI service (models, agent, draft generation) | 3010 (internal) |
| `aitoearn-mongodb` | MongoDB database (started as a single-node replica set) | 27017 |
| `aitoearn-redis` | Cache / queues (default password: `password`) | 6379 |
| `aitoearn-rustfs` | S3-compatible object storage for media files | 9000 (API) / 9001 (console) |
| `aitoearn-mongodb-rs-init` | One-shot job: initializes the MongoDB replica set, then exits | — |
| `aitoearn-rustfs-init` | One-shot job: creates the `aitoearn` bucket, then exits | — |
| `aitoearn-init` | One-shot job: creates the default admin user and an auto-login token, then exits | — |

Nginx routes requests as follows: `/` → web frontend, `/api/ai/` and `/api/agent/` → AI service, `/api/` → main server, `/oss/` → object storage (read), and port `9000` proxies browser file uploads to RustFS.

### 4.4 Verify the installation

```bash
docker compose ps
```

All long-running services should be `Up (healthy)`; the three `*-init` jobs should show `Exited (0)`. A verified healthy deployment looks like this:

```
aitoearn-nginx     Up (healthy)
aitoearn-web       Up (healthy)
aitoearn-server    Up (healthy)
aitoearn-ai        Up (healthy)
aitoearn-mongodb   Up (healthy)
aitoearn-redis     Up (healthy)
aitoearn-rustfs    Up (healthy)
aitoearn-init            Exited (0)
aitoearn-mongodb-rs-init Exited (0)
aitoearn-rustfs-init     Exited (0)
```

Then open **<http://localhost:8080>** in your browser. A quick command-line check:

```bash
curl -s http://localhost:8080/_nhealth   # → "healthy"
```

This is what a freshly deployed instance looks like after auto-login (Content Management home):

![AiToEarn home after first start](images/aitoearn-home.png)

---

## 5. First Login

You don't need to register on a self-hosted instance. On first startup the `aitoearn-init` job:

1. Creates a default admin user — **`admin@aitoearn.local`** (name "Admin").
2. Generates a JWT auto-login token and stores it on a shared Docker volume.
3. The web frontend reads that token and **logs you in automatically** when you open <http://localhost:8080>.

> 🔒 **Security note:** the default JWT secret is `change-this-jwt-secret`, MongoDB uses `admin`/`password`, Redis uses `password`, and RustFS uses `rustfsadmin`/`rustfsadmin`. This is fine on a laptop; **change all of these before exposing the instance to the internet** (see [§6.4](#64-config-files-on-disk) and [§11](#11-day-2-operations)).

---

## 6. Configuration

### 6.1 The Configuration UI

Open the deployed UI → **Configuration** (bottom of the left sidebar). This dialog edits the two backend YAML config files live (they are mounted read-write into the containers). It has two tabs — **Server** and **AI service** — and buttons to **Reload**, **Validate**, **Save**, and **Restart service**.

![Configuration dialog](images/aitoearn-config.png)

Settings are grouped into sections such as:

- **Relay** — service relay, API key, callback and AI-relay outbound settings
- **Basic** — runtime mode, port, API prefix, logging, OpenAPI
- **Database / Redis & locks** — MongoDB, Redis, queue and distributed-lock settings
- **Auth & security** — login, tokens, API-key settings
- **File storage** — object storage, uploads
- **AI service / Model providers / Model catalog / Draft generation** — provider keys and base URLs (OpenAI, Volcengine, Grok, DashScope, Gemini, Anthropic), model capabilities and defaults
- **Agent** — agent endpoint, model list, default/thinking models, task timeouts
- **Channels** — per-platform publishing settings (client IDs, secrets, callbacks)

After editing, click **Save** and then **Restart service** so the affected service reloads the configuration.

### 6.2 Configure Relay (strongly recommended)

**Why?** Publishing requires OAuth-authorizing your social accounts (TikTok, Instagram, YouTube, …). Each platform normally demands its own developer application with a `client_id`/`client_secret` — very tedious to set up yourself. **Relay** lets your self-hosted instance use the official aitoearn.ai credentials instead, so one API Key authorizes every platform.

1. Get an API Key from the hosted service ([§3](#3-getting-an-api-key)).
2. In your self-hosted UI, open **Configuration**.
3. **Server tab → Relay** — set the **Server URL** and your **API key**; the **Callback URL** points back at your instance (e.g. `http://localhost:8080/api/v2/channels/relay/callback`). This enables content publishing and social-platform OAuth authorization.
4. **AI service tab → Relay** — (optional) lets you use AI models provided by the platform instead of bringing your own keys.
5. Use the Server URL that matches your key: China keys → `https://aitoearn.cn/api`, international keys → `https://aitoearn.ai/api`. A mismatch returns 401.
6. Click **Save**, then **Restart service**.

Once Relay is configured, the **Channels** section is flagged "Not recommended" for manual editing — the relay supplies platform credentials for you.

### 6.3 Bring your own AI keys (alternative to AI Relay)

Under **Configuration → AI → Model providers** you can enter your own API keys and base URLs for OpenAI, Gemini, Anthropic, Volcengine, Grok, DashScope, etc. The **Model catalog** and **Draft generation** sections control which chat/image/video models are offered and their defaults.

### 6.4 Config files on disk

The Configuration UI writes to these files (you can also edit them directly and restart the service):

| File (in the cloned repo) | Mounted into | Purpose |
|---|---|---|
| `project/aitoearn-backend/apps/aitoearn-server/config/config.yaml` | `aitoearn-server:/app/config.yaml` | Main backend: DB/Redis/auth/storage/channel & relay settings |
| `project/aitoearn-backend/apps/aitoearn-ai/config/config.yaml` | `aitoearn-ai:/app/config.yaml` | AI service: providers, model catalog, agent settings |

Secrets you should change for production: `auth.secret` (JWT), `auth.internalToken`, MongoDB root password (also in `docker-compose.yml`), Redis password, RustFS access/secret keys.

---

## 7. Using the Web App — Feature Walkthrough

The left sidebar has five main sections — **Content Management**, **AI Publish**, **Publish**, **AI Generated Assets**, and **Task History** — plus **Configuration**, **My Channels**, and **Extension** at the bottom.

### 7.1 Content Management (Home, `/`)

The draft-creation workspace and **draft box**. At the top is a batch draft composer: upload media assets (up to 3 videos / 3 audio clips ≤ 15 s total, up to 9 images — reference them in your prompt by typing `@`), write a prompt, then pick:

- the generation mode (e.g. **Generate Draft (Video)**),
- the **target platforms** (10+ selectable at once — each platform's caption limits are enforced automatically),
- the **model** (e.g. Seedance 2.0 Fast), resolution (720p …), aspect ratio (9:16 …), duration, and batch count.

Generated drafts land in the tabs below (**All / Drafts / Video / Image**), organized in groups, with a **Generation History** view. From here you review drafts, edit captions/media, and send them onward to publishing. An **Explore more prompts** link opens the prompt gallery for inspiration.

### 7.2 AI Publish (`/ai-social`)

The conversational entry point to the **Content Agent**. Describe what you want ("make three short videos about X and post them to TikTok and YouTube tonight"), optionally pick from the **prompt gallery**, and the Agent plans the task: generating content, adapting it per platform, and preparing publishes. You can watch the task preview as it works. Each conversation/task opens in a chat view (`/chat/<taskId>`).

### 7.3 Publish (`/accounts`)

The multi-platform publishing workspace, built around a **content calendar** (week/month views, jump to Today):

![Publish calendar](images/aitoearn-publish.png)

- **Add Channels** — connect your social accounts via OAuth (or QR code for some Chinese platforms). With Relay configured this works out of the box; without Relay you must supply your own developer credentials per platform under **Configuration → Channels**. Connected accounts are managed in **My Channels** (sidebar) and filterable via the **All Channels** selector.
- **New Work** — create a post once, pick target accounts, and schedule per-platform times directly on the calendar.
- **Agent Create** — hand the slot to the Content Agent to generate the work for you.
- **Publish records & analytics** — per-account publishing history and work-level analytics.

### 7.4 AI Generated Assets (`/agent-assets`)

Reusable AI-generated assets that belong to your Agents — generated media and other resources Agents draw on when creating content.

### 7.5 Task History (`/tasks-history`)

Every Agent task you've run: status, results, and generated artifacts. Use it to re-open a past task's chat, check what was published, or debug why a task failed.

### 7.6 Extension (Engage)

The **Extension** entry in the sidebar installs the AiToEarn browser extension, which powers the Engage features: automated likes/bookmarks/follows, AI smart replies, comment mining, and brand monitoring.

### 7.7 Settings

Open **Settings** from the sidebar/user menu. Notable tabs:

- **Profile** — nickname, avatar.
- **API Key** — create keys for MCP/OpenClaw access *to your own instance*.
- **Wallet / Income / Balance** — monetization: creator income, advertiser balance, withdrawals (hosted service).
- **Credits / Bills** — usage credits and billing (hosted service).
- **General** — language (English, 中文, 日本語, 한국어, Français, Deutsch and more) and theme (light/dark).

---

## 8. Using AiToEarn from Claude, Cursor & Other AI Assistants (MCP)

AiToEarn speaks the **Model Context Protocol (MCP)**, so any MCP-compatible assistant can publish and manage content through it.

Endpoints (pick the one matching your API Key's environment):

| Environment | MCP URL | SSE URL |
|---|---|---|
| International | `https://aitoearn.ai/api/unified/mcp` | `https://aitoearn.ai/api/unified/sse` |
| China | `https://aitoearn.cn/api/unified/mcp` | `https://aitoearn.cn/api/unified/sse` |
| Self-hosted | `http://localhost:8080/api/unified/mcp` | `http://localhost:8080/api/unified/sse` |

**Claude Desktop** — edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aitoearn": {
      "type": "http",
      "url": "https://aitoearn.ai/api/unified/mcp",
      "headers": {
        "x-api-key": "your-api-key"
      }
    }
  }
}
```

**Cursor** — in MCP settings add the MCP URL and the auth header `x-api-key: your-api-key`.

**Any other MCP client** needs just those two values: the MCP URL and the `x-api-key` header.

### 8.1 Worked example (verified against a self-hosted instance)

The unified MCP endpoint exposes 35 tools covering drafts, media, AI draft generation, publishing flows, platform metadata, analytics, and engagement. This complete session was run against a local Docker deployment with `curl` — any MCP client does the same under the hood.

**1. Initialize the MCP session:**

```bash
curl -s -X POST http://localhost:8080/api/unified/mcp \
  -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"demo","version":"1.0"}}}'
# → {"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{"listChanged":true}},"serverInfo":{"name":"aitoearn","version":"1.0.0"}},...}
```

**2. Discover tools** with `{"method":"tools/list"}` — you get `createDraft`, `listDrafts`, `createVideoDraft` (AI generation), `createChannelPublishFlow`, `publishChannelTaskNow`, `getChannelAccountAnalytics`, `listChannelPlatforms`, and 28 more.

**3. Create a draft:**

```bash
curl -s -X POST http://localhost:8080/api/unified/mcp \
  -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"createDraft","arguments":{
        "groupId":"<id from getDraftGroupInfoByName>",
        "title":"5 Docker tips every developer should know",
        "desc":"Quick carousel: healthchecks, compose overrides, named volumes... #docker",
        "topics":["docker","devtips"],
        "type":"article",
        "mediaList":[{"url":"https://example.com/cover.png","type":"img"}]}}}'
# → "Draft created successfully, ID: 6a651a96b87db9cacf19e606"
```

**4. The draft immediately appears in the web UI** under Content Management:

![Draft created via MCP visible in the UI](images/aitoearn-draft-created.png)

From here the same MCP surface can send it onward — `createChannelPublishFlow` schedules it to connected accounts, and `getDraftTaskStatus` tracks AI-generation tasks kicked off with `createVideoDraft`/`createImageTextDraft` (those need AI Relay or provider keys configured, see [§6](#6-configuration)).

---

## 9. Using AiToEarn in OpenClaw

With an API Key in hand, install the OpenClaw plugin:

```bash
npx -y @aitoearn/openclaw-plugin-cli
```

On first run, choose your environment (China ↔ `aitoearn.cn` key, International ↔ `aitoearn.ai` key — a mismatch returns 401) and paste the API Key. You can then receive and execute AiToEarn earning tasks directly inside OpenClaw.

---

## 10. Running from Source (Developers)

> Requires Node.js 20.18+ (Node 22 works) and pnpm. Use Docker for MongoDB/Redis or point the configs at your own instances.

### 10.1 Backend (NestJS monorepo, Nx)

```bash
cd project/aitoearn-backend
pnpm install

# Create local config overrides
cp apps/aitoearn-ai/config/config.yaml     apps/aitoearn-ai/config/local.config.yaml
cp apps/aitoearn-server/config/config.yaml apps/aitoearn-server/config/local.config.yaml

pnpm nx serve aitoearn-ai       # AI service on :3010
# in another terminal:
pnpm nx serve aitoearn-server   # main API on :3002
```

### 10.2 Web frontend (Next.js 14, App Router)

```bash
cd project/aitoearn-web
pnpm install
pnpm run dev
```

### 10.3 Electron desktop client (separate repo)

```bash
git clone https://github.com/yikart/AttAiToEarn.git
cd AttAiToEarn
npm install
npm run rebuild    # compiles better-sqlite3 (needs node-gyp + Python)
npm run dev
```

See [CONTRIBUTING.md](https://github.com/yikart/AiToEarn/blob/main/CONTRIBUTING.md) before opening pull requests.

---

## 11. Day-2 Operations

All commands run from the cloned `AiToEarn` directory.

| Task | Command |
|---|---|
| Check status | `docker compose ps` |
| Follow logs (all / one service) | `docker compose logs -f` / `docker compose logs -f aitoearn-server` |
| Restart one service (e.g. after config edit) | `docker compose restart aitoearn-server` |
| Stop everything (keep data) | `docker compose down` |
| Stop and **delete all data** | `docker compose down -v` ⚠️ removes MongoDB/Redis/RustFS volumes |
| Update to latest images | `docker compose pull && docker compose up -d` (app images use `pull_policy: always`, so a plain `up -d` also refreshes them) |
| Back up the database | `docker exec aitoearn-mongodb mongodump --uri "mongodb://admin:password@localhost:27017/?authSource=admin" --archive > backup.dump` |

Data lives in named Docker volumes: `mongodb-data`, `mongodb-config`, `redis-data`, `rustfs-data`, `init-data`.

---

## 12. Troubleshooting

**`docker compose up` fails with "cannot connect to the Docker daemon"**
The Docker daemon isn't running. Start Docker Desktop, or on Linux `sudo systemctl start docker` (verified: once the daemon is up, the same `docker compose up -d` succeeds).

**HTTP 401 when configuring Relay / MCP / OpenClaw**
Your API Key and environment don't match. `aitoearn.cn` keys work only with `https://aitoearn.cn/api`; `aitoearn.ai` keys only with `https://aitoearn.ai/api`.

**Port 8080 (or 9000/27017/6379) already in use**
Edit the `ports:` mappings in `docker-compose.yml` (e.g. change `"8080:80"` to `"8081:80"`) and run `docker compose up -d` again.

**`aitoearn-web` exits with "AUTO_LOGIN_TOKEN is missing"**
The init job didn't complete. Check `docker compose logs aitoearn-init`, fix the cause (usually MongoDB not healthy yet), then `docker compose up -d` again.

**`aitoearn-init` exits with code 1 behind a corporate / TLS-intercepting proxy**
The init job runs `npm install` inside a container; if your network intercepts TLS with a custom CA, that install fails certificate verification. Fix by giving the container your CA bundle via a `docker-compose.override.yml` (verified working):

```yaml
services:
  aitoearn-init:
    volumes:
      - /path/to/your/ca-bundle.crt:/etc/ssl/certs/corp-ca.crt:ro
    environment:
      NODE_EXTRA_CA_CERTS: /etc/ssl/certs/corp-ca.crt
      npm_config_cafile: /etc/ssl/certs/corp-ca.crt
```

Then `docker compose up -d` again.

**`aitoearn-nginx` keeps restarting with `socket() [::]:80 failed (97: Address family not supported by protocol)`**
Your host has IPv6 disabled. Remove the two `listen [::]:…` lines from `nginx/nginx.conf` (or mount a patched copy via `docker-compose.override.yml`) and run `docker compose up -d nginx` (verified working).

**Web UI loads but publishing/authorization fails**
Most likely Relay isn't configured — see [§6.2](#62-configure-relay-strongly-recommended). Without Relay you need your own per-platform developer credentials under **Configuration → Channels**.

**AI generation fails**
Configure either **AI → Relay** or your own provider keys under **AI → Model providers**, then **Save** and **Restart service** on the AI service tab.

**A service is `unhealthy` or restarting**
`docker compose logs -f <service>` shows why. Common causes: not enough RAM (MongoDB + both Node backends want ~4 GB total) or a corrupted config.yaml after manual edits.

**Slow first startup**
Normal — the stack waits for health checks in dependency order (MongoDB → Redis/RustFS → AI → Server → init → Web → Nginx). Two to three minutes on first boot is typical after the image pull.

---

## 13. Resources & Support

- **Official docs / help center**: <https://docs.aitoearn.ai/>
- **Website**: <https://aitoearn.ai/> (international) · <https://aitoearn.cn/> (China)
- **Source code**: <https://github.com/yikart/AiToEarn> (MIT license)
- **Releases / changelog**: <https://github.com/yikart/AiToEarn/releases>
- **Issues**: <https://github.com/yikart/AiToEarn/issues> — open an issue first for any problem so the team can track it
- **Telegram**: <https://t.me/harryyyy2025>
- **Demo videos**: [Publish](https://www.youtube.com/watch?v=5041jEKaiU8) · [Engage](https://youtu.be/-QoHNrZBmp0) · [Create](https://youtu.be/y900LxIrZT4)
- Docker deployment reference in the repo: [`DOCKER_DEPLOYMENT_EN.md`](https://github.com/yikart/AiToEarn/blob/main/DOCKER_DEPLOYMENT_EN.md)
