# Reason file — funding carry (TEMPLATE, not yet a reason)

**Template drafted by Claude on 2026-09-29 under `PAUSE_NOTE_2026-09-29.md` §1d. It becomes a reason file only when Michael fills in sections 2 and 4 in his own words, fills in section 6, and renames it `REASON_<date>_funding_carry.md`.** Claude then checks it against §1d in writing (section 7) before any pre-registration is drafted.

---

## 1. Candidate
**Funding carry (hedged)** — candidate 1 in `CANDIDATE_REASONS_2026-09-29.md`.

**§1d category claimed:** new mechanism with a stated cause.

## 2. The cause — why should this edge exist? *(Michael, in your own words)*

> *Write 3-6 sentences. Things to cover: who pays funding and why they keep paying it; why that payment should persist rather than disappear once people notice it; what the hedge removes and what risk it leaves; when you expect it NOT to work.*
>
> ___

## 3. What the idea is, mechanically (factual — filled in by Claude)
- When a coin's perpetual funding rate is positive, longs pay shorts every funding period (8 hours for most coins, 4 hours for some).
- Position: **short the perpetual + long the same amount of the coin on spot.** Price moves roughly cancel; the funding payments are the return.
- Exit when funding falls or turns negative, or on a rule fixed in the pre-registration.
- **Costs:** four fee legs (spot buy, perp sell, perp buy back, spot sell). At Binance base rates that is roughly spot 0.10% x 2 + perp taker 0.05% x 2 ≈ **0.30% round trip before slippage** — lower with maker orders or BNB fee discounts, higher on thin coins. A position must collect more than that in funding to break even.
- **Risks the hedge does not remove:** funding turning negative while held; the perpetual and spot prices drifting apart; the short perpetual leg needing margin in a sharp rally (it can be liquidated even though the spot leg gained); exchange/custody risk on both legs.

## 4. The bar question *(Michael, in your own words)*

> **"Would this still be worth running if the last five tests had all been profitable?"**
>
> *Answer yes or no, and say why. A good answer explains why this is a different source of return, not a response to the last five failing.*
>
> ___

## 5. Disclosures (factual — filled in by Claude)
- **Numbers already seen that touch this idea:** while checking the rotation benchmark on 2026-09-29, Claude printed yearly average funding for the top-40 alt basket — about **+21% in 2021** and about **-22% in 2025**. They come from a finished test (disqualifier 1). **This reason must not rely on them**, and the pre-registration must treat them as seen.
- **Data already local:** funding history for 679 crypto contracts, 2021-01 to 2026-09 (`user_data/rotation_data/*/funding.parquet`), downloaded for the rotation test; only the yearly averages above have been looked at.
- **Data not yet obtained:** spot prices for the hedge leg (public Binance spot archive; coverage per coin unknown).
- **Nothing else about funding returns has been computed or looked at.**

## 6. Signed
- Written by: ___ (Michael)
- Date: ___

## 7. Claude's check against §1d *(filled in after sections 2, 4 and 6)*
- Disqualifier 1 (a number from tests 1-4 or short-1h): ___
- Disqualifier 2 (a favourable regime): ___
- Disqualifier 3 (a parameter that won once): ___
- Qualifying category and whether it holds: ___
- Bar question — does the answer hold up: ___
- Objections, if any: ___
