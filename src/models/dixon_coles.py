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

def _calc_mg_prob(matrix, g_min, g_max):
    max_g = matrix.shape[0]
    return float(np.sum([matrix[x, y] for x in range(max_g) for y in range(max_g) if g_min <= x + y <= g_max]))

def _calc_mg_team_prob(matrix, g_min, g_max, is_home=True):
    max_g = matrix.shape[0]
    if is_home:
        return float(np.sum([matrix[x, y] for x in range(max_g) for y in range(max_g) if g_min <= x <= g_max]))
    return float(np.sum([matrix[x, y] for x in range(max_g) for y in range(max_g) if g_min <= y <= g_max]))

def predict_match_probabilities(home_pts_avg, home_gf_avg, home_ga_avg, 
                               away_pts_avg, away_gf_avg, away_ga_avg,
                               market_odds=None, w_market=0.85,
                               rho=-0.05, home_advantage=0.15):
    h_att = 0.5 * home_gf_avg + 0.5 * 1.25
    h_def = 0.5 * home_ga_avg + 0.5 * 1.25
    a_att = 0.5 * away_gf_avg + 0.5 * 1.25
    a_def = 0.5 * away_ga_avg + 0.5 * 1.25

    lambda_val = max(0.3, (h_att * 0.5 + a_def * 0.5) + home_advantage)
    mu_val = max(0.3, (a_att * 0.5 + h_def * 0.5))

    max_goals = 8
    m_full = np.zeros((max_goals, max_goals))
    for x in range(max_goals):
        for y in range(max_goals):
            m_full[x, y] = poisson.pmf(x, lambda_val) * poisson.pmf(y, mu_val) * tau(x, y, lambda_val, mu_val, rho)
    m_full /= np.sum(m_full)

    # Tempi di gioco (45% 1T, 55% 2T)
    m_1t = np.zeros((max_goals, max_goals))
    m_2t = np.zeros((max_goals, max_goals))
    for x in range(max_goals):
        for y in range(max_goals):
            m_1t[x, y] = poisson.pmf(x, lambda_val * 0.45) * poisson.pmf(y, mu_val * 0.45)
            m_2t[x, y] = poisson.pmf(x, lambda_val * 0.55) * poisson.pmf(y, mu_val * 0.55)
    m_1t /= np.sum(m_1t)
    m_2t /= np.sum(m_2t)

    mg_ranges = [(1,2), (1,3), (1,4), (2,3), (2,4), (2,5)]
    mg_team_ranges = [(0,1), (0,2), (0,3), (1,2), (1,3), (1,4), (2,3), (2,4), (2,5)]

    probs = {
        "1": float(np.sum(np.tril(m_full, -1))),
        "X": float(np.sum(np.diag(m_full))),
        "2": float(np.sum(np.triu(m_full, 1))),
        "BTTS_YES": float(1.0 - (np.sum(m_full[0, :]) + np.sum(m_full[:, 0]) - m_full[0, 0])),
        "BTTS_NO": float(np.sum(m_full[0, :]) + np.sum(m_full[:, 0]) - m_full[0, 0])
    }

    # U/O Match & Tempi
    for line in [1.5, 2.5, 3.5, 4.5]:
        probs[f"OVER_{str(line).replace('.','')}"] = float(np.sum([m_full[x,y] for x in range(max_goals) for y in range(max_goals) if x+y > line]))
        probs[f"UNDER_{str(line).replace('.','')}"] = float(np.sum([m_full[x,y] for x in range(max_goals) for y in range(max_goals) if x+y < line]))
        probs[f"OVER_1T_{str(line).replace('.','')}"] = float(np.sum([m_1t[x,y] for x in range(max_goals) for y in range(max_goals) if x+y > line]))
        probs[f"UNDER_1T_{str(line).replace('.','')}"] = float(np.sum([m_1t[x,y] for x in range(max_goals) for y in range(max_goals) if x+y < line]))
        probs[f"OVER_2T_{str(line).replace('.','')}"] = float(np.sum([m_2t[x,y] for x in range(max_goals) for y in range(max_goals) if x+y > line]))
        probs[f"UNDER_2T_{str(line).replace('.','')}"] = float(np.sum([m_2t[x,y] for x in range(max_goals) for y in range(max_goals) if x+y < line]))

    # Multigol Match, 1T, 2T e Squadre
    for g1, g2 in mg_ranges:
        probs[f"MG_{g1}_{g2}"] = _calc_mg_prob(m_full, g1, g2)
        probs[f"MG1T_{g1}_{g2}"] = _calc_mg_prob(m_1t, g1, g2)
        probs[f"MG2T_{g1}_{g2}"] = _calc_mg_prob(m_2t, g1, g2)

    for g1, g2 in mg_team_ranges:
        probs[f"MG_H_{g1}_{g2}"] = _calc_mg_team_prob(m_full, g1, g2, is_home=True)
        probs[f"MG_A_{g1}_{g2}"] = _calc_mg_team_prob(m_full, g1, g2, is_home=False)
        probs[f"MG1T_H_{g1}_{g2}"] = _calc_mg_team_prob(m_1t, g1, g2, is_home=True)
        probs[f"MG1T_A_{g1}_{g2}"] = _calc_mg_team_prob(m_1t, g1, g2, is_home=False)
        probs[f"MG2T_H_{g1}_{g2}"] = _calc_mg_team_prob(m_2t, g1, g2, is_home=True)
        probs[f"MG2T_A_{g1}_{g2}"] = _calc_mg_team_prob(m_2t, g1, g2, is_home=False)

    return {k: round(v, 4) for k, v in probs.items()}