CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name     VARCHAR(120) NOT NULL,
  email         VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS design_styles (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(60) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       VARCHAR(80) NOT NULL,
  room_type  VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS remodel_requests (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id            UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  style_id           INT REFERENCES design_styles(id),
  original_image_url TEXT NOT NULL,
  budget             NUMERIC(10, 2),
  status             VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS remodel_results (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id          UUID NOT NULL REFERENCES remodel_requests(id) ON DELETE CASCADE,
  generated_image_url TEXT,
  suggestions         JSONB NOT NULL DEFAULT '[]',
  ai_provider         VARCHAR(40) NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO design_styles (name, description) VALUES
  ('modern', 'Líneas limpias, colores neutros y pocos objetos'),
  ('nordic', 'Madera clara, blanco y mucha luz natural'),
  ('industrial', 'Metal, ladrillo visto y tonos oscuros'),
  ('bohemian', 'Texturas, plantas y colores cálidos'),
  ('minimalist', 'Lo esencial, espacios despejados')
ON CONFLICT (name) DO NOTHING;
