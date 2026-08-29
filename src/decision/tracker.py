import json
from src.core.db import get_db_connection

def place_bet(bet_type, match_desc, selection, odds, stake):
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

def get_performance_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bets_tracker WHERE status != 'PENDING'")
    settled = cursor.fetchall()
    
    cursor.execute("SELECT * FROM bets_tracker WHERE status = 'PENDING'")
    pending = cursor.fetchall()
    conn.close()

    if not settled:
        return {
            "total_settled": 0,
            "pending": len(pending),
            "total_staked": 0.0,
            "total_profit": 0.0,
            "roi_pct": 0.0,
            "win_rate_pct": 0.0
        }

    total_staked = sum(r["stake"] for r in settled)
    total_profit = sum(r["profit_loss"] for r in settled)
    wins = sum(1 for r in settled if r["status"] == "WON")

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
    win_rate = (wins / len(settled) * 100) if settled else 0.0

    return {
        "total_settled": len(settled),
        "pending": len(pending),
        "total_staked": round(total_staked, 2),
        "total_profit": round(total_profit, 2),
        "roi_pct": round(roi, 2),
        "win_rate_pct": round(win_rate, 1)
    }
