import { t } from "../i18n.js";
import { setFocus, store } from "../store.js";
import { badge, h, pageHead, panel, row, section } from "../ui.js";
import { page } from "./common.js";

export function integrations() {
  setFocus({ type: "rotation" });
  const { integrations: it, config } = store.state;
  const running = it.service.startsWith("state: running");
  const hookRows = Object.entries(it.hooks).map(([event, on]) =>
    row(event, t(`hook.${event}`), badge(on === true ? t("badge.installed") : t("badge.missing"), on === true ? "ok" : "warn"),
      { icon: "bot" }));
  return page(
    pageHead(t("page.integrations"), t("desc.integrations")),
    section(t("section.service")),
    panel(row(t("int.agent"), it.service.split("\n")[0],
      badge(running ? t("badge.running") : t("badge.stopped"), running ? "ok" : "warn"), { icon: "power" })),
    section(t("section.hooks")), panel(...hookRows),
    section(t("section.config")),
    panel(
      row(t("int.toml"), h("span", { class: "mono" }, config.path ?? t("int.notSet")), [], { icon: "sliders-horizontal" }),
      row(t("int.cli"), h("span", { class: "mono" }, "tc002 doctor · tc002 layout apply · tc002 uninstall"), [], { icon: "keyboard" })),
  );
}
