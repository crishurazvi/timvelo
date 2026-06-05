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
from streamlit_js_eval import get_geolocation
import plotly.express as px

# --- CONFIGURARE PAGINĂ STREAMLIT ---
st.set_page_config(
    page_title="VeloTM Radar",
    page_icon="🚲",
    layout="centered", # Mai compact, ideal pentru dispozitive mobile
    initial_sidebar_state="collapsed"
)

# --- CONFIGURĂRI DE BAZĂ ȘI DIRECTOARE ---
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "history.sqlite")
SETTINGS_PATH = os.path.join(DB_DIR, "user_settings.json")
os.makedirs(DB_DIR, exist_ok=True)

DEFAULT_URL = "http://www.velotm.ro/harta-statii-biciclete"
TIMISOARA_CENTER = (45.75372, 21.229718)

# --- MANAGEMENT BAZĂ DE DATE SQLITE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

# --- MANAGEMENT SETĂRI UTILIZATOR ---
def load_user_settings():
    if not os.path.exists(SETTINGS_PATH):
        # Valori implicite pentru puncte de interes
        default_settings = {
            "ACASĂ": [45.748580, 21.225070], # Statia Savoy ca punct de plecare default
            "SPITAL": [45.738000, 21.242050],
            "CENTRU": [45.755960, 21.226760],
            "GARĂ": [45.75051, 21.20815],
            "FACULTATE": [45.74681, 21.23925],
            "IULIUS TOWN": [45.765620, 21.225930],
            "CUSTOM": [45.75372, 21.229718],
            "commutes": [
                {"name": "ACASĂ ➡️ CENTRU", "start": "ACASĂ", "end": "CENTRU"},
                {"name": "GARĂ ➡️ FACULTATE", "start": "GARĂ", "end": "FACULTATE"}
            ]
        }
        save_user_settings(default_settings)
        return default_settings
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_settings(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)

# --- PARSARE ȘI EXTRAGERE DATE ---
@st.cache_data(ttl=30, show_spinner=False)
def fetch_page(url=DEFAULT_URL, cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    if cookie:
        headers["Cookie"] = cookie.strip()
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise RuntimeError(f"Eroare rețea la descărcarea paginii: {str(e)}")

def extract_stations_from_html(html):
    # Regex precis pentru showStations() si var items
    items_match = re.search(
        r"var\s+items\s*=\s*(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])\s*;",
        html,
        re.DOTALL
    )
    if not items_match:
        # Căutare generalizată rezistentă la spații libere suplimentare
        items_match = re.search(
            r"(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])",
            html,
            re.DOTALL
        )
        if not items_match:
            raise ValueError("Nu s-a găsit vectorul de stații 'items' în codul sursă.")
            
    json_str = items_match.group(1)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Structură JSON invalidă în datele extrase: {str(e)}")

def normalize_stations(raw_data):
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    
    # Mapare exactă pentru eliminarea oricăror anomalii de scriere din sursă
    column_mapping = {
        "StationName": "Statie",
        "Address": "Adresa",
        "OcuppiedSpots": "Biciclete disponibile",
        "EmptyDoors": "Locuri goale",
        "Status": "Status",
        "Latitude": "lat",
        "Longitude": "lon"
    }
    
    df = df.rename(columns=column_mapping)
    
    df["Biciclete disponibile"] = pd.to_numeric(df["Biciclete disponibile"], errors='coerce').fillna(0).astype(int)
    df["Locuri goale"] = pd.to_numeric(df["Locuri goale"], errors='coerce').fillna(0).astype(int)
    df["lat"] = pd.to_numeric(df["lat"], errors='coerce').fillna(TIMISOARA_CENTER[0])
    df["lon"] = pd.to_numeric(df["lon"], errors='coerce').fillna(TIMISOARA_CENTER[1])
    
    df["Scor preluare"] = df.apply(calculate_station_score, axis=1)
    df["Scor returnare"] = df.apply(calculate_return_score, axis=1)
    
    return df

def calculate_station_score(row):
    if row["Status"] != "Online":
        return "Inutilă momentan"
    bikes = row["Biciclete disponibile"]
    if bikes > 5:
        return "Excelentă pentru preluare"
    elif 3 <= bikes <= 5:
        return "OK pentru preluare"
    elif 1 <= bikes <= 2:
        return "Riscantă"
    return "Fără biciclete"

def calculate_return_score(row):
    if row["Status"] != "Online":
        return "Inutilă momentan"
    doors = row["Locuri goale"]
    if doors > 5:
        return "Excelentă pentru returnare"
    elif 3 <= doors <= 5:
        return "OK pentru returnare"
    elif 1 <= doors <= 2:
        return "Riscantă pentru returnare"
    return "Nu poți returna"

# --- CALCULE DISTANȚE ȘI GEO-LOCAȚIE ---
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Raza pământului în km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_user_location():
    # Inițiem prompt-ul nativ de localizare pe mobil
    try:
        loc = get_geolocation()
        if loc and "coords" in loc:
            return float(loc["coords"]["latitude"]), float(loc["coords"]["longitude"])
    except Exception:
        pass
    return None

def get_nearest_bike_stations(df, user_lat, user_lon, n=3):
    # Doar stații online cu cel puțin o bicicletă
    valid_df = df[(df["Status"] == "Online") & (df["Biciclete disponibile"] > 0)].copy()
    if valid_df.empty:
        return pd.DataFrame()
    valid_df["distance"] = valid_df.apply(lambda r: haversine_distance(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
    # Sortare primară după distanță, secundară după cantitate
    return valid_df.sort_values(by=["distance", "Biciclete disponibile"], ascending=[True, False]).head(n)

def get_nearest_return_stations(df, user_lat, user_lon, n=3):
    # Doar stații online cu cel puțin un loc liber
    valid_df = df[(df["Status"] == "Online") & (df["Locuri goale"] > 0)].copy()
    if valid_df.empty:
        return pd.DataFrame()
    valid_df["distance"] = valid_df.apply(lambda r: haversine_distance(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
    return valid_df.sort_values(by=["distance", "Locuri goale"], ascending=[True, False]).head(n)

def make_google_maps_walking_url(origin_lat, origin_lon, dest_lat, dest_lon):
    if origin_lat is not None and origin_lon is not None:
        return f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}&travelmode=walking"
    return f"https://www.google.com/maps/search/?api=1&query={dest_lat},{dest_lon}"

# --- OPERAȚIUNI ISTORIC ȘI ANALYTICS ---
def save_snapshot_to_sqlite(df):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        
        # Extragem ultimul snapshot pentru a evita duplicarea datelor identice în ferestre scurte de timp
        cursor.execute("SELECT timestamp, bikes_available, empty_doors FROM station_snapshots ORDER BY id DESC LIMIT 1")
        last_entry = cursor.fetchone()
        
        # Dacă datele globale sunt exact identice la ultimul minut, sărim peste scriere
        if last_entry:
            last_time = datetime.fromisoformat(last_entry[0])
            if (datetime.now() - last_time).seconds < 240:
                conn.close()
                return

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
            
        cursor.executemany("""
            INSERT INTO station_snapshots (timestamp, station_name, address, bikes_available, empty_doors, status, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_history_from_sqlite():
    try:
        conn = sqlite3.connect(DB_PATH)
        df_hist = pd.read_sql_query("SELECT * FROM station_snapshots ORDER BY timestamp DESC", conn)
        conn.close()
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        return df_hist
    except Exception:
        return pd.DataFrame()

# --- INTEGRARE METEO CU OPEN-METEO (FĂRĂ API KEY) ---
def fetch_weather_open_meteo(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,wind_speed_10m,weather_code&timezone=auto"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("current", {})
    except Exception:
        pass
    return None

def calculate_bike_weather_score(weather_data):
    if not weather_data:
        return None
    
    score = 10
    temp = weather_data.get("temperature_2m", 20)
    precip = weather_data.get("precipitation", 0)
    wind = weather_data.get("wind_speed_10m", 0)
    
    # Evaluări bazate pe temperatură
    if temp < 5:
        score -= 5
    elif temp < 12:
        score -= 2
    elif temp > 36:
        score -= 3
        
    # Evaluări pe bază de precipitații (ploaie/ninsoare)
    if precip > 0:
        if precip < 2:
            score -= 3
        else:
            score -= 7
            
    # Evaluări pe bază de vânt (km/h)
    if wind > 15:
        score -= 2
    if wind > 30:
        score -= 4
        
    return max(0, score)

# --- ALERTE INTERNE ---
def detect_station_changes(current_df, previous_df):
    if previous_df is None or previous_df.empty or current_df is None or current_df.empty:
        return []
    
    curr_indexed = current_df.set_index("Statie")
    prev_indexed = previous_df.set_index("Statie")
    
    alerts = []
    for name in curr_indexed.index.intersection(prev_indexed.index):
        c = curr_indexed.loc[name]
        p = prev_indexed.loc[name]
        
        # Preluare disponibilitate: de la 0 la 1+
        if p["Biciclete disponibile"] == 0 and c["Biciclete disponibile"] > 0:
            alerts.append(f"🚲 A apărut bicicletă la {name}: 0 ➡️ {c['Biciclete disponibile']}")
        # Preluare disponibilitate: de la 1+ la 0
        elif p["Biciclete disponibile"] > 0 and c["Biciclete disponibile"] == 0:
            alerts.append(f"⚠️ Stația {name} a rămas fără biciclete!")
            
        # Modificare stare conexiune offline/online
        if p["Status"] == "Offline" and c["Status"] == "Online":
            alerts.append(f"🟢 Stația {name} a redevenit ONLINE")
        elif p["Status"] != "Offline" and c["Status"] == "Offline":
            alerts.append(f"🔴 Stația {name} a devenit OFFLINE")
            
        # Returnare locuri libere: de la 0 la 1+
        if p["Locuri goale"] == 0 and c["Locuri goale"] > 0:
            alerts.append(f"📥 Acum poți returna la {name}: 0 ➡️ {c['Locuri goale']} locuri goale")
            
    return alerts

# --- INITIALIZARE STATE & COMPONENTE ---
if "user_location" not in st.session_state:
    st.session_state.user_location = None
if "current_view" not in st.session_state:
    st.session_state.current_view = "Găsește bicicletă"
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None
if "current_df" not in st.session_state:
    st.session_state.current_df = None
if "last_fetch_time" not in st.session_state:
    st.session_state.last_fetch_time = None

settings = load_user_settings()

# --- SIDEBAR CONFIGURARE ---
st.sidebar.title("VeloTM Radar Setări")
url_input = st.sidebar.text_input("VeloTM URL:", value=DEFAULT_URL)
refresh_period = st.sidebar.selectbox("Actualizare automată:", options=[0, 30, 60, 120, 300], format_func=lambda x: "Dezactivat" if x == 0 else f"{x} secunde")
use_demo_mode = st.sidebar.checkbox("Utilizează date Demo (Offline)")
cookie_val = st.sidebar.text_input("Cookie sesiune (Opțional):", type="password")

if refresh_period > 0:
    st_autorefresh(interval=refresh_period * 1000, key="auto_radar_refresh")

# Actualizare date rețea
def update_data():
    try:
        if use_demo_mode:
            html = DEMO_HTML
        else:
            html = fetch_page(url_input, cookie=cookie_val if cookie_val else None)
        
        raw = extract_stations_from_html(html)
        normalized = normalize_stations(raw)
        
        st.session_state.prev_df = st.session_state.current_df
        st.session_state.current_df = normalized
        st.session_state.last_fetch_time = datetime.now()
        
        save_snapshot_to_sqlite(normalized)
    except Exception as e:
        st.sidebar.error(f"Eroare colectare date: {str(e)}")

if st.sidebar.button("Forțează Actualizare Live") or st.session_state.current_df is None:
    update_data()

# --- PROCESARE GEOLOCAȚIE ---
detected_loc = get_user_location()
if detected_loc:
    st.session_state.user_location = detected_loc

user_lat, user_lon = TIMISOARA_CENTER
if st.session_state.user_location:
    user_lat, user_lon = st.session_state.user_location

# --- RENDER ELEMENTE INTERFAȚĂ METRICI & WEATHER ---
def render_weather_score(weather_data):
    if not weather_data:
        st.caption("Datele meteo nu sunt disponibile momentan.")
        return
    score = calculate_bike_weather_score(weather_data)
    temp = weather_data.get("temperature_2m", 20)
    
    if score >= 8:
        verdict = "🟢 Excelent pentru bicicletă"
    elif score >= 5:
        verdict = "🟡 Acceptabil"
    else:
        verdict = "🔴 Mai bine eviți bicicleta acum"
        
    st.markdown(f"**Vremea în Timișoara:** {temp}°C | **Scor VeloTM:** {score}/10 - **{verdict}**")

def render_metrics(df):
    if df is not None and not df.empty:
        total_bikes = df["Biciclete disponibile"].sum()
        total_doors = df["Locuri goale"].sum()
        online_stations = df[df["Status"] == "Online"].shape[0]
        offline_stations = df[df["Status"] == "Offline"].shape[0]
        
        st.markdown(f"📊 **Status Rețea:** {total_bikes} Biciclete | {total_doors} Locuri libere | Stații: {online_stations} Online / {offline_stations} Offline")

# --- ELEMENTE VIZUALE PRINCIPALE - INTERFAȚĂ MOBILĂ ---
st.markdown("<h2 style='text-align: center;'>🚲 VeloTM Radar</h2>", unsafe_allow_html=True)

# Integrare Prognoză Meteo rapidă
w_data = fetch_weather_open_meteo(user_lat, user_lon)
render_weather_score(w_data)
render_metrics(st.session_state.current_df)

if not st.session_state.user_location:
    st.warning("Nu am primit acces la locație. Poți selecta manual poziția prin presets sau pe hartă.")
    if st.button("📍 Solicită permisiune locație (Permite accesul meu)"):
        st.session_state.user_location = get_user_location()
        st.rerun()

# Butoane mari pentru mobil (Quick Navigation)
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
with col_nav1:
    if st.button("🔍 Bicicletă", use_container_width=True):
        st.session_state.current_view = "Găsește bicicletă"
with col_nav2:
    if st.button("📥 Returnare", use_container_width=True):
        st.session_state.current_view = "Găsește loc de returnare"
with col_nav3:
    if st.button("🗺️ Traseu", use_container_width=True):
        st.session_state.current_view = "Traseul meu"
with col_nav4:
    if st.button("⭐️ Favorite", use_container_width=True):
        st.session_state.current_view = "Favorite"

# --- LOGICĂ RECOMANDĂRI ---
df_current = st.session_state.current_df

if df_current is not None and not df_current.empty:

    if st.session_state.current_view == "Găsește bicicletă":
        st.subheader("🚶 Cele mai apropiate preluări:")
        near_bikes = get_nearest_bike_stations(df_current, user_lat, user_lon)
        if not near_bikes.empty:
            for _, r in near_bikes.iterrows():
                dist_m = int(r["distance"] * 1000)
                st.info(f"**{r['Statie']}** - {r['Biciclete disponibile']} biciclete ({r['Locuri goale']} porți goale) - la {dist_m}m de tine. [{r['Scor preluare']}]")
                url_gmaps = make_google_maps_walking_url(st.session_state.user_location[0] if st.session_state.user_location else None, st.session_state.user_location[1] if st.session_state.user_location else None, r["lat"], r["lon"])
                st.write(f"[🚶 Deschide traseu pe jos Google Maps]({url_gmaps})")
        else:
            st.error("Nu au fost găsite biciclete disponibile în apropiere.")

    elif st.session_state.current_view == "Găsește loc de returnare":
        st.subheader("🏁 Cele mai apropiate returnări:")
        near_returns = get_nearest_return_stations(df_current, user_lat, user_lon)
        if not near_returns.empty:
            for _, r in near_returns.iterrows():
                dist_m = int(r["distance"] * 1000)
                st.success(f"**{r['Statie']}** - {r['Locuri goale']} porți libere ({r['Biciclete disponibile']} biciclete) - la {dist_m}m de tine. [{r['Scor returnare']}]")
                url_gmaps = make_google_maps_walking_url(st.session_state.user_location[0] if st.session_state.user_location else None, st.session_state.user_location[1] if st.session_state.user_location else None, r["lat"], r["lon"])
                st.write(f"[🚶 Deschide traseu pe jos Google Maps]({url_gmaps})")
        else:
            st.error("Nu au fost găsite porți libere în apropiere.")

    elif st.session_state.current_view == "Traseul meu":
        st.subheader("📍 Planifică traseu cu VeloTM")
        route_start = st.selectbox("Origine:", options=list(settings.keys())[:-1]) # elimină commutes din listă
        route_end = st.selectbox("Destinație:", options=list(settings.keys())[:-1])
        
        start_coords = settings.get(route_start)
        end_coords = settings.get(route_end)
        
        if start_coords and end_coords:
            best_pick = get_nearest_bike_stations(df_current, start_coords[0], start_coords[1], n=1)
            best_drop = get_nearest_return_stations(df_current, end_coords[0], end_coords[1], n=1)
            
            if not best_pick.empty and not best_drop.empty:
                bp = best_pick.iloc[0]
                bd = best_drop.iloc[0]
                
                dist1 = int(haversine_distance(start_coords[0], start_coords[1], bp["lat"], bp["lon"]) * 1000)
                dist2 = int(haversine_distance(bd["lat"], bd["lon"], end_coords[0], end_coords[1]) * 1000)
                
                st.markdown(f"**Preluare de la:** {bp['Statie']} ({bp['Biciclete disponibile']} biciclete) - la {dist1}m pietonal.")
                st.markdown(f"**Returnare la:** {bd['Statie']} ({bd['Locuri goale']} porți libere) - la {dist2}m pietonal.")
                
                merita = "DA, merită să folosești VeloTM acum!" if (dist1 < 1000 and dist2 < 1000 and bp["Biciclete disponibile"] > 1 and bd["Locuri goale"] > 1) else "NU se recomandă acum (distanțe mari sau indisponibilități)."
                st.write(f"**Verdict:** {merita}")
                
                url_s = make_google_maps_walking_url(start_coords[0], start_coords[1], bp["lat"], bp["lon"])
                url_d = make_google_maps_walking_url(bd["lat"], bd["lon"], end_coords[0], end_coords[1])
                st.write(f"[🚶 Traseu pietonal pornire]({url_s}) | [🚶 Traseu pietonal destinație]({url_d})")

    elif st.session_state.current_view == "Favorite":
        st.subheader("⭐️ Favorite configurate")
        
        # Secțiune pentru setare locație direct prin Click pe Hartă (ex: ACASĂ)
        target_f = st.radio("Configurează coordonate favorite prin click pe hartă:", ["ACASĂ", "SPITAL", "CENTRU", "GARĂ", "FACULTATE", "IULIUS TOWN", "CUSTOM"])
        st.write("Sfat: Dă click pe harta de dedesubt pentru a salva automat noua poziție.")
        
        picker_map = folium.Map(location=[user_lat, user_lon], zoom_start=14)
        for name, coords in settings.items():
            if name != "commutes" and coords:
                folium.Marker(coords, tooltip=name, icon=folium.Icon(color="purple")).add_to(picker_map)
                
        map_data = st_folium(picker_map, height=300, use_container_width=True, key="station_picker_map")
        
        if map_data and map_data.get("last_clicked"):
            click_lat = map_data["last_clicked"]["lat"]
            click_lon = map_data["last_clicked"]["lng"]
            settings[target_f] = [click_lat, click_lon]
            save_user_settings(settings)
            st.success(f"Poziție configurată pentru {target_f}: {click_lat:.5f}, {click_lon:.5f}")
            st.rerun()

        # Afișare rapidă status favorite
        for key in ["ACASĂ", "SPITAL", "CENTRU", "GARĂ", "FACULTATE", "IULIUS TOWN"]:
            coords = settings.get(key)
            if coords:
                near = get_nearest_bike_stations(df_current, coords[0], coords[1], n=1)
                if not near.empty:
                    st.write(f"🏠 **{key}** -> Cea mai apropiată: **{near.iloc[0]['Statie']}** ({near.iloc[0]['Biciclete disponibile']} biciclete)")

    # --- EXCLUDERE MULTIPLE PAGINI: TABEL ȘI ISTORIC ---
    st.markdown("---")
    tab_map, tab_commute, tab_list, tab_charts = st.tabs(["🗺️ Hartă Detaliată", "🔄 Commute Mode", "📋 Toate Stațiile", "📊 Istoric"])
    
    with tab_map:
        m_full = folium.Map(location=[user_lat, user_lon], zoom_start=13)
        folium.Marker([user_lat, user_lon], tooltip="Poziția ta", icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m_full)
        
        for _, r in df_current.iterrows():
            badge_text = r["Biciclete disponibile"]
            color = "green" if r["Status"] == "Online" and badge_text > 5 else "orange" if r["Status"] == "Online" else "red"
            
            p_html = f"<b>{r['Statie']}</b><br>Disponibile: {r['Biciclete disponibile']}<br>Porți libere: {r['Locuri goale']}"
            folium.Marker(
                [r["lat"], r["lon"]],
                popup=folium.Popup(p_html, max_width=200),
                tooltip=f"{r['Statie']}: {badge_text} biciclete",
                icon=folium.Icon(color=color, icon="bicycle", prefix="fa")
            ).add_to(m_full)
        st_folium(m_full, height=400, use_container_width=True, key="main_folium_map")

    with tab_commute:
        st.subheader("🔄 Rute Commute active:")
        for comm in settings.get("commutes", []):
            start_name = comm["start"]
            end_name = comm["end"]
            start_c = settings.get(start_name)
            end_c = settings.get(end_name)
            
            if start_c and end_c:
                st_p = get_nearest_bike_stations(df_current, start_c[0], start_c[1], n=1)
                st_r = get_nearest_return_stations(df_current, end_c[0], end_c[1], n=1)
                
                if not st_p.empty and not st_r.empty:
                    p_sta = st_p.iloc[0]
                    r_sta = st_r.iloc[0]
                    worth = "🟢 Merită VeloTM" if (p_sta["Biciclete disponibile"] > 2 and r_sta["Locuri goale"] > 2) else "🔴 Riscant"
                    st.write(f"🔄 **{comm['name']}** -> Plecare: **{p_sta['Statie']}** ({p_sta['Biciclete disponibile']} biciclete) | Destinație: **{r_sta['Statie']}** ({r_sta['Locuri goale']} libere) | **{worth}**")

    with tab_list:
        st.subheader("📋 Situația completă:")
        filter_status = st.selectbox("Filtrează stațiile:", ["toate", "online", "offline", "cu biciclete disponibile", "fără biciclete", "cu locuri goale"])
        
        filtered = df_current.copy()
        if filter_status == "online":
            filtered = filtered[filtered["Status"] == "Online"]
        elif filter_status == "offline":
            filtered = filtered[filtered["Status"] == "Offline"]
        elif filter_status == "cu biciclete disponibile":
            filtered = filtered[filtered["Biciclete disponibile"] > 0]
        elif filter_status == "fără biciclete":
            filtered = filtered[filtered["Biciclete disponibile"] == 0]
        elif filter_status == "cu locuri goale":
            filtered = filtered[filtered["Locuri goale"] > 0]
            
        st.dataframe(filtered[["Statie", "Biciclete disponibile", "Locuri goale", "Status", "Scor preluare", "Scor returnare"]], use_container_width=True, hide_index=True)

    with tab_charts:
        st.subheader("📊 Analitice & Predicții:")
        df_history = load_history_from_sqlite()
        
        if not df_history.empty:
            st.write("Evoluție rețea generală:")
            summed = df_history.groupby("timestamp")["bikes_available"].sum().reset_index()
            fig = px.line(summed, x="timestamp", y="bikes_available", title="Total biciclete disponibile în timp")
            st.plotly_chart(fig, use_container_width=True)
            
            # Predicții simple
            st.write("📈 Predicție de risc stație:")
            sel_st = st.selectbox("Alege o stație pentru predicție:", options=df_current["Statie"].unique())
            hist_st = df_history[df_history["station_name"] == sel_st].copy()
            if not hist_st.empty:
                hist_st["hour"] = hist_st["timestamp"].dt.hour
                avg_bikes_hour = hist_st[hist_st["hour"] == datetime.now().hour]["bikes_available"].mean()
                if not pd.isna(avg_bikes_hour):
                    risk_txt = "risc mare să fie goală." if avg_bikes_hour < 1.5 else "risc redus."
                    st.write(f"La această oră, stația de obicei are în medie {avg_bikes_hour:.1f} biciclete. **Rezultat:** {risk_txt}")
            
            # Stații problematice
            st.subheader("Top stații problematice:")
            most_empty = df_history[df_history["bikes_available"] == 0].groupby("station_name").size().reset_index(name="Apariții Goală").sort_values(by="Apariții Goală", ascending=False).head(3)
            st.dataframe(most_empty, use_container_width=True, hide_index=True)
        else:
            st.caption("Istoricul se va compila după rularea în fundal și salvarea mai multor snapshot-uri.")

# --- SECȚIUNE ALERTE INTERNE ---
if "alerts" not in st.session_state:
    st.session_state.alerts = []
    
new_alerts = detect_station_changes(st.session_state.current_df, st.session_state.prev_df)
if new_alerts:
    st.session_state.alerts.extend(new_alerts)
    
if st.session_state.alerts:
    st.markdown("### 🔔 Evenimente Recente:")
    for al in st.session_state.alerts[-5:]: # ultimele 5 alerte în interfață
        st.caption(al)
