import json
import os
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

def export_daily_report(singles, accumulator):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Export JSON
    json_path = REPORTS_DIR / f"report_{today_str}.json"
    data = {
        "date": today_str,
        "singles": singles,
        "accumulator": accumulator
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Export Markdown
    md_path = REPORTS_DIR / f"report_{today_str}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# FootSight AI — Daily Report ({today_str})\n\n")
        
        f.write("## 📌 Top Scommesse Singole Consigliate\n")
        if singles:
            f.write("| # | Lega | Match | Esito | Quota | Prob. Stima | Edge | EV | Stake % |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            for idx, s in enumerate(singles, 1):
                odds_val = float(s.get("odds", 1.0))
                prob_val = float(s.get("prob_est", 0.0))
                edge_val = float(s.get("edge", 0.0))
                ev_val = float(s.get("ev", 0.0))
                f.write(f"| {idx} | {s.get('league', 'N/A')} | {s.get('match', 'N/A')} | {s.get('selection', 'N/A')} | {odds_val:.2f} | {prob_val*100:.1f}% | +{edge_val*100:.1f}% | +{ev_val:.4f} | {s.get('stake_pct', 0.0)}% |\n")
        else:
            f.write("_Nessuna singola a valore trovata per oggi._\n")
            
        f.write("\n\n## 🎯 Multipla Consigliata\n")
        if accumulator:
            tot_odds = float(accumulator.get("total_odds", 0.0))
            comb_prob = float(accumulator.get("combined_prob", 0.0))
            exp_val = float(accumulator.get("expected_value", 0.0))
            f.write(f"**Quota Totale**: {tot_odds:.2f} | **Prob. Combinata**: {comb_prob}% | **EV**: +{exp_val}\n\n")
            f.write("| # | Lega | Match | Esito | Quota | Prob. Stima | EV |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for idx, ev in enumerate(accumulator.get("events", []), 1):
                odds_val = float(ev.get("odds", 1.0))
                prob_val = float(ev.get("prob", 0.0))
                ev_val = float(ev.get("ev", ev.get("expected_value", 0.0)))
                f.write(f"| {idx} | {ev.get('league', 'N/A')} | {ev.get('match', 'N/A')} | {ev.get('selection', 'N/A')} | {odds_val:.2f} | {prob_val*100:.1f}% | +{ev_val:.4f} |\n")
        else:
            f.write("_Nessuna multipla generabile con i filtri impostati._\n")

    print(f"[OK] Report quotidiani esportati con successo in:\n - {md_path}\n - {json_path}")