import numpy as np
from scipy.stats import poisson

def tau(x, y, lambda_val, mu_val, rho):
    if x == 0 and y == 0:
        return 1.0 - (lambda_val * mu_val * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_val * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu_val * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def predict_match_probabilities(home_pts_avg, home_gf_avg, home_ga_avg, 
                               away_pts_avg, away_gf_avg, away_ga_avg,
                               market_odds=None, w_market=0.85,
                               rho=-0.05, home_advantage=0.15):
    """
    Calcola le probabilità per tutti i mercati principali e derivati:
    1X2, Over/Under, BTTS, Multigol Match, Multigol 1T e Combo.
    """
    h_att = 0.5 * home_gf_avg + 0.5 * 1.25
    h_def = 0.5 * home_ga_avg + 0.5 * 1.25
    a_att = 0.5 * away_gf_avg + 0.5 * 1.25
    a_def = 0.5 * away_ga_avg + 0.5 * 1.25

    lambda_val = max(0.3, (h_att * 0.5 + a_def * 0.5) + home_advantage)
    mu_val = max(0.3, (a_att * 0.5 + h_def * 0.5))

    max_goals = 8
    score_matrix = np.zeros((max_goals, max_goals))

    for x in range(max_goals):
        for y in range(max_goals):
            p_x = poisson.pmf(x, lambda_val)
            p_y = poisson.pmf(y, mu_val)
            adj = tau(x, y, lambda_val, mu_val, rho)
            score_matrix[x, y] = p_x * p_y * adj

    score_matrix /= np.sum(score_matrix)

    # --- 1X2 ---
    p_1 = float(np.sum(np.tril(score_matrix, -1)))
    p_x = float(np.sum(np.diag(score_matrix)))
    p_2 = float(np.sum(np.triu(score_matrix, 1)))

    # --- Under / Over ---
    p_u15 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x + y < 1.5]))
    p_o15 = 1.0 - p_u15
    p_u25 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x + y < 2.5]))
    p_o25 = 1.0 - p_u25
    p_u35 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x + y < 3.5]))
    p_o35 = 1.0 - p_u35

    # --- BTTS (Goal / NoGoal) ---
    p_btts_no = float(np.sum(score_matrix[0, :]) + np.sum(score_matrix[:, 0]) - score_matrix[0, 0])
    p_btts_yes = 1.0 - p_btts_no

    # --- MULTIGOL MATCH ---
    p_mg_1_2 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 1 <= x + y <= 2]))
    p_mg_1_3 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 1 <= x + y <= 3]))
    p_mg_1_4 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 1 <= x + y <= 4]))
    p_mg_2_3 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 2 <= x + y <= 3]))
    p_mg_2_4 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 2 <= x + y <= 4]))
    p_mg_2_5 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if 2 <= x + y <= 5]))

    # --- MULTIGOL 1° TEMPO (1T) ---
    # Storicamente nei campionati europei il 1T registra circa il 45% dei gol totali (lambda_1t = 0.45 * lambda)
    lambda_1t = lambda_val * 0.45
    mu_1t = mu_val * 0.45
    matrix_1t = np.zeros((max_goals, max_goals))
    for x in range(max_goals):
        for y in range(max_goals):
            matrix_1t[x, y] = poisson.pmf(x, lambda_1t) * poisson.pmf(y, mu_1t)
    matrix_1t /= np.sum(matrix_1t)

    p_mg1t_1_2 = float(np.sum([matrix_1t[x, y] for x in range(max_goals) for y in range(max_goals) if 1 <= x + y <= 2]))
    p_mg1t_1_3 = float(np.sum([matrix_1t[x, y] for x in range(max_goals) for y in range(max_goals) if 1 <= x + y <= 3]))
    p_mg1t_2_3 = float(np.sum([matrix_1t[x, y] for x in range(max_goals) for y in range(max_goals) if 2 <= x + y <= 3]))

    # --- COMBO MARKETS ---
    p_combo_1_o15 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x > y and (x + y) > 1.5]))
    p_combo_1x_o15 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x >= y and (x + y) > 1.5]))
    p_combo_x2_u35 = float(np.sum([score_matrix[x, y] for x in range(max_goals) for y in range(max_goals) if x <= y and (x + y) < 3.5]))
    p_combo_1_btts = float(np.sum([score_matrix[x, y] for x in range(1, max_goals) for y in range(1, max_goals) if x > y]))
    p_combo_2_btts = float(np.sum([score_matrix[x, y] for x in range(1, max_goals) for y in range(1, max_goals) if y > x]))

    probs = {
        "1": round(p_1, 4), "X": round(p_x, 4), "2": round(p_2, 4),
        "OVER_15": round(p_o15, 4), "UNDER_15": round(p_u15, 4),
        "OVER_25": round(p_o25, 4), "UNDER_25": round(p_u25, 4),
        "OVER_35": round(p_o35, 4), "UNDER_35": round(p_u35, 4),
        "BTTS_YES": round(p_btts_yes, 4), "BTTS_NO": round(p_btts_no, 4),
        "MG_1_2": round(p_mg_1_2, 4), "MG_1_3": round(p_mg_1_3, 4),
        "MG_1_4": round(p_mg_1_4, 4), "MG_2_3": round(p_mg_2_3, 4),
        "MG_2_4": round(p_mg_2_4, 4), "MG_2_5": round(p_mg_2_5, 4),
        "MG1T_1_2": round(p_mg1t_1_2, 4), "MG1T_1_3": round(p_mg1t_1_3, 4), "MG1T_2_3": round(p_mg1t_2_3, 4),
        "COMBO_1_O15": round(p_combo_1_o15, 4), "COMBO_1X_O15": round(p_combo_1x_o15, 4),
        "COMBO_X2_U35": round(p_combo_x2_u35, 4), "COMBO_1_BTTS": round(p_combo_1_btts, 4),
        "COMBO_2_BTTS": round(p_combo_2_btts, 4)
    }

    # Ancoraggio Bayesiano alle quote di mercato se presenti
    if market_odds and isinstance(market_odds, dict):
        if "1" in market_odds and "X" in market_odds and "2" in market_odds:
            o1, ox, o2 = market_odds["1"], market_odds["X"], market_odds["2"]
            r1, rx, r2 = 1.0/o1, 1.0/ox, 1.0/o2
            tot_r = r1 + rx + r2
            p_mkt_1, p_mkt_x, p_mkt_2 = r1/tot_r, rx/tot_r, r2/tot_r

            probs["1"] = round((w_market * p_mkt_1) + ((1.0 - w_market) * probs["1"]), 4)
            probs["X"] = round((w_market * p_mkt_x) + ((1.0 - w_market) * probs["X"]), 4)
            probs["2"] = round((w_market * p_mkt_2) + ((1.0 - w_market) * probs["2"]), 4)

    return probs
