// Pieces shared by several pages.

import { t } from "../i18n.js";
import { screenPreview } from "../media.js";
import { load } from "../store.js";
import { appIcon, button, h, panel, row } from "../ui.js";

// A rotation item's thumbnail: a screen's live-looking LED preview, or a built-in's icon.
export function thumb(key, isScreen) {
  return isScreen
    ? h("img", { class: "led-thumb", src: screenPreview(key), alt: "", loading: "lazy" })
    : h("span", { class: "thumb-tile" }, appIcon(key));
}

export function offlineNotice(clock) {
  return panel(row(t("badge.offline"), { text: clock.error ?? "", warn: true },
    [button(t("btn.retry"), load, { ico: "refresh-cw" })], { icon: "cloud-off" }));
}

export const page = (...children) => h("div", { class: "page" }, ...children);
