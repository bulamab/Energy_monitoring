/**
 * charts/bar_monthly.js
 * Histogramme mensuel simple.
 *
 * @param {object} chart   - instance ECharts
 * @param {object} kpi     - données KPI depuis l'API
 */
function renderBarMonthly(chart, kpi) {
  const color  = (kpi.display || {}).color || "#3498db";
  const dates  = Object.keys(kpi.data);
  const values = Object.values(kpi.data);

  chart.setOption({
    tooltip: {
      trigger: "axis",
      formatter: p => `${p[0].axisValue}<br/>${p[0].value} ${kpi.unit}`
    },
    grid: { left: 55, right: 20, top: 35, bottom: 55 },
    xAxis: {
      type: "category",
      data: dates.map(d => d.substring(0, 7)),
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: {
      type: "value",
      name: kpi.unit,
      nameLocation: "end",
      nameTextStyle: { fontSize: 11 }
    },
    series: [{
      type     : "bar",
      data     : values,
      itemStyle: { color },
      barMaxWidth: 40
    }]
  });
}
// Auto-enregistrement
registerChart("bar_monthly", renderBarMonthly);