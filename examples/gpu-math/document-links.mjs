import {parseColor} from './colors.mjs';

export const encodeDestination = value => encodeURIComponent(value);
export const decodeDestination = value => decodeURIComponent(value);
export const uriValue = value => value.replace(/\\([%#&_{}$])/g, '$1');

export function linkAppearance(options = [], diagnostics = [], initial = null) {
  const result = {enabled: true, borderWidth: 1, colorlinks: false,
    ref: [1, 0, 0, 1], cite: [0, 1, 0, 1], url: [0, 1, 1, 1], ...initial};
  for (const option of options) {
    let [key, ...parts] = option.split('='), value = parts.join('=').trim();
    key = key.trim(); value = value.replace(/^\{(.*)\}$/, '$1');
    if (key === 'hidelinks' && value !== 'false') { result.borderWidth = 0; result.colorlinks = false; }
    else if (key === 'colorlinks') { result.colorlinks = value !== 'false'; result.borderWidth = result.colorlinks ? 0 : 1; }
    else if (key === 'pdfborder') {
      const numbers = value.split(/\s+/).map(Number);
      if (numbers.length === 3 && numbers.every(Number.isFinite) && numbers[2] >= 0) result.borderWidth = numbers[2];
      else diagnostics.push('Unsupported hyperref pdfborder: ' + value);
    } else if (['linkcolor', 'citecolor', 'urlcolor', 'allcolors'].includes(key)) {
      const color = parseColor(value);
      if (!color) diagnostics.push('Unsupported hyperref color: ' + value);
      else for (const kind of key === 'allcolors' ? ['ref', 'cite', 'url'] : [key === 'linkcolor' ? 'ref' : key === 'citecolor' ? 'cite' : 'url']) result[kind] = color;
    } else if (key && !['hidelinks', 'unicode', 'pdfencoding', 'bookmarks', 'bookmarksopen', 'bookmarksnumbered', 'pdfusetitle', 'breaklinks'].includes(key)) diagnostics.push('Unsupported hyperref setup: ' + key);
  }
  return result;
}

export function markDestination(items, ids = []) {
  const item = items.find(item => item.kind !== 'link');
  if (item && ids.length) item.destinationIds = [...new Set([...(item.destinationIds ?? []), ...ids])];
}

export function collectDestinations(pages, data) {
  const destinations = Object.create(null);
  destinations.document = {page: 0, x: 0, y: 0};
  pages.forEach((page, index) => {
    destinations['page:' + (index + 1)] = {page: index, x: 0, y: 0};
    for(const point of page.destinations??[])destinations[point.id]={page:index,x:point.x,y:point.y};
    for (const item of page.items) for (const id of item.destinationIds ?? []) {
      if (Object.hasOwn(destinations, id)) continue;
      const top = data.tiles?.[item.key]?.plane?.[1] ?? 0;
      destinations[id] = {page: index, x: item.x, y: item.y + top * (item.sy ?? 1)};
    }
  });
  return destinations;
}
