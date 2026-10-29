// HTTP calls to the local tc002 server. Every write carries the page's session token.

const TOKEN = document.querySelector('meta[name="tc002-token"]').content;

export class ApiFailure extends Error {
  constructor(problem) {
    const detail = [problem.detail, ...(problem.errors ?? []).map((e) => e.message)]
      .filter(Boolean).join(" · ");
    super(detail || problem.title || "Request failed");
    this.title = problem.title ?? "Request failed";
  }
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-TC002-Token": TOKEN, ...options.headers },
  });
  const body = await res.json().catch(() => ({ title: `HTTP ${res.status}` }));
  if (!res.ok) throw new ApiFailure(body);
  return body;
}

export const get = (path) => request(path);
export const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body) });

// For page unload: must not be cancelled when the tab goes away.
export function postOnExit(path, body) {
  fetch(path, {
    method: "POST", keepalive: true, body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", "X-TC002-Token": TOKEN },
  });
}
