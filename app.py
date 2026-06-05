import os
import re
import json
import math
import sqlite3
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dt_parser
from streamlit_folium import st_folium
import folium
from streamlit_autorefresh import st_autorefresh
from streamlit_js_eval import get_geolocation

# Configurare pagină Streamlit (optimizată mobil)
st.set_page_config(
    page_title="VeloTM Radar",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constante & Setări Directoare
DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
DB_FILE = os.path.join(DATA_DIR, "history.sqlite")

os.makedirs(DATA_DIR, exist_ok=True)

# Coordonate implicite pentru Timișoara (Piața Victoriei)
DEFAULT_LAT = 45.753722
DEFAULT_LON = 21.225712

# ------------------------------------------------------------------------------
# INIȚIALIZARE ȘI GESTIONARE FIȘIERE / BD
# ------------------------------------------------------------------------------
def init_sqlite():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS station_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            station_name TEXT,
            address TEXT,
            bikes_available INTEGER,
            empty_doors INTEGER,
            status TEXT,
            latitude REAL,
            longitude REAL
        )
    """)
    conn.commit()
    conn.close()

def load_user_settings():
    default_settings = {
        "favorites": [],
        "personal_points": {
            "ACASĂ": None,
            "SPITAL": None,
            "CENTRU": [45.755960, 21.226760],
            "GARĂ": [45.746140, 21.215050],
            "FACULTATE": None,
            "IULIUS TOWN": [45.765620, 21.225930]
        },
        "commutes": []
    }
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=4, ensure_ascii=False)
        return default_settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_settings

def save_user_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

init_sqlite()
settings = load_user_settings()

# ------------------------------------------------------------------------------
# SCRAPER LIVE VELOTM
# ------------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    }
    try:
        response = requests.get(url, headers=headers, timeout=12, verify=False)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error: {e}"

def extract_stations_from_html(html):
    if not html or html.startswith("Error"):
        return None
    
    # Caută array-ul javascript var items = [...]
    pattern = r"var\s+items\s*=\s*(\[.*?\]);"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    
    json_str = match.group(1)
    # Curățare robustă pentru eventuale erori de sintaxă JS
    json_str = re.sub(r',(\s*[\]\}])', r'\1', json_str)
    try:
        return json.loads(json_str)
    except Exception:
        # Fallback parser bazat pe regex dacă json.loads eșuează
        try:
            items_list = []
            block_pattern = r"\{[^{}]*\}"
            blocks = re.findall(block_pattern, json_str)
            for block in blocks:
                cleaned = re.sub(r'(\w+)\s*:', r'"\1":', block)
                try:
                    items_list.append(json.loads(cleaned))
                except Exception:
                    continue
            return items_list if items_list else None
        except Exception:
            return None

# ------------------------------------------------------------------------------
# FUNCȚII EVALUARE SCORURI (Corectate pentru a utiliza coloanele redenumite)
# ------------------------------------------------------------------------------
def calculate_pickup_score(row):
    status = str(row["Status"]).strip()
    try:
        bikes = int(row["Biciclete disponibile"])
    except (KeyError, ValueError, TypeError):
        bikes = 0
        
    if status == "Offline":
        return "Inutilă momentan"
    if bikes > 5:
        return "Excelentă pentru preluare"
    if 3 <= bikes <= 5:
        return "OK pentru preluare"
    if 1 <= bikes <= 2:
        return "Riscantă"
    return "Fără biciclete"

def calculate_return_score(row):
    status = str(row["Status"]).strip()
    try:
        doors = int(row["Locuri goale"])
    except (KeyError, ValueError, TypeError):
        doors = 0
        
    if status == "Offline":
        return "Inutilă momentan"
    if doors > 5:
        return "Excelentă pentru returnare"
    if 3 <= doors <= 5:
        return "OK pentru returnare"
    if 1 <= doors <= 2:
        return "Riscantă pentru returnare"
    return "Nu poți returna"

def calculate_station_color(row):
    status = str(row["Status"]).strip()
    try:
        bikes = int(row["Biciclete disponibile"])
    except (KeyError, ValueError, TypeError):
        bikes = 0
        
    if status == "Offline":
        return "red"
    if bikes > 5:
        return "green"
    if 1 <= bikes <= 5:
        return "orange"
    return "red"

def normalize_stations(raw_items):
    if not raw_items:
        return pd.DataFrame()
    
    df = pd.DataFrame(raw_items)
    # Standardizare coloane (Redenumirea are loc aici)
    df = df.rename(columns={
        "StationName": "Statie",
        "Address": "Adresa",
        "OcuppiedSpots": "Biciclete disponibile",
        "EmptyDoors": "Locuri goale",
        "Status": "Status",
        "Latitude": "lat",
        "Longitude": "lon"
    })
    
    df["Biciclete disponibile"] = pd.to_numeric(df["Biciclete disponibile"], errors="coerce").fillna(0).astype(int)
    df["Locuri goale"] = pd.to_numeric(df["Locuri goale"], errors="coerce").fillna(0).astype(int)
    df["Capacitate"] = df["Biciclete disponibile"] + df["Locuri goale"]
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    
    # Aplicare scoruri pe baza noilor coloane standardizate
    df["Scor preluare"] = df.apply(calculate_pickup_score, axis=1)
    df["Scor returnare"] = df.apply(calculate_return_score, axis=1)
    df["Culoare marker"] = df.apply(calculate_station_color, axis=1)
    df["Este online"] = df["Status"] != "Offline"
    df["Are biciclete"] = df["Biciclete disponibile"] > 0
    df["Are locuri goale"] = df["Locuri goale"] > 0
    
    return df

# ------------------------------------------------------------------------------
# MATEMATICĂ GEOSPAȚIALĂ & ALGORITMI
# ------------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Rază pământ în metri
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def format_distance(distance_m):
    if distance_m < 1000:
        return f"{int(distance_m)} m"
    return f"{distance_m / 1000:.2f} km"

def make_google_maps_walking_url(origin_lat, origin_lon, dest_lat, dest_lon):
    return f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}&travelmode=walking"

def make_google_maps_search_url(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def get_nearest_bike_stations(df, origin_lat, origin_lon, n=3):
    valid_df = df[df["Este online"] & df["Are biciclete"]].copy()
    if valid_df.empty:
        return pd.DataFrame()
    valid_df["Distanță"] = valid_df.apply(lambda r: haversine_distance(origin_lat, origin_lon, r["lat"], r["lon"]), axis=1)
    # Penalizare ușoară pentru stații cu o singură bicicletă
    valid_df["Scor sortare"] = valid_df["Distanță"] + valid_df["Biciclete disponibile"].apply(lambda b: 150 if b == 1 else 0)
    return valid_df.sort_values(by="Scor sortare").head(n)

def get_nearest_return_stations(df, origin_lat, origin_lon, n=3):
    valid_df = df[df["Este online"] & df["Are locuri goale"]].copy()
    if valid_df.empty:
        return pd.DataFrame()
    valid_df["Distanță"] = valid_df.apply(lambda r: haversine_distance(origin_lat, origin_lon, r["lat"], r["lon"]), axis=1)
    # Penalizare ușoară pentru stații cu un singur loc gol
    valid_df["Scor sortare"] = valid_df["Distanță"] + valid_df["Locuri goale"].apply(lambda d: 150 if d == 1 else 0)
    return valid_df.sort_values(by="Scor sortare").head(n)

# ------------------------------------------------------------------------------
# ISTORIC SNAPSHOTS SQLITE & EVENT DETECTOR
# ------------------------------------------------------------------------------
def save_snapshot_to_sqlite(df):
    if df.empty:
        return
    
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Verificare ultimul timestamp pentru a evita stocarea duplicată la refresh-uri excesive
    cursor.execute("SELECT MAX(timestamp) FROM station_snapshots")
    last_ts_res = cursor.fetchone()
    
    now_str = datetime.now().isoformat()
    should_save = True
    
    if last_ts_res and last_ts_res[0]:
        try:
            last_ts = dt_parser.parse(last_ts_res[0])
            elapsed_seconds = (datetime.now() - last_ts).total_seconds()
            
            # Salvăm o dată la maxim 5 minute dacă datele sunt absolut identice
            if elapsed_seconds < 300:
                cursor.execute("""
                    SELECT station_name, bikes_available, empty_doors, status 
                    FROM station_snapshots 
                    WHERE timestamp = ?
                """, (last_ts_res[0],))
                prev_records = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
                current_records = {row["Statie"]: (row["Biciclete disponibile"], row["Locuri goale"], row["Status"]) for _, row in df.iterrows()}
                
                if prev_records == current_records:
                    should_save = False
        except Exception:
            pass
            
    if should_save:
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO station_snapshots (timestamp, station_name, address, bikes_available, empty_doors, status, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now_str,
                row["Statie"],
                row["Adresa"],
                int(row["Biciclete disponibile"]),
                int(row["Locuri goale"]),
                row["Status"],
                float(row["lat"]),
                float(row["lon"])
            ))
        conn.commit()
    conn.close()

def load_history_from_sqlite():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        df_hist = pd.read_sql_query("SELECT * FROM station_snapshots", conn)
        conn.close()
        if not df_hist.empty:
            df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        return df_hist
    except Exception:
        return pd.DataFrame()

def detect_station_changes(current_df, previous_df):
    events = []
    if current_df.empty or previous_df.empty:
        return events
        
    prev_dict = previous_df.set_index("Statie").to_dict(orient="index")
    for _, curr in current_df.iterrows():
        statie = curr["Statie"]
        if statie in prev_dict:
            prev = prev_dict[statie]
            
            # 1. Schimbare status funcționalitate
            if curr["Status"] != prev["Status"]:
                events.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "statie": statie,
                    "tip": "Status",
                    "mesaj": f"Schimbare status: {prev['Status']} ➔ {curr['Status']}"
                })
                
            # 2. Re-aprovizionare stație goală
            if prev["Biciclete disponibile"] == 0 and curr["Biciclete disponibile"] > 0:
                events.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "statie": statie,
                    "tip": "Aprovizionare",
                    "mesaj": f"🚲 Au apărut biciclete: 0 ➔ {curr['Biciclete disponibile']} disponibile."
                })
            
            # 3. Stație complet golită
            if prev["Biciclete disponibile"] > 0 and curr["Biciclete disponibile"] == 0:
                events.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "statie": statie,
                    "tip": "Golire",
                    "mesaj": f"⚠️ Stația s-a golit complet de biciclete."
                })

            # 4. Deblocare locuri de returnare
            if prev["Locuri goale"] == 0 and curr["Locuri goale"] > 0:
                events.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "statie": statie,
                    "tip": "Returnare-Liber",
                    "mesaj": f"🔓 Locuri libere de returnare disponibile: {curr['Locuri goale']} locuri."
                })
    return events

# ------------------------------------------------------------------------------
# SERVICIU METEO GRATUIT (OPEN-METEO)
# ------------------------------------------------------------------------------
def fetch_weather_open_meteo(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("current_weather", {})
    except Exception:
        pass
    return None

def calculate_bike_weather_score(weather):
    if not weather:
        return 5, "Fără date meteo", "⚪"
        
    temp = weather.get("temperature", 20)
    wind = weather.get("windspeed", 10)
    code = weather.get("weathercode", 0)
    
    score = 10
    
    # Penalizări Temperatură
    if temp < 5:
        score -= 4
    elif temp < 12:
        score -= 2
    elif temp > 35:
        score -= 3
        
    # Penalizări Vânt
    if wind > 30:
        score -= 4
    elif wind > 18:
        score -= 2
        
    # Penalizări Cod Meteo WMO
    if code in [51, 53, 55, 80]:
        score -= 3
        verdict = "Ploaie ușoară"
        icon = "🌦️"
    elif code in [61, 63, 65, 81, 82]:
        score -= 6
        verdict = "Ploaie torențială"
        icon = "🌧️"
    elif code in [71, 73, 75, 77]:
        score -= 8
        verdict = "Ninsoare"
        icon = "❄️"
    elif code in [95, 96, 99]:
        score -= 9
        verdict = "Furtună"
        icon = "⛈️"
    else:
        verdict = "Vreme favorabilă"
        icon = "☀️" if temp >= 15 else "⛅"
        
    score = max(0, min(10, score))
    return score, verdict, icon

# ------------------------------------------------------------------------------
# COMPONENTE INTERFAȚĂ & DESIGN MOBILE-FIRST
# ------------------------------------------------------------------------------
def render_header(df, weather):
    st.markdown("""
        <style>
            .title-radar { color: #45B6B0; font-size: 2.3rem; font-weight: 800; margin-bottom: 2px; }
            .subtitle-radar { color: #A0AEC0; font-size: 1rem; margin-bottom: 20px; }
            .card-metric { background-color: #1C2130; border-radius: 12px; padding: 15px; border: 1px solid #2D3748; text-align: center; }
            .card-metric-val { font-size: 1.8rem; font-weight: bold; color: #45B6B0; }
            .card-metric-lbl { font-size: 0.85rem; color: #718096; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title-radar">🚲 VeloTM Radar</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle-radar">Monitorizare live, recomandări și navigare inteligentă în Timișoara</div>', unsafe_allow_html=True)

    if not df.empty:
        total_bikes = df["Biciclete disponibile"].sum()
        total_doors = df["Locuri goale"].sum()
        online_st = df[df["Este online"]].shape[0]
        offline_st = df[~df["Este online"]].shape[0]
        
        # Scorul meteo
        w_score, w_desc, w_icon = calculate_bike_weather_score(weather)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="card-metric"><div class="card-metric-val">{total_bikes}</div><div class="card-metric-lbl">Biciclete Disponibile</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="card-metric"><div class="card-metric-val">{total_doors}</div><div class="card-metric-lbl">Porti Libere</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="card-metric"><div class="card-metric-val">{online_st} <span style="font-size:1rem;color:#E53E3E;">({offline_st} off)</span></div><div class="card-metric-lbl">Statii Online</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="card-metric"><div class="card-metric-val">{w_icon} {w_score}/10</div><div class="card-metric-lbl">Scor Velo-Meteo ({w_desc})</div></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# HARTA INTERACTIVĂ (FOLIUM)
# ------------------------------------------------------------------------------
def render_map(df, user_location=None, personal_points=None, highlighted_stations=None, key_suffix=""):
    # Centrare pe locația userului sau central implicit
    center_lat = user_location[0] if user_location else DEFAULT_LAT
    center_lon = user_location[1] if user_location else DEFAULT_LON
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles="cartodbpositron")
    
    # 1. Adăugare Marker Poziție Curentă Utilizator
    if user_location:
        folium.Marker(
            location=user_location,
            popup="Locația ta",
            icon=folium.Icon(color="blue", icon="user", prefix="fa")
        ).add_to(m)
        
    # 2. Adăugare Puncte Personale (Acasă, Spital etc)
    if personal_points:
        for name, coords in personal_points.items():
            if coords:
                folium.Marker(
                    location=coords,
                    popup=f"Punct salvat: {name}",
                    icon=folium.Icon(color="darkpurple", icon="home" if name == "ACASĂ" else "star", prefix="fa")
                ).add_to(m)

    # 3. Adăugare Stații VeloTM
    for _, row in df.iterrows():
        is_highlighted = False
        if highlighted_stations and row["Statie"] in highlighted_stations:
            is_highlighted = True
            
        color = "cadetblue" if is_highlighted else row["Culoare marker"]
        
        popup_html = f"""
            <div style="font-family: sans-serif; font-size:12px; width:220px;">
                <b>Stația {row['Statie']}</b><br/>
                <span style="color:#718096;">{row['Adresa']}</span><br/><hr style="margin:5px 0;"/>
                🚲 Biciclete: <b>{row['Biciclete disponibile']}</b><br/>
                🔓 Porți libere: <b>{row['Locuri goale']}</b><br/>
                📊 Status: <b>{row['Status']}</b><br/>
                💡 Scor preluare: <i>{row['Scor preluare']}</i><br/><br/>
                <a href="{make_google_maps_search_url(row['lat'], row['lon'])}" target="_blank" style="background-color:#45B6B0;color:white;padding:5px 10px;text-decoration:none;border-radius:5px;display:inline-block;text-align:center;">Deschide pe Hartă</a>
            </div>
        """
        
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color, icon="bicycle", prefix="fa")
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=450, key=f"folium_map_{key_suffix}")
    return map_data

# ------------------------------------------------------------------------------
# FLUXUL LOGIC ȘI EXECUȚIA APLICAȚIEI
# ------------------------------------------------------------------------------
def main():
    if "events" not in st.session_state:
        st.session_state.events = []
    if "prev_df" not in st.session_state:
        st.session_state.prev_df = pd.DataFrame()
    if "user_coords" not in st.session_state:
        st.session_state.user_coords = None

    # --------------------------------------------------------------------------
    # SIDEBAR CONFIGURAȚIE
    # --------------------------------------------------------------------------
    st.sidebar.markdown("### ⚙️ Setări VeloTM Radar")
    source_url = st.sidebar.text_input(
        "Sursă date live VeloTM",
        value="http://www.velotm.ro/harta-statii-biciclete"
    )
    
    refresh_opts = {
        "Oprit": None,
        "30 Secunde": 30000,
        "60 Secunde": 60000,
        "2 Minute": 120000,
        "5 Minute": 300000
    }
    refresh_sel = st.sidebar.selectbox("Interval actualizare automată", list(refresh_opts.keys()), index=2)
    refresh_ms = refresh_opts[refresh_sel]
    
    if refresh_ms:
        st_autorefresh(interval=refresh_ms, key="velotm_autorefresh")
        
    st.sidebar.markdown("---")
    
    with st.spinner("Se descarcă datele VeloTM live..."):
        html_content = fetch_page(source_url)
        raw_items = extract_stations_from_html(html_content)
        
    if not raw_items:
        st.error("Nu s-au putut extrage datele live de pe portalul VeloTM. Verificați conexiunea sau URL-ul din sidebar.")
        with st.sidebar.expander("Vizualizare cod sursă parțial"):
            st.code(html_content[:1500] if html_content else "Niciun răspuns de la server.")
        return

    df = normalize_stations(raw_items)
    save_snapshot_to_sqlite(df)
    
    # Evaluare evenimente noi
    if not st.session_state.prev_df.empty:
        new_events = detect_station_changes(df, st.session_state.prev_df)
        if new_events:
            st.session_state.events = (new_events + st.session_state.events)[:20]
            
    st.session_state.prev_df = df.copy()

    # Încărcare Meteo dinamic pentru Timișoara
    weather_data = fetch_weather_open_meteo(DEFAULT_LAT, DEFAULT_LON)
    render_header(df, weather_data)

    # --------------------------------------------------------------------------
    # GEOLOCAȚIE BROWSER (Solicitare de la utilizator)
    # --------------------------------------------------------------------------
    st.markdown("### 📍 Poziția ta curentă")
    col_geo_1, col_geo_2 = st.columns([1, 2])
    with col_geo_1:
        if st.button("🗺️ Permite accesul la locația mea", use_container_width=True):
            try:
                g_loc = get_geolocation()
                if g_loc and "coords" in g_loc:
                    st.session_state.user_coords = [
                        g_loc["coords"]["latitude"],
                        g_loc["coords"]["longitude"]
                    ]
                    st.success("Locație geospațială detectată.")
                else:
                    st.warning("Nu s-a putut citi locația. Verificați setările sau permisiunile.")
            except Exception:
                st.info("Sistemul de securitate al browserului solicită acceptul dumneavoastră.")
    
    with col_geo_2:
        if st.session_state.user_coords:
            st.info(f"Poziție curentă: Lat {st.session_state.user_coords[0]:.5f}, Lon {st.session_state.user_coords[1]:.5f}")
        else:
            st.warning("Locația GPS nu este determinată. Se folosește centrul orașului.")

    # --------------------------------------------------------------------------
    # TAB-URI NAVIGARE
    # --------------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📍 Ghid Rapid", 
        "🗺️ Hartă Live", 
        "🛣️ Planificare Traseu", 
        "⭐ Personal & Favorite",
        "📈 Istoric & Analiză",
        "🔔 Alerte Live"
    ])

    # TAB 1: GHID RAPID
    with tab1:
        st.markdown("### 🔍 Unde găsesc cea mai apropiată bicicletă?")
        ref_lat = st.session_state.user_coords[0] if st.session_state.user_coords else DEFAULT_LAT
        ref_lon = st.session_state.user_coords[1] if st.session_state.user_coords else DEFAULT_LON
        
        col_pickup, col_drop = st.columns(2)
        
        with col_pickup:
            st.subheader("🚲 Preluare Rapidă")
            nearest_p = get_nearest_bike_stations(df, ref_lat, ref_lon, n=3)
            if not nearest_p.empty:
                for _, r in nearest_p.iterrows():
                    dist_text = format_distance(r["Distanță"])
                    st.markdown(f"""
                        <div style="background-color: #1C2130; padding:12px; border-radius:10px; border-left: 5px solid {r['Culoare marker']}; margin-bottom:10px;">
                            <b>{r['Statie']}</b><br/>
                            Disponibile: <span style="font-size:1.1rem;font-weight:bold;color:#45B6B0;">{r['Biciclete disponibile']}</span> biciclete | {r['Locuri goale']} locuri goale<br/>
                            Distanță estimată: <b>{dist_text}</b><br/>
                            Scor: <i>{r['Scor preluare']}</i>
                        </div>
                    """, unsafe_allow_html=True)
                    st.write(f"[🚶 Traseu Google Maps]({make_google_maps_walking_url(ref_lat, ref_lon, r['lat'], r['lon'])})")
            else:
                st.write("Toate stațiile din apropiere sunt offline sau goale.")

        with col_drop:
            st.subheader("🔓 Returnare Rapidă")
            nearest_d = get_nearest_return_stations(df, ref_lat, ref_lon, n=3)
            if not nearest_d.empty:
                for _, r in nearest_d.iterrows():
                    dist_text = format_distance(r["Distanță"])
                    st.markdown(f"""
                        <div style="background-color: #1C2130; padding:12px; border-radius:10px; border-left: 5px solid #4299E1; margin-bottom:10px;">
                            <b>{r['Statie']}</b><br/>
                            Locuri libere: <span style="font-size:1.1rem;font-weight:bold;color:#4299E1;">{r['Locuri goale']}</span> porți libere<br/>
                            Distanță estimată: <b>{dist_text}</b><br/>
                            Scor: <i>{r['Scor returnare']}</i>
                        </div>
                    """, unsafe_allow_html=True)
                    st.write(f"[🚶 Traseu Google Maps]({make_google_maps_walking_url(ref_lat, ref_lon, r['lat'], r['lon'])})")
            else:
                st.write("Toate stațiile din apropiere sunt offline sau pline.")

    # TAB 2: HARTĂ LIVE & TABEL DATE COMPLET
    with tab2:
        st.markdown("### 🗺️ Situația Stațiilor VeloTM în timp real")
        render_map(df, user_location=st.session_state.user_coords, personal_points=settings["personal_points"], key_suffix="tab2")
        
        st.markdown("### 📋 Toate Stațiile din Rețea")
        filtru = st.selectbox("Filtrează stațiile după status și disponibilitate:", [
            "Toate", "Online", "Offline", "Cu biciclete disponibile", "Fără biciclete", "Cu locuri goale"
        ])
        
        df_table = df.copy()
        if filtru == "Online":
            df_table = df_table[df_table["Este online"]]
        elif filtru == "Offline":
            df_table = df_table[~df_table["Este online"]]
        elif filtru == "Cu biciclete disponibile":
            df_table = df_table[df_table["Are biciclete"]]
        elif filtru == "Fără biciclete":
            df_table = df_table[df_table["Biciclete disponibile"] == 0]
        elif filtru == "Cu locuri goale":
            df_table = df_table[df_table["Are locuri goale"]]
            
        st.dataframe(
            df_table[["Statie", "Adresa", "Biciclete disponibile", "Locuri goale", "Capacitate", "Status", "Scor preluare", "Scor returnare"]],
            use_container_width=True
        )

    # TAB 3: PLANIFICATOR TRASEU (POINT A -> POINT B)
    with tab3:
        st.markdown("### 🛣️ Planificare Traseu Smart VeloTM")
        personal_names = [k for k, v in settings["personal_points"].items() if v is not None]
        point_opts = ["Locația mea curentă"] + personal_names + ["Hartă (Punct ales manual)"]
        
        col_pa, col_pb = st.columns(2)
        with col_pa:
            src_opt = st.selectbox("Origine (Punct A)", point_opts, index=0)
        with col_pb:
            dest_opt = st.selectbox("Destinație (Punct B)", point_opts, index=min(2, len(point_opts)-1))
            
        coords_a = None
        if src_opt == "Locația mea curentă":
            coords_a = st.session_state.user_coords
        elif src_opt == "Hartă (Punct ales manual)":
            st.info("Dați click pe harta de mai jos pentru a alege punctul de pornire.")
            picker_data = render_map(df, key_suffix="picker_a")
            if picker_data and picker_data.get("last_clicked"):
                coords_a = [picker_data["last_clicked"]["lat"], picker_data["last_clicked"]["lng"]]
        else:
            coords_a = settings["personal_points"].get(src_opt)
            
        coords_b = None
        if dest_opt == "Locația mea curentă":
            coords_b = st.session_state.user_coords
        elif dest_opt == "Hartă (Punct ales manual)":
            st.info("Dați click pe harta de mai jos pentru a alege punctul de destinație.")
            picker_data_b = render_map(df, key_suffix="picker_b")
            if picker_data_b and picker_data_b.get("last_clicked"):
                coords_b = [picker_data_b["last_clicked"]["lat"], picker_data_b["last_clicked"]["lng"]]
        else:
            coords_b = settings["personal_points"].get(dest_opt)

        if coords_a and coords_b:
            p_stations = get_nearest_bike_stations(df, coords_a[0], coords_a[1], n=1)
            r_stations = get_nearest_return_stations(df, coords_b[0], coords_b[1], n=1)
            
            if not p_stations.empty and not r_stations.empty:
                p_station = p_stations.iloc[0]
                r_station = r_stations.iloc[0]
                
                dist_walk_1 = haversine_distance(coords_a[0], coords_a[1], p_station["lat"], p_station["lon"])
                dist_bike = haversine_distance(p_station["lat"], p_station["lon"], r_station["lat"], r_station["lon"])
                dist_walk_2 = haversine_distance(r_station["lat"], r_station["lon"], coords_b[0], coords_b[1])
                
                st.markdown("#### 🎯 Traseu Optimizat Recomandat:")
                st.write(f"🚶 **Pas 1 (Pietonal):** Mergeți de la pornire la stația **{p_station['Statie']}** (~{format_distance(dist_walk_1)}).")
                st.write(f"🚲 **Pas 2 (Ciclism):** Luați bicicleta și pedalați până la stația **{r_station['Statie']}** (~{format_distance(dist_bike)}).")
                st.write(f"🚶 **Pas 3 (Pietonal):** Returnați bicicleta și mergeți pe jos la destinație (~{format_distance(dist_walk_2)}).")
                
                if dist_walk_1 > 900 or dist_walk_2 > 900:
                    st.warning("⚠️ Verdict: **Riscant.** Stațiile sunt destul de departe de punctele selectate.")
                else:
                    st.success("✅ Verdict: **Traseu Recomandat.** Accesibil și optim.")
                    
                col_lnk1, col_lnk2 = st.columns(2)
                with col_lnk1:
                    st.markdown(f"[🚶 Navigație Pasul 1 pe Google Maps]({make_google_maps_walking_url(coords_a[0], coords_a[1], p_station['lat'], p_station['lon'])})")
                with col_lnk2:
                    st.markdown(f"[🚶 Navigație Pasul 3 pe Google Maps]({make_google_maps_walking_url(r_station['lat'], r_station['lon'], coords_b[0], coords_b[1])})")
            else:
                st.error("Nu s-au putut identifica stații online în proximitatea coordonatelor.")
        else:
            st.info("Alegeți originea și destinația pentru a genera planul de călătorie.")

    # TAB 4: FAVORITE ȘI PUNCTE PERSONALE
    with tab4:
        st.markdown("### ⭐ Administrare Puncte Personale & Favorite")
        st.subheader("📍 Setează un punct personal pe hartă")
        selected_point_name = st.selectbox("Alege ce punct dorești să definești:", list(settings["personal_points"].keys()))
        
        st.write("Oferiți click pe hartă în locația dorită pentru a salva coordonatele:")
        map_picker = render_map(df, key_suffix="point_saver")
        
        if map_picker and map_picker.get("last_clicked"):
            click_lat = map_picker["last_clicked"]["lat"]
            click_lon = map_picker["last_clicked"]["lng"]
            
            if st.button(f"Salvează coordonatele pentru {selected_point_name}"):
                settings["personal_points"][selected_point_name] = [click_lat, click_lon]
                save_user_settings(settings)
                st.success(f"Punctul '{selected_point_name}' a fost salvat: {click_lat:.6f}, {click_lon:.6f}")
                st.rerun()

        st.subheader("⭐ Selectare Stații VeloTM Favorite")
        favorite_list = st.multiselect(
            "Selectează stațiile tale preferate:",
            options=sorted(df["Statie"].unique().tolist()),
            default=settings.get("favorites", [])
        )
        if st.button("Salvează lista de favorite"):
            settings["favorites"] = favorite_list
            save_user_settings(settings)
            st.success("Lista de favorite actualizată.")
            
        if settings.get("favorites"):
            st.markdown("#### 🌟 Status Rapid Favorite:")
            fav_df = df[df["Statie"].isin(settings["favorites"])]
            for _, r in fav_df.iterrows():
                st.markdown(f"- **{r['Statie']}**: 🚲 {r['Biciclete disponibile']} disp. | 🔓 {r['Locuri goale']} libere ({r['Status']})")

    # TAB 5: ISTORIC & ANALIZĂ EVOLUȚIE
    with tab5:
        st.markdown("### 📈 Evoluție Istorică Stații VeloTM")
        hist_df = load_history_from_sqlite()
        
        if not hist_df.empty:
            all_stations_list = sorted(hist_df["station_name"].unique())
            selected_chart_station = st.selectbox("Selectează stația pentru grafic:", all_stations_list)
            
            st_data = hist_df[hist_df["station_name"] == selected_chart_station].sort_values(by="timestamp")
            
            if not st_data.empty:
                fig = px.line(
                    st_data, 
                    x="timestamp", 
                    y=["bikes_available", "empty_doors"],
                    labels={"value": "Unități", "timestamp": "Timp", "variable": "Tip"},
                    title=f"Disponibilitate Istorică în Stația {selected_chart_station}",
                    color_discrete_sequence=["#45B6B0", "#4299E1"]
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st_data["hour"] = st_data["timestamp"].dt.hour
                hourly_avg = st_data.groupby("hour")["bikes_available"].mean()
                current_hour = datetime.now().hour
                
                st.markdown("#### 🔮 Analiză Probabilitate / Predicție:")
                if current_hour in hourly_avg.index:
                    avg_bikes = hourly_avg.loc[current_hour]
                    if avg_bikes < 1.5:
                        st.warning(f"⚠️ **Risc de lipsă biciclete:** La această oră ({current_hour}:00), istoric stația are o medie de doar {avg_bikes:.1f} biciclete disponibile.")
                    else:
                        st.success(f"✅ **Probabilitate ridicată:** Istoric, la această oră ({current_hour}:00), stația are o medie de {avg_bikes:.1f} biciclete disponibile.")
            else:
                st.info("Nu există date suficiente pentru această stație.")
        else:
            st.info("Baza de date istorică este în curs de constituire. Istoricul va deveni disponibil pe măsură ce aplicația înregistrează date.")

    # TAB 6: ALERTE LIVE (EVENIMENTE RECENTE)
    with tab6:
        st.markdown("### 🔔 Jurnal Evenimente Recente VeloTM")
        if st.session_state.events:
            for ev in st.session_state.events:
                st.markdown(f"**[{ev['timestamp']}] {ev['statie']}** - {ev['mesaj']}")
        else:
            st.info("Nu s-au înregistrat modificări în rețea în această sesiune.")

if __name__ == "__main__":
    main()
