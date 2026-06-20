/**
 * charts/energy_label_heating.js
 * Étiquette énergie enveloppe bâtiment — SVG dynamique.
 * Sélecteur d'année, positionne la flèche selon le ratio %.
 */
function renderEnergyLabel(chart, kpi, el) {

  const years        = kpi.years_available || [];
  const years_data   = kpi.years_data      || {};
  const qh_li_ref    = kpi.qh_li_ref       || 0;

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
      renderEnergyLabel(chart, kpi, el);
    };
    selector.appendChild(btn);
  });

  // --- Données de l'année sélectionnée ---
  const d = years_data[el._selectedYear] || {};
  const ratio      = d.ratio_pct   || 0;
  const qh_li_norm = d.qh_li_norm  || 0;
  const qh_eff     = d.qh_effectif || 0;
  const year       = el._selectedYear || "";

  // --- Positions Y dans le viewBox ---
  const Y_TOP    = 9.25;
  const Y_BOTTOM = 143.0;
  const PCT_MAX  = 350;

  const pct_clamped    = Math.min(ratio, PCT_MAX);
  const y_arrow        = Y_TOP + (pct_clamped / PCT_MAX) * (Y_BOTTOM - Y_TOP);
  const arrow_h        = 17.0;
  const y_arrow_center = y_arrow - arrow_h / 2;

  // --- SVG ---
  el.innerHTML = `
  <svg width="100%" viewBox="0 0 180 185" xmlns="http://www.w3.org/2000/svg"
       style="max-width:340px; display:block; margin:auto;">

    <g transform="translate(0,-3.7041668)">
      <g transform="translate(0,0.46117582)">
        <path style="fill:#009c6d" d="m 33.538408,22.220448 h 32.208694 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="32.5">A</text>
        <path style="fill:#50af31" d="m 33.538408,39.628809 h 45.102901 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="50">B</text>
        <path style="fill:#c3d52a" d="m 33.538408,57.037169 h 58.001627 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="67.5">C</text>
        <path style="fill:#fff200" d="m 33.538408,74.44553 h 71.000237 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#555;font-family:sans-serif;font-weight:bold" x="36" y="85">D</text>
        <path style="fill:#f7941d" d="m 33.538408,91.853891 h 83.898963 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="102.3">E</text>
        <path style="fill:#f15a24" d="m 33.538408,109.26225 h 96.797693 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="119.7">F</text>
        <path style="fill:#ed1c24" d="m 33.538408,126.67061 h 109.696423 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="137.2">G</text>
      </g>
    </g>

    <!-- Pourcentages -->
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="22.5">0%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="40.5">50%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="58.5">100%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="76.5">150%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="96.5">200%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="115.5">250%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="134.5">300%</text>

    <!-- Flèche noire dynamique -->
    <path style="fill:#000000"
      d="M 178,${y_arrow_center}
         l -49.10312,0
         l -6.61633,8.5001524
         l 6.61633,8.454208
         l 49.10312,0 z"/>

    <!-- Ratio % sur la flèche -->
    <text style="font-size:9px;font-family:sans-serif;font-style:italic;fill:#fff"
          x="138" y="${y_arrow_center + 10.5}">${ratio.toFixed(1)}%</text>

    <!-- Valeurs en bas -->
    <text style="font-size:7.06px;font-family:sans-serif" x="2" y="158">Qh,li,réf =</text>
    <text style="font-size:7.06px;font-family:sans-serif;font-weight:bold" x="52" y="158">${qh_li_ref}</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="67.5" y="158">kWh/m².an</text>

    <text style="font-size:7.06px;font-family:sans-serif" x="2" y="168">Qh,effectif =</text>
    <text style="font-size:7.06px;font-family:sans-serif;font-weight:bold" x="52" y="168">${qh_li_norm}</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="67.5" y="168">kWh/m².an</text>

    <text style="font-size:7.06px;font-family:sans-serif;fill:#666" x="150" y="178">${year}</text>

  </svg>`;
}

registerChart("energy_label_heating", renderEnergyLabel);