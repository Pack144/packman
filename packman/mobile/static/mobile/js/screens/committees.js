import { appBar, esc, titleBar } from "../components.js";
import { api } from "../api.js";

// Marks a committee as Pack Leadership (Akela, Assistant Akelas, Den
// Leaders) in the list — drawn with currentColor so `.committee-star` can
// tint it gold without a second icon variant.
function starIcon() {
  return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l2.9 6.3 6.9.7-5.2 4.6 1.5 6.8L12 17.6l-6.1 3.3 1.5-6.8-5.2-4.6 6.9-.7z"/></svg>';
}

export async function renderCommittees(container) {
  const data = await api.committees();
  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${titleBar("Committees")}
    <div class="screen-scroll">
      ${
        data.committees.length
          ? `<div class="card row-divided">
        ${data.committees
          .map(
            (committee) => `
          <a class="row" href="#/committees/${encodeURIComponent(committee.slug)}">
            <div class="grow"><span class="committee-name">${esc(committee.name)}</span></div>
            ${committee.leadership ? `<span class="committee-star">${starIcon()}</span>` : ""}
          </a>`
          )
          .join("")}
      </div>`
          : '<p class="empty">No committees have been set up yet.</p>'
      }
    </div>
  `;
}

function memberRow(member) {
  return `
    <a class="row" href="#/profile/${encodeURIComponent(member.slug)}">
      <div class="grow"><div class="row-title">${esc(member.name)}</div></div>
      <span class="chev">&rsaquo;</span>
    </a>
  `;
}

export async function renderCommitteeDetail(container, slug) {
  // The selected Pack Year; null asks the API for its default (the current
  // year, or the committee's most recent one if it has none).
  let year = null;

  async function paint() {
    const committee = await api.committee(slug, year);
    year = committee.year;
    const roster = [...committee.akelas, ...committee.members];

    // User-supplied values are escaped via esc() before interpolation.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${appBar(`
        <a href="#/committees" style="color:#fff;font-size:22px;line-height:1;padding-right:2px" aria-label="Back to Committees">&lsaquo;</a>
        <div class="appbar-title">Committees</div>
      `)}
      <div class="screen-scroll">
        <div class="committee-head">
          <h1 class="h1red">${esc(committee.name)}</h1>
          ${
            committee.years.length > 1
              ? `<select class="pill" id="committee-year" aria-label="Pack Year">
            ${committee.years
              .map(
                (y) => `<option value="${y.year}"${y.year === committee.year ? " selected" : ""}>${esc(y.label)}</option>`
              )
              .join("")}
          </select>`
              : `<span class="pill">${esc(committee.year_label)}</span>`
          }
        </div>
        ${committee.description ? `<p class="committee-desc">${esc(committee.description)}</p>` : ""}
        <div class="card row-divided">
          ${
            roster.length
              ? roster.map(memberRow).join("")
              : '<p class="empty" style="padding:16px">No members assigned yet.</p>'
          }
        </div>
      </div>
    `;

    container.querySelector("#committee-year")?.addEventListener("change", (event) => {
      year = Number(event.target.value);
      paint();
    });
  }

  await paint();
}
