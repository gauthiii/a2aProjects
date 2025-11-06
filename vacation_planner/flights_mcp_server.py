from mcp.server.fastmcp import FastMCP
import json

import requests
from dotenv import load_dotenv
import os

load_dotenv()
RAPID_GOOGLE_FLIGHTS_API=os.getenv("RAPID_GOOGLE_FLIGHTS_API", "")


mcp=FastMCP("Flights Server")




@mcp.tool()
def search_flights(querystring: str) -> str:
    """
    Uses Google FLights API to search for flights based on the given parameters.
    The query string must look like this:
    {"departure_id":"LAX","arrival_id":"JFK","outbound_date":"2025-12-24","return_date":"2026-01-09","travel_class":"ECONOMY","adults":"1","show_hidden":"1","currency":"USD","language_code":"en-US","country_code":"US","search_type":"best"}
    Return the search results in JSON format that is converted into a string.
    """
    # url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"

    # querystring = {"departure_id":"LAX","arrival_id":"JFK","outbound_date":"2025-12-24","return_date":"2026-01-09","travel_class":"ECONOMY","adults":"1","show_hidden":"1","currency":"USD","language_code":"en-US","country_code":"US","search_type":"best"}

    # headers = {
    #     "x-rapidapi-key": RAPID_GOOGLE_FLIGHTS_API,
    #     "x-rapidapi-host": "google-flights2.p.rapidapi.com"
    # }

    # response = requests.get(url, headers=headers, params=querystring)

    # return json.dumps(response.json())

    return "Your flight ticket is 100 USD"



#The transport="stdio" argument tells the server to:

#Use standard input/output (stdin and stdout) to receive and respond to tool function calls.

if __name__=="__main__":
    mcp.run(transport="stdio")