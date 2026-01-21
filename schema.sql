BEGIN;
CREATE TABLE IF NOT EXISTS matches(
  matchId TEXT PRIMARY KEY,
  channelId INTEGER NOT NULL,
  guildId INTEGER NOT NULL,
  teamAName TEXT NOT NULL,
  teamBName TEXT NOT NULL,
  winner TEXT,
  mvpId INTEGER,
  matchMaximumBalls INTEGER
);
CREATE TABLE IF NOT EXISTS innings(
  inningId TEXT PRIMARY KEY,
  matchId TEXT NOT NULL,
  runs INTEGER,
  balls INTEGER,
  wickets INTEGER,
  battingTeam TEXT,
  bowlingTeam TEXT,
  isDeclared INTEGER,
  isFollowOn INTEGER,
  FOREIGN KEY(matchId) REFERENCES matches(matchId) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS deliveries(
  ballId TEXT PRIMARY KEY,
  matchId TEXT NOT NULL,
  inningId TEXT NOT NULL,
  inningNo INTEGER,
  batterId INTEGER,
  nonStrikerId INTEGER,
  bowlerId INTEGER,
  canDo0 INTEGER,
  canDoBoundary INTEGER,
  isWicket INTEGER,
  runs INTEGER,
  InningRuns INTEGER,
  InningBalls INTEGER,
  InningOvers REAL,
  InningWickets INTEGER,
  batterNum INTEGER,
  bowlerNum INTEGER,
  timestamp INTEGER,
  day INTEGER,
  session INTEGER,
  FOREIGN KEY(matchId) REFERENCES matches(matchId) ON DELETE CASCADE,
  FOREIGN KEY(inningId) REFERENCES innings(inningId) ON DELETE CASCADE
);