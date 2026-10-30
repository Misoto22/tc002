// Pieces shared by several pages.

import { t } from "../i18n.js";
import { screenPreview } from "../media.js";
import { H, SCALE, W } from "../led.js";
import { load } from "../store.js";
import { button, h, panel, row } from "../ui.js";

export const slotKey = (s) => s.screen ?? s.builtin;

// A rotation item's LED thumbnail: a screen's own render, or a close imitation of a
// built-in app (the firmware draws those; the server approximates them).
export function thumb(key, isScreen) {
  return h("img", {
    class: "led-thumb", alt: "", loading: "lazy", width: W * SCALE, height: H * SCALE,
    src: isScreen ? screenPreview(key) : `/api/preview/builtin-${key}.gif`,
  });
}

// Why the clock is not answering, in words: the technical reason stays in the tooltip.
export function clockProblem(clock) {
  return { text: t("clock.unreachable", { host: clock.host ?? "—" }), warn: true, title: clock.error ?? "" };
}

export function offlineNotice(clock) {
  return panel(row(t("badge.offline"), clockProblem(clock),
    [button(t("btn.retry"), load, { ico: "refresh-cw" })], { icon: "cloud-off" }));
}

export const page = (...children) => h("div", { class: "page" }, ...children);

// The background service's launchctl status in words ("Running · started 4 times since
// login"); the raw line stays in the tooltip for anyone debugging.
export function serviceSummary(status) {
  const line = status.split("\n")[0];
  const runs = line.match(/runs: (\d+)/)?.[1];
  let text = t("service.other");
  if (line.startsWith("not installed")) text = t("service.notInstalled");
  else if (line.includes("state: running")) text = t("service.running", { n: runs ?? "?" });
  else if (line.includes("state:")) text = t("service.stopped");
  return { text, title: line };
}
