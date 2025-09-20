(function () {
  const KEY = 'FocusPoint_sidebar_collapsed';
  const sb = document.getElementById('sidebar');
  const btn = document.getElementById('sidebarToggle');

  function setCollapsed(v) {
    if (!sb) return;
    if (v) sb.classList.add('collapsed');
    else sb.classList.remove('collapsed');
    try { localStorage.setItem(KEY, v ? '1' : '0'); } catch (_) {}
  }

  // restore
  try { setCollapsed(localStorage.getItem(KEY) === '1'); } catch (_) {}

  if (btn) btn.addEventListener('click', () => {
    const v = !sb.classList.contains('collapsed');
    setCollapsed(v);
  });
})();

