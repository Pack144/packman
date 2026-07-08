import { avatar, badge, esc, pluralize } from "../components.js";

export function denDetailMarkup(den) {
  return `
    <div class="card den-header-card">
      <div class="row">
        ${badge(den.rank_letter)}
        <div class="col">
          <div class="row-title lg">${esc(den.rank)} Den</div>
          <span class="mono">DEN ${den.number} &middot; ${esc(pluralize(den.cub_count, "CUB").toUpperCase())}</span>
        </div>
      </div>
    </div>
    ${den.leaders
      .map(
        (leader) => `
      <div class="card">
        <div class="row">
          ${avatar(leader.avatar, leader.name, "md")}
          <div class="col">
            <div class="row-title">${esc(leader.name)}</div>
            <span class="mono">${esc(leader.position.toUpperCase())}</span>
          </div>
        </div>
      </div>`
      )
      .join("")}
    <span class="mono section-label">CUBS &amp; FAMILIES</span>
    <div class="card list-card">
      ${
        den.roster.length
          ? den.roster
              .map(
                (entry, i) => `
        ${i > 0 ? '<hr class="hr">' : ""}
        <a class="row" href="#/profile/${encodeURIComponent(entry.scout.slug)}">
          ${avatar(entry.scout.avatar, entry.scout.name, "sm")}
          <div class="col">
            <div class="row-title">${esc(entry.scout.name)} ${badge(entry.scout.rank_letter)}</div>
            <span class="mono">${esc(entry.parents.map((p) => p.name).join(" & ").toUpperCase()) || "&mdash;"}</span>
          </div>
          <span class="chev">&rsaquo;</span>
        </a>`
              )
              .join("")
          : '<p class="empty">No cubs assigned to this den yet.</p>'
      }
    </div>
  `;
}
