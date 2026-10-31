"""Candidate generator for the pipeline.

Breadth over depth: each batch is spread across families; a family's share grows when
it produces survivors but never drops to zero, and an identical configuration is never
tested twice (ids are content hashes, checked against pipeline.db).
"""
from __future__ import annotations

import hashlib
import json
import random

import signals as S
import families_v2  # noqa: F401  (registers the new families)

SHORT_ONLY = {"breakdown", "resistance_rejection", "breakdown_retest", "vwap_rejection", "lower_high",
              "bear_trend_continuation", "bear_divergence", "volume_breakdown", "downside_vol_expansion"}

PARAMS = {
    "volatility_breakout": {"bars": [1, 2, 3, 4, 6], "atr_mult": [1.5, 2.0, 2.5, 3.0]},
    "breakout": {"lookback": [10, 20, 40, 55]},
    "pullback": {"depth_atr": [0.3, 0.5, 0.8]},
    "mean_reversion": {"rsi_lo": [20, 25, 30], "rsi_hi": [70, 75, 80]},
    "funding_extreme": {"z": [2.0, 2.5, 3.0]},
    "structure_break": {"lookback": [24, 50, 100]},
    "rel_strength": {"n": [24, 72, 168], "thr": [0.03, 0.05, 0.10]},
    "regime_switch": {"adx_hi": [22, 25, 30], "adx_lo": [15, 18]},
}
COMBO_A = ["breakout", "range_breakout", "structure_break", "vol_contraction_break", "volatility_breakout"]
COMBO_B = ["momentum", "rel_strength", "trend_resume", "rsi_reset", "vol_expansion", "funding_extreme"]
FILTER_SETS = [[], ["btc_regime"], ["btc_regime", "volume"], ["not_flat"], ["volume"], ["vol_expanding"]]
REGIMES = [None, None, None, {"trend": ["strong_up", "strong_down", "weak_up", "weak_down"]},
           {"trend": ["range", "weak_up", "weak_down"]}]
STOPS = [("atr2", {"stop_mode": "atr", "stop_atr": 2.0}), ("atr3", {"stop_mode": "atr", "stop_atr": 3.0}),
         ("wide", {"stop_mode": "atr", "stop_atr": 8.0}), ("struct", {"stop_mode": "structure", "stop_atr": 2.0})]
EXITS = {
    "reverse_only": {"tp_mode": "none", "tp_atr": (), "tp_frac": ()},
    "ladder": {"tp_mode": "atr", "tp_atr": (1.5, 3.0, 5.0, 8.0), "tp_frac": (0.5, 0.25, 0.15, 0.10)},
    "runner": {"tp_mode": "atr", "tp_atr": (1.5, 99, 99, 99), "tp_frac": (0.5, 0, 0, 0), "trail_after_tp": 1},
    "fixed_2r": {"tp_mode": "atr", "tp_atr": (4.0, 99, 99, 99), "tp_frac": (1.0, 0, 0, 0)},
}
HOLD = [24, 96, 400]   # maximum holding period in 1h bars: a day, four days, ~17 days


def families() -> list[str]:
    return sorted(S.FAMILIES)


def cid(spec: dict, cfg: dict) -> str:
    return hashlib.sha1(json.dumps([spec, cfg], sort_keys=True, default=str).encode()).hexdigest()[:12]


def describe(spec: dict, cfg: dict) -> tuple[str, str, str]:
    """(name, entry text, exit text) in plain words for the research record."""
    fam = spec["family"]
    p = spec.get("params") or {}
    ptxt = ", ".join(f"{k}={v}" for k, v in p.items() if k not in ("pa", "pb"))
    name = f"{fam}" + (f"({ptxt})" if ptxt else "") + f" · {'+'.join(spec['filters']) or 'no filter'} · {spec['direction']}"
    entry = (f"{fam} signal{(' (' + ptxt + ')') if ptxt else ''}; filters: {', '.join(spec['filters']) or 'none'}; "
             f"trend mode: {spec.get('trend_mode')}; regime gate: {spec.get('regime') or 'none'}; "
             f"direction: {spec['direction']}; entry at next bar open.")
    tp = {"none": "no take-profit (exit on the opposite signal)", "atr": f"take-profit ladder {cfg.get('tp_atr')} x ATR"}
    ex = (f"stop {cfg['stop_mode']} {cfg['stop_atr']} x ATR; {tp.get(cfg.get('tp_mode'), cfg.get('tp_mode'))}"
          f"{'; trailing after first target' if cfg.get('trail_after_tp') else ''}; opposite signal closes; "
          f"time exit after {cfg['max_bars']} bars.")
    return name, entry, ex


def make(fam: str, rng: random.Random) -> tuple[dict, dict]:
    params = {k: rng.choice(v) for k, v in PARAMS.get(fam, {}).items()}
    if fam == "combo":
        a, b = rng.choice(COMBO_A), rng.choice(COMBO_B)
        params = {"a": a, "b": b, "window": rng.choice([3, 6, 12]),
                  "pa": {k: rng.choice(v) for k, v in PARAMS.get(a, {}).items()},
                  "pb": {k: rng.choice(v) for k, v in PARAMS.get(b, {}).items()}}
    counter = fam in S.COUNTER_TREND
    direction = "short" if fam in SHORT_ONLY else rng.choice(["long", "long", "both", "short"])
    spec = {"family": fam, "params": params, "filters": rng.choice(FILTER_SETS),
            "trend_mode": rng.choice(["against", "both"] if counter else ["with", "both"]),
            "regime": rng.choice(REGIMES), "direction": direction, "min_score": 0.0}
    sname, st = rng.choice(STOPS)
    xname, ex = rng.choice(list(EXITS.items()))
    cfg = {"leverage": 1.0, "entry_mode": "instant", "breakeven_after_tp1": xname != "reverse_only",
           "max_bars": rng.choice(HOLD), **st, **ex}
    return spec, cfg


MAX_SHORT_SHARE = 0.25   # shorts failed 0/28 on the full gate ladder (GO_NO_GO A12); keep exploring, but not mostly


def legacy_trials() -> dict[str, int]:
    """Configurations each family already had before the pipeline (tournament + short sweep)."""
    import sqlite3
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "registry" / "platform.db"
    if not p.exists():
        return {}
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    out = dict(con.execute("SELECT name, configs_tested FROM families").fetchall())
    con.close()
    return out


def next_batch(n: int, tested: set[str], fam_stats: dict[str, tuple[int, int]], seed: int) -> list[dict]:
    """fam_stats: family -> (pipeline trials so far, survivors so far).

    Priority = (1 + 3 x survivors) / (1 + trials), where trials include the family's legacy
    configurations - so never-explored ideas (the new families) come first, and a family that
    produces survivors earns more attempts. Shorts are capped at MAX_SHORT_SHARE of a batch.
    """
    rng = random.Random(seed)
    legacy = legacy_trials()
    tri = {f: fam_stats.get(f, (0, 0))[0] + legacy.get(f, 0) // 50 for f in families()}
    weight = {f: (1 + 3 * fam_stats.get(f, (0, 0))[1]) / (1 + tri[f]) for f in families()}
    out, seen, guard, shorts = [], set(tested), 0, 0
    while len(out) < n and guard < n * 50:
        guard += 1
        fams = sorted(weight, key=lambda f: (-weight[f], rng.random()))
        fam = fams[0] if rng.random() < 0.7 else rng.choice(fams)
        spec, cfg = make(fam, rng)
        if spec["direction"] == "short":
            if shorts >= max(1, int(n * MAX_SHORT_SHARE)):
                if fam in SHORT_ONLY:
                    weight[fam] *= 0.5
                continue
            shorts += 1
        k = cid(spec, cfg)
        if k in seen:
            continue
        seen.add(k)
        out.append({"id": k, "spec": spec, "cfg": cfg})
        t, s = fam_stats.get(fam, (0, 0))
        fam_stats[fam] = (t + 1, s)
        tri[fam] += 1
        weight[fam] = (1 + 3 * s) / (1 + tri[fam])
    return out
