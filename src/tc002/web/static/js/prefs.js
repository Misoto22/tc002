// Per-browser preferences: theme, colour palette and language. Stored in localStorage when available;
// the page works the same when storage is blocked, it just forgets between visits.

import { setLang } from "./i18n.js";
import { transition } from "./ui.js";

const KEY = "tc002.prefs";

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) ?? {};
  } catch {
    return {};
  }
}

function write(prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    // storage blocked (private window): keep the choice for this visit only
  }
}

export const prefs = {
  theme: "system", // system | light | dark
  palette: "paper", // see PALETTES
  sidebar: "open", // open | collapsed
  lang: navigator.language?.toLowerCase().startsWith("zh") ? "zh" : "en",
  ...read(),
};

// Colour themes (css/palettes.css); "paper" is the default look in tokens.css.
export const PALETTES = ["paper", "matcha", "ai", "sakura", "kohaku"];

export function applyPrefs() {
  const root = document.documentElement;
  root.dataset.theme = prefs.theme;
  root.dataset.palette = PALETTES.includes(prefs.palette) ? prefs.palette : "paper";
  setLang(prefs.lang);
}

// Change one preference. Theme and palette changes spread as a circle from `origin`
// (the control that was used); everything else cross-fades.
export function setPref(key, value, after, origin) {
  prefs[key] = value;
  write(prefs);
  const root = document.documentElement;
  if (origin && (key === "theme" || key === "palette")) {
    root.style.setProperty("--reveal-x", `${origin.x}px`);
    root.style.setProperty("--reveal-y", `${origin.y}px`);
    root.dataset.transition = "reveal";
  }
  transition(() => { applyPrefs(); after?.(); }, () => delete root.dataset.transition);
}
