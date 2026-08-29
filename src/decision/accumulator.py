from itertools import combinations
from src.core.db import get_db_connection
from src.models.dixon_coles import predict_match_probabilities

def get_match_features(cursor, match_id):
    cursor.execute(
        "SELECT feature_name, feature_value FROM features_computed WHERE match_id=?",
        (match_id,)
    )
    rows = cursor.fetchall()
    return {r["feature_name"]: r["feature_value"] for r in rows}

def build_accumulator(target_min_odds=5.0, target_max_odds=10.0, min_events=4, max_events=7):
    """
    Genera una schedina multipla PRUDENTE e ad alta probabilità di successo:
    - Selezioni singole a basso rischio: quote tra 1.25 e 1.85 (Prob. stimata >= 55-60%)
    - Numero eventi: tra 4 e 7 partite
    - Quota totale complessiva: strettamente tra target_min_odds (5.00) e target_max_odds (10.00)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM odds_history WHERE odds_value > 50.0")
    conn.commit()

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

    if not matches:
        print("[!] Nessuna partita programmata trovata a DB.")
        conn.close()
        return None

    candidate_bets = []

    for m in matches:
        m_id = m["match_id"]
        feats = get_match_features(cursor, m_id)
        if not feats:
            continue

        cursor.execute(
            "SELECT selection, odds_value FROM odds_history WHERE match_id=? AND odds_value BETWEEN 1.15 AND 2.20",
            (m_id,)
        )
        odds_rows = cursor.fetchall()

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

        # Selezioni orientate alla prudenza (quote singole 1.25 - 1.85)
        possible_selections = [
            ("1", f"1 ({m['home_team']})", probs["1"], mkt_odds.get("1")),
            ("2", f"2 ({m['away_team']})", probs["2"], mkt_odds.get("2")),
            ("OVER_15", "Over 1.5", probs["OVER_15"], None),
            ("UNDER_35", "Under 3.5", probs["UNDER_35"], None),
            ("MG_1_4", "Multigol 1-4", probs["MG_1_4"], None),
            ("MG_2_4", "Multigol 2-4", probs["MG_2_4"], None),
            ("COMBO_1X_O15", "1X + Over 1.5", probs["COMBO_1X_O15"], None)
        ]

        for code, label, p_est, real_odd in possible_selections:
            # Filtro per preferire eventi con probabilità stimata elevata (>= 58%)
            if p_est < 0.58:
                continue

            if real_odd:
                odds = float(real_odd)
            else:
                odds = round((1.0 / p_est) * 0.93, 2)

            # Ristringiamo il range per singolo evento a quote prudenziale [1.25 - 1.85]
            if not (1.25 <= odds <= 1.85):
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
        print("[!] Nessuna scommessa prudente soddisfa i criteri di probabilità elevata.")
        return None

    # Ordiniamo i candidati per probabilità stimata decrescente
    candidate_bets = sorted(candidate_bets, key=lambda x: x["prob"], reverse=True)
    best_acc = None
    best_score = -999.0

    # Cerca combinazioni tra min_events (4) e max_events (7)
    for k in range(min_events, max_events + 1):
        for combo in combinations(candidate_bets[:35], k):
            m_ids = [c["match_id"] for c in combo]
            if len(m_ids) != len(set(m_ids)):
                continue

            total_odds = 1.0
            total_prob = 1.0
            for c in combo:
                total_odds *= c["odds"]
                total_prob *= c["prob"]

            if target_min_odds <= total_odds <= target_max_odds:
                # Privilegia le combinazioni con la massima Probabilità Combinata Totale
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
