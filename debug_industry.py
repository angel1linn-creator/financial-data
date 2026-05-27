import yfinance as yf

tickers = ["2330.TW", "2357.TW", "2353.TW"]
for t in tickers:
    print(f"Testing {t}...")
    s = yf.Ticker(t)
    info = s.info
    print(f"  Short Name: {info.get('shortName')}")
    print(f"  Industry: {info.get('industry')}")
    print(f"  Sector: {info.get('sector')}")
    print("-" * 20)
