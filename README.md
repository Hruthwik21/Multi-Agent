# PolyMind 🧠

> A multi-AI model collaborative discussion platform — where a query is debated by specialized AI agents before producing the best possible synthesized answer.

![PolyMind Platform](https://img.shields.io/badge/Powered%20By-Google%20Antigravity%20SDK-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What is PolyMind?

PolyMind is a platform where **4 specialized AI agents** collaboratively discuss any query you submit — in real-time — before a final synthesizer produces the definitive answer.

```
User Query
    │
    ▼
[Analyst 🔍] → breaks down the problem
[Critic  ⚡] → challenges assumptions
[Expert  📚] → provides domain knowledge
    │ (2 debate rounds)
    ▼
[Synthesizer ✨] → best possible final answer
```

Works for **any kind of query**:
- 🧑‍💻 Code: "Write a function to detect balanced parentheses"
- 🔬 Facts: "What caused the fall of the Roman Empire?"
- 🎓 Quiz: "Explain the Monty Hall problem and the correct solution"
- 💡 Ideas: "How would you design a scalable notification system?"

---

## Architecture

| Layer | Technology |
|---|---|
| AI Orchestration | Google Antigravity (AGY) SDK |
| AI Models | Google Gemini (via AGY) |
| Backend | Python FastAPI + asyncio |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla HTML + CSS + JS |

### Discussion Flow

1. **Round 1 (Initial)** — Analyst, Critic, and Expert each give their first perspective
2. **Round 2 (Cross-examination)** — Each agent reads the previous round and refines their view
3. **Synthesis** — The Synthesizer reads all rounds and produces the final answer

---

## Setup

### Prerequisites
- Python 3.11+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/api-keys)

### 1. Clone the repo
```bash
git clone https://github.com/Hruthwik21/PolyMind.git
cd PolyMind
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure your API key
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

### 5. Run the backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 6. Open the frontend
Open your browser and go to:
```
http://localhost:8000
```

That's it! Type your query and watch the discussion unfold.

---

## Project Structure

```
PolyMind/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app (API endpoints + SSE)
│   ├── discussion_engine.py # Core multi-agent discussion loop
│   ├── models.py            # Pydantic data models
│   └── agents/
│       ├── __init__.py
│       ├── analyst.py       # Analyst persona
│       ├── critic.py        # Critic persona
│       ├── expert.py        # Expert persona
│       └── synthesizer.py   # Synthesizer persona
├── frontend/
│   ├── index.html           # Main UI
│   ├── styles.css           # Dark glassmorphism design
│   └── app.js               # SSE client + rendering
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

### `POST /api/discuss`
Start a discussion session.

**Request body:**
```json
{
  "query": "What is the Monty Hall problem?",
  "rounds": 2
}
```

**Response:**
```json
{
  "session_id": "abc-123",
  "query": "...",
  "rounds": 2,
  "stream_url": "/api/stream/abc-123"
}
```

### `GET /api/stream/{session_id}`
SSE stream of agent messages. Each event is:
```
event: agent_message
data: {"agent": "analyst", "agent_name": "Analyst", "content": "...", "round": 0}

event: done
data: {"session_id": "abc-123"}
```

### `GET /health`
Health check — verifies API key is configured.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Your Gemini API key |
| `DISCUSSION_ROUNDS` | No | Default rounds (2) |
| `HOST` | No | Server host (localhost) |
| `PORT` | No | Server port (8000) |

---

## Contributing

Pull requests are welcome! To add a new agent persona:
1. Create `backend/agents/your_agent.py` following the existing pattern
2. Add it to `backend/agents/__init__.py`
3. Integrate it into `discussion_engine.py`

---

## License

MIT © [Hruthwik21](https://github.com/Hruthwik21)
