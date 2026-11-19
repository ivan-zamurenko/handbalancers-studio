// Real data will populate these panels when training facts exist. No synthetic series.
const tabs = [...document.querySelectorAll('.progress-tabs [role=tab]')];
function select(tab, focus = false) {
  for (const item of tabs) {
    const active = item === tab;
    item.setAttribute('aria-selected', String(active));
    item.tabIndex = active ? 0 : -1;
    document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
  }
  if (focus) tab.focus({preventScroll:true});
  tab.scrollIntoView({block:'nearest',inline:'nearest'});
}
for (const [index,tab] of tabs.entries()) {
  tab.addEventListener('click',()=>select(tab));
  tab.addEventListener('keydown',event=>{
    const next = event.key === 'ArrowRight' ? (index+1)%tabs.length
      : event.key === 'ArrowLeft' ? (index+tabs.length-1)%tabs.length
      : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length-1 : null;
    if (next !== null) { event.preventDefault(); select(tabs[next],true); }
  });
}
document.addEventListener('studio:language-changed', () => {
  const tab = tabs.find(item => item.getAttribute('aria-selected') === 'true');
  if (!tab) return;
  const list = tab.parentElement;
  const selected = tab.getBoundingClientRect();
  const viewport = list.getBoundingClientRect();
  // Translation changes widths; reveal the selected pill without scrolling the page.
  if (selected.right > viewport.right) list.scrollLeft += selected.right - viewport.right + 4;
  else if (selected.left < viewport.left) list.scrollLeft -= viewport.left - selected.left + 4;
});
