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
                f.write(f"| {idx} | {s['league']} | {s['match']} | {s['selection']} | {s['odds']:.2f} | {s['prob_est']*100:.1f}% | +{s['edge']*100:.1f}% | +{s['ev']:.4f} | {s['stake_pct']}% |\n")
        else:
            f.write("_Nessuna singola a valore trovata per oggi._\n")
            
        f.write("\n\n## 🎯 Multiple Consigliata (Target Quota 15+)\n")
        if accumulator:
            f.write(f"**Quota Totale**: {accumulator['total_odds']} | **Prob. Combinata**: {accumulator['combined_prob']}% | **EV**: +{accumulator['expected_value']}\n\n")
            f.write("| # | Lega | Match | Esito | Quota | Prob. Stima | EV |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for idx, ev in enumerate(accumulator["events"], 1):
                f.write(f"| {idx} | {ev['league']} | {ev['match']} | {ev['selection']} | {ev['odds']:.2f} | {ev['prob']*100:.1f}% | +{ev['ev']:.4f} |\n")
        else:
            f.write("_Nessuna multipla generabile con i filtri impostati._\n")

    print(f"[OK] Report quotidiani esportati con successo in:\n - {md_path}\n - {json_path}")
