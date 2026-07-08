import { badge, chip, esc, pluralize } from "../components.js";
import { api } from "../api.js";
import { denDetailMarkup } from "./den-shared.js";

export async function renderDens(container) {
  const data = await api.dens();
  const groups = [];
  data.dens.forEach((den) => {
    let group = groups.find((g) => g.rank === den.rank);
    if (!group) {
      group = { rank: den.rank, dens: [] };
      groups.push(group);
    }
    group.dens.push(den);
  });

  container.innerHTML = `
    <h1 class="hi">All Dens</h1>
    ${groups
      .map(
        (group) => `
      <span class="mono section-label">${esc(group.rank.toUpperCase())} &middot; ${esc(
          pluralize(group.dens.length, "DEN").toUpperCase()
        )}</span>
      <div class="card list-card">
        ${group.dens
          .map(
            (den, i) => `
          ${i > 0 ? '<hr class="hr">' : ""}
          <a class="row${den.is_mine ? " mine" : ""}" href="#/dens/${den.number}">
            ${badge(den.rank_letter)}
            <div class="col">
              <div class="row-title">Den ${den.number} &middot; ${esc(den.rank)}s</div>
              <span class="mono">${den.grade ? esc(den.grade.toUpperCase()) + " &middot; " : ""}${esc(
              pluralize(den.cub_count, "CUB").toUpperCase()
            )}</span>
            </div>
            ${den.my_cub ? chip(den.my_cub.toUpperCase()) : ""}
            <span class="chev">&rsaquo;</span>
          </a>`
          )
          .join("")}
      </div>`
      )
      .join("")}
  `;
}

export async function renderDenDetail(container, number) {
  const den = await api.den(number);
  container.innerHTML = `
    <a class="back-link" href="#/dens">&lsaquo; All Dens</a>
    ${denDetailMarkup(den)}
  `;
}
