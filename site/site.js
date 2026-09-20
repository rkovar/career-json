// Progressive enhancements: content and navigation remain readable without JS.
for (const group of document.querySelectorAll('[data-tabs]')) {
  const tabs = [...group.querySelectorAll('[data-tab]')];
  group.setAttribute('role', 'tablist');
  const select = (selected, focus = false) => {
    for (const tab of tabs) {
      const active = tab === selected;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      tab.classList.toggle('selected', active);
      const panel = document.getElementById(tab.getAttribute('aria-controls'));
      panel.setAttribute('role', 'tabpanel');
      panel.hidden = !active;
    }
    if (focus) selected.focus();
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', event => {
      const target = {ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1}[event.key];
      if (target !== undefined) { event.preventDefault(); select(tabs[target], true); }
    });
  });
  select(tabs[0]);
  group.hidden = false;
}
for (const button of document.querySelectorAll('[data-copy]')) {
  if (!navigator.clipboard?.writeText) continue;
  button.hidden = false;
  button.addEventListener('click', async () => {
    const status = button.closest('.terminal').querySelector('.copy-status');
    try {
      await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
      status.textContent = 'Commands copied. Paste them into your terminal.';
    } catch {
      status.textContent = 'Copy was unavailable. Select the commands above and copy them manually.';
    }
  });
}
