import pandas as pd
from pathlib import Path
FUT = Path("data/market/dev_1h/binance/futures")
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}
val = {}
for p in FUT.glob("*_USDT_USDT-1h-futures.feather"):
    n = p.name.split("_")[0]
    if n in STABLE: continue
    x = pd.read_feather(p, columns=["date", "close", "volume"]); x["date"] = pd.to_datetime(x["date"], utc=True)
    val[n] = (x.set_index("date")["close"] * x.set_index("date")["volume"]).resample("MS").sum()
V = pd.DataFrame(val)
s = set()
for m in V.index[1:]:
    if m >= pd.Timestamp("2021-12-01", tz="UTC"):
        s |= set(V.shift(1).loc[m].dropna().nlargest(30).index)
have = {p.stem for p in Path("data/market/flow").glob("*.feather")}
print(",".join(sorted(s - have)))
