// Minimal global boot & helpers
window.$ = (sel, ctx = document) => ctx.querySelector(sel);
window.$$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

window.addEventListener('DOMContentLoaded', () => {
  // Close flash on click
  $$('.flash').forEach(f => f.addEventListener('click', () => f.remove()));
});

