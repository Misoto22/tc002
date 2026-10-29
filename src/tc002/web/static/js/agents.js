// Live agent state (sessions, plan limits) and the actions of the Integrations page.
// Agent state is polled while the window is visible; everything else reloads on demand.

import { get, post } from "./api.js";
import { t } from "./i18n.js";
import { load, store } from "./store.js";
import { toast } from "./ui.js";

const EVERY_MS = 5000;

export async function refreshAgents() {
  store.state.agents = await get("/api/agents");
}

// Calls onChange whenever sessions or limits changed since the last poll.
export function pollAgents(onChange) {
  setInterval(async () => {
    if (document.hidden || !store.state) return;
    const before = JSON.stringify(store.state.agents);
    try {
      await refreshAgents();
    } catch (err) {
      console.warn("tc002: agent poll failed", err); // the next poll retries
      return;
    }
    if (JSON.stringify(store.state.agents) !== before) onChange();
  }, EVERY_MS);
}

// One fixed action on this Mac (see web/host_actions.py), then fresh state.
export async function integration(action) {
  try {
    await post(`/api/integrations/${action}`, {});
    toast(t("int.done"));
  } catch (err) {
    toast(err.title, err.message, "error");
  }
  await load();
}

export const hooksConnected = () => {
  const hooks = store.state.integrations.hooks ?? {};
  return Object.values(hooks).length > 0 && Object.values(hooks).every((v) => v === true);
};

// Sessions in the order that matters: waiting, working, done, idle; longest first.
export function orderedSessions() {
  const rank = { waiting: 0, working: 1, done: 2, idle: 3 };
  return [...store.state.agents.sessions].sort((a, b) =>
    rank[a.state] - rank[b.state] || b.secondsInState - a.secondsInState);
}
