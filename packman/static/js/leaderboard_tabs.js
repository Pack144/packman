document.querySelectorAll('[data-bs-toggle="tab"]').forEach((tab) => {
  tab.addEventListener("shown.bs.tab", (event) => {
    const selectedTab = event.target.id.replace("-tab", "");
    const url = new URL(window.location);
    url.searchParams.set("tab", selectedTab);
    window.history.replaceState({}, "", url);
    document.querySelectorAll('input[name="tab"]').forEach((input) => {
      input.value = selectedTab;
    });
  });
});

document.querySelectorAll("[data-leaderboard-navigation]").forEach((select) => {
  select.addEventListener("change", (event) => {
    const url = new URL(event.target.value, window.location.origin);
    const activeTab = document.querySelector('[data-bs-toggle="tab"].active');
    if (activeTab) {
      url.searchParams.set("tab", activeTab.id.replace("-tab", ""));
    }
    window.location.assign(url);
  });
});
