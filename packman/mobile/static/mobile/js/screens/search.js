import { appBar, avatar, denBadge, esc, icons, pluralize, rankTag } from "../components.js";
import { api, searchLocal } from "../api.js";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "cub", label: "Cubs" },
  { key: "parent", label: "Parents" },
  { key: "den", label: "By Den" },
];

function highlight(name, query) {
  const safe = esc(name);
  if (!query) return safe;
  const index = name.toLowerCase().indexOf(query.toLowerCase());
  if (index < 0) return safe;
  return (
    esc(name.slice(0, index)) +
    `<b style="color:var(--ink)">${esc(name.slice(index, index + query.length))}</b>` +
    esc(name.slice(index + query.length))
  );
}

function resultSection(title, rows) {
  if (!rows.length) return "";
  return `
    <div>
      <h2 class="sect">${esc(title)}</h2>
      <div class="card row-divided">${rows.join("")}</div>
    </div>
  `;
}

export async function renderSearch(container) {
  let query = "";
  let type = "all";
  let debounce = null;
  let denList = null;

  function cubRow(result) {
    return `
      <a class="row" href="#/profile/${encodeURIComponent(result.slug)}">
        ${avatar(result.avatar, result.name, "sm")}
        <div class="grow">
          <div class="row-title">${highlight(result.name, query)}</div>
          <div class="mono plain">${esc(result.subtitle)}</div>
        </div>
        ${rankTag(result.rank_key, result.rank)}
      </a>`;
  }

  function parentRow(result) {
    return `
      <a class="row" href="#/profile/${encodeURIComponent(result.slug)}">
        ${avatar(result.avatar, result.name, "sm")}
        <div class="grow">
          <div class="row-title">${highlight(result.name, query)}</div>
          <div class="mono plain">${esc(result.subtitle)}</div>
        </div>
        <span class="chev">&rsaquo;</span>
      </a>`;
  }

  function denRows(dens) {
    return `
      <div class="card row-divided">
        ${dens
          .map(
            (den) => `
          <a class="row" href="#/dens/${den.number}">
            ${denBadge(den.rank_key, den.rank_badge)}
            <div class="grow">
              <div class="row-title">Den ${den.number}${den.rank_plural ? ` · ${esc(den.rank_plural)}` : ""}</div>
              <div class="mono plain">${den.grade ? esc(den.grade) + " · " : ""}${esc(
              pluralize(den.cub_count, "Cub")
            )}</div>
            </div>
            <span class="chev">&rsaquo;</span>
          </a>`
          )
          .join("")}
      </div>`;
  }

  function paint(body) {
    // User-supplied values are escaped via esc() before interpolation.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${appBar(
        `
        <div class="appbar-title">Search</div>
        <div class="appbar-search">
          ${icons.searchGray}
          <input type="search" id="search-input" placeholder="Search parents &amp; Cubs" value="${esc(query)}">
        </div>`,
        { column: true }
      )}
      <div class="screen-scroll">
        <div class="pills">
          ${FILTERS.map(
            (f) => `<button class="pill${f.key === type ? " on" : ""}" data-type="${f.key}">${f.label}</button>`
          ).join("")}
        </div>
        ${body}
      </div>
    `;

    const input = container.querySelector("#search-input");
    input.focus();
    input.setSelectionRange(query.length, query.length);
    input.addEventListener("input", (event) => {
      query = event.target.value;
      clearTimeout(debounce);
      // Matching the cached directory is instant, so results land on the
      // keystroke; only the server fallback below waits for a pause in typing.
      refresh();
    });
    container.querySelectorAll(".pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        type = btn.dataset.type;
        clearTimeout(debounce);
        refresh();
      });
    });
  }

  function paintResults(cubs, parents) {
    const cubSection = resultSection("Cubs", cubs.map(cubRow));
    const parentSection = resultSection("Parents", parents.map(parentRow));
    if (!cubSection && !parentSection) {
      paint(`<p class="empty">No matches for &ldquo;${esc(query)}&rdquo;.</p>`);
      return false;
    }
    paint(cubSection + parentSection);
    return true;
  }

  /**
   * The cached index only carries each member's display name. The server also
   * matches middle names, and the legal first name of anybody who goes by a
   * nickname, so a local miss is worth one request to be certain of.
   */
  function scheduleRemoteSearch() {
    if (navigator.onLine === false) return;
    const asked = query;
    const askedType = type;
    debounce = setTimeout(async () => {
      try {
        const data = await api.search(asked, askedType);
        // The reader has typed on since; whatever is on screen is newer.
        if (asked !== query || askedType !== type) return;
        if (data.cubs.length || data.parents.length) paintResults(data.cubs, data.parents);
      } catch {
        // Offline or a transient failure — the local miss stands.
      }
    }, 250);
  }

  async function refresh() {
    if (type === "den") {
      if (!denList) {
        denList = (await api.dens()).dens;
      }
      paint(denRows(denList));
      return;
    }
    if (!query.trim()) {
      paint("");
      return;
    }
    const { cubs, parents } = searchLocal(query, type);
    if (!paintResults(cubs, parents)) scheduleRemoteSearch();
  }

  paint("");
}
