CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  file_name TEXT NOT NULL,
  doc_type TEXT,
  classification TEXT,
  organization TEXT,
  hash_sum TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL,
  upload_date TIMESTAMPTZ NOT NULL,
  size_bytes BIGINT NOT NULL,
  lang TEXT,
  step TEXT,
  error TEXT,
  neo4j_synced BOOLEAN,
  graph_nodes INTEGER,
  graph_relationships INTEGER,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS confidence_weights (
  component TEXT PRIMARY KEY,
  weight DOUBLE PRECISION NOT NULL CHECK (weight >= 0)
);

CREATE TABLE IF NOT EXISTS source_reliability_config (
  doc_type TEXT PRIMARY KEY,
  reliability DOUBLE PRECISION NOT NULL CHECK (reliability >= 0 AND reliability <= 1)
);

INSERT INTO confidence_weights (component, weight) VALUES
  ('source_reliability', 0.30),
  ('extraction_confidence', 0.25),
  ('corroboration', 0.20),
  ('consistency', 0.15),
  ('recency', 0.10)
ON CONFLICT (component) DO NOTHING;

    INSERT INTO source_reliability_config (doc_type, reliability) VALUES
      ('статья', 0.90),
      ('патент', 0.80),
      ('диссертация', 0.80),
      ('книга', 0.75),
      ('отчёт', 0.70),
      ('отчёт_черновой', 0.50),
      ('препринт', 0.40)
    ON CONFLICT (doc_type) DO NOTHING;

    CREATE TABLE IF NOT EXISTS runtime_config (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    INSERT INTO runtime_config (key, value) VALUES
      ('llm_model', 'yandexgpt-5.1'),
      ('ocr_model', 'markdown')
    ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS mkg_users (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'team',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  author_id TEXT,
  author_name TEXT NOT NULL,
  author_role TEXT NOT NULL,
  body TEXT NOT NULL,
  msg_type TEXT NOT NULL DEFAULT 'user',
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_thread_idx ON chat_messages(thread_id, created_at);
