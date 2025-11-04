from mcp.server.fastmcp import FastMCP
import os, requests


from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("WeatherMCP")

OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Returns basic weather info for a city.
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_KEY, "units": "metric"}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    return {
        "city": city,
        "temp_c": data["main"]["temp"],
        "description": data["weather"][0]["description"],
    }

if __name__ == "__main__":
    # stdio so MCP clients (agents) can attach
    mcp.run(transport="stdio")
