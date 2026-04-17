# Content Learning Guide Agent

An AI-powered agent that analyses YouTube channels and guides users through the content as a personalised, structured learning path — like having a tutor who knows every video on the channel.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 Channel Analysis | Paste a YouTube channel URL; the agent fetches all videos, transcripts and metadata |
| 🧠 Topic Discovery | GPT-4o automatically clusters videos into topics/modules |
| 🗺️ Learning Paths | Get an ordered, beginner-to-advanced watchlist for any topic |
| 💬 Chat Interface | ChatGPT-style conversational UI with session memory |
| 📹 Video Cards | Rich video cards with thumbnails, titles and direct links |
| ⚡ Semantic Search | Ask anything; the agent searches across all video content using vector embeddings |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              Next.js Frontend               │
│  (Chat UI · Sidebar Topics · Video Cards)   │
└────────────────────┬────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────┐
│            FastAPI Backend                  │
│                                             │
│  fetcher.py   → YouTube Data API v3         │
│                 youtube-transcript-api      │
│                                             │
│  embeddings.py → OpenAI text-embedding-3   │
│                  ChromaDB (vector store)    │
│                                             │
│  agent.py     → GPT-4o (RAG + chat memory) │
└─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py           # FastAPI routes
│   ├── fetcher.py        # YouTube data collection
│   ├── embeddings.py     # ChromaDB embedding pipeline
│   ├── agent.py          # RAG chat agent + topic analysis
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Main page (channel input + chat)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx  # Message list with video card parsing
│   │   │   ├── ChatInput.tsx   # Auto-resizing textarea
│   │   │   ├── Sidebar.tsx     # Topics + learning paths
│   │   │   └── VideoCard.tsx   # Thumbnail + title + link card
│   │   └── lib/
│   │       └── api.ts          # Axios API client
│   ├── Dockerfile
│   └── package.json
│
└── docker-compose.yml
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key ([platform.openai.com](https://platform.openai.com))
- YouTube Data API v3 key ([console.cloud.google.com](https://console.cloud.google.com))

### 1. Clone and set up environment variables

```bash
git clone <repo-url>
cd <repo-dir>

# Backend
cp backend/.env.example backend/.env
# Edit backend/.env and fill in your API keys

# Frontend
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local if your backend runs on a different port
```

### 2a. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 2b. Run manually

**Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Getting Your API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy and paste into `backend/.env` as `OPENAI_API_KEY=sk-...`

### YouTube Data API v3 Key
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable **YouTube Data API v3** in the API Library
4. Go to **Credentials** → **Create Credentials** → **API key**
5. Copy and paste into `backend/.env` as `YOUTUBE_API_KEY=AIza...`

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyse` | Start indexing a YouTube channel |
| GET | `/status/{channel_id}` | Poll indexing progress |
| GET | `/topics/{channel_id}` | Get discovered topic clusters |
| POST | `/learning-path` | Get ordered learning path for a topic |
| POST | `/search` | Semantic search across channel content |
| POST | `/chat` | Chat with the agent |
| DELETE | `/session/{session_id}` | Clear conversation history |
| GET | `/videos/{channel_id}` | List all indexed videos |

Full interactive docs at http://localhost:8000/docs

---

## 💡 Usage Guide

1. **Open** http://localhost:3000
2. **Paste** a YouTube channel URL (e.g. `https://www.youtube.com/@channelname`)
3. **Click Analyse** — the agent fetches all videos in the background (takes 1–10 min depending on channel size)
4. Once ready, **topics appear** in the left sidebar
5. **Click a topic** to see an ordered learning path, or **chat** directly:
   - *"What topics does this channel cover?"*
   - *"I'm a beginner at Python. Where should I start?"*
   - *"Show me the top 5 most popular videos"*
   - *"Give me a 1-week learning plan for machine learning"*

---

## 🔮 Roadmap (v2)

- [ ] Instagram / TikTok profile support
- [ ] User accounts with saved learning progress
- [ ] Quiz generation from video transcripts
- [ ] Progress tracking (mark videos as watched)
- [ ] Email/notification reminders
- [ ] Playlist import
- [ ] Mobile app (React Native)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn |
| AI / LLM | OpenAI GPT-4o (chat + topic analysis) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (local persistent) |
| YouTube | YouTube Data API v3 + youtube-transcript-api |
| Deployment | Docker Compose / Vercel + Railway |
