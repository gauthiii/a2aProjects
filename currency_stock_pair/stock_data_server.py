import yfinance as yf
from datetime import datetime

from mcp.server.fastmcp import FastMCP

import pandas as pd



mcp=FastMCP("Stock Data Server")




@mcp.tool()
def get_current_date():
    """
    Returns the current date as a string.
    """
    return datetime.now().strftime("%Y-%m-%d")

@mcp.tool()
def get_stock_data(symbol, start_date, end_date):
    """
    Returns a clean DataFrame with columns:
    Date, Close, High, Open, Volume
    """
    df = yf.download(symbol, start=start_date, end=end_date)

    # Reset index to make 'Date' a column
    df = df.reset_index()

    # If multi-level columns exist (as with yfinance), flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() for col in df.columns.values]

    # Standardize column names (handle cases like 'Close_NVDA')
    rename_map = {}
    for col in df.columns:
        for key in ["Date", "Close", "High", "Open", "Volume"]:
            if key.lower() in col.lower():
                rename_map[col] = key
    df = df.rename(columns=rename_map)

    # Keep only required columns, in order
    df = df[["Date", "Close", "High", "Open", "Volume"]]

    return df.astype(str)



#The transport="stdio" argument tells the server to:

#Use standard input/output (stdin and stdout) to receive and respond to tool function calls.

if __name__=="__main__":
    mcp.run(transport="stdio")