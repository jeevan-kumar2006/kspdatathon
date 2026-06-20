"""
KSP Crime Intelligence Platform — Backend
Serves a single index.html with all API routes.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from config import (
    DISTRICTS, CRIME_TYPES, WEATHER_CITIES, NAME_MAP_REV
)
from database import get_db, init_db, generate_data
from services import (
    fetch_district_boundaries, fetch_police_stations,
    nominatim_search, fetch_weather, weather_description, weather_icon,
    fetch_wiki_summary,
    compute_hotspots, compute_anomalies, compute_predictions
)

# Point STATIC_DIR to the "static" folder
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[KSP] Starting — initializing database...")
    init_db()
    generate_data()
    print("[KSP] Ready — http://localhost:8000")
    yield
    print("[KSP] Shutting down")


app = FastAPI(title="KSP Crime Intelligence Platform", version="4.0.0",
              lifespan=lifespan)

# This allows your browser to load style.css and app.js
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)


@app.get("/")
async def serve_dashboard():
    """Serve the single-page dashboard from the static folder."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"error": f"index.html not found at {index_path}"}

# ... [KEEP THE REST OF YOUR app.py EXACTLY THE SAME] ...


@app.get("/api/health")
def health():
    return {"status": "operational", "service": "KSP v4.0"}


@app.get("/api/dashboard/stats")
def dashboard_stats():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM incidents"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Under Investigation'"); pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Chargesheet Filed'"); charged = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents"); dists = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT station) FROM incidents"); stats = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents WHERE severity>=8"); highrisk = c.fetchone()[0]
    c.execute("SELECT strftime('%Y-%m',date) as m, COUNT(*) as c FROM incidents GROUP BY m ORDER BY m LIMIT 24")
    monthly = [{"month": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("SELECT crime_type, COUNT(*) as c FROM incidents GROUP BY crime_type ORDER BY c DESC")
    by_type = [{"type": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("SELECT district, COUNT(*) as c FROM incidents GROUP BY district ORDER BY c DESC LIMIT 10")
    by_dist = [{"district": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("SELECT hour, COUNT(*) as c FROM incidents GROUP BY hour ORDER BY hour")
    hourly = [{"hour": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("""SELECT CASE WHEN severity<=3 THEN 'Low' WHEN severity<=6 THEN 'Medium'
                 WHEN severity<=8 THEN 'High' ELSE 'Critical' END as lvl, COUNT(*) as c
                 FROM incidents GROUP BY lvl""")
    severity = [{"level": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("SELECT district, COUNT(*) as c, AVG(severity) as s FROM incidents GROUP BY district")
    dist_crime = [{"district": r[0], "count": r[1], "avg_sev": round(r[2], 1)} for r in c.fetchall()]
    conn.close()
    return {"total_incidents": total, "pending_investigation": pending,
            "chargesheeted": charged, "districts_active": dists,
            "stations_active": stats, "high_risk_districts": highrisk,
            "monthly_trend": monthly, "by_crime_type": by_type,
            "by_district": by_dist, "hourly_distribution": hourly,
            "severity_distribution": severity, "district_crime": dist_crime}


@app.get("/api/incidents/map")
def map_incidents(district: Optional[str] = None,
                  crime_type: Optional[str] = None, limit: int = 2000):
    conn = get_db(); c = conn.cursor()
    q = """SELECT id, crime_type, district, station, latitude, longitude,
                  date, time, hour, severity, status
           FROM incidents WHERE 1=1"""
    p = []
    if district: q += " AND district=?"; p.append(district)
    if crime_type: q += " AND crime_type=?"; p.append(crime_type)
    q += f" ORDER BY RANDOM() LIMIT {limit}"
    c.execute(q, p)
    data = [dict(r) for r in c.fetchall()]; conn.close()
    return data


@app.get("/api/incidents/district/{district_name}")
def district_incidents(district_name: str):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, crime_type, station, latitude, longitude,
                        date, time, hour, severity, status
                 FROM incidents WHERE district=? ORDER BY date DESC""", (district_name,))
    data = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT station, COUNT(*) as c, AVG(severity) as s
                 FROM incidents WHERE district=? GROUP BY station ORDER BY c DESC""", (district_name,))
    stations = [{"station": r[0], "count": r[1], "avg_sev": round(r[2], 1)} for r in c.fetchall()]
    c.execute("""SELECT crime_type, COUNT(*) as c FROM incidents
                 WHERE district=? GROUP BY crime_type ORDER BY c DESC""", (district_name,))
    types = [{"type": r[0], "count": r[1]} for r in c.fetchall()]
    c.execute("""SELECT hour, COUNT(*) as c FROM incidents
                 WHERE district=? GROUP BY hour ORDER BY hour""", (district_name,))
    hours = [{"hour": r[0], "count": r[1]} for r in c.fetchall()]
    conn.close()
    return {"incidents": data, "stations": stations, "types": types, "hours": hours}


@app.get("/api/hotspots")
def hotspots():
    return compute_hotspots()


@app.get("/api/network")
def network_data(limit: int = 80):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT p.id, p.name, p.role, p.alias, COUNT(ip.incident_id) as ic
                 FROM persons p JOIN incident_persons ip ON p.id=ip.person_id
                 GROUP BY p.id ORDER BY ic DESC LIMIT ?""", (limit,))
    nodes = []; nm = {}
    for r in c.fetchall():
        nid = str(r[0])
        nodes.append({"id": nid, "label": r[1][:18],
                       "title": f"{r[1]} ({r[2]}) — {r[4]} cases",
                       "group": r[2], "value": min(25, r[4] * 3)})
        nm[r[0]] = nid
    edges = []
    c.execute("""SELECT person_id_1, person_id_2, association_type, weight
                 FROM person_associations LIMIT 150""")
    for r in c.fetchall():
        if r[0] in nm and r[1] in nm:
            edges.append({"from": nm[r[0]], "to": nm[r[1]],
                          "label": r[2], "title": f"{r[2]} ({r[3]})",
                          "value": r[3] * 10})
    c.execute("""SELECT ip1.person_id, ip2.person_id, i.crime_type
                 FROM incident_persons ip1
                 JOIN incident_persons ip2 ON ip1.incident_id=ip2.incident_id
                     AND ip1.person_id < ip2.person_id
                 JOIN incidents i ON i.id=ip1.incident_id LIMIT 120""")
    for r in c.fetchall():
        if r[0] in nm and r[1] in nm:
            edges.append({"from": nm[r[0]], "to": nm[r[1]],
                          "label": "Co-involved", "title": f"Linked via {r[2]}",
                          "value": 2, "dashes": True})
    conn.close()
    return {"nodes": nodes, "edges": edges}


@app.get("/api/predictions")
def predictions():
    return compute_predictions()


@app.get("/api/anomalies")
def anomalies():
    return compute_anomalies()


@app.get("/api/trend-alerts")
def trend_alerts():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT MAX(date) FROM incidents"); mx = c.fetchone()[0]
    if not mx: conn.close(); return []
    from datetime import date, timedelta
    mx_d = date.fromisoformat(mx)
    rs = (mx_d - timedelta(days=30)).isoformat()
    ps = (mx_d - timedelta(days=60)).isoformat()
    c.execute("""SELECT district, crime_type,
                 SUM(CASE WHEN date>=? THEN 1 ELSE 0 END) as recent,
                 SUM(CASE WHEN date>=? AND date<? THEN 1 ELSE 0 END) as previous
                 FROM incidents WHERE date>=?
                 GROUP BY district, crime_type
                 HAVING recent > previous*1.3 AND recent > 3
                 ORDER BY (recent-previous) DESC LIMIT 8""", (rs, ps, rs, ps))
    alerts = []
    for r in c.fetchall():
        pct = round(((r[2] - r[3]) / max(1, r[3])) * 100, 0)
        alerts.append({"district": r[0], "crime_type": r[1],
            "recent": r[2], "previous": r[3], "increase_pct": pct,
            "severity": "critical" if pct > 100 else ("high" if pct > 50 else "medium")})
    conn.close()
    return alerts


@app.get("/api/repeat-offenders")
def repeat_offenders(limit: int = 15):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT p.id, p.name, p.alias, p.age, p.gender,
                        p.last_known_location, COUNT(ip.incident_id) as ic,
                        GROUP_CONCAT(DISTINCT i.crime_type) as ct,
                        GROUP_CONCAT(DISTINCT i.modus_operandi) as mo,
                        GROUP_CONCAT(DISTINCT i.district) as dd
                 FROM persons p
                 JOIN incident_persons ip ON p.id=ip.person_id
                 JOIN incidents i ON i.id=ip.incident_id
                 WHERE ip.relationship='suspect_in'
                 GROUP BY p.id HAVING ic > 1 ORDER BY ic DESC LIMIT ?""", (limit,))
    result = []
    for r in c.fetchall():
        result.append({"id": r[0], "name": r[1], "alias": r[2] or "",
            "age": r[3], "gender": r[4], "location": r[5] or "Unknown",
            "incident_count": r[6],
            "crime_types": list(set(r[7].split(","))) if r[7] else [],
            "methods": list(set(r[8].split(","))) if r[8] else [],
            "districts": list(set(r[9].split(","))) if r[9] else []})
    conn.close()
    return result


@app.get("/api/socio-economic")
def socio_economic():
    import random
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT district, COUNT(*) as c, AVG(severity) as sev FROM incidents GROUP BY district")
    cd = {r[0]: {"total": r[1], "avg_sev": round(r[2], 2)} for r in c.fetchall()}
    conn.close()
    return [{"district": d, "crime_count": cd.get(d, {"total": 0, "avg_sev": 0})["total"],
             "avg_severity": cd.get(d, {"total": 0, "avg_sev": 0})["avg_sev"],
             "population_density": random.randint(200, 8000),
             "urbanization_rate": round(random.uniform(0.2, 0.95), 2),
             "literacy_rate": round(random.uniform(0.6, 0.95), 2),
             "poverty_index": round(random.uniform(0.05, 0.4), 2)}
            for d in DISTRICTS]


@app.get("/api/districts")
def get_districts():
    return list(DISTRICTS.keys())


@app.get("/api/crime-types")
def get_crime_types():
    return CRIME_TYPES


@app.get("/api/geo/boundaries")
def geo_boundaries():
    return fetch_district_boundaries()


@app.get("/api/geo/stations")
def geo_stations():
    return fetch_police_stations()


@app.get("/api/geo/search")
def geo_search(q: str = Query(..., min_length=2)):
    try:
        return nominatim_search(q)
    except Exception as e:
        raise HTTPException(502, str(e))


@app.get("/api/geo/weather-cities")
def geo_weather_cities():
    results = []
    for city in WEATHER_CITIES:
        w = fetch_weather(city["lat"], city["lng"])
        if w:
            results.append({"city": city["name"], "temperature": w["temperature"],
                "windspeed": w["windspeed"], "weathercode": w["weathercode"],
                "description": weather_description(w["weathercode"]),
                "icon": weather_icon(w["weathercode"])})
    return results


@app.get("/api/geo/weather")
def geo_weather(lat: float, lng: float):
    w = fetch_weather(lat, lng)
    if not w:
        raise HTTPException(502, "Weather fetch failed")
    return {"temperature": w["temperature"], "windspeed": w["windspeed"],
            "weathercode": w["weathercode"],
            "description": weather_description(w["weathercode"]),
            "icon": weather_icon(w["weathercode"])}


@app.get("/api/geo/district-wiki/{district_name}")
def geo_district_wiki(district_name: str):
    names = [district_name]
    if district_name in NAME_MAP_REV:
        names.append(NAME_MAP_REV[district_name] + " district")
    names.append(district_name + " district")
    for name in names:
        result = fetch_wiki_summary(name)
        if result and result.get("extract"):
            return result
    return {"title": district_name, "extract": "No data available.", "thumbnail": ""}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
