// Searchable city combobox for the weather app. Online it asks Open-Meteo (via the local
// server); offline it falls back to a built-in list. A pick sets city, lat and lon together.
// The result list is a popover on <body>, positioned under the input, so the settings
// panel it sits in can neither clip it nor be covered by it.

import { get } from "./api.js";
import { lang, t } from "./i18n.js";
import { h, icon } from "./ui.js";

export function cityPicker(current, onPick) {
  let results = [];
  let active = -1;
  let timer;
  let seq = 0;
  const input = h("input", {
    class: "field city-input", placeholder: t("city.placeholder"), value: current.city ?? "",
    role: "combobox", "aria-autocomplete": "list", "aria-expanded": "false", "aria-controls": "city-list",
    "aria-label": t("field.city"), autocomplete: "off",
  });
  const list = h("div", { class: "popover city-list", id: "city-list", role: "listbox" });
  const coords = h("div", { class: "row-hint mono" },
    current.lat && current.lon ? `${Number(current.lat).toFixed(2)}, ${Number(current.lon).toFixed(2)}` : "");

  function place() {
    const box = input.getBoundingClientRect();
    const width = Math.max(box.width, 300);
    list.style.cssText = `top:${box.bottom + 6}px;left:${Math.max(8, box.right - width)}px;width:${width}px`;
  }

  const outside = (e) => { if (!list.contains(e.target) && e.target !== input) close(); };

  function open() {
    if (!list.isConnected) {
      document.body.append(list);
      document.addEventListener("pointerdown", outside);
    }
    place();
    input.setAttribute("aria-expanded", "true");
  }

  function close() {
    list.remove();
    document.removeEventListener("pointerdown", outside);
    input.setAttribute("aria-expanded", "false");
  }

  async function search() {
    const mine = ++seq;
    const q = input.value.trim();
    const data = await get(`/api/cities?${new URLSearchParams({ q, lang: lang() })}`).catch(() => null);
    if (mine !== seq || !data || document.activeElement !== input) return; // stale or left
    results = data.results;
    active = results.length ? 0 : -1;
    list.replaceChildren(
      ...results.map((r, i) => h("div", {
        class: "city-option", role: "option", "aria-selected": String(i === active), id: `city-${i}`,
        onPointerdown: (e) => { e.preventDefault(); pick(i); },
      }, icon("map-pin"), h("span", {}, r.name), h("span", { class: "muted" }, r.region))),
      results.length ? h("div", { class: "city-source" }, t(`city.source.${data.source}`))
        : h("div", { class: "palette-empty" }, t("city.none")));
    open();
  }

  function pick(i) {
    const r = results[i];
    if (!r) return;
    input.value = r.name;
    coords.textContent = `${r.lat.toFixed(2)}, ${r.lon.toFixed(2)} · ${r.region}`;
    close();
    onPick({ city: r.name, lat: String(r.lat), lon: String(r.lon) });
  }

  function paint() {
    [...list.querySelectorAll(".city-option")].forEach((el, i) => el.setAttribute("aria-selected", String(i === active)));
    input.setAttribute("aria-activedescendant", active >= 0 ? `city-${active}` : "");
  }

  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(search, 220); });
  input.addEventListener("focus", search);
  input.addEventListener("blur", () => setTimeout(close, 120));
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(results.length - 1, active + 1); paint(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(0, active - 1); paint(); }
    else if (e.key === "Enter") { e.preventDefault(); pick(active); }
    else if (e.key === "Escape") close();
  });
  // the page scrolls under a fixed popover: follow the input, or close if it left the view
  document.getElementById("main")?.addEventListener("scroll", () => { if (list.isConnected) place(); }, { passive: true });

  return h("div", { class: "city-picker" },
    h("div", { class: "city-field" }, icon("search", "icon city-search"), input), coords);
}
