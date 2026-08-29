import pandas as pd
import requests
import io
import json
from pathlib import Path
from src.core.db import get_db_connection

BASE_URL = "https://www.football-data.co.uk/mmz4281"

def get_league_codes():
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "leagues.json"
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {l["fd_code"]: l["league_id"] for l in data.get("leagues", []) if l.get("fd_code")}

def get_or_create_team(cursor, raw_team_name, country):
    # Check alias
    cursor.execute(
        "SELECT team_id FROM team_aliases WHERE source_name='football-data' AND raw_name=?",
        (raw_team_name,)
    )
    row = cursor.fetchone()
    if row:
        return row["team_id"]

    # Check canonical name
    cursor.execute("SELECT team_id FROM teams WHERE canonical_name=?", (raw_team_name,))
    row = cursor.fetchone()
    if row:
        team_id = row["team_id"]
    else:
        cursor.execute("INSERT INTO teams (canonical_name, country) VALUES (?, ?)", (raw_team_name, country))
        team_id = cursor.lastrowid

    # Insert alias
    cursor.execute(
        "INSERT OR IGNORE INTO team_aliases (team_id, source_name, raw_name) VALUES (?, 'football-data', ?)",
        (team_id, raw_team_name)
    )
    return team_id

def ingest_football_data(season_code="2526"):
    """
    Scarica ed elabora i CSV da Football-Data.co.uk per la stagione indicata (es. '2526' per 2025/2026).
    """
    fd_to_league_id = get_league_codes()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Prendi informazioni paesi dalle leghe
    cursor.execute("SELECT fd_code, country FROM leagues")
    league_country_map = {row["fd_code"]: row["country"] for row in cursor.fetchall()}

    total_matches = 0

    for fd_code, league_id in fd_to_league_id.items():
        url = f"{BASE_URL}/{season_code}/{fd_code}.csv"
        country = league_country_map.get(fd_code, "Unknown")
        print(f"[*] Ingestion in corso per {fd_code} ({league_id}) da {url}...")

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                print(f"[!] Impossibile scaricare {fd_code} (Status: {res.status_code})")
                continue

            # Parsing CSV
            df = pd.read_csv(io.StringIO(res.text))
            if df.empty or 'HomeTeam' not in df.columns:
                print(f"[!] CSV vuoto o malformato per {fd_code}")
                continue

            # Standardizza colonne minime
            for _, row in df.iterrows():
                home_team_raw = str(row['HomeTeam']).strip()
                away_team_raw = str(row['AwayTeam']).strip()
                
                if not home_team_raw or home_team_raw == 'nan':
                    continue

                home_team_id = get_or_create_team(cursor, home_team_raw, country)
                away_team_id = get_or_create_team(cursor, away_team_raw, country)

                # Gestione data
                raw_date = str(row['Date'])
                try:
                    match_date = pd.to_datetime(raw_date, dayfirst=True).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    continue

                home_goals = int(row['FTHG']) if pd.notnull(row.get('FTHG')) else None
                away_goals = int(row['FTAG']) if pd.notnull(row.get('FTAG')) else None
                status = 'FINISHED' if home_goals is not None else 'SCHEDULED'

                # Inserisci Match
                cursor.execute(
                    """
                    INSERT INTO matches (league_id, season, match_date_utc, home_team_id, away_team_id, home_goals, away_goals, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (league_id, season_code, match_date, home_team_id, away_team_id, home_goals, away_goals, status)
                )
                match_id = cursor.lastrowid

                # Inserisci Statistiche Match se disponibili
                hs = int(row['HS']) if pd.notnull(row.get('HS')) else None
                as_ = int(row['AS']) if pd.notnull(row.get('AS')) else None
                hst = int(row['HST']) if pd.notnull(row.get('HST')) else None
                ast = int(row['AST']) if pd.notnull(row.get('AST')) else None

                if hs is not None or as_ is not None:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO match_stats_raw (match_id, home_shots, away_shots, home_shots_target, away_shots_target)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (match_id, hs, as_, hst, ast)
                    )

                total_matches += 1

            conn.commit()

        except Exception as e:
            print(f"[ERROR] Errore nell'elaborazione di {fd_code}: {e}")

    conn.close()
    print(f"[OK] Ingestion completata. Totale partite elaborate: {total_matches}")
