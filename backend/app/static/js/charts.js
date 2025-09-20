// Simple helpers (currently unused in templates but handy)
window.FocusPointCharts = (function () {
  function clamp01(x){ return Math.max(0, Math.min(1, x)); }
  function barWidth(value, maxValue) {
    const d = (maxValue > 0 ? value / maxValue : 0);
    return (clamp01(d) * 100).toFixed(3) + '%';
  }
  return { barWidth };
})();

