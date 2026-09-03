import { avatar, esc, icons, rankTag } from "../components.js";

export function leaderCards(leaders) {
  return leaders
    .map(
      (leader) => `
    <div class="card">
      <div class="row" style="padding:14px 15px">
        ${avatar(leader.avatar, leader.name, "md")}
        <div class="grow">
          <div class="row-title" style="font-size:16px">${esc(leader.name)}</div>
          <div class="mono">${esc(leader.position)}</div>
        </div>
        ${leader.phone ? `<a class="icon-btn" style="color:var(--accent)" href="tel:${esc(leader.phone)}" aria-label="Call ${esc(leader.name)}">${icons.phone}</a>` : ""}
        ${leader.phone ? `<a class="icon-btn" style="color:var(--accent)" href="sms:${esc(leader.phone)}" aria-label="Text ${esc(leader.name)}">${icons.message}</a>` : ""}
        ${leader.email ? `<a class="icon-btn" style="color:var(--accent)" href="mailto:${esc(leader.email)}" aria-label="Email ${esc(leader.name)}">${icons.mail}</a>` : ""}
      </div>
    </div>`
    )
    .join("");
}

export function rosterCard(den) {
  return `
    <section>
      <h2 class="sect">Cubs &amp; Families</h2>
      <div class="card row-divided">
        ${
          den.roster.length
            ? den.roster
                .map(
                  (entry) => `
          <a class="row" href="#/profile/${encodeURIComponent(entry.scout.slug)}">
            ${avatar(entry.scout.avatar, entry.scout.name, "sm")}
            <div class="grow">
              <div class="name-line">
                <span class="row-title">${esc(entry.scout.name)}</span>
                ${rankTag(entry.scout.rank_key, entry.scout.rank)}
              </div>
              <div class="mono plain">${esc(entry.parents.map((p) => p.name).join(" & ")) || "&mdash;"}</div>
            </div>
            <span class="chev">&rsaquo;</span>
          </a>`
                )
                .join("")
            : '<p class="empty" style="padding:16px">No cubs assigned to this den yet.</p>'
        }
      </div>
    </section>
  `;
}

/** Same den roster, grouped by parent instead of by Cub. Each parent's cub
 * list only ever includes names from this den's own roster, so a parent with
 * kids in multiple dens never shows a sibling from another den here. */
export function parentsCard(den) {
  const parents = new Map();
  den.roster.forEach((entry) => {
    entry.parents.forEach((parent) => {
      if (!parents.has(parent.slug)) {
        parents.set(parent.slug, { slug: parent.slug, name: parent.name, avatar: parent.avatar, cubs: [] });
      }
      parents.get(parent.slug).cubs.push(entry.scout.name);
    });
  });
  const list = [...parents.values()].sort((a, b) => a.name.localeCompare(b.name));
  return `
    <section>
      <h2 class="sect">Parents</h2>
      <div class="card row-divided">
        ${
          list.length
            ? list
                .map(
                  (parent) => `
          <a class="row" href="#/profile/${encodeURIComponent(parent.slug)}">
            ${avatar(parent.avatar, parent.name, "sm")}
            <div class="grow">
              <div class="row-title">${esc(parent.name)}</div>
              <div class="mono plain">${esc(parent.cubs.join(" & "))}</div>
            </div>
            <span class="chev">&rsaquo;</span>
          </a>`
                )
                .join("")
            : '<p class="empty" style="padding:16px">No parents found for this den yet.</p>'
        }
      </div>
    </section>
  `;
}

/** Segmented Cubs/Parents toggle shown above a den's roster. */
export function denViewTabs(view) {
  return `
    <div class="segmented">
      <button class="segment${view === "cubs" ? " on" : ""}" data-den-view="cubs">
        <div class="seg-title">Cubs</div>
      </button>
      <button class="segment${view === "parents" ? " on" : ""}" data-den-view="parents">
        <div class="seg-title">Parents</div>
      </button>
    </div>
  `;
}

/** Wires clicks on the tabs rendered by denViewTabs() within `container`. */
export function bindDenViewTabs(container, onChange) {
  container.querySelectorAll("[data-den-view]").forEach((btn) => {
    btn.addEventListener("click", () => onChange(btn.dataset.denView));
  });
}

export function denDetailMarkup(den, view = "cubs") {
  return `
    ${leaderCards(den.leaders)}
    ${denViewTabs(view)}
    ${view === "parents" ? parentsCard(den) : rosterCard(den)}
  `;
}
