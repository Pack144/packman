const BASE = "/mobile/api/";

async function request(path, params) {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await fetch(url, { credentials: "same-origin" });

  if (response.status === 401 || response.status === 403) {
    // Keep the hash-based in-app route so post-login lands back on the same screen.
    const next = encodeURIComponent(
      window.location.pathname + window.location.search + window.location.hash
    );
    window.location.href = `${window.PACKMAN_MOBILE.loginUrl}?next=${next}`;
    throw new Error("Not authenticated");
  }
  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  home: () => request("home/"),
  myDens: () => request("dens/mine/"),
  dens: () => request("dens/"),
  den: (number) => request(`dens/${number}/`),
  search: (q, type) => request("search/", { q, type }),
  member: (slug) => request(`members/${encodeURIComponent(slug)}/`),
};
