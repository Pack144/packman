import { appBar, avatar, esc, icons, rankTag } from "../components.js";
import { denLabel, familyOf, getDirectory, getFamilyRequirements } from "../api.js";

function profileBar(member, { me }) {
  const back = me
    ? ""
    : '<a class="appbar-back" href="javascript:history.back()" aria-label="Back">&lsaquo;</a>';
  // A cub's den titles the bar; adults have no den, so they get their own name.
  return appBar(`${back}<div class="appbar-title">${esc(denLabel(member) || member.name)}</div>`);
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

function familyCard(family) {
  if (!family.length) return "";
  return `
    <div>
      <h2 class="sect">Family</h2>
      <div class="card row-divided">
        ${family.map(familyRow).join("")}
      </div>
    </div>
  `;
}

// Maps the derived status the API sends to the pill that shows it. Keys are
// RequirementRecord.Health values.
const REQUIREMENT_TONES = {
  OK: "ok",
  SOON: "warn",
  EXP: "bad",
  NA: "muted",
  NEW: "muted",
};

/**
 * "Sept. 18, 2026" from the wire's ISO date. Split rather than passed to
 * Date(iso), which would read it as UTC and can land a day early west of
 * Greenwich.
 */
function expiryLabel(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function requirementRow(record) {
  const tone = REQUIREMENT_TONES[record.status] || "muted";
  const expires =
    record.status === "OK" || record.status === "SOON" || record.status === "EXP"
      ? record.expires_on
      : null;
  return `
    <div class="row req-row">
      <div class="grow">
        <div class="row-title">${esc(record.requirement)}</div>
        ${expires ? `<div class="mono plain">Expires ${esc(expiryLabel(expires))}</div>` : ""}
      </div>
      <span class="req-pill ${tone}">${esc(record.status_label)}</span>
    </div>`;
}

function requirementGroup(group) {
  if (!group.records.length) return "";
  return `
    <div class="req-group">
      <div class="req-who">${esc(group.name)}</div>
      <div class="card row-divided">
        ${group.records.map(requirementRow).join("")}
      </div>
    </div>`;
}

/**
 * The whole family's requirements, shown only on the viewer's own Me screen.
 * Someone else's profile never carries this: their paperwork isn't ours.
 */
function requirementsCard(requirements) {
  if (!requirements) return "";
  const groups = requirements.groups.map(requirementGroup).join("");
  if (!groups) return "";
  const summary = requirements.outstanding
    ? `<span class="req-pill warn">${requirements.outstanding} need${
        requirements.outstanding === 1 ? "s" : ""
      } attention</span>`
    : '<span class="req-pill ok">All up to date</span>';
  return `
    <div>
      <h2 class="sect">Membership Requirements</h2>
      <div class="req-summary">
        ${summary}
        <span class="mono plain">${esc(requirements.year_label)}</span>
      </div>
      ${groups}
    </div>
  `;
}

export async function renderProfile(container, slug, { me = false } = {}) {
  const directory = await getDirectory();
  // Only fetched for your own screen, and never blocks it: the section is
  // supplementary, so an offline or failed call just leaves it out.
  const requirements = me ? await getFamilyRequirements() : null;
  const member = directory.bySlug.get(slug);

  if (!member) {
    // Static copy only; no user data interpolated here.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${appBar('<a class="appbar-back" href="javascript:history.back()" aria-label="Back">&lsaquo;</a><div class="appbar-title">Profile</div>')}
      <div class="screen-scroll"><p class="empty">This profile could not be found.</p></div>
    `;
    return;
  }

  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${profileBar(member, { me })}
    <div class="screen-scroll">
      ${headerMarkup(member)}
      ${actionButtons(member)}
      ${contactCard(member)}
      ${familyCard(familyOf(directory, member))}
      ${requirementsCard(requirements)}
    </div>
  `;
}
