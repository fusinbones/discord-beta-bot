
# 🧠 Jim the Mentor — Windsurf Project Spec

## 📌 Project Summary
This project upgrades the Jim Discord bot into a full-fledged AI mentor for resellers using:
- Claude + Firecrawl via MCP for listing analysis
- Persistent user memory
- Mentorship onboarding
- Discord-only interaction
- ElevenLabs voice messages
- AI image editing tools (OpenAI, Replicate, Clipping Magic)

## 🔧 Required API Keys (Env Vars)
```env
CLAUDE_API_KEY=
FIRECRAWL_MCP_URL=
FIRECRAWL_AUTH_TOKEN=
ELEVENLABS_API_KEY=
OPENAI_API_KEY=
REPLICATE_API_KEY=
CLIPPING_MAGIC_API_ID=
CLIPPING_MAGIC_API_SECRET=
GOOGLE_API_KEY=
CANVA_API_KEY= (optional)
```

## ⚙️ Features to Implement

### 1. `!mentor` Command (Discord)
- Trigger onboarding DM from Jim
- Store user profile with:
  - Discord ID
  - Reseller store URLs (Poshmark, eBay, Mercari, etc.)
  - Timeframe (1/2/3 months)
  - Main goal (e.g. revenue, items sold, daily listings)
- Save this info to persistent memory (MongoDB, Supabase, etc.)

### 2. Onboarding Flow in DM
- Casual, emotional tone
- Questions to ask:
  - “What’s your dream outcome with reselling?”
  - “How fast do you want to hit that goal — 1, 2, or 3 months?”
  - “Send me your store links so I can dig in.”

### 3. Firecrawl + Claude Analysis
- Use Claude Sonnet 4 + Firecrawl MCP connector
- For each store URL, crawl active and sold listings
- Claude analyzes:
  - Pricing strategies
  - Photo quality
  - Title optimization
  - Competitor comparisons
- Format into a helpful, personal summary from Jim

### 4. Persistent User Memory
- Store and recall:
  - Name/nickname
  - Store URLs
  - Goals
  - Past activity
  - Wins and struggles
- Auto-load this memory for future sessions

### 5. Voice Drops (Optional)
- Use ElevenLabs to generate motivational or check-in audio
- Trigger randomly or on specific actions (e.g., sale, slump)
- Play through Discord with `ffmpeg` or attach as MP3

### 6. Visual Assistance
- Let users upload listing images
- Jim can:
  - Remove background (Clipping Magic)
  - Improve image quality (Replicate)
  - Generate new stock photos (OpenAI DALL·E)
- Let users type prompts like:
  - `!photoedit remove background`
  - `!photoedit add white backdrop`
  - `!generate “plus size woman wearing floral maxi dress on a beach”`

### 7. Daily + Weekly Interaction
- Schedule check-ins via DMs:
  - “What are we listing today?”
  - “You’re 4 days from your goal — let’s lock in!”
- Use cron or job queues

### 8. Jim’s Personality Prompt (for Claude)
- Casual, witty, emotionally tuned
- Supportive but holds the user accountable
- Example system message:

```
You are Jim, an AI mentor and friend to resellers. You speak casually but insightfully, always focused on helping the user grow their business. You remember everything about them, give direct advice with kindness, and gently call them out when they need it.
```

## ✅ Optional Features for Future Sprints
- `!vault` command to deliver PDF checklists and templates
- Leaderboard or anonymous challenge mode
- Weekly “BOLO” alerts from Firecrawl
- `!overwhelm` command to help users break through decision fatigue

## 📁 File Structure Example
```
/jim-discord-bot
│
├── /commands
│   ├── mentor.js (or mentor.py)
│   ├── photoedit.js
│
├── /services
│   ├── firecrawlClaude.js
│   ├── elevenLabs.js
│   ├── replicateTools.js
│
├── /memory
│   ├── userProfileStore.js
│
├── .env
├── index.js
└── README.md
```
