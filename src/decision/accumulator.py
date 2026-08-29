from itertools import combinations
from src.core.db import get_db_connection
from src.models.dixon_coles import predict_match_probabilities

def get_match_features(cursor, match_id):
    cursor.execute("SELECT feature_name, feature_value FROM features_computed WHERE match_id=?", (match_id,))
    rows = cursor.fetchall()
    return {r["feature_name"]: r["feature_value"] for r in rows}

def build_accumulator(target_min_odds=3.0, target_max_odds=15.0, min_events=2, max_events=8, single_min_odd=1.12, single_max_odd=3.50):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Recupera tutti i match disponibili a database
    cursor.execute(
        """
        SELECT m.match_id, m.league_id, m.match_date_utc, 
               t1.canonical_name as home_team, t2.canonical_name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date_utc DESC LIMIT 30
        """
    )
    matches = cursor.fetchall()

    if not matches:
        conn.close()
        return None

    candidate_bets = []

    for m in matches:
        m_id = m["match_id"]
        feats = get_match_features(cursor, m_id)
        
        # Recupera quote reali da DB se presenti
        cursor.execute(
            "SELECT selection, odds_value FROM odds_history WHERE match_id=?",
            (m_id,)
        )
        odds_rows = cursor.fetchall()
        mkt_odds = {}
        for r in odds_rows:
            sel = str(r["selection"]).strip().upper()
            mkt_odds[sel] = float(r["odds_value"])

        h_pts = feats.get("home_rolling_pts_avg", 1.0) if feats else 1.0
        h_gf = feats.get("home_rolling_gf_avg", 1.0) if feats else 1.0
        h_ga = feats.get("home_rolling_ga_avg", 1.0) if feats else 1.0
        a_pts = feats.get("away_rolling_pts_avg", 1.0) if feats else 1.0
        a_gf = feats.get("away_rolling_gf_avg", 1.0) if feats else 1.0
        a_ga = feats.get("away_rolling_ga_avg", 1.0) if feats else 1.0

        probs = predict_match_probabilities(h_pts, h_gf, h_ga, a_pts, a_gf, a_ga)

        # Selezioni candidate per la multipla
        candidate_options = [
            ("1", f"1 ({m['home_team']})", probs.get("1", 0.0), mkt_odds.get("1")),
            ("2", f"2 ({m['away_team']})", probs.get("2", 0.0), mkt_odds.get("2")),
            ("OVER_15", "Over 1.5", probs.get("OVER_15", 0.0), mkt_odds.get("OVER_15")),
            ("UNDER_35", "Under 3.5", probs.get("UNDER_35", 0.0), mkt_odds.get("UNDER_35")),
            ("BTTS_YES", "Goal", probs.get("BTTS_YES", 0.0), mkt_odds.get("BTTS_YES")),
            ("MG_1_4", "Multigol 1-4", probs.get("MG_1_4", 0.0), None),
            ("MG_2_4", "Multigol 2-4", probs.get("MG_2_4", 0.0), None),
        ]

        for code, label, p_est, real_odd in candidate_options:
            if p_est < 0.35:
                continue

            odds = real_odd if real_odd else round((1.0 / max(p_est, 0.05)) * 0.90, 2)
            
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

    # Ordina i candidati per probabilità stimata decrescente
    candidate_bets = sorted(candidate_bets, key=lambda x: x["prob"], reverse=True)
    best_acc = None
    best_score = -999.0

    # Generazione combinazioni
    for k in range(min_events, max_events + 1):
        for combo in combinations(candidate_bets[:30], k):
            m_ids = [c["match_id"] for c in combo]
            if len(m_ids) != len(set(m_ids)):
                continue

            total_odds = 1.0
            total_prob = 1.0
            for c in combo:
                total_odds *= c["odds"]
                total_prob *= c["prob"]

            if target_min_odds <= total_odds <= target_max_odds:
                score = total_prob * 100.0
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