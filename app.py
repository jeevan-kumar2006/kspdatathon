"""
KSP Crime Intelligence & Analytical Platform — Main Application
Serves the frontend dashboard and all API endpoints.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional

from config import DISTRICTS, CRIME_TYPES, WEATHER_CITIES
from database import get_db, init_db, generate_data
from services import (
    fetch_district_boundaries, fetch_police_stations,
    nominatim_search, fetch_weather, weather_description, weather_icon,
    fetch_wiki_summary, normalize_district_name,
    compute_hotspots, compute_anomalies, compute_predictions
)

STATIC_DIR = Path(__file__).parent / "static"


# ── Lifespan: startup/shutdown ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[KSP] Starting — initializing database...")
    init_db()
    generate_data()
    print("[KSP] Ready — http://localhost:8000")
    yield
    print("[KSP] Shutting down")


app = FastAPI(title="KSP Crime Intelligence Platform", version="3.0.0",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ── Serve Frontend ──────────────────────────────────────────────────
@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"error": "static/index.html not found"}


# ── Health Check ────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "operational",
        "service": "KSP Crime Intelligence Platform v3.0",
        "apis": {
            "overpass": "active",
            "nominatim": "active",
            "openmeteo": "active",
            "wikipedia": "active"
        }
    }


# ── Dashboard Statistics ────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def dashboard_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM incidents")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Under Investigation'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Chargesheet Filed'")
    charged = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents")
    districts = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT station) FROM incidents")
    stations = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents WHERE severity>=8")
    highrisk = c.fetchone()[0]

    c.execute("""SELECT strftime('%Y-%m',date) as m, COUNT(*) as c
                 FROM incidents GROUP BY m ORDER BY m LIMIT 24""")
    monthly = [{"month": r[0], "count": r[1]} for r in c.fetchall()]

    c.execute("SELECT crime_type, COUNT(*) as c FROM incidents GROUP BY crime_type ORDER BY c DESC")
    by_type = [{"type": r[0], "count": r[1]} for r in c.fetchall()]

    c.execute("SELECT district, COUNT(*) as c FROM incidents GROUP BY district ORDER BY c DESC LIMIT 10")
    by_dist = [{"district": r[0], "count": r[1]} for r in c.fetchall()]

    c.execute("SELECT hour, COUNT(*) as c FROM incidents GROUP BY hour ORDER BY hour")
    hourly = [{"hour": r[0], "count": r[1]} for r in c.fetchall()]

    c.execute("""SELECT CASE
                 WHEN severity<=3 THEN 'Low'
                 WHEN severity<=6 THEN 'Medium'
                 WHEN severity<=8 THEN 'High'
                 ELSE 'Critical' END as lvl, COUNT(*) as c
                 FROM incidents GROUP BY lvl""")
    severity = [{"level": r[0], "count": r[1]} for r in c.fetchall()]

    c.execute("SELECT district, COUNT(*) as c, AVG(severity) as s FROM incidents GROUP BY district")
    dist_crime = [{"district": r[0], "count": r[1], "avg_sev": round(r[2], 1)}
                  for r in c.fetchall()]

    conn.close()
    return {
        "total_incidents": total, "pending_investigation": pending,
        "chargesheeted": charged, "districts_active": districts,
        "stations_active": stations, "high_risk_districts": highrisk,
        "monthly_trend": monthly, "by_crime_type": by_type,
        "by_district": by_dist, "hourly_distribution": hourly,
        "severity_distribution": severity, "district_crime": dist_crime
    }


# ── Map Incidents ───────────────────────────────────────────────────
@app.get("/api/incidents/map")
def map_incidents(district: Optional[str] = None,
                  crime_type: Optional[str] = None,
                  limit: int = 1500):
    conn = get_db()
    c = conn.cursor()
    query = """SELECT id, crime_type, district, station, latitude, longitude,
                      date, time, severity, status
               FROM incidents WHERE 1=1"""
    params = []
    if district:
        query += " AND district=?"
        params.append(district)
    if crime_type:
        query += " AND crime_type=?"
        params.append(crime_type)
    query += f" ORDER BY RANDOM() LIMIT {limit}"
    c.execute(query, params)
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data


# ── Hotspots (KMeans) ──────────────────────────────────────────────
@app.get("/api/hotspots")
def hotspots():
    return compute_hotspots()


# ── Network Analysis ────────────────────────────────────────────────
@app.get("/api/network")
def network_data(limit: int = 80):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT p.id, p.name, p.role, p.alias, COUNT(ip.incident_id) as ic
                 FROM persons p
                 JOIN incident_persons ip ON p.id=ip.person_id
                 GROUP BY p.id ORDER BY ic DESC LIMIT ?""", (limit,))
    nodes = []
    node_map = {}
    for r in c.fetchall():
        nid = str(r[0])
        nodes.append({
            "id": nid,
            "label": r[1][:18],
            "title": f"{r[1]} ({r[2]}) — {r[4]} cases",
            "group": r[2],
            "value": min(25, r[4] * 3)
        })
        node_map[r[0]] = nid

    edges = []
    # Direct associations
    c.execute("""SELECT person_id_1, person_id_2, association_type, weight
                 FROM person_associations LIMIT 150""")
    for r in c.fetchall():
        if r[0] in node_map and r[1] in node_map:
            edges.append({
                "from": node_map[r[0]], "to": node_map[r[1]],
                "label": r[2], "title": f"{r[2]} ({r[3]})",
                "value": r[3] * 10
            })

    # Case-based links
    c.execute("""SELECT ip1.person_id, ip2.person_id, i.crime_type
                 FROM incident_persons ip1
                 JOIN incident_persons ip2 ON ip1.incident_id=ip2.incident_id
                     AND ip1.person_id < ip2.person_id
                 JOIN incidents i ON i.id=ip1.incident_id
                 LIMIT 120""")
    for r in c.fetchall():
        if r[0] in node_map and r[1] in node_map:
            edges.append({
                "from": node_map[r[0]], "to": node_map[r[1]],
                "label": "Co-involved",
                "title": f"Linked via {r[2]}",
                "value": 2, "dashes": True
            })
    conn.close()
    return {"nodes": nodes, "edges": edges}


# ── Predictions (Linear Regression) ────────────────────────────────
@app.get("/api/predictions")
def predictions():
    return compute_predictions()


# ── Anomalies (Isolation Forest) ───────────────────────────────────
@app.get("/api/anomalies")
def anomalies():
    return compute_anomalies()


# ── Trend Alerts ────────────────────────────────────────────────────
@app.get("/api/trend-alerts")
def trend_alerts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM incidents")
    max_date = c.fetchone()[0]
    if not max_date:
        conn.close()
        return []

    from datetime import date, timedelta
    mx = date.fromisoformat(max_date)
    recent_start = (mx - timedelta(days=30)).isoformat()
    prev_start = (mx - timedelta(days=60)).isoformat()

    c.execute("""SELECT district, crime_type,
                 SUM(CASE WHEN date>=? THEN 1 ELSE 0 END) as recent,
                 SUM(CASE WHEN date>=? AND date<? THEN 1 ELSE 0 END) as previous
                 FROM incidents WHERE date>=?
                 GROUP BY district, crime_type
                 HAVING recent > previous*1.3 AND recent > 3
                 ORDER BY (recent-previous) DESC LIMIT 8""",
              (recent_start, prev_start, recent_start, prev_start))

    alerts = []
    for r in c.fetchall():
        pct = round(((r[2] - r[3]) / max(1, r[3])) * 100, 0)
        alerts.append({
            "district": r[0], "crime_type": r[1],
            "recent": r[2], "previous": r[3],
            "increase_pct": pct,
            "severity": "critical" if pct > 100 else ("high" if pct > 50 else "medium")
        })
    conn.close()
    return alerts


# ── Repeat Offenders ────────────────────────────────────────────────
@app.get("/api/repeat-offenders")
def repeat_offenders(limit: int = 15):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT p.id, p.name, p.alias, p.age, p.gender,
                        p.last_known_location, COUNT(ip.incident_id) as ic,
                        GROUP_CONCAT(DISTINCT i.crime_type) as ct,
                        GROUP_CONCAT(DISTINCT i.modus_operandi) as mo,
                        GROUP_CONCAT(DISTINCT i.district) as dd
                 FROM persons p
                 JOIN incident_persons ip ON p.id=ip.person_id
                 JOIN incidents i ON i.id=ip.incident_id
                 WHERE ip.relationship='suspect_in'
                 GROUP BY p.id HAVING ic > 1
                 ORDER BY ic DESC LIMIT ?""", (limit,))
    result = []
    for r in c.fetchall():
        result.append({
            "id": r[0], "name": r[1], "alias": r[2] or "",
            "age": r[3], "gender": r[4],
            "location": r[5] or "Unknown",
            "incident_count": r[6],
            "crime_types": list(set(r[7].split(","))) if r[7] else [],
            "methods": list(set(r[8].split(","))) if r[8] else [],
            "districts": list(set(r[9].split(","))) if r[9] else []
        })
    conn.close()
    return result


# ── Socio-Economic ──────────────────────────────────────────────────
@app.get("/api/socio-economic")
def socio_economic():
    import random
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT district, COUNT(*) as c, AVG(severity) as sev FROM incidents GROUP BY district")
    crime_data = {r[0]: {"total": r[1], "avg_sev": round(r[2], 2)} for r in c.fetchall()}
    conn.close()

    result = []
    for district, info in DISTRICTS.items():
        cd = crime_data.get(district, {"total": 0, "avg_sev": 0})
        result.append({
            "district": district,
            "crime_count": cd["total"],
            "avg_severity": cd["avg_sev"],
            "population_density": random.randint(200, 8000),
            "urbanization_rate": round(random.uniform(0.2, 0.95), 2),
            "literacy_rate": round(random.uniform(0.6, 0.95), 2),
            "poverty_index": round(random.uniform(0.05, 0.4), 2)
        })
    return result


# ── Reference Data ──────────────────────────────────────────────────
@app.get("/api/districts")
def get_districts():
    return list(DISTRICTS.keys())

@app.get("/api/crime-types")
def get_crime_types():
    return CRIME_TYPES


# ── External API Proxies ───────────────────────────────────────────
@app.get("/api/geo/boundaries")
def geo_boundaries():
    """Overpass API: real Karnataka district boundary polygons."""
    return fetch_district_boundaries()

@app.get("/api/geo/stations")
def geo_stations():
    """Overpass API: real police station POIs."""
    return fetch_police_stations()

@app.get("/api/geo/search")
def geo_search(q: str = Query(..., min_length=2)):
    """Nominatim API: geocode a location."""
    try:
        return nominatim_search(q)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/geo/weather-cities")
def geo_weather_cities():
    """Open-Meteo API: weather for 6 Karnataka cities."""
    results = []
    for city in WEATHER_CITIES:
        w = fetch_weather(city["lat"], city["lng"])
        if w:
            results.append({
                "city": city["name"],
                "temperature": w["temperature"],
                "windspeed": w["windspeed"],
                "weathercode": w["weathercode"],
                "winddir": w["winddir"],
                "description": weather_description(w["weathercode"]),
                "icon": weather_icon(w["weathercode"])
            })
    return results

@app.get("/api/geo/weather")
def geo_weather(lat: float, lng: float):
    """Open-Meteo API: weather for any coordinates."""
    w = fetch_weather(lat, lng)
    if not w:
        raise HTTPException(502, "Weather fetch failed")
    return {
        "temperature": w["temperature"],
        "windspeed": w["windspeed"],
        "weathercode": w["weathercode"],
        "description": weather_description(w["weathercode"]),
        "icon": weather_icon(w["weathercode"])
    }

@app.get("/api/geo/district-wiki/{district_name}")
def geo_district_wiki(district_name: str):
    """Wikipedia REST API: district summary."""
    names = [district_name]
    if district_name in (getattr(__import__('config'), 'NAME_MAP_REV', {})):
        names.append(
            __import__('config').NAME_MAP_REV[district_name] + " district"
        )
    names.append(district_name + " district")
    for name in names:
        result = fetch_wiki_summary(name)
        if result and result.get("extract"):
            return result
    return {"title": district_name, "extract": "No data available.", "thumbnail": ""}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
