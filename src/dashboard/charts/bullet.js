function renderBullet(chart, kpi, el) {
  const years   = kpi.years_available || [];
  const target  = kpi.target;
  const ranges  = kpi.ranges;
  const axisMin = kpi.min ?? 0;
  const axisMax = kpi.max ?? 100;
  const values  = kpi.data.values;
  const unit    = kpi.unit || "%";

  const ZONE_HEIGHT    = 26;
  const BAR_HEIGHT     = 10;
  const LINE_OVERSHOOT = 6;   // dépassement du repère cible au-dessus/dessous des zones

  // --- Réduit la hauteur du conteneur (override du CSS .chart{height:300px}) ---
  el.style.height = "110px";
  chart.resize();

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
      renderBullet(chart, kpi, el);
    };
    selector.appendChild(btn);
  });

  const value = values[el._selectedYear];

  // --- Zones de fond + ligne cible : tout en pixels, centré sur yCenter ---
  const zonesCustom = {
    type  : "custom",
    silent: true,
    z     : 1,
    data  : [0],
    renderItem: (params, api) => {
      const yCenter = api.coord([axisMin, 0])[1];
      const segments = ranges && ranges.length
        ? ranges
        : [{ to: axisMax, color: "#ecf0f1" }];

      let prev = axisMin;
      const children = segments.map(r => {
        const xStart = api.coord([prev, 0])[0];
        const xEnd   = api.coord([r.to, 0])[0];
        prev = r.to;
        return {
          type : "rect",
          shape: {
            x     : xStart,
            y     : yCenter - ZONE_HEIGHT / 2,
            width : xEnd - xStart,
            height: ZONE_HEIGHT,
          },
          style: { fill: r.color },
        };
      });

      if (target != null) {
        const xTarget = api.coord([target, 0])[0];
        children.push({
          type : "line",
          shape: {
            x1: xTarget, y1: yCenter - ZONE_HEIGHT / 2 - LINE_OVERSHOOT,
            x2: xTarget, y2: yCenter + ZONE_HEIGHT / 2 + LINE_OVERSHOOT,
          },
          style: { stroke: "#000", lineWidth: 2 },
        });
      }

      return { type: "group", children };
    },
  };

  // --- Barre de mesure ---
  const measureSeries = {
    type     : "bar",
    data     : [value],
    barWidth : BAR_HEIGHT,
    itemStyle: { color: "#848485" },
    label    : {
      show           : true,
      position       : "top",
      distance       : 14,        // ← écart bar→label, augmentez pour décaler plus haut
      formatter      : value != null ? `${value} ${unit}` : "—",
      fontSize       : 12,
      fontWeight     : "bold",
      textBorderWidth: 0,
      textBorderColor: "transparent",
    },
    z        : 2,
  };

  chart.setOption({
    tooltip: {
      trigger  : "item",
      formatter: () =>
        (value != null ? `${value} ${unit}` : "Pas de donnée") +
        (target != null ? `<br/>Cible : ${target} ${unit}` : ""),
    },
    grid : { left: 20, right: 60, top: 35, bottom: 20 },
    xAxis: {
      type         : "value",
      min          : axisMin,
      max          : axisMax,
      name         : unit,
      nameLocation : "end",
      nameTextStyle: {
        fontSize: 11,
        padding : [300, 0, 0, 20],   // top: descend au niveau des graduations / left: éloigne de la dernière valeur
      },
      axisLabel    : { fontSize: 11 },
    },
    yAxis: { type: "category", data: [""], show: false },
    series: [zonesCustom, measureSeries],
  }, true);
}
registerChart("bullet", renderBullet);