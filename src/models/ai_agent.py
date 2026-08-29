import os
import requests
import streamlit as st
from src.core.db import get_db_connection

# Legge la chiave dalle variabili d'ambiente o dai Secrets di Streamlit
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_match_news_context(home_team, away_team):
    """Recupera le notizie e gli infortuni più recenti per le due squadre coinvolte."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT source_name, title, description 
        FROM rss_injuries_raw 
        WHERE LOWER(title) LIKE ? OR LOWER(title) LIKE ?
           OR LOWER(description) LIKE ? OR LOWER(description) LIKE ?
        ORDER BY id DESC LIMIT 4
    """
    h_term = f"%{home_team.lower()}%"
    a_term = f"%{away_team.lower()}%"
    
    cursor.execute(query, (h_term, a_term, h_term, a_term))
    news = cursor.fetchall()
    conn.close()
    
    if not news:
        return "Nessuna notizia o infortunio critico segnalato di recente dalle fonti RSS."
    
    news_text = "NOTIZIE RECENTI E INFORTUNI DALLE TESTATE:\n"
    for n in news:
        news_text += f"- [{n['source_name']}] {n['title']}: {n['description'][:120]}...\n"
    return news_text

def get_agent_memory():
    """Recupera dallo storico le ultime giocate perse per apprendere dagli errori."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT match_description, selection, profit_loss 
        FROM bets_tracker 
        WHERE status = 'LOST' 
        ORDER BY bet_id DESC LIMIT 3
        """
    )
    losses = cursor.fetchall()
    conn.close()
    
    if not losses:
        return "Nessun errore passato registrato."
    
    memory_text = "STORICO ERRORI DA VALUTARE:\n"
    for l in losses:
        memory_text += f"- Partita: {l['match_description']} | Selezione errata: {l['selection']}\n"
    return memory_text

def analyze_with_ollama(match_desc, selection, odds, prob, ev, model_name="llama-3.1-8b-instant"):
    """
    Effettua la chiamata cloud tramite Groq per generare l'analisi tattico-sportiva.
    """
    teams = match_desc.split(" vs ")
    home_team = teams[0].strip() if len(teams) > 0 else ""
    away_team = teams[1].strip() if len(teams) > 1 else ""

    news_context = get_match_news_context(home_team, away_team)
    memory = get_agent_memory()
    
    prompt = f"""
    Sei un giornalista sportivo e analista tattico di calcio esperto per FootSight AI. 
    Analizza il seguente pronostico integrando i dati con il contesto calcistico e le notizie di campo.

    PARTITA: {match_desc}
    ESITO PROPOSTO: {selection} (Quota: {odds})
    STIMA ANALITICA: Probabilità {prob * 100:.1f}%, Expected Value +{ev:.4f}

    {news_context}

    {memory}

    ISTRUZIONI PER LA RISPOSTA:
    1. ESITO AGENTE: Scegli [APPROVATO] o [RESPINTO]
    2. MOTIVAZIONE SPORTIVA: Scrivi un'analisi da opinionista calcistico (max 3-4 frasi). Parla di forma recente delle squadre, fattore campo, stile di gioco, assenze o motivazioni di classifica. NON limitarti a ripetere i numeri matematici dell'EV o delle probabilità.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "json/application"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "Sei un analista calcistico professionale e sintetico."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_data = response.json()
            return res_data["choices"][0]["message"]["content"]
        else:
            return f"[!] Errore Groq API (Status {response.status_code}): {response.text}"
    except Exception as e:
        return f"[!] Errore di connessione a Groq: {e}"