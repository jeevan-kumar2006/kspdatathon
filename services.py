"""KSP Crime Intelligence Platform — ML Analytics & External API Services"""

import json
import time
import urllib.parse
import numpy as np
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler

import requests

from config import (
    OVERPASS_URL, NOMINATIM_URL, OPENMETEO_URL, WIKI_URL,
    DISTRICTS, NAME_MAP, NAME_MAP_REV, WEATHER_CITIES
)
from database import get_db


# ═══════════════════════════════════════════════════════════════════
# CACHING LAYER — stores external API responses in SQLite
# ═══════════════════════════════════════════════════════════════════

def cache_get(key):
    """Retrieve cached data if not expired."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT data, fetched_at FROM api_cache WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row["data"]), row["fetched_at"]
    return None, None


def cache_set(key, data, ttl=86400):
    """Store data in cache with TTL in seconds."""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO api_cache VALUES (?,?,?)",
              (key, json.dumps(data), time.time() + ttl))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# EXTERNAL APIs — Overpass, Nominatim, Open-Meteo, Wikipedia
# ═══════════════════════════════════════════════════════════════════

def normalize_district_name(name):
    """Convert OSM new names to our DB old names."""
    if not name:
        return ""
    for osm_name, db_name in NAME_MAP.items():
        if osm_name.lower() in name.lower():
            return db_name
    return name.strip()


def fetch_district_boundaries():
    """Fetch Karnataka district boundary polygons from Overpass API."""
    cached, exp = cache_get("overpass_boundaries")
    if cached and exp > time.time():
        print("[OVERPASS] District boundaries from cache")
        return cached

    print("[OVERPASS] Fetching district boundaries (30-90s first time)...")
    query = """
    [out:json][timeout:180];
    area["name"="Karnataka"]["admin_level"="4"]->.state;
    rel(area.state)["admin_level"="6"]["boundary"="administrative"];
    out geom;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=180)
        r.raise_for_status()
        data = r.json()
        geojson = _relations_to_geojson(data.get("elements", []))
        cache_set("overpass_boundaries", geojson, ttl=86400 * 7)
        print(f"[OVERPASS] Got {len(geojson['features'])} boundaries")
        return geojson
    except Exception as e:
        print(f"[OVERPASS] Boundary fetch failed: {e}")
        return cached if cached else {"type": "FeatureCollection", "features": []}


def _relations_to_geojson(relations):
    """Convert Overpass relation elements to GeoJSON FeatureCollection."""
    features = []
    for rel in relations:
        tags = rel.get("tags", {})
        name = tags.get("name", "Unknown")
        outers, inners = [], []
        for member in rel.get("members", []):
            if "geometry" not in member:
                continue
            coords = [[round(p["lon"], 5), round(p["lat"], 5)]
                       for p in member["geometry"]]
            if len(coords) < 4:
                continue
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            if member.get("role", "outer") == "outer":
                outers.append(coords)
            else:
                inners.append(coords)
        if not outers:
            continue
        if len(outers) == 1:
            geometry = {"type": "Polygon", "coordinates": outers + inners}
        else:
            geometry = {"type": "MultiPolygon",
                        "coordinates": [[o] for o in outers]}
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "name_normalized": normalize_district_name(name),
                "osm_id": rel.get("id", 0)
            },
            "geometry": geometry
        })
    return {"type": "FeatureCollection", "features": features}


def fetch_police_stations():
    """Fetch real police station POIs from Overpass API."""
    cached, exp = cache_get("overpass_stations")
    if cached and exp > time.time():
        print("[OVERPASS] Police stations from cache")
        return cached

    print("[OVERPASS] Fetching police stations...")
    query = """
    [out:json][timeout:90];
    area["name"="Karnataka"]->.state;
    (node["amenity"="police"](area.state);
     way["amenity"="police"](area.state););
    out center body;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
        r.raise_for_status()
        data = r.json()
        stations = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat and lon:
                stations.append({
                    "name": tags.get("name", "Police Station"),
                    "lat": lat, "lng": lon,
                    "operator": tags.get("operator", ""),
                    "addr": tags.get("addr:city", ""),
                    "osm_id": el.get("id", 0)
                })
        cache_set("overpass_stations", stations, ttl=86400 * 3)
        print(f"[OVERPASS] Got {len(stations)} police stations")
        return stations
    except Exception as e:
        print(f"[OVERPASS] Station fetch failed: {e}")
        return cached if cached else []


def nominatim_search(query):
    """Geocode a location using Nominatim API."""
    params = {
        "q": query, "format": "json", "limit": 8,
        "bounded": 1, "viewbox": "73.5,11.5,79.0,18.0",
        "accept-language": "en"
    }
    r = requests.get(NOMINATIM_URL, params=params, timeout=10,
                     headers={"User-Agent": "KSP-Crime-Intel/1.0"})
    r.raise_for_status()
    return [{"name": item["display_name"].split(",")[0],
             "full": item["display_name"],
             "lat": float(item["lat"]), "lng": float(item["lon"]),
             "type": item.get("type", "")}
            for item in r.json()]


def fetch_weather(lat, lng):
    """Fetch current weather via Open-Meteo API."""
    cache_key = f"weather_{lat:.1f}_{lng:.1f}"
    cached, exp = cache_get(cache_key)
    if cached and exp > time.time():
        return cached
    try:
        url = f"{OPENMETEO_URL}?latitude={lat}&longitude={lng}&current_weather=true"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        cw = r.json().get("current_weather", {})
        result = {
            "temperature": cw.get("temperature"),
            "windspeed": cw.get("windspeed"),
            "weathercode": cw.get("weathercode"),
            "winddir": cw.get("winddirection")
        }
        cache_set(cache_key, result, ttl=1800)
        return result
    except Exception:
        return cached if cached else None


WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Heavy showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail"
}

def weather_description(code):
    return WEATHER_CODES.get(code, "Unknown")

def weather_icon(code):
    if code <= 1: return "fa-sun"
    if code <= 3: return "fa-cloud-sun"
    if code <= 48: return "fa-smog"
    if code <= 65: return "fa-cloud-rain"
    if code <= 75: return "fa-snowflake"
    if code <= 82: return "fa-cloud-showers-heavy"
    return "fa-bolt"


def fetch_wiki_summary(title):
    """Fetch Wikipedia summary for a district."""
    cache_key = f"wiki_{title}"
    cached, exp = cache_get(cache_key)
    if cached and exp > time.time():
        return cached
    try:
        r = requests.get(
            f"{WIKI_URL}/{urllib.parse.quote(title)}", timeout=10,
            headers={"User-Agent": "KSP-Crime-Intel/1.0"}
        )
        if r.status_code == 200:
            data = r.json()
            result = {
                "title": data.get("title", ""),
                "extract": data.get("extract", "")[:500],
                "thumbnail": (data.get("thumbnail") or {}).get("source", "")
            }
            cache_set(cache_key, result, ttl=86400 * 7)
            return result
    except Exception:
        pass
    return cached if cached else None


# ═══════════════════════════════════════════════════════════════════
# ML ANALYTICS — KMeans, Isolation Forest, Linear Regression
# ═══════════════════════════════════════════════════════════════════

def compute_hotspots():
    """KMeans spatial clustering to find crime hotspots."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT latitude, longitude, crime_type, severity, hour FROM incidents")
    rows = c.fetchall()
    conn.close()

    if len(rows) < 10:
        return []

    coords = np.array([[r[0], r[1]] for r in rows])
    n_clusters = min(15, max(3, len(rows) // 100))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(coords)

    result = []
    for i in range(n_clusters):
        pts = [rows[j] for j in range(len(rows)) if labels[j] == i]
        if len(pts) < 3:
            continue
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        crime_counts = Counter(p[2] for p in pts)
        top_crime, top_count = crime_counts.most_common(1)[0]
        peak_hour = Counter(p[4] for p in pts).most_common(1)[0][0]
        avg_sev = round(sum(p[3] for p in pts) / len(pts), 1)

        result.append({
            "lat": round(sum(lats) / len(lats), 4),
            "lng": round(sum(lngs) / len(lngs), 4),
            "count": len(pts),
            "top_crime": top_crime,
            "top_crime_count": top_count,
            "peak_hour": peak_hour,
            "avg_severity": avg_sev,
            "radius": min(250, len(pts) * 5)
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def compute_anomalies():
    """Isolation Forest to detect statistical anomalies in incidents."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT id, crime_type, district, station, latitude, longitude,
                        date, time, hour, severity, modus_operandi FROM incidents""")
    data = [dict(r) for r in c.fetchall()]
    conn.close()

    if len(data) < 50:
        return []

    le_d = LabelEncoder()
    le_t = LabelEncoder()
    le_s = LabelEncoder()

    features = np.column_stack([
        le_d.fit_transform([d["district"] for d in data]),
        le_t.fit_transform([d["crime_type"] for d in data]),
        le_s.fit_transform([d["station"] for d in data]),
        [d["hour"] for d in data],
        [d["severity"] for d in data],
        [d["latitude"] for d in data],
        [d["longitude"] for d in data]
    ])

    scaler = StandardScaler()
    iso = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    predictions = iso.fit_predict(scaler.fit_transform(features))

    anomalies = []
    for i, pred in enumerate(predictions):
        if pred == -1:
            d = data[i]
            anomalies.append({
                "id": d["id"],
                "crime_type": d["crime_type"],
                "district": d["district"],
                "station": d["station"],
                "date": d["date"],
                "time": d["time"],
                "severity": d["severity"],
                "modus_operandi": d["modus_operandi"],
                "reason": f"Unusual {d['crime_type']} in {d['district']} at {d['time']}"
            })
    return anomalies[:50]


def compute_predictions():
    """Linear regression per-district to predict future crime volume."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT district, strftime('%Y-%m', date) as month, COUNT(*) as count
                 FROM incidents GROUP BY district, month ORDER BY district, month""")
    rows = c.fetchall()
    conn.close()

    district_months = defaultdict(lambda: defaultdict(int))
    for r in rows:
        district_months[r[0]][r[1]] = r[2]

    predictions = []
    for district, months in district_months.items():
        if len(months) < 6:
            continue
        sorted_months = sorted(months.keys())
        values = np.array([months[m] for m in sorted_months], dtype=float)
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)

        next_3 = np.maximum(0, np.polyval(coeffs,
                    [len(values), len(values)+1, len(values)+2])).astype(int)

        recent_avg = np.mean(values[-3:]) if len(values) >= 3 else np.mean(values)
        pred_avg = np.mean(next_3)
        change = ((pred_avg - recent_avg) / max(1, recent_avg)) * 100

        predictions.append({
            "district": district,
            "historical_avg": round(recent_avg, 1),
            "p1": int(next_3[0]), "p2": int(next_3[1]), "p3": int(next_3[2]),
            "trend": "increasing" if coeffs[0] > 1
                     else ("decreasing" if coeffs[0] < -1 else "stable"),
            "risk_change": round(change, 1),
            "risk_level": "high" if change > 20 else ("medium" if change > 5 else "low")
        })

    predictions.sort(key=lambda x: x["risk_change"], reverse=True)
    return predictions
