/**
 * charts/bar_monthly_multi_year.js
 * Histogramme mensuel comparatif multi-années — barres groupées.
 *
 * @param {object} chart   - instance ECharts
 * @param {object} kpi     - données KPI depuis l'API
 */
function renderBarMonthlyMultiYear(chart, kpi) {
  const display = kpi.display || {};
  const colors  = display.colors || ["#3498db","#e67e22","#2ecc71","#9b59b6","#e74c3c"];
  const months  = kpi.data.months;
  const years   = kpi.data.years;

  const series = Object.entries(years).map(([year, values], i) => ({
    name      : year,
    type      : "bar",
    data      : values,
    itemStyle : { color: colors[i % colors.length] },
    barMaxWidth: 28
  }));

  chart.setOption({
    tooltip: {
      trigger: "axis",
      formatter: params => {
        const lines = params.map(p =>
          `${p.marker}${p.seriesName} : ${p.value ?? "—"} ${kpi.unit}`
        );
        return [params[0].axisValue, ...lines].join("<br/>");
      }
    },
    legend: {
      data      : Object.keys(years),
      bottom    : 0,
      textStyle : { fontSize: 11 }
    },
    grid: { left: 55, right: 20, top: 35, bottom: 45 },
    xAxis: {
      type     : "category",
      data     : months,
      axisLabel: { fontSize: 11 }
    },
    yAxis: {
      type          : "value",
      name          : kpi.unit,
      nameLocation  : "end",
      nameTextStyle : { fontSize: 11 }
    },
    series
  });
}
// Auto-enregistrement
registerChart("bar_monthly_multi_year", renderBarMonthlyMultiYear);