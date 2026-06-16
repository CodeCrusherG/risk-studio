(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const money = (value) => Number.isFinite(value) ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value) : "—";
  const pct = (value) => Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
  const ratio = (value) => Number.isFinite(value) ? `${value.toFixed(2)}×` : "—";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
  const dialog = $("sourceDialog");
  let currentInputs = null;
  let currentAnalysis = null;
  let currentView = "study";

  function download(name, value) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function setError(message) {
    const box = $("sourceError");
    box.textContent = message || "";
    box.hidden = !message;
  }

  async function runAnalysis() {
    setError("");
    let inputs;
    try {
      const parsed = JSON.parse($("jsonInput").value);
      inputs = parsed.inputs || parsed;
    } catch {
      setError("Enter valid portfolio JSON.");
      return;
    }
    const token = document.body.dataset.localToken || "";
    const headers = { "Content-Type": "application/json" };
    if (token) headers["X-Marvis-Token"] = token;
    const button = $("runAnalysis");
    button.disabled = true;
    button.textContent = "Analyzing…";
    try {
      const response = await fetch("/api/risk-studio/analyze", { method: "POST", credentials: "same-origin", headers, body: JSON.stringify(inputs) });
      const data = await response.json();
      if (!response.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : "Analysis failed.");
      }
      currentInputs = inputs;
      currentAnalysis = data;
      render();
      dialog.close();
      showView("overview");
    } catch (error) {
      setError(error.message || "Analysis failed.");
    } finally {
      button.disabled = false;
      button.textContent = "Run analysis";
    }
  }

  async function loadMarketFeed() {
    $("marketFeedStatus").textContent = "UPDATING";
    try {
      const response = await fetch("/api/risk-studio/market-feed", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("ECB data could not be reached");
      const marketFeed = await response.json();
      $("marketRates").innerHTML = marketFeed.rates.map((rate) => `<div class="market-rate"><span>EUR / ${escapeHtml(rate.currency)}</span><strong>${rate.value.toLocaleString("en-US", { maximumFractionDigits: 4 })}</strong><small class="${rate.change_pct < 0 ? "negative" : "positive"}">${rate.change_pct >= 0 ? "+" : ""}${rate.change_pct.toFixed(2)}% vs prior day</small></div>`).join("");
      const latestDate = marketFeed.rates[0].date;
      $("marketFeedTime").textContent = `ECB observation ${latestDate} · refreshed ${new Date(marketFeed.retrieved_at).toLocaleTimeString()}`;
      $("marketFeedStatus").textContent = "ECB CONNECTED";
    } catch (error) {
      $("marketFeedStatus").textContent = "FEED UNAVAILABLE";
      $("marketRates").innerHTML = `<p class="empty">${escapeHtml(error.message)}. Portfolio analysis requires your own data.</p>`;
      $("marketFeedTime").textContent = "Last attempt: " + new Date().toLocaleTimeString();
    }
  }

  function renderChart(pnl) {
    const target = $("lossChart");
    if (!pnl?.length) { target.textContent = "No historical P&L available."; return; }
    const values = pnl.slice(-90);
    const width = 760, height = 205, pad = 16;
    const maxAbs = Math.max(1, ...values.map((value) => Math.abs(value))) * 1.14;
    const x = (index) => pad + (index / Math.max(1, values.length - 1)) * (width - 2 * pad);
    const y = (value) => height / 2 - (value / maxAbs) * (height / 2 - pad);
    const path = values.map((value, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
    const grid = [-maxAbs / 2, 0, maxAbs / 2].map((value) => `<line x1="${pad}" x2="${width - pad}" y1="${y(value)}" y2="${y(value)}" stroke="${value === 0 ? '#b6c1b3' : '#e1e8df'}" stroke-dasharray="${value === 0 ? '' : '3 5'}" />`).join("");
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="pnlFill" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#85c563" stop-opacity=".35"/><stop offset="1" stop-color="#85c563" stop-opacity="0"/></linearGradient></defs>${grid}<path d="${path} L${x(values.length - 1)},${height} L${x(0)},${height}Z" fill="url(#pnlFill)"/><path d="${path}" fill="none" stroke="#317d59" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>`;
    target.setAttribute("aria-label", `Historical daily portfolio P&L over ${values.length} observations. Minimum ${money(Math.min(...values))}; maximum ${money(Math.max(...values))}.`);
    $("chartObservations").textContent = `${values.length} recent observations`;
  }

  function renderAttention(analysis) {
    const items = [];
    for (const item of analysis.exposures) {
      if (item.breach) items.push({ name: item.name, text: `Limit utilization ${pct(item.utilization)}. Review exposure and collateral.` });
      else if (item.utilization >= 0.8) items.push({ name: item.name, text: `Utilization ${pct(item.utilization)} is near the limit.` });
    }
    for (const item of analysis.credit_reviews) {
      if (item.flags.length) items.push({ name: item.name, text: `${item.flags.length} credit review flag${item.flags.length === 1 ? "" : "s"}: ${item.flags.slice(0, 2).join("; ")}.` });
    }
    if (analysis.summary.backtest_exceptions) items.push({ name: "Model monitoring", text: `${analysis.summary.backtest_exceptions} VaR backtest exception${analysis.summary.backtest_exceptions === 1 ? "" : "s"} in ${analysis.summary.backtest_observations} observations.` });
    $("attentionList").innerHTML = items.length ? items.slice(0, 4).map((item, index) => `<div class="attention-item"><span class="attention-index">${String(index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.text)}</p></div></div>`).join("") : '<p class="empty">No threshold signals in the current dataset.</p>';
  }

  function creditContent(analysis) {
    return `<div class="detail-grid">${analysis.credit_reviews.map((cp) => `<article class="review-card"><div class="sector">${escapeHtml(cp.sector)}</div><h3>${escapeHtml(cp.name)}</h3><span class="rating ${cp.flags.length > 1 ? "warn" : ""}">${escapeHtml(cp.indicative_band)}</span><div class="ratio-grid"><div><label>LIQUIDITY</label><strong>${ratio(cp.liquidity)}</strong></div><div><label>NET DEBT / EBITDA</label><strong>${ratio(cp.net_debt_ebitda)}</strong></div><div><label>INTEREST COVER</label><strong>${ratio(cp.interest_coverage)}</strong></div><div><label>NET MARGIN</label><strong>${pct(cp.net_margin)}</strong></div></div><p>${escapeHtml(cp.review)}</p></article>`).join("")}</div><div class="method-note">Indicative bands are generated by transparent thresholds over the supplied figures. They are not approved counterparty ratings and must not drive credit approval or capital calculations.</div>`;
  }

  function exposureContent(analysis) {
    return `<div class="table-wrap"><table><thead><tr><th>COUNTERPARTY</th><th>POSITIVE MTM</th><th>COLLATERAL</th><th>PFE</th><th>LIMIT</th><th>UTILIZATION</th><th>DAY CHANGE</th><th>STATUS</th></tr></thead><tbody>${analysis.exposures.map((item) => `<tr><td><strong>${escapeHtml(item.name)}</strong><br><small>${escapeHtml(item.sector)}</small></td><td>${money(item.gross_exposure)}</td><td>${money(item.collateral)}</td><td>${money(item.potential_future_exposure)}</td><td>${money(item.credit_limit)}</td><td>${pct(item.utilization)}</td><td>${item.day_over_day_change === null ? "—" : `${item.day_over_day_change >= 0 ? "+" : ""}${money(item.day_over_day_change)}`}</td><td class="${item.breach ? "breach" : item.utilization >= .8 ? "watch" : "safe"}">${item.breach ? "BREACH" : item.utilization >= .8 ? "WATCH" : "WITHIN LIMIT"}</td></tr>`).join("")}</tbody></table></div><div class="method-note">Potential future exposure uses a volatility add-on to positive MTM. Collateral is deducted for limit utilization. Netting, legal enforceability, wrong-way risk, and collateral haircuts are not modeled.</div>`;
  }

  function methodologyContent(analysis) {
    const summary = analysis.summary;
    return `<div class="method-grid"><article class="detail-panel"><div class="method-label">99% HISTORICAL VAR</div><div class="method-value">${money(summary.var_99)}</div><p>One-day portfolio loss quantile across ${analysis.daily_pnl.length} aligned observations.</p></article><article class="detail-panel"><div class="method-label">99% EXPECTED SHORTFALL</div><div class="method-value">${money(summary.expected_shortfall_99)}</div><p>Average loss in the tail at or beyond the VaR threshold.</p></article><article class="detail-panel"><div class="method-label">BACKTEST EXCEPTIONS</div><div class="method-value">${summary.backtest_exceptions}<small> / ${summary.backtest_observations}</small></div><p>Observed loss above the previous 30 day VaR estimate.</p></article></div><div class="section-head"><div><p class="kicker">STRESS SCENARIOS</p><h2>Product stress</h2></div></div><div class="table-wrap"><table><thead><tr><th>COUNTERPARTY</th><th>PRODUCT</th><th>SHOCK</th><th>ESTIMATED P&amp;L</th></tr></thead><tbody>${analysis.stress.map((item) => `<tr><td>${escapeHtml(item.counterparty)}</td><td>${escapeHtml(item.product)}</td><td>${item.shock_pct.toFixed(1)}%</td><td class="${item.estimated_pnl < 0 ? "breach" : "safe"}">${money(item.estimated_pnl)}</td></tr>`).join("")}</tbody></table></div><div class="method-note">${escapeHtml(analysis.methodology.var)} ${escapeHtml(analysis.methodology.margin)} Stress shocks are fixed examples, not calibrated regulatory scenarios.</div>`;
  }

  function showView(view) {
    currentView = view;
    const portfolioView = ["overview", "credit", "exposure", "methodology"].includes(view);
    $("studyView").hidden = view !== "study";
    $("portfolioView").hidden = !portfolioView;
    $("marketView").hidden = view !== "market";
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.closest(".nav") && button.dataset.view === "overview"
        ? portfolioView : button.dataset.view === view;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    $("breadcrumbCurrent").textContent = { study: "Observed defaults", overview: "Your portfolio", credit: "Credit review", exposure: "Exposure", methodology: "Methodology", market: "FX reference rates" }[view];
    $("exportAnalystReport").hidden = !currentAnalysis || !portfolioView;
    $("portfolioOverview").hidden = view !== "overview";
    $("detail").hidden = !portfolioView || view === "overview" || !currentAnalysis;
    if (portfolioView && view !== "overview" && currentAnalysis) {
      const details = {
        credit: ["COUNTERPARTY ANALYSIS", "Credit review", "Financial ratios, indicative rating bands, and review flags."],
        exposure: ["EXPOSURE AND LIMITS", "Exposure", "Positive MTM, collateral, potential future exposure, and limit utilization."],
        methodology: ["RISK MEASURES", "Methodology and backtesting", "Historical risk measures, illustrative margin, stress scenarios, and VaR exceptions."],
      }[view];
      $("detailKicker").textContent = details[0];
      $("detailTitle").textContent = details[1];
      $("detailIntro").textContent = details[2];
      $("detailContent").innerHTML = ({ credit: creditContent, exposure: exposureContent, methodology: methodologyContent })[view](currentAnalysis);
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function render() {
    if (!currentAnalysis) return;
    $("portfolioEmpty").hidden = true;
    $("portfolioPanels").hidden = false;
    const summary = currentAnalysis.summary;
    $("metricExposure").textContent = money(summary.net_exposure);
    $("metricBreaches").textContent = String(summary.breaches).padStart(2, "0");
    $("metricVar").textContent = money(summary.var_99);
    $("metricMargin").textContent = money(summary.initial_margin);
    $("portfolioCount").textContent = `${summary.counterparties} counterparties · ${summary.positions} positions`;
    $("exportAnalystReport").disabled = false;
    $("exportAnalystReportMobile").disabled = false;
    $("exportReport").disabled = false;
    $("sourceMode").textContent = "IMPORTED PORTFOLIO";
    $("portfolioSourceNote").textContent = "Portfolio analysis uses your imported JSON data. ECB FX rates are shown separately.";
    renderChart(currentAnalysis.daily_pnl);
    renderAttention(currentAnalysis);
    showView(currentView);
  }

  function exportAnalystReport() {
    if (!currentAnalysis) return;
    const a = currentAnalysis, sum = a.summary;
    const rows = a.exposures.map((item) => `<tr><td>${escapeHtml(item.name)}</td><td>${money(item.net_exposure)}</td><td>${money(item.potential_future_exposure)}</td><td>${pct(item.utilization)}</td><td>${item.day_over_day_change === null ? "—" : money(item.day_over_day_change)}</td><td>${escapeHtml(item.day_over_day_comment)}</td></tr>`).join("");
    const credit = a.credit_reviews.map((item) => `<article><h3>${escapeHtml(item.name)} <span>${escapeHtml(item.indicative_band)}</span></h3><p><b>${escapeHtml(item.sector)}</b> · Liquidity ${ratio(item.liquidity)} · Net debt/EBITDA ${ratio(item.net_debt_ebitda)} · Interest coverage ${ratio(item.interest_coverage)}.</p><p>${escapeHtml(item.review)}</p></article>`).join("");
    const stress = a.stress.map((item) => `<tr><td>${escapeHtml(item.counterparty)}</td><td>${escapeHtml(item.product)}</td><td>${item.shock_pct.toFixed(1)}%</td><td>${money(item.estimated_pnl)}</td></tr>`).join("");
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><title>Risk Studio · Risk Review</title><style>body{font:14px/1.5 Georgia,serif;color:#18242a;max-width:900px;margin:45px auto;padding:0 25px}h1{font-size:40px;margin:0}h2{font-size:23px;border-bottom:1px solid #bcc7be;padding-bottom:7px;margin-top:35px}h3{font-size:17px;margin-bottom:5px}h3 span{float:right;color:#3d7550}small,.muted{color:#65736b}header{border-bottom:4px solid #b5e45a;padding-bottom:20px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:25px}.kpis div{border:1px solid #bdc9bf;padding:12px}.kpis b{display:block;font-size:22px}.kpis small{font-size:10px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border-bottom:1px solid #d9e0d9;text-align:left;padding:9px}th{background:#f1f5ef}article{padding:8px 0;border-bottom:1px solid #d9e0d9}.notice{background:#f3f5ea;padding:14px;margin:28px 0;font-size:12px}@media print{body{margin:15mm auto}.kpis,article,table{break-inside:avoid}}</style><header><small>RISK STUDIO · USER SUPPLIED DATA</small><h1>Institutional risk review</h1><p>Generated ${escapeHtml(new Date().toLocaleString())}. Amounts use the source portfolio currency unit.</p></header><div class="kpis"><div><small>NET EXPOSURE</small><b>${money(sum.net_exposure)}</b></div><div><small>LIMIT BREACHES</small><b>${sum.breaches}</b></div><div><small>99% VAR</small><b>${money(sum.var_99)}</b></div><div><small>INDICATIVE MARGIN</small><b>${money(sum.initial_margin)}</b></div></div><h2>Counterparty credit reviews</h2>${credit}<h2>Exposure and movement</h2><table><thead><tr><th>Counterparty</th><th>Net exposure</th><th>PFE</th><th>Limit use</th><th>Day change</th><th>Commentary</th></tr></thead><tbody>${rows}</tbody></table><h2>Risk methodology</h2><p>Historical 99% VaR: <b>${money(sum.var_99)}</b>. Expected shortfall: <b>${money(sum.expected_shortfall_99)}</b>. Indicative initial margin: <b>${money(sum.initial_margin)}</b>. Backtest exceptions: <b>${sum.backtest_exceptions} / ${sum.backtest_observations}</b>.</p><h2>Product stress</h2><table><thead><tr><th>Counterparty</th><th>Product</th><th>Shock</th><th>Estimated P&amp;L</th></tr></thead><tbody>${stress}</tbody></table><div class="notice"><b>Method and limitations.</b> ${escapeHtml(a.methodology.credit)} ${escapeHtml(a.methodology.pfe)} ${escapeHtml(a.methodology.var)} ${escapeHtml(a.methodology.margin)} Portfolio inputs were supplied by the user. ECB FX rates are displayed separately and do not alter portfolio calculations. Approved ratings, ISDA SIMM, legal netting, and regulatory capital methodology are not included.</div></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    const link = document.createElement("a"); link.href = url; link.download = "risk-studio-review.html"; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  $("heroAnalyze").addEventListener("click", () => currentAnalysis ? showView("credit") : dialog.showModal());
  $("exportAnalystReport").addEventListener("click", exportAnalystReport);
  $("exportAnalystReportMobile").addEventListener("click", exportAnalystReport);
  $("openSources").addEventListener("click", () => dialog.showModal());
  $("refreshMarketFeed").addEventListener("click", loadMarketFeed);
  $("runAnalysis").addEventListener("click", runAnalysis);
  $("downloadTemplate").addEventListener("click", () => download("risk-studio-input-skeleton.json", { counterparties: [], positions: [], margin_multiplier: 1.25 }));
  $("exportReport").addEventListener("click", () => currentAnalysis && download("risk-studio-analysis.json", { inputs: currentInputs, analysis: currentAnalysis }));
  $("jsonFile").addEventListener("change", async (event) => { const file = event.target.files?.[0]; if (file) { $("jsonInput").value = await file.text(); setError(""); } });
  showView("study");
  loadMarketFeed();
  setInterval(loadMarketFeed, 15 * 60 * 1000);
})();
