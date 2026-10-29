import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { pageHead, panel, row, section, toggle } from "../ui.js";
import { page } from "./common.js";

const CATEGORY_ICON = { tools: "clock", social: "sparkles", calendar: "history" };

export function builtins() {
  if (store.focus.type !== "builtin") setFocus({ type: "builtin", key: "clock" });
  const d = store.draft;
  const live = store.state.clock.builtins ?? {};
  const inPlaylist = new Set(d.playlist.slots.map((s) => s.builtin).filter(Boolean));

  const groups = ["tools", "social", "calendar"].flatMap((cat) => {
    const apps = store.state.catalogue.filter((a) => a.category === cat);
    return [section(t(`builtins.cat.${cat}`)), panel(...apps.map(({ key }) => {
      const kept = d.device.keep_builtins.includes(key);
      const used = inPlaylist.has(key);
      const hints = [];
      if (live[key]) hints.push(live[key].enabled ? t("builtins.onNow") : t("builtins.offNow"));
      if (live[key]?.credentials) hints.push(t("builtins.linked"));
      if (used) hints.push(t("builtins.inPlaylist"));
      return row(appName(key), hints.join(" · "),
        toggle(kept, (on) => edit((dr) => {
          dr.device.keep_builtins = on ? [...dr.device.keep_builtins, key] : dr.device.keep_builtins.filter((k) => k !== key);
        }, { rerender: true }), { label: appName(key), disabled: used && kept }),
        { path: "device.keep_builtins", icon: CATEGORY_ICON[cat], onFocus: () => setFocus({ type: "builtin", key }) });
    }))];
  });
  return page(pageHead(t("page.builtins"), t("desc.builtins")), ...groups);
}
