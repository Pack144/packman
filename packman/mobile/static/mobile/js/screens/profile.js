import { avatar, colorFor, esc, icons, initialsOf, rankTag } from "../components.js";
import { api } from "../api.js";

function heroMarkup(member, { me }) {
  const back = me
    ? ""
    : '<a class="back" href="javascript:history.back()" aria-label="Back">&lsaquo;</a>';
  const media = member.photo
    ? `<img src="${esc(member.photo)}" alt="${esc(member.name)}">`
    : `<div class="initials" style="background:${colorFor(member.name)}">${esc(initialsOf(member.name))}</div>`;
  const denTag = member.den ? rankTag(member.rank_key, member.den) : "";
  return `
    <div class="profile-hero">
      ${media}
      <div class="overlay"></div>
      ${back}
      <div class="caption">
        <div class="profile-name">${esc(member.name)}</div>
        ${
          denTag || member.grade
            ? `<div class="profile-meta">${denTag}${
                member.grade ? `<span class="profile-grade">${esc(member.grade)}</span>` : ""
              }</div>`
            : ""
        }
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
          <div class="row" style="padding:13px 15px">
            <span style="color:#8a919c">${icons.phone}</span>
            <div>
              <div class="mono">${esc(p.type)}</div>
              <a class="contact-value" href="tel:${esc(p.value)}">${esc(p.value)}</a>
            </div>
          </div>`
          )
          .join("")}
        ${member.emails
          .map(
            (e) => `
          <div class="row" style="padding:13px 15px">
            <span style="color:#8a919c">${icons.mail}</span>
            <div>
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

function familyCard(member) {
  if (!member.family.length) return "";
  return `
    <div>
      <h2 class="sect">Family</h2>
      <div class="card row-divided">
        ${member.family
          .map(
            (f) => `
          <a class="row" href="#/profile/${encodeURIComponent(f.slug)}">
            ${avatar(f.avatar, f.name, "sm")}
            <div class="grow">
              <div class="name-line">
                <span class="row-title">${esc(f.name)}</span>
                ${f.rank ? rankTag(f.rank_key, f.rank) : ""}
              </div>
              <div class="mono plain">${esc(f.relation)}</div>
            </div>
            <span class="chev">&rsaquo;</span>
          </a>`
          )
          .join("")}
      </div>
    </div>
  `;
}

export async function renderProfile(container, slug, { me = false } = {}) {
  const member = await api.member(slug);

  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    <div class="screen-scroll flush">
      ${heroMarkup(member, { me })}
      <div class="profile-body">
        ${actionButtons(member)}
        ${contactCard(member)}
        ${familyCard(member)}
      </div>
    </div>
  `;
}
