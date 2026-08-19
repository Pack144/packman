const routes = [];

export function route(pattern, handler) {
  routes.push({ segments: pattern.split("/").filter(Boolean), handler });
}

function match(hash) {
  const segments = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  for (const { segments: patternSegments, handler } of routes) {
    if (patternSegments.length !== segments.length) continue;
    const params = {};
    const ok = patternSegments.every((segment, i) => {
      if (segment.startsWith(":")) {
        params[segment.slice(1)] = decodeURIComponent(segments[i]);
        return true;
      }
      return segment === segments[i];
    });
    if (ok) return { handler, params };
  }
  return null;
}

export function navigate(path) {
  window.location.hash = path;
}

export function startRouter() {
  const dispatch = () => {
    const found = match(window.location.hash || "#/home");
    if (found) {
      found.handler(found.params);
    } else {
      navigate("/home");
    }
  };
  window.addEventListener("hashchange", dispatch);
  dispatch();
}
