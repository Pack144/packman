export function esc(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

export function avatar(url, name, size = "md") {
  return `<img class="av ${size}" src="${esc(url)}" alt="${esc(name)}" loading="lazy">`;
}

export function badge(letter) {
  return `<span class="badge">${esc(letter || "?")}</span>`;
}

export function chip(text) {
  return `<span class="chip">${esc(text)}</span>`;
}

export function tag(text) {
  return `<span class="tag">${esc(text)}</span>`;
}

export function pluralize(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}
