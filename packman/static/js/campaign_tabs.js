const campaignTabs = document.querySelector("[data-campaign-tabs]");

function getActiveCampaignTab() {
  return campaignTabs?.querySelector("[data-campaign-tab].active")?.dataset.campaignTab;
}

campaignTabs?.querySelectorAll('[data-bs-toggle="tab"]').forEach((tab) => {
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

document.querySelectorAll("[data-campaign-navigation]").forEach((select) => {
  select.addEventListener("change", (event) => {
    const url = new URL(event.target.value, window.location.origin);
    const activeTab = getActiveCampaignTab();
    if (activeTab) {
      url.searchParams.set("tab", activeTab);
    }
    window.location.assign(url);
  });
});
