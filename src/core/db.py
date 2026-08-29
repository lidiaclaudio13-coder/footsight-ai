import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "footsight.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS leagues (
    league_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    fd_code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    raw_name TEXT NOT NULL,
    FOREIGN KEY(team_id) REFERENCES teams(team_id),
    UNIQUE(source_name, raw_name)
);

CREATE TABLE IF NOT EXISTS stadiums (
    stadium_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id TEXT NOT NULL,
    season TEXT NOT NULL,
    match_date_utc TIMESTAMP NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    status TEXT DEFAULT 'SCHEDULED',
    FOREIGN KEY(league_id) REFERENCES leagues(league_id),
    FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY(away_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS match_stats_raw (
    match_id INTEGER PRIMARY KEY,
    home_shots INTEGER,
    away_shots INTEGER,
    home_shots_target INTEGER,
    away_shots_target INTEGER,
    home_possession REAL,
    away_possession REAL,
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS rss_injuries_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    link TEXT UNIQUE,
    published_at TIMESTAMP,
    extracted_team_id INTEGER,
    extracted_player TEXT,
    absence_type TEXT,
    confidence_score REAL,
    FOREIGN KEY(extracted_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS weather_data (
    match_id INTEGER PRIMARY KEY,
    temperature_c REAL,
    precipitation_mm REAL,
    wind_speed_kmh REAL,
    snowfall_cm REAL,
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS odds_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    bookmaker TEXT NOT NULL,
    market_type TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds_value REAL NOT NULL,
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS features_computed (
    match_id INTEGER NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL NOT NULL,
    PRIMARY KEY (match_id, feature_name),
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS accumulator_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_odds REAL NOT NULL,
    expected_value REAL NOT NULL,
    risk_level TEXT NOT NULL,
    selection_json TEXT NOT NULL
);

-- NUOVE TABELLE TRACKER ED ESPORTAZIONE
CREATE TABLE IF NOT EXISTS bets_tracker (
    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bet_type TEXT NOT NULL, -- 'SINGLE' | 'ACCUMULATOR'
    match_description TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    status TEXT DEFAULT 'PENDING', -- 'PENDING' | 'WON' | 'LOST'
    payout REAL DEFAULT 0.0,
    profit_loss REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date_utc);
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league_id);
CREATE INDEX IF NOT EXISTS idx_odds_match ON odds_history(match_id);
"""

def get_db_connection():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[OK] Database inizializzato con successo presso: {DB_PATH}")
