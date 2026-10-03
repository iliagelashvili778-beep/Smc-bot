import os, requests, yfinance as yf, pandas as pd

SYMBOLS = {"XAU/USD": "GC=F", "BTC": "BTC-USD", "SOL": "SOL-USD"}
TOKEN = os.environ["TG_TOKEN"]
CHAT = os.environ["TG_CHAT"]
BALANCE = float(os.environ.get("BALANCE", "1000"))
RISK = 0.01

def send(text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT, "text": text}, timeout=20)

def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n).mean()
    return 100 - 100 / (1 + up / dn)

def analyze(name, t):
    df = yf.download(t, period="30d", interval="1h",
                     progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna().iloc[:-1]
    if len(df) < 60:
        return None
    c = df.Close
    df["e20"] = c.ewm(span=20).mean()
    df["e50"] = c.ewm(span=50).mean()
    df["rsi"] = rsi(c)
    last = df.iloc[-1]
    if last.e20 > last.e50 and last.Close > last.e50:
        side = "BUY"
    elif last.e20 < last.e50 and last.Close < last.e50:
        side = "SELL"
    else:
        return None
    rec = df.iloc[-21:-1]
    if side == "BUY":
        sweep = last.Low < rec.Low.min() and last.Close > rec.Low.min()
        rsi_ok = last.rsi < 45
    else:
        sweep = last.High > rec.High.max() and last.Close < rec.High.max()
        rsi_ok = last.rsi > 55
    fvg = False
    for i in range(len(df) - 10, len(df)):
        a, b = df.iloc[i - 2], df.iloc[i]
        if side == "BUY" and b.Low > a.High: fvg = True
        if side == "SELL" and b.High < a.Low: fvg = True
    if not (sweep and (fvg or rsi_ok)):
        return None
    entry = float(last.Close)
    if side == "BUY":
        sl = float(last.Low); tp = entry + 2 * (entry - sl)
    else:
        sl = float(last.High); tp = entry - 2 * (sl - entry)
    risk = abs(entry - sl)
    if risk == 0:
        return None
    size = BALANCE * RISK / risk
    return (f"📊 {name} {side} (H1)\nEntry: {entry:.2f}\nSL: {sl:.2f}\n"
            f"TP: {tp:.2f} (1:2)\nSize: {size:.4f} units (1% risk)\n"
            f"Liquidity sweep ✅ | FVG {'✅' if fvg else '—'} | "
            f"RSI {last.rsi:.0f}")

if os.environ.get("TEST"):
    send("✅ ბოტი მუშაობს")
for n, t in SYMBOLS.items():
    try:
        msg = analyze(n, t)
        if msg:
            send(msg)
    except Exception as e:
        print(n, e)
