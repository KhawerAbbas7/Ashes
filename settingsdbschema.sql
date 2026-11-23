BEGIN;
CREATE TABLE IF NOT EXISTS settings(
  guildId INTEGER PRIMARY KEY,
  prefix TEXT
);
CREATE TABLE IF NOT EXISTS blacklist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  object_type TEXT NOT NULL CHECK(object_type IN ('user', 'channel', 'server', 'category')),
  reason TEXT,
  moderator_id INTEGER,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  expires_at INTEGER,
  UNIQUE(object_id, object_type)
);