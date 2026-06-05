import streamlit as st
import pandas as pd
import requests
import re
import json
import os
import math
import sqlite3
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
from streamlit_js_eval import streamlit_js_eval
import plotly.express as px

# --- CONFIGURARE PAGINĂ STREAMLIT ---
st.set_page_config(
    page_title="VeloTM Radar",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONFIGURĂRI DE BAZĂ ȘI DIRECTOARE ---
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "history.sqlite")
os.makedirs(DB_DIR, exist_ok=True)

# Coordonate implicite pentru Timișoara (Centru)
TIMISOARA_CENTER = (45.75372, 21.22571)

# Preseturi de coordonate pentru stațiile de interes
LOCATION_PRESETS = {
    "Centru (Piața Victoriei)": (45.75372, 21.22571),
    "Gara de Nord": (45.75051, 21.20815),
    "Iulius Town": (45.76632, 21.22915),
    "Spitalul Județean": (45.73912, 21.24225),
    "Complexul Studențesc (Facultate)": (45.74681, 21.23925),
    "Acasă (Configurat în Sidebar)": None
}

DEMO_HTML = """
<html>
<body>
<script>
function showStations() {
    var items = [{"StationName":"1 - Modern","Address":"Statia 1 - Modern","OcuppiedSpots":15,"EmptyDoors":24,"Status":"Online","Latitude":45.760420,"Longitude":21.258490},{"StationName":"3 - Mocioni Prefectura","Address":"statia 3 mocioni prefectura ","OcuppiedSpots":3,"EmptyDoors":15,"Status":"Subpopulated","Latitude":45.756760,"Longitude":21.240950},{"StationName":"4 - Pod DaVinci","Address":"Statia4 - Pod DaVinci","OcuppiedSpots":8,"EmptyDoors":29,"Status":"Subpopulated","Latitude":45.750320,"Longitude":21.235380},{"StationName":"6 - Pod Traian","Address":"Pod Traian","OcuppiedSpots":0,"EmptyDoors":22,"Status":"Offline","Latitude":45.749650,"Longitude":21.220270},{"StationName":"8 - Golf","Address":"Statia 8 - Golf","OcuppiedSpots":9,"EmptyDoors":8,"Status":"Online","Latitude":45.742410,"Longitude":21.196290},{"StationName":"Ana Ipatescu","Address":"Ana Ipatescu","OcuppiedSpots":0,"EmptyDoors":16,"Status":"Offline","Latitude":45.728310,"Longitude":21.204950},{"StationName":"Aries","Address":"Bulbuca cu Aries","OcuppiedSpots":1,"EmptyDoors":3,"Status":"Offline","Latitude":45.738000,"Longitude":21.242050},{"StationName":"Armoniei","Address":"Armoniei","OcuppiedSpots":12,"EmptyDoors":4,"Status":"Online","Latitude":45.779890,"Longitude":21.234540},{"StationName":"Bogdanesti - Cetatii","Address":"a115","OcuppiedSpots":9,"EmptyDoors":9,"Status":"Online","Latitude":45.757800,"Longitude":21.209690},{"StationName":"Carol 1","Address":"Carol 1 cu Dragalina","OcuppiedSpots":5,"EmptyDoors":11,"Status":"Subpopulated","Latitude":45.744750,"Longitude":21.210790},{"StationName":"Cons. Europei","Address":"Piata Consiliul Europei","OcuppiedSpots":0,"EmptyDoors":16,"Status":"Offline","Latitude":45.765620,"Longitude":21.225930},{"StationName":"Divizia 9 Cavalerie","Address":"Divizia 9 Cavalerie","OcuppiedSpots":5,"EmptyDoors":14,"Status":"Subpopulated","Latitude":45.769030,"Longitude":21.229960},{"StationName":"Domasneanu","Address":"Domasneanu","OcuppiedSpots":0,"EmptyDoors":36,"Status":"Offline","Latitude":45.732790,"Longitude":21.258270},{"StationName":"Felix","Address":"Felix","OcuppiedSpots":5,"EmptyDoors":32,"Status":"Subpopulated","Latitude":45.777770,"Longitude":21.220480},{"StationName":"Kaufland","Address":"Kaufland(Gh Lazar)","OcuppiedSpots":5,"EmptyDoors":12,"Status":"Online","Latitude":45.760540,"Longitude":21.218670},{"StationName":"Kogalniceanu","Address":"Kogalniceanu","OcuppiedSpots":0,"EmptyDoors":15,"Status":"Offline","Latitude":45.762780,"Longitude":21.247640},{"StationName":"Lct. Ovidiu Balea","Address":"Lct Ovidiu Balea","OcuppiedSpots":0,"EmptyDoors":27,"Status":"Offline","Latitude":45.766470,"Longitude":21.193930},{"StationName":"Libertatii","Address":"Libertatii","OcuppiedSpots":2,"EmptyDoors":13,"Status":"Subpopulated","Latitude":45.755960,"Longitude":21.226760},{"StationName":"Liege","Address":"Liege","OcuppiedSpots":0,"EmptyDoors":11,"Status":"Offline","Latitude":45.775000,"Longitude":21.221270},{"StationName":"Mihai Viteazu","Address":"Mihai Viteazu","OcuppiedSpots":8,"EmptyDoors":11,"Status":"Online","Latitude":45.744930,"Longitude":21.225740},{"StationName":"Piata 700","Address":"Piata 700","OcuppiedSpots":4,"EmptyDoors":12,"Status":"Subpopulated","Latitude":45.756510,"Longitude":21.223300},{"StationName":"Piata Leonardo DaVinci","Address":"Piata Leonardo DaVinci","OcuppiedSpots":0,"EmptyDoors":1,"Status":"Offline","Latitude":45.748330,"Longitude":21.235670},{"StationName":"Piata Marasti","Address":"Piata Marasti","OcuppiedSpots":8,"EmptyDoors":10,"Status":"Online","Latitude":45.759350,"Longitude":21.228380},{"StationName":"Piata Mocioni","Address":"Piata Mocioni","OcuppiedSpots":0,"EmptyDoors":15,"Status":"Subpopulated","Latitude":45.746140,"Longitude":21.215050},{"StationName":"Piata Virgil Economu","Address":"Piata Virgil Economu","OcuppiedSpots":0,"EmptyDoors":37,"Status":"Offline","Latitude":45.766020,"Longitude":21.261310},{"StationName":"Posta Centrala","Address":"Posta Centrala","OcuppiedSpots":7,"EmptyDoors":12,"Status":"Online","Latitude":45.754710,"Longitude":21.233770},{"StationName":"Profi","Address":"Profi - Str Sagului cu Str Rebreanu","OcuppiedSpots":1,"EmptyDoors":10,"Status":"Offline","Latitude":45.732860,"Longitude":21.209020},{"StationName":"Regele Ferdinand","Address":"Str. Regele Ferdinand","OcuppiedSpots":5,"EmptyDoors":14,"Status":"Subpopulated","Latitude":45.751130,"Longitude":21.223760},{"StationName":"Ripensia","Address":"Sala Olimpia","OcuppiedSpots":3,"EmptyDoors":10,"Status":"Subpopulated","Latitude":45.745250,"Longitude":21.241630},{"StationName":"Statia 26 Cetatii SmartFit","Address":"Bulevardul Cetatii - SmartFit","OcuppiedSpots":7,"EmptyDoors":13,"Status":"Online","Latitude":45.768590,"Longitude":21.218350},{"StationName":"Statia 27 Cetatii San Marzano","Address":"Bulevardul Cetatii - San Marzano","OcuppiedSpots":5,"EmptyDoors":15,"Status":"Subpopulated","Latitude":45.767560,"Longitude":21.216710},{"StationName":"Statia 28 Cetatii Colt Amforei","Address":"Bulevardul Cetatii - Colt Amforei ","OcuppiedSpots":2,"EmptyDoors":17,"Status":"Subpopulated","Latitude":45.765440,"Longitude":21.213410},{"StationName":"Statia 30 Cetatii Gh. Lazar","Address":"Bulevardul Cetatii - Gh. Lazar","OcuppiedSpots":5,"EmptyDoors":15,"Status":"Subpopulated","Latitude":45.763320,"Longitude":21.211090},{"StationName":"Statia 31Cetatii Gh. Lazar","Address":"Bulevardul Cetatii - Gh. Lazar","OcuppiedSpots":5,"EmptyDoors":15,"Status":"Subpopulated","Latitude":45.763260,"Longitude":21.211080},{"StationName":"Statia2 - Badea Cartan","Address":"statia 2 badea cartan","OcuppiedSpots":0,"EmptyDoors":19,"Status":"Offline","Latitude":45.760630,"Longitude":21.249290},{"StationName":"Statia5 - Savoy","Address":"Statia5 - Savoy","OcuppiedSpots":13,"EmptyDoors":27,"Status":"Online","Latitude":45.748580,"Longitude":21.225070},{"StationName":"Statia7-Dragalina","Address":"Pod Dragalina","OcuppiedSpots":0,"EmptyDoors":17,"Status":"Offline","Latitude":45.747020,"Longitude":21.209290},{"StationName":"Statia9 - Pod Modos","Address":"Statia9 - Pod Modos","OcuppiedSpots":0,"EmptyDoors":36,"Status":"Offline","Latitude":45.738900,"Longitude":21.185420},{"StationName":"Take Ionescu","Address":"Take Ionescu","OcuppiedSpots":8,"EmptyDoors":11,"Status":"Online","Latitude":45.757980,"Longitude":21.234140},{"StationName":"Torontanului Bucovinei","Address":"Torontanului cu Bucovinei","OcuppiedSpots":9,"EmptyDoors":11,"Status":"Online","Latitude":45.772040,"Longitude":21.216820},{"StationName":"Vidrighin - 1 Dec 1918","Address":"a1","OcuppiedSpots":10,"EmptyDoors":9,"Status":"Online","Latitude":45.748420,"Longitude":21.253530},{"StationName":"Vidrighin - Chimistilor","Address":"a112","OcuppiedSpots":9,"EmptyDoors":10,"Status":"Online","Latitude":45.741250,"Longitude":21.256100},{"StationName":"Vidrighin - Piata Domasnean","Address":"a113","OcuppiedSpots":6,"EmptyDoors":12,"Status":"Online","Latitude":45.734190,"Longitude":21.258680},{"StationName":"Vidrighin - Podeanu","Address":"a111","OcuppiedSpots":10,"EmptyDoors":10,"Status":"Online","Latitude":45.744970,"Longitude":21.254360}];
}
</script>
</body>
</html>
"""

# --- INIȚIALIZARE ȘI GESTIUNE BAZĂ DE DATE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabela pentru instantanee
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS station_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            station_name TEXT NOT NULL,
            address TEXT,
            bikes_available INTEGER,
            empty_doors INTEGER,
            status TEXT,
            latitude REAL,
            longitude REAL
        )
    """)
    # Tabela pentru favorite locale (peristente în SQLite)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            station_name TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- FUNCȚII TEHNICE / AJUTĂTOARE ---

@st.cache_data(ttl=15, show_spinner=False)
def fetch_page(url, cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    if cookie:
        headers["Cookie"] = cookie
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise RuntimeError(f"Nu s-a putut accesa URL-ul. Detalii: {str(e)}")

def extract_stations_from_html(html):
    # Căutare robustă folosind expresii regulate pe pattern-ul stabilit
    items_match = re.search(
        r"var\s+items\s*=\s*(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])\s*;",
        html,
        re.DOTALL
    )
    if not items_match:
        # Fallback mai permisiv dacă lipsesc spații sau structura are mici variații
        items_match = re.search(
            r"(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])",
            html,
            re.DOTALL
        )
        if not items_match:
            raise ValueError("Nu s-a detectat structura de date JavaScript 'items' în codul paginii.")
            
    try:
        return json.loads(items_match.group(1))
    except Exception as e:
        raise ValueError(f"Eroare la parsarea obiectului JSON obținut: {str(e)}")

def normalize_stations(raw_data):
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    
    # Redenumire câmpuri greșite/originale la cele standard românești solicitate
    mapping = {
        "StationName": "Statie",
        "Address": "Adresa",
        "OcuppiedSpots": "Biciclete disponibile",
        "EmptyDoors": "Locuri goale",
        "Status": "Status",
        "Latitude": "lat",
        "Longitude": "lon"
    }
    
    for orig, target in mapping.items():
        if orig not in df.columns:
            df[orig] = 0 if orig in ["OcuppiedSpots", "EmptyDoors"] else ""
            
    df = df.rename(columns=mapping)
    
    # Curățare și conversii tipuri
    df["Biciclete disponibile"] = pd.to_numeric(df["Biciclete disponibile"], errors='coerce').fillna(0).astype(int)
    df["Locuri goale"] = pd.to_numeric(df["Locuri goale"], errors='coerce').fillna(0).astype(int)
    df["lat"] = pd.to_numeric(df["lat"], errors='coerce').fillna(TIMISOARA_CENTER[0])
    df["lon"] = pd.to_numeric(df["lon"], errors='coerce').fillna(TIMISOARA_CENTER[1])
    df["Statie"] = df["Statie"].astype(str).str.strip()
    df["Status"] = df["Status"].astype(str).str.strip()
    
    # Calcularea scorurilor practice
    df["Scor preluare"] = df.apply(lambda r: calculate_pickup_score(r), axis=1)
    df["Scor returnare"] = df.apply(lambda r: calculate_return_score(r), axis=1)
    
    return df

def calculate_pickup_score(row):
    if row["Status"] != "Online":
        return "Inutilă momentan"
    bikes = row["Biciclete disponibile"]
    if bikes > 5:
        return "Excelentă pentru preluare"
    elif 3 <= bikes <= 5:
        return "OK"
    elif 1 <= bikes <= 2:
        return "Riscantă"
    return "Fără biciclete"

def calculate_return_score(row):
    if row["Status"] != "Online":
        return "Nu poți returna"
    doors = row["Locuri goale"]
    if doors > 5:
        return "Excelentă pentru returnare"
    elif 3 <= doors <= 5:
        return "OK pentru returnare"
    elif 1 <= doors <= 2:
        return "Riscantă pentru returnare"
    return "Nu poți returna"

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Kilometri
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_nearest_bike_stations(df, user_lat, user_lon, n=3):
    # Filtrăm doar stațiile online care au efectiv biciclete
    valid = df[(df["Status"] == "Online") & (df["Biciclete disponibile"] > 0)].copy()
    if valid.empty:
        return pd.DataFrame()
    valid["Distanță (m)"] = valid.apply(lambda r: int(haversine_distance(user_lat, user_lon, r["lat"], r["lon"]) * 1000), axis=1)
    return valid.sort_values("Distanță (m)").head(n)

def get_nearest_return_stations(df, user_lat, user_lon, n=3):
    # Filtrăm doar stațiile online care au porți libere
    valid = df[(df["Status"] == "Online") & (df["Locuri goale"] > 0)].copy()
    if valid.empty:
        return pd.DataFrame()
    valid["Distanță (m)"] = valid.apply(lambda r: int(haversine_distance(user_lat, user_lon, r["lat"], r["lon"]) * 1000), axis=1)
    return valid.sort_values("Distanță (m)").head(n)

# --- INTEGRARE ISTORIC SQLite ---
def save_snapshot_to_sqlite(df):
    try:
        conn = sqlite3.connect(DB_PATH)
        now_str = datetime.now().isoformat()
        records = []
        for _, r in df.iterrows():
            records.append((
                now_str,
                r["Statie"],
                r["Adresa"],
                int(r["Biciclete disponibile"]),
                int(r["Locuri goale"]),
                r["Status"],
                float(r["lat"]),
                float(r["lon"])
            ))
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO station_snapshots (timestamp, station_name, address, bikes_available, empty_doors, status, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"Eroare la salvarea istoricului local în SQLite: {e}")

def load_history_from_sqlite(limit_days=7):
    try:
        conn = sqlite3.connect(DB_PATH)
        limit_date = (datetime.now() - timedelta(days=limit_days)).isoformat()
        query = "SELECT * FROM station_snapshots WHERE timestamp >= ? ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn, params=(limit_date,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# --- COMPARTIMENT FAVORITE PERSISTENTE ---
def get_favorites():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT station_name FROM favorites")
        favs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return favs
    except Exception:
        return []

def add_favorite(station_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO favorites (station_name) VALUES (?)", (station_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def remove_favorite(station_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE station_name = ?", (station_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass

# --- ALERTE ȘI NOTIFICĂRI TELEGRAM ---
def detect_station_changes(current_df, previous_df):
    if previous_df is None or previous_df.empty or current_df is None or current_df.empty:
        return []
    
    changes = []
    # Aliniem seturile de date după numele stației
    curr_indexed = current_df.set_index("Statie")
    prev_indexed = previous_df.set_index("Statie")
    
    for name in curr_indexed.index.intersection(prev_indexed.index):
        c_row = curr_indexed.loc[name]
        p_row = prev_indexed.loc[name]
        
        # Schimbare status de conectivitate
        if c_row["Status"] != p_row["Status"]:
            changes.append({
                "Statie": name,
                "Tip": "Status Conexiune",
                "Mesaj": f"Stația a trecut de la {p_row['Status']} la {c_row['Status']}"
            })
            
        # Trecerea de la 0 la cel puțin o bicicletă disponibilă
        if p_row["Biciclete disponibile"] == 0 and c_row["Biciclete disponibile"] > 0:
            changes.append({
                "Statie": name,
                "Tip": "Bicicletă Disponibilă",
                "Mesaj": f"Oportunitate! Sunt disponibile {c_row['Biciclete disponibile']} biciclete (anterior erau 0)."
            })
            
        # Trecerea de la biciclete disponibile la complet goală
        if p_row["Biciclete disponibile"] > 0 and c_row["Biciclete disponibile"] == 0:
            changes.append({
                "Statie": name,
                "Tip": "Stație Goală",
                "Mesaj": "Atenție! Nu mai există nicio bicicletă disponibilă la această stație."
            })
            
        # Trecerea de la 0 la porți libere pentru returnare
        if p_row["Locuri goale"] == 0 and c_row["Locuri goale"] > 0:
            changes.append({
                "Statie": name,
                "Tip": "Locuri de Returnare",
                "Mesaj": f"Puteți returna acum! S-au eliberat {c_row['Locuri goale']} porți (anterior 0)."
            })
            
    return changes

def send_telegram_notification(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# --- METEO ---
def get_weather_score(api_key):
    if not api_key:
        return None
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Timisoara,RO&appid={api_key}&units=metric"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            temp = data["main"]["temp"]
            weather_desc = data["weather"][0]["main"].lower()
            wind_speed = data["wind"]["speed"]
            
            # Algoritm simplu de scoring meteo 0-10
            score = 10
            penalty_reasons = []
            
            if "rain" in weather_desc or "drizzle" in weather_desc:
                score -= 4
                penalty_reasons.append("ploaie")
            if "snow" in weather_desc:
                score -= 6
                penalty_reasons.append("ninsoare")
            if temp < 5:
                score -= 3
                penalty_reasons.append("frig extrem")
            elif temp > 35:
                score -= 2
                penalty_reasons.append("caniculă")
            if wind_speed > 10:
                score -= 2
                penalty_reasons.append("vânt puternic")
                
            score = max(0, score)
            return {
                "scor": score,
                "temp": temp,
                "desc": data["weather"][0]["description"],
                "penalizari": penalty_reasons
            }
    except Exception:
        pass
    return None

# --- ÎNCĂRCARE DATE ÎN SESSION STATE ---
if "stations_df" not in st.session_state:
    st.session_state.stations_df = None
if "prev_stations_df" not in st.session_state:
    st.session_state.prev_stations_df = None
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = None
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set() # pentru a nu trimite notificări duplicate

def run_update(url, cookie, use_demo):
    try:
        if use_demo:
            html = DEMO_HTML
        else:
            html = fetch_page(url, cookie)
            
        raw_data = extract_stations_from_html(html)
        df_new = normalize_stations(raw_data)
        
        # Salvăm snapshot-ul în starea curentă
        st.session_state.prev_stations_df = st.session_state.stations_df
        st.session_state.stations_df = df_new
        st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
        st.session_state.error_msg = None
        
        # Salvare în baza de date SQLite
        save_snapshot_to_sqlite(df_new)
        
    except Exception as e:
        st.session_state.error_msg = str(e)

# --- SIDEBAR CONFIGURARE ---
st.sidebar.title("🛠️ Setări Sistem")

# Parametri de conectare
url_input = st.sidebar.text_input("VeloTM URL:", value="https://www.ratt.ro/vtm/harta-statii-biciclete")
use_demo = st.sidebar.checkbox("Mod Offline (Date Demo)", value=False, help="Bifați dacă serverul VeloTM nu răspunde.")

cookie_val = st.secrets.get("vtm_cookie", "")
cookie_input = st.sidebar.text_input("Cookie sesiune (Opțional):", value=cookie_val, type="password")

# Auto-refresh configurabil
refresh_options = [0, 30, 60, 120, 300]
refresh_choice = st.sidebar.selectbox("Frecvență auto-actualizare:", options=refresh_options, format_func=lambda x: "Oprit" if x == 0 else f"{x} secunde")
if refresh_choice > 0:
    st_autorefresh(interval=refresh_choice * 1000, key="vtm_refresher")

st.sidebar.subheader("📍 Coordonate Acasă")
my_lat = st.sidebar.number_input("Latitudine:", value=45.75372, format="%.6f")
my_lon = st.sidebar.number_input("Longitudine:", value=21.22571, format="%.6f")
LOCATION_PRESETS["Acasă (Configurat în Sidebar)"] = (my_lat, my_lon)

# Notificări Telegram
st.sidebar.subheader("✈️ Notificări Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value=st.secrets.get("telegram_bot_token", ""), type="password")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID:", value=st.secrets.get("telegram_chat_id", ""))

# Serviciu Meteo
st.sidebar.subheader("🌤️ OpenWeather Integrat")
ow_key = st.sidebar.text_input("API Key (OpenWeather):", value=st.secrets.get("openweather_api_key", ""), type="password")

# Declanșator actualizare manuală
if st.sidebar.button("♻️ Actualizează Acum") or st.session_state.stations_df is None:
    run_update(url_input, cookie_input, use_demo)

# --- PROCESARE SCHIMBĂRI ȘI ALERTE ---
current_df = st.session_state.stations_df
prev_df = st.session_state.prev_stations_df

recent_changes = []
if current_df is not None and prev_df is not None:
    recent_changes = detect_station_changes(current_df, prev_df)
    fav_list = get_favorites()
    
    # Trimitem pe Telegram doar evenimentele noi legate de stațiile favorite
    for change in recent_changes:
        if change["Statie"] in fav_list:
            alert_key = f"{change['Statie']}_{change['Tip']}_{st.session_state.last_updated}"
            if alert_key not in st.session_state.sent_alerts:
                msg_body = f"🔔 *VeloTM Radar Alert* - {change['Statie']}\n{change['Mesaj']}"
                send_telegram_notification(tg_token, tg_chat_id, msg_body)
                st.session_state.sent_alerts.add(alert_key)

# --- INTERFAȚĂ ECRAN PRINCIPAL (MOBIL FRIENDLY) ---
st.title("🚲 VeloTM Radar")
st.markdown("Asistentul tău urban rapid pentru rețeaua de biciclete din Timișoara.")

if st.session_state.error_msg:
    st.error(f"Eroare date: {st.session_state.error_msg}")
    st.info("Puteți bifa 'Mod Offline (Date Demo)' din meniul lateral pentru a rula aplicația cu setul de date fallback.")

# --- BOX METEO ---
weather_data = get_weather_score(ow_key)
if weather_data:
    score = weather_data["scor"]
    temp = weather_data["temp"]
    desc = weather_data["desc"]
    
    if score >= 8:
        color = "green"
        verdict = "Excelent pentru bicicletă!"
    elif score >= 5:
        color = "orange"
        verdict = "Acceptabil, atenție la detalii."
    else:
        color = "red"
        verdict = "Mai bine folosești alt mijloc de transport."
        
    st.markdown(
        f"""
        <div style="background-color: #1e272e; padding: 12px; border-radius: 8px; border-left: 5px solid {color}; margin-bottom: 15px;">
            <p style="margin: 0; font-size: 14px; color: #a4b0be;">Meteo Timișoara: {temp}°C, {desc}</p>
            <h5 style="margin: 5px 0 0 0; color: white;">Scor Biking: <b>{score}/10</b> - <span style="color:{color};">{verdict}</span></h5>
        </div>
        """,
        unsafe_allow_name=True,
        unsafe_allow_html=True
    )

# --- SECȚIUNE LOCALIZARE LIVE ---
st.markdown("### 📍 Poziția ta curentă")
col_loc1, col_loc2 = st.columns([1, 1])

with col_loc1:
    location_mode = st.radio(
        "Sursă coordonate utilizator:",
        options=["Utilizează preset locație", "Detectează GPS Live (Mobil-friendly)"],
        horizontal=True
    )

user_lat, user_lon = TIMISOARA_CENTER[0], TIMISOARA_CENTER[1]
gps_detected = False

if location_mode == "Detectează GPS Live (Mobil-friendly)":
    # Extrage coordonatele prin API-ul nativ de geolocalizare din browser
    gps_loc = streamlit_js_eval(data_of='geolocation', key='gps_locator_eval')
    if gps_loc:
        user_lat = gps_loc['coords']['latitude']
        user_lon = gps_loc['coords']['longitude']
        st.success(f"GPS Identificat: {user_lat:.5f}, {user_lon:.5f}")
        gps_detected = True
    else:
        st.warning("Se așteaptă accesul la GPS... Asigurați-vă că ați oferit permisiunea browserului. Se folosește Centrul în mod implicit.")
else:
    preset_choice = st.selectbox("Alege o locație presetată:", options=list(LOCATION_PRESETS.keys()))
    coords = LOCATION_PRESETS[preset_choice]
    if coords:
        user_lat, user_lon = coords[0], coords[1]
        st.info(f"Poziție setată: {user_lat:.5f}, {user_lon:.5f}")

# --- METRICE GENERALE STATISTICI ---
if current_df is not None and not current_df.empty:
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Biciclete Disponibile", current_df["Biciclete disponibile"].sum())
    c2.metric("Porturi Libere", current_df["Locuri goale"].sum())
    c3.metric("Stații Online", current_df[current_df["Status"] == "Online"].shape[0])
    c4.metric("Stații Offline 🔴", current_df[current_df["Status"] == "Offline"].shape[0])
    c5.metric("Ultima Actualizare", st.session_state.last_updated)

    # --- TABURI PRINCIPALE TIP RADAR ---
    t_radar, t_route, t_commute, t_table, t_analytics = st.tabs([
        "🎯 RADAR RAPID", 
        "🗺️ PLANIFICATOR RUTE", 
        "🔄 COMMUTE MODE", 
        "📋 LISTĂ STAȚII",
        "📊 ISTORIC & ANALYTICS"
    ])

    with t_radar:
        col_pickup, col_return = st.columns(2)
        
        with col_pickup:
            st.subheader("🚶 Unde găsesc rapid o bicicletă?")
            near_bikes = get_nearest_bike_stations(current_df, user_lat, user_lon, n=3)
            
            if not near_bikes.empty:
                for _, r in near_bikes.iterrows():
                    color = "#2ecc71" if r["Scor preluare"] == "Excelentă pentru preluare" else "#f1c40f" if r["Scor preluare"] == "OK" else "#e67e22"
                    st.markdown(
                        f"""
                        <div style="background-color: #2c3a47; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 5px solid {color};">
                            <h5 style="margin:0; color:#f8f9fa;">{r['Statie']}</h5>
                            <p style="margin: 4px 0 0 0; font-size:14px; color:#bdc581;">
                                Distanță: <b>{r['Distanță (m)']} m</b> | Disponibile: <b style="color:#2ecc71;">{r['Biciclete disponibile']} biciclete</b>
                            </p>
                            <span style="font-size:12px; background-color:{color}; color:black; padding:2px 6px; border-radius:4px; font-weight:bold;">
                                {r['Scor preluare']}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.write("Nicio bicicletă disponibilă în apropiere.")
                
        with col_return:
            st.subheader("🏁 Unde pot lăsa bicicleta?")
            near_returns = get_nearest_return_stations(current_df, user_lat, user_lon, n=3)
            
            if not near_returns.empty:
                for _, r in near_returns.iterrows():
                    color = "#2ecc71" if r["Scor returnare"] == "Excelentă pentru returnare" else "#f1c40f" if r["Scor returnare"] == "OK pentru returnare" else "#e67e22"
                    st.markdown(
                        f"""
                        <div style="background-color: #2c3a47; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 5px solid {color};">
                            <h5 style="margin:0; color:#f8f9fa;">{r['Statie']}</h5>
                            <p style="margin: 4px 0 0 0; font-size:14px; color:#bdc581;">
                                Distanță: <b>{r['Distanță (m)']} m</b> | Porți libere: <b style="color:#3498db;">{r['Locuri goale']} locuri</b>
                            </p>
                            <span style="font-size:12px; background-color:{color}; color:black; padding:2px 6px; border-radius:4px; font-weight:bold;">
                                {r['Scor returnare']}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.write("Niciun loc de returnare disponibil în apropiere.")

        # --- FAVORITE GENERATE DIN REȚEA ---
        st.subheader("⭐️ Stațiile mele Favorite")
        my_favs = get_favorites()
        if my_favs:
            fav_df = current_df[current_df["Statie"].isin(my_favs)]
            if not fav_df.empty:
                f_cols = st.columns(len(fav_df)) if len(fav_df) < 5 else st.columns(4)
                for idx, (_, r) in enumerate(fav_df.iterrows()):
                    col_target = f_cols[idx % len(f_cols)]
                    col_target.markdown(
                        f"""
                        <div style="background-color:#1e272e; padding:12px; border-radius:8px; border-top: 4px solid #f1c40f; text-align:center;">
                            <h6 style="margin:0 0 5px 0;">{r['Statie']}</h6>
                            <p style="margin:2px 0; font-size:13px;">Biciclete: <b style="color:#2ecc71;">{r['Biciclete disponibile']}</b></p>
                            <p style="margin:2px 0; font-size:13px;">Locuri libere: <b style="color:#3498db;">{r['Locuri goale']}</b></p>
                            <p style="margin:2px 0; font-size:11px; color:#bdc581;">{r['Status']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("Niciuna dintre stațiile favorite nu a putut fi detectată în acest moment.")
        else:
            st.info("Nu ai nicio stație favorită selectată. Adaugă din lista de mai jos sau din sidebar.")

        # --- EVENIMENTE RECENTE ---
        if recent_changes:
            with st.expander("🔔 Evenimente Recente Detectate", expanded=True):
                for change in recent_changes:
                    st.write(f"**{change['Statie']}**: {change['Mesaj']} ({change['Tip']})")

        # --- HARTA RADAR CU PIN-URI ---
        st.subheader("🗺️ Hartă Radar Timișoara")
        m = folium.Map(location=[user_lat, user_lon], zoom_start=14, tiles="openstreetmap")
        
        # Adăugăm marker pentru locația utilizatorului
        folium.Marker(
            location=[user_lat, user_lon],
            tooltip="Poziția ta",
            icon=folium.Icon(color="blue", icon="user", prefix="fa")
        ).add_to(m)
        
        # Adăugăm stațiile pe hartă
        for _, r in current_df.iterrows():
            if r["Status"] == "Online":
                if r["Biciclete disponibile"] > 5:
                    col = "green"
                elif 1 <= r["Biciclete disponibile"] <= 5:
                    col = "orange"
                else:
                    col = "lightred"
            else:
                col = "red"
                
            p_html = f"""
            <b>{r['Statie']}</b><br>
            Biciclete: {r['Biciclete disponibile']}<br>
            Porturi libere: {r['Locuri goale']}<br>
            Preluare: {r['Scor preluare']}<br>
            Returnare: {r['Scor returnare']}
            """
            
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=folium.Popup(p_html, max_width=200),
                tooltip=f"{r['Statie']} ({r['Biciclete disponibile']} biciclete)",
                icon=folium.Icon(color=col, icon="bicycle", prefix="fa")
            ).add_to(m)
            
        st_folium(m, height=450, use_container_width=True, returned_objects=[])

    with t_route:
        st.subheader("🗺️ Planifică un traseu optim cu VeloTM")
        col_start, col_end = st.columns(2)
        
        with col_start:
            route_start = st.selectbox("Origine (De unde pornești):", options=list(LOCATION_PRESETS.keys()), index=0)
            coords_s = LOCATION_PRESETS[route_start]
            
        with col_end:
            route_end = st.selectbox("Destinație (Unde vrei să ajungi):", options=list(LOCATION_PRESETS.keys()), index=2)
            coords_e = LOCATION_PRESETS[route_end]
            
        if coords_s and coords_e:
            # Găsim cea mai apropiată stație cu bicicletă de la plecare
            p_st = get_nearest_bike_stations(current_df, coords_s[0], coords_s[1], n=1)
            # Găsim cea mai apropiată stație cu porți de la sosire
            r_st = get_nearest_return_stations(current_df, coords_e[0], coords_e[1], n=1)
            
            if not p_st.empty and not r_st.empty:
                pickup = p_st.iloc[0]
                return_st = r_st.iloc[0]
                
                dist_walk_1 = haversine_distance(coords_s[0], coords_s[1], pickup["lat"], pickup["lon"]) * 1000
                dist_walk_2 = haversine_distance(return_st["lat"], return_st["lon"], coords_e[0], coords_e[1]) * 1000
                
                # Evaluăm dacă merită deplasarea cu bicicleta
                is_feasible = (dist_walk_1 < 1000) and (dist_walk_2 < 1000)
                decision = "🟢 MERITĂ din punct de vedere practic!" if is_feasible else "🟠 POATE NU MERITĂ (distanță pietonală mare până la stații)."
                
                st.markdown(
                    f"""
                    <div style="background-color: #2c3a47; padding: 15px; border-radius: 8px; margin-top:10px;">
                        <h4>Recomandare de Traseu:</h4>
                        <p>1. Mergi pe jos <b>{int(dist_walk_1)} m</b> (aprox. {round(dist_walk_1/80)} min) până la stația <b>{pickup['Statie']}</b>.</p>
                        <p>2. Preia o bicicletă (disponibile live: <b>{pickup['Biciclete disponibile']}</b>).</p>
                        <p>3. Rulează până la stația <b>{return_st['Statie']}</b> (porți libere la destinație: <b>{return_st['Locuri goale']}</b>).</p>
                        <p>4. Returnează bicicleta și mergi pe jos <b>{int(dist_walk_2)} m</b> (aprox. {round(dist_walk_2/80)} min) până la destinație.</p>
                        <hr style="border-color:#bdc581;"/>
                        <h5>Decizie: <b>{decision}</b></h5>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.warning("Nu am putut planifica o rută din lipsa disponibilității optime a stațiilor.")

    with t_commute:
        st.subheader("🔄 Mod Commute Recurent")
        commutes = [
            {"nume": "Acasă ➡️ Iulius Town", "start": "Acasă (Configurat în Sidebar)", "end": "Iulius Town"},
            {"nume": "Gara de Nord ➡️ Centru", "start": "Gara de Nord", "end": "Centru (Piața Victoriei)"},
            {"nume": "Complex Studențesc ➡️ Spitalul Județean", "start": "Complexul Studențesc (Facultate)", "end": "Spitalul Județean"}
        ]
        
        for comm in commutes:
            cs = LOCATION_PRESETS.get(comm["start"])
            ce = LOCATION_PRESETS.get(comm["end"])
            
            if cs and ce:
                st_p = get_nearest_bike_stations(current_df, cs[0], cs[1], n=1)
                st_r = get_nearest_return_stations(current_df, ce[0], ce[1], n=1)
                
                if not st_p.empty and not st_r.empty:
                    p_row = st_p.iloc[0]
                    r_row = st_r.iloc[0]
                    
                    status_badge = "🟢 Merită Acum" if (p_row["Biciclete disponibile"] > 2 and r_row["Locuri goale"] > 2) else "🔴 Riscant Acum"
                    
                    st.markdown(
                        f"""
                        <div style="background-color: #1e272e; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between;">
                                <b>{comm['nume']}</b>
                                <span style="font-weight:bold;">{status_badge}</span>
                            </div>
                            <p style="margin: 5px 0 0 0; font-size:13px; color:#a4b0be;">
                                Plecare din <b>{p_row['Statie']}</b> ({p_row['Biciclete disponibile']} biciclete) ➡️ Retur în <b>{r_row['Statie']}</b> ({r_row['Locuri goale']} locuri)
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with t_table:
        st.subheader("📋 Situația completă a rețelei VeloTM")
        
        # Filtru specializat pentru tabel
        f_type = st.selectbox(
            "Vizualizare tip stații:",
            options=["Toate", "Online", "Offline", "Doar cu biciclete disponibile", "Doar fără biciclete", "Doar cu locuri de returnare", "Favorite"]
        )
        
        table_df = current_df.copy()
        
        if f_type == "Online":
            table_df = table_df[table_df["Status"] == "Online"]
        elif f_type == "Offline":
            table_df = table_df[table_df["Status"] == "Offline"]
        elif f_type == "Doar cu biciclete disponibile":
            table_df = table_df[table_df["Biciclete disponibile"] > 0]
        elif f_type == "Doar fără biciclete":
            table_df = table_df[table_df["Biciclete disponibile"] == 0]
        elif f_type == "Doar cu locuri de returnare":
            table_df = table_df[table_df["Locuri goale"] > 0]
        elif f_type == "Favorite":
            table_df = table_df[table_df["Statie"].isin(get_favorites())]
            
        # Adăugare de acțiune pentru salvare sau ștergere favorită
        st.dataframe(
            table_df[["Statie", "Adresa", "Biciclete disponibile", "Locuri goale", "Status", "Scor preluare", "Scor returnare"]],
            use_container_width=True,
            hide_index=True
        )
        
        col_fav1, col_fav2 = st.columns(2)
        with col_fav1:
            to_add = st.selectbox("Adaugă la favorite:", options=current_df["Statie"].tolist())
            if st.button("Adaugă ⭐️"):
                add_favorite(to_add)
                st.success(f"S-a salvat la favorite: {to_add}")
                st.rerun()
                
        with col_fav2:
            current_favs = get_favorites()
            if current_favs:
                to_remove = st.selectbox("Șterge din favorite:", options=current_favs)
                if st.button("Șterge ❌"):
                    remove_favorite(to_remove)
                    st.success(f"S-a eliminat din favorite: {to_remove}")
                    st.rerun()
            else:
                st.write("Nu aveți nicio stație adăugată la favorite în baza de date.")

    with t_analytics:
        st.subheader("📊 Analitice, Istoric și Estimări")
        
        history_df = load_history_from_sqlite()
        if not history_df.empty:
            st.write("Istoric de monitorizare salvat cu succes local în SQLite.")
            
            # Selector stație pentru analiza în timp
            sel_station = st.selectbox("Selectează stația pentru istoric detaliat:", options=current_df["Statie"].unique())
            
            station_hist = history_df[history_df["station_name"] == sel_station].copy()
            if not station_hist.empty:
                station_hist["timestamp"] = pd.to_datetime(station_hist["timestamp"])
                
                # Grafic evoluție
                fig = px.line(
                    station_hist, 
                    x="timestamp", 
                    y=["bikes_available", "empty_doors"],
                    labels={"value": "Unități", "timestamp": "Dată/Oră", "variable": "Indicator"},
                    title=f"Evoluția disponibilității pentru {sel_station}"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- PREDICȚIE ȘI CALCUL RISC ---
                # Agregăm pe ore pentru a genera profilul de risc zilnic
                station_hist["Hour"] = station_hist["timestamp"].dt.hour
                hourly_profile = station_hist.groupby("Hour")["bikes_available"].mean()
                
                current_hour = datetime.now().hour
                avg_bikes_now = hourly_profile.get(current_hour, None)
                
                if avg_bikes_now is not None:
                    risk_status = "scăzut"
                    if avg_bikes_now < 1.5:
                        risk_status = "⚠️ FOARTE MARE"
                    elif avg_bikes_now < 3:
                        risk_status = "MODERAT"
                        
                    st.markdown(
                        f"""
                        <div style="background-color: #2c3a47; padding: 12px; border-radius: 8px;">
                            ℹ️ <b>Predicție istorică simplificată pentru {sel_station}:</b><br>
                            La această oră ({current_hour}:00), stația are în medie <b>{avg_bikes_now:.1f}</b> biciclete disponibile.<br>
                            Risc de stație complet goală la această oră: <b>{risk_status}</b>.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("Nu există suficiente date în istoric pentru stația selectată.")
                
            # --- TOP STAȚII PROBLEMATICE ---
            st.subheader("🚨 Top Stații Problematice (din istoric)")
            
            # Stații care ajung cel mai des goale (bikes_available == 0)
            goale_count = history_df[history_df["bikes_available"] == 0].groupby("station_name").size().reset_index(name="count")
            goale_count = goale_count.sort_values("count", ascending=False).head(5)
            
            # Stații care ajung cel mai des offline (status == "Offline")
            offline_count = history_df[history_df["status"] == "Offline"].groupby("station_name").size().reset_index(name="count")
            offline_count = offline_count.sort_values("count", ascending=False).head(5)
            
            col_prob1, col_prob2 = st.columns(2)
            with col_prob1:
                st.markdown("**Stații goale cel mai des:**")
                st.dataframe(goale_count, hide_index=True, use_container_width=True)
            with col_prob2:
                st.markdown("**Stații offline cel mai des:**")
                st.dataframe(offline_count, hide_index=True, use_container_width=True)
                
        else:
            st.info("Istoricul local în SQLite se populează pe parcursul rulării aplicației la fiecare refresh automat.")

else:
    st.warning("Nu există date disponibile. Asigură-te că URL-ul din sidebar este corect sau bifează Modul Offline.")
