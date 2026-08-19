import json

DEFAULT_LOCATIONS = [
    {"city": "Dubai", "country": "ae"},
    {"city": "Kochi", "country": "in"},
    {"city": "Bangalore", "country": "in"},
    {"city": "Abu Dhabi", "country": "ae"},
    {"city": "Singapore", "country": "sg"},
]

DEFAULT_LOCATIONS_JSON = json.dumps(DEFAULT_LOCATIONS)


def parse_locations(locations_json: str, fallback_location: str, fallback_country: str):
    if locations_json:
        try:
            items = json.loads(locations_json)
            if isinstance(items, list) and items:
                return [
                    {"city": i["city"], "country": i.get("country", fallback_country)}
                    for i in items
                    if i.get("city")
                ]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return [{"city": fallback_location, "country": fallback_country}]
