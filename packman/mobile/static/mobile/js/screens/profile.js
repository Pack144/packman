import { avatar, badge, chip, esc } from "../components.js";
import { api } from "../api.js";

export async function renderProfile(container, slug) {
  const member = await api.member(slug);

  const pills = [];
  if (member.phone_numbers.length) {
    const number = member.phone_numbers[0].value;
    pills.push(`<a class="pill" href="tel:${esc(number)}">Call</a>`);
    pills.push(`<a class="pill" href="sms:${esc(number)}">Text</a>`);
  }
  if (member.emails.length) {
    pills.push(`<a class="pill" href="mailto:${esc(member.emails[0])}">Email</a>`);
  }

  container.innerHTML = `
    <a class="back-link" href="javascript:history.back()">&lsaquo; Back</a>
    <div class="profile-header">
      ${avatar(member.avatar, member.name, "lg")}
      <div class="row-title lg">${esc(member.name)}</div>
      ${member.den ? `<div class="row chip-row">${badge(member.rank_letter)}${chip(member.den)}</div>` : ""}
    </div>
    ${pills.length ? `<div class="row chip-row pills">${pills.join("")}</div>` : ""}
    ${
      member.phone_numbers.length || member.emails.length
        ? `<div class="card list-card">
      ${member.phone_numbers
        .map(
          (p, i) => `
        ${i > 0 ? '<hr class="hr">' : ""}
        <div class="row"><div class="col"><span class="mono">${esc(
          p.type.toUpperCase()
        )}</span><div>${esc(p.value)}</div></div></div>`
        )
        .join("")}
      ${member.emails
        .map(
          (e) => `
        <hr class="hr">
        <div class="row"><div class="col"><span class="mono">EMAIL</span><div>${esc(e)}</div></div></div>`
        )
        .join("")}
    </div>`
        : ""
    }
    ${
      member.family.length
        ? `<span class="mono section-label">FAMILY</span>
      <div class="card list-card">
        ${member.family
          .map(
            (f, i) => `
          ${i > 0 ? '<hr class="hr">' : ""}
          <a class="row" href="#/profile/${encodeURIComponent(f.slug)}">
            ${avatar(f.avatar, f.name, "sm")}
            <div class="col"><div class="row-title">${esc(f.name)}</div><span class="mono">${esc(
              f.relation.toUpperCase()
            )}</span></div>
            <span class="chev">&rsaquo;</span>
          </a>`
          )
          .join("")}
      </div>`
        : ""
    }
  `;
}
