from itertools import combinations
from src.core.db import get_db_connection
from src.models.dixon_coles import predict_match_probabilities

def get_match_features(cursor, match_id):
    cursor.execute("SELECT feature_name, feature_value FROM features_computed WHERE match_id=?", (match_id,))
    rows = cursor.fetchall()
    return {r["feature_name"]: r["feature_value"] for r in rows}

def build_accumulator(
    target_min_odds=3.0, 
    target_max_odds=15.0, 
    min_events=2, 
    max_events=8, 
    exact_events=None, 
    single_min_odd=1.15, 
    single_max_odd=4.00
):
    """
    Genera la miglior multipla in base ai vincoli forniti.
    - exact_events: se specificato (int), forza la multipla ad avere ESATTAMENTE quel numero di eventi.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT m.match_id, m.league_id, m.match_date_utc, 
               t1.canonical_name as home_team, t2.canonical_name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date_utc DESC LIMIT 35
        """
    )
    matches = cursor.fetchall()

    if not matches:
        conn.close()
        return None

    candidate_bets = []

    labels_map = {
        "1": "1", "X": "X", "2": "2",
        "BTTS_YES": "Goal", "BTTS_NO": "NoGoal",
        "OVER_15": "Over 1.5", "UNDER_15": "Under 1.5",
        "OVER_25": "Over 2.5", "UNDER_25": "Under 2.5",
        "OVER_35": "Over 3.5", "UNDER_35": "Under 3.5",
        "OVER_45": "Over 4.5", "UNDER_45": "Under 4.5",
        "OVER_1T_15": "1T Over 1.5", "UNDER_1T_15": "1T Under 1.5",
        "OVER_2T_15": "2T Over 1.5", "UNDER_2T_15": "2T Under 1.5",
        "MG_1_2": "Multigol 1-2", "MG_1_3": "Multigol 1-3", "MG_1_4": "Multigol 1-4",
        "MG_2_3": "Multigol 2-3", "MG_2_4": "Multigol 2-4", "MG_2_5": "Multigol 2-5",
        "MG1T_1_2": "Multigol 1T 1-2", "MG1T_1_3": "Multigol 1T 1-3",
        "MG2T_1_2": "Multigol 2T 1-2", "MG2T_1_3": "Multigol 2T 1-3"
    }

    for m in matches:
        m_id = m["match_id"]
        feats = get_match_features(cursor, m_id)
        
        cursor.execute(
            "SELECT selection, odds_value FROM odds_history WHERE match_id=?",
            (m_id,)
        )
        odds_rows = cursor.fetchall()
        mkt_odds = {str(r["selection"]).strip().upper(): float(r["odds_value"]) for r in odds_rows}

        h_pts = feats.get("home_rolling_pts_avg", 1.0) if feats else 1.0
        h_gf = feats.get("home_rolling_gf_avg", 1.0) if feats else 1.0
        h_ga = feats.get("home_rolling_ga_avg", 1.0) if feats else 1.0
        a_pts = feats.get("away_rolling_pts_avg", 1.0) if feats else 1.0
        a_gf = feats.get("away_rolling_gf_avg", 1.0) if feats else 1.0
        a_ga = feats.get("away_rolling_ga_avg", 1.0) if feats else 1.0

        probs = predict_match_probabilities(h_pts, h_gf, h_ga, a_pts, a_gf, a_ga)

        for code, label in labels_map.items():
            p_est = probs.get(code, 0.0)
            
            if p_est < 0.20:
                continue

            real_odd = mkt_odds.get(code)
            odds = real_odd if real_odd else round((1.0 / max(p_est, 0.02)) * 0.90, 2)
            
            # Filtro rigido sulla quota della singola selezione per evento
            if not (single_min_odd <= odds <= single_max_odd):
                continue

            ev = (p_est * odds) - 1.0
            candidate_bets.append({
                "match_id": m_id,
                "league": m["league_id"],
                "match": f"{m['home_team']} vs {m['away_team']}",
                "selection": label,
                "odds": odds,
                "prob": p_est,
                "ev": round(ev, 4)
            })

    conn.close()

    if not candidate_bets:
        return None

    # Ordina i candidati per valore atteso e probabilità
    candidate_bets = sorted(candidate_bets, key=lambda x: (x["ev"], x["prob"]), reverse=True)
    best_acc = None
    best_score = -999.0

    # Definisce il range di k (numero eventi) da testare
    if exact_events is not None and exact_events > 0:
        event_counts = [exact_events]
    else:
        event_counts = range(min_events, max_events + 1)

    # Cerca combinazioni tra i candidati estratti (limite primi 50 mercati più promettenti)
    for k in event_counts:
        for combo in combinations(candidate_bets[:50], k):
            m_ids = [c["match_id"] for c in combo]
            if len(m_ids) != len(set(m_ids)):
                continue

            total_odds = 1.0
            total_prob = 1.0
            for c in combo:
                total_odds *= c["odds"]
                total_prob *= c["prob"]

            if target_min_odds <= total_odds <= target_max_odds:
                score = total_prob * total_odds
                if score > best_score:
                    best_score = score
                    best_acc = {
                        "total_odds": round(total_odds, 2),
                        "combined_prob": round(total_prob * 100, 2),
                        "expected_value": round((total_prob * total_odds) - 1.0, 4),
                        "num_events": len(combo),
                        "events": combo
                    }

    return best_acc
