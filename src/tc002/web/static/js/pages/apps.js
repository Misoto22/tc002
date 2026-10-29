import { cityPicker } from "../citypicker.js";
import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { h, pageHead, row, section, segmented, toggle } from "../ui.js";
import { offlineNotice, page } from "./common.js";

const APP_ICON = { clock: "clock", weather: "cloud-sun", busy: "timer", tomato: "timer" };

export function apps() {
  const focused = store.focus.type === "builtin" && APP_ICON[store.focus.key] ? store.focus.key : "clock";
  setFocus({ type: "builtin", key: focused });
  const live = store.state.clock.apps ?? {};

  const sections = Object.entries(store.state.schema.apps).flatMap(([app, fields]) => {
    const value = (key) => store.draft.apps?.[app]?.[key] ?? live[app]?.[key];
    const set = (patch) => edit((dr) => { dr.apps[app] = { ...dr.apps[app], ...patch }; });
    const focus = () => setFocus({ type: "builtin", key: app });
    const opts = (key) => ({ path: `apps.${app}.${key}`, onFocus: focus });

    const rows = [];
    for (const [key, rule] of Object.entries(fields)) {
      if (key === "lat" || key === "lon") continue; // set by the city picker
      if (key === "city") {
        rows.push(row(t("field.city"), t("field.cityHint"),
          cityPicker({ city: value("city"), lat: value("lat"), lon: value("lon") }, (picked) => set(picked)),
          { ...opts("city"), icon: "map-pin" }));
      } else if (rule.kind === "flags") {
        for (const flag of rule.options) {
          rows.push(row(t(`flag.${flag}`), t("field.displayInfo"),
            toggle(value(key)?.[flag], (on) => set({ [key]: { ...value(key), [flag]: on } }), { label: t(`flag.${flag}`) }),
            opts(key)));
        }
      } else {
        rows.push(row(t(`field.${key}`), null,
          segmented(rule.options.map((o) => [o, o]), value(key), (v) => set({ [key]: v }), t(`field.${key}`)),
          { ...opts(key), icon: key === "timeFormat" ? "clock" : "timer" }));
      }
    }
    const kept = store.draft.device.keep_builtins.includes(app);
    return [
      section(h("span", { class: "section-with-icon" }, appName(app), kept ? null : h("span", { class: "muted" }, ` · ${t("apps.off")}`))),
      h("div", { class: `panel${focused === app ? " focused" : ""}`, onPointerdown: focus, onFocusin: focus }, ...rows),
    ];
  });

  return page(pageHead(t("page.apps"), t("desc.apps")),
    store.state.clock.online ? null : offlineNotice(store.state.clock), ...sections);
}

