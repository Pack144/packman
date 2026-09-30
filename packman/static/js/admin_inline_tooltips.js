(() => {
  let tooltipId = 0;

  function addTooltip(trigger) {
    if (trigger.dataset.inlineTooltipInitialized) {
      return;
    }

    const helpText = trigger.getAttribute("title");
    if (!helpText) {
      return;
    }

    trigger.dataset.inlineTooltipInitialized = "true";
    trigger.removeAttribute("title");
    trigger.setAttribute("tabindex", "0");
    trigger.setAttribute("role", "img");
    trigger.setAttribute("aria-label", `Help: ${helpText}`);

    const tooltip = document.createElement("span");
    tooltip.className = "admin-inline-tooltip";
    tooltip.id = `admin-inline-tooltip-${++tooltipId}`;
    tooltip.setAttribute("role", "tooltip");
    tooltip.hidden = true;
    tooltip.textContent = helpText;
    document.body.append(tooltip);
    trigger.setAttribute("aria-describedby", tooltip.id);

    function showTooltip() {
      tooltip.hidden = false;
      const triggerRect = trigger.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const margin = 8;
      const left = Math.max(
        margin,
        Math.min(triggerRect.left, window.innerWidth - tooltipRect.width - margin),
      );
      const below = triggerRect.bottom + margin;
      const top = below + tooltipRect.height <= window.innerHeight - margin
        ? below
        : Math.max(margin, triggerRect.top - tooltipRect.height - margin);

      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    }

    function hideTooltip() {
      tooltip.hidden = true;
    }

    trigger.addEventListener("mouseenter", showTooltip);
    trigger.addEventListener("mouseleave", hideTooltip);
    trigger.addEventListener("focus", showTooltip);
    trigger.addEventListener("blur", hideTooltip);
    trigger.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hideTooltip();
      }
    });
  }

  function initializeTooltips(root) {
    if (root instanceof Element && root.matches(".help-tooltip[title]")) {
      addTooltip(root);
    }
    root.querySelectorAll?.(".help-tooltip[title]").forEach(addTooltip);
  }

  initializeTooltips(document);

  new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof Element) {
          initializeTooltips(node);
        }
      });
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
