import { appBar, denBadge, esc, pluralize, rankColor, rankTag, titleBar } from "../components.js";
import { api } from "../api.js";
import { denDetailMarkup } from "./den-shared.js";

export async function renderDens(container) {
  const data = await api.dens();
  const groups = [];
  data.dens.forEach((den) => {
    let group = groups.find((g) => g.rank === den.rank);
    if (!group) {
      group = { rank: den.rank, rank_key: den.rank_key, dens: [] };
      groups.push(group);
    }
    group.dens.push(den);
  });

  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${titleBar("All Dens", pluralize(data.dens.length, "DEN"))}
    <div class="screen-scroll">
      ${groups
        .map(
          (group) => `
        <div>
          <div class="group-head">
            <span class="sect" style="color:${rankColor(group.rank_key)}">${esc(group.rank || "Unranked")}</span>
            <span class="mono">${esc(pluralize(group.dens.length, "DEN"))}</span>
          </div>
          <div class="card row-divided">
            ${group.dens
              .map(
                (den) => `
              <a class="row${den.is_mine ? " mine" : ""}" href="#/dens/${den.number}">
                ${denBadge(den.rank_key, den.rank_badge)}
                <div class="grow">
                  <div class="name-line">
                    <span class="row-title">Den ${den.number}${den.rank_plural ? ` · ${esc(den.rank_plural)}` : ""}</span>
                    ${den.my_cub ? rankTag(den.rank_key, den.my_cub) : ""}
                  </div>
                  <div class="mono plain">${den.grade ? esc(den.grade) + " · " : ""}${esc(
                  pluralize(den.cub_count, "Cub")
                )}</div>
                </div>
                <span class="chev">&rsaquo;</span>
              </a>`
              )
              .join("")}
          </div>
        </div>`
        )
        .join("")}
    </div>
  `;
}

export async function renderDenDetail(container, number) {
  const den = await api.den(number);
  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${appBar(`
      <a href="#/dens" style="color:#fff;font-size:22px;line-height:1;padding-right:2px">&lsaquo;</a>
      <div class="appbar-title">Den ${den.number}${den.rank_plural ? ` · ${esc(den.rank_plural)}` : ""}</div>
      <div class="appbar-meta">${den.grade ? esc(den.grade.toUpperCase()) + " · " : ""}${esc(
    pluralize(den.cub_count, "CUB")
  )}</div>
    `)}
    <div class="screen-scroll">
      ${denDetailMarkup(den)}
    </div>
  `;
}
