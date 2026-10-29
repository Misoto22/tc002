// A screen tried with real data: the picture it would put on the clock, whether reading
// worked (and how long it took, or why not), and what it read. Used on a screen's own
// page and on Connections. Results are kept for a minute per screen and options, so
// redrawing a page does not ask the internet again.

import { post } from "./api.js";
import { t } from "./i18n.js";
import { screenPreview } from "./media.js";
import { H, SCALE, W } from "./led.js";
import { TIMING } from "./timing.js";
import { button, h, icon } from "./ui.js";

const results = new Map(); // key -> { at, promise }

function check(screen, options, force) {
  const key = `${screen}:${JSON.stringify(options ?? null)}`;
  const kept = results.get(key);
  if (!force && kept && Date.now() - kept.at < TIMING.liveCheckKeepMs) return kept.promise;
  const promise = post("/api/try-screen", { screen, options })
    .catch((err) => ({ ok: false, error: err.message, ms: 0 }));
  results.set(key, { at: Date.now(), promise });
  return promise;
}

export function status(r) {
  if (!r) return h("div", { class: "live-status" }, icon("loader-circle", "icon spin"), t("live.reading"));
  return h("div", { class: `live-status ${r.ok ? "ok" : "bad"}` },
    h("span", { class: `dot ${r.ok ? "ok" : "bad"}` }),
    h("strong", {}, r.ok ? t("live.ok") : t("live.fail")),
    h("span", { class: "muted" }, r.ok ? t("live.took", { ms: r.ms }) : r.error));
}

export function factList(r) {
  if (!r?.ok || !r.facts?.length) return null;
  const label = (k) => (t(`fact.${k}`) === `fact.${k}` ? k : t(`fact.${k}`)); // a field without a name stays as is
  return h("dl", { class: "facts" }, ...r.facts.flatMap(([k, v]) => [h("dt", {}, label(k)), h("dd", { class: "mono" }, v)]));
}

// The card. `options`: the draft's options for this screen (null: the saved ones).
export function liveCheck(screen, options = null, { unsaved = false } = {}) {
  const img = h("img", { class: "led-thumb live-img", alt: "", width: W * SCALE, height: H * SCALE, src: screenPreview(screen) });
  const tag = h("span", { class: "live-tag" }, t("live.example"));
  const body = h("div", { class: "live-body" }, status(null));
  const card = h("div", { class: "live-card" },
    h("figure", { class: "live-figure" }, img, h("figcaption", {}, tag)),
    h("div", { class: "live-side" }, h("div", { class: "live-head" },
      h("span", { class: "live-title" }, t("live.title")),
      unsaved ? h("span", { class: "tag" }, t("live.unsaved")) : null,
      h("span", { class: "spacer" }),
      button(t("live.retry"), () => run(true), { kind: "ghost", ico: "refresh-cw" })), body));
  async function run(force = false) {
    body.replaceChildren(status(null));
    const r = await check(screen, options, force);
    if (!card.isConnected && !force) return;
    if (r.ok) { img.src = r.gif; tag.textContent = t("live.title"); }
    body.replaceChildren(status(r), factList(r) ?? "");
  }
  run();
  return card;
}
