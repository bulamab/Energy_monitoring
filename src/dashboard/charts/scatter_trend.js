/**
 * charts/scatter_trend.js
 * Scatter plot avec courbe de tendance linéaire.
 * Points colorés par année, équation de régression affichée.
 */
function renderScatterTrend(chart, kpi, el) {
  const display  = kpi.display || {};
  const colors   = display.colors || ["#3498db","#e67e22","#2ecc71","#9b59b6","#e74c3c"];
  const points   = kpi.data.points   || {};
  const trend    = kpi.data.trendline;
  const equation = kpi.data.equation;
  const years    = Object.keys(points);

  // --- Séries scatter par année ---
  const series = years.map((year, i) => ({
    name      : year,
    type      : "scatter",
    data      : (points[year] || []).map(p => [p.x, p.y]),
    symbolSize: 7,
    itemStyle : { color: colors[i % colors.length], opacity: 0.8 },
  }));

  // --- Droite de tendance ---
  if (trend && trend.length === 2) {
    series.push({
      name     : "Tendance",
      type     : "line",
      data     : trend.map(p => [p.x, p.y]),
      smooth   : false,
      symbol   : "none",
      lineStyle: { color: "#2c3e50", width: 2, type: "dashed" },
      itemStyle: { color: "#2c3e50" },
    });
  }

  // --- Labels d'axes ---
  const yLabel = `${kpi.y_label || ""} (${kpi.unit_y || ""})`;
  const xLabel = `${kpi.x_label || ""} (${kpi.unit_x || ""})`;
  const subtitle = equation ? equation.text : "";

  chart.setOption({
    title: [
      // Titre axe Y — positionné manuellement à gauche
      //{
      //  text     : yLabel,
      //  textStyle: { fontSize: 11, color: "#555", fontWeight: "normal" },
      //  left     : 0,
      //  top      : "top",
      //  textVerticalAlign: "bottom",
      //},
      
      // Équation de régression — sous le graphique
      {
        text        : "",
        subtext     : subtitle,
        subtextStyle: { fontSize: 11, color: "#7f8c8d" },
        //left        : "right",
        right       : 30,
        top         : 10,
      }
    ],
    tooltip: {
      trigger  : "item",
      formatter: params => {
        if (params.seriesType === "line") return params.seriesName;
        return `${params.seriesName}<br/>
                ${kpi.x_label} : ${params.value[0]} ${kpi.unit_x}<br/>
                ${kpi.y_label} : ${params.value[1]} ${kpi.unit_y}`;
      }
    },
    legend: {
      data     : [...years, ...(trend ? ["Tendance"] : [])],
      bottom   : 0,
      textStyle: { fontSize: 11 }
    },
    grid: { left: 50, right: 20, top: 20, bottom: 65 },
    xAxis: {
      type         : "value",
      name         : xLabel,
      nameLocation : "middle",
      nameGap      : 28,
      axisLabel    : { fontSize: 11 }
    },
    yAxis: {
      type         : "value",
      name         : yLabel,
      nameLocation : "middle",
      nameGap      : 28,
      axisLabel    : { fontSize: 11 }
      // pas de name — géré par title
    },
    series
  });
}
registerChart("scatter_trend", renderScatterTrend);