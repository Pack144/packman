import { denBadge, esc, pluralize, setMyDenCount, titleBar } from "../components.js";
import { getDirectory, myActiveChildren, myDens } from "../api.js";
import { bindDenViewTabs, denDetailMarkup } from "./den-shared.js";

function denHeaderCard(den) {
  return `
    <div class="card">
      <div class="row" style="padding:14px 15px">
        ${denBadge(den.rank_key, den.rank_badge)}
        <div class="grow">
          <div class="row-title" style="font-size:16px">Den ${den.number}${
    den.rank_plural ? ` · ${esc(den.rank_plural)}` : ""
  }</div>
          <div class="mono plain">${den.grade ? esc(den.grade) + " · " : ""}${esc(
    pluralize(den.cub_count, "Cub")
  )}${den.my_cub ? ` · ${esc(den.my_cub)}’s den` : ""}</div>
        </div>
      </div>
    </div>
  `;
}

export async function renderMyDens(container) {
  const directory = await getDirectory();
  const dens = myDens(directory);
  const cubCount = myActiveChildren(directory).length;
  setMyDenCount(dens.length);
  const title = dens.length === 1 ? "My Den" : "My Dens";

  if (!dens.length) {
    // Static copy only; no user data interpolated here.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${titleBar("My Dens")}
      <div class="screen-scroll"><p class="empty">None of your cubs are assigned to a den yet.</p></div>
    `;
    return;
  }

  let active = 0;
  let view = "cubs";

  function paint() {
    const den = dens[active];
    // User-supplied values are escaped via esc() before interpolation.
    // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
    container.innerHTML = `
      ${titleBar(title, `${cubCount} CUB${cubCount === 1 ? "" : "S"}`)}
      <div class="screen-scroll">
        ${
          dens.length > 1
            ? `<div class="segmented">
          ${dens
            .map(
              (d, i) => `
            <button class="segment${i === active ? " on" : ""}" data-index="${i}">
              <div class="seg-title">${esc(d.rank_plural || "Den " + d.number)}</div>
              <div class="mono">${d.my_cub ? esc(d.my_cub) + " · " : ""}Den ${d.number}</div>
            </button>`
            )
            .join("")}
        </div>`
            : denHeaderCard(den)
        }
        ${denDetailMarkup(den, view)}
      </div>
    `;
    container.querySelectorAll(".segment[data-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        active = Number(btn.dataset.index);
        paint();
      });
    });
    bindDenViewTabs(container, (newView) => {
      view = newView;
      paint();
    });
  }

  paint();
}
