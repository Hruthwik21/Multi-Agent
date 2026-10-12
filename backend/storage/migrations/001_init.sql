-- PolyMind SQLite migrations (simple SQL; alembic optional for Postgres prod)
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, html TEXT NOT NULL);
