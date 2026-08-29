import pandas as pd
import numpy as np
from datetime import datetime
from src.core.db import get_db_connection

def parse_utc_timestamp(dt_val):
    """Convert string/timestamp to tz-naive UTC pandas Timestamp."""
    if dt_val is None:
        return None
    ts = pd.to_datetime(dt_val, utc=True)
    return ts.tz_localize(None)

def compute_features_for_match(cursor, match_id, window=5):
    """
    Calcola le feature per un singolo match garantendo L'ASSENZA TOTALE DI DATA LEAKAGE.
    Utilizza unicamente i dati di partite concluse PRIMA di match_date_utc.
    """
    cursor.execute(
        """
        SELECT match_id, league_id, match_date_utc, home_team_id, away_team_id 
        FROM matches WHERE match_id=?
        """,
        (match_id,)
    )
    target = cursor.fetchone()
    if not target:
        return 0

    t_date_str = target["match_date_utc"]
    target_match_date = parse_utc_timestamp(t_date_str)
    
    h_team = target["home_team_id"]
    a_team = target["away_team_id"]

    features = {}

    def get_team_history(team_id):
        query = """
            SELECT m.match_id, m.match_date_utc, m.home_team_id, m.away_team_id, 
                   m.home_goals, m.away_goals, s.home_shots, s.away_shots
            FROM matches m
            LEFT JOIN match_stats_raw s ON m.match_id = s.match_id
            WHERE (m.home_team_id=? OR m.away_team_id=?) 
              AND m.match_date_utc < ? 
              AND m.status='FINISHED'
            ORDER BY m.match_date_utc DESC
            LIMIT ?
        """
        cursor.execute(query, (team_id, team_id, t_date_str, window))
        return cursor.fetchall()

    # --- Feature Squadra di Casa ---
    h_hist = get_team_history(h_team)
    if h_hist:
        h_pts, h_gf, h_ga, h_shots = [], [], [], []
        for m in h_hist:
            is_home = (m["home_team_id"] == h_team)
            gf = m["home_goals"] if is_home else m["away_goals"]
            ga = m["away_goals"] if is_home else m["home_goals"]
            shots = m["home_shots"] if is_home else m["away_shots"]

            h_gf.append(gf if gf is not None else 0)
            h_ga.append(ga if ga is not None else 0)
            if shots is not None:
                h_shots.append(shots)

            if gf > ga:
                h_pts.append(3)
            elif gf == ga:
                h_pts.append(1)
            else:
                h_pts.append(0)

        features["home_rolling_pts_avg"] = float(np.mean(h_pts))
        features["home_rolling_gf_avg"] = float(np.mean(h_gf))
        features["home_rolling_ga_avg"] = float(np.mean(h_ga))
        features["home_rolling_shots_avg"] = float(np.mean(h_shots)) if h_shots else 0.0

        last_match_date = parse_utc_timestamp(h_hist[0]["match_date_utc"])
        features["home_rest_days"] = float((target_match_date - last_match_date).days)
    else:
        features["home_rolling_pts_avg"] = 1.0
        features["home_rolling_gf_avg"] = 1.0
        features["home_rolling_ga_avg"] = 1.0
        features["home_rolling_shots_avg"] = 0.0
        features["home_rest_days"] = 7.0

    # --- Feature Squadra In Trasferta ---
    a_hist = get_team_history(a_team)
    if a_hist:
        a_pts, a_gf, a_ga, a_shots = [], [], [], []
        for m in a_hist:
            is_home = (m["home_team_id"] == a_team)
            gf = m["home_goals"] if is_home else m["away_goals"]
            ga = m["away_goals"] if is_home else m["home_goals"]
            shots = m["home_shots"] if is_home else m["away_shots"]

            a_gf.append(gf if gf is not None else 0)
            a_ga.append(ga if ga is not None else 0)
            if shots is not None:
                a_shots.append(shots)

            if gf > ga:
                a_pts.append(3)
            elif gf == ga:
                a_pts.append(1)
            else:
                a_pts.append(0)

        features["away_rolling_pts_avg"] = float(np.mean(a_pts))
        features["away_rolling_gf_avg"] = float(np.mean(a_gf))
        features["away_rolling_ga_avg"] = float(np.mean(a_ga))
        features["away_rolling_shots_avg"] = float(np.mean(a_shots)) if a_shots else 0.0

        last_match_date = parse_utc_timestamp(a_hist[0]["match_date_utc"])
        features["away_rest_days"] = float((target_match_date - last_match_date).days)
    else:
        features["away_rolling_pts_avg"] = 1.0
        features["away_rolling_gf_avg"] = 1.0
        features["away_rolling_ga_avg"] = 1.0
        features["away_rolling_shots_avg"] = 0.0
        features["away_rest_days"] = 7.0

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for feat_name, feat_val in features.items():
        cursor.execute(
            """
            INSERT OR REPLACE INTO features_computed (match_id, computed_at, feature_name, feature_value)
            VALUES (?, ?, ?, ?)
            """,
            (match_id, now_str, feat_name, feat_val)
        )

    return len(features)

def build_all_features():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT match_id FROM matches ORDER BY match_date_utc ASC")
    matches = cursor.fetchall()
    print(f"[*] Avvio calcolo feature per {len(matches)} partite...")

    count = 0
    for m in matches:
        count += compute_features_for_match(cursor, m["match_id"])

    conn.commit()
    conn.close()
    print(f"[OK] Calcolo feature completato! Elaborate {count} variabili totali.")
