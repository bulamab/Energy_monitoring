/**
 * charts/bar_stacked.js
 * Histogramme empilé — résolution paramétrable (monthly/yearly/weekly).
 * Avec sélecteur d'année (monthly/weekly) et ligne optionnelle.
 */
function renderBarStacked(chart, kpi, el) {
  const display     = kpi.display || {};
  const colors      = display.colors || ["#3498db","#e67e22","#2ecc71","#9b59b6","#e74c3c","#1abc9c"];
  const x_labels    = kpi.data.x_labels;
  const labels      = kpi.data.labels;
  const series_data = kpi.data.series;
  const line_cfg    = kpi.data.line || null;
  const resolution  = kpi.resolution || "monthly";
  const years       = kpi.years_available;

  // --- Sélecteur d'année (monthly et weekly seulement) ---
  const card = el.closest(".card");
  let selector = card.querySelector(".year-selector");

  if (resolution === "yearly") {
    // Pas de sélecteur pour yearly
    if (selector) selector.remove();
    el._selectedYear = "all";
  } else {
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
        renderBarStacked(chart, kpi, el);
      };
      selector.appendChild(btn);
    });
  }

  // --- Données du groupe sélectionné ---
  const yearKey   = el._selectedYear || "all";
  const year_data = series_data[yearKey] || {};
  const meter_ids = Object.keys(labels);

  // --- Axe Y secondaire ---
  const use_secondary = line_cfg && line_cfg.axis === "secondary";

  const yAxes = [{
    type         : "value",
    name         : kpi.unit,
    nameLocation : "end",
    nameTextStyle: { fontSize: 11 },
  }];

  if (use_secondary) {
    yAxes.push({
      type         : "value",
      name         : line_cfg.unit || "",
      nameLocation : "end",
      nameTextStyle: { fontSize: 11, color: line_cfg.color || "#f39c12" },
      axisLine     : { lineStyle: { color: line_cfg.color || "#f39c12" } },
      axisLabel    : { color: line_cfg.color || "#f39c12" },
      splitLine    : { show: false },
    });
  }

  // --- Séries barres empilées ---
  const echarts_series = meter_ids.map((mid, i) => ({
    name      : labels[mid],
    type      : "bar",
    stack     : "total",
    yAxisIndex: 0,
    data      : (year_data[mid] || Array(x_labels.length).fill(null)),
    itemStyle : { color: colors[i % colors.length] },
    label     : resolution === "yearly" ? {
        show     : true,
        position : "inside",
        formatter: params => params.value !== null && params.value !== 0 ? `${params.value.toFixed(0)} ${kpi.unit}` : "",
        fontSize : 10,
        color    : "#2c3e50",
    } : { show: false },
    barWidth  : "90%",
  }));

  // --- Ligne optionnelle ---
  const legend_items = meter_ids.map(mid => labels[mid]);

  if (line_cfg && line_cfg.values && line_cfg.values[yearKey]) {
    echarts_series.push({
      name      : line_cfg.label,
      type      : "line",
      yAxisIndex: use_secondary ? 1 : 0,
      data      : line_cfg.values[yearKey],
      smooth    : true,
      symbol    : "circle",
      symbolSize: 5,
      lineStyle : { color: line_cfg.color || "#2c3e50", width: 2 },
      itemStyle : { color: line_cfg.color || "#2c3e50" },
      label     : {
        show    : true,
        position: "top",
        formatter: params => params.value !== null ? `${params.value.toFixed(0)} ${line_cfg.unit || kpi.unit}` : "",
        fontSize : 10,
        color    : line_cfg.color || "#2c3e50",
      },
      z         : 10,
    });
    legend_items.push(line_cfg.label);
  }

  // --- Tooltip ---
  const formatter = params => {
    const label = params[0].axisValue;
    const bars  = params.filter(p => p.seriesType === "bar" && p.value !== null);
    const line  = params.find(p => p.seriesType === "line");
    const lines = bars.map(p => `${p.marker}${p.seriesName} : ${p.value ?? "—"} ${kpi.unit}`);
    const total = bars.reduce((s, p) => s + (p.value || 0), 0);
    if (bars.length > 1) lines.push(`<b>Total : ${total.toFixed(1)} ${kpi.unit}</b>`);
    if (line && line.value !== null) {
      const unit2 = line_cfg.unit ? line_cfg.unit : kpi.unit;
      lines.push(`${line.marker}${line.seriesName} : ${line.value} ${unit2}`);
    }
    return [label, ...lines].join("<br/>");
  };

  chart.setOption({
    tooltip : { trigger: "axis", axisPointer: { type: "shadow" }, formatter },
    legend  : { data: legend_items, bottom: 0, textStyle: { fontSize: 11 } },
    grid    : { left: 55, right: use_secondary ? 65 : 20, top: 20, bottom: 45 },
    xAxis   : {
      type     : "category",
      data     : x_labels,
      axisLabel: { fontSize: 11, rotate: resolution === "weekly" ? 45 : 0 }
    },
    yAxis  : yAxes,
    series : echarts_series
  }, true);
}
// Auto-enregistrement
registerChart("bar_stacked", renderBarStacked);