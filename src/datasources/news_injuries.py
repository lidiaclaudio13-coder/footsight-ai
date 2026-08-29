import feedparser
import requests
from datetime import datetime
from src.core.db import get_db_connection

RSS_FEEDS = {
    "Gazzetta_Calcio": "https://www.gazzetta.it/rss/home.xml",
    "TuttoMercatoWeb_SerieA": "https://www.tuttomercatoweb.com/rss/?action=rubrica&id=11",
    "AS_Liga": "https://as.com/rss/futbol/primera.xml",
    "BBC_Football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "SkySports_Football": "https://www.skysports.com/rss/12040"
}

INJURY_KEYWORDS = [
    "infortunio", "infortunato", "lesione", "stop", "tegola", "squalificato",
    "risentimento", "operato", "frattura", "out", "assente", "lesion", "baja",
    "lesionado", "injured", "injury", "ruled out", "suspended", "clause"
]

def find_extracted_team(cursor, text):
    cursor.execute("SELECT team_id, canonical_name FROM teams")
    teams = cursor.fetchall()
    text_lower = text.lower()
    for team in teams:
        if team["canonical_name"].lower() in text_lower and len(team["canonical_name"]) > 3:
            return team["team_id"]
    return None

def fetch_rss_feed(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return feedparser.parse(response.content)
    except Exception as e:
        print(f"[!] Errore nel caricamento feed {url}: {e}")
    return None

def parse_all_rss_feeds():
    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0

    for source_name, feed_url in RSS_FEEDS.items():
        print(f"[*] Parsing feed RSS: {source_name}...")
        parsed_data = fetch_rss_feed(feed_url)

        if not parsed_data or not parsed_data.entries:
            print(f"    [!] Nessun elemento letto per {source_name}")
            continue

        for entry in parsed_data.entries:
            title = entry.get("title", "")
            description = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")

            full_text = f"{title} {description}"
            if any(keyword in full_text.lower() for keyword in INJURY_KEYWORDS):
                extracted_team_id = find_extracted_team(cursor, full_text)
                now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO rss_injuries_raw 
                        (source_name, title, description, link, published_at, extracted_team_id, confidence_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (source_name, title, description, link, now_str, extracted_team_id, 0.85)
                    )
                    if cursor.rowcount > 0:
                        saved_count += 1
                except Exception:
                    pass

    conn.commit()
    conn.close()
    print(f"[OK] Salvate {saved_count} notizie rilevanti su infortuni/squalifiche da RSS.")