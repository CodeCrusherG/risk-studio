/* Public historical credit validation, independent of uploaded institutional portfolios. */
(() => {
  "use strict";
  const target = document.getElementById("creditCaseContent");
  if (!target) return;
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const number = (n, places = 3) => Number(n).toLocaleString("en-US", {minimumFractionDigits: places, maximumFractionDigits: places});
  const percent = n => `${number(n * 100, 2)}%`;
  async function load() {
    try {
      const response = await fetch("/api/risk-studio/credit-case-study", {credentials: "same-origin"});
      const r = await response.json();
      if (!response.ok) throw new Error(r.detail || "Case study unavailable");
      const m = r.models[r.reference_model].holdout;
      const ci = r.bootstrap.intervals.auc;
      const rows = Object.entries(r.models).map(([name, result]) => {
        const v = result.holdout;
        return `<tr><th scope="row">${escape(name.replaceAll("_", " "))}</th><td>${number(v.auc)}</td><td>${number(v.ks)}</td><td>${number(v.brier, 4)}</td><td>${number(v.log_loss, 4)}</td><td>${percent(v.mean_predicted_pd)}</td><td>${number(v.observed_expected_ratio)}</td></tr>`;
      }).join("");
      const bins = m.reliability.map(b => `<tr><td>${percent(b.lower)}–${percent(b.upper)}</td><td>${number(b.count, 0)}</td><td>${percent(b.mean_predicted_pd)}</td><td>${percent(b.observed_default_rate)}</td><td>${percent(b.wilson_95_low)}–${percent(b.wilson_95_high)}</td></tr>`).join("");
      const splitRows = Object.entries(r.partitions).map(([name, p]) => `<tr><th scope="row">${escape(name)}</th><td>${number(p.rows, 0)}</td><td>${number(p.defaults, 0)}</td><td>${percent(p.default_rate)}</td></tr>`).join("");
      target.innerHTML = `<p class="case-intro">Payment histories: April–September 2005. Outcome: payment default in the following month.</p>
        <div class="case-kpis"><article><span>Observed records</span><strong>${number(r.data_quality.rows, 0)}</strong><small>${number(r.data_quality.defaults, 0)} payment defaults</small></article><article><span>Observed default rate</span><strong>${percent(r.data_quality.defaults / r.data_quality.rows)}</strong><small>Full source cohort</small></article><article><span>Holdout AUC</span><strong>${number(m.auc)}</strong><small>95% interval ${number(ci.low)}–${number(ci.high)}</small></article><article><span>Holdout KS</span><strong>${number(m.ks)}</strong><small>${number(m.rows, 0)} held-out records</small></article></div>
        <figure class="case-chart-panel"><h2>Model validation</h2><p>Holdout ROC and calibration for logistic regression and calibrated boosting; score distributions across same-cohort partitions.</p><div class="case-chart-scroll" tabindex="0" aria-label="Model validation charts; scroll horizontally on small screens"><img class="case-chart" src="${r.artifact_urls['validation.png']}" alt="Held-out ROC and calibration curves, with same-cohort partition score distributions. Numeric results are provided in the model comparison table below."></div></figure>
        <div class="case-actions"><a class="secondary-button" href="${r.artifact_urls['report.md']}">Validation report ↓</a><a class="secondary-button" href="${r.artifact_urls['report.json']}">Metrics JSON ↓</a><a class="secondary-button" href="${r.artifact_urls['predictions.csv']}">Labels and estimated PD ↓</a><a class="secondary-button" href="${r.artifact_urls['observed_clients.csv']}">Source records CSV ↓</a></div>
        <details class="case-details"><summary>Model comparison and calibration tables</summary>
          <h3>Held-out model comparison</h3><p>The calibrated booster was designated before holdout evaluation. Training and calibration data do not count as independent validation.</p>
          <div class="table-wrap" tabindex="0"><table><thead><tr><th>Model</th><th>AUC</th><th>KS</th><th>Brier</th><th>Log loss</th><th>Mean PD</th><th>Observed / expected</th></tr></thead><tbody>${rows}</tbody></table></div>
          <h3>Calibration by estimated probability</h3><div class="table-wrap" tabindex="0"><table><thead><tr><th>PD band</th><th>Records</th><th>Mean estimated PD</th><th>Observed defaults</th><th>95% Wilson interval</th></tr></thead><tbody>${bins}</tbody></table></div>
        </details>
        <details class="case-details"><summary>Study design, limitations, and sources</summary>
          <p>This research study is pending independent review.</p>
          <h3>Data partitions</h3><p>${escape(r.protocol.split_description)} ${number(r.data_quality.duplicate_predictor_rows, 0)} duplicate predictor rows were grouped to avoid crossing partitions.</p><div class="table-wrap" tabindex="0"><table><thead><tr><th>Partition</th><th>Records</th><th>Defaults</th><th>Observed rate</th></tr></thead><tbody>${splitRows}</tbody></table></div>
          <p>Development-to-holdout score PSI: <strong>${number(r.stability.score.holdout.psi, 6)}</strong>. This compares random partitions within one cohort. Time drift and out-of-time performance are unmeasured.</p>
          <h3>Review findings</h3><ul>${r.governance.findings.map(f => `<li><strong>${escape(f.severity)} · ${escape(f.finding)}</strong> ${escape(f.action)}</li>`).join("")}</ul>
          <h3>Study limitations</h3><ul>${r.limitations.map(s => `<li>${escape(s)}</li>`).join("")}</ul>
          <p>Use the source CSV in <a href="/workbench">the workbench</a> for data profiling and model development. It includes observed values and each record’s assigned partition.</p>
          <p class="case-source">Source: <a href="https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients" target="_blank" rel="noopener noreferrer">Yeh (2009), UCI, DOI 10.24432/C55S3H</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>. Downloaded ${escape(r.source.retrieved_at || "date unrecorded")}. <a href="${r.artifact_urls['source_manifest.json']}">Source manifest ↓</a><br>Archive SHA-256: <code>${escape(r.source.archive_sha256)}</code><br>${escape(r.integrity)}</p>
        </details>`;
    } catch (error) {
      target.textContent = error.message || "The public case study is unavailable.";
    }
  }
  load();
})();
