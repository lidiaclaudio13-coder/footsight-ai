import requests
import json
from pathlib import Path
from src.core.db import get_db_connection
from config.settings import ODDS_API_KEY

BASE_URL = "https://api.the-odds-api.com/v4/sports"

ODDS_API_LEAGUE_MAP = {
    "IT_SA": "soccer_italy_serie_a",
    "IT_SB": "soccer_italy_serie_b",
    "FR_L1": "soccer_france_ligue_one",
    "FR_L2": "soccer_france_ligue_two",
    "DE_BL1": "soccer_germany_bundesliga",
    "DE_BL2": "soccer_germany_bundesliga2",
    "ES_LL": "soccer_spain_la_liga",
    "ES_LL2": "soccer_spain_la_liga2",
    "NL_ERE": "soccer_netherlands_eredivisie",
    "AT_BL": "soccer_austria_bundesliga",
    "BE_PL": "soccer_belgium_first_div"
}

def resolve_team_id(cursor, raw_name, country="Unknown"):
    raw_name_clean = raw_name.strip()
    
    cursor.execute(
        "SELECT team_id FROM team_aliases WHERE source_name='the-odds-api' AND raw_name=?",
        (raw_name_clean,)
    )
    row = cursor.fetchone()
    if row:
        return row["team_id"]
        
    cursor.execute("SELECT team_id FROM teams WHERE canonical_name=?", (raw_name_clean,))
    row = cursor.fetchone()
    if row:
        team_id = row["team_id"]
        cursor.execute(
            "INSERT OR IGNORE INTO team_aliases (team_id, source_name, raw_name) VALUES (?, 'the-odds-api', ?)",
            (team_id, raw_name_clean)
        )
        return team_id

    cursor.execute("SELECT team_id FROM teams WHERE canonical_name LIKE ?", (f"%{raw_name_clean}%",))
    row = cursor.fetchone()
    if row:
        team_id = row["team_id"]
    else:
        cursor.execute("INSERT INTO teams (canonical_name, country) VALUES (?, ?)", (raw_name_clean, country))
        team_id = cursor.lastrowid

    cursor.execute(
        "INSERT OR IGNORE INTO team_aliases (team_id, source_name, raw_name) VALUES (?, 'the-odds-api', ?)",
        (team_id, raw_name_clean)
    )
    return team_id

def fetch_and_store_odds(league_id, regions="eu", markets="h2h,totals"):
    if not ODDS_API_KEY or ODDS_API_KEY == "TUA_API_KEY_QUI":
        print("[!] Attenzione: ODDS_API_KEY non impostata nel file .env. Funzione eseguita in modalità simulata/skip.")
        return 0

    sport_key = ODDS_API_LEAGUE_MAP.get(league_id)
    if not sport_key:
        print(f"[!] Mappatura The-Odds-API non presente per {league_id}")
        return 0

    url = f"{BASE_URL}/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions={regions}&markets={markets}&oddsFormat=decimal"
    print(f"[*] Richiesta quote live a The-Odds-API per lega: {league_id} (Mercati: {markets})...")

    res = requests.get(url)
    if res.status_code != 200:
        print(f"[ERROR] Errore API Odds (Status {res.status_code}): {res.text}")
        return 0

    events = res.json()
    conn = get_db_connection()
    cursor = conn.cursor()
    saved_odds_count = 0

    for event in events:
        home_raw = event["home_team"]
        away_raw = event["away_team"]
        commence_time = event["commence_time"]

        home_id = resolve_team_id(cursor, home_raw)
        away_id = resolve_team_id(cursor, away_raw)

        cursor.execute(
            """
            SELECT match_id FROM matches 
            WHERE home_team_id=? AND away_team_id=? AND status='SCHEDULED'
            ORDER BY match_date_utc ASC LIMIT 1
            """,
            (home_id, away_id)
        )
        match_row = cursor.fetchone()
        
        if not match_row:
            cursor.execute(
                """
                INSERT INTO matches (league_id, season, match_date_utc, home_team_id, away_team_id, status)
                VALUES (?, '2526', ?, ?, ?, 'SCHEDULED')
                """,
                (league_id, commence_time, home_id, away_id)
            )
            match_id = cursor.lastrowid
        else:
            match_id = match_row["match_id"]

        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker["title"]
            for market in bookmaker.get("markets", []):
                m_key = market["key"]
                for outcome in market.get("outcomes", []):
                    name = outcome["name"]
                    price = outcome["price"]
                    point = outcome.get("point")

                    selection_label = f"{name} {point}" if point is not None else str(name)

                    cursor.execute(
                        """
                        INSERT INTO odds_history (match_id, bookmaker, market_type, selection, odds_value)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (match_id, book_name, m_key, selection_label, float(price))
                    )
                    saved_odds_count += 1

    conn.commit()
    conn.close()
    print(f"[OK] Inserite {saved_odds_count} quote per la lega {league_id}")
    return saved_odds_count