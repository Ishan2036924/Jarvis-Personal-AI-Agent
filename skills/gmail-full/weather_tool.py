#!/usr/bin/env python3
"""Weather tool using Open-Meteo API (free, no key needed)"""
import sys, json, urllib.request

CITIES = {
    "boston": (42.36, -71.06),
    "new york": (40.71, -74.01),
    "san francisco": (37.77, -122.42),
    "los angeles": (34.05, -118.24),
    "chicago": (41.88, -87.63),
    "seattle": (47.61, -122.33),
    "miami": (25.76, -80.19),
    "denver": (39.74, -104.99),
    "austin": (30.27, -97.74),
    "washington dc": (38.91, -77.04),
}

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

def get_coords(city):
    city_lower = city.lower().strip()
    if city_lower in CITIES:
        return CITIES[city_lower]
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.request.quote(city)}&count=1"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        if data.get('results'):
            r = data['results'][0]
            return (r['latitude'], r['longitude'])
    return None

def get_weather(city="Boston"):
    coords = get_coords(city)
    if not coords:
        print(json.dumps({"error": f"City '{city}' not found"}))
        return
    lat, lon = coords
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&current=temperature_2m,apparent_temperature,weathercode,windspeed_10m,relative_humidity_2m"
           f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
           f"&temperature_unit=fahrenheit&windspeed_unit=mph&timezone=America/New_York&forecast_days=3")
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        current = data['current']
        daily = data['daily']
        result = {
            "location": city,
            "temperature_f": current['temperature_2m'],
            "feels_like_f": current['apparent_temperature'],
            "condition": WEATHER_CODES.get(current['weathercode'], "Unknown"),
            "humidity": f"{current['relative_humidity_2m']}%",
            "wind_mph": current['windspeed_10m'],
            "today_high_f": daily['temperature_2m_max'][0],
            "today_low_f": daily['temperature_2m_min'][0],
            "tomorrow_high_f": daily['temperature_2m_max'][1],
            "tomorrow_low_f": daily['temperature_2m_min'][1],
            "tomorrow_condition": WEATHER_CODES.get(daily['weathercode'][1], "Unknown"),
        }
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else "Boston"
    get_weather(city)
