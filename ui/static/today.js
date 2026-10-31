/* ================================================================ TODAY
   Market condition, live tape, market map, strategy fit, feed and the journal. Information only. */
(() => {
  const q = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const sg = (v, d = 2) => (v > 0 ? "+" : "") + Number(v).toFixed(d);
  const fmtP = (p) => p >= 1000 ? p.toLocaleString("en-US", { maximumFractionDigits: 1 }) : p >= 1 ? p.toFixed(p >= 100 ? 2 : 4) : p.toPrecision(4);
  const CELL_COL = { "Bull-Calm": "#22d3a6", "Bull-Wild": "#f59e0b", "Bear-Calm": "#818cf8", "Bear-Wild": "#f43f5e" };
  const STATUS = { green: "Validated", yellow: "Conditional", research: "In research" };
  const FIT = { good: "Fits today", mixed: "Mixed", avoid: "Avoid today", cash: "In cash", none: "Not built", unknown: "Untested" };
  let T = null, timer = null, ws = null, mood = null, wsSeen = 0, pollTimer = null;

  // every tab takes today's market colour (theme.css); remembered so a reload starts in the right colour
  function setCell(cell) { document.documentElement.dataset.cell = cell; try { localStorage.setItem("ql-cell", cell); } catch (e) {} }

  async function load() {
    const r = await fetch("/api/today"); const d = await r.json();
    if (d.error) throw new Error(d.error);
    T = d; render();
  }

  function greet() {
    const h = new Date().getHours();
    const part = h < 5 ? "Good night" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    const day = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
    return `${part}, Michael · ${day}`;
  }

  function render() {
    const c = T.condition, f = T.feeds, v = q("#view-today");
    v.dataset.cell = c.cell;
    setCell(c.cell);
    const [a, b] = c.cell.split("-");
    q("#tdGreet").textContent = greet();
    q("#tdCell").textContent = `${a} · ${b}`;
    q("#tdCellText").textContent = c.text;
    q("#tdSince").innerHTML = `<span>since <b>${c.since}</b> · day <b>${c.days}</b></span><span>last daily close <b>${c.as_of}</b></span>` +
      `<span>live bot <b>${T.live_on ? "running" : "parked"}</b></span>`;
    const volPct = Math.min(100, c.vol_ratio / 2 * 100), br = f.breadth.pct;
    q("#tdGauges").innerHTML = [
      ["BTC", `<span id="tdBtc" data-v="${btcNow(f, c)}">${fmtP(btcNow(f, c))}</span>`, `live price · last daily close ${fmtP(c.btc_close)}`, ""],
      ["20-day trend", `<span class="${c.ret20 > 0 ? "up" : "down"}">${sg(c.ret20, 1)}%</span>`, c.ret20 > 0 ? "above 0 → bull" : "at or below 0 → bear",
        `<div class="td-bar"><span style="width:${Math.min(100, Math.abs(c.ret20) / 25 * 100)}%"></span></div>`],
      ["Volatility", `${(c.vol_ratio * 100).toFixed(0)}%`, "of its yearly median · 100% = wild line",
        `<div class="td-bar"><span style="width:${volPct}%"></span><em style="left:50%"></em></div>`],
      ["Breadth", `${br}%`, `of top ${f.breadth.of} coins up 24h`, `<div class="td-bar"><span style="width:${br}%"></span><em style="left:50%"></em></div>`],
    ].map(([k, val, d, extra]) => `<div class="td-g"><div class="k">${k}</div><div class="v">${val}</div><div class="d">${d}</div>${extra}</div>`).join("");
    renderMap(c);
    renderTape(f.tape);
    q("#tdSugs").innerHTML = T.suggestions.map((s) => `<li class="${s.tone}"><span class="ic">${{ good: "✦", warn: "▲", info: "●", muted: "i" }[s.tone] || "●"}</span><span>${esc(s.text)}</span></li>`).join("");
    q("#tdStrats").innerHTML = T.strategies.map((s) => `
      <div class="td-s ${s.today.level}">
        <div class="tl"><span class="td-badge ${s.status}"><i></i>${STATUS[s.status] || s.status}</span><span class="td-pill ${s.today.level}">${FIT[s.today.level] || s.today.level}</span></div>
        <div class="nm">${esc(s.name)}</div>
        <div class="meta">${esc(s.style)} · ${esc(s.horizon)}</div>
        <div class="why">${esc(s.today.why)}</div>
        <div class="ev">${esc(s.evidence)}<br>${esc(s.status_text)}</div>
      </div>`).join("");
    renderFeed(f);
    renderJournal();
    q("#tdAt").textContent = "updated " + new Date(T.generated).toLocaleTimeString();
  }

  /* ---- market map: x = BTC 20-day return, y = volatility vs yearly median (log scale), last 90 days ---- */
  function renderMap(c) {
    const W = 380, H = 270, P = { l: 30, r: 12, t: 14, b: 26 };
    const xs = c.trail.map((p) => p.x), lim = Math.max(15, Math.ceil(Math.max(...xs.map(Math.abs)) / 5) * 5 + 5);
    const X = (x) => P.l + (Math.max(-lim, Math.min(lim, x)) + lim) / (2 * lim) * (W - P.l - P.r);
    const Y = (y) => { const ly = Math.log2(Math.max(0.35, Math.min(2.8, y))); return P.t + (1 - (ly + 1.5) / 3) * (H - P.t - P.b); };
    const x0 = X(0), y1 = Y(1);
    const quad = (cell, x, y, w, h) => `<rect class="q${c.cell === cell ? " on" : ""}" x="${x}" y="${y}" width="${w}" height="${h}" fill="${CELL_COL[cell]}" rx="6"/>`;
    const lab = (cell, x, y, anchor) => `<text class="ql${c.cell === cell ? " on" : ""}" x="${x}" y="${y}" text-anchor="${anchor}">${cell.replace("-", " · ").toUpperCase()}</text>`;
    let s = quad("Bear-Wild", P.l, P.t, x0 - P.l, y1 - P.t) + quad("Bull-Wild", x0, P.t, W - P.r - x0, y1 - P.t) +
      quad("Bear-Calm", P.l, y1, x0 - P.l, H - P.b - y1) + quad("Bull-Calm", x0, y1, W - P.r - x0, H - P.b - y1);
    s += lab("Bear-Wild", P.l + 8, P.t + 14, "start") + lab("Bull-Wild", W - P.r - 8, P.t + 14, "end") +
      lab("Bear-Calm", P.l + 8, H - P.b - 8, "start") + lab("Bull-Calm", W - P.r - 8, H - P.b - 8, "end");
    s += `<line class="ax" x1="${x0}" y1="${P.t}" x2="${x0}" y2="${H - P.b}"/><line class="ax" x1="${P.l}" y1="${y1}" x2="${W - P.r}" y2="${y1}"/>`;
    s += `<text class="axl" x="${P.l}" y="${H - 8}">${-lim}%</text><text class="axl" x="${x0}" y="${H - 8}" text-anchor="middle">0</text>` +
      `<text class="axl" x="${W - P.r}" y="${H - 8}" text-anchor="end">+${lim}%</text>` +
      `<text class="axl" x="${P.l - 4}" y="${y1 + 3}" text-anchor="end">1×</text><text class="axl" x="${P.l - 4}" y="${Y(2) + 3}" text-anchor="end">2×</text>` +
      `<text class="axl" x="${P.l - 4}" y="${Y(0.5) + 3}" text-anchor="end">.5×</text>`;
    const pts = c.trail.map((p) => [X(p.x), Y(p.y), p]);
    for (let i = 1; i < pts.length; i++) {
      const o = 0.08 + 0.75 * (i / pts.length);
      s += `<line x1="${pts[i - 1][0].toFixed(1)}" y1="${pts[i - 1][1].toFixed(1)}" x2="${pts[i][0].toFixed(1)}" y2="${pts[i][1].toFixed(1)}" stroke="var(--m1)" stroke-opacity="${o.toFixed(2)}" stroke-width="1.4" stroke-linecap="round"/>`;
    }
    pts.forEach(([x, y, p], i) => {
      if (i === pts.length - 1) return;
      s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${i % 7 === 0 ? 2.2 : 1.4}" fill="${CELL_COL[p.cell]}" opacity="${(0.25 + 0.6 * i / pts.length).toFixed(2)}"><title>${p.day} · ${p.cell.replace("-", " + ")} · 20d ${sg(p.x, 1)}% · vol ${(p.y * 100).toFixed(0)}%</title></circle>`;
    });
    const [nx, ny, np] = pts[pts.length - 1];
    s += `<circle class="pulse" cx="${nx}" cy="${ny}" r="5" fill="var(--m1)"/><circle class="now" cx="${nx}" cy="${ny}" r="5.5" fill="var(--m3)" stroke="var(--m1)" stroke-width="2"><title>Today (${np.day}) · ${np.cell.replace("-", " + ")}</title></circle>`;
    const svg = q("#tdMap");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = s;
  }

  /* live BTC: the tape's last price (REST, refreshed with the page), not the last daily close */
  function btcNow(f, c) { const b = (f.tape || []).find((t) => t.s === "BTCUSDT"); return b ? b.last : c.btc_close; }

  /* ---- ticker tape with live prices (Binance public websocket, REST fallback every 10 s) ---- */
  function renderTape(tape) {
    const one = tape.map((t) => `<span class="td-tick" data-s="${t.s}"><b>${t.s.replace("USDT", "")}</b><span class="p">${fmtP(t.last)}</span><span class="c ${t.chg >= 0 ? "up" : "down"}">${sg(t.chg)}%</span></span>`).join("");
    q("#tdTape").innerHTML = one + one;                                   // doubled for a seamless loop
    if (!ws && tape.length) openWs(tape.map((t) => t.s));
  }
  function openWs(syms) {
    try {
      ws = new WebSocket("wss://fstream.binance.com/stream?streams=" + syms.map((s) => s.toLowerCase() + "@miniTicker").join("/"));
    } catch (e) { ws = null; return; }
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data).data; if (!m) return;
      wsSeen = Date.now(); applyTick(m.s, +m.c, (+m.c / +m.o - 1) * 100);
    };
    ws.onclose = () => { ws = null; setTimeout(() => T && q("#view-today").classList.contains("active") && openWs(syms), 5000); };
  }
  function applyTick(s, last, chg) {
    document.querySelectorAll(`.td-tick[data-s="${s}"]`).forEach((el) => {
      const p = el.querySelector(".p"), prev = +p.dataset.v || last;
      p.textContent = fmtP(last); p.dataset.v = last;
      if (last !== prev) { p.classList.add(last > prev ? "flash-up" : "flash-down"); setTimeout(() => p.classList.remove("flash-up", "flash-down"), 60); }
      const c = el.querySelector(".c"); c.textContent = sg(chg) + "%"; c.className = "c " + (chg >= 0 ? "up" : "down");
    });
    if (s === "BTCUSDT") {
      const b = q("#tdBtc"); if (!b) return;
      const prev = +b.dataset.v || last; b.textContent = fmtP(last); b.dataset.v = last;
      const box = b.parentElement;
      if (last !== prev) { box.classList.add(last > prev ? "flash-up" : "flash-down"); setTimeout(() => box.classList.remove("flash-up", "flash-down"), 60); }
    }
  }
  async function pollPrices() {
    if (!T || !q("#view-today").classList.contains("active") || Date.now() - wsSeen < 15000) return;
    try {
      const rows = await (await fetch("/api/tickers")).json();
      const want = new Set(T.feeds.tape.map((t) => t.s));
      rows.forEach((r) => { if (want.has(r.symbol)) applyTick(r.symbol, r.last, r.chg); });
    } catch (e) { /* next poll */ }
  }

  /* ---- feed ---- */
  function renderFeed(f) {
    const mx = Math.max(...f.gainers.map((x) => Math.abs(x.chg)), ...f.losers.map((x) => Math.abs(x.chg)), 1);
    const row = (x, col, val) => `<div class="td-fr"><b>${esc(x.s)}</b><div class="bar"><span style="width:${Math.min(100, Math.abs(x.chg) / mx * 100)}%;background:${col}"></span></div><span class="n">${val}</span></div>`;
    const fmx = Math.max(...f.funding_high.map((x) => Math.abs(x.funding)), ...f.funding_low.map((x) => Math.abs(x.funding)), 0.0001);
    const frow = (x) => `<div class="td-fr"><b>${esc(x.s)}</b><div class="bar"><span style="width:${Math.min(100, Math.abs(x.funding) / fmx * 100)}%;background:${x.funding >= 0 ? "var(--warning)" : "var(--accent)"}"></span></div><span class="n">${sg(x.funding, 3)}%</span></div>`;
    q("#tdFeed").innerHTML = `
      <div><div class="lbl"><span>Breadth · top ${f.breadth.of}</span><span>${f.breadth.up} up · ${f.breadth.of - f.breadth.up} down</span></div>
        <div class="td-breadth"><span style="width:${f.breadth.pct}%"></span></div></div>
      <div><div class="lbl"><span>Leading · 24h</span><span>top 60 by volume</span></div>${f.gainers.map((x) => row(x, "var(--up)", `<span class="up">${sg(x.chg, 1)}%</span>`)).join("")}</div>
      <div><div class="lbl"><span>Lagging · 24h</span></div>${f.losers.map((x) => row(x, "var(--down)", `<span class="down">${sg(x.chg, 1)}%</span>`)).join("")}</div>
      <div><div class="lbl"><span>Funding extremes · per 8h</span><span>median ${sg(f.avg_funding_pct, 3)}%</span></div>${f.funding_high.map(frow).join("")}${f.funding_low.map(frow).join("")}</div>`;
  }

  /* ---- journal ---- */
  function renderJournal() {
    if (!q("#tdMoods").children.length) {
      q("#tdMoods").innerHTML = Object.entries(T.moods).map(([k, e]) => `<button class="td-mood" data-mood="${k}">${e} ${k}</button>`).join("");
    }
    let lastDay = "", h = "";
    for (const e of T.journal) {
      const d = new Date(e.t), day = d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
      if (day !== lastDay) { h += `<li class="day">${day}</li>`; lastDay = day; }
      const dot = e.kind === "condition" && e.cell ? ` style="--cdot:${CELL_COL[e.cell]}"` : "";
      const md = e.kind === "note" && e.mood ? `<span class="md" title="${esc(e.mood)}">${T.moods[e.mood] || ""}</span>` : "";
      h += `<li class="e ${esc(e.kind)}"${dot}><span class="when">${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" })}</span>${md}<span class="txt">${esc(e.text)}</span></li>`;
    }
    q("#tdTl").innerHTML = h || `<li class="day">No entries yet</li>`;
  }

  async function save() {
    const ta = q("#tdNote"), text = ta.value.trim(); if (!text) return;
    const btn = q("#tdSave"); btn.disabled = true; q("#tdJmsg").textContent = "";
    try {
      const r = await fetch("/api/journal", { method: "POST", headers: { "Content-Type": "application/json", "X-Quantlab": "1" }, body: JSON.stringify({ text, mood }) });
      const j = await r.json(); if (j.error) throw new Error(j.error);
      T.journal.unshift(j); ta.value = ""; mood = null;
      document.querySelectorAll(".td-mood").forEach((b) => b.classList.remove("on"));
      renderJournal();
    } catch (e) { q("#tdJmsg").textContent = "Not saved: " + e.message; }
    finally { btn.disabled = !q("#tdNote").value.trim(); }
  }

  function wire() {
    q("#tdNote").addEventListener("input", (e) => { q("#tdSave").disabled = !e.target.value.trim(); });
    q("#tdNote").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) save(); });
    q("#tdSave").onclick = save;
    q("#tdMoods").onclick = (e) => {
      const b = e.target.closest(".td-mood"); if (!b) return;
      mood = mood === b.dataset.mood ? null : b.dataset.mood;
      document.querySelectorAll(".td-mood").forEach((x) => x.classList.toggle("on", x.dataset.mood === mood));
    };
    q("#tdRefresh").onclick = () => load().catch(fail);
  }
  const fail = (e) => { q("#tdCellText").textContent = "Could not load today's data: " + e.message; };

  window.todayView = () => {
    load().catch(fail);
    clearInterval(timer);
    timer = setInterval(() => { if (q("#view-today").classList.contains("active")) load().catch(() => {}); }, 60000);
    if (!pollTimer) pollTimer = setInterval(pollPrices, 10000);
  };
  wire();
})();
