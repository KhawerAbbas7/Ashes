BEGIN;
CREATE TABLE IF NOT EXISTS users(
  userId INTEGER PRIMARY KEY, 
  coins INTEGER DEFAULT 0
);
CREATE TABLE cooldowns(
  userId INTEGER NOT NULL,
  command TEXT NOT NULL,
  lastClaimAt INTEGER NOT NULL,
  expiresAt INTEGER NOT NULL,
  reminded INTEGER DEFAULT 0,
  PRIMARY KEY (userId, command));
CREATE TABLE streaks(
  userId INTEGER NOT NULL,
  command TEXT NOT NULL,
  streak INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (userId, command));
CREATE TABLE IF NOT EXISTS inventory(
  userId INTEGER NOT NULL, 
  item TEXT NOT NULL,
  itemValue TEXT DEFAULT '',
  PRIMARY KEY (userId, item)
);