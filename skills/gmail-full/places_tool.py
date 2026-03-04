#!/usr/bin/env python3
"""Google Places tool for OpenClaw."""
import os, sys, json, urllib.request, urllib.parse

# Read API key from .env
API_KEY = ''
env_path = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('GOOGLE_MAPS_API_KEY='):
                API_KEY = line.strip().split('=', 1)[1]

def search_places(query, location="42.3398,-71.0892", radius=2000):
    """Search for places near a location. Default: Northeastern University."""
    url = f"https://places.googleapis.com/v1/places:searchText"
    data = json.dumps({
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": float(location.split(',')[0]), "longitude": float(location.split(',')[1])},
                "radius": radius
            }
        },
        "maxResultCount": 5
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri,places.currentOpeningHours.openNow,places.priceLevel"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            places = []
            for p in result.get('places', []):
                places.append({
                    "name": p.get('displayName', {}).get('text', ''),
                    "address": p.get('formattedAddress', ''),
                    "rating": p.get('rating', 'N/A'),
                    "reviews": p.get('userRatingCount', 0),
                    "open_now": p.get('currentOpeningHours', {}).get('openNow', 'unknown'),
                    "price": p.get('priceLevel', 'N/A'),
                    "maps_url": p.get('googleMapsUri', '')
                })
            print(json.dumps(places, indent=2))
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}", "details": e.read().decode()[:500]}))

def get_directions(origin, destination, mode="transit"):
    """Get directions. Mode: transit, driving, walking, bicycling."""
    params = urllib.parse.urlencode({
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": API_KEY
    })
    url = f"https://maps.googleapis.com/maps/api/directions/json?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data['status'] != 'OK':
                print(json.dumps({"error": data['status']}))
                return
            route = data['routes'][0]['legs'][0]
            steps = []
            for s in route['steps'][:10]:
                steps.append(s.get('html_instructions', '').replace('<b>','').replace('</b>','').replace('<div style="font-size:0.9em">',', ').replace('</div>',''))
            print(json.dumps({
                "distance": route['distance']['text'],
                "duration": route['duration']['text'],
                "start": route['start_address'],
                "end": route['end_address'],
                "steps": steps
            }, indent=2))
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}", "details": e.read().decode()[:500]}))

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if action == 'search':
        query = sys.argv[2]
        location = sys.argv[3] if len(sys.argv) > 3 else "42.3398,-71.0892"
        search_places(query, location)
    elif action == 'directions':
        origin = sys.argv[2]
        dest = sys.argv[3]
        mode = sys.argv[4] if len(sys.argv) > 4 else "transit"
        get_directions(origin, dest, mode)
    else:
        print("Usage: places_tool.py search|directions <args>")
