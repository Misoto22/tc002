// Options of tc002's own screens ([screen.<name>] in tc002.toml), drawn from the server's
// description of each screen's OPTIONS, so a new option needs no UI code.

import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { appIcon, h, panel, row, section, segmented, slider } from "../ui.js";

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

// One section per enabled screen that has options.
export function screenOptions() {
  const described = store.state.screenOptions;
  const enabled = store.draft.screens.enabled.filter((s) => described[s]);
  return enabled.flatMap((name) => {
    const values = store.draft.screen?.[name] ?? {};
    const focus = () => setFocus({ type: "screen", key: name });
    const rows = Object.entries(described[name]).map(([key, spec]) => row(
      t(`opt.${name}.${key}`), t(`opt.${name}.${key}Hint`) === `opt.${name}.${key}Hint` ? null : t(`opt.${name}.${key}Hint`),
      control(name, key, spec, values[key] ?? spec.default,
        (v) => edit((dr) => { dr.screen = { ...dr.screen, [name]: { ...dr.screen?.[name], [key]: v } }; })),
      { path: `screen.${name}.${key}`, onFocus: focus }));
    return [section([appIcon(name, "sm"), appName(name), h("span", { class: "muted" }, `· ${t("opt.tc002Screen")}`)]),
      panel(...rows)];
  });
}
