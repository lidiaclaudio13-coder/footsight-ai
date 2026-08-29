from src.core.db import get_db_connection
from src.models.dixon_coles import predict_match_probabilities
from src.decision.accumulator import get_match_features

def calculate_kelly_stake(prob_est, odds, fraction=0.25, max_bankroll_pct=0.03):
    """Calcola la frazione di Kelly frazionata (Quarter-Kelly) con cap al 3%."""
    b = odds - 1.0
    p = prob_est
    q = 1.0 - p
    f_kelly = (b * p - q) / b
    if f_kelly <= 0:
        return 0.0
    stake = f_kelly * fraction
    return round(min(stake, max_bankroll_pct) * 100, 1)

def find_top_singles(top_n=5, min_ev=0.02, max_single_odds=3.50):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT m.match_id, m.league_id, m.match_date_utc, 
               t1.canonical_name as home_team, t2.canonical_name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.status = 'SCHEDULED'
        ORDER BY m.match_date_utc ASC
        """
    )
    matches = cursor.fetchall()

    singles = []

    for m in matches:
        m_id = m["match_id"]
        feats = get_match_features(cursor, m_id)
        if not feats:
            continue

        cursor.execute(
            """
            SELECT selection, odds_value FROM odds_history 
            WHERE match_id=? AND odds_value BETWEEN 1.25 AND ?
            """,
            (m_id, max_single_odds)
        )
        odds_rows = cursor.fetchall()
        if not odds_rows:
            continue

        mkt_odds = {}
        for r in odds_rows:
            sel = str(r["selection"]).strip().upper()
            val = float(r["odds_value"])
            if sel in ["1", "HOME", m["home_team"].upper()]:
                mkt_odds["1"] = val
            elif sel in ["X", "DRAW"]:
                mkt_odds["X"] = val
            elif sel in ["2", "AWAY", m["away_team"].upper()]:
                mkt_odds["2"] = val
            elif "OVER 2.5" in sel:
                mkt_odds["OVER_25"] = val
            elif "UNDER 2.5" in sel:
                mkt_odds["UNDER_25"] = val

        probs = predict_match_probabilities(
            feats.get("home_rolling_pts_avg", 1.0),
            feats.get("home_rolling_gf_avg", 1.0),
            feats.get("home_rolling_ga_avg", 1.0),
            feats.get("away_rolling_pts_avg", 1.0),
            feats.get("away_rolling_gf_avg", 1.0),
            feats.get("away_rolling_ga_avg", 1.0),
            market_odds=mkt_odds,
            w_market=0.85
        )

        for sel_key, odds in mkt_odds.items():
            if sel_key not in probs:
                continue

            prob_est = probs[sel_key]
            ev = (prob_est * odds) - 1.0
            implied_prob = 1.0 / odds
            edge = prob_est - implied_prob

            if ev >= min_ev and edge > 0.01:
                sel_label = sel_key
                if sel_key == "1":
                    sel_label = f"1 ({m['home_team']})"
                elif sel_key == "2":
                    sel_label = f"2 ({m['away_team']})"
                elif sel_key == "OVER_25":
                    sel_label = "Over 2.5"
                elif sel_key == "UNDER_25":
                    sel_label = "Under 2.5"

                stake_pct = calculate_kelly_stake(prob_est, odds)

                if stake_pct > 0.0:
                    singles.append({
                        "league": m["league_id"],
                        "match": f"{m['home_team']} vs {m['away_team']}",
                        "selection": sel_label,
                        "odds": odds,
                        "prob_est": prob_est,
                        "implied_prob": implied_prob,
                        "edge": edge,
                        "ev": ev,
                        "stake_pct": stake_pct
                    })

    conn.close()
    singles = sorted(singles, key=lambda x: x["ev"], reverse=True)
    return singles[:top_n]