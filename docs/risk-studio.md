# Risk Studio

The **Observed defaults** panel contains a reproducible UCI credit-card study with 30,000 observed records and 6,636 defaults. It shows model comparisons on a separate holdout, calibration, sample stability, source lineage, and downloadable predictions. [Run and inspect the case study](public-credit-case-study.md). These historical retail observations do not supply institutional trades, financial statements, dated portfolio returns, or LGDs.

Risk Studio's dashboard is available at `/` and `/risk-studio`. The workbench at `/workbench` supports data preparation, modeling, validation, and strategy development. Alongside the public credit study, the dashboard provides three views for an imported institutional portfolio:

| View | Calculations |
| --- | --- |
| Credit review | Financial ratios, visible warning thresholds, indicative rating bands, and a summary per counterparty. |
| Exposure | Positive MTM, collateral, an illustrative potential future exposure add-on, credit limit utilization, breaches, and movement against a previous exposure snapshot. |
| Methodology | Historical one-day 99% VaR, 99% expected shortfall, rolling backtest exceptions, an illustrative initial margin buffer, and fixed product stress scenarios. |

The public credit study is populated by default. Institutional portfolio analysis appears after a JSON import; no live trade or counterparty feed, approved internal model, pricing engine, SIMM implementation, or regulatory capital methodology is included. Imported JSON is analyzed in memory and is not saved. Exported JSON contains the supplied inputs and calculated result. A printable HTML analyst report is available after an analysis.

The dashboard retrieves daily EUR/USD, EUR/GBP, EUR/JPY, and EUR/INR reference rates from the [European Central Bank Data Portal](https://data.ecb.europa.eu/data/datasets/EXR). The panel shows the observation date and retrieval time, refreshes every 15 minutes, and reports an unavailable state if the public API cannot be reached. These reference rates are not executable quotes and do not automatically alter user supplied portfolio calculations.

## Input and API

Download an empty input skeleton from **Manage data** in Risk Studio. The input object has `counterparties` and `positions` arrays, plus an optional `margin_multiplier`. Each counterparty supplies financial statement values, collateral, a credit limit, and an optional `previous_net_exposure`. Each position supplies a counterparty, product, notional, mark to market, daily volatility percentage, horizon in days, and at least 30 historical daily returns in percent. Returns are aligned by array position and all amounts are assumed to share one reporting currency.

`POST /api/risk-studio/analyze` accepts that JSON object. It returns the credit reviews, exposure table, portfolio risk series, backtest, stress results, assumptions, and summary. Invalid or non-finite inputs are rejected. The app's existing local access guard applies to this route.

## Calculation notes

- **Credit screen:** Liquidity, net debt to EBITDA, interest coverage, net margin, operating cash flow, and debt to assets are assessed with visible threshold flags. Bands A, BBB, BB, and B summarize the number of flags. They are not approved credit ratings.
- **Exposure:** Gross exposure is positive MTM. The potential future exposure proxy adds `1.96 × absolute notional × daily volatility × sqrt(horizon / 252)` for each position. Net exposure subtracts collateral with a floor of zero. Limit utilization uses collateralized potential future exposure. Day movement compares current and supplied previous net exposure.
- **Historical risk:** One-day portfolio P&L is the sum of notional times aligned daily return. VaR is the 99th percentile of losses; expected shortfall averages losses at or above that threshold. Indicative margin is VaR times the selected buffer. Backtesting compares each loss after day 30 with a VaR estimated from the preceding 30 observations.
- **Stress:** Fixed illustrative shocks are applied by product. These are not calibrated regulatory scenarios.

## Production integration boundary

A production implementation needs approved schemas and source systems for financial statements, trades and valuations, collateral and limits, and dated market histories. It also needs currency conversion, legal netting sets, collateral eligibility and haircuts, trade pricing, model governance and calibration, role based access, persistent audit history, reviewed reports, and independent validation. The current JSON import is a prototype input contract for those future integrations, not a production feed.
