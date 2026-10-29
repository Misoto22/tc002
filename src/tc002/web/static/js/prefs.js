// Per-browser preferences: theme and language. Stored in localStorage when available;
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
  lang: navigator.language?.toLowerCase().startsWith("zh") ? "zh" : "en",
  ...read(),
};

export function applyPrefs() {
  document.documentElement.dataset.theme = prefs.theme;
  setLang(prefs.lang);
}

export function setPref(key, value, after) {
  prefs[key] = value;
  write(prefs);
  transition(() => { applyPrefs(); after?.(); }); // cross-fades the whole page
}
