import { appBar, esc } from "../components.js";
import { committeeYear, getDirectory, packYearLabel } from "../api.js";

function memberRow(member) {
  // A committee roster can span years; someone who served a while back may
  // have left the pack entirely since — named, but not linked to a profile.
  if (!member.linked) {
    return `
      <div class="row row-disabled">
        <div class="grow"><div class="row-title">${esc(member.name)}</div></div>
      </div>
    `;
  }
  return `
    <a class="row" href="#/profile/${encodeURIComponent(member.slug)}">
      <div class="grow"><div class="row-title">${esc(member.name)}</div></div>
      <span class="chev">&rsaquo;</span>
    </a>
  `;
}

export async function renderCommitteeDetail(container, slug) {
  const directory = await getDirectory();
  const committee = directory.committees.find((c) => c.slug === slug);
  if (!committee) {
    // Static copy only; no user data interpolated here.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${appBar(`
        <a href="#/search" style="color:#fff;font-size:22px;line-height:1;padding-right:2px" aria-label="Back to Search">&lsaquo;</a>
        <div class="appbar-title">Committees</div>
      `)}
      <div class="screen-scroll"><p class="empty">This committee could not be found.</p></div>
    `;
    return;
  }

  // The selected Pack Year; null asks committeeYear() for its default (the
  // most recent year that has a roster).
  let year = null;

  function paint() {
    const view = committeeYear(committee, year);
    year = view.year;
    const roster = view.members;

    // User-supplied values are escaped via esc() before interpolation.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${appBar(`
        <a href="#/search" style="color:#fff;font-size:22px;line-height:1;padding-right:2px" aria-label="Back to Search">&lsaquo;</a>
        <div class="appbar-title">Committees</div>
      `)}
      <div class="screen-scroll">
        <div class="committee-head">
          <h1 class="h1red">${esc(view.name)}</h1>
          ${
            view.years.length > 1
              ? `<select class="pill" id="committee-year" aria-label="Pack Year">
            ${view.years
              .map((y) => `<option value="${y}"${y === view.year ? " selected" : ""}>${esc(packYearLabel(y))}</option>`)
              .join("")}
          </select>`
              : `<span class="pill">${esc(view.year_label)}</span>`
          }
        </div>
        ${view.description ? `<p class="committee-desc">${esc(view.description)}</p>` : ""}
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

  paint();
}
