/**
 * charts/energy_label_heating.js
 * Étiquette énergie enveloppe bâtiment — SVG dynamique.
 * Positionne la flèche noire selon le ratio % calculé.
 */
function renderEnergyLabel(chart, kpi, el) {

  const ratio      = kpi.ratio_pct   || 0;
  const qh_li_norm = kpi.qh_li_norm  || 0;
  const qh_eff     = kpi.qh_effectif || 0;
  const year       = kpi.year        || "";

  // --- Positions Y des catégories dans le viewBox (0 0 180 180) ---
  // Chaque catégorie = 50%, flèches de A (0%) à G (300%+)
  // Relevé depuis le SVG : y_top ≈ 9.25, y_bottom ≈ 143
  const Y_TOP    = 9.25;    // y correspondant à 0%
  const Y_BOTTOM = 143.0;   // y correspondant à 350% (bas de G)
  const PCT_MAX  = 350;     // % max affiché

  // Calcul position Y de la flèche noire
  const pct_clamped = Math.min(ratio, PCT_MAX);
  const y_arrow = Y_TOP + (pct_clamped / PCT_MAX) * (Y_BOTTOM - Y_TOP);

  // Hauteur de la flèche noire (même que les autres : ~17mm)
  const arrow_h = 17.0;
  const y_arrow_center = y_arrow - arrow_h / 2;

  // --- Construction du SVG ---
  const svgNS = "http://www.w3.org/2000/svg";

  // SVG de base (copie fidèle de l'original sans la flèche noire statique)
  el.innerHTML = `
  <svg width="100%" viewBox="0 0 180 180" xmlns="http://www.w3.org/2000/svg"
       style="max-width:340px; display:block; margin:auto;">

    <!-- Flèches colorées A→G -->
    <g transform="translate(0,-3.7041668)">
      <g transform="translate(0,0.46117582)">
        <!-- A vert foncé -->
        <path style="fill:#009c6d" d="m 33.538408,22.220448 h 32.208694 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="32.5">A</text>
        <!-- B vert -->
        <path style="fill:#50af31" d="m 33.538408,39.628809 h 45.102901 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="50">B</text>
        <!-- C vert-jaune -->
        <path style="fill:#c3d52a" d="m 33.538408,57.037169 h 58.001627 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="67.5">C</text>
        <!-- D jaune -->
        <path style="fill:#fff200" d="m 33.538408,74.44553 h 71.000237 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#555;font-family:sans-serif;font-weight:bold" x="36" y="85">D</text>
        <!-- E orange -->
        <path style="fill:#f7941d" d="m 33.538408,91.853891 h 83.898963 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="102.3">E</text>
        <!-- F rouge-orange -->
        <path style="fill:#f15a24" d="m 33.538408,109.26225 h 96.797693 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="119.7">F</text>
        <!-- G rouge -->
        <path style="fill:#ed1c24" d="m 33.538408,126.67061 h 109.696423 l 6.616335,8.500153 -6.616335,8.454208 H 33.538408 Z"/>
        <text style="font-size:10.58px;fill:#fff;font-family:sans-serif;font-weight:bold" x="36" y="137.2">G</text>
      </g>
    </g>

    <!-- Pourcentages à gauche -->
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="22.5">0%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="58.5">50%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="96.5">100%</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="6.9" y="134.5">200%</text>

    <!-- Flèche noire dynamique -->
    <path style="fill:#000000"
      d="m 178.71192,${y_arrow_center}
         l -49.10312,-0.259914
         l -6.61633,8.5001524
         l 6.61633,8.454208
         l 49.10312,0.259914 z"/>

    <!-- Ratio % sur la flèche noire -->
    <text style="font-size:10.58px;font-family:sans-serif;font-style:italic;fill:#fff"
          x="140" y="${y_arrow_center + 10.5}">${ratio.toFixed(1)} %</text>

    <!-- Valeurs en bas -->
    <text style="font-size:7.06px;font-family:sans-serif" x="21" y="163.5">Qh,li =</text>
    <text style="font-size:7.06px;font-family:sans-serif;font-weight:bold" x="52" y="163.5">${qh_li_norm}</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="67.5" y="163.5">kWh/m².an</text>

    <text style="font-size:7.06px;font-family:sans-serif" x="1.7" y="174.5">Qh,effectif =</text>
    <text style="font-size:7.06px;font-family:sans-serif;font-weight:bold" x="52" y="174.5">${qh_eff}</text>
    <text style="font-size:7.06px;font-family:sans-serif" x="67.5" y="174.5">kWh/m².an</text>

    <!-- Année -->
    <text style="font-size:7.06px;font-family:sans-serif;fill:#666" x="130" y="174.5">${year}</text>

  </svg>`;
}

registerChart("energy_label_heating", renderEnergyLabel);