/* Quantlab terminal - front end. Charts: TradingView Lightweight Charts v4 (Apache-2.0). */
"use strict";
const LW = LightweightCharts;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const api = async (p, opt) => { const r = await fetch(p, opt); const j = await r.json(); if (j && j.error) throw new Error(j.error); return j; };
const MAJORS = new Set(["BTCUSDT", "ETHUSDT", "BNBUSDT"]);

/* ---------------------------------------------------------------- formatting */
function decimals(p) { return p >= 1000 ? 2 : p >= 10 ? 3 : p >= 1 ? 4 : p >= 0.01 ? 5 : p >= 0.0001 ? 7 : 9; }
const fp = (p) => p == null || !isFinite(p) ? "–" : Number(p).toLocaleString("en-US", { minimumFractionDigits: decimals(Math.abs(p)), maximumFractionDigits: decimals(Math.abs(p)) });
// 2026-10-20 Michael: every time on the page in HIS time (this PC's clock), never UTC. lt() takes a UTC time
// (ISO / "YYYY-MM-DD HH:MM:SS" without zone / epoch ms) and returns local "YYYY-MM-DD HH:MM" (n = chars kept).
const lt = (s, n = 16) => { if (s == null || s === "") return "–"; let x = String(s).trim().replace(/ UTC$/, "");
  x = /^\d+$/.test(x) ? Number(x) : (/[zZ]$|[+-]\d\d:?\d\d$/.test(x) ? x : x.replace(" ", "T") + "Z");
  const d = new Date(x); if (isNaN(d)) return String(s).slice(0, n); const q = (v) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${q(d.getMonth() + 1)}-${q(d.getDate())} ${q(d.getHours())}:${q(d.getMinutes())}:${q(d.getSeconds())}`.slice(0, n); };
// the daily candle closes at 00:00 UTC; this is that moment on this PC's clock (follows summer / winter time)
const dayClose = () => { const d = new Date(); d.setUTCHours(0, 0, 0, 0); return d.toTimeString().slice(0, 5); };
const pct = (v, d = 2) => v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + v.toFixed(d) + "%";
/* signed: a negative used to fall through every >= test and print raw (CVD, taker delta) */
const big = (v) => { if (!isFinite(v)) return "–"; const a = Math.abs(v), sg = v < 0 ? "\u2212" : "";
  return sg + (a >= 1e9 ? (a / 1e9).toFixed(2) + "B" : a >= 1e6 ? (a / 1e6).toFixed(1) + "M" : a >= 1e3 ? (a / 1e3).toFixed(1) + "K" : a.toFixed(0)); };
const cls = (v) => v > 0 ? "up" : v < 0 ? "down" : "";

/* ---------------------------------------------------------------- indicators */
const IND = {
  ema(v, n) { const k = 2 / (n + 1), o = new Array(v.length).fill(null); let e = null;
    for (let i = 0; i < v.length; i++) { e = e == null ? v[i] : v[i] * k + e * (1 - k); if (i >= n - 1) o[i] = e; } return o; },
  sma(v, n) { const o = new Array(v.length).fill(null); let s = 0;
    for (let i = 0; i < v.length; i++) { s += v[i]; if (i >= n) s -= v[i - n]; if (i >= n - 1) o[i] = s / n; } return o; },
  bb(v, n = 20, k = 2) { const m = IND.sma(v, n), u = [], l = [];
    for (let i = 0; i < v.length; i++) { if (m[i] == null) { u.push(null); l.push(null); continue; }
      let s = 0; for (let j = i - n + 1; j <= i; j++) s += (v[j] - m[i]) ** 2; const sd = Math.sqrt(s / n);
      u.push(m[i] + k * sd); l.push(m[i] - k * sd); } return { m, u, l }; },
  rsi(v, n = 14) { const o = new Array(v.length).fill(null); let g = 0, l = 0;
    for (let i = 1; i < v.length; i++) { const d = v[i] - v[i - 1], up = Math.max(d, 0), dn = Math.max(-d, 0);
      if (i <= n) { g += up / n; l += dn / n; if (i === n) o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); }
      else { g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n; o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); } } return o; },
  macd(v) { const a = IND.ema(v, 12), b = IND.ema(v, 26), m = v.map((_, i) => a[i] != null && b[i] != null ? a[i] - b[i] : null);
    const start = m.findIndex((x) => x != null), sig = new Array(v.length).fill(null);
    if (start >= 0) { const e = IND.ema(m.slice(start), 9); e.forEach((x, i) => sig[start + i] = x); }
    return { m, s: sig, h: m.map((x, i) => x != null && sig[i] != null ? x - sig[i] : null) }; },
  atr(b, n = 14) { const o = new Array(b.length).fill(null); let a = null;
    for (let i = 1; i < b.length; i++) { const tr = Math.max(b[i].high - b[i].low, Math.abs(b[i].high - b[i - 1].close), Math.abs(b[i].low - b[i - 1].close));
      a = a == null ? tr : (a * (n - 1) + tr) / n; if (i >= n) o[i] = a; } return o; },
  vwap(b) { const o = []; let day = null, pv = 0, vv = 0;   /* resets every UTC day */
    for (const x of b) { const d = Math.floor(x.time / 86400); if (d !== day) { day = d; pv = 0; vv = 0; }
      const tp = (x.high + x.low + x.close) / 3; pv += tp * x.volume; vv += x.volume; o.push(vv ? pv / vv : null); } return o; },
  donchian(b, n = 20) { const u = [], l = [];
    for (let i = 0; i < b.length; i++) { if (i < n) { u.push(null); l.push(null); continue; }
      let h = -Infinity, lo = Infinity; for (let j = i - n; j < i; j++) { h = Math.max(h, b[j].high); lo = Math.min(lo, b[j].low); }
      u.push(h); l.push(lo); } return { u, l }; },
};

/* ---------------------------------------------------------------- chart theme */
function chartOpts(extra = {}) {
  return Object.assign({
    autoSize: true,
    layout: { background: { type: "solid", color: "transparent" }, textColor: css("--text-secondary"), fontFamily: "Inter, sans-serif", fontSize: 11 },
    grid: { vertLines: { color: css("--grid") }, horzLines: { color: css("--grid") } },
    rightPriceScale: { borderColor: css("--border") },
    timeScale: { borderColor: css("--border"), timeVisible: true, secondsVisible: false, rightOffset: 6 },
    crosshair: { mode: LW.CrosshairMode.Normal, vertLine: { color: css("--text-muted"), labelBackgroundColor: css("--surface-3") },
                 horzLine: { color: css("--text-muted"), labelBackgroundColor: css("--surface-3") } },
  }, extra);
}
const allCharts = [];
function mkChart(el, extra) { const c = LW.createChart(el, chartOpts(extra)); allCharts.push(c); return c; }

/* ================================================================ MARKETS */
const M = { sym: "BTCUSDT", tf: "1h", bars: [], fund: [], daily: [], ind: {}, ws: null, alertLines: [], log: false,
            on: { ema: true, bb: false, vwap: false, don: false, trend: true, vp: false }, signals: [], sigKey: "",
            sig: { tested: true, red: false, trend: true, ema: false, macd: false, whale: false },
            panes: { rsi: true, macd: true, fund: true, flow: true }, pos: null, posKey: "" };
let main, rsiC, macdC, fundC, flowC, S = {};

function buildMarketCharts() {
  main = mkChart($("#cMain"));
  rsiC = mkChart($("#cRsi"), { timeScale: { visible: false } });
  macdC = mkChart($("#cMacd"), { timeScale: { visible: false } });
  fundC = mkChart($("#cFund"), { timeScale: { visible: false } });
  flowC = mkChart($("#cFlow"), { timeScale: { visible: false }, leftPriceScale: { visible: true, borderColor: css("--border") } });
  const ln = (c, color, w = 2, extra = {}) => c.addLineSeries(Object.assign({ color, lineWidth: w, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, extra));
  S.candle = main.addCandlestickSeries({ upColor: css("--up"), downColor: css("--down"), borderVisible: false, wickUpColor: css("--up"), wickDownColor: css("--down") });
  S.vol = main.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false, priceLineVisible: false });
  main.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
  main.priceScale("right").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.2 } });
  S.ema20 = ln(main, css("--series-1"), 1); S.ema50 = ln(main, css("--series-2"), 1); S.ema200 = ln(main, css("--series-7"), 2);
  S.bbU = ln(main, css("--series-4"), 1); S.bbM = ln(main, css("--series-4"), 1, { lineStyle: LW.LineStyle.Dotted }); S.bbL = ln(main, css("--series-4"), 1);
  S.vwap = ln(main, css("--series-5"), 2);
  S.donU = ln(main, css("--series-3"), 1, { lineStyle: LW.LineStyle.Dashed }); S.donL = ln(main, css("--series-3"), 1, { lineStyle: LW.LineStyle.Dashed });
  /* the trend reference can sit far from price: draw it, but never let it stretch the price scale */
  S.trend = ln(main, css("--series-7"), 2, { lineStyle: LW.LineStyle.LargeDashed, lineType: LW.LineType.WithSteps, autoscaleInfoProvider: () => null });
  [rsiC, macdC, fundC].forEach((c) => c.applyOptions({ layout: { attributionLogo: false } }));
  S.rsi = ln(rsiC, css("--series-7"), 2, { lastValueVisible: true });
  S.rsi.createPriceLine({ price: 70, color: css("--text-muted"), lineStyle: LW.LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false });
  S.rsi.createPriceLine({ price: 30, color: css("--text-muted"), lineStyle: LW.LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false });
  S.macdH = macdC.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
  S.macd = ln(macdC, css("--series-1"), 2); S.macdS = ln(macdC, css("--series-2"), 1);
  S.fund = fundC.addHistogramSeries({ priceLineVisible: false, priceFormat: { type: "custom", formatter: (v) => v.toFixed(4) + "%" } });
  /* taker flow: every trade has an aggressor. volume - 2 x taker-buy is what the sellers hit, in quote USDT. */
  S.flow = flowC.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false,
    priceFormat: { type: "custom", formatter: (v) => big(v) } });
  S.cvd = ln(flowC, css("--series-7"), 2, { priceScaleId: "left", lastValueVisible: true,
    priceFormat: { type: "custom", formatter: (v) => big(v) } });

  /* keep the four panes on one time axis */
  const panes = [main, rsiC, macdC, fundC, flowC]; let syncing = false;
  panes.forEach((c) => c.timeScale().subscribeVisibleLogicalRangeChange((r) => {
    if (syncing || !r) return; syncing = true; panes.forEach((o) => o !== c && o.timeScale().setVisibleLogicalRange(r)); syncing = false; }));
  const anchor = new Map([[main, S.candle], [rsiC, S.rsi], [macdC, S.macd], [fundC, S.fund], [flowC, S.flow]]);
  const valAt = (o, i) => o === main ? M.bars[i]?.close : o === rsiC ? M.ind.rsi?.[i] : o === macdC ? M.ind.macd?.m[i]
    : o === flowC ? M.ind.delta?.[i] : M.ind.fund?.[i];
  main.timeScale().subscribeVisibleLogicalRangeChange(() => drawVP());
  main.subscribeClick((p) => {
    if (LV.tool && p.point) {                                   /* placing a trade by hand */
      const px = S.candle.coordinateToPrice(p.point.y);
      if (px == null) return;
      if (LV.tool === "entry") { LV.draft = { entry: px, at: p.time ?? null }; LV.tool = "stop"; toolBtn(); return; }
      const d = LV.draft || {}, long = px < d.entry;
      const set = { kind: "manual", name: "Trade tool", side: long ? "LONG" : "SHORT", entry: d.entry, stop: px,
                    target: d.entry + (d.entry - px) * 2, at: d.at, note: "placed by hand · target at 2R" };
      LV.tool = null; LV.draft = null; toolBtn(); lvAdd(set);
      return;
    }
    const s2 = hitAt(p.point);                                  /* clicked one of the on-chart labels */
    if (!s2) return;
    const i = LV.sets.findIndex((v) => v.entry === s2.entry && v.stop === s2.stop);
    if (i >= 0) { LV.pick = i; lvRender(); } else lvAdd(s2);
  });
  main.subscribeCrosshairMove((p) => {
    const el = $("#cMain"); if (!el) return;
    el.style.cursor = LV.tool ? "crosshair" : (hitAt(p.point) ? "pointer" : "");
  });
  panes.forEach((c) => c.subscribeCrosshairMove((p) => {
    const i = p.time ? M.bars.findIndex((b) => b.time === p.time) : -1;
    panes.forEach((o) => { if (o === c) return; const v = i >= 0 ? valAt(o, i) : null;
      if (v != null && isFinite(v)) { try { o.setCrosshairPosition(v, p.time, anchor.get(o)); } catch (e) {} } else o.clearCrosshairPosition(); });
    legend(i >= 0 ? i : M.bars.length - 1);
  }));
}

/* The trade lives on the chart: a shaded reward zone to the target, a risk zone to the stop, and a label on the
   candle that produced the signal. Every label is clickable - LV.hit keeps the boxes drawn on the last pass. */
function zoneRect(g, x0, x1, pa, pb, colour) {
  const ya = S.candle.priceToCoordinate(pa), yb = S.candle.priceToCoordinate(pb);
  if (ya == null || yb == null) return;
  g.fillStyle = colour;
  g.fillRect(x0, Math.min(ya, yb), Math.max(x1 - x0, 0), Math.abs(yb - ya));
}

function drawZones(g, right) {
  const v = LV.on && LV.sets[LV.pick];
  if (!v || v.entry == null) return;
  let x0 = 0;
  if (v.at != null) { const c = main.timeScale().timeToCoordinate(v.at); if (c != null) x0 = Math.max(0, c); }
  if (v.target != null) zoneRect(g, x0, right, v.entry, v.target, css("--up") + "18");
  if (v.stop != null) zoneRect(g, x0, right, v.entry, v.stop, css("--down") + "18");
}

function chip(g, x, y, text, bg, below) {
  g.font = "600 10px Inter, sans-serif";
  const pad = 5, w = g.measureText(text).width + pad * 2, h = 15;
  const bx = Math.round(x - w / 2), by = Math.round(below ? y + 8 : y - h - 8);
  g.fillStyle = bg;
  if (g.roundRect) { g.beginPath(); g.roundRect(bx, by, w, h, 3); g.fill(); } else g.fillRect(bx, by, w, h);
  g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(text, bx + w / 2, by + h / 2 + 0.5);
  g.beginPath(); g.moveTo(x, below ? by : by + h); g.lineTo(x, y); g.strokeStyle = bg; g.lineWidth = 1; g.stroke();
  return { x0: bx, y0: by, x1: bx + w, y1: by + h };
}

function drawLabels(g, right, h) {
  LV.hit = [];
  if (!LV.on || !M.bars.length) return;
  const ts = main.timeScale(), seen = new Map();
  const put = (time, price, text, colour, below, set) => {
    const x = ts.timeToCoordinate(time), y = S.candle.priceToCoordinate(price);
    if (x == null || y == null || x < 0 || x > right) return;
    const k = Math.round(x / 6);                       /* stack labels that land on the same spot */
    const lvl = seen.get(k) || 0; seen.set(k, lvl + 1);
    const r = chip(g, x, y + (below ? lvl * 18 : -lvl * 18), text, colour, below);
    if (set) LV.hit.push({ ...r, set });
  };
  for (const s of testedShown()) {
    const t = barAt(s.entry_time); if (t == null) continue;
    const long = s.direction === "LONG";
    put(t, long ? M.bars[M.bars.findIndex((b) => b.time === t)]?.low ?? s.entry : M.bars[M.bars.findIndex((b) => b.time === t)]?.high ?? s.entry,
        `${long ? "LONG" : "SHORT"} ${RES_ICON[s.result] || ""}`.trim(),
        s.badge === "RED" ? css("--neutral") : long ? css("--up") : css("--down"), long,
        { kind: "sig", name: `${s.condition}`, side: s.direction, entry: s.entry, stop: s.stop, target: s.target,
          at: t, note: `${s.badge} · ${s.result}${s.ret_pct != null ? " " + pct(s.ret_pct) : ""}` });
  }
  for (const v of LV.sets) {
    if (v.at == null || v.entry == null) continue;
    put(v.at, v.entry, v.side === "LONG" ? "LONG" : "SHORT", v.side === "LONG" ? css("--up") : css("--down"),
        v.side === "LONG", v);
  }
}

function hitAt(pt) {
  if (!pt) return null;
  for (let i = LV.hit.length - 1; i >= 0; i--) {
    const r = LV.hit[i];
    if (pt.x >= r.x0 && pt.x <= r.x1 && pt.y >= r.y0 && pt.y <= r.y1) return r.set;
  }
  return null;
}

/* Volume by price over whatever is on screen. Each bar's volume is spread across the price bins its range
   covers and split by its taker-buy share, so the green part is what was bought into the ask. The widest bin is
   the point of control - the price this market has agreed on most, and the level it tends to defend. */
function drawVP() {
  const cv = $("#vpCv"), host = $("#cMain");
  if (!cv || !host || !S.candle) return;
  const w = host.clientWidth, h = host.clientHeight, dpr = window.devicePixelRatio || 1;
  if (!w || !h) return;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); cv.style.width = w + "px"; cv.style.height = h + "px";
  }
  cv.style.left = host.offsetLeft + "px"; cv.style.top = host.offsetTop + "px"; cv.style.right = "auto"; cv.style.bottom = "auto";
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  let scale = 60;
  try { const pw = main.priceScale("right").width(); if (pw > 0) scale = pw; } catch (e) {}
  drawZones(g, w - scale);
  drawLabels(g, w - scale, h);
  if (!M.on.vp || M.bars.length < 2) return;
  const r = main.timeScale().getVisibleLogicalRange(); if (!r) return;
  const from = Math.max(0, Math.floor(r.from)), to = Math.min(M.bars.length - 1, Math.ceil(r.to));
  const vis = M.bars.slice(from, to + 1); if (vis.length < 2) return;
  let lo = Infinity, hi = -Infinity;
  for (const b of vis) { if (b.low < lo) lo = b.low; if (b.high > hi) hi = b.high; }
  if (!(hi > lo)) return;
  const N = 60, tot = new Float64Array(N), buy = new Float64Array(N);
  const bin = (px) => Math.min(N - 1, Math.max(0, Math.floor((px - lo) / (hi - lo) * N)));
  for (const b of vis) {
    const a = bin(b.low), z = bin(b.high), span = z - a + 1, v = (b.volume || 0) / span;
    const bs = b.volume > 0 ? Math.min(Math.max(b.taker_buy / b.volume, 0), 1) : 0.5;
    for (let k = a; k <= z; k++) { tot[k] += v; buy[k] += v * bs; }
  }
  let max = 0, poc = 0;
  for (let k = 0; k < N; k++) { if (tot[k] > max) { max = tot[k]; poc = k; } }
  if (!max) return;
  let scaleW = scale;
  const right = w - scaleW, maxW = Math.min(right * 0.2, 150);
  const price = (k) => lo + (k / N) * (hi - lo);
  for (let k = 0; k < N; k++) {
    if (!tot[k]) continue;
    const yTop = S.candle.priceToCoordinate(price(k + 1)), yBot = S.candle.priceToCoordinate(price(k));
    if (yTop == null || yBot == null) continue;
    const bh = Math.max(1, yBot - yTop - 1), bw = tot[k] / max * maxW, bwBuy = buy[k] / max * maxW;
    g.fillStyle = css("--down") + (k === poc ? "44" : "26");
    g.fillRect(right - bw, yTop, bw, bh);
    g.fillStyle = css("--up") + (k === poc ? "5c" : "3a");
    g.fillRect(right - bwBuy, yTop, bwBuy, bh);
  }
  const yP = S.candle.priceToCoordinate(price(poc + 0.5));
  if (yP != null) {
    g.strokeStyle = css("--series-4"); g.lineWidth = 1; g.setLineDash([4, 3]);
    g.beginPath(); g.moveTo(0, yP); g.lineTo(right, yP); g.stroke(); g.setLineDash([]);
    g.fillStyle = css("--series-4"); g.font = "10px Inter, sans-serif"; g.textAlign = "right";
    g.fillText("POC " + fp(price(poc + 0.5)), right - 4, yP - 3);
  }
}

function pt(vals) { return M.bars.map((b, i) => vals[i] == null ? { time: b.time } : { time: b.time, value: vals[i] }); }

function computeAll() {
  const c = M.bars.map((b) => b.close);
  const I = {};
  I.ema20 = IND.ema(c, 20); I.ema50 = IND.ema(c, 50); I.ema200 = IND.ema(c, 200);
  I.bb = IND.bb(c); I.vwap = IND.vwap(M.bars); I.don = IND.donchian(M.bars); I.rsi = IND.rsi(c); I.macd = IND.macd(c);
  I.atr = IND.atr(M.bars); I.volAvg = IND.sma(M.bars.map((b) => b.volume), 20);
  /* taker buy volume is the part of the bar's volume that bought into the ask; the rest sold into the bid. */
  I.buyShare = M.bars.map((b) => b.volume > 0 ? Math.min(Math.max(b.taker_buy / b.volume, 0), 1) : null);
  I.delta = M.bars.map((b, i) => I.buyShare[i] == null ? null : (2 * b.taker_buy - b.volume) * b.close);
  let run = 0; I.cvd = M.bars.map((b, i) => I.delta[i] == null ? run : (run += I.delta[i]));
  /* 20d trend reference = daily close 20 days before the bar's day (the level MajorsTrend compares against) */
  const dmap = new Map(M.daily.map((d) => [Math.floor(d.time / 86400), d.close]));
  I.trend = M.bars.map((b) => dmap.get(Math.floor(b.time / 86400) - 20) ?? null);
  /* funding settled at or before each bar */
  let j = -1; I.fund = M.bars.map((b) => { while (j + 1 < M.fund.length && M.fund[j + 1].time <= b.time + 1) j++; return j >= 0 ? M.fund[j].value : null; });
  M.ind = I;
}

function paintAll() {
  const I = M.ind, up = css("--up"), dn = css("--down");
  S.candle.setData(M.bars.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));
  S.vol.setData(M.bars.map((b) => ({ time: b.time, value: b.volume, color: (b.close >= b.open ? up : dn) + "55" })));
  const set = (s, v, on) => s.setData(on ? pt(v) : []);
  set(S.ema20, I.ema20, M.on.ema); set(S.ema50, I.ema50, M.on.ema); set(S.ema200, I.ema200, M.on.ema);
  set(S.bbU, I.bb.u, M.on.bb); set(S.bbM, I.bb.m, M.on.bb); set(S.bbL, I.bb.l, M.on.bb);
  set(S.vwap, I.vwap, M.on.vwap && M.tf !== "1d"); set(S.donU, I.don.u, M.on.don); set(S.donL, I.don.l, M.on.don);
  set(S.trend, I.trend, M.on.trend);
  S.rsi.setData(pt(I.rsi)); S.macd.setData(pt(I.macd.m)); S.macdS.setData(pt(I.macd.s));
  S.macdH.setData(M.bars.map((b, i) => I.macd.h[i] == null ? { time: b.time } : { time: b.time, value: I.macd.h[i], color: (I.macd.h[i] >= 0 ? up : dn) + "aa" }));
  S.fund.setData(M.bars.map((b, i) => I.fund[i] == null ? { time: b.time } : { time: b.time, value: I.fund[i], color: I.fund[i] >= 0 ? up : dn }));
  S.flow.setData(M.bars.map((b, i) => I.delta[i] == null ? { time: b.time }
    : { time: b.time, value: I.delta[i], color: (I.delta[i] >= 0 ? up : dn) + "cc" }));
  S.cvd.setData(pt(I.cvd));
  paintMarkers(); drawVP();
}

function paintLast() {           /* live tick: update only the last point of every series */
  const I = M.ind, i = M.bars.length - 1, b = M.bars[i], t = b.time, up = css("--up"), dn = css("--down");
  const u = (s, v, on = true) => { if (on && v != null) s.update({ time: t, value: v }); };
  S.candle.update({ time: t, open: b.open, high: b.high, low: b.low, close: b.close });
  S.vol.update({ time: t, value: b.volume, color: (b.close >= b.open ? up : dn) + "55" });
  u(S.ema20, I.ema20[i], M.on.ema); u(S.ema50, I.ema50[i], M.on.ema); u(S.ema200, I.ema200[i], M.on.ema);
  u(S.bbU, I.bb.u[i], M.on.bb); u(S.bbM, I.bb.m[i], M.on.bb); u(S.bbL, I.bb.l[i], M.on.bb);
  u(S.vwap, I.vwap[i], M.on.vwap && M.tf !== "1d"); u(S.donU, I.don.u[i], M.on.don); u(S.donL, I.don.l[i], M.on.don);
  u(S.trend, I.trend[i], M.on.trend); u(S.rsi, I.rsi[i]); u(S.macd, I.macd.m[i]); u(S.macdS, I.macd.s[i]);
  if (I.macd.h[i] != null) S.macdH.update({ time: t, value: I.macd.h[i], color: (I.macd.h[i] >= 0 ? up : dn) + "aa" });
  if (I.fund[i] != null) S.fund.update({ time: t, value: I.fund[i], color: I.fund[i] >= 0 ? up : dn });
}

function legend(i) {
  const b = M.bars[i]; if (!b) return; const I = M.ind, p = M.bars[i - 1];
  const ch = p ? (b.close / p.close - 1) * 100 : 0;
  const item = (color, label, v) => v == null ? "" : `<span><i style="background:${color}"></i>${label} <span class="mono">${fp(v)}</span></span>`;
  $("#legend").innerHTML = `<div class="l1 mono"><span><b>O</b>${fp(b.open)}</span><span><b>H</b>${fp(b.high)}</span><span><b>L</b>${fp(b.low)}</span>
    <span><b>C</b>${fp(b.close)}</span><span class="${cls(ch)}">${pct(ch)}</span><span><b>Vol</b>${big(b.qvol)}</span></div>
    <div class="ind">${M.on.ema ? item(css("--series-1"), "EMA20", I.ema20[i]) + item(css("--series-2"), "EMA50", I.ema50[i]) + item(css("--series-7"), "EMA200", I.ema200[i]) : ""}
    ${M.on.bb ? item(css("--series-4"), "BB↑", I.bb.u[i]) + item(css("--series-4"), "BB↓", I.bb.l[i]) : ""}
    ${M.on.vwap && M.tf !== "1d" ? item(css("--series-5"), "VWAP", I.vwap[i]) : ""}${M.on.trend ? item(css("--series-7"), "20d ref", I.trend[i]) : ""}</div>${sigLegend(b.time)}`;
  $("#lgRsi").textContent = I.rsi[i] != null ? I.rsi[i].toFixed(1) : "";
  $("#lgMacd").textContent = I.macd.h[i] != null ? `${I.macd.m[i].toPrecision(4)} / ${I.macd.s[i].toPrecision(4)} / ${I.macd.h[i].toPrecision(3)}` : "";
  $("#lgFund").textContent = I.fund[i] != null ? I.fund[i].toFixed(4) + "%" : "";
  $("#lgFlow").innerHTML = I.buyShare[i] == null ? "" :
    `<span class="${I.delta[i] >= 0 ? "up" : "down"}">${I.delta[i] >= 0 ? "buyers" : "sellers"} ${big(Math.abs(I.delta[i]))}</span>
     · ${(I.buyShare[i] * 100).toFixed(0)}% of the bar bought · CVD ${big(I.cvd[i])}`;
}

function readout() {
  const I = M.ind, i = M.bars.length - 1, b = M.bars[i]; if (!b) return;
  const r = I.rsi[i], h = I.macd.h[i], hp = I.macd.h[i - 1], e20 = I.ema20[i], e50 = I.ema50[i], e200 = I.ema200[i];
  const stack = e200 == null ? "–" : e20 > e50 && e50 > e200 ? `<span class="state bull">BULL STACK</span>` : e20 < e50 && e50 < e200 ? `<span class="state bear">BEAR STACK</span>` : `<span class="state flat">MIXED</span>`;
  const pb = I.bb.u[i] != null ? (b.close - I.bb.l[i]) / (I.bb.u[i] - I.bb.l[i]) : null;
  const tr = I.trend[i];
  const rows = [
    ["RSI 14", r == null ? "–" : `${r.toFixed(1)} ${r >= 70 ? '<span class="state bear">≥ 70</span>' : r <= 30 ? '<span class="state bull">≤ 30</span>' : ""}`],
    ["MACD histogram", h == null ? "–" : `<span class="${cls(h)}">${h > 0 ? "▲ positive" : "▼ negative"}</span>${hp != null && Math.sign(h) !== Math.sign(hp) ? " · just crossed" : ""}`],
    ["EMA 20/50/200", stack],
    ["Price vs EMA200", e200 == null ? "–" : `<span class="${cls(b.close - e200)}">${pct((b.close / e200 - 1) * 100)}</span>`],
    ["Bollinger %B", pb == null ? "–" : (pb * 100).toFixed(0) + "%"],
    ["ATR 14 (% of price)", I.atr[i] == null ? "–" : (I.atr[i] / b.close * 100).toFixed(2) + "%"],
    ["Volume vs 20-bar avg", I.volAvg[i] ? (b.volume / I.volAvg[i]).toFixed(2) + "×" : "–"],
    ["20d trend (MajorsTrend rule)", tr == null ? "–" : b.close > tr ? `<span class="state bull">UP</span> ${pct((b.close / tr - 1) * 100)}` : `<span class="state bear">DOWN</span> ${pct((b.close / tr - 1) * 100)}`],
  ];
  $("#readout").innerHTML = rows.map(([k, v]) => `<span>${k}</span><span>${v}</span>`).join("");
}

async function marketPanel() {
  const t = TICK.map.get(M.sym); let oiTxt = "–";
  try { const o = await api(`/api/oi?symbol=${M.sym}`); oiTxt = big(o.now * (t ? t.mark : 0)) + " USDT"; } catch (e) {}
  if (M.posKey !== M.sym) {                       /* long/short positioning: big accounts vs everyone else */
    M.posKey = M.sym; M.pos = null;
    api(`/api/positioning?symbol=${M.sym}`).then((d) => { if (M.posKey === M.sym) { M.pos = d; marketPanel(); } })
      .catch(() => {});                           /* older server build has no such route - just leave the rows out */
  }
  if (!t) return;
  const left = Math.max(0, t.next_funding - Date.now()), hh = Math.floor(left / 3.6e6), mm = Math.floor(left % 3.6e6 / 6e4);
  $("#mkt").innerHTML = [["Last", fp(t.last)], ["Mark", fp(t.mark)], ["24h change", `<span class="${cls(t.chg)}">${pct(t.chg)}</span>`],
    ["24h high / low", `${fp(t.high)} / ${fp(t.low)}`], ["24h volume", big(t.qv) + " USDT"], ["Open interest", oiTxt],
    ["Funding (current)", `<span class="${cls(t.funding)}">${(t.funding * 100).toFixed(4)}%</span>`], ["Next funding in", `${hh}h ${String(mm).padStart(2, "0")}m`],
    ...posRows()]
    .map(([k, v]) => `<span>${k}</span><span>${v}</span>`).join("");
}

function posRows() {
  const P = M.pos; if (!P) return [];
  const side = (v) => v == null ? "–" : `<span class="${v >= 1 ? "up" : "down"}">${v.toFixed(2)}:1 ${v >= 1 ? "long" : "short"}</span>`;
  const last = (a) => a && a.length ? a[a.length - 1].value : null;
  const chg = (a) => { if (!a || a.length < 25) return ""; const d = a[a.length - 1].value - a[a.length - 25].value;
    return ` <span class="small muted" title="change over 24 hours">${d >= 0 ? "+" : "\u2212"}${Math.abs(d).toFixed(2)}</span>`; };
  const rows = [];
  if (last(P.top) != null) rows.push(["Big accounts L/S", side(last(P.top)) + chg(P.top)]);
  if (last(P.accounts) != null) rows.push(["All accounts L/S", side(last(P.accounts)) + chg(P.accounts)]);
  if (last(P.taker) != null) rows.push(["Taker buy/sell 1h", side(last(P.taker))]);
  return rows;
}

function wsConnect() {
  if (M.ws) { M.ws.onclose = null; M.ws.close(); }
  const ws = new WebSocket(`wss://fstream.binance.com/ws/${M.sym.toLowerCase()}@kline_${M.tf}`);
  M.ws = ws; let pending = false;
  ws.onopen = () => conn(true, "live");
  ws.onclose = () => { conn(false, "reconnecting"); setTimeout(() => M.ws === ws && wsConnect(), 3000); };
  ws.onmessage = (ev) => {
    const k = JSON.parse(ev.data).k; if (!k) return;
    const bar = { time: Math.floor(k.t / 1000), open: +k.o, high: +k.h, low: +k.l, close: +k.c, volume: +k.v, qvol: +k.q, taker_buy: +k.V };
    const last = M.bars[M.bars.length - 1];
    if (last && last.time === bar.time) M.bars[M.bars.length - 1] = bar; else if (!last || bar.time > last.time) M.bars.push(bar); else return;
    if (pending) return; pending = true;
    requestAnimationFrame(() => { pending = false; computeAll(); paintLast(); legend(M.bars.length - 1); readout(); });
  };
}

async function loadMarket() {
  $("#symName").textContent = M.sym;
  try {
    const [bars, fund, daily] = await Promise.all([api(`/api/klines?symbol=${M.sym}&interval=${M.tf}&limit=1000`),
      api(`/api/funding?symbol=${M.sym}`), api(`/api/klines?symbol=${M.sym}&interval=1d&limit=1000`)]);
    M.bars = bars; M.fund = fund; M.daily = daily;
  } catch (e) { conn(false, "data error"); return; }
  const d = decimals(M.bars.at(-1).close), fmt = { type: "price", precision: d, minMove: 1 / 10 ** d };
  [S.candle, S.ema20, S.ema50, S.ema200, S.bbU, S.bbM, S.bbL, S.vwap, S.donU, S.donL, S.trend].forEach((s) => s.applyOptions({ priceFormat: fmt }));
  M.alertLines.forEach((l) => S.candle.removePriceLine(l)); M.alertLines = [];
  computeAll(); paintAll();
  loadSignals();
  const n = M.bars.length; main.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 180), to: n + 6 });
  legend(n - 1); readout(); marketPanel(); coinAlerts(); lvRender(); barClock(); wsConnect();
  $$(".wrow").forEach((r) => r.classList.toggle("sel", r.dataset.s === M.sym));
}

function selectSymbol(sym, tf) { M.sym = sym; if (tf) { M.tf = tf; $$("#tfSeg button").forEach((b) => b.classList.toggle("on", b.dataset.tf === tf)); } loadMarket(); }

/* ---------------------------------------------------------------- long / short signals */
const RES_ICON = { target: "✓", stop: "✕", time: "⏱", open: "…" };
const BADGE_ICON = { GREEN: "🟢", YELLOW: "🟡", ORANGE: "🟠", RED: "🔴" };
function barAt(t) {              /* time of the last bar that starts at or before t (markers must sit on a bar) */
  const b = M.bars; if (!b.length || t < b[0].time) return null;
  let lo = 0, hi = b.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (b[m].time <= t) lo = m; else hi = m - 1; }
  return b[lo].time;
}
async function loadSignals() {
  const key = M.sym; M.sigKey = key; $("#sigSummary").textContent = "Loading…"; $("#sigList").innerHTML = "";
  try { const r = await api(`/api/signals?symbol=${M.sym}`); if (M.sigKey !== key) return; M.signals = r.signals; }
  catch (e) { M.signals = []; $("#sigSummary").textContent = "Signals unavailable: " + e.message; return; }
  paintMarkers(); sigPanel(); legend(M.bars.length - 1);
  if (M.pendingJump) { const s = M.pendingJump; M.pendingJump = null; if (barAt(s.entry_time) != null) jumpTo(s); }
}
const testedShown = () => M.signals.filter((s) => M.sig.tested && (s.badge !== "RED" || M.sig.red));
function trendFlips() {           /* MajorsTrend rule: long while close / close 20 days earlier > 1, decided on the daily close */
  const d = M.daily, out = []; let prev = null;
  for (let k = 20; k < d.length - 1; k++) {            /* the last daily candle is still open: skip it */
    const st = d[k].close / d[k - 20].close - 1 > 0;
    if (prev !== null && st !== prev) out.push({ time: d[k].time + 86400, long: st });
    prev = st;
  }
  return out;
}
function crosses(a, b) {
  const out = [];
  for (let i = 1; i < M.bars.length; i++) {
    if ([a[i], b[i], a[i - 1], b[i - 1]].some((v) => v == null)) continue;
    if (a[i - 1] <= b[i - 1] && a[i] > b[i]) out.push({ i, long: true });
    else if (a[i - 1] >= b[i - 1] && a[i] < b[i]) out.push({ i, long: false });
  }
  return out;
}
function paintMarkers() {
  if (!S.candle || !M.bars.length) return;
  const up = css("--up"), dn = css("--down"), neu = css("--neutral"), mk = [];
  for (const s of testedShown()) {
    const t = barAt(s.entry_time); if (t == null) continue; const L = s.direction === "LONG";
    mk.push({ time: t, position: L ? "belowBar" : "aboveBar", shape: L ? "arrowUp" : "arrowDown",
      color: s.badge === "RED" ? neu : L ? up : dn, text: `${L ? "LONG" : "SHORT"} ${RES_ICON[s.result]}` });
  }
  if (M.sig.trend) for (const f of trendFlips()) {
    const t = barAt(f.time); if (t == null) continue;
    mk.push({ time: t, position: f.long ? "belowBar" : "aboveBar", shape: f.long ? "arrowUp" : "square",
      color: css("--series-7"), text: f.long ? "TREND LONG" : "TREND EXIT" });
  }
  if (M.sig.whale) M.bars.forEach((b, i) => {
    const avg = M.ind.volAvg[i]; if (!avg || b.volume < 3 * avg) return;
    const buy = M.ind.buyShare[i];
    mk.push({ time: b.time, position: "aboveBar", shape: "circle", color: css("--series-4"),
      text: `${(b.volume / avg).toFixed(1)}× vol${buy == null ? "" : ` · ${(buy * 100).toFixed(0)}% bought`}` });
  });
  if (M.sig.ema) for (const c of crosses(M.ind.ema20, M.ind.ema50))
    mk.push({ time: M.bars[c.i].time, position: c.long ? "belowBar" : "aboveBar", shape: "circle", color: css("--series-1"), text: c.long ? "EMA L" : "EMA S" });
  if (M.sig.macd) for (const c of crosses(M.ind.macd.m, M.ind.macd.s))
    mk.push({ time: M.bars[c.i].time, position: c.long ? "belowBar" : "aboveBar", shape: "circle", color: css("--series-2"), text: c.long ? "MACD L" : "MACD S" });
  mk.sort((a, b) => a.time - b.time);
  S.candle.setMarkers(mk);
}
function sigLegend(t) {
  const parts = testedShown().filter((s) => barAt(s.entry_time) === t).map((s) =>
    `<span class="${s.direction === "LONG" ? "up" : "down"}">${s.direction === "LONG" ? "▲" : "▼"} ${s.direction}</span> ${s.condition} ${BADGE_ICON[s.badge]}`
    + ` · entry ${fp(s.entry)} · target ${fp(s.target)} · stop ${fp(s.stop)} · `
    + (s.result === "open" ? "still open" : `${s.result} ${RES_ICON[s.result]} ${pct(s.ret_pct)}`));
  if (M.sig.trend) trendFlips().filter((f) => barAt(f.time) === t).forEach((f) => parts.push(
    `<span style="color:var(--series-7)">${f.long ? "▲ TREND LONG" : "■ TREND EXIT"}</span> 20-day return turned ${f.long ? "positive" : "≤ 0"} on the previous daily close`));
  return parts.length ? `<div class="sig">${parts.join("<br>")}</div>` : "";
}
function sigPanel() {
  const list = testedShown(), done = list.filter((s) => s.result !== "open");
  if (!M.sig.tested) { $("#sigSummary").textContent = "Tested-rule markers are switched off (Indicators menu)."; $("#sigList").innerHTML = ""; return; }
  if (!list.length) {
    $("#sigSummary").innerHTML = `No ${M.sig.red ? "" : "🟡🟠 "}signals on this coin in the window.` + (M.sig.red ? "" : " Turn on 🔴 rules in the Indicators menu to see the failed ones.");
    $("#sigList").innerHTML = ""; return;
  }
  const n = (r) => done.filter((s) => s.result === r).length;
  const avg = done.length ? done.reduce((a, s) => a + s.ret_pct, 0) / done.length : null;
  $("#sigSummary").innerHTML = `${list.length} signals · ${n("target")} target ✓ · ${n("stop")} stop ✕ · ${n("time")} time ⏱ · ${list.length - done.length} open<br>`
    + `Avg closed trade <b class="mono ${cls(avg)}">${pct(avg)}</b> after costs`
    + (done.length < 30 ? ` · <span class="warn">only ${done.length} closed: too few to judge this coin</span>` : "");
  $("#sigList").innerHTML = list.slice(-12).reverse().map((s) => `<div class="sig-row" data-t="${s.entry_time}">
    <span class="d">${lt(s.entry_time * 1000).slice(5, 13)}h</span>
    <span class="${s.direction === "LONG" ? "up" : "down"}">${s.direction === "LONG" ? "▲" : "▼"}</span>
    <span class="c">${BADGE_ICON[s.badge]} ${s.condition}</span>
    <span class="r ${cls(s.ret_pct)}">${RES_ICON[s.result]} ${s.result === "open" ? "open" : pct(s.ret_pct, 1)}</span></div>`).join("");
  $$("#sigList .sig-row").forEach((r) => r.onclick = () => {
    const s = list.find((x) => x.entry_time === +r.dataset.t); if (!s) return;
    if (barAt(s.entry_time) == null) {          /* older than the loaded candles: 4h holds ~166 days */
      const order = ["15m", "1h", "4h", "1d"], next = order[Math.min(order.indexOf(M.tf) + 1, 3)];
      if (next !== M.tf) { M.pendingJump = s; selectSymbol(M.sym, next); }
      return;
    }
    jumpTo(s);
  });
}
function jumpTo(s) {
  drawAlert({ ref_price: s.entry, target: s.target, stop: s.stop });
  const t = barAt(s.entry_time), i = M.bars.findIndex((b) => b.time === t);
  if (i >= 0) { main.timeScale().setVisibleLogicalRange({ from: i - 90, to: i + 60 }); legend(i); }
}

/* ---------------------------------------------------------------- watchlist */
const TICK = { rows: [], map: new Map(), sort: "qv", q: "" };
async function loadTickers() {
  try { const rows = await api("/api/tickers"); const prev = TICK.map; TICK.rows = rows.slice(0, 250);
    TICK.map = new Map(rows.map((r) => [r.symbol, r])); renderWatch(prev); conn(true); if ($("#mkt").innerHTML === "" ) marketPanel(); }
  catch (e) { conn(false, "no data"); }
}
function renderWatch(prev) {
  const alerted = new Set((SCAN.data?.alerts || []).filter((a) => a.badge !== "RED").map((a) => a.coin + "USDT"));
  let rows = TICK.rows.filter((r) => r.symbol.includes(TICK.q));
  const key = TICK.sort; rows = [...rows].sort((a, b) => key === "qv" ? b.qv - a.qv : key === "chg" ? b.chg - a.chg : b.funding - a.funding);
  $("#watchList").innerHTML = rows.map((r) => {
    const p = prev && prev.get(r.symbol), fl = p && p.last !== r.last ? (r.last > p.last ? "flash-up" : "flash-down") : "";
    const extra = key === "funding" ? `${(r.funding * 100).toFixed(3)}` : pct(r.chg);
    return `<div class="wrow ${r.symbol === M.sym ? "sel" : ""}" data-s="${r.symbol}"><span class="s">${r.symbol.replace(/USDT$/, "")}${MAJORS.has(r.symbol) ? '<span class="badge">MT</span>' : ""}${alerted.has(r.symbol) ? '<span class="badge">⚑</span>' : ""}</span>
      <span class="mono ${fl}">${fp(r.last)}</span><span class="mono ${cls(key === "funding" ? r.funding : r.chg)}">${extra}</span></div>`; }).join("");
}

/* ================================================================ STRATEGIES */
let stratBuilt = false, eqChart, eqLogOn = true;
// V4 complacency short: forward test card (paper only, hourly task "Quantlab V4 Forward")
async function loadV4() {
  const d = await api("/api/v4");
  const el = $("#v4Card");
  if (d.missing) { el.innerHTML = `<div class="empty">No forward-test state yet (task "Quantlab V4 Forward" writes it hourly).</div>`; return; }
  const coins = Object.entries(d.latest_close || {}).map(([c, s]) => {
    const zOk = s.z <= -1.5, rOk = s.r10_pct < 0;
    return `<section class="card mcard"><div class="row1"><span class="coin">${c}</span>
      <span class="state ${s.signal ? "bear" : "flat"}">${s.signal ? "SHORT SIGNAL" : "NO SIGNAL"}</span></div>
      <div class="kv"><span>Fear gauge (DVOL)</span><span>${s.dvol.toFixed(1)}</span>
      <span>DVOL vs 90 days (needs ≤ −1.5)</span><span class="${zOk ? "up" : ""}">${s.z > 0 ? "+" : ""}${s.z.toFixed(2)} ${zOk ? "✓" : "✕"}</span>
      <span>10-day return (needs &lt; 0)</span><span class="${rOk ? "up" : ""}">${pct(s.r10_pct, 1)} ${rOk ? "✓" : "✕"}</span>
      <span>Daily close</span><span>${s.day}</span></div></section>`;
  }).join("");
  const n = d.closed_trades || 0;
  const kpis = [["Closed trades", n, "verdict at 12 or 2027-10-14"], ["Avg per trade", n ? pct(d.avg_pct) : "–", "research: +2.19%"],
    ["Profit factor", d.pf != null ? d.pf.toFixed(2) : "–", "needs ≥ 1.2"], ["300 USDT →", d.account.toFixed(2), `max drop ${d.max_drop_pct}%`],
    ["Open now", (d.open || []).length, "max 2 (BTC, ETH)"]]
    .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("");
  const rows = [...(d.open || []).map((t) => ({ ...t, res: `open · ${pct(t.upnl_pct)}`, c: cls(t.upnl_pct) })),
    ...(d.trades || []).slice().reverse().map((t) => ({ ...t, res: `${pct(t.ret_pct)} · ${t.why}`, c: cls(t.ret_pct) }))];
  const table = rows.length ? `<div class="table-wrap"><table><thead><tr><th>Coin</th><th>Entry</th><th>Entry</th><th>Stop</th><th>DVOL z</th><th>Result</th></tr></thead><tbody>
    ${rows.map((t) => `<tr><td>${t.coin}</td><td>${lt(t.t_in)}</td><td>${fp(t.entry)}</td><td>${fp(t.stop)}</td><td>${t.z.toFixed(2)}</td><td class="${t.c}">${t.res}</td></tr>`).join("")}
    </tbody></table></div>` : `<p class="muted small">No trades yet. It fires about 16 times a year, mostly in calm falling markets.</p>`;
  const sig = Object.entries(d.latest_close || {}).map(([c, s]) => `${c} ${s.signal ? '<b class="down">SHORT</b>' : "<b>no signal</b>"}`).join(" · ");
  $("#v4Sum").innerHTML = `<span class="pick-key">${sig}</span><span class="pick-key k2"><small>trades</small> <b>${n}</b> <small>open</small> <b>${(d.open || []).length}</b></span>
    <span class="pick-key k2"><small>300 →</small> <b>${d.account.toFixed(2)}</b></span>`;
  el.innerHTML = `<div class="card-head"><div>
      <p class="muted small">Options traders calm (DVOL low vs its 90 days) while the coin fell over 10 days → short BTC / ETH for 7 days, stop 3× the normal daily move, 1×. Started ${String(d.forward_start).slice(0, 10)}.</p></div>
      <div class="muted small">updated ${lt(d.updated)}</div></div>
    <div class="grid2">${coins}</div>
    <div class="kpis v4kpis">${kpis}</div>
    ${table}`;
}

// Crash-day forward log, Bear-Wild (paper only, hourly task; rules C:\quantlab\FORWARD_2026-10-17_crashday.md)
async function loadCrash() {
  const d = await api("/api/crashday");
  const el = $("#crashCard");
  if (d.missing) { el.innerHTML = `<div class="empty">No state yet (task "Quantlab Crashday Forward" writes it hourly).</div>`; return; }
  const s = d.summary || {}, lc = d.latest_close || {}, closed = s.events_closed || 0;
  const bw = lc.cell === "Bear-Wild";
  const today = `<section class="card mcard"><div class="row1"><span class="coin">BTC · ${lc.day || "–"}</span>
      <span class="state ${lc.crash ? "bear" : "flat"}">${lc.crash ? (bw ? "CRASH DAY · EVENT" : "CRASH DAY · context") : "NO CRASH"}</span></div>
      <div class="kv"><span>Daily move</span><span class="${cls(lc.btc_ret_pct)}">${pct(lc.btc_ret_pct)}</span>
      <span>Crash line (2× normal move, at least −4%)</span><span>${pct(lc.crash_line_pct)} ${lc.crash ? "✓" : "✕"}</span>
      <span>Market at the close (needs Bear-Wild)</span><span class="${bw ? "down" : ""}">${lc.cell || "–"} ${bw ? "✓" : "✕"}</span></div></section>`;
  const setups = [["L", "Bounce long", "long BTC + ETH, 72 h, stop 3× daily move"], ["S", "Continuation short", "short BTC + ETH, 72 h, stop 3× daily move"],
    ["F", "Flush setup (F1)", "crash-bounce longs on the top-200 coins, 24 h"]];
  const rp = (d.replay || {}).summary || {};
  const cards = setups.map(([k, name, what]) => { const j = s[k] || {}, h = rp[k] || {};
    const verdictReady = /^VERDICT/.test(s.stage || "");
    const tag = !j.events ? "WAITING" : verdictReady ? (j.would_pass ? "🟡 PASS" : "🔴 FAIL") : (j.would_pass ? "on track" : "below bar");
    return `<section class="card mcard"><div class="row1"><span class="coin">${k} · ${name}</span>
      <span class="state ${j.would_pass ? "bull" : "flat"}">${tag}</span></div>
      <div class="kv"><span>What</span><span>${what}</span>
      <span>Events · avg per event</span><span class="${cls(j.avg_pct)}">${j.events || 0} · ${pct(j.avg_pct)}</span>
      <span>PF over events (needs ≥ 1.3)</span><span>${j.pf != null ? j.pf.toFixed(2) : "–"}</span>
      <span>Events positive (needs ≥ 60%)</span><span>${j.pos_share != null ? (j.pos_share * 100).toFixed(0) + "%" : "–"}</span>
      ${k === "F" ? `<span>Flush trades (needs ≥ 30)</span><span>${s.flush_trades || 0}</span>` : ""}
      <span class="muted">History 2021-26 (reference)</span><span class="muted">${h.events ? `${h.events} ev · ${pct(h.avg_pct)} · PF ${h.pf != null ? h.pf.toFixed(2) : "–"}` : "not replayable"}</span></div></section>`; }).join("");
  const kpis = [["Events", `${closed} / 10`, "verdict at 10 or 2028-10-17"], ["Look at", "5 events", "numbers only, no verdict"],
    ["Stage", (s.stage || "–").replace(/\s*\(.*\)/, ""), `started ${d.forward_start}`], ["If nothing passes", "Cash", "Bear-Wild = no trade on crash days"]]
    .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("");
  const days = (d.days || []).slice().reverse();
  const legRes = (r, k) => r[k] != null ? `<td class="${cls(r[k])}">${pct(r[k])}</td>` : `<td class="muted">${r.role === "event" ? "open" : "–"}</td>`;
  const table = days.length ? `<div class="table-wrap"><table><thead><tr><th>Crash day</th><th>BTC move</th><th>Market</th><th>Counts as</th><th>L long</th><th>S short</th><th>F flush</th></tr></thead><tbody>
    ${days.map((r) => `<tr><td>${r.day}</td><td class="down">${pct(r.btc_ret_pct)}</td><td>${r.cell || "–"}</td>
      <td>${r.role === "event" ? "<b>event</b>" : r.role === "cluster" ? "same event" : "context only"}</td>
      ${legRes(r, "L")}${legRes(r, "S")}<td class="${cls(r.F)}">${r.role !== "event" ? "–" : r.flush == null ? "waiting" : r.flush.trades.length ? `${pct(r.F)} <span class="muted small">(${r.flush.trades.length})</span>` : "no trades"}</td></tr>`).join("")}
    </tbody></table></div>` : `<p class="muted small">No crash day yet. BTC needs a daily drop of 2× its normal move and at least 4%; in a Bear-Wild market that happens about 4–5 times a year.</p>`;
  $("#crashSum").innerHTML = `<span class="pick-key">${lc.crash ? '<b class="down">CRASH DAY</b>' : "<b>no crash</b>"} · ${lc.cell || ""}</span>
    <span class="pick-key k2"><small>events</small> <b>${closed}/10</b></span>`;
  el.innerHTML = `<div class="card-head"><div>
      <p class="muted small">Fills the empty Bear-Wild cell. On every crash day in a Bear-Wild market it measures three answers on new data only: buy the bounce, short the continuation, or the flush setup. If none passes, the answer is cash. Paper only, nothing is ordered.</p></div>
      <div class="muted small">updated ${lt(d.updated)}</div></div>
    <div class="grid2">${today}</div>
    <div class="kpis v4kpis">${kpis}</div>
    <div class="grid3">${cards}</div>
    ${table}`;
}

async function loadStrategies() {
  loadV4().catch((e) => $("#v4Card").innerHTML = `<div class="empty">V4 card could not load: ${e.message}</div>`);
  loadCrash().catch((e) => $("#crashCard").innerHTML = `<div class="empty">Crash-day card could not load: ${e.message}</div>`);
  const [mj, eq] = await Promise.all([api("/api/majors"), api("/api/majors_equity")]);
  $("#majorsAsOf").textContent = "Decided on the daily close of " + new Date(mj[0].decided * 1000).toISOString().slice(0, 10) + " (closes " + dayClose() + " your time) · orders at the next open";
  const tot = mj.reduce((s, m) => s + m.weight, 0);
  $("#majorsCards").innerHTML = mj.map((m) => `<section class="card mcard"><div class="row1"><span class="coin">${m.symbol.replace("USDT", "")}</span>
      <span class="state ${m.state === "LONG" ? "bull" : "flat"}">${m.state}</span></div>
      <div class="big">${fp(m.close)}</div>
      <div class="kv"><span>20-day return</span><span class="${cls(m.ret20)}">${pct(m.ret20)}</span>
      <span>30-day volatility (yearly)</span><span>${m.vol30.toFixed(0)}%</span>
      <span>Target weight</span><span>${m.weight.toFixed(1)}% of equity</span>
      <span>Flips if a close is ${m.state === "LONG" ? "below" : "above"}</span><span>${fp(m.flip_level)}</span></div>
      <div class="chart spark" id="spark-${m.symbol}"></div></section>`).join("");
  mj.forEach((m) => {
    const c = mkChart($(`#spark-${m.symbol}`), { handleScroll: false, handleScale: false, timeScale: { visible: false }, rightPriceScale: { visible: false },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } }, crosshair: { vertLine: { visible: false }, horzLine: { visible: false } } });
    const s = c.addAreaSeries({ lineColor: css("--series-1"), topColor: css("--series-1") + "40", bottomColor: css("--series-1") + "00", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    c.applyOptions({ layout: { attributionLogo: false } });
    s.setData(m.history.slice(-60)); s.createPriceLine({ price: m.flip_level, color: css("--text-muted"), lineStyle: LW.LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false });
    c.timeScale().fitContent();
  });
  const k = eq.metrics;
  $("#eqKpis").innerHTML = [["300 USDT →", fp(k.final).replace(/\.\d+$/, ""), `${eq.start} → ${eq.end}`], ["CAGR", pct(k.cagr * 100, 1), "per year"],
    ["Max drawdown", "−" + (k.max_dd * 100).toFixed(0) + "%", "peak to trough"], ["Sharpe", k.sharpe.toFixed(2), "daily, annualised"],
    ["Profit factor", (k.pf || 0).toFixed(2), `${k.trades} trades`], ["Exposure now", tot.toFixed(0) + "%", "of equity in the market"]]
    .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("");
  $("#majorsSum").innerHTML = `<span class="pick-key">${mj.map((m) => `${m.symbol.replace("USDT", "")} <b class="${m.state === "LONG" ? "up" : ""}">${m.state}</b>`).join(" · ")}</span>
    <span class="pick-key k2"><small>backtest 300 →</small> <b>${fp(k.final).replace(/\.\d+$/, "")}</b></span>
    <span class="pick-key k2"><small>exposure</small> <b>${tot.toFixed(0)}%</b></span>`;

  eqChart = mkChart($("#cEquity"), { rightPriceScale: { mode: LW.PriceScaleMode.Logarithmic, borderColor: css("--border") }, timeScale: { timeVisible: false, borderColor: css("--border"), minBarSpacing: 0.05 } });
  const toPts = (a) => a.map(([t, v]) => ({ time: t, value: v }));
  const sHold = eqChart.addLineSeries({ color: css("--neutral"), lineWidth: 1, priceLineVisible: false, title: "BTC hold" });
  const sEq = eqChart.addLineSeries({ color: css("--series-1"), lineWidth: 2, priceLineVisible: false, title: "MajorsTrend" });
  sHold.setData(toPts(eq.btc_hold)); sEq.setData(toPts(eq.equity)); eqChart.timeScale().fitContent();
  const dd = mkChart($("#cDD"), { timeScale: { timeVisible: false, borderColor: css("--border"), minBarSpacing: 0.05 } });
  dd.applyOptions({ layout: { attributionLogo: false } });
  const sDD = dd.addAreaSeries({ lineColor: css("--down"), topColor: css("--down") + "10", bottomColor: css("--down") + "55", lineWidth: 1, invertFilledArea: true,
    priceLineVisible: false, priceFormat: { type: "custom", formatter: (v) => v.toFixed(0) + "%" } });
  sDD.setData(eq.drawdown.map(([t, v]) => ({ time: t, value: v * 100 }))); dd.timeScale().fitContent();
  let sy = false; [[eqChart, dd], [dd, eqChart]].forEach(([a, b]) => a.timeScale().subscribeVisibleLogicalRangeChange((r) => { if (sy || !r) return; sy = true; b.timeScale().setVisibleLogicalRange(r); sy = false; }));
  yearBars(eq.years);
  const xc = mkChart($("#cExpo"), { timeScale: { timeVisible: false, borderColor: css("--border"), minBarSpacing: 0.05 } });
  xc.applyOptions({ layout: { attributionLogo: false } });
  const xs = xc.addAreaSeries({ lineColor: css("--series-1"), topColor: css("--series-1") + "50", bottomColor: css("--series-1") + "05", lineWidth: 1, priceLineVisible: false,
    priceFormat: { type: "custom", formatter: (v) => v.toFixed(0) + "%" } });
  xs.setData(eq.exposure.map(([t, v]) => ({ time: t, value: v * 100 }))); xc.timeScale().fitContent();
}

/* yearly returns: labelled SVG bars (10 bars read better with values on them than with an axis) */
function yearBars(years) {
  const el = $("#cYears"), e = Object.entries(years), W = el.clientWidth || 600, H = 220, T = 22, B = 44;
  const mx = Math.max(...e.map(([, v]) => Math.abs(v)), 1), hasNeg = e.some(([, v]) => v < 0);
  const zero = hasNeg ? T + (H - T - B) * (mx / (mx + Math.max(...e.map(([, v]) => -v), 0))) : H - B;
  const scale = (zero - T) / mx, bw = (W - 20) / e.length, gap = Math.max(4, bw * 0.22);
  let g = `<line x1="0" x2="${W}" y1="${zero}" y2="${zero}" stroke="var(--border)"/>`;
  e.forEach(([y, v], i) => { const x = 10 + i * bw + gap / 2, w = bw - gap, h = Math.abs(v) * scale, top = v >= 0 ? zero - h : zero;
    g += `<rect x="${x}" y="${top}" width="${w}" height="${Math.max(h, 1)}" rx="3" fill="${v >= 0 ? "var(--up)" : "var(--down)"}"><title>${y}: ${pct(v, 1)}</title></rect>
      <text x="${x + w / 2}" y="${v >= 0 ? top - 6 : top + h + 14}" text-anchor="middle" class="bar-v">${(v > 0 ? "+" : "") + v.toFixed(0)}%</text>
      <text x="${x + w / 2}" y="${H - 6}" text-anchor="middle" class="bar-y">${y}</text>`; });
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">${g}</svg>`;
}

/* ================================================================ RESEARCH */
const RES = { rows: [], sort: "at", dir: -1, stage: "", q: "" };
const isPass = (v) => !/^\s*(FAIL|KILL)/i.test(v || "") && /\bPASS\b|SHIP|FORWARD/i.test(v || "");   // "FAIL ... no config passes" is a fail
async function loadResearch() {
  RES.rows = await api("/api/research");
  const r = RES.rows, fam = new Set(r.map((x) => x.family));
  const dev = r.filter((x) => x.stage === "dev" && isPass(x.verdict)).length;
  const val = r.filter((x) => /valid/.test(x.stage) && isPass(x.verdict)).length;
  const fin = r.filter((x) => /final|recent/.test(x.stage) && isPass(x.verdict)).length;
  $("#resKpis").innerHTML = [["Runs", r.length, "in the ledger"], ["Families", fam.size, "distinct ideas"], ["Passed DEV", dev, "in-sample gates"],
    ["Passed VALID", val, "unseen period"], ["Passed FINAL", fin, "last unseen look"], ["Trader", "FlowTrend", "see the Trader tab"]]
    .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("");
  scatter(); table();
}
function scatter() {
  const pts = RES.rows.filter((x) => x.pf != null && x.dd != null);
  const W = $("#scatter").clientWidth || 600, H = 300, L = 44, B = 30, T = 10, R = 12;
  const X = (d) => L + Math.min(d, 100) / 100 * (W - L - R), Y = (p) => T + (1 - (Math.min(Math.max(p, 0.6), 1.8) - 0.6) / 1.2) * (H - T - B);
  let g = "";
  for (let d = 0; d <= 100; d += 20) g += `<line class="gl" x1="${X(d)}" x2="${X(d)}" y1="${T}" y2="${H - B}"/><text x="${X(d)}" y="${H - 10}" text-anchor="middle">${d}%</text>`;
  for (let p = 0.6; p <= 1.81; p += 0.2) g += `<line class="gl" x1="${L}" x2="${W - R}" y1="${Y(p)}" y2="${Y(p)}"/><text x="${L - 6}" y="${Y(p) + 4}" text-anchor="end">${p.toFixed(1)}</text>`;
  g += `<line class="thr" x1="${L}" x2="${W - R}" y1="${Y(1.15)}" y2="${Y(1.15)}"/><line class="thr" x1="${X(35)}" x2="${X(35)}" y1="${T}" y2="${H - B}"/>`;
  g += `<text x="${W - R}" y="${H - B - 6}" text-anchor="end">max drawdown →</text><text x="${L + 6}" y="${T + 12}">profit factor ↑</text>`;
  const dots = pts.map((x, i) => `<circle data-i="${RES.rows.indexOf(x)}" cx="${X(x.dd)}" cy="${Y(x.pf)}" r="${isPass(x.verdict) ? 6 : 4.5}" fill="${isPass(x.verdict) ? css("--good") : css("--critical")}" fill-opacity="${isPass(x.verdict) ? 1 : .55}"/>`).join("");
  $("#scatter").innerHTML = `<svg viewBox="0 0 ${W} ${H}">${g}${dots}</svg>`;
  $$("#scatter circle").forEach((c) => {
    c.addEventListener("mousemove", (e) => { const x = RES.rows[+c.dataset.i];
      tip(e, `<b>${x.family}</b> · ${x.tf} · ${x.stage}<br>${isPass(x.verdict) ? "✓" : "✕"} ${x.verdict}<br>PF <span class="mono">${x.pf}</span> · DD <span class="mono">${x.dd}%</span> · 300 → <span class="mono">${x.final ?? "–"}</span>`); });
    c.addEventListener("mouseleave", () => tip());
  });
}
/* one drawer per family: furthest stage, best numbers and run count on one line; its runs fold out */
const STAGE_RANK = { dev: 0, valid: 1, fair: 2, recent: 3, final: 4 };
const stageRank = (s) => STAGE_RANK[Object.keys(STAGE_RANK).find((k) => (s || "").startsWith(k))] ?? 0;
function table() {
  const cols = [["protocol", "Prot."], ["tf", "TF"], ["stage", "Stage"], ["verdict", "Verdict"], ["trades", "Trades", 1], ["pf", "PF", 1],
    ["pf_x2", "PF 2× cost", 1], ["dd", "Max DD %", 1], ["final", "300 →", 1], ["sharpe", "Sharpe", 1], ["twin", "Twins pct", 1], ["at", "Run"]];
  const rows = RES.rows.filter((x) => (!RES.stage || x.stage.startsWith(RES.stage)) && (`${x.family} ${x.verdict} ${x.tf}`.toLowerCase().includes(RES.q)));
  const fams = new Map(); rows.forEach((x) => { if (!fams.has(x.family)) fams.set(x.family, []); fams.get(x.family).push(x); });
  const v = (x) => `<span class="vb ${isPass(x) ? "pass" : /FAIL|KILL/i.test(x) ? "fail" : "other"}">${isPass(x) ? "✓" : /FAIL|KILL/i.test(x) ? "✕" : "•"} ${x || "–"}</span>`;
  const sum = [...fams].map(([f, rs]) => {
    rs.sort((a, b) => { const k = RES.sort, va = a[k] ?? -1e9, vb = b[k] ?? -1e9; return (va > vb ? 1 : va < vb ? -1 : 0) * RES.dir; });
    const top = rs.slice().sort((a, b) => stageRank(b.stage) - stageRank(a.stage) || isPass(b.verdict) - isPass(a.verdict))[0];   // furthest stage reached
    const passed = rs.filter((x) => isPass(x.verdict)), best = (k) => Math.max(...rs.map((x) => x[k] ?? -1e9));
    return { f, rs, top, passed, pf: best("pf"), fin: best("final"), at: rs.reduce((m, x) => x.at > m ? x.at : m, "") };
  }).sort((a, b) => (b.passed.length > 0) - (a.passed.length > 0) || stageRank(b.top.stage) - stageRank(a.top.stage) || (b.at > a.at ? 1 : -1));
  $("#resCards").innerHTML = sum.length ? sum.map((s) => { const id = "res:" + s.f;
    return `<div class="pick bot-card strat-card ${BOPEN.has(id) ? "open" : ""}" data-id="${id}">
      <div class="pick-top" role="button" tabindex="0" aria-expanded="${BOPEN.has(id)}"><h4>${s.f}</h4>${v(s.top.verdict)}
        <span class="strat-sum"><span class="pick-key"><small>runs</small> <b>${s.rs.length}</b></span>
        <span class="pick-key k2"><small>best PF</small> <b>${s.pf > 99 ? ">99" : s.pf > -1e9 ? s.pf : "–"}</b></span>
        <span class="pick-key k2"><small>best 300 →</small> <b>${s.fin > -1e9 ? s.fin : "–"}</b></span>
        <span class="pick-key k2"><small>last run</small> <b>${s.at ? s.at.slice(0, 10) : "–"}</b></span></span><i class="chev">▾</i></div>
      <div class="pick-body"><div><div class="table-wrap"><table class="res-runs">
        <thead><tr>${cols.map(([k, l, r]) => `<th data-k="${k}" class="${r ? "r" : ""}">${l}${RES.sort === k ? (RES.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead>
        <tbody>${s.rs.map((x) => `<tr>${cols.map(([k, , r]) => `<td class="${r ? "r" : ""}">${k === "verdict" ? v(x.verdict) : k === "at" ? (x.at || "").slice(0, 10) : (k === "pf" || k === "pf_x2") && x[k] > 99 ? ">99" : x[k] ?? "–"}</td>`).join("")}</tr>`).join("")}</tbody>
      </table></div></div></div></div>`; }).join("") : `<div class="empty">No runs match.</div>`;
}
$("#resCards").onclick = (e) => {
  const th = e.target.closest("th[data-k]");
  if (th) { const k = th.dataset.k; RES.dir = RES.sort === k ? -RES.dir : -1; RES.sort = k; table(); return; }
  const h = e.target.closest(".pick-top"); if (h) botToggle(h);
};
$("#resCards").onkeydown = (e) => { const h = e.target.closest(".pick-top"); if (h && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); botToggle(h); } };

/* ================================================================ SCANNER */
const SCAN = { data: null, running: false };
async function loadScan() {
  try { const s = await api("/api/scan"); SCAN.data = s.scan; SCAN.f1 = s.f1; SCAN.running = s.running; } catch (e) { return; }
  renderScan(); renderWatch(); coinAlerts(); loadForward();
  if (SCAN.running) setTimeout(loadScan, 4000);
}

/* ---------------------------------------------------------------- forward test */
const FWD = { data: null, filter: "" };
/* post-mortem: the scanner explaining its own results (daily task, research/opportunity/postmortem.py) */
const PM_LABEL = { "as is": "as is", market: "with BTC trend", solo: "skip market-wide hours", both: "both" };
async function loadPostmortem() {
  let o; try { o = await api("/api/postmortem"); } catch (e) { return; }
  if (!o || !o.live) return;
  const lv = o.live, hi = o.history, R = lv.reasons || {};
  const tot = Object.values(R).reduce((x, y) => x + y, 0) || 1, share = (k) => Math.round((R[k] || 0) / tot * 100);
  const passed = (R["passed, with the market"] || 0) + (R["passed, against the market"] || 0);
  $("#pmSum").innerHTML = `<span class="pick-key"><small>closed</small> <b>${lv.n}</b></span>
    <span class="pick-key k2"><small>passed</small> <b class="${passed / tot >= 0.5 ? "up" : "down"}">${Math.round(passed / tot * 100)}%</b></span>
    <span class="pick-key k2"><small>changes that pass</small> <b>${o.proposals.length}</b></span>`;
  $("#pmState").textContent = `updated ${o.updated} · ${lv.n} closed signals on ${lv.days} days · daily at 06:20`;
  const reasons = [["passed, with the market", "up"], ["passed, against the market", "up"], ["market moved against", "down"],
    ["coin itself", "down"], ["fast stop", "down"], ["near miss", "down"], ["time up", ""]]
    .map(([k, c]) => `<div class="chipbox"><b class="${c}">${R[k] || 0}</b> ${k} <span class="muted">(${share(k)}%)</span></div>`).join("");
  const rows = Object.entries(lv.rules).sort((a, b) => b[1].avg_pct - a[1].avg_pct).map(([k, r]) => {
    const h = hi?.rules?.[k]?.variants || {};
    const best = Object.entries(h).filter(([v]) => v !== "as is").sort((a, b) => (b[1].day_avg_pct ?? -99) - (a[1].day_avg_pct ?? -99))[0];
    return `<tr><td><b>${k}</b></td><td class="${r.direction === "LONG" ? "up" : "down"}">${r.direction === "LONG" ? "▲" : "▼"}</td>
      <td class="r">${r.n}</td><td class="r up">${r.passed}</td><td class="r down">${r.failed}</td><td class="r">${r.time_up}</td>
      <td class="r ${cls(r.avg_pct)}">${pct(r.avg_pct)}</td>
      <td class="r ${cls(r.with_market_avg)}">${r.with_market_avg == null ? "–" : pct(r.with_market_avg)}</td>
      <td class="r ${cls(r.against_market_avg)}">${r.against_market_avg == null ? "–" : pct(r.against_market_avg)}</td>
      <td class="r ${cls(h["as is"]?.day_avg_pct)}">${h["as is"] ? `${pct(h["as is"].day_avg_pct)} <span class="muted small">t ${h["as is"].t_day}</span>` : "–"}</td>
      <td class="small">${best ? `${PM_LABEL[best[0]] || best[0]}: <span class="${cls(best[1].day_avg_pct)}">${pct(best[1].day_avg_pct)}</span> <span class="muted">t ${best[1].t_day}</span>` : "–"}</td></tr>`; }).join("");
  const props = o.proposals.length ? o.proposals.map((p) => `<div class="chipbox">💡 <b>${p.rule}</b> + ${PM_LABEL[p.change] || p.change}: history ${pct(p.history.day_avg_pct)} (as is ${pct(p.history_as_is.day_avg_pct)}), live ${pct(p.live.avg_pct)} (as is ${pct(p.live_as_is.avg_pct)})</div>`).join("")
    : `<div class="small muted">No change passes yet: ${o.rule}</div>`;
  $("#pmBody").innerHTML = `<div class="fwd-strip">${reasons}</div>
    <div class="table-wrap"><table><thead><tr><th>Rule</th><th></th><th class="r">Closed</th><th class="r">✅</th><th class="r">❌</th><th class="r">⏱</th>
      <th class="r">Live avg</th><th class="r" title="BTC moved the same way as the trade while it was open">When market went with it</th>
      <th class="r" title="BTC moved against the trade while it was open">When market went against</th>
      <th class="r" title="day-average per trade after costs, ${hi?.start}..${hi?.end}, ${hi?.coins} coins the scanner watches">History 6 months</th><th>Best change on history</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div style="margin-top:8px">${props}</div>`;
}
async function loadForward() {
  try { FWD.data = await api("/api/forward"); } catch (e) { return; }
  renderForward();
  if (SCAN.data) renderScan();                     // alert cards show their follow-up from the forward log
  loadPostmortem();
}
/* paper books: fixed rule sets traded on paper from their start (research/opportunity/paper_books.json) */
function renderBooks(books) {
  $("#bookCards").innerHTML = books.map((b) => { const id = "book:" + b.id, st = lt(b.start);
    const rows = b.trades.map((r) => `<tr><td class="mono small">${sigTime(new Date(r.trigger_time * 1000).toISOString().slice(0, 19).replace("T", " "))}</td>
      <td>${r.coin}</td><td class="${r.direction === "LONG" ? "up" : "down"}">${r.direction === "LONG" ? "▲" : "▼"} ${r.direction}</td><td>${r.condition}</td>
      <td class="r">${fp(r.entry)}</td><td class="r">${fp(r.target)}</td><td class="r">${fp(r.stop)}</td><td class="${verdict(r).cls}">${verdict(r).txt}</td>
      <td class="r mono ${cls(r.usdt)}">${r.usdt == null ? "–" : (r.usdt > 0 ? "+" : "") + r.usdt.toFixed(2)}</td></tr>`).join("");
    return `<div class="pick bot-card strat-card ${BOPEN.has(id) ? "open" : ""}" data-id="${id}">
      <div class="pick-top" role="button" tabindex="0" aria-expanded="${BOPEN.has(id)}"><h4>📒 ${b.label}</h4><span class="pill small">PAPER</span>
        <span class="strat-sum"><span class="pick-key"><small>closed</small> <b>${b.closed}</b> <small>open</small> <b>${b.open}</b></span>
        <span class="pick-key k2"><b class="up">✅ ${b.target}</b> <b class="down">❌ ${b.stop}</b> <b>⏱ ${b.time}</b></span>
        <span class="pick-key k2"><small>net</small> <b class="${cls(b.net_usdt)}">${(b.net_usdt > 0 ? "+" : "") + b.net_usdt.toFixed(2)} USDT</b></span></span><i class="chev">▾</i></div>
      <div class="pick-body"><div>
        <div class="small muted">Since ${st} · ${b.margin_usdt} USDT margin at ${b.leverage}x per signal (${b.margin_usdt * b.leverage} USDT position) · costs and funding included · nothing is traded · ${b.why}</div>
        ${rows ? `<div class="table-wrap"><table><thead><tr><th>Signal flagged</th><th>Coin</th><th>Trade</th><th>Rule</th><th class="r">Entry</th><th class="r">Target</th><th class="r">Stop</th><th>Result</th><th class="r">USDT</th></tr></thead><tbody>${rows}</tbody></table></div>`
          : `<div class="empty">No signals yet since ${st}.</div>`}
      </div></div></div>`; }).join("");
}
function renderForward() {
  const d = FWD.data; if (!d) return;
  const b = d.badges?.conditions || {}, tot = d.totals || { n: 0, open: 0, closed: 0 };
  const tradeable = Object.values(b).filter((x) => x.badge !== "RED").length;
  $("#fwdStrip").innerHTML = [
    `Auto-scan <b>hourly at :02</b>${d.task?.last_auto ? ` · last run <b>${d.task.last_auto}</b>` : " · first run pending"}`,
    `Forward log <b>${tot.n || 0}</b> triggers · <b>${tot.open || 0}</b> open · <b>${tot.closed || 0}</b> closed`,
    `Tradeable rules now <b>${tradeable}</b> / ${Object.keys(b).length}`,
    ...[[24, "last 24h"], [168, "last 7 days"]].map(([h, lab]) => {
      const v = (d.verdicts || {})[h] || {};
      return `Verdicts ${lab}: <b class="up">✅ ${v.target || 0}</b> passed · <b class="down">❌ ${v.stop || 0}</b> failed · ⏱ ${v.time || 0} time up`; }),
  ].map((x) => `<div class="chipbox">${x}</div>`).join("");
  const rows = Object.entries(b).sort((x, y) => (BADGE_RANK_UI[x[1].badge] - BADGE_RANK_UI[y[1].badge]) || ((y[1].forward?.closed || 0) - (x[1].forward?.closed || 0)));
  const min = d.badges?.rule?.min_closed || 50;
  $("#fwdTable").innerHTML = `<thead><tr><th>Rule</th><th>Trade</th><th>Badge now</th><th class="r">Backtest 25-26</th>
    <th>Forward progress</th><th class="r" title="same rule, same hour = one market event">Events</th><th class="r">Fwd avg</th><th class="r">Fwd day-avg</th><th class="r">Win %</th><th>Target / stop / time</th><th>Why</th></tr></thead><tbody>` +
    rows.map(([k, x]) => { const f = x.forward || {};
      return `<tr><td><b>${k}</b></td><td class="${x.direction === "LONG" ? "up" : "down"}">${x.direction === "LONG" ? "▲" : "▼"} ${x.direction} ${x.hours}h</td>
      <td>${BADGE_ICON[x.badge]} ${x.badge}${x.dev_badge !== x.badge ? ` <span class="muted small">(dev ${BADGE_ICON[x.dev_badge]})</span>` : ""}</td>
      <td class="r ${cls(x.dev_test.avg_net_pct)}">${pct(x.dev_test.avg_net_pct)}</td>
      <td><span class="prog"><i style="width:${Math.min(100, (f.closed || 0) / min * 100)}%"></i></span><span class="mono small">${f.closed || 0}/${min}</span>${f.open ? ` <span class="muted small">+${f.open} open</span>` : ""}</td>
      <td class="r mono" title="${f.cluster_events ? `${f.cluster_n} trades came from ${f.cluster_events} clustered events (3+ coins); solo avg ${f.solo_avg_pct == null ? "–" : pct(f.solo_avg_pct)}, cluster avg ${pct(f.cluster_avg_pct)}` : "no clustered events yet"}">${f.closed ? `${f.events}${f.cluster_events ? ` <span class="muted small">(${f.cluster_events} clustered)</span>` : ""}` : "–"}</td>
      <td class="r ${cls(f.avg_pct)}">${f.closed ? pct(f.avg_pct) : "–"}</td><td class="r ${cls(f.day_avg_pct)}">${f.closed ? pct(f.day_avg_pct) : "–"}</td>
      <td class="r">${f.closed ? f.win_pct + "%" : "–"}</td>
      <td>${f.closed ? `<span class="mini3"><i style="width:${f.target_pct}%;background:var(--up)"></i><i style="width:${f.stop_pct}%;background:var(--down)"></i><i style="width:${f.time_pct}%;background:var(--neutral)"></i></span> <span class="small muted">${f.target_pct}/${f.stop_pct}/${f.time_pct}</span>` : "–"}</td>
      <td class="why">${x.why.join("; ")}</td></tr>`; }).join("") + "</tbody>";
  $("#boardSum").innerHTML = `<span class="pick-key"><small>tradeable</small> <b>${tradeable} / ${Object.keys(b).length}</b></span>
    <span class="pick-key k2"><small>closed</small> <b>${tot.closed || 0}</b></span>`;
  const v24 = (d.verdicts || {})[24] || {};
  $("#logSum").innerHTML = `<span class="pick-key"><small>triggers</small> <b>${tot.n || 0}</b> <small>open</small> <b>${tot.open || 0}</b></span>
    <span class="pick-key k2"><small>24h</small> <b class="up">✅ ${v24.target || 0}</b> <b class="down">❌ ${v24.stop || 0}</b> <b>⏱ ${v24.time || 0}</b></span>`;
  renderBooks(d.books || []);
  const isOpen = (r) => r.status === "open" || r.status === "pending";
  const log = d.recent.filter((r) => !FWD.filter || (FWD.filter === "open" ? isOpen(r) : !isOpen(r)));
  $("#fwdLog").innerHTML = `<thead><tr><th>Signal flagged</th><th>Coin</th><th>Trade</th><th>Rule</th><th>Badge at alert</th><th class="r">Entry</th><th class="r">Target</th><th class="r">Stop</th><th>Verdict</th></tr></thead><tbody>` +
    log.map((r) => `<tr><td class="mono small">${sigTime(new Date(r.trigger_time * 1000).toISOString().slice(0, 19).replace("T", " "))}</td>
      <td><a href="#" class="coinlink" data-s="${r.coin}USDT">${r.coin}</a></td><td class="${r.direction === "LONG" ? "up" : "down"}">${r.direction === "LONG" ? "▲" : "▼"} ${r.direction}</td>
      <td>${r.condition}${r.cluster_n >= 3 ? ` <span class="pill small" title="${r.cluster_n} coins triggered this rule in the same hour: one market event">×${r.cluster_n}</span>` : ""}</td><td>${BADGE_ICON[r.badge] || ""}</td><td class="r">${fp(r.entry)}</td><td class="r">${fp(r.target)}</td><td class="r">${fp(r.stop)}</td>
      <td class="${verdict(r).cls}">${verdict(r).txt}</td></tr>`).join("") + "</tbody>";
  $$("#fwdLog .coinlink").forEach((a) => a.onclick = (e) => { e.preventDefault(); showView("markets"); selectSymbol(a.dataset.s, "1h"); });
}
/* ---------------------------------------------------------------- trader (quantlab's own, read-only view) */
let TR = null, trTimer = null, TRMODE = null;
const usd = (v, d = 2) => v == null || !isFinite(v) ? "–" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d = 2) => v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + Number(v).toFixed(d);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function renderTrader(d) {
  TR = d;
  if ($("#view-markets")?.classList.contains("active")) lvRender();
  const modes = Object.keys(d.modes);
  if (!modes.length) { $("#trKpis").innerHTML = `<div class="empty">No trader has run yet (data/trader is empty).</div>`; return; }
  if (!TRMODE || !d.modes[TRMODE]) TRMODE = modes.includes("live") ? "live" : "paper";
  const seg = $("#trMode"); seg.hidden = modes.length < 2;
  seg.innerHTML = modes.map((m) => `<button data-m="${m}" class="${m === TRMODE ? "on" : ""}">${m === "live" ? "Real money" : "Paper"}</button>`).join("");
  $$("#trMode button").forEach((b) => b.onclick = () => { TRMODE = b.dataset.m; renderTrader(TR); });
  const m = d.modes[TRMODE], paper = TRMODE === "paper";
  const st = !m.alive ? { cls: "alert", txt: "Not running" } : m.state === "running" ? { cls: "on", txt: (paper ? "Paper" : "Live") + " · trading" }
    : m.state === "halted" ? { cls: "alert", txt: "Day-loss halt · managing open trades" }
    : { cls: "paused", txt: "Paused · managing open trades" };
  $("#trBadge").className = "live-badge " + st.cls; $("#trBadge span").textContent = st.txt;
  $("#trSub").textContent = `${paper ? "Paper wallet, real Binance prices, no orders sent" : "Real money"} · state ${m.state} since ${lt(m.since)} · last heartbeat ${lt(m.heartbeat, 19)}${m.age_min != null ? ` (${m.age_min} min ago)` : ""}${m.halt_why ? ` · halted until ${lt(m.halt_until)}: ${m.halt_why}` : ""}`;
  $("#trAt").textContent = "read " + lt(d.at, 19).slice(11);
  $("#trPause").disabled = m.state !== "running";
  $("#trResume").disabled = !(paper && m.state !== "running");
  const wr = m.n_closed ? Math.round(100 * m.wins / m.n_closed) : null;
  $("#trKpis").innerHTML = [
    paper ? ["Equity", usd(m.equity), `started ${usd(m.start, 0)} USDT · closed + open`, "hero"] : null,
    ["Closed P&L", sgn(m.closed_pnl), `${m.n_closed} trades · ${wr == null ? "–" : wr + "% won"}`],
    ["Open P&L", sgn(m.open_pnl), `${m.open.length} open of 6 slots`],
    ["Worst closed trade", m.worst_closed == null ? "–" : sgn(m.worst_closed), "USDT"],
  ].filter(Boolean).map(([k, v, s, h]) => `<div class="kpi ${h || ""}"><div class="k">${k}</div><div class="v ${h ? "" : cls(parseFloat(v))}">${v}</div><div class="d">${s}</div></div>`).join("");
  const mk = d.market;
  $("#trMarket").innerHTML = !mk || mk.error ? `<span class="small muted">BTC trend: could not read</span>`
    : `<span class="live-badge ${mk.bull ? "on" : "paused"}"><i></i><span>BTC · ${mk.bull ? "UP" : "DOWN"}</span></span>
       <span><b>BTC 20-day return ${sgn(mk.ret20)}%</b> on the ${mk.as_of} daily candle · since ${mk.complete ? mk.since : "before " + mk.since}</span>
       <span class="small muted">Information only: FlowTrend does not use it.</span>`;
  const side = (t) => t.short ? `<span class="down">short</span>` : `<span class="up">long</span>`;
  const exitBy = (t) => { const x = new Date(t.open_time.replace(" ", "T") + "Z"); x.setUTCMinutes(0, 0, 0); x.setUTCHours(x.getUTCHours() + 48); return lt(x.getTime()); };
  $("#trOpen").innerHTML = m.open.length ? `<thead><tr><th>Coin</th><th>Side</th><th class="r">Entry</th><th class="r">Now</th><th class="r">Stop</th><th class="r">Stake</th><th class="r">P&L</th><th>Opened</th><th>Exit by</th></tr></thead><tbody>` +
    m.open.map((t) => `<tr><td><b>${t.coin}</b></td><td>${side(t)}</td><td class="r mono">${fp(t.open_price)}</td><td class="r mono">${fp(t.price)}</td>
      <td class="r mono">${fp(t.stop_price)}</td><td class="r mono">${usd(t.stake)}</td><td class="r mono ${cls(t.upnl)}"><b>${sgn(t.upnl)}</b></td>
      <td class="mono small">${lt(t.open_time)}</td><td class="mono small">${exitBy(t)}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No open trades.</td></tr></tbody>`;
  $("#trClosedNote").textContent = m.n_closed > m.closed.length ? `last ${m.closed.length} of ${m.n_closed}` : "newest first";
  $("#trClosed").innerHTML = m.closed.length ? `<thead><tr><th>Coin</th><th>Side</th><th class="r">Entry</th><th class="r">Exit</th><th>Why</th><th class="r">P&L</th><th>Opened</th><th>Closed</th></tr></thead><tbody>` +
    m.closed.map((t) => `<tr><td><b>${t.coin}</b></td><td>${side(t)}</td><td class="r mono">${fp(t.open_price)}</td><td class="r mono">${fp(t.close_price)}</td>
      <td${t.note ? ` title="${esc(t.note)}"` : ""}>${esc(t.reason)}${t.note ? " *" : ""}</td><td class="r mono ${cls(t.pnl)}">${sgn(t.pnl)}</td><td class="mono small">${lt(t.open_time)}</td><td class="mono small">${lt(t.close_time)}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No closed trades yet.</td></tr></tbody>`;
  $("#trLog").textContent = (m.log || []).join("\n");
}
async function loadTrader() { renderTrader(await api("/api/trader")); }
function trFail(e) { $("#trKpis").innerHTML = `<div class="empty">Could not load: ${esc(e.message)}</div>`; }
function liveView() {
  loadTrader().catch(trFail); loadDecisions().catch(() => {});
  clearInterval(trTimer);
  trTimer = setInterval(() => { if ($("#view-live").classList.contains("active")) loadTrader().catch(trFail); else clearInterval(trTimer); }, 20000);
}
$("#trRefresh").onclick = () => loadTrader().catch(trFail);

/* decision log: earlier calls, read-only */
async function loadDecisions() {
  const d = await api("/api/decisions"), t = d.total;
  $("#decSum").innerHTML = t.n ? `${t.n} decision${t.n > 1 ? "s" : ""} · ${t.scored} judged · you beat the bot ${t.better}/${t.scored} · value added <b>${sgn(t.added)}</b> USDT` : "no decisions recorded";
  $("#decTable").innerHTML = d.rows.length ? `<thead><tr><th>When</th><th>You saw</th><th>Call</th><th class="r">Open P&L then</th>
    <th class="r">Bot alone 24 h</th><th class="r">Bot alone ${d.horizon_h} h</th><th class="r">Value added</th></tr></thead><tbody>` + d.rows.map((r) =>
    `<tr><td class="mono small">${lt(r.at).slice(5)}<br><span class="muted">${r.positions.length} pos</span></td>
      <td class="ins">${esc(r.insight)}${r.tags.length ? `<br>${r.tags.map((x) => `<span class="tagc">${esc(x)}</span>`).join(" ")}` : ""}</td>
      <td><b>${r.label}</b></td><td class="r mono">${sgn(r.exit_now_value)}</td><td class="r mono">${sgn(r.bot_alone_24h)}</td>
      <td class="r mono">${r.pending ? `<span class="muted">pending</span>` : sgn(r.bot_alone)}</td>
      <td class="r mono">${r.value_added == null ? `<span class="muted">waits</span>` : `<b>${sgn(r.value_added)}</b>`}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No decisions recorded.</td></tr></tbody>`;
}

/* pause / resume: typed confirmation -> server writes the trader's state file */
const ACT = {
  pause: { word: "PAUSE", title: "Pause new trades", body: () => `<p>The trader stops opening <b>new</b> trades. Open trades stay and are still managed (stops and 48 h exits keep working). Undo with Resume.</p>` },
  resume: { word: "RESUME", title: "Resume paper trading", body: () => `<p>The paper trader may open new trades again, following FlowTrend's rules. No real orders.</p>` },
};
function trMsg(c, html) { const j = $("#trMsg"); j.hidden = false; j.className = "job " + c; j.innerHTML = html; }
function openModal(act) {
  const a = ACT[act], m = $("#liveModal");
  $("#mTitle").textContent = a.title + (TRMODE === "live" ? " · real money" : " · paper"); $("#mBody").innerHTML = a.body();
  $("#mWord").textContent = a.word; $("#mInput").value = ""; $("#mGo").disabled = true; m.hidden = false; $("#mInput").focus();
  $("#mInput").oninput = () => { $("#mGo").disabled = $("#mInput").value.trim() !== a.word; };
  $("#mCancel").onclick = () => { m.hidden = true; };
  $("#mGo").onclick = async () => {
    m.hidden = true;
    try {
      const r = await api("/api/trader/action", { method: "POST", headers: { "Content-Type": "application/json", "X-Quantlab": "1" },
        body: JSON.stringify({ mode: TRMODE, action: act, confirm: a.word }) });
      trMsg("ok", `${TRMODE}: now <b>${r.state}</b>`);
    } catch (e) { trMsg("bad", esc(e.message)); }
    loadTrader().catch(trFail);
  };
}
$("#trPause").onclick = () => openModal("pause");
$("#trResume").onclick = () => openModal("resume");
const BADGE_RANK_UI = { GREEN: 0, YELLOW: 1, ORANGE: 2, RED: 3 };
const INC_ICON = { INCUBATING: "🧪", PROMOTED: "🟡", KILLED: "🔴", EXPIRED: "⚪", TAMPERED: "⛔" };
/* ================================================================ switcher paper bot (2026-10-24, paper only) */
const SW_PICK = { R: "R · reversal book", M: "M · momentum basket", cash: "cash" };
async function loadSwitcher() {
  const d = await api("/api/switcher");
  if (d.error) throw new Error(d.error);
  if (d.missing) { $("#swStrip").innerHTML = `<div class="empty">No status yet — the paper bot has not run.</div>`; return; }
  const h = d.health || {};
  const state = h.ok ? `<span class="up">● running</span>` : !h.alive ? `<span class="down">● stopped</span>` : `<span class="down">● late / errors</span>`;
  $("#swAt").textContent = "last pass " + lt(d.checked_utc + "Z");
  $("#swStrip").innerHTML = [
    `Bot ${state} <span class="muted">${h.alive ? "pid " + h.pid : "process not found"} · last pass ${h.age_min ?? "–"} min ago${h.errors_recent ? " · " + h.errors_recent + " error(s) in log" : ""}</span>`,
    `This week <b>${SW_PICK[d.pick_this_week] || d.pick_this_week || "–"}</b>`,
    `Paper equity <b>${usd(d.equity)}</b> <span class="muted">of ${usd(d.wallet || 300, 0)} · closed ${fitUsd(d.realized)} · open ${fitUsd(d.open_pnl)}</span>`,
    `Trades <b>${d.trades_closed}</b> closed · <b>${d.positions_open}</b> open`,
    `Forward count from <b>${d.forward_from}</b> <span class="muted">· ${d.coins} coins · candles to ${lt(d.updated_utc)}</span>`,
  ].map((x) => `<div class="chipbox">${x}</div>`).join("");
  const p = (v) => v == null ? `<span class="muted">–</span>` : `<span class="${cls(v)}">${pct(v)}</span>`;
  $("#swWeeks").innerHTML = `<thead><tr><th>week (Mon)</th><th>pick</th><th>R known</th><th>R earned</th><th>M earned</th><th>switcher</th></tr></thead><tbody>` +
    (d.weeks || []).slice().reverse().map((w) => { const sw = w.pick === "R" ? w.R : w.pick === "M" ? w.M : w.pick === "cash" ? 0 : null;
      return `<tr><td class="mono">${w.week}</td><td>${w.pick}</td><td class="mono">${p(w.R_known)}</td><td class="mono">${p(w.R)}</td><td class="mono">${p(w.M)}</td><td class="mono">${w.pick === "(backtest)" ? `<span class="muted">–</span>` : p(sw)}</td></tr>`; }).join("") + "</tbody>";
  const pos = d.positions || [];
  $("#swPos").innerHTML = !pos.length ? `<tbody><tr><td class="muted">No paper positions yet — counting starts Monday ${d.forward_from} 00:00 UTC (${lt(d.forward_from + "T00:00:00Z")} on this PC).</td></tr></tbody>` :
    `<thead><tr><th>book</th><th>pair</th><th>side</th><th>opened</th><th>closed</th><th class="r">entry</th><th class="r">now / exit</th><th class="r">USDT</th></tr></thead><tbody>` +
    pos.map((r) => `<tr><td>${r.book}</td><td class="mono">${r.pair}</td><td>${r.side}</td><td class="mono">${lt(r.open)}</td><td class="mono">${r.is_open ? "open" : lt(r.close)}</td>
      <td class="r mono">${Number(r.entry).toPrecision(6)}</td><td class="r mono">${Number(r.now).toPrecision(6)}</td><td class="r mono ${cls(r.usdt)}">${fitUsd(r.usdt)}</td></tr>`).join("") + "</tbody>";
  $("#swLog").textContent = (d.log || []).join("\n");
}
async function loadDelist() {
  const d = await api("/api/delist");
  if (d.error) throw new Error(d.error);
  if (d.missing) { $("#dlStrip").innerHTML = `<div class="empty">Not started yet.</div>`; return; }
  const h = d.health || {}, cl = d.closed || [], op = d.open || [];
  const sum = (a, k) => a.reduce((x, y) => x + (y[k] || 0), 0);
  $("#dlStrip").innerHTML = [
    `Bot ${h.ok ? `<span class="up">● running</span>` : `<span class="down">● ${h.alive ? "late" : "stopped"}</span>`} <span class="muted">checked ${h.age_min ?? "–"} min ago</span>`,
    `Closed <b>${cl.length}</b> <span class="${cls(sum(cl, "usdt"))}">${fitUsd(sum(cl, "usdt"))}</span> USDT`,
    `Open <b>${op.length}</b> <span class="${cls(sum(op, "open_usdt"))}">${fitUsd(sum(op, "open_usdt"))}</span> USDT`,
    `Waiting for entry <b>${(d.pending || []).length}</b>`,
  ].map((x) => `<div class="chipbox">${x}</div>`).join("");
  const t = (ms) => ms ? lt(ms) : "–";
  const rows = [...op.map((x) => ({ ...x, st: "open", u: x.open_usdt })), ...cl.slice().reverse().map((x) => ({ ...x, st: x.exit, u: x.usdt }))];
  $("#dlTable").innerHTML = !rows.length ? `<tbody><tr><td class="muted">No delisting announced since the bot started — it trades only on new announcements (about 2–3 a month).</td></tr></tbody>` :
    `<thead><tr><th>coin</th><th>entry</th><th class="r">entry price</th><th>status</th><th class="r">USDT</th></tr></thead><tbody>` +
    rows.map((x) => `<tr><td class="mono">${x.sym}</td><td class="mono">${t(x.entry_ms)}</td><td class="r mono">${x.entry}</td><td>${x.st}</td><td class="r mono ${cls(x.u)}">${fitUsd(x.u)}</td></tr>`).join("") + "</tbody>";
}
$("#swRefresh").onclick = () => { loadSwitcher().catch((e) => $("#swStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
  loadDelist().catch((e) => $("#dlStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`); };
/* ================================================================ market fit (2026-10-21, information only) */
const FIT = { d: null, k: "combo", bot: null, live: {} };
const FIT_NAMES = { trend: "Trend", vol: "Moves", width: "Breadth", combo: "Trend × moves" };
const FIT_BOTS = { NFI: "NFI X8 (full list)", E0V1EN: "E0V1EN (2nd bot, long only)", Tandem: "Tandem", FlowTrend: "FlowTrend",
  V4Complacency: "V4 Complacency", MajorsTrend: "Majors trend", VBreak4BullCalm: "VBreak4 bull-calm", BreakoutDay: "BreakoutDay (test 🔴, not live)" };
function fitWord(x, base) {                       /* plain-language comparison with the strategy's own normal */
  if (x == null || base == null) return "–";
  if (base <= 0) return x > base ? "better" : "worse";
  const r = x / base;
  return r >= 1.15 ? "more" : r <= 0.85 ? "less" : "usual";
}
const fitUsd = (x) => x == null ? "–" : (x >= 0 ? "+" : "") + x.toFixed(2);
async function loadFit() {
  const [d, tr] = await Promise.all([api("/api/fit"), api("/api/trader").catch(() => null)]);
  FIT.d = d;
  if (d.error) throw new Error(d.error);
  const run = new Set();                            /* FlowTrend marked while the quantlab trader runs */
  if (tr && Object.values(tr.modes || {}).some((m) => m.alive)) run.add("FlowTrend");
  FIT.live = run;
  const L = d.labels, I = d.inputs, c = d.cuts;
  $("#fitAt").textContent = "checked " + lt(d.made);
  $("#fitStrip").innerHTML = [
    `Market today <b>${L.trend} · ${L.vol} · ${L.width} breadth</b>`,
    `Trend: BTC 7 days <b>${I.btc_7d_pct >= 0 ? "+" : ""}${I.btc_7d_pct}%</b> <span class="muted">(up &gt; +${c.trend * 100}%, down &lt; −${c.trend * 100}%)</span>`,
    `Moves: BTC average daily move <b>${I.btc_avg_move_pct}%</b> <span class="muted">(calm &lt; ${(c.vol[0] * 100).toFixed(2)}% · wild &gt; ${(c.vol[1] * 100).toFixed(2)}%)</span>`,
    `Breadth: coins above their 20-day average <b>${I.breadth_pct}%</b> of ${I.coins} <span class="muted">(weak &lt; ${c.breadth[0] * 100}% · strong &gt; ${c.breadth[1] * 100}%)</span>`,
  ].map((x) => `<div class="chipbox">${x}</div>`).join("");
  const bots = Object.entries(d.bots).sort((x, y) => ((y[1].match.combo || {}).usdt_per_day ?? -99) - ((x[1].match.combo || {}).usdt_per_day ?? -99));
  $("#fitAll").innerHTML = `<thead><tr><th>Strategy</th><th>similar days</th><th>trades a day</th><th></th><th>USDT a day</th><th></th><th>win rate</th><th>avg trade</th><th>all trades in test</th></tr></thead><tbody>` +
    bots.map(([k, b]) => { const m = b.match.combo || {}, a = b.all, few = (m.days || 0) < 30 || a.trades < 60;
      return `<tr class="${run.has(k) ? "now" : ""}"><td>${run.has(k) ? "● " : ""}${FIT_BOTS[k] || k}</td><td class="mono">${m.days ?? "–"}</td>
        <td class="mono">${m.trades_per_day ?? "–"} <span class="muted">/ ${a.trades_per_day}</span></td><td>${fitWord(m.trades_per_day, a.trades_per_day)}</td>
        <td class="mono">${fitUsd(m.usdt_per_day)} <span class="muted">/ ${fitUsd(a.usdt_per_day)}</span></td><td>${fitWord(m.usdt_per_day, a.usdt_per_day)}</td>
        <td class="mono">${m.win_rate ?? "–"}%</td><td class="mono">${m.avg_trade_pct ?? "–"}%</td>
        <td class="mono">${a.trades}${few ? ' <span class="muted">· few, read with care</span>' : ""}</td></tr>`; }).join("") + "</tbody>";
  if (!FIT.bot || !d.bots[FIT.bot]) FIT.bot = bots[0][0];
  $("#fitBots").innerHTML = bots.map(([k]) => `<button data-b="${k}" class="${k === FIT.bot ? "on" : ""}">${FIT_BOTS[k] || k}</button>`).join("");
  $$("#fitBots button").forEach((x) => x.onclick = () => { FIT.bot = x.dataset.b; $$("#fitBots button").forEach((y) => y.classList.toggle("on", y === x)); fitTable(); });
  $("#fitNote").innerHTML = "The second number in a cell is the strategy's normal (all days of its test). Labels for a day use only data up to the day before (yesterday's close); a trade counts on the day it opened. " +
    "E0V1EN: its list has many more coins in 2026 than in 2024, and a few young coins (UB, BR, BULLA, AKE, ZAMA) carried its best 2026 months. " +
    "Strategies with few trades (Majors trend, V4) give thin tables. Switching by market type was tested on 2026-10-07 and did not earn; this page sets expectations only.";
  fitTable();
}
function fitTable() {
  const d = FIT.d, k = FIT.k, b = d && d.bots[FIT.bot]; if (!b) return;
  $("#fitTable").innerHTML = `<thead><tr><th>${FIT_NAMES[k]}</th><th>days</th><th>trades a day</th><th>win rate</th><th>avg trade</th><th>USDT a day</th><th>shorts</th></tr></thead><tbody>` +
    b.tables[k].map((r) => { const now = d.labels[k] === r.label;
      return `<tr class="${now ? "now" : ""}"><td>${now ? "▶ " : ""}${r.label}</td><td class="mono">${r.days}</td><td class="mono">${r.trades_per_day}</td>
        <td class="mono">${r.win_rate ?? "–"}%</td><td class="mono">${r.avg_trade_pct ?? "–"}%</td><td class="mono">${fitUsd(r.usdt_per_day)}</td><td class="mono">${r.shorts_pct ?? "–"}%</td></tr>`; }).join("") +
    `<tr><td class="muted">all days</td><td class="mono">${b.all.days}</td><td class="mono">${b.all.trades_per_day}</td><td class="mono">${b.all.win_rate}%</td><td class="mono">${b.all.avg_trade_pct}%</td><td class="mono">${fitUsd(b.all.usdt_per_day)}</td><td></td></tr></tbody>`;
}
$$("#fitSeg button").forEach((b) => b.onclick = () => { $$("#fitSeg button").forEach((x) => x.classList.toggle("on", x === b)); FIT.k = b.dataset.k; fitTable(); });
$("#fitRefresh").onclick = () => loadFit().catch((e) => $("#fitStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);

const BL_ICON = { PAPER: "🧪", PASS: "🟡", KILLED: "🔴", EXPIRED: "⚪", TAMPERED: "⛔" };
async function loadBearLab() {
  const d = await api("/api/bearlab"), ideas = d.ideas || [], st = d.state || {}, n = (x) => ideas.filter((i) => i.status === x).length;
  const openNow = ideas.reduce((k, i) => k + ((i.live && i.live.open) || []).length, 0);
  $("#blStrip").innerHTML = [
    `Last evaluation <b>${lt(st.ts)}</b> · live data until <b>${lt(st.data_until)}</b>`,
    `🧪 <b>${n("PAPER")}</b> on paper · 🟡 <b>${n("PASS")}</b> · 🔴 <b>${n("KILLED")}</b> · ⚪ <b>${n("EXPIRED")}</b>${n("TAMPERED") ? ` · ⛔ <b>${n("TAMPERED")}</b>` : ""}`,
    `Open paper shorts now <b>${openNow}</b>`,
    `Screens <b>${d.screens.total}</b> · passed light check <b>${d.screens.passed}</b>`,
    d.passed_md ? `<span class="warn">🟡 an idea passed on live data – see PASSED.md</span>` : "",
  ].filter(Boolean).map((x) => `<div class="chipbox">${x}</div>`).join("");
  const f2 = (v) => pct(v);
  $("#blCards").innerHTML = ideas.length ? ideas.map((v) => { const L = v.live || {}, S = v.screen || {}, id = "bl:" + v.id,
      t = L.trades || 0, p = Math.min(t / 40, (L.days || 0) / 12, 1), op = L.open || [], wo = L.worst || [];
    return `<div class="pick bot-card inc-card ${BOPEN.has(id) ? "open" : ""}" data-id="${id}">
      <div class="pick-top" role="button" tabindex="0" aria-expanded="${BOPEN.has(id)}"><h4>${v.id}</h4>
        <span class="pill small">${BL_ICON[v.status] || ""} ${v.status}</span>
        <span class="strat-sum"><span class="pick-key"><span class="prog"><i style="width:${p * 100}%"></i></span></span>
        <span class="pick-key k2"><small>trades / days</small> <b>${t} / ${L.days || 0}</b></span>
        <span class="pick-key k2"><small>open</small> <b>${op.length}</b></span>
        <span class="pick-key k2"><small>day-avg</small> <b class="${cls(L.day_avg)}">${t ? f2(L.day_avg) : "–"}</b></span></span><i class="chev">▾</i></div>
      <div class="pick-body"><div>
        <div class="small muted mono">since ${lt(v.start)} · ${v.source}</div>
        ${v.why ? `<div class="small">${BL_ICON[v.status] || ""} ${v.why}</div>` : ""}
        <div class="kpis bots-kpis">${[["Live: trades / days", `${t} / ${L.days || 0}`, "needs 40 trades on 12 days"],
          ["Live: day-avg", t ? f2(L.day_avg) : "–", "per day, after costs and funding"],
          ["Live: t", L.day_t == null ? "–" : L.day_t.toFixed(2), "needs ≥ 2.5"],
          ["Live: avg 2× costs", t ? f2(L.avg_2x) : "–", "needs > 0"],
          ["History 2022-01 → 2024-04", f2(S.avg_A), `${S.trades_A ?? "–"} trades, avg per trade`],
          ["History 2024-05 → 2026-09", f2(S.avg_B), `${S.trades_B ?? "–"} trades · 2× costs ${f2(S.avg_2x)}`]]
          .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("")}</div>
        <p class="small"><b>Open now (paper):</b> ${op.length ? op.map((o) => `${o[0]} since ${lt(o[1])} <b class="${cls(o[2])}">${pct(o[2])}</b>`).join(" · ") : "none"}</p>
        <p class="small"><b>Worst closed (live):</b> ${wo.length ? wo.map((o) => `${o[0]} ${lt(o[1])} <b class="${cls(o[2])}">${pct(o[2])}</b>`).join(" · ") : "none yet"}</p>
        <p class="small"><b>Why it is here:</b> ${v.reason}</p>
      </div></div></div>`; }).join("") : `<div class="empty">No ideas on paper yet.</div>`;
  $("#blDisc").textContent = d.discovery || "No discovery run yet.";
}
async function loadScalps() {
  const d = await api("/api/scalps"), L = d.latest || {}, ideas = d.ideas || [], sc = d.screens || [], n = (x) => ideas.filter((i) => i.status === x).length;
  const live = ideas.filter((i) => i.status === "PAPER" || i.status === "PASS").length, nPass = sc.filter((s) => s.passed).length;
  $("#scStrip").innerHTML = [
    `Last scan <b>${lt(L.ts)}</b> · 5m data until <b>${lt(L.data_until)}</b>`,
    L.bear_day == null ? "" : `Bear day now <b>${L.bear_day ? "yes – alerts on" : "no – alerts paused"}</b>`,
    `Rules alerting <b>${live}</b> · 🔴 <b>${n("KILLED")}</b> · ⚪ <b>${n("EXPIRED")}</b>${n("TAMPERED") ? ` · ⛔ <b>${n("TAMPERED")}</b>` : ""}`,
    `Screens <b>${sc.length}</b> · passed <b>${nPass}</b>`,
    d.passed_md ? `<span class="warn">🟡 a rule passed on live data – see PASSED.md</span>` : "",
  ].filter(Boolean).map((x) => `<div class="chipbox">${x}</div>`).join("");
  const op = L.open || [];
  $("#scOpen").innerHTML = op.length ? `<thead><tr><th>coin</th><th>side</th><th>rule</th><th>entry (UTC)</th><th>entry</th><th>stop</th><th>target</th><th>exit by</th><th>now</th></tr></thead><tbody>` +
    op.map((o) => `<tr><td><b>${o.coin}</b></td><td>${o.side}</td><td>${BL_ICON[o.status] || ""} ${o.idea}</td><td class="mono">${lt(o.entry_time)}</td>
      <td class="mono">${o.entry}</td><td class="mono">${o.stop}</td><td class="mono">${o.target ?? "–"}</td><td class="mono">${lt(o.exit_by)}</td>
      <td class="mono ${cls(o.now_pct)}">${pct(o.now_pct)}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No open scalps.${live ? "" : " No rule has passed its screen yet, so there is nothing to alert."}</td></tr></tbody>`;
  $("#scRules").innerHTML = ideas.length ? `<thead><tr><th>rule</th><th>status</th><th>side</th><th>since</th><th>live trades / days</th><th>live avg</th><th>t</th><th>history A / B</th><th>why it is here</th></tr></thead><tbody>` +
    ideas.map((v) => { const l = v.live || {}, s = v.screen || {};
      return `<tr><td><b>${v.id}</b></td><td>${BL_ICON[v.status] || ""} ${v.status}${v.why ? `<div class="small muted">${v.why}</div>` : ""}</td><td>${l.side || "–"}</td>
        <td class="mono">${lt(v.start)}</td><td class="mono">${l.trades || 0} / ${l.days || 0}</td><td class="mono ${cls(l.avg)}">${l.trades ? pct(l.avg) : "–"}</td>
        <td class="mono">${l.day_t ?? "–"}</td><td class="mono">${pct(s.avg_A)} / ${pct(s.avg_B)}</td><td class="small">${v.reason}</td></tr>`; }).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No rule is alerting yet.</td></tr></tbody>`;
  $("#scScreens").innerHTML = sc.length ? `<thead><tr><th>rule</th><th>result</th><th>trades</th><th>avg / trade</th><th>2× costs</th><th>half A</th><th>half B</th><th>win</th><th>day t</th><th>screened</th></tr></thead><tbody>` +
    sc.map((s) => `<tr><td><b>${s.rule}</b></td><td>${s.passed ? "✅ passed" : "🔴 failed"}</td><td class="mono">${s.trades}</td>
      <td class="mono ${cls(s.avg)}">${pct(s.avg)}</td><td class="mono ${cls(s.avg_2x)}">${pct(s.avg_2x)}</td>
      <td class="mono ${cls(s.avg_A)}">${pct(s.avg_A)} <span class="muted">(${s.trades_A ?? 0})</span></td><td class="mono ${cls(s.avg_B)}">${pct(s.avg_B)} <span class="muted">(${s.trades_B ?? 0})</span></td>
      <td class="mono">${s.win ?? "–"}%</td><td class="mono">${s.day_t ?? "–"}</td><td class="mono small">${lt(s.ts)}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">Nothing screened yet.</td></tr></tbody>`;
}
async function loadSupport(fresh) {
  if (fresh) $("#spStrip").innerHTML = `<div class="chipbox">scanning all coins… (~15 s)</div>`;
  const d = await api("/api/support" + (fresh ? "?fresh=1" : "")), m = d.market || {}, st = d.log_stats || {};
  LV.supRows = [...(d.top || []), ...(d.near || [])];        /* support zones become drawable levels on the chart */
  const chart = (c) => { showView("markets"); selectSymbol(c + "USDT", "1d"); };
  $("#spAt").textContent = "scanned " + lt(d.ts);
  $("#spStrip").innerHTML = [
    `Coins scanned <b>${d.scanned}</b> of ${d.universe}`,
    `At support now <b>${(d.near || []).length}</b>`,
    `Picks <b>${(d.top || []).length}</b>`,
    `BTC 20 days <b class="${cls(m.btc_20d)}">${pct(m.btc_20d)}</b> <span class="small">${m.note || ""}</span>`,
    `Past picks <b>${st.picks || 0}</b> · closed <b>${st.closed || 0}</b> · 🎯 <b>${st.targets || 0}</b> · 🛑 <b>${st.stops || 0}</b>` +
      (st.avg_closed != null ? ` · avg <b class="${cls(st.avg_closed)}">${pct(st.avg_closed)}</b>` : ""),
  ].map((x) => `<div class="chipbox">${x}</div>`).join("");
  const top = d.top || [];
  $("#spTop").innerHTML = top.length ? top.map((r, i) => `<div class="sp-card">
      <div class="sp-h"><span class="sp-rank">#${i + 1}</span><span class="sp-coin" data-c="${r.coin}">${r.coin}</span>
        <span class="mono">${fp(r.price)}</span><span class="sp-score">${r.score}</span></div>
      <div class="sp-bar"><i style="width:${r.score}%"></i></div>
      <div class="sp-lv"><div>buy zone<b>${fp(r.buy_lo)}–${fp(r.buy_hi)}</b></div><div>stop<b class="down">${fp(r.stop)}</b>${pct(r.stop_pct, 1)}</div>
        <div>target<b class="up">${fp(r.target)}</b>${pct(r.target_pct, 1)}</div><div>reward / risk<b>${r.rr}×</b>RSI ${r.rsi}</div></div>
      <ul>${r.reasons.map((x) => `<li>${x}</li>`).join("")}</ul>
      ${r.warnings.length ? `<ul class="sp-w">${r.warnings.map((x) => `<li>⚠ ${x}</li>`).join("")}</ul>` : ""}
    </div>`).join("") : `<div class="empty">No coin passes every filter right now: nothing sits close to a strong support with enough room above. Waiting is a valid answer.</div>`;
  const near = d.near || [];
  $("#spNear").innerHTML = near.length ? `<thead><tr><th></th><th>coin</th><th>price</th><th>support</th><th>held</th><th>above it</th><th>stop</th><th>target</th><th>R/R</th><th>RSI</th><th>7d</th><th>30d</th><th>trend</th><th>24h vol</th><th>score</th></tr></thead><tbody>` +
    near.map((r) => `<tr><td>${r.eligible ? "✓" : ""}</td><td><a href="#" class="coinlink" data-c="${r.coin}"><b>${r.coin}</b></a></td><td class="mono">${fp(r.price)}</td>
      <td class="mono">${fp(r.support)}</td><td class="mono">${r.touches}×</td><td class="mono">${pct(r.dist_pct, 1)}</td><td class="mono down">${pct(r.stop_pct, 1)}</td>
      <td class="mono up">${pct(r.target_pct, 1)}</td><td class="mono">${r.rr}</td><td class="mono">${r.rsi}</td><td class="mono ${cls(r.ch7)}">${pct(r.ch7, 1)}</td>
      <td class="mono ${cls(r.ch30)}">${pct(r.ch30, 1)}</td><td>${r.trend}</td><td class="mono">${big(r.vol24)}</td><td class="mono"><b>${r.score}</b></td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No coin is at a strong support now.</td></tr></tbody>`;
  const lg = d.log || [], R = { target: "🎯 target", stop: "🛑 stop", time: "⌛ 30 days" };
  $("#spLogHead").textContent = `each coin logged once at the first scan that ranks it top 10 · result after ${d.rules.cost_pct}% spot fees · stop counts first if both touched in one 4h candle`;
  $("#spLog").innerHTML = lg.length ? `<thead><tr><th>picked</th><th>coin</th><th>rank</th><th>entry</th><th>stop</th><th>target</th><th>result</th><th>return</th></tr></thead><tbody>` +
    lg.map((r) => `<tr><td class="mono">${lt(r.ts_ms)}</td><td><b>${r.coin}</b></td><td class="mono">#${r.rank}</td><td class="mono">${fp(r.entry)}</td>
      <td class="mono">${fp(r.stop)}</td><td class="mono">${fp(r.target)}</td><td>${R[r.result] || "open"}</td>
      <td class="mono ${cls(r.ret_pct)}">${pct(r.ret_pct)}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">No picks logged yet.</td></tr></tbody>`;
  $("#spSkipped").textContent = `No Binance spot pair (skipped): ${(d.no_spot || []).join(", ") || "none"} · too thin (< 250K USDT a day): ${(d.thin || []).join(", ") || "none"}` +
    ((d.errors || []).length ? ` · errors: ${d.errors.map((e) => e.coin).join(", ")}` : "");
  $$("#spTop .sp-coin, #spNear .coinlink").forEach((a) => a.onclick = (e) => { e.preventDefault(); chart(a.dataset.c); });
}
$("#spRefresh").onclick = () => loadSupport(true).catch((e) => $("#spStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
$("#scRefresh").onclick = () => loadScalps().catch((e) => $("#scStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
async function loadIncubator() {
  const d = await api("/api/incubator"), s = d.state;
  if (!s) { $("#incCards").innerHTML = `<div class="empty">No evaluation yet.</div>`; return; }
  const ideas = Object.entries(s.ideas), n = (st) => ideas.filter(([, v]) => v.status === st).length;
  $("#incStrip").innerHTML = [
    `Last evaluation <b>${lt(s.updated)}</b> · data until <b>${lt(s.data_until)}</b>`,
    `BTC market type today <b>${s.market_type_today}</b>`,
    `🧪 <b>${n("INCUBATING")}</b> incubating · 🟡 <b>${n("PROMOTED")}</b> · 🔴 <b>${n("KILLED")}</b> · ⚪ <b>${n("EXPIRED")}</b>`,
    `Discovery tries <b>${s.screens.total}</b> · passed light check <b>${s.screens.passed}</b>`,
    s.code_ok ? "" : `<span class="warn">⛔ incubator code changed after freezing: verdicts on hold</span>`,
  ].filter(Boolean).map((x) => `<div class="chipbox">${x}</div>`).join("");
  /* one drawer per idea: name, status, progress and the forward numbers on one line; the rest folds out */
  $("#incCards").innerHTML = ideas.length ? ideas.map(([k, v]) => { const f = v.forward || {}, r = v.rule, p = Math.min(f.trades / r.min_trades || 0, f.days / r.min_days || 0, 1), id = "inc:" + k;
    return `<div class="pick bot-card inc-card ${BOPEN.has(id) ? "open" : ""}" data-id="${id}">
      <div class="pick-top" role="button" tabindex="0" aria-expanded="${BOPEN.has(id)}"><h4>${v.name}</h4>
        <span class="pill small">${INC_ICON[v.status] || ""} ${v.status}</span>
        <span class="strat-sum"><span class="pick-key"><span class="prog"><i style="width:${p * 100}%"></i></span></span>
        <span class="pick-key k2"><small>trades / days</small> <b>${f.trades || 0} / ${f.days || 0}</b></span>
        <span class="pick-key k2"><small>day-avg</small> <b class="${cls(f.day_avg_pct)}">${f.trades ? pct(f.day_avg_pct) : "–"}</b></span></span><i class="chev">▾</i></div>
      <div class="pick-body"><div>
        <div class="small muted mono">${k} · ${v.kind} · since ${v.start.slice(0, 10)} · source ${v.source}</div>
        ${v.why ? `<div class="small">${INC_ICON[v.status] || ""} ${v.why}</div>` : ""}
        <div class="kpis bots-kpis">${[["Progress", `${Math.round(p * 100)}%`, `needs ${r.min_trades} trades on ${r.min_days} days`],
          ["Trades / days", `${f.trades || 0} / ${f.days || 0}`, `time limit ${r.max_days} days`],
          ["Day-avg", f.trades ? pct(f.day_avg_pct) : "–", "per day, after costs"],
          ["t", f.day_t == null ? "–" : f.day_t.toFixed(2), "needs ≥ 2"],
          ["PF 2× costs", f.pf_2x == null ? "–" : f.pf_2x.toFixed(2), "needs ≥ 1"],
          ["Win rate", f.win_pct == null ? "–" : f.win_pct.toFixed(0) + "%", f.last ? "last trade " + lt(f.last) : "no trades yet"]]
          .map(([a, b, c]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="d">${c}</div></div>`).join("")}</div>
        <p class="small"><b>Why it is here:</b> ${v.reason}</p>
      </div></div></div>`; }).join("") : `<div class="empty">No ideas in the incubator.</div>`;
  $("#incDisc").textContent = d.discovery || "No discovery run yet.";
}
// The scanner works on closed 1h candles: trigger_bar is the candle's OPEN, the signal exists from its CLOSE (+1h).
// Shown in this PC's local time.
function sigTime(bar) {
  const t = new Date(Date.parse(bar.replace(" ", "T")) + 3.6e6);
  const loc = t.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  return loc;
}
// Scanner judging itself: each logged signal from forward.db, entry = open of the hour after the signal.
// exit_time is the 1h bar in which target/stop was hit, so "within Nh" counts that bar.
function verdict(r) {
  const nowH = (Date.now() / 1000 - r.entry_time) / 3600;
  const took = r.exit_time ? (r.exit_time - r.entry_time) / 3600 + 1 : null;
  const res = r.ret_pct == null ? "" : ` ${pct(r.ret_pct)}`;
  if (r.status === "target") return { cls: "up", txt: `✅ PASSED · target hit within ${took}h${res}` };
  if (r.status === "stop") return { cls: "down", txt: `❌ FAILED · stop hit within ${took}h${res}` };
  if (r.status === "time") return r.ret_pct > 0 ? { cls: "up", txt: `⏱ TIME UP after ${r.hours}h · closed in profit${res}` }
                                                 : { cls: "down", txt: `⏱ TIME UP after ${r.hours}h · closed at a loss${res}` };
  if (r.status === "pending") return { cls: "", txt: "⏳ waiting for the entry hour to close" };
  const left = Math.max(0, Math.ceil(r.hours - nowH));
  return { cls: "", txt: `⏳ OPEN · ${Math.max(0, Math.floor(nowH))}h of ${r.hours}h used · neither target nor stop yet · ${left}h left` };
}
// Full detail of one signal: when, what the numbers were, where price is now, the plan and the record.
function alertDetails(a) {
  const d = a.direction === "LONG" ? 1 : -1, bar = Date.parse(a.trigger_bar.replace(" ", "T"));
  const loc = (ms) => new Date(ms).toLocaleString("en-GB", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  const mins = Math.round((Date.now() - (bar + 3.6e6)) / 6e4);
  const ago = mins < 60 ? `${mins} min ago` : `${Math.floor(mins / 60)}h ${mins % 60}min ago`;
  const move = d * (a.last_price / a.ref_price - 1) * 100;
  const toT = Math.abs(a.target / a.last_price - 1) * 100, toS = Math.abs(a.stop / a.last_price - 1) * 100;
  const r = fwdRow(a), t = a.test, rt = a.random_test;
  const row = (k, v) => `<div class="kv"><span>${k}</span><span>${v}</span></div>`;
  return `<details class="adet" onclick="event.stopPropagation()"><summary>Details</summary>
    ${row("Signal flagged", `${loc(bar + 3.6e6)} · ${ago}`)}
    ${row("Trigger candle", `1h candle ${loc(bar)} → ${loc(bar + 3.6e6)}`)}
    ${row("Entry", `open of the next hour, ${loc(bar + 3.6e6)}${r && r.entry ? ` · filled ${fp(r.entry)}` : ""}`)}
    ${row("Exit by", `${loc(bar + 3.6e6 * (1 + a.hours))} if neither target nor stop is hit (${a.hours}h)`)}
    ${row("What fired", a.why)}
    ${row("24h volume", `${a.vratio.toFixed(1)}× its 30-day average${a.vratio > 20 ? ' <span class="muted">(30-day average was tiny: new or relisted coin)</span>' : ""}`)}
    ${row("24h move", `${a.z24 >= 0 ? "+" : ""}${a.z24.toFixed(2)} × its normal daily swing`)}
    ${row("Funding now", a.frate == null ? "–" : `${(a.frate * 100).toFixed(4)}% per 8h${a.frate < 0 ? " (shorts pay longs)" : " (longs pay shorts)"}`)}
    ${row("24h traded", `${(a.qv / 1e6).toFixed(1)}M USDT`)}
    ${row("Price now", `${fp(a.last_price)} · <span class="${cls(move)}">${pct(move)}</span> for this ${a.direction.toLowerCase()} · ${toT.toFixed(1)}% to target, ${toS.toFixed(1)}% to stop`)}
    ${row("Plan", `target ${fp(a.target)} (+${a.target_pct.toFixed(1)}%) · stop ${fp(a.stop)} (−${a.stop_pct.toFixed(1)}%) · min order ${a.min_cost} USDT`)}
    ${a.cluster_n > 1 ? row("Same hour", `${a.cluster_n} coins fired this rule together (market move, not coin news)`) : ""}
    ${row("Past cases 2025-26", `${t.n} trades on ${t.coins} coins over ${t.days} days · win ${t.win_pct}% · PF ${t.pf} · worst ${pct(t.worst_pct)}`)}
    ${row("Random entries", `same coins/hours at random: avg ${pct(rt.avg_net_pct)} · PF ${rt.pf}`)}
    ${row("Live record so far", (() => { const f = FWD.data?.badges?.conditions?.[a.condition]?.forward; return f && f.closed
      ? `${f.closed} closed · ✅ ${f.target_pct}% · ❌ ${f.stop_pct}% · ⏱ ${f.time_pct}% · avg ${pct(f.avg_pct)}` : "no closed trades yet"; })())}
  </details>`;
}
function fwdRow(a) {
  const t = Math.floor(Date.parse(a.trigger_bar.replace(" ", "T")) / 1000);
  return (FWD.data?.recent || []).find((r) => r.symbol === a.symbol && r.condition === a.condition && r.trigger_time === t);
}
function alertCard(a) {
  const t = a.test, d = a.direction === "LONG" ? 1 : -1;
  const done = d * (a.last_price / a.ref_price - 1) * 100 / a.target_pct;
  return `<div class="alert" data-sym="${a.coin}USDT" data-i="${SCAN.data.alerts.indexOf(a)}">
    <div class="a1"><span class="coin">${a.coin}</span><span class="dir ${a.direction.toLowerCase()}">${a.direction === "LONG" ? "▲" : "▼"} ${a.direction}</span>
      <span class="state ${a.badge === "YELLOW" ? "bull" : "flat"}">${a.badge === "YELLOW" ? "🟡" : a.badge === "GREEN" ? "🟢" : a.badge === "ORANGE" ? "🟠" : "🔴"} ${a.badge}</span>
      <span class="cond">${a.condition} · ${a.hours_ago}h ago</span></div>
    <div class="small">Signal flagged <b class="mono">${sigTime(a.trigger_bar)}</b> · 1h candle close</div>
    ${(() => { const r = fwdRow(a); if (!r) return ""; const v = verdict(r); return `<div class="small ${v.cls}"><b>Follow-up:</b> ${v.txt}</div>`; })()}
    <div class="why">${a.why}</div>
    <div class="levels"><div><div class="k">Entry ~</div><div class="v">${fp(a.ref_price)}</div></div>
      <div><div class="k">Target</div><div class="v up">${fp(a.target)}</div></div>
      <div><div class="k">Stop</div><div class="v down">${fp(a.stop)}</div></div>
      <div><div class="k">Exit by</div><div class="v">${a.hours}h</div></div></div>
    <div class="small muted">Past cases 2025-26: <b class="mono">${t.n}</b> on ${t.coins} coins · avg after costs <b class="mono ${cls(t.avg_net_pct)}">${pct(t.avg_net_pct)}</b> (random ${pct(a.random_test.avg_net_pct)}) · median ${pct(t.median_net_pct)} · day t ${t.t_day}</div>
    <div class="bar3" title="target first / stop first / time exit"><i style="width:${t.target_first}%;background:var(--up)"></i><i style="width:${t.stop_first}%;background:var(--down)"></i><i style="width:${t.time_exit}%;background:var(--neutral)"></i></div>
    <div class="small muted">Target first ${t.target_first}% · stop first ${t.stop_first}% · time exit ${t.time_exit}% · regimes ${a.regimes_positive}/4</div>
    ${done >= 0.5 ? `<div class="warn">⚠ Late: price already covered ${(done * 100).toFixed(0)}% of the way to target</div>` : ""}
    <div class="badge-line">300 USDT, 2% risk: size ${a.notional_2pct_risk.toFixed(0)} USDT · ${a.badge_why.join("; ")}</div>
    ${alertDetails(a)}</div>`;
}
function renderF1() {
  const f = SCAN.f1;
  if (!f) { $("#f1Body").innerHTML = `<div class="empty">Not run yet: the next scan creates it.</div>`; return; }
  $("#f1State").textContent = `updated ${lt(f.updated)} · market today ${f.market_type_today} · ${f.history_n} signals logged`;
  const dn = String(f.market_type_today || "").startsWith("DN");
  const head = `<div class="small muted">${f.rule}. Active ${f.active_when}.</div><div class="small muted">${f.why.join(" · ")}</div>`;
  const rows = f.alerts.length ? `<div class="table-wrap"><table><thead><tr><th>Signal</th><th>Coin</th><th class="r">24h move</th><th class="r">Volume ×</th><th class="r">Entry ~</th><th class="r">Now</th><th class="r">Stop</th><th>Exit by</th></tr></thead><tbody>` +
    f.alerts.map((a) => `<tr><td class="mono">${lt(a.signal_bar).slice(5)}</td><td><a href="#" class="coinlink" data-s="${a.coin}USDT">${a.coin}</a></td>
      <td class="r down">${a.ret24_pct.toFixed(1)}%</td><td class="r mono">${a.vol_x == null ? "–" : a.vol_x.toFixed(1)}</td><td class="r">${fp(a.ref_price)}</td>
      <td class="r ${cls(a.last_price / a.ref_price - 1)}">${fp(a.last_price)}</td><td class="r down">${fp(a.stop)} <span class="muted small">−${a.stop_pct.toFixed(1)}%</span></td>
      <td class="mono small">${lt(a.exit_by).slice(5)}</td></tr>`).join("") + "</tbody></table></div>"
    : `<div class="empty">${dn ? "No crash-bounce signal in the last 24h." : "Sleeping: today is an uptrend day, F1 only fires on downtrend days."}</div>`;
  $("#f1Body").innerHTML = head + rows;
  $("#f1Sum").innerHTML = `<span class="pick-key">${f.alerts.length ? `<b class="up">${f.alerts.length} signal${f.alerts.length > 1 ? "s" : ""}</b> in 24h` : dn ? "no signal in 24h" : "sleeping · uptrend day"}</span>
    <span class="pick-key k2"><small>logged</small> <b>${f.history_n}</b></span>`;
  $$("#f1Body .coinlink").forEach((a) => a.onclick = (e) => { e.preventDefault(); showView("markets"); selectSymbol(a.dataset.s, "1h"); });
}
function renderScan() {
  renderF1();
  const s = SCAN.data, btn = $("#scanBtn");
  btn.disabled = SCAN.running; btn.textContent = SCAN.running ? "Scanning…" : "Run scan";
  if (!s) { $("#scanList").innerHTML = `<div class="empty">No scan yet. Press <b>Run scan</b> (about 1-3 minutes).</div>`; return; }
  const age = (Date.now() - Date.parse(s.time.replace(" UTC", "Z").replace(" ", "T"))) / 3.6e6;
  $("#scanState").innerHTML = `Last scan ${s.time} · ${s.coins} coins${age > 3 ? ' · <span class="warn">older than 3h, triggers may be stale</span>' : ""}`;
  const good = s.alerts.filter((a) => a.badge !== "RED"), red = s.alerts.filter((a) => a.badge === "RED");
  $("#scanCount").textContent = good.length || "";
  $("#scanList").innerHTML = good.length ? groupAlerts(good).map((g) => g.length < 3 ? g.map(alertCard).join("")
    : `<div class="event"><div class="event-h">Market event: <b>${g[0].condition} ${g[0].direction}</b> on <b>${g.length}</b> coins in the same hour (flagged ${sigTime(g[0].trigger_bar)}).
        This is one bet on the market, not ${g.length}. Two most liquid coins shown.</div>${g.slice(0, 2).map(alertCard).join("")}
        <div class="small muted">Also triggered: ${g.slice(2).map((a) => a.coin).join(", ")}</div></div>`).join("")
    : `<div class="empty">No alerts with a tested edge in this scan.</div>`;
  $("#redSum").innerHTML = `<span class="pick-key"><b>${red.length}</b> <small>alerts this scan</small></span>`;
  $("#scanRed").innerHTML = groupAlerts(red).map((g) => `<span>${g[0].condition}${g.length > 1 ? ` ×${g.length}` : ""} · ${g.map((a) => a.coin).join(", ")}</span>`).join("");
  $$(".alert").forEach((el) => el.onclick = () => { showView("markets"); selectSymbol(el.dataset.sym, "1h");
    const a = SCAN.data.alerts[+el.dataset.i]; setTimeout(() => drawAlert(a), 900); });
}
function groupAlerts(list) {          // same rule + same trigger hour = one market event, most liquid coin first
  const m = new Map();
  list.forEach((a) => { const k = a.condition + "|" + a.trigger_bar; if (!m.has(k)) m.set(k, []); m.get(k).push(a); });
  return [...m.values()].map((g) => g.sort((x, y) => (y.qv || 0) - (x.qv || 0)));
}
function drawAlert(a) {
  const set = { kind: "pick", name: a.condition ? `Scanner · ${a.condition}` : "Picked signal",
                side: a.direction || (a.target != null && a.ref_price != null && a.target < a.ref_price ? "SHORT" : "LONG"),
                entry: a.ref_price, stop: a.stop, target: a.target, note: a.note || "" };
  const i = LV.sets.findIndex((v) => v.entry === set.entry && v.stop === set.stop);
  if (i >= 0) { LV.pick = i; lvRender(); return; }
  lvAdd(set);
}
function coinAlerts() {
  const list = (SCAN.data?.alerts || []).filter((a) => a.coin + "USDT" === M.sym);
  $("#coinAlerts").innerHTML = list.length ? list.map((a) => `<div class="kv"><span>${a.condition}</span><span class="${a.direction === "LONG" ? "up" : "down"}">${a.direction} · ${a.badge}</span>
    <span>Target / stop</span><span>${fp(a.target)} / ${fp(a.stop)}</span></div><button class="chip" style="margin-top:8px" data-i="${SCAN.data.alerts.indexOf(a)}">Draw levels</button>`).join("<hr style='border:0;border-top:1px solid var(--border)'>")
    : "No fresh scanner trigger.";
  $$("#coinAlerts button").forEach((b) => b.onclick = () => drawAlert(SCAN.data.alerts[+b.dataset.i]));
}

function activeInd() {
  const on = $$("#indToggles input:checked");
  $("#indN").textContent = on.length;
  $("#activeInd").innerHTML = on.map((i) => { const sw = i.parentElement.querySelector(".sw");
    return `<span>${sw ? sw.outerHTML : ""}${i.dataset.short || i.parentElement.textContent.trim()}</span>`; }).join("");
}


/* ================================================================ trade levels + position size (2026-11-14)
   One place for every price this coin has a reason to care about: the paper trader's own open trade, a fresh
   scanner trigger, and the spot-support zone. Each set draws entry / stop / target on the chart and feeds the
   size calculator, so the number you would actually send is on screen next to the level that produced it. */
const LV = { on: true, sets: [], pick: 0, supRows: [], lines: [], trAt: 0, trBusy: false, hit: [], tool: null, draft: null, extra: [], supAt: 0, supBusy: false };
const TF_SEC = { "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400 };
const base = () => M.sym.replace(/USDT$/, "");
const usdt = (v) => v == null || !isFinite(v) ? "–" : Number(v).toFixed(2);

function lvSets() {
  const b = base(), out = [];
  for (const t of (TR?.modes?.paper?.open || []).filter((t) => t.coin === b))
    out.push({ kind: "pos", name: "Paper trade, open now", side: t.short ? "SHORT" : "LONG",
      entry: t.open_price, stop: t.stop_price, target: null, at: barAt(Date.parse(String(t.open_time).replace(" ", "T") + "Z") / 1000),
      note: `${usdt(t.stake)} USDT · opened ${lt(t.open_time)}${t.upnl != null ? ` · P&L ${sgn(t.upnl)}` : ""}` });
  for (const t of (TR?.modes?.live?.open || []).filter((t) => t.coin === b))
    out.push({ kind: "pos", name: "LIVE trade, open now", side: t.short ? "SHORT" : "LONG",
      entry: t.open_price, stop: t.stop_price, target: null, note: `${usdt(t.stake)} USDT · real money` });
  for (const a of (SCAN.data?.alerts || []).filter((a) => a.coin === b))
    out.push({ kind: "scan", name: `Scanner · ${a.condition}`, side: a.direction, badge: a.badge,
      entry: a.ref_price, stop: a.stop, target: a.target,
      at: barAt(Date.parse(String(a.trigger_bar).replace(" ", "T").replace("+00:00", "Z")) / 1000),
      note: `${BADGE_ICON[a.badge] || ""} ${a.badge} · ${a.hours}h limit · flagged ${lt(a.trigger_bar)}` });
  const live = M.bars.at(-1)?.close;
  const sup = LV.supRows.find((r) => r.coin === b && r.support
    && (!live || (live / r.support - 1) <= 0.5));            /* price 50%+ above it: stale level, not a zone to trade */
  /* LV.extra holds what the user put there by hand (trade tool, a clicked label) so a rebuild cannot drop it */
  if (sup) out.push({ kind: "sup", name: "Spot support zone", side: "LONG",
    entry: sup.buy_hi ?? sup.support, stop: sup.stop, target: sup.target, zone: [sup.buy_lo, sup.buy_hi],
    note: `held ${sup.touches}× · ${sup.dist_atr} ATR above the level` });
  return [...LV.extra, ...out];
}

function lvAdd(set) {                                   /* put it at the top and keep it selected */
  LV.extra = [set, ...LV.extra.filter((v) => v.kind !== set.kind)].slice(0, 2);
  LV.pick = 0; lvRender();
}

function lvClear() { LV.lines.forEach((l) => { try { S.candle.removePriceLine(l); } catch (e) {} }); LV.lines = []; M.alertLines = []; }

function lvDraw(set) {
  if (!S.candle) return;
  lvClear();
  if (!LV.on || !set) return;
  const last = M.bars.at(-1)?.close, away = (v) => last && v ? ` ${pct((v / last - 1) * 100)}` : "";
  const add = (price, color, title, style = LW.LineStyle.Dashed, width = 1) => {
    if (price == null || !isFinite(price)) return;
    LV.lines.push(S.candle.createPriceLine({ price, color, title, lineWidth: width, lineStyle: style, axisLabelVisible: true }));
  };
  if (set.zone && set.zone[0] != null && set.zone[1] != null) {
    add(set.zone[0], css("--series-3"), "zone ↓", LW.LineStyle.Dotted);
    add(set.zone[1], css("--series-3"), "zone ↑", LW.LineStyle.Dotted);
  }
  add(set.entry, css("--text-secondary"), "Entry" + away(set.entry), LW.LineStyle.Solid, 2);
  add(set.stop, css("--down"), "Stop" + away(set.stop));
  add(set.target, css("--up"), "Target" + away(set.target));
  M.alertLines = LV.lines;
  drawVP(); tradeBox(set);
}

/* the same numbers as the side card, on the chart where the eye already is */
function tradeBox(v) {
  const el = $("#tradeBox"); if (!el) return;
  if (!LV.on || !v || v.entry == null) { el.className = "trade-box"; el.innerHTML = ""; return; }
  const rr = v.target != null && v.stop != null ? Math.abs(v.target - v.entry) / Math.abs(v.entry - v.stop) : null;
  const risk = v.stop != null ? Math.abs(v.entry - v.stop) / v.entry * 100 : null;
  const eq = +($("#szEq")?.value) || 300, rk = +($("#szRisk")?.value) || 1;
  const size = risk ? (eq * rk / 100) / (risk / 100) : null;
  el.className = "trade-box on " + (v.side === "LONG" ? "long" : "short");
  el.innerHTML = `<h5 class="${v.side === "LONG" ? "up" : "down"}">${v.side} · ${esc(v.name)}</h5>
    <div class="row"><span><i>in</i> ${fp(v.entry)}</span>${v.stop != null ? `<span><i>stop</i> ${fp(v.stop)}</span>` : ""}
      ${v.target != null ? `<span><i>tgt</i> ${fp(v.target)}</span>` : ""}${rr ? `<span><i>R:R</i> ${rr.toFixed(2)}</span>` : ""}</div>
    ${size ? `<div class="sz">${risk.toFixed(2)}% stop · ${size.toFixed(0)} USDT for ${(eq * rk / 100).toFixed(2)} at risk</div>` : ""}`;
}

function lvRender() {
  if (!LV.trBusy && Date.now() - LV.trAt > 30000) {          /* the Live tab may not have been opened yet */
    LV.trBusy = true;
    api("/api/trader").then((d) => { TR = d; LV.trAt = Date.now(); LV.trBusy = false; lvRender(); })
      .catch(() => { LV.trAt = Date.now(); LV.trBusy = false; });
  }
  if (!LV.supBusy && Date.now() - LV.supAt > 600000) {       /* the whole support scan, so any coin has its level */
    LV.supBusy = true;                                       /* the server caches it, so this is cheap after the first */
    api("/api/support").then((d) => { LV.supRows = [...(d.top || []), ...(d.near || [])];
      LV.supAt = Date.now(); LV.supBusy = false; lvRender(); })
      .catch(() => { LV.supAt = Date.now(); LV.supBusy = false; });
  }
  LV.sets = lvSets();
  if (LV.pick >= LV.sets.length) LV.pick = 0;
  $("#lvN").textContent = LV.sets.length || "";
  const el = $("#lvList");
  if (!el) return;
  el.innerHTML = LV.sets.length ? LV.sets.map((v, i) => {
    const rr = v.target != null && v.stop != null && v.entry != null
      ? Math.abs(v.target - v.entry) / Math.abs(v.entry - v.stop) : null;
    const sl = v.stop != null && v.entry ? Math.abs(v.entry - v.stop) / v.entry * 100 : null;
    return `<button class="lv ${v.side === "LONG" ? "long" : "short"} ${i === LV.pick ? "on" : ""}" data-i="${i}">
      <span class="lv-h"><b>${esc(v.name)}</b><span class="side ${v.side === "LONG" ? "up" : "down"}">${v.side}</span></span>
      <span class="lv-n"><span><i>in</i> ${fp(v.entry)}</span><span><i>stop</i> ${v.stop == null ? "–" : fp(v.stop)}</span>
        <span><i>tgt</i> ${v.target == null ? "–" : fp(v.target)}</span>${rr ? `<span><i>R:R</i> ${rr.toFixed(2)}</span>` : ""}
        ${sl ? `<span><i>risk</i> ${sl.toFixed(2)}%</span>` : ""}</span>
      <span class="lv-x">${esc(v.note || "")}</span></button>`;
  }).join("") : `<div class="small muted">Nothing on ${esc(base())} right now — no open trade, no fresh scanner trigger.
    Support levels appear once the Spot support tab has run.</div>`;
  $$("#lvList .lv").forEach((b) => b.onclick = () => { LV.pick = +b.dataset.i; lvDraw(LV.sets[LV.pick]); lvRender(); });
  lvDraw(LV.sets[LV.pick]);
  sizeRender();
}

function sizeRender() {
  const out = $("#szOut"); if (!out) return;
  const v = LV.sets[LV.pick];
  $("#lvPickName").textContent = v ? v.name : "";
  if (!v || v.entry == null || v.stop == null) {
    out.innerHTML = `<span class="muted" style="grid-column:1/-1">Pick a level set with a stop to size it.</span>`;
    return;
  }
  const eq = Math.max(+$("#szEq").value || 0, 0), risk = Math.max(+$("#szRisk").value || 0, 0), lev = Math.max(+$("#szLev").value || 1, 1);
  const stopFrac = Math.abs(v.entry - v.stop) / v.entry;
  const riskUsdt = eq * risk / 100;
  const notional = stopFrac > 0 ? riskUsdt / stopFrac : 0;
  const qty = notional / v.entry, margin = notional / lev;
  const rr = v.target != null ? Math.abs(v.target - v.entry) / Math.abs(v.entry - v.stop) : null;
  const win = v.target != null ? riskUsdt * rr : null;
  const needLev = eq > 0 ? notional / eq : 0;
  const rows = [
    ["Risk if the stop fills", `<b class="big down">−${riskUsdt.toFixed(2)} USDT</b>`],
    ["Stop distance", `${(stopFrac * 100).toFixed(2)}%`],
    ["Position size", `<b class="big">${notional.toFixed(2)} USDT</b>`],
    ["= coins", `${qty.toPrecision(6)} ${esc(base())}`],
    ["Margin at " + lev + "×", `${margin.toFixed(2)} USDT`],
  ];
  if (rr) rows.push(["At target", `<span class="up">+${win.toFixed(2)} USDT</span> · ${rr.toFixed(2)} R`]);
  if (notional < 5) rows.push(["⚠ Below Binance minimum", `<span class="warn">${notional.toFixed(2)} &lt; ~5 USDT</span>`]);
  if (needLev > lev) rows.push(["⚠ Needs leverage", `<span class="warn">${needLev.toFixed(1)}× for this size</span>`]);
  out.innerHTML = rows.map(([k, val]) => `<span>${k}</span><span>${val}</span>`).join("");
}

function toolBtn() {
  const b = $("#toolBtn"); if (!b) return;
  b.classList.toggle("on", !!LV.tool);
  b.textContent = LV.tool === "entry" ? "⊹ click the entry" : LV.tool === "stop" ? "⊹ now click the stop" : "⊹ Trade tool";
}

function barClock() {
  const el = $("#barClock"); if (!el || !M.bars.length) return;
  const sec = TF_SEC[M.tf] || 3600, last = M.bars.at(-1);
  const left = last.time + sec - Math.floor(Date.now() / 1000);
  const p = (x) => String(Math.max(x, 0)).padStart(2, "0");
  const txt = left > 0 ? (left >= 3600 ? `${Math.floor(left / 3600)}:${p(Math.floor(left / 60) % 60)}:${p(left % 60)}`
                                       : `${p(Math.floor(left / 60))}:${p(left % 60)}`) : "closing…";
  el.innerHTML = `<b>${esc(txt)}</b>${M.tf} bar close`;
}

/* ================================================================ drawers (fold / unfold cards) */
const BOPEN = new Set();          // drawers the viewer has unfolded (kept across refreshes)
function botToggle(h) {
  const el = h.parentElement, id = el.dataset.id, open = !BOPEN.has(id);
  open ? BOPEN.add(id) : BOPEN.delete(id); el.classList.toggle("open", open); h.setAttribute("aria-expanded", open);
}
["#scanDrawers", "#incCards", "#stratDrawers"].forEach((s) => {
  $(s).onclick = (e) => { const h = e.target.closest(".pick-top"); if (h) botToggle(h); };
  $(s).onkeydown = (e) => { const h = e.target.closest(".pick-top"); if (h && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); botToggle(h); } };
});
/* ================================================================ shell */
function tip(e, html) { const t = $("#tip"); if (!e) { t.style.display = "none"; return; } t.innerHTML = html; t.style.display = "block";
  t.style.left = Math.min(e.clientX + 14, innerWidth - 290) + "px"; t.style.top = (e.clientY + 14) + "px"; }
function conn(ok, txt) { const c = $("#conn"); c.className = "conn " + (ok ? "ok" : "bad"); c.querySelector("b").textContent = txt || (ok ? "live" : "offline"); }
const built = new Set();
function showView(v) {
  try { history.replaceState(null, "", "#" + v); } catch (e) {}      /* a reload comes back to this tab */
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === v));
  $$(".view").forEach((x) => x.classList.toggle("active", x.id === "view-" + v));
  if (v === "live") { liveView(); return; }            // always fresh: real money
  if (v === "today") { todayView(); return; }
  if (v === "switcher") { loadSwitcher().catch((e) => $("#swStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
    loadDelist().catch((e) => $("#dlStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`); return; }
  if (v === "scalps") { loadScalps().catch((e) => $("#scStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`); return; }
  if (v === "support") { loadSupport().catch((e) => $("#spStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`); return; }
  if (built.has(v)) return; built.add(v);
  if (v === "strategies") loadStrategies().catch((e) => $("#majorsCards").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
  if (v === "fit") loadFit().catch((e) => $("#fitStrip").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
  if (v === "incubator") loadIncubator().catch((e) => $("#incCards").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
  if (v === "bearlab") loadBearLab().catch((e) => $("#blCards").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
  if (v === "research") loadResearch().catch((e) => $("#resKpis").innerHTML = `<div class="empty">Could not load: ${e.message}</div>`);
}
function applyTheme() {
  allCharts.forEach((c) => c.applyOptions({ layout: { background: { type: "solid", color: "transparent" }, textColor: css("--text-secondary") },
    grid: { vertLines: { color: css("--grid") }, horzLines: { color: css("--grid") } }, rightPriceScale: { borderColor: css("--border") }, timeScale: { borderColor: css("--border") } }));
  S.candle.applyOptions({ upColor: css("--up"), downColor: css("--down"), wickUpColor: css("--up"), wickDownColor: css("--down") });
  [["ema20", "--series-1"], ["ema50", "--series-2"], ["ema200", "--series-7"], ["bbU", "--series-4"], ["bbM", "--series-4"], ["bbL", "--series-4"],
   ["vwap", "--series-5"], ["donU", "--series-3"], ["donL", "--series-3"], ["trend", "--series-7"], ["rsi", "--series-7"], ["macd", "--series-1"], ["macdS", "--series-2"]]
    .forEach(([k, v]) => S[k].applyOptions({ color: css(v) }));
  if (M.bars.length) { paintAll(); }
  if (built.has("research")) scatter();
}

function init() {
  try { const t = localStorage.getItem("ql-theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
  try { const c = localStorage.getItem("ql-cell"); if (c) document.documentElement.dataset.cell = c; } catch (e) {}
  fetch("/api/today").then((r) => r.json()).then((d) => { const c = d && d.condition && d.condition.cell;     /* market colour for every tab */
    if (c) { document.documentElement.dataset.cell = c; try { localStorage.setItem("ql-cell", c); } catch (e) {} } }).catch(() => {});
  buildMarketCharts();
  $$(".tab").forEach((t) => t.onclick = () => showView(t.dataset.view));
  $("#themeBtn").onclick = () => { const r = document.documentElement; r.dataset.theme = r.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("ql-theme", r.dataset.theme); } catch (e) {} applyTheme(); };
  $$("#tfSeg button").forEach((b) => b.onclick = () => selectSymbol(M.sym, b.dataset.tf));
  $$("#indToggles input[data-sig]").forEach((i) => i.onchange = () => { M.sig[i.dataset.sig] = i.checked; paintMarkers(); sigPanel(); activeInd(); });
  $$("#indToggles input[data-ind]").forEach((i) => i.onchange = () => { M.on[i.dataset.ind] = i.checked; paintAll(); legend(M.bars.length - 1); activeInd(); });
  $$("#indToggles input[data-pane]").forEach((i) => i.onchange = () => { $(`.pane[data-pane="${i.dataset.pane}"]`).classList.toggle("hidden", !i.checked); activeInd(); });
  const menu = $("#indToggles");
  $("#indBtn").onclick = (e) => { e.stopPropagation(); const r = e.currentTarget.getBoundingClientRect();
    menu.style.left = r.left + "px"; menu.style.top = (r.bottom + 6) + "px"; menu.classList.toggle("open"); };
  document.addEventListener("click", (e) => { if (!menu.contains(e.target)) menu.classList.remove("open"); });
  activeInd();
  $("#lvBtn").onclick = () => { LV.on = !LV.on; $("#lvBtn").classList.toggle("on", LV.on); lvDraw(LV.sets[LV.pick]); };
  setInterval(() => { if ($("#view-markets").classList.contains("active")) drawVP(); }, 900);
  ["#szEq", "#szRisk", "#szLev"].forEach((id) => $(id) && $(id).addEventListener("input",
    () => { sizeRender(); tradeBox(LV.sets[LV.pick]); }));
  $("#toolBtn").onclick = () => { LV.tool = LV.tool ? null : "entry"; LV.draft = null; toolBtn(); };
  document.addEventListener("keydown", (e) => {
    if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName) || e.ctrlKey || e.metaKey || e.altKey) return;
    if (!$("#view-markets").classList.contains("active")) return;
    const tf = { "1": "15m", "2": "1h", "3": "4h", "4": "1d" }[e.key];
    if (tf) { selectSymbol(M.sym, tf); return; }
    if (e.key === "l" || e.key === "L") $("#lvBtn").click();
    else if (e.key === "t" || e.key === "T") $("#toolBtn").click();
    else if (e.key === "Escape" && LV.tool) { LV.tool = null; LV.draft = null; toolBtn(); }
    else if (e.key === "[" || e.key === "]") {              /* step through the level sets */
      if (!LV.sets.length) return;
      LV.pick = (LV.pick + (e.key === "]" ? 1 : LV.sets.length - 1)) % LV.sets.length; lvRender();
    }
  });
  setInterval(barClock, 1000);
  window.addEventListener("resize", () => setTimeout(drawVP, 120));
  $("#logBtn").onclick = () => { M.log = !M.log; $("#logBtn").classList.toggle("on", M.log);
    main.priceScale("right").applyOptions({ mode: M.log ? LW.PriceScaleMode.Logarithmic : LW.PriceScaleMode.Normal }); };
  $("#eqLog").onclick = () => { eqLogOn = !eqLogOn; $("#eqLog").classList.toggle("on", eqLogOn);
    eqChart && eqChart.priceScale("right").applyOptions({ mode: eqLogOn ? LW.PriceScaleMode.Logarithmic : LW.PriceScaleMode.Normal }); };
  $("#search").oninput = (e) => { TICK.q = e.target.value.toUpperCase().trim(); renderWatch(); };
  $("#search").onkeydown = (e) => { if (e.key === "Enter") { const f = $(".wrow"); if (f) selectSymbol(f.dataset.s); } };
  $$("#watchSort button").forEach((b) => b.onclick = () => { $$("#watchSort button").forEach((x) => x.classList.toggle("on", x === b)); TICK.sort = b.dataset.sort; renderWatch(); });
  $("#watchList").onclick = (e) => { const r = e.target.closest(".wrow"); if (r) selectSymbol(r.dataset.s); };
  $("#resSearch").oninput = (e) => { RES.q = e.target.value.toLowerCase(); table(); };
  $$("#resStage button").forEach((b) => b.onclick = () => { $$("#resStage button").forEach((x) => x.classList.toggle("on", x === b)); RES.stage = b.dataset.st; table(); });
  $("#scanBtn").onclick = async () => { await api("/api/scan/run", { method: "POST", headers: { "X-Quantlab": "1" } }); SCAN.running = true; renderScan(); setTimeout(loadScan, 3000); };
  window.addEventListener("resize", () => built.has("research") && scatter());
  setInterval(() => { $("#clock").textContent = new Date().toTimeString().slice(0, 8); }, 1000);
  loadTickers().then(loadMarket); loadScan();
  setInterval(loadTickers, 10000); setInterval(marketPanel, 15000);
  setInterval(() => { if (!SCAN.running) loadScan(); }, 60000);       /* pick up the hourly auto-scan */
  $$("#fwdFilter button").forEach((b) => b.onclick = () => { $$("#fwdFilter button").forEach((x) => x.classList.toggle("on", x === b)); FWD.filter = b.dataset.f; renderForward(); });
  const h = location.hash.slice(1);                      /* Today is the landing view, unless a reload had another tab */
  showView($(`.tab[data-view="${h}"]`) ? h : "today");
  /* the browser slows timers in a hidden tab; on return, catch up at once instead of waiting for the next tick */
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    loadTickers().catch(() => {}); marketPanel();
    const v = ($(".tab.active") || {}).dataset?.view;
    if (v === "live") loadTrader().catch(trFail);
    if (v === "today") todayView();
  });
}
init();
