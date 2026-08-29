import sys
import json
from pathlib import Path
from src.core.db import init_db, get_db_connection
from src.datasources.football_data import ingest_football_data
from src.datasources.odds_api import fetch_and_store_odds
from src.datasources.news_injuries import parse_all_rss_feeds
from src.features.rolling_stats import build_all_features
from src.decision.accumulator import build_accumulator
from src.decision.single_finder import find_top_singles
from src.decision.tracker import place_bet, settle_bet, get_performance_summary
from src.models.evaluator import run_backtest
from src.reporting.cli_reporter import print_accumulator_report, print_singles_report, print_tracker_summary
from src.reporting.exporter import export_daily_report

TARGET_LEAGUES_FOR_ODDS = [
    "IT_SA", "IT_SB", 
    "ES_LL", "ES_LL2", 
    "DE_BL1", "DE_BL2", 
    "FR_L1", "FR_L2", 
    "NL_ERE", "BE_PL", "AT_BL"
]

def load_leagues_seed():
    config_path = Path(__file__).resolve().parent / "config" / "leagues.json"
    if not config_path.exists():
        print(f"[ERROR] File di configurazione non trovato: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_db_connection()
    cursor = conn.cursor()

    for l in data.get("leagues", []):
        cursor.execute(
            """
            INSERT INTO leagues (league_id, country, name, tier, fd_code)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(league_id) DO UPDATE SET
                country=excluded.country,
                name=excluded.name,
                tier=excluded.tier,
                fd_code=excluded.fd_code;
            """,
            (l["league_id"], l["country"], l["name"], l["tier"], l["fd_code"])
        )

    conn.commit()
    conn.close()
    print("[OK] Campionati registrati con successo nel DB.")

def run_daily_pipeline(season="2526", target_max_odds=10.0):
    print("\n==================================================")
    print("      AVVIO AUTOMATICO PIPELINE FOOTSIGHT AI      ")
    print("==================================================\n")

    print("[STEP 1/4] Aggiornamento risultati e calendario per tutti i campionati...")
    ingest_football_data(season_code=season)

    print("\n[STEP 2/4] Aggiornamento quote live multi-lega...")
    for league_id in TARGET_LEAGUES_FOR_ODDS:
        fetch_and_store_odds(league_id=league_id)

    print("\n[STEP 3/4] Parsing notizie RSS (Infortuni/Squalifiche)...")
    parse_all_rss_feeds()

    print("\n[STEP 4/4] Calcolo matrice delle feature (Anti-Leakage)...")
    build_all_features()

    print("\n" + "="*50)
    print("              REPORT GIORNALIERO GENERATO         ")
    print("="*50 + "\n")

    singles = find_top_singles(top_n=5)
    print_singles_report(singles)

    acc = build_accumulator(target_min_odds=4.0, target_max_odds=target_max_odds, min_events=4, max_events=7)
    print_accumulator_report(acc)

    export_daily_report(singles, acc)

def print_help():
    print("\n==================================================")
    print("          FOOTSIGHT AI - COMANDI LOCALI           ")
    print("==================================================")
    print("  init-db              : Inizializza il DB SQLite e le leghe")
    print("  daily-run            : Esegue l'intera pipeline dati + report")
    print("  generate-multipla    : Genera la schedina (es: generate-multipla 15.0)")
    print("  generate-singles     : Trova le top value bets (es: generate-singles 5)")
    print("  backtest             : Esegue il test di calibrazione (Brier Score)")
    print("  ingest               : Scarica i risultati storici")
    print("  fetch-odds           : Scarica le quote live (all o singola lega)")
    print("  parse-rss            : Aggiorna infortuni e news")
    print("  build-features       : Ricalcola le statistiche rolling")
    print("  tracker-stats        : Mostra il rendimento del tuo bankroll")
    print("==================================================\n")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "init-db":
        init_db()
        load_leagues_seed()
    elif command == "ingest":
        season = sys.argv[2] if len(sys.argv) > 2 else "2526"
        ingest_football_data(season_code=season)
    elif command == "fetch-odds":
        target = sys.argv[2] if len(sys.argv) > 2 else "all"
        if target == "all":
            for l_id in TARGET_LEAGUES_FOR_ODDS:
                fetch_and_store_odds(league_id=l_id)
        else:
            fetch_and_store_odds(league_id=target)
    elif command == "parse-rss":
        parse_all_rss_feeds()
    elif command == "build-features":
        build_all_features()
    elif command == "generate-multipla":
        max_odds = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
        acc = build_accumulator(target_min_odds=4.0, target_max_odds=max_odds, min_events=4, max_events=7)
        print_accumulator_report(acc)
    elif command == "generate-singles":
        top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        singles = find_top_singles(top_n=top_n)
        print_singles_report(singles)
    elif command == "backtest":
        res = run_backtest()
        if res:
            print("\n==================================================")
            print("         FOOTSIGHT AI - BACKTEST REPORT           ")
            print("==================================================")
            print(f"Partite Analizzate: {res['processed_matches']}")
            print(f"Brier Score Medio: {res['mean_brier_score']} (Ideal < 0.20)")
            print(f"Stato Calibrazione: {res['calibration_status']}")
            print("==================================================\n")
    elif command == "daily-run":
        run_daily_pipeline()
    elif command == "place-bet":
        b_type = sys.argv[2]
        match_desc = sys.argv[3]
        selection = sys.argv[4]
        odds = float(sys.argv[5])
        stake = float(sys.argv[6])
        place_bet(b_type, match_desc, selection, odds, stake)
    elif command == "settle-bet":
        b_id = int(sys.argv[2])
        res = sys.argv[3]
        settle_bet(b_id, res)
    elif command == "tracker-stats":
        sum_data = get_performance_summary()
        print_tracker_summary(sum_data)
    else:
        print(f"Comando sconosciuto: '{command}'")
        print_help()

if __name__ == "__main__":
    main()
