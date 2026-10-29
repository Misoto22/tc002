import { ago, t } from "../i18n.js";
import { quickControls } from "../quick.js";
import { applySaved, load, setFocus, store } from "../store.js";
import { badge, button, h, pageHead, panel, row, section } from "../ui.js";
import { page } from "./common.js";

export function overview() {
  setFocus({ type: "rotation" });
  const { clock, integrations } = store.state;
  const hooks = integrations.hooks ?? {};
  const hooksOn = Object.values(hooks).filter((v) => v === true).length;
  const drift = clock.drift ?? [];
  const running = integrations.service.startsWith("state: running");

  const status = panel(
    row(t("row.clock"), clock.online ? `${clock.host} · ${t("fact.firmware")} ${clock.base.appVer}` : { text: clock.error, warn: true },
      badge(clock.online ? t("badge.online") : t("badge.offline"), clock.online ? "ok" : "bad"), { icon: "wifi" }),
    row(t("row.service"), integrations.service.split("\n")[0],
      badge(running ? t("badge.running") : t("badge.stopped"), running ? "ok" : "warn"), { icon: "power" }),
    row(t("row.hooks"), integrations.lastEvent
      ? t("row.lastEvent", { kind: integrations.lastEvent.kind, ago: ago(integrations.lastEvent.secondsAgo) })
      : t("row.noEvent"),
    badge(t("badge.hooks", { n: hooksOn }), hooksOn === 3 ? "ok" : "warn"), { icon: "bot" }),
    row(t("row.sync"), drift.length ? { text: t("row.differs", { list: drift.join(", ") }), warn: true } : t("row.everythingSynced"),
      drift.length ? button(t("btn.applyNow"), applySaved, { kind: "primary", ico: "refresh-cw" }) : badge(t("badge.inSync"), "ok"),
      { icon: "refresh-cw" }),
  );

  const facts = clock.online && h("dl", { class: "panel facts" },
    ...[["ip", clock.base.ip], ["wifi", clock.base.ssid], ["firmware", clock.base.appVer],
      ["mcu", clock.base.mcuVer], ["mac", clock.base.mac], ["serial", clock.base.devSn]]
      .map(([k, v]) => h("div", { class: "fact" }, h("dt", {}, t(`fact.${k}`)), h("dd", {}, v ?? "—"))));

  return page(
    pageHead(t("page.overview"), t("desc.overview"), button(t("btn.refresh"), load, { ico: "refresh-cw" })),
    clock.online && section(t("quick.title")),
    clock.online && h("div", { class: "panel quick-grid" }, ...quickControls()),
    section(t("section.status")), status,
    facts && section(t("section.device")), facts,
    clock.online && section(t("row.customApps")),
    clock.online && panel(row(clock.customApps.join(", ") || t("row.none"), t("row.customAppsHint"), [], { icon: "blocks" })),
  );
}
