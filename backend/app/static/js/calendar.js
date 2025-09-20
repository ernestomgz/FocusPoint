// Reusable DD/MM/YYYY calendar as a popup
(function () {
  const fmt2 = (n) => (n < 10 ? '0' + n : '' + n);
  function toDmy(d){ return fmt2(d.getDate())+'/'+fmt2(d.getMonth()+1)+'/'+d.getFullYear(); }
  function parseDmy(s){
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec((s||'').trim());
    if(!m) return null;
    const d = new Date(+m[3], +m[2]-1, +m[1]);
    return isNaN(d) ? null : d;
  }

  function attach(el){
    let val = parseDmy(el.value) || new Date();
    let view = new Date(val.getFullYear(), val.getMonth(), 1);

    const pop = document.createElement('div');
    pop.className = 'cal-pop';
    pop.style.display = 'none';
    const head = document.createElement('div');
    head.className = 'cal-head';
    const prev = document.createElement('button'); prev.type='button'; prev.className='cal-btn'; prev.textContent='«';
    const next = document.createElement('button'); next.type='button'; next.className='cal-btn'; next.textContent='»';
    const title = document.createElement('div'); title.className='cal-head-title';
    head.append(prev, title, next);

    const dows = document.createElement('div'); dows.className='cal-grid';
    ['Mo','Tu','We','Th','Fr','Sa','Su'].forEach(x=>{
      const el = document.createElement('div'); el.className='cal-dow'; el.textContent=x; dows.appendChild(el);
    });

    const grid = document.createElement('div'); grid.className='cal-grid';
    pop.append(head, dows, grid);
    document.body.appendChild(pop);

    function render(){
      title.textContent = view.toLocaleString(undefined, {month:'long', year:'numeric'});
      grid.innerHTML = '';
      const firstDow = (new Date(view.getFullYear(), view.getMonth(), 1).getDay()+6)%7; // Mon=0
      const daysInMonth = new Date(view.getFullYear(), view.getMonth()+1, 0).getDate();
      const prevDays = new Date(view.getFullYear(), view.getMonth(), 0).getDate();

      for(let i=0;i<firstDow;i++){
        const day = prevDays - firstDow + 1 + i;
        const c = document.createElement('div'); c.className='cal-cell m'; c.textContent = day;
        c.addEventListener('click', ()=>{ view.setMonth(view.getMonth()-1); render(); });
        grid.appendChild(c);
      }
      for(let d=1; d<=daysInMonth; d++){
        const c = document.createElement('div'); c.className='cal-cell'; c.textContent = d;
        if (val.getFullYear()===view.getFullYear() && val.getMonth()===view.getMonth() && val.getDate()===d){
          c.style.background='#e9e6ff';
        }
        c.addEventListener('click', ()=>{
          val = new Date(view.getFullYear(), view.getMonth(), d);
          el.value = toDmy(val);
          hide();
        });
        grid.appendChild(c);
      }
      const totalCells = firstDow + daysInMonth;
      const nextCount = (totalCells<=35? (35-totalCells) : (42-totalCells));
      for(let d=1; d<=nextCount; d++){
        const c = document.createElement('div'); c.className='cal-cell m'; c.textContent = d;
        c.addEventListener('click', ()=>{ view.setMonth(view.getMonth()+1); render(); });
        grid.appendChild(c);
      }
    }

    function show(){
      const r = el.getBoundingClientRect();
      pop.style.left = (window.scrollX + r.left) + 'px';
      pop.style.top  = (window.scrollY + r.bottom + 6) + 'px';
      pop.style.display='block';
      render();
    }
    function hide(){ pop.style.display='none'; }

    el.addEventListener('focus', show);
    el.addEventListener('click', show);
    document.addEventListener('click', (e)=>{ if(!pop.contains(e.target) && e.target!==el) hide(); });
    prev.addEventListener('click', ()=>{ view.setMonth(view.getMonth()-1); render(); });
    next.addEventListener('click', ()=>{ view.setMonth(view.getMonth()+1); render(); });
  }

  window.FocusPointCalendar = {
    attachAll() { document.querySelectorAll('.date-dmy').forEach(attach); }
  };
})();

