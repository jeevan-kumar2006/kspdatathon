# KSP Crime Intelligence Platform

A real-time crime intelligence dashboard built for the **Karnataka State Police (KSP)** Datathon. It provides an interactive map-based interface for visualizing, filtering, and analyzing crime data across all 27 districts of Karnataka.

---

## Features

- **Interactive Map** — Leaflet-based map with crime hotspot heatmaps, police station markers, and red-zone overlays
- **District Drill-Down** — Click into any district to view station-level stats, crime-type breakdowns, and time distributions
- **Predictive Risk** — Scikit-learn powered next-month crime forecasts per district with trend indicators
- **Network & Link Analysis** — Vis.js force graph connecting suspects, victims, and witnesses across incidents
- **Anomaly Detection** — Automatic flagging of statistical outliers in crime frequency
- **Repeat Offenders** — Searchable suspect/offender registry with role tagging (Suspect / Victim / Witness / Accused)
- **Live Weather Strip** — Real-time weather for 6 major Karnataka cities via Open-Meteo (no API key required)
- **Time Filter Slider** — Filter all data by hour of day (0–23) or view all hours at once
- **Advanced Viz Panel** — Expandable side panel with district-level charts for crime types and time distribution
- **Dark / Light Mode** — Toggle with a floating button; preference persisted in `localStorage`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · Uvicorn |
| Database | SQLite (`ksp_crime.db`) |
| ML / Analytics | NumPy · Scikit-learn |
| Frontend | Vanilla HTML · CSS · JavaScript |
| Maps | Leaflet.js |
| Charts | Chart.js |
| Network Graph | Vis-Network |
| External APIs | Open-Meteo · Nominatim (OSM) · Overpass API · Wikipedia REST |

---

## Project Structure

```
kspdatathon/
├── app.py            # FastAPI application & all API routes
├── config.py         # Districts, crime types, reference data & external API URLs
├── database.py       # SQLite schema, seeding, and query helpers
├── services.py       # Hotspot, anomaly & prediction logic; external API wrappers
├── requirements.txt  # Python dependencies
├── ksp_crime.db      # SQLite database (auto-generated on first run)
└── static/
    ├── index.html    # Single-page application shell
    ├── style.css     # All styles (dark/light theme, layout, components)
    └── app.js        # Frontend logic (map, charts, network graph, API calls)
```

---

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/jeevan-kumar2006/kspdatathon.git
cd kspdatathon

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app:app --reload
```

Then open **http://localhost:8000** in your browser.

> The database (`ksp_crime.db`) is auto-generated with synthetic data on first run if it does not already exist.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend SPA |
| `GET` | `/api/stats` | Summary KPIs (totals, pending, chargesheet, etc.) |
| `GET` | `/api/incidents` | Paginated incident list with filters |
| `GET` | `/api/hotspots` | Top crime hotspot locations |
| `GET` | `/api/predictions` | Next-month risk predictions per district |
| `GET` | `/api/anomalies` | Detected anomalies in recent data |
| `GET` | `/api/network` | Suspect-victim-witness graph data |
| `GET` | `/api/weather` | Live weather for major Karnataka cities |
| `GET` | `/api/search` | Geocoding via Nominatim |
| `POST` | `/api/suspects` | Add a new person (suspect / victim / witness) |
| `GET` | `/api/suspects` | List all tracked persons |

---

## Data

All crime incident data is **synthetically generated** for demonstration purposes. It includes:

- **27 Karnataka districts** with real geographic coordinates
- **15 crime types** (Theft, Robbery, Burglary, Murder, Assault, Cyber Crime, etc.)
- **Realistic police station names** per district
- Kannada-region first and last names for anonymized persons

---

## External Services Used

All external services are **free and require no API keys**:

- [Open-Meteo](https://open-meteo.com/) — Weather data
- [Nominatim (OpenStreetMap)](https://nominatim.org/) — Location search & geocoding
- [Overpass API](https://overpass-api.de/) — Police station locations from OSM
- [Wikipedia REST API](https://www.mediawiki.org/wiki/API:REST_API) — District summaries

---

## License

This project was built for the **KSP Datathon** competition. All crime data is synthetic and for demonstration only.
