// Where a screen's LED preview comes from. Sessions and plan limits are rendered from
// live data, keyed on it so the image refreshes when it changes; other screens use a
// fixed example rendered by the server.

import { store } from "./store.js";

const LIVE = new Set(["claude", "usage"]);

export function screenPreview(screen) {
  if (!LIVE.has(screen)) return `/api/preview/${screen}.gif`;
  const a = store.state?.agents;
  const version = a ? Object.values(a.counts).join("") + JSON.stringify(Object.values(a.usage).map((u) => [u.limit_5h, u.limit_week])) : "";
  return `/api/preview/live-${screen}.gif?v=${encodeURIComponent(version)}`;
}
