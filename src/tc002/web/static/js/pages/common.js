// Pieces shared by several pages.

import { appName, t } from "../i18n.js";
import { load } from "../store.js";
import { button, h, panel, row } from "../ui.js";

const PREVIEWS = { claude: "claude-busy", sys: "sys" };

export function thumb(key, isScreen) {
  return isScreen
    ? h("img", { class: "led-thumb", src: `/api/preview/${PREVIEWS[key] ?? key}.gif`, alt: "", loading: "lazy" })
    : h("span", { class: "builtin-tile" }, appName(key));
}

export function offlineNotice(clock) {
  return panel(row(t("badge.offline"), { text: clock.error ?? "", warn: true },
    [button(t("btn.retry"), load, { ico: "refresh-cw" })], { icon: "cloud-off" }));
}

export const page = (...children) => h("div", { class: "page" }, ...children);
