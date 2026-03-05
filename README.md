## Semantic Auto Mapper

**Goal**: map business glossary terms and physical data attributes (including acronym-heavy column names) using semantic-ish matching, with human-in-the-loop approval / rejection and lightweight reinforcement from feedback.

### Stack

- **Backend**: FastAPI, SQLite, SQLAlchemy
- **Frontend**: Static HTML + vanilla JS (no build step)
- **Tests**: pytest unit tests for the matching engine

### Layout

- `backend/app/main.py` – FastAPI app, API routes, static frontend wiring
- `backend/app/matching.py` – normalization, acronym expansion, similarity scoring, feedback adjustment
- `backend/app/models.py` – ORM models for mappings and feedback
- `backend/app/schemas.py` – Pydantic request/response models
- `backend/app/database.py` – SQLite engine + session factory
- `backend/tests/test_matching.py` – unit tests for core matching behaviour
- `frontend/index.html` – main UI
- `frontend/widget.html` – compact iframe-friendly widget UI

Running the API (from project root):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/` for the main UI, or embed the widget in another app:

```html
<iframe
  src="http://localhost:8000/widget"
  style="width: 100%; height: 480px; border: 0; border-radius: 12px;"
></iframe>
```

### Bitbucket / GitHub

Git has been initialized with `origin` set to `https://github.com/ashwinmohan81/AutoMapper.git`. Once you’re happy with the initial version:

```bash
git add .
git commit -m "Initial semantic auto mapper scaffold"
git push -u origin main
```

