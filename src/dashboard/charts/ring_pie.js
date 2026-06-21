/**
 * charts/ring_pie.js
 * Camembert en anneau — répartition entre plusieurs compteurs.
 * Sélecteur d'année (même pattern que bar_stacked.js / bullet.js).
 */
function renderRingPie(chart, kpi, el) {
  const display       = kpi.display || {};
  const colors        = display.colors || ["#3498db","#e67e22","#2ecc71","#9b59b6","#e74c3c","#1abc9c"];
  const years         = kpi.years_available || [];
  const unit          = kpi.unit || "";
  const valuesByYear  = kpi.data.values || {};

  // --- Sélecteur d'année ---
  const card = el.closest(".card");
  let selector = card.querySelector(".year-selector");
  if (!selector) {
    selector = document.createElement("div");
    selector.className = "year-selector";
    selector.style.cssText = "display:flex; gap:0.4rem; margin-bottom:0.6rem; flex-wrap:wrap;";
    el.before(selector);
  }
  if (!el._selectedYear || !years.map(String).includes(el._selectedYear)) {
    el._selectedYear = String(years[years.length - 1]);
  }
  selector.innerHTML = "";
  years.forEach(year => {
    const btn = document.createElement("button");
    btn.textContent = year;
    btn.style.cssText = `
      padding: 2px 10px; border-radius: 12px;
      border: 1px solid #bdc3c7; cursor: pointer; font-size: 0.8rem;
      background: ${String(year) === el._selectedYear ? "#3498db" : "white"};
      color: ${String(year) === el._selectedYear ? "white" : "#2c3e50"};
    `;
    btn.onclick = () => {
      el._selectedYear = String(year);
      renderRingPie(chart, kpi, el);
    };
    selector.appendChild(btn);
  });

  const slices = valuesByYear[el._selectedYear] || [];

  chart.setOption({
    tooltip: {
      trigger  : "item",
      formatter: params =>
        `${params.marker}${params.name} : ${params.value} ${unit} (${params.percent}%)`,
    },
    legend: {
      bottom   : 0,
      textStyle: { fontSize: 11 },
    },
    series: [{
      type              : "pie",
      radius            : ["45%", "70%"],
      center            : ["50%", "45%"],
      avoidLabelOverlap : true,
      itemStyle         : { borderColor: "#fff", borderWidth: 2 },
      label             : { show: true, formatter: "{b}\n{d}%", fontSize: 11 },
      labelLine         : { show: true },
      data              : slices.map((s, i) => ({
        ...s,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }],
  }, true);
}
// Auto-enregistrement
registerChart("ring_pie", renderRingPie);