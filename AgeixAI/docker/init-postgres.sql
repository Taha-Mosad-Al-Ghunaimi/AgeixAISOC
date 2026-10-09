-- AgeixAISOC — PostgreSQL pgvector bootstrap
-- Runs once on first container start (volume creation).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
