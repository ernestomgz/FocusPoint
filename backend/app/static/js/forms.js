// Lightweight helpers for preloading edit forms when selecting an existing item.
// Works even if only some fields are present; defensive defaults.
(function () {
  // If the server renders data-attrs on <option>, this will copy them into inputs.
  function bindCopy(selectId, mapping) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    function apply() {
      const opt = sel.selectedOptions && sel.selectedOptions[0];
      if (!opt) return;
      Object.entries(mapping).forEach(([attr, inputId]) => {
        const v = opt.getAttribute('data-' + attr);
        if (v == null) return;
        const el = document.getElementById(inputId);
        if (!el) return;
        el.value = v;
        el.dispatchEvent(new Event('input'));
        el.dispatchEvent(new Event('change'));
      });
    }
    sel.addEventListener('change', apply);
    // initial
    apply();
  }

  // Example bindings (these only do work if your server provides data-* on options):
  bindCopy('proj_id', {
    'name': 'proj_name',
    'objective': 'proj_obj',
    'description': 'proj_desc',
    'status': 'proj_status',
    'color': 'proj_color',
    'end': 'proj_end' // should be DD/MM/YYYY
  });

  bindCopy('ms_id', {
    'name': 'ms_name',
    'end': 'ms_end',
    'percent': 'ms_percent',
    'status': 'ms_status',
    'note': 'ms_note'
  });
})();

