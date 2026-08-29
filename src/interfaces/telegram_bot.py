import json
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from src.decision.accumulator import build_accumulator
from src.decision.single_finder import find_top_singles
from src.features.rolling_stats import build_all_features
from src.datasources.football_data import ingest_football_data
from src.datasources.news_injuries import parse_all_rss_feeds

def load_token():
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "telegram.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Configurazione non trovata: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("telegram_token")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 **FootSight AI Bot Operativo!**\n\n"
        "Ecco i comandi a tua disposizione:\n"
        "🎯 /multipla - Genera la multipla bilanciata (Quota max 10.0)\n"
        "📌 /singole - Estrae le Top 5 Value Bets con Kelly Stake\n"
        "⚡ /daily - Esegue la pipeline completa ed invia i report\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def multipla_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Calcolo multipla bilanciata in corso...")
    acc = build_accumulator(target_min_odds=4.0, target_max_odds=10.0, min_events=4, max_events=7)

    if not acc:
        await update.message.reply_text("❌ Nessuna multipla prudente generabile con i dati attuali.")
        return

    res = (
        f"🎯 **FOOTSIGHT AI — MULTIPLA (Quota {acc['total_odds']})**\n"
        f"📊 Prob. Combinata: `{acc['combined_prob']}%` | EV: `+{acc['expected_value']}`\n\n"
        f"**EVENTI IN SCHEDINA:**\n"
    )
    for idx, ev in enumerate(acc['events'], 1):
        res += f"{idx}. `[{ev['league']}]` {ev['match']}\n"
        res += f"   👉 Esito: *{ev['selection']}* | Quota: `{ev['odds']:.2f}` | Prob: `{round(ev['prob']*100, 1)}%`\n"

    await update.message.reply_text(res, parse_mode="Markdown")

async def singole_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Ricerca Top Value Bets in corso...")
    singles = find_top_singles(top_n=5)

    if not singles:
        await update.message.reply_text("❌ Nessuna scommessa singola a valore trovata.")
        return

    res = "📌 **TOP VALUE BETS SINGOLE (Kelly Stake)**\n\n"
    for idx, s in enumerate(singles, 1):
        res += f"{idx}. `[{s['league']}]` {s['match']}\n"
        res += f"   👉 Esito: *{s['selection']}* | Quota: `{s['odds']:.2f}`\n"
        res += f"   📈 Prob: `{round(s['prob_est']*100, 1)}%` | EV: `+{s['ev']:.4f}` | **Stake: {s['stake_pct']}%**\n\n"

    await update.message.reply_text(res, parse_mode="Markdown")

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ **Avvio Pipeline quotidiana completa...**\n(Aggiornamento dati, notizie ed elaborazione feature)")

    try:
        ingest_football_data(season_code="2526")
        parse_all_rss_feeds()
        build_all_features()
        await update.message.reply_text("✅ Pipeline completata! Invio report in corso...")
        await singole_command(update, context)
        await multipla_command(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Errore durante la pipeline: {e}")

def run_telegram_bot():
    token = load_token()
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("multipla", multipla_command))
    app.add_handler(CommandHandler("singles", singole_command))
    app.add_handler(CommandHandler("singole", singole_command))
    app.add_handler(CommandHandler("daily", daily_command))

    print("[*] Bot Telegram FootSight AI avviato ed in ascolto...")
    app.run_polling()
