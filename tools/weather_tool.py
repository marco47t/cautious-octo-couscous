import urllib.request
import json
from utils.logger import logger

def get_weather(city: str) -> str:
    """Get current weather conditions for any city in the world.

    Args:
        city: City name e.g. 'Cairo', 'London', 'New York'.

    Returns:
        Current weather including temperature, conditions, humidity, and wind.
    """
    try:
        url = f"https://wttr.in/{urllib.request.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "PersonalAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        area_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]

        return (
            f"🌤️ Weather in {area_name}, {country}:\n\n"
            f"🌡️ Temperature: {current['temp_C']}°C / {current['temp_F']}°F\n"
            f"🌡️ Feels like: {current['FeelsLikeC']}°C\n"
            f"☁️ Condition: {current['weatherDesc'][0]['value']}\n"
            f"💧 Humidity: {current['humidity']}%\n"
            f"💨 Wind: {current['windspeedKmph']} km/h {current['winddir16Point']}\n"
            f"👁️ Visibility: {current['visibility']} km"
        )
    except Exception as e:
        logger.error(f"Weather error for {city}: {e}")
        return f"Could not get weather for '{city}': {e}"
