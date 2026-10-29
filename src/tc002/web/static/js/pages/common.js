// Pieces shared by several pages.

import { t } from "../i18n.js";
import { screenPreview } from "../media.js";
import { H, SCALE, W } from "../led.js";
import { load } from "../store.js";
import { button, h, panel, row } from "../ui.js";

// A rotation item's LED thumbnail: a screen's own render, or a close imitation of a
// built-in app (the firmware draws those; the server approximates them).
export function thumb(key, isScreen) {
  return h("img", {
    class: "led-thumb", alt: "", loading: "lazy", width: W * SCALE, height: H * SCALE,
    src: isScreen ? screenPreview(key) : `/api/preview/builtin-${key}.gif`,
  });
}

export function offlineNotice(clock) {
  return panel(row(t("badge.offline"), { text: clock.error ?? "", warn: true },
    [button(t("btn.retry"), load, { ico: "refresh-cw" })], { icon: "cloud-off" }));
}

export const page = (...children) => h("div", { class: "page" }, ...children);
