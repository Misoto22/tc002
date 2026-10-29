// Options of one of tc002's own screens ([screen.<name>] in tc002.toml), drawn from the
// server's description of each screen's OPTIONS, so a new option needs no UI code.

import { t } from "../i18n.js";
import { edit, store } from "../store.js";
import { h, row, segmented, slider } from "../ui.js";

function control(name, key, spec, value, set) {
  const label = t(`opt.${name}.${key}`);
  if (spec.kind === "choice") return segmented(spec.spec.map((v) => [v, t(`opt.value.${v}`)]), value, set, label);
  if (spec.kind === "int") return slider(spec.spec[0], spec.spec[1], value, set, label);
  if (spec.kind === "date") {
    return h("input", { class: "field", type: "date", value: value ?? "", "aria-label": label,
      onChange: (e) => set(e.target.value) });
  }
  if (spec.kind === "zones" || spec.kind === "list") {
    const zones = [...(value ?? spec.default)];
    return h("div", { class: "zones" }, ...Array.from({ length: spec.spec }, (_, i) => h("input", {
      class: "field mono", value: zones[i] ?? "", placeholder: spec.default[i] ?? "", "aria-label": `${label} ${i + 1}`,
      onChange: (e) => { zones[i] = e.target.value.trim(); set(zones.filter(Boolean)); },
    })));
  }
  return h("input", { class: "field", value: value ?? "", maxlength: spec.spec, "aria-label": label,
    onChange: (e) => set(e.target.value.trim()) });
}

// The option rows of screen `name`, or null when it has none.
export function screenOptions(name) {
  const described = store.state.screenOptions[name];
  if (!described) return null;
  const values = store.draft.screen?.[name] ?? {};
  const hint = (key) => {
    const text = t(`opt.${name}.${key}Hint`);
    return text === `opt.${name}.${key}Hint` ? null : text;
  };
  return Object.entries(described).map(([key, spec]) => row(t(`opt.${name}.${key}`), hint(key),
    control(name, key, spec, values[key] ?? spec.default,
      (v) => edit((dr) => { dr.screen = { ...dr.screen, [name]: { ...dr.screen?.[name], [key]: v } }; })),
    { path: `screen.${name}.${key}` }));
}
