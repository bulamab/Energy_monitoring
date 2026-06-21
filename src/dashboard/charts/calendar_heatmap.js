/**
 * charts/calendar_heatmap.js
 * Heatmap calendaire — une valeur par jour, style GitHub contributions.
 * Sélecteur d'année (même pattern que les autres charts).
 */
function renderCalendarHeatmap(chart, kpi, el) {
  const years       = kpi.years_available || [];
  const unit        = kpi.unit || "";
  const vmin        = kpi.min ?? 0;
  const vmax        = kpi.max ?? 1;
  const colorScale  = kpi.color_scale || ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"];
  const valuesByYear = kpi.data.values || {};

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
      renderCalendarHeatmap(chart, kpi, el);
    };
    selector.appendChild(btn);
  });

  const points = valuesByYear[el._selectedYear] || [];

  chart.setOption({
    tooltip: {
      formatter: p => `${p.data[0]} : ${p.data[1] != null ? p.data[1] : "—"} ${unit}`,
    },
    visualMap: {
      min       : vmin,
      max       : vmax,
      calculable: true,
      orient    : "horizontal",
      left      : "center",
      bottom    : 0,
      itemWidth : 14,
      itemHeight: 80,
      textStyle : { fontSize: 10 },
      inRange   : { color: colorScale },
    },
    calendar: {
      top       : 30,
      left      : 30,
      right     : 20,
      cellSize  : ["auto", 14],
      range     : el._selectedYear,
      itemStyle : { borderWidth: 2, borderColor: "#fff" },
      yearLabel : { show: false },
      dayLabel  : { fontSize: 10 },
      monthLabel: { fontSize: 10 },
    },
    series: [{
      type            : "heatmap",
      coordinateSystem: "calendar",
      data            : points,
    }],
  }, true);
}
// Auto-enregistrement
registerChart("calendar_heatmap", renderCalendarHeatmap);