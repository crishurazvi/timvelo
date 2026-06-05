import streamlit as st
import pandas as pd
import requests
import re
import json
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# Configurare pagină Streamlit
st.set_page_config(
    page_title="VeloTM Live Monitor",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Date Demo / Fallback extrase din sursa paginii oferite de utilizator
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

# Funcție pentru descărcarea paginii HTML live
def fetch_page(url: str, cookie: str = None) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    if cookie:
        headers["Cookie"] = cookie.strip()
        
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Nu s-a putut descărca pagina. Detalii eroare: {str(e)}")

# Funcție pentru extragerea array-ului JS prin regex
def extract_stations_from_html(html_content: str) -> list:
    # Căutare optimizată a variabilei "items" care conține structura de stații
    items_match = re.search(
        r"var\s+items\s*=\s*(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])\s*;",
        html_content,
        re.DOTALL
    )
    if not items_match:
        # Căutare secundară mai relaxată în caz că formatarea variază ușor
        items_match = re.search(
            r"(\[\s*\{\s*['\"]StationName['\"].*?\}\s*\])",
            html_content,
            re.DOTALL
        )
        if not items_match:
            raise ValueError(
                "Nu s-a putut găsi structura JSON a stațiilor în codul sursă HTML."
            )
            
    json_str = items_match.group(1)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Eroare la parsarea datelor JSON extrase: {str(e)}")

# Funcție pentru normalizarea și curățarea datelor în Pandas DataFrame
def normalize_stations(raw_data: list) -> pd.DataFrame:
    if not raw_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(raw_data)
    
    # Maparea exactă a coloanelor conform cerințelor
    column_mapping = {
        "StationName": "Statie",
        "Address": "Adresa",
        "OcuppiedSpots": "Biciclete disponibile",
        "EmptyDoors": "Locuri goale",
        "Status": "Status",
        "Latitude": "lat",
        "Longitude": "lon"
    }
    
    # Validare structură date
    missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Datele din sursă nu conțin coloanele: {missing_cols}")
        
    df = df.rename(columns=column_mapping)
    
    # Conversii de tipuri
    df["Biciclete disponibile"] = pd.to_numeric(df["Biciclete disponibile"], errors='coerce').fillna(0).astype(int)
    df["Locuri goale"] = pd.to_numeric(df["Locuri goale"], errors='coerce').fillna(0).astype(int)
    df["lat"] = pd.to_numeric(df["lat"], errors='coerce')
    df["lon"] = pd.to_numeric(df["lon"], errors='coerce')
    
    # Eliminare spații inutile
    df["Statie"] = df["Statie"].astype(str).str.strip()
    df["Adresa"] = df["Adresa"].astype(str).str.strip()
    df["Status"] = df["Status"].astype(str).str.strip()
    
    return df

# Funcție ajutătoare pentru re-împrospătare date
def refresh_data_action(url, cookie, use_demo):
    try:
        if use_demo:
            html = DEMO_HTML
        else:
            html = fetch_page(url, cookie)
            
        data = extract_stations_from_html(html)
        df = normalize_stations(data)
        st.session_state.stations_df = df
        st.session_state.last_updated = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        st.session_state.error_msg = None
    except Exception as e:
        st.session_state.error_msg = str(e)

# --- Inițializare Session State ---
if "stations_df" not in st.session_state:
    st.session_state.stations_df = None
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = None

# --- SIDEBAR CONFIGURARE ---
st.sidebar.image("https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=150&q=80", use_container_width=True)
st.sidebar.title("Configurare Monitor")

# URL Sursă
default_url = "https://www.ratt.ro/vtm/harta-statii-biciclete"
url_input = st.sidebar.text_input("URL Hartă VeloTM:", value=default_url)

# Mod Demo / Fallback în caz de probleme de rețea sau CORS
use_demo_data = st.sidebar.checkbox(
    "Utilizează date Demo (offline)", 
    value=False,
    help="Activează această opțiune dacă site-ul public are probleme de rețea sau necesită VPN/Autentificare suplimentară."
)

# Autentificare via Session Cookie (st.secrets sau input direct)
secret_cookie = st.secrets.get("vtm_cookie", "") if "vtm_cookie" in st.secrets else ""
cookie_input = st.sidebar.text_input(
    "Cookie Sesiune (opțional):", 
    value=secret_cookie, 
    type="password",
    help="Dacă pagina necesită autentificare, introduceți valoarea parametrului Cookie."
)

# Interval Auto-Refresh
refresh_interval = st.sidebar.selectbox(
    "Interval Auto-Refresh:",
    options=[0, 30, 60, 120, 300],
    format_func=lambda x: "Oprit" if x == 0 else f"{x} secunde"
)

# Declanșare Auto-Refresh din pachetul streamlit-autorefresh
if refresh_interval > 0:
    st_autorefresh(interval=refresh_interval * 1000, key="data_autorefresh_trigger")

# Buton Actualizare Manuală
if st.sidebar.button("♻️ Actualizează datele", use_container_width=True) or st.session_state.stations_df is None:
    with st.spinner("Se descarcă și parsează datele live..."):
        refresh_data_action(url_input, cookie_input, use_demo_data)

# --- SECȚIUNE INTERFAȚĂ PRINCIPALĂ ---
st.title("🚲 VeloTM Live Monitor")
st.markdown("Monitorizarea în timp real a stațiilor de bike-sharing din Timișoara.")

# Afișare erori în cazul în care parsarea eșuează
if st.session_state.error_msg:
    st.error(f"⚠️ A apărut o eroare: {st.session_state.error_msg}")
    st.info("Puteți bifa opțiunea 'Utilizează date Demo (offline)' din meniul lateral pentru a testa funcționalitatea aplicației cu datele furnizate în codul sursă.")

# Verificare existență date
df = st.session_state.stations_df

if df is not None and not df.empty:
    
    # --- SECȚIUNE METRICE ---
    total_bikes = df["Biciclete disponibile"].sum()
    total_spots = df["Locuri goale"].sum()
    
    statii_online = df[df["Status"] == "Online"].shape[0]
    statii_offline = df[df["Status"] == "Offline"].shape[0]
    statii_altele = df[~df["Status"].isin(["Online", "Offline"])].shape[0]
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Biciclete Disponibile", total_bikes)
    m2.metric("Porturi / Locuri Goale", total_spots)
    m3.metric("Stații Online 🟢", statii_online)
    m4.metric("Stații Offline 🔴", statii_offline)
    m5.metric("Stații Sub/Suprapopulate 🟡", statii_altele)
    
    if st.session_state.last_updated:
        st.caption(f"Ultima actualizare a datelor: **{st.session_state.last_updated}**")
        
    st.markdown("---")
    
    # --- FILTRE INTERACTIVE ---
    st.subheader("Filtrare și Căutare")
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        filter_status = st.selectbox(
            "Filtrează stațiile din vizualizări:",
            options=[
                "Toate stațiile",
                "Doar stații online",
                "Doar stații offline",
                "Doar stații cu biciclete disponibile",
                "Doar stații fără biciclete"
            ]
        )
        
    with col_f2:
        search_term = st.text_input("Caută după nume sau adresă:", placeholder="Ex: Modern, Mocioni, Bulevardul...").strip()
        
    # Aplicare filtre în DataFrame
    filtered_df = df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df["Statie"].str.contains(search_term, case=False, na=False) |
            filtered_df["Adresa"].str.contains(search_term, case=False, na=False)
        ]
        
    if filter_status == "Doar stații online":
        filtered_df = filtered_df[filtered_df["Status"] == "Online"]
    elif filter_status == "Doar stații offline":
        filtered_df = filtered_df[filtered_df["Status"] == "Offline"]
    elif filter_status == "Doar stații cu biciclete disponibile":
        filtered_df = filtered_df[filtered_df["Biciclete disponibile"] > 0]
    elif filter_status == "Doar stații fără biciclete":
        filtered_df = filtered_df[filtered_df["Biciclete disponibile"] == 0]
        
    # --- AFIȘARE REZULTATE PE TABS ---
    tab1, tab2 = st.tabs(["🗺️ Hartă Interactivă", "📊 Tabel Date"])
    
    with tab1:
        st.markdown("#### Locațiile stațiilor și disponibilitatea pe hartă")
        
        # Centrare hartă pe coordonatele medii ale Timișoarei din datele noastre
        mean_lat = filtered_df["lat"].mean() if not filtered_df["lat"].isnull().all() else 45.75372
        mean_lon = filtered_df["lon"].mean() if not filtered_df["lon"].isnull().all() else 21.22571
        
        m = folium.Map(location=[mean_lat, mean_lon], zoom_start=13, control_scale=True)
        
        for _, row in filtered_df.iterrows():
            # Stabilire culoare marker în funcție de status
            status = row["Status"]
            if status == "Online":
                marker_color = "green"
            elif status == "Offline":
                marker_color = "red"
            else:
                marker_color = "orange" # pentru Subpopulated / Suprapopulated
                
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 13px; width: 220px; line-height: 1.4;">
                <h5 style="margin: 0 0 5px 0; color: #2c3e50; font-weight: bold;">{row['Statie']}</h5>
                <hr style="margin: 5px 0; border: 0; border-top: 1px solid #eee;" />
                <p style="margin: 3px 0;"><b>Adresă:</b> {row['Adresa']}</p>
                <p style="margin: 3px 0;"><b>Biciclete disponibile:</b> <span style="color:green; font-weight:bold;">{row['Biciclete disponibile']}</span></p>
                <p style="margin: 3px 0;"><b>Locuri goale:</b> <span style="color:#2980b9; font-weight:bold;">{row['Locuri goale']}</span></p>
                <p style="margin: 3px 0;"><b>Status:</b> <span style="color:{'green' if status == 'Online' else 'red' if status == 'Offline' else 'orange'}; font-weight:bold;">{row['Status']}</span></p>
            </div>
            """
            
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row["Statie"],
                icon=folium.Icon(color=marker_color, icon="bicycle", prefix="fa")
            ).add_to(m)
            
        st_folium(m, height=550, use_container_width=True, returned_objects=[])
        
    with tab2:
        st.markdown(f"Se afișează **{filtered_df.shape[0]}** stații conform filtrelor aplicate.")
        st.dataframe(
            filtered_df[["Statie", "Adresa", "Biciclete disponibile", "Locuri goale", "Status"]],
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Introduceți configurările corecte în panoul lateral și apăsați pe 'Actualizează datele'.")
