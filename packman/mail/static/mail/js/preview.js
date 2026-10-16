(() => {
  const button = document.getElementById("message-preview-button");
  if (!button) return;

  const form = button.closest("form");
  const dialog = document.getElementById("message-preview-modal");
  const modal = new bootstrap.Modal(dialog);
  const frame = document.getElementById("message-preview-frame");
  const status = document.getElementById("message-preview-status");
  let controller;

  dialog.addEventListener("hidden.bs.modal", () => {
    controller?.abort();
    frame.removeAttribute("srcdoc");
    button.focus();
  });

  button.addEventListener("click", async () => {
    window.tinymce?.triggerSave();
    const data = new URLSearchParams();
    data.set("subject", form.elements.subject.value);
    data.set("body", form.elements.body.value);
    controller = new AbortController();
    button.disabled = true;
    frame.hidden = true;
    frame.removeAttribute("srcdoc");
    status.classList.remove("text-danger");
    status.textContent = dialog.dataset.loadingMessage;
    modal.show();

    try {
      const response = await fetch(button.dataset.previewUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
        },
        body: data,
        signal: controller.signal,
      });
      if (response.redirected || !response.headers.get("Content-Type")?.includes("application/json")) {
        throw new Error(dialog.dataset.errorMessage);
      }
      const result = await response.json();
      if (!response.ok) {
        const errors = Object.values(result.errors || {}).flat().map((error) => error.message);
        throw new Error(errors.join(" ") || dialog.dataset.errorMessage);
      }
      if (typeof result.html !== "string") throw new Error(dialog.dataset.errorMessage);
      frame.srcdoc = result.html;
      frame.hidden = false;
      status.textContent = "";
    } catch (error) {
      if (error.name !== "AbortError") {
        status.classList.add("text-danger");
        status.textContent = error instanceof TypeError ? dialog.dataset.errorMessage : error.message;
      }
    } finally {
      button.disabled = false;
    }
  });
})();
