"""Strategy generator.

Builds a candidate universe by composing ENTRY x FILTER x REGIME x EXIT x
MANAGEMENT, but constrained: each family declares which regimes and filters it
is logically compatible with, so we get a broad universe without a meaningless
cartesian blow-up (a mean-reversion strategy gated to "strong trend only with a
volatility-expansion filter" is not worth a backtest slot).
"""
from __future__ import annotations

import itertools

from backtest import Config
from signals import COUNTER_TREND, FAMILIES

TRENDING = {"trend": ["strong_up", "strong_down", "weak_up", "weak_down"]}
STRONG = {"trend": ["strong_up", "strong_down"]}
RANGING = {"trend": ["range", "weak_up", "weak_down"]}
HIGHVOL = {"vol": ["high", "normal"]}
EXPANDING = {"vol_state": ["expanding"]}
ANY = None

# family -> (regimes to try, filter sets to try, trend modes)
RECIPES = {
    # baseline family from the earlier research phase, with and without the
    # market-wide regime gate, at several clock speeds
    "volatility_breakout":   ([ANY], [["btc_regime"], ["btc_regime", "volume"], ["not_flat"], []],
                              ["with", "both"]),
    "breakout":            ([ANY, EXPANDING, HIGHVOL], [["volume", "not_flat"], ["volume", "vol_expanding"], ["not_flat", "vwap"]], ["with", "both"]),
    "range_breakout":        ([ANY, EXPANDING], [["volume"], ["volume", "not_flat"]], ["both", "with"]),
    "trend_continuation":    ([TRENDING, STRONG], [["adx"], ["adx", "volume"], ["not_flat"]], ["with"]),
    "pullback":              ([TRENDING, STRONG], [["adx"], ["volume", "not_flat"], ["adx", "vwap"]], ["with"]),
    "mean_reversion":        ([RANGING, ANY], [["not_flat"], ["volatility"], ["not_flat", "vwap"]], ["against", "both"]),
    "channel":               ([RANGING, ANY], [["not_flat"], ["volatility"]], ["against", "both"]),
    "sr_rejection":          ([ANY, RANGING], [["volume"], ["not_flat"]], ["both", "against"]),
    "momentum":              ([TRENDING, ANY], [["volume", "not_flat"], ["adx"]], ["with", "both"]),
    "vol_expansion":         ([EXPANDING, ANY], [["volume"], ["volume", "not_flat"]], ["with", "both"]),
    "vol_contraction_break": ([ANY, EXPANDING], [["volume"], ["not_flat"]], ["both", "with"]),
    "trendline_bounce":      ([TRENDING, STRONG], [["adx"], ["not_flat"]], ["with"]),
    "reentry_pullback":      ([TRENDING, ANY], [["adx"], ["volume", "not_flat"]], ["with"]),
    "reversal":              ([ANY, RANGING], [["not_flat"], ["volume"]], ["against", "both"]),
    "rsi_divergence":        ([ANY, RANGING], [["not_flat"], ["volume"]], ["against", "both"]),
    "breakout_retest":       ([ANY, EXPANDING], [["volume"], ["volume", "not_flat"]], ["with", "both"]),
}

# exit / management templates -- the GG-Shot-style ladder is one option, not the law
EXITS = {
    "ladder_4": dict(tp_mode="atr", tp_atr=(1.5, 3.0, 5.0, 8.0), tp_frac=(0.50, 0.25, 0.15, 0.10)),
    "ladder_fast": dict(tp_mode="atr", tp_atr=(1.0, 2.0, 3.5, 6.0), tp_frac=(0.50, 0.25, 0.15, 0.10)),
    "ladder_wide": dict(tp_mode="atr", tp_atr=(2.0, 4.0, 7.0, 12.0), tp_frac=(0.40, 0.30, 0.20, 0.10)),
    "half_half": dict(tp_mode="atr", tp_atr=(2.0, 4.0, 99, 99), tp_frac=(0.50, 0.50, 0.0, 0.0)),
    "runner": dict(tp_mode="atr", tp_atr=(1.5, 99, 99, 99), tp_frac=(0.50, 0.0, 0.0, 0.0), trail_after_tp=1),
    "no_tp_trail": dict(tp_mode="none", tp_atr=(), tp_frac=(), trail_after_tp=0),
}

MANAGEMENT = {
    "be_on": dict(breakeven_after_tp1=True),
    "be_off": dict(breakeven_after_tp1=False),
    "be_trail": dict(breakeven_after_tp1=True, trail_after_tp=2, trail_atr=2.5),
    "osc_exit": dict(breakeven_after_tp1=True, osc_exit=True),
}

STOPS = [("atr2", dict(stop_mode="atr", stop_atr=2.0)),
         ("atr3", dict(stop_mode="atr", stop_atr=3.0)),
         # Disaster-only stop: measured during development, the volatility
         # family's edge comes from holding to the reverse signal -- a 2-3 ATR
         # stop cut PF from 1.65 to 1.07. This keeps a stop far enough out to
         # prevent liquidation while letting that style compete.
         ("wide", dict(stop_mode="atr", stop_atr=8.0)),
         ("struct", dict(stop_mode="structure", stop_atr=2.0))]

ENTRIES = [("instant", dict(entry_mode="instant")),
           ("split", dict(entry_mode="split"))]

# --- short-side treatments -------------------------------------------------
# Diagnosis: longs and shorts hit at the same rate but payoff is 6.21 vs 1.88,
# and shorts bleed specifically in `strong_down`. Each option below attacks one
# of those two facts; "sym" is the old symmetric behaviour, kept as the control.
SHORT_MODES = {
    "sym": ({}, {}),
    "off": ({"direction": "long"}, {}),
    # shorts take profit instead of riding, since short winners do not run
    "tp": ({}, dict(short_tp_mode="atr", short_tp_atr=(1.5, 3.0, 5.0, 99),
                    short_tp_frac=(0.5, 0.3, 0.2, 0.0), short_max_bars=120)),
    # avoid the squeeze-prone strongest downtrends
    "weakdn": ({"short_regime": ["weak_down", "range"]}, {}),
    # both fixes together
    "tp_weakdn": ({"short_regime": ["weak_down", "range"]},
                  dict(short_tp_mode="atr", short_tp_atr=(1.5, 3.0, 5.0, 99),
                       short_tp_frac=(0.5, 0.3, 0.2, 0.0), short_max_bars=120)),
    # keep the runner exit but cut losers faster and cap holding time
    "tight": ({}, dict(short_stop_atr=1.5, short_max_bars=96)),
}


def _regime_name(rg) -> str:
    if rg is None:
        return "any"
    return "+".join("".join(w[0] for w in v[0].split("_")) for v in rg.values()) or "any"


def generate(full: bool = False, short_modes: list[str] | None = None) -> list[dict]:
    """Return candidate strategy definitions.

    `full=False` keeps one representative exit/management/stop combination per
    signal recipe (breadth first); `full=True` expands the management grid for
    the finalists.
    """
    out = []
    for fam, (regimes, filtersets, modes) in RECIPES.items():
        # the volatility-breakout family carries its own clock/threshold grid
        # faster clocks and lower thresholds included so higher-frequency
        # variants can compete against the slow ones on equal terms
        param_grid = [{"bars": b, "atr_mult": m}
                      for b in (1, 2, 3, 4) for m in (1.0, 1.5, 2.0, 2.5, 3.0)] \
            if fam == "volatility_breakout" else [{}]
        if fam == "breakout":
            param_grid = [{"lookback": n} for n in (10, 20, 40)]
        for rg, fs, mode in itertools.product(regimes, filtersets, modes):
            if fam in COUNTER_TREND and mode == "with":
                continue                       # contradictory by construction
            exits = EXITS.items() if full else [("ladder_4", EXITS["ladder_4"]),
                                                ("runner", EXITS["runner"]),
                                                ("no_tp_trail", EXITS["no_tp_trail"])]
            mgmt = MANAGEMENT.items() if full else [("be_on", MANAGEMENT["be_on"])]
            stops = STOPS if full else STOPS[:3]
            entries = ENTRIES if full else ENTRIES[:1]
            shorts = SHORT_MODES.items() if short_modes is None else \
                [(k, SHORT_MODES[k]) for k in short_modes]
            for prm, (en, ec), (sn, sc), (xn, xc), (mn, mc), (shn, (sspec, scfg)) in \
                    itertools.product(param_grid, entries, stops, exits, mgmt, shorts):
                cfg = dict(ec)
                cfg.update(sc)
                cfg.update(xc)
                cfg.update(mc)
                cfg.update(scfg)
                ptag = ("|" + "_".join(f"{k}{v}" for k, v in prm.items())) if prm else ""
                sid = (f"{fam}|{_regime_name(rg)}|{'+'.join(fs) or 'nofilt'}|{mode}"
                       f"|{sn}|{xn}|{mn}|{en}|sh_{shn}{ptag}")
                spec = {"family": fam, "filters": fs, "regime": rg,
                        "trend_mode": mode, "direction": "both",
                        "min_score": 0.0, "params": dict(prm)}
                spec.update(sspec)
                out.append({"id": sid, "spec": spec, "cfg": cfg})
    return out


def to_config(d: dict, leverage: float = 2.0) -> Config:
    c = Config(leverage=leverage)
    for k, v in d.items():
        setattr(c, k, v)
    return c


if __name__ == "__main__":
    g = generate()
    print(f"{len(g)} candidates (breadth pass)")
    print(f"{len(generate(full=True))} candidates (full grid)")
    fams = {}
    for x in g:
        fams[x["spec"]["family"]] = fams.get(x["spec"]["family"], 0) + 1
    print(fams)
