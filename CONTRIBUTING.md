# Contributing — PolyMind v2

## How to add an agent
1. Create `backend/agents/my_agent.py`:
```python
from backend.agents.base import BaseAgent
class MyAgent(BaseAgent):
    name = "my_agent"
    allowed_tools = ["read_file", "run_linter"]
    system_file = "my_agent.system.md"
    def focus(self): return "what I look for"
```
2. Add `backend/prompts/my_agent.system.md` (focus + rules + JSON reminder is auto-appended).
3. Register in `backend/engine.py` (`self.agents.append(MyAgent(...))`).
4. Add a unit test in `tests/unit/test_council.py` asserting ≥1 valid claim on the fixture diff.
5. Run `pytest -q` and `ruff check backend`.

## Dev loop
`pip install -r requirements.txt` · `uvicorn backend.main:app --reload` · `pytest -q` · `python -m eval.run`
