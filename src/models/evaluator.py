import numpy as np
from src.core.db import get_db_connection
from src.models.dixon_coles import predict_match_probabilities
from src.decision.accumulator import get_match_features

def run_backtest(min_ev=0.08, stake_unit=10.0):
    """
    Simula una strategia di scommesse sulle partite giocate a DB (FINISHED)
    e calcola il Brier Score complessivo per verificare la calibrazione delle probabilità.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT m.match_id, m.league_id, m.home_goals, m.away_goals,
               t1.canonical_name as home_team, t2.canonical_name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.status = 'FINISHED' AND m.home_goals IS NOT NULL
        ORDER BY m.match_date_utc ASC
        """
    )
    matches = cursor.fetchall()

    if not matches:
        print("[!] Nessuna partita terminata trovata a DB per il backtest.")
        conn.close()
        return None

    brier_scores = []

    for m in matches:
        m_id = m["match_id"]
        feats = get_match_features(cursor, m_id)
        
        # Gestione sicura delle feature mancanti
        h_pts = feats.get("home_rolling_pts_avg", 1.0) if feats else 1.0
        h_gf = feats.get("home_rolling_gf_avg", 1.0) if feats else 1.0
        h_ga = feats.get("home_rolling_ga_avg", 1.0) if feats else 1.0
        a_pts = feats.get("away_rolling_pts_avg", 1.0) if feats else 1.0
        a_gf = feats.get("away_rolling_gf_avg", 1.0) if feats else 1.0
        a_ga = feats.get("away_rolling_ga_avg", 1.0) if feats else 1.0

        probs = predict_match_probabilities(h_pts, h_gf, h_ga, a_pts, a_gf, a_ga)

        hg = m["home_goals"]
        ag = m["away_goals"]
        
        if hg > ag:
            actual_outcome = "1"
        elif hg == ag:
            actual_outcome = "X"
        else:
            actual_outcome = "2"

        actual_vec = [1 if actual_outcome == o else 0 for o in ["1", "X", "2"]]
        pred_vec = [probs["1"], probs["X"], probs["2"]]
        brier = np.mean([(p - a) ** 2 for p, a in zip(pred_vec, actual_vec)])
        brier_scores.append(brier)

    conn.close()

    mean_brier = float(np.mean(brier_scores)) if brier_scores else 0.0

    return {
        "processed_matches": len(matches),
        "mean_brier_score": round(mean_brier, 4),
        "calibration_status": "CALIBRATED" if mean_brier < 0.22 else "NEEDS_TUNING"
    }