from mcp.server.fastmcp import FastMCP

import requests
from dotenv import load_dotenv
import os

load_dotenv()
EXCHANGE_RATE_API_KEY=os.getenv("EXCHANGE_RATE_API_KEY", "")


mcp=FastMCP("Currency Server")




@mcp.tool()
def convert_currency_with_api(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts an amount using a specific API service (ExchangeRate-API).
    Returns a string with the conversion result.
    Eg. "100 USD = 82.34 EUR"
    """
    # The URL structure uses the 'from' currency as the base
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/{from_currency}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        
        data = response.json()
        rates = data.get("conversion_rates", {})
        
        if to_currency in rates:
            rate = rates[to_currency]
            converted_amount = amount * rate
            print(f"{amount} {from_currency} = {round(converted_amount, 2)} {to_currency}")

            return f"{amount} {from_currency} = {round(converted_amount, 2)} {to_currency}"
        else:
            print(f"Target currency code '{to_currency}' not found in the API response.")
            return f"Target currency code '{to_currency}' not found in the API response."

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch exchange rates: {e}")
        return f"Failed to fetch exchange rates. {e}"



#The transport="stdio" argument tells the server to:

#Use standard input/output (stdin and stdout) to receive and respond to tool function calls.

if __name__=="__main__":
    mcp.run(transport="stdio")