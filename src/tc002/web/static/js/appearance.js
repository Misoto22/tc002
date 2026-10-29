// LED colour themes for tc002's screens on the clock, and keeping them in step with the
// UI's colour palette when the theme is set to "match". Stored in tc002.toml [appearance].

import { post } from "./api.js";
import { H, SCALE, W } from "./led.js";
import { t } from "./i18n.js";
import { store } from "./store.js";
import { h, section, toast } from "./ui.js";

const current = () => store.state.config.data.appearance;

function remember(appearance) {
  for (const doc of [store.state.config.data, store.saved, store.draft]) doc.appearance = { ...appearance };
}

async function change(patch, quiet = false) {
  if (!store.state.config.path) return;
  try {
    const result = await post("/api/appearance", patch);
    remember(result.appearance);
    if (!quiet) toast(t("led.applied"), result.serviceRestarted ? t("save.serviceReloaded") : null);
  } catch (err) {
    toast(err.title, err.message, "error");
  }
}

// Called when the UI's palette changes: the clock follows it while the theme is "match".
export function followUiPalette(palette) {
  if (!store.state || current().ui_palette === palette) return;
  change({ ui_palette: palette }, current().led_theme !== "match");
}

const label = (id) => (id === "match" ? t("led.match") : id === "classic" ? t("led.classic") : t(`palette.${id}`));

export function ledThemes(rerender) {
  const chosen = current().led_theme;
  const resolved = chosen === "match" ? current().ui_palette : chosen;
  const cards = store.state.ledThemes.map((id) => h("button", {
    type: "button", class: "choice led-choice", "aria-pressed": String(chosen === id),
    onClick: async () => { await change({ led_theme: id }); rerender(); },
  },
  h("img", { class: "led-thumb", alt: "", loading: "lazy", width: W * SCALE, height: H * SCALE,
    src: `/api/preview/usage.gif?theme=${encodeURIComponent(id === "match" ? resolved : id)}` }),
  h("span", { class: "choice-title" }, label(id)),
  id === "match" ? h("span", { class: "muted" }, label(resolved)) : null));
  return [
    section(t("led.title"), h("span", { class: "muted" }, `· ${t("led.hint")}`)),
    h("div", { class: "choices led-choices" }, ...cards),
  ];
}
