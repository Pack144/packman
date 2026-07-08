import { avatar, esc, tag } from "../components.js";
import { api } from "../api.js";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "cub", label: "Cubs" },
  { key: "parent", label: "Parents" },
];

export async function renderSearch(container) {
  let query = "";
  let type = "all";
  let debounce = null;

  function paint(results) {
    container.innerHTML = `
      <div class="search-box">
        <input type="search" id="search-input" placeholder="Search parents &amp; Cubs" value="${esc(query)}">
      </div>
      <div class="row chip-row">
        ${FILTERS.map(
          (f) => `<button class="chip-btn${f.key === type ? " sel" : ""}" data-type="${f.key}">${f.label}</button>`
        ).join("")}
      </div>
      ${
        results.length
          ? `<span class="mono section-label">RESULTS</span>
        <div class="card list-card">
          ${results
            .map(
              (r, i) => `
            ${i > 0 ? '<hr class="hr">' : ""}
            <a class="row" href="#/profile/${encodeURIComponent(r.slug)}">
              ${avatar(r.avatar, r.name, "sm")}
              <div class="col">
                <div class="row-title">${esc(r.name)}</div>
                <span class="mono">${esc(r.subtitle.toUpperCase())}</span>
              </div>
              ${tag(r.type === "cub" ? "CUB" : "PARENT")}
            </a>`
            )
            .join("")}
        </div>`
          : query.trim()
          ? `<p class="empty">No matches for &ldquo;${esc(query)}&rdquo;.</p>`
          : ""
      }
    `;

    const input = container.querySelector("#search-input");
    input.focus();
    input.setSelectionRange(query.length, query.length);
    input.addEventListener("input", (event) => {
      query = event.target.value;
      clearTimeout(debounce);
      debounce = setTimeout(runSearch, 250);
    });
    container.querySelectorAll(".chip-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        type = btn.dataset.type;
        runSearch();
      });
    });
  }

  async function runSearch() {
    if (!query.trim()) {
      paint([]);
      return;
    }
    const data = await api.search(query, type);
    paint(data.results);
  }

  paint([]);
}
