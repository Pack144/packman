import { appBar, avatar, esc, icons, rankTag } from "../components.js";
import { api } from "../api.js";

function profileBar(member, { me }) {
  const back = me
    ? ""
    : '<a class="appbar-back" href="javascript:history.back()" aria-label="Back">&lsaquo;</a>';
  // A cub's den titles the bar; adults have no den, so they get their own name.
  return appBar(`${back}<div class="appbar-title">${esc(member.den || member.name)}</div>`);
}

function headerMarkup(member) {
  // "Den 4 · 2nd Grade" — either half stands on its own if the other is missing.
  const line = [member.den_number ? `Den ${member.den_number}` : "", member.grade || ""]
    .filter(Boolean)
    .join(" · ");
  return `
    <div class="profile-header">
      ${avatar(member.photo, member.name, "lg")}
      <div class="profile-ident">
        <div class="profile-name">${esc(member.name)}${
          member.title ? `<span class="profile-title">, ${esc(member.title)}</span>` : ""
        }</div>
        ${line ? `<div class="profile-grade">${esc(line)}</div>` : ""}
        ${member.rank_plural ? rankTag(member.rank_key, member.rank_plural) : ""}
      </div>
    </div>
  `;
}

function actionButtons(member) {
  const phone = member.phone_numbers[0]?.value;
  const email = member.emails[0];
  const buttons = [];
  if (phone) {
    buttons.push(`<a class="action-btn primary" href="tel:${esc(phone)}">${icons.phone}Call</a>`);
    buttons.push(`<a class="action-btn" href="sms:${esc(phone)}">${icons.message}Text</a>`);
  }
  if (email) {
    buttons.push(`<a class="action-btn" href="mailto:${esc(email)}">${icons.mail}Email</a>`);
  }
  return buttons.length ? `<div class="action-row">${buttons.join("")}</div>` : "";
}

function contactCard(member) {
  if (!member.phone_numbers.length && !member.emails.length) return "";
  return `
    <div>
      <h2 class="sect">Contact</h2>
      <div class="card row-divided">
        ${member.phone_numbers
          .map(
            (p) => `
          <div class="row contact-row">
            <div class="grow">
              <div class="mono">${esc(p.type)}</div>
              <a class="contact-value" href="tel:${esc(p.value)}">${esc(p.value)}</a>
            </div>
          </div>`
          )
          .join("")}
        ${member.emails
          .map(
            (e) => `
          <div class="row contact-row">
            <div class="grow">
              <div class="mono">Email</div>
              <a class="contact-value" href="mailto:${esc(e)}">${esc(e)}</a>
            </div>
          </div>`
          )
          .join("")}
      </div>
    </div>
  `;
}

function familyRow(f) {
  const inner = `
    ${avatar(f.avatar, f.name, "sm")}
    <div class="grow">
      <div class="name-line">
        <span class="row-title">${esc(f.name)}</span>
        ${f.rank ? rankTag(f.rank_key, f.rank) : ""}
      </div>
      <div class="mono plain">${esc(f.relation)}</div>
    </div>
  `;
  // A sibling who's graduated or left the Pack is outside the directory's
  // visibility scope — their profile 404s — so they're listed but not linked.
  if (!f.active) {
    return `<div class="row row-disabled">${inner}</div>`;
  }
  return `
    <a class="row" href="#/profile/${encodeURIComponent(f.slug)}">
      ${inner}
      <span class="chev">&rsaquo;</span>
    </a>`;
}

function familyCard(member) {
  if (!member.family.length) return "";
  return `
    <div>
      <h2 class="sect">Family</h2>
      <div class="card row-divided">
        ${member.family.map(familyRow).join("")}
      </div>
    </div>
  `;
}

export async function renderProfile(container, slug, { me = false } = {}) {
  const member = await api.member(slug);

  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${profileBar(member, { me })}
    <div class="screen-scroll">
      ${headerMarkup(member)}
      ${actionButtons(member)}
      ${contactCard(member)}
      ${familyCard(member)}
    </div>
  `;
}
