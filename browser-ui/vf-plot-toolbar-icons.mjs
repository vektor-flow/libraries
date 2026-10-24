// Deterministic vector geometry, 24-unit grid, one optical stroke weight.
export const PLOT_TOOLBAR_ICONS=Object.freeze({
 select:'<rect x="4" y="4" width="16" height="16" rx="1" stroke-dasharray="3 3"/><path d="m9 9 4 10 1-5 5-1Z"/>',
 first:'<path d="M5 5v14M19 12H9m5-5-5 5 5 5"/>',
 back:'<path d="m14 6-6 6 6 6"/>',
 forward:'<path d="m10 6 6 6-6 6"/>',
 last:'<path d="M19 5v14M5 12h10m-5-5 5 5-5 5"/>',
 'zoom-out':'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4M7.5 10.5h6"/>',
 'zoom-in':'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4M7.5 10.5h6m-3-3v6"/>',
 capture:'<path d="M8 6l1.5-2h5L16 6h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="4"/>',
 play:'<path d="m8 5 11 7-11 7Z"/>',
 pause:'<path d="M8 5v14M16 5v14"/>',
 video:'<rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 6-3v10l-6-3"/>',
 stop:'<rect x="5" y="5" width="14" height="14" rx="2"/>',
 pdf:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Zm0 0v6h6M8 13h8m-8 4h5"/>',
 png:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
 chevron:'<path d="m7 10 5 5 5-5"/>'
});
export function plotToolbarSvg(name) {
 const shape=PLOT_TOOLBAR_ICONS[name];if(!shape)throw new RangeError('Unknown toolbar icon');
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'+shape+'</svg>';
}
