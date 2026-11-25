// HTTP calls to the local tc002 server. Every write carries the page's session token.
// The server makes a new token each time it starts; a page left open across a restart
// fetches the new one from index.html (same origin only) and retries, so it keeps working
// and keeps its unsaved edits.

import { t } from "./i18n.js";

const META = 'meta[name="tc002-token"]';
let token = document.querySelector(META).content;

async function freshToken() {
  const res = await fetch("/", { cache: "no-store" });
  const doc = new DOMParser().parseFromString(await res.text(), "text/html");
  token = doc.querySelector(META)?.content ?? token;
}

export class ApiFailure extends Error {
  constructor(problem) {
    const detail = [problem.detail, ...(problem.errors ?? []).map((e) => e.message)]
      .filter(Boolean).join(" · ");
    const fallback = problem.title ?? `HTTP ${problem.status ?? ""}`.trim();
    super(detail || fallback);
    // the type's last segment names the error; show its title in the UI's language
    const key = `err.${(problem.type ?? "").split("/").pop()}`;
    this.title = t(key) === key ? fallback : t(key);
    this.status = problem.status;
  }
}

async function request(path, options = {}, retried = false) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-TC002-Token": token, ...options.headers },
  });
  const body = await res.json().catch(() => ({ title: `HTTP ${res.status}` }));
  if (res.status === 403 && body.title === "Missing token" && !retried) {
    await freshToken(); // the server restarted since this page loaded
    return request(path, options, true);
  }
  if (!res.ok) throw new ApiFailure(body);
  return body;
}

export const get = (path) => request(path);
export const post = (path, body, headers = {}) =>
  request(path, { method: "POST", body: JSON.stringify(body), headers });

// For page unload: must not be cancelled when the tab goes away.
export function postOnExit(path, body) {
  fetch(path, {
    method: "POST", keepalive: true, body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", "X-TC002-Token": token },
  });
}
