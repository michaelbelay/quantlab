# Candidate reasons — for choosing what, if anything, ends the pause

**Dated 2026-09-29. Written under `PAUSE_NOTE_2026-09-29.md` (in effect, SHA-256 `401ded2b…bf76`), §1d.**
**This is a list of possibilities, not a reason file and not a test.** No data was loaded, queried or looked at to write it. Nothing here ends the pause: that takes a dated `REASON_<date>.md`, written by Michael, naming one candidate and answering the bar question, which Claude then checks in writing.

**Why these five:** every test so far was a form of *predicting direction* (breakouts, relative strength). Combining strategies only helps if each has its own edge — five break-even ideas together still break even — so the useful search is for edges with a **different cause**. Each candidate below names its cause, what is genuinely new, the data it needs, how it would fail, and how it stands against §1d.

---

## 1. Funding carry (hedged)

- **Cause:** perpetual funding transfers money from the crowded side to the other side. Demand for leveraged long exposure is persistently one-sided in crypto, so longs tend to pay shorts. A position that is **short the perpetual and long the same coin on spot** has little price exposure and collects the funding.
- **What's new here:** it earns a payment instead of predicting direction. Nothing in tests 1-4 did this.
- **Data needed:** funding history (already local for 679 contracts, 2021-2026), **spot prices** for the hedge leg (public Binance spot archive — not downloaded; availability per coin to be checked), spot fees.
- **Manual fit:** good. Positions change when the funding regime changes — days to weeks, not minutes.
- **How it dies:** funding turns negative and stays there; the four fee legs (spot + perp, in and out) eat a thin payment; the perp-spot price gap widens against you; the short perp leg gets margin-called in a sharp rally if it isn't funded with enough collateral; exchange risk on both legs.
- **§1d:** new mechanism with a stated cause. **Bar test: yes** — it would be worth testing even if the last five tests had been profitable, because it is a different return source, not a better version of them.
- **Contamination to disclose:** while checking the rotation benchmark, Claude printed yearly average funding for the top-40 basket (about +21% in 2021, about -22% in 2025). A reason file must not lean on those numbers.

## 2. Grid / range trading

- **Cause:** prices spend long stretches moving sideways inside a range. A ladder of resting buy orders below and sell orders above collects each swing, earning maker fees rather than paying taker fees. This is the mechanism behind Gunbot-style grids.
- **What's new here:** tests 1-4 traded single entries with a stop. A grid holds **inventory across many small orders** and has no directional view. Mean-reversion *signals* failed in this project earlier, but a grid is not a signal — it is closer to selling volatility.
- **Data needed:** 1-minute bars to simulate fills honestly (**already local for the 30 desk coins, 2024-09 .. 2026-09**; a fill needs price to trade *through* a level, as in test 3).
- **Manual fit:** poor. A grid means many orders, refreshed constantly — in practice it needs a bot, which the pause keeps off the live account. A test could still establish whether the edge exists before that question comes up.
- **How it dies:** a strong trend. The grid keeps buying into a falling market (or selling into a rising one) and ends up holding a large losing position. Many small wins, then one large loss — the payoff shape that looks consistent right until it isn't. **This is also why grid screenshots look so steady.**
- **§1d:** new mechanism with a stated cause. **Bar test: yes**, with the caveat that its payoff shape needs a drawdown gate at least as strict as test 4's.
- **Contamination:** none known.

## 3. Liquidation and open-interest events

- **Cause:** when leveraged positions are force-closed in bulk, the selling (or buying) is involuntary and price-insensitive, so it can overshoot. After the forced flow ends, price may partly snap back.
- **What's new here:** it needs **new data**: liquidation volumes and fine-grained open-interest changes, which tests 1-4 couldn't see. (Test 1's "flush reversal" used a price-and-volume proxy with an OI filter, at 15m/30m only; it was near zero before costs.)
- **Data needed:** a liquidation history. The GreenAgent recorder was noted as collecting open interest and liquidations since 2025-10 (about 11 months, 30 Bybit symbols) — **availability unverified today**: no database file was found in the GreenAgent folder on 2026-09-29. Binance's 5-minute open interest is local for the 30 desk coins since 2024-09.
- **Manual fit:** medium. Events are sudden; a person would act within an hour, not seconds.
- **How it dies:** too little history (11 months is one or two regimes); the snap-back is captured by faster players before a manual entry; the flush continues (catching a falling knife).
- **§1d:** new dataset that changes what can be measured — **but only if the data exists and covers enough time**. Also a possible falsification test of test 1's flush-reversal result at a different horizon. **Bar test: yes** in principle.
- **Contamination:** test 1's flush-reversal results (family L) have been seen.

## 4. Token unlocks and scheduled supply events

- **Cause:** large token unlocks release new supply on a known date. If recipients sell, there is predictable pressure; if the market prices it in early, the pressure comes before the date.
- **What's new here:** event-driven and **scheduled in advance** — the only candidate where the timing is known before the move, not detected from price.
- **Data needed:** a historical unlock calendar (dates and sizes as a share of circulating supply). **No source in hand;** public trackers exist but historical coverage and cost are unknown.
- **Manual fit:** very good — a calendar, days of notice.
- **How it dies:** the effect is already priced in and trades away; unlock sizes are too uneven to generalise; too few events per year for a sound test.
- **§1d:** new mechanism with a stated cause, and new data. **Bar test: yes.**
- **Contamination:** none known. (Project notes mention one unlock, XPL on 2026-09-25, as a universe exclusion reason; no returns were looked at.)

## 5. New listings

- **Cause:** a newly listed perpetual arrives with launch attention and often a small circulating float, followed by steady supply from unlocks and early holders. The hypothesis is a systematic drift after listing — direction to be stated in the reason file, not assumed.
- **What's new here:** an event signal defined by the listing date.
- **Data needed:** listing dates — **already known** for all 679 crypto contracts from the rotation data audit (first traded bar), plus their 1h prices.
- **Manual fit:** good — listings are announced.
- **How it dies:** survivorship in how listings are counted; the drift exists but can't be captured because newly listed contracts are thin and expensive to trade; shorts get squeezed.
- **§1d:** new mechanism — **but the weakest of the five on contamination.**
- **Contamination — must be disclosed and weighed:** the rotation benchmark showed the equal-weight alt basket (heavy in recent listings, dead coins included) losing about 90%. That result *suggests* a post-listing decline, which makes this candidate **partly derived from a number in test 4** (disqualifier 1). A reason file would have to show the cause stands without that number. **The bar test is doubtful:** would it have been proposed if test 4 had been profitable?

---

## Not candidates, and why

- **Copying a bot or signal channel's published results** (Gunbot configurations, Telegram signal groups): unverifiable, self-selected numbers — disqualifier 1 from outside the project.
- **DCA (buying fixed amounts on a schedule):** a way to spread entries, not an edge. It changes timing risk, not expected return.
- **Martingale / averaging down with growing size:** consistent small wins until one losing streak takes the account. Excluded on risk of ruin.
- **"Combine the strategies we already tested":** none has a validated edge; combining them adds no expectancy.

## Suggested order, for Michael's decision (not a decision)

| Rank | Candidate | Why |
|---|---|---|
| 1 | **Funding carry** | Clearest cause, genuinely different return source, fits a manual desk, most data public. Main work: spot data + hedge accounting. |
| 2 | **Grid / range** | Clear cause, data already local; the key question is whether its trend losses outweigh its range gains. Implementation would need automation later. |
| 3 | **Token unlocks** | Strong cause, perfect manual fit — **blocked on finding historical data.** |
| 4 | **Liquidations / OI** | **Blocked on verifying the data**, and the history may be too short. |
| 5 | **New listings** | Plausible, but contaminated by test 4; weakest against the bar. |

If a reason file names one of these, the next steps are the usual ones: Claude checks it against §1d in writing → a pre-registration is drafted and approved → a data audit → one run. **One candidate at a time**, each needing its own edge before any combination is considered.
