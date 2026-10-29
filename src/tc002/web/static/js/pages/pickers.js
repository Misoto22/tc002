// Pickers for options that name things elsewhere: stocks found by searching Yahoo
// Finance, and the user's own Home Assistant devices. Each shows the chosen items as
// removable chips and adds more from a search list, up to the option's limit.

import { get } from "../api.js";
import { t } from "../i18n.js";
import { TIMING } from "../timing.js";
import { attachPopover, h, icon } from "../ui.js";

function chips(values, label, onRemove) {
  return h("div", { class: "pick-chips" }, ...values.map((v, i) => h("span", { class: "pick-chip" },
    h("span", { class: "mono" }, v), label(v) ? h("span", { class: "muted" }, label(v)) : null,
    h("button", { type: "button", class: "pick-x", "aria-label": t("pick.remove", { name: v }),
      onClick: () => onRemove(i) }, icon("x")))));
}

// A search box whose results open under it; `search(q)` resolves to
// [{value, title, detail}] or throws an error with a message to show.
function searchBox(placeholder, search, onPick, loadOnFocus = false) {
  let close = null;
  let timer;
  let seq = 0;
  const input = h("input", { class: "field pick-input", placeholder, autocomplete: "off", "aria-label": placeholder });
  const list = h("div", { class: "popover pick-list", role: "listbox" });
  const show = (...children) => {
    list.replaceChildren(...children);
    if (!close) close = attachPopover(list, input, () => { close = null; });
  };
  async function run() {
    const mine = ++seq;
    const q = input.value.trim();
    if (!q && !loadOnFocus) { close?.(); return; }
    show(h("div", { class: "palette-empty" }, t("pick.loading")));
    try {
      const results = await search(q);
      if (mine !== seq) return;
      show(...(results.length ? results.map((r) => h("button", {
        type: "button", class: "pick-option", role: "option",
        onPointerdown: (e) => { e.preventDefault(); close?.(); input.value = ""; onPick(r.value); },
      }, h("span", { class: "mono" }, r.title), h("span", { class: "muted" }, r.detail)))
        : [h("div", { class: "palette-empty" }, t("pick.none"))]));
    } catch (err) {
      if (mine === seq) show(h("div", { class: "palette-empty" }, err.message));
    }
  }
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, TIMING.citySearchMs); });
  if (loadOnFocus) input.addEventListener("focus", run);
  return h("div", { class: "city-field" }, icon("search", "icon city-search"), input);
}

const names = new Map(); // symbol -> company, kept across redraws of the page
export function symbolPicker(values, max, onChange) {
  const add = (symbol) => { if (!values.includes(symbol) && values.length < max) onChange([...values, symbol]); };
  const search = async (q) => (await get(`/api/symbols?${new URLSearchParams({ q })}`)).results.map((r) => {
    names.set(r.symbol, r.name);
    return { value: r.symbol, title: r.symbol, detail: [r.name, r.exchange].filter(Boolean).join(" · ") };
  });
  return h("div", { class: "picker" },
    chips(values, (v) => names.get(v), (i) => onChange(values.filter((_, j) => j !== i))),
    values.length < max ? searchBox(t("pick.search"), search, add) : h("span", { class: "muted" }, t("pick.max", { n: max })));
}

let entityCache = null; // one read of Home Assistant per page visit is enough
export function entityPicker(values, max, onChange) {
  const add = (id) => { if (!values.includes(id) && values.length < max) onChange([...values, id]); };
  const search = async (q) => {
    entityCache ??= get("/api/home/entities").then((r) => r.results).catch((err) => { entityCache = null; throw err; });
    const needle = q.toLowerCase();
    return (await entityCache)
      .filter((e) => !needle || e.name.toLowerCase().includes(needle) || e.id.includes(needle))
      .slice(0, 30)
      .map((e) => ({ value: e.id, title: e.name, detail: `${e.id} · ${e.value}` }));
  };
  return h("div", { class: "picker" },
    chips(values, () => null, (i) => onChange(values.filter((_, j) => j !== i))),
    values.length < max ? searchBox(t("pick.entities"), search, add, true) : h("span", { class: "muted" }, t("pick.max", { n: max })));
}

export const forgetEntities = () => { entityCache = null; };
