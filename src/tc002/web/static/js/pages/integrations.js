import { hooksConnected, integration } from "../agents.js";
import { get, post } from "../api.js";
import { t } from "../i18n.js";
import { setFocus, store } from "../store.js";
import { badge, button, h, pageHead, panel, row, section, toast } from "../ui.js";
import { page } from "./common.js";

let logText = null; // shown under the service row once asked for

async function toggleLog(rerender) {
  if (logText !== null) { logText = null; rerender(); return; }
  try {
    logText = (await get("/api/log")).text || t("int.logEmpty");
  } catch (err) {
    toast(err.title, err.message, "error");
  }
  rerender();
}

function reveal(what) {
  post("/api/reveal", { what }).catch((err) => toast(err.title, err.message, "error"));
}

function hookChips(hooks) {
  return h("div", { class: "chips" }, ...Object.entries(hooks).map(([event, on]) =>
    h("span", { class: `chip mono${on === true ? "" : " missing"}` }, event)));
}

export function integrations() {
  setFocus({ type: "rotation" });
  const { integrations: it, config, clock, agents } = store.state;
  const running = it.service.startsWith("state: running");
  const installed = !it.service.startsWith("not installed");
  const rerender = () => document.getElementById("page").replaceChildren(integrations());
  const codexSeen = agents.usage.codex.source !== "none";
  return page(
    pageHead(t("page.integrations"), t("desc.integrations")),
    section(t("int.clock")),
    panel(row(clock.host ? `TC002 · ${clock.host}` : t("int.notSet"),
      clock.online ? `${t("fact.firmware")} ${clock.base.appVer}` : { text: clock.error ?? "", warn: true },
      [badge(clock.online ? t("badge.online") : t("badge.offline"), clock.online ? "ok" : "bad"),
        h("a", { class: "btn", href: "#setup" }, t("int.change"))], { icon: "tv" })),
    section(t("int.agents")),
    panel(
      row(t("int.hooks"), h("div", {}, t("int.hooksHint"), hookChips(it.hooks)),
        hooksConnected()
          ? button(t("int.disconnect"), () => integration("disconnect-claude"))
          : button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }),
        { app: "claude" }),
      row(t("int.statusline"), t("int.statuslineHint"),
        it.statusline ? badge(t("badge.installed"), "ok")
          : button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }),
        { app: "claude" }),
      row(t("int.codex"), t("int.codexHint"), badge(codexSeen ? t("int.ready") : t("limits.unknown"), codexSeen ? "ok" : ""),
        { app: "codex" })),
    section(t("int.mac")),
    panel(
      row(t("int.agent"), h("div", {}, h("div", {}, it.service.split("\n")[0]), h("div", { class: "muted" }, t("int.serviceHint"))),
        [badge(running ? t("badge.running") : t("badge.stopped"), running ? "ok" : "warn"),
          installed ? button(t("int.restart"), () => integration("restart-service"), { ico: "rotate-ccw" })
            : button(t("int.install"), () => integration("install-service"), { kind: "primary", ico: "power" }),
          button(logText === null ? t("int.showLog") : t("int.hideLog"), () => toggleLog(rerender), { ico: "scroll-text" })],
        { icon: "power" }),
      logText !== null ? h("pre", { class: "log" }, logText) : null,
      row(t("int.toml"), h("span", { class: "mono" }, config.path ?? t("int.notSet")),
        config.path ? button(t("int.reveal"), () => reveal("config"), { ico: "folder-search" }) : [],
        { icon: "sliders-horizontal" })),
  );
}
