import { esc } from "../components.js";
import { api } from "../api.js";
import { denDetailMarkup } from "./den-shared.js";

export async function renderMyDens(container) {
  const data = await api.myDens();

  if (!data.dens.length) {
    container.innerHTML = '<p class="empty">None of your cubs are assigned to a den yet.</p>';
    return;
  }

  let active = 0;

  function paint() {
    const den = data.dens[active];
    container.innerHTML = `
      ${
        data.dens.length > 1
          ? `<div class="den-switcher">
        ${data.dens
          .map(
            (d, i) => `<button class="switch-tab${i === active ? " on" : ""}" data-index="${i}">${esc(
              d.rank
            )}s</button>`
          )
          .join("")}
      </div>`
          : ""
      }
      ${denDetailMarkup(den)}
    `;
    container.querySelectorAll(".switch-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        active = Number(btn.dataset.index);
        paint();
      });
    });
  }

  paint();
}
