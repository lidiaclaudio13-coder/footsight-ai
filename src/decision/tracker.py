from src.core.db import get_db_connection

def place_bet(bet_type, match_desc, selection, odds, stake):
    if stake <= 0 or odds <= 1.0:
        print("[ERROR] Impossibile registrare la scommessa: Stake e Quota devono essere maggiori di zero.")
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bets_tracker (bet_type, match_description, selection, odds, stake, status)
        VALUES (?, ?, ?, ?, ?, 'PENDING')
        """,
        (bet_type, match_desc, selection, odds, stake)
    )
    conn.commit()
    bet_id = cursor.lastrowid
    conn.close()
    print(f"[OK] Scommessa registrata con successo nel Tracker! ID: {bet_id}")
    return bet_id

def settle_bet(bet_id, result):
    result = result.upper()
    if result not in ["WON", "LOST"]:
        print("[ERROR] Il risultato deve essere 'WON' o 'LOST'")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT odds, stake FROM bets_tracker WHERE bet_id=?", (bet_id,))
    row = cursor.fetchone()
    if not row:
        print(f"[ERROR] Scommessa ID {bet_id} non trovata.")
        conn.close()
        return

    odds = row["odds"]
    stake = row["stake"]

    if result == "WON":
        payout = stake * odds
        profit = payout - stake
    else:
        payout = 0.0
        profit = -stake

    cursor.execute(
        """
        UPDATE bets_tracker 
        SET status=?, payout=?, profit_loss=?
        WHERE bet_id=?
        """,
        (result, payout, profit, bet_id)
    )
    conn.commit()
    conn.close()
    print(f"[OK] Scommessa ID {bet_id} aggiornata come {result}! (P&L: {profit:+.2f}€)")

from src.core.db import get_db_connection

def get_performance_summary():
    """
    Recupera le statistiche di performance dal tracker.
    Crea la tabella se non esiste ed evita crash in assenza di dati.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Assicura che la tabella esista per evitare OperationalError
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets_tracker (
            bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_description TEXT,
            selection TEXT,
            odds REAL,
            stake REAL,
            status TEXT DEFAULT 'PENDING',
            profit_loss REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    try:
        cursor.execute("SELECT * FROM bets_tracker WHERE status != 'PENDING'")
        settled_bets = cursor.fetchall()

        if not settled_bets:
            conn.close()
            return {
                "total_bets": 0,
                "won": 0,
                "lost": 0,
                "win_rate": "0.0%",
                "total_staked": 0.0,
                "total_profit": 0.0,
                "roi": "0.0%"
            }

        total = len(settled_bets)
        won = sum(1 for b in settled_bets if b["status"] == "WON")
        lost = sum(1 for b in settled_bets if b["status"] == "LOST")
        total_staked = sum(b["stake"] for b in settled_bets)
        total_profit = sum(b["profit_loss"] for b in settled_bets)
        win_rate = (won / total * 100) if total > 0 else 0.0
        roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0

        conn.close()
        return {
            "total_bets": total,
            "won": won,
            "lost": lost,
            "win_rate": f"{win_rate:.1f}%",
            "total_staked": round(total_staked, 2),
            "total_profit": round(total_profit, 2),
            "roi": f"{roi:.1f}%"
        }
    except Exception as e:
        conn.close()
        return {"error": f"Errore recupero dati: {str(e)}"}
