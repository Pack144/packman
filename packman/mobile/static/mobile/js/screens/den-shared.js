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

export function denDetailMarkup(den) {
  return `
    ${leaderCards(den.leaders)}
    ${rosterCard(den)}
  `;
}
