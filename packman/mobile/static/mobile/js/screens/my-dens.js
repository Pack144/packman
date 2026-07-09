import { denBadge, esc, pluralize, setMyDenCount, titleBar } from "../components.js";
import { api } from "../api.js";
import { denDetailMarkup } from "./den-shared.js";

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
  const data = await api.myDens();
  setMyDenCount(data.dens.length);
  const title = data.dens.length === 1 ? "My Den" : "My Dens";

  if (!data.dens.length) {
    container.innerHTML = `
      ${titleBar("My Dens")}
      <div class="screen-scroll"><p class="empty">None of your cubs are assigned to a den yet.</p></div>
    `;
    return;
  }

  let active = 0;

  function paint() {
    const den = data.dens[active];
    container.innerHTML = `
      ${titleBar(title, `${data.cub_count} CUB${data.cub_count === 1 ? "" : "S"}`)}
      <div class="screen-scroll">
        ${
          data.dens.length > 1
            ? `<div class="segmented">
          ${data.dens
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
        ${denDetailMarkup(den)}
      </div>
    `;
    container.querySelectorAll(".segment").forEach((btn) => {
      btn.addEventListener("click", () => {
        active = Number(btn.dataset.index);
        paint();
      });
    });
  }

  paint();
}
