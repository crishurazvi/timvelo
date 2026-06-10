# VeloTM Radar

VeloTM Radar este o aplicație full-stack pentru monitorizarea live a stațiilor VeloTM din Timișoara. Backend-ul face scraping live de pe portalul oficial VeloTM, normalizează datele, calculează scoruri, salvează istoric SQLite, detectează evenimente și oferă meteo prin Open-Meteo fără API key. Frontend-ul este o interfață mobile-first în React, Vite, Tailwind CSS și Leaflet.

## Arhitectură

```txt
backend/   FastAPI, scraper, SQLite, APScheduler, Open-Meteo
frontend/  React + Vite + Tailwind CSS + React Leaflet + Recharts
```

## Funcționalități

- scraping live de la `http://www.velotm.ro/harta-statii-biciclete`
- parser robust pentru `var items = [...]`
- normalizare `OcuppiedSpots` ca biciclete disponibile și `EmptyDoors` ca locuri goale
- scor de preluare și scor de returnare
- recomandări pentru cele mai apropiate stații cu biciclete și cu locuri goale
- planificator punct A → punct B
- linkuri Google Maps pentru mers pe jos
- hartă live cu marker colorat și badge de biciclete
- puncte personale în localStorage: ACASĂ, SPITAL, CENTRU, GARĂ, FACULTATE, IULIUS TOWN, CUSTOM
- stații favorite în localStorage
- istoric pe stație și grafice Recharts
- evenimente recente: apar biciclete, se golește stația, devine offline, apar locuri goale
- meteo bike-friendly prin Open-Meteo, fără API key

## Rulare backend local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend-ul citește portul din variabila `PORT`. Pentru Render:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Rulare frontend local

```bash
cd frontend
npm install
npm run dev
```

Frontend-ul folosește implicit:

```txt
VITE_API_BASE_URL=http://localhost:8000
```

În Render setează:

```txt
VITE_API_BASE_URL=https://numele-backendului.onrender.com
```

## Deployment pe Render

### Backend

Creează un Render Web Service:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Variabile recomandate:

```txt
VELOTM_URL=http://www.velotm.ro/harta-statii-biciclete
SCRAPE_INTERVAL_MINUTES=10
DB_PATH=history.sqlite
```

### Frontend

Creează un Render Static Site:

- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`

Variabilă necesară:

```txt
VITE_API_BASE_URL=https://URL-BACKEND-RENDER.onrender.com
```

Există și `render.yaml` pentru blueprint, dar pentru control mai fin poți crea serviciile manual.

## Limitare Render free și SQLite

Pe Render free, filesystem-ul este efemer. Baza `history.sqlite` poate dispărea la restart sau redeploy. Pentru MVP este acceptabil, dar istoricul real persistent trebuie mutat ulterior spre PostgreSQL, Supabase sau altă bază externă.

Codul izolează accesul la DB în `backend/database.py`, deci migrarea spre PostgreSQL poate fi făcută înlocuind funcțiile din acel modul fără a rescrie frontend-ul.

## Cum funcționează scraping-ul

`backend/scraper.py` descarcă HTML-ul paginii oficiale VeloTM, caută `showStations()` și apoi `var items = [...]`. Array-ul JavaScript este extras printr-un parser cu balansare de paranteze, curățat de trailing commas și convertit cu `json.loads`.

Câmpuri mapate:

```txt
StationName -> name
Address -> address
OcuppiedSpots -> bikes_available
EmptyDoors -> empty_doors
Status -> status
Latitude -> latitude
Longitude -> longitude
```

Dacă scraping-ul eșuează, backend-ul păstrează ultimele date valide din cache sau DB și trimite un `warning` în răspunsul API.

## Geolocație

Frontend-ul folosește API-ul de geolocație al browserului. Pe telefoane și browsere moderne, geolocația cere HTTPS sau localhost. Dacă utilizatorul refuză, aplicația permite alegerea punctelor pe hartă.

Statusuri folosite:

```txt
idle, requesting, granted, denied, unavailable
```

## Setarea punctului ACASĂ

Mergi în tabul Favorite, alege `ACASĂ`, dă click pe hartă, apoi apasă `Salvează ACASĂ`. Coordonatele sunt salvate în localStorage sub cheia:

```txt
velotm_personal_points
```

## Ruta punct A → punct B

În tabul Traseu, alege plecarea și destinația. Poți folosi poziția curentă, puncte salvate, hartă sau coordonate manuale ca fallback. Frontend-ul trimite un POST către `/api/route`, iar backend-ul alege:

1. stația optimă de preluare lângă A
2. stația optimă de returnare lângă B
3. distanțele de mers pe jos
4. verdictul `Merită VeloTM acum` sau `Nu merită acum`

## Google Maps walking

Linkurile se generează în formatul:

```txt
https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={lat},{lon}&travelmode=walking
```

Dacă nu există origine, se folosește search:

```txt
https://www.google.com/maps/search/?api=1&query={lat},{lon}
```

## Meteo fără API key

Backend-ul folosește Open-Meteo. Nu este necesar API key. Scorul bike-friendly este calculat din temperatură, vânt, precipitații, cod meteo și zi/noapte.

Etichete:

```txt
8-10: Excelent pentru bicicletă
5-7: Acceptabil
0-4: Mai bine nu
```

Dacă API-ul meteo eșuează, endpointul întoarce `weather_available: false`, fără să blocheze aplicația.

## Istoric și evenimente

APScheduler rulează scraping la fiecare 10 minute. Fiecare snapshot este comparat cu precedentul. Nu se salvează duplicate inutile dacă datele sunt identice și a trecut foarte puțin timp.

Endpointuri utile:

```txt
GET /api/stations
POST /api/refresh
POST /api/route
GET /api/history/{station_name}
GET /api/events
GET /api/weather
GET /api/health
```

## Migrare ulterioară la PostgreSQL

1. Creează o bază PostgreSQL pe Render, Supabase sau alt provider.
2. Adaugă `DATABASE_URL` în env.
3. Înlocuiește implementarea din `backend/database.py` cu SQLAlchemy sau psycopg.
4. Păstrează aceleași funcții publice: `save_snapshot`, `get_latest_snapshot`, `get_station_history`, `save_events`, `get_recent_events`.
5. Frontend-ul nu trebuie modificat dacă API-ul păstrează același contract.
