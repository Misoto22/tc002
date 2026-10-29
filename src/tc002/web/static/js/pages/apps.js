import { cityPicker } from "../citypicker.js";
import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { post } from "../api.js";
import { appIcon, badge, button, h, pageHead, row, section, segmented, toast, toggle } from "../ui.js";
import { offlineNotice, page } from "./common.js";

const APP_ICON = { clock: "clock", weather: "cloud-sun", busy: "timer", tomato: "timer" };

// A social token goes straight to the clock; tc002 never stores it or reads it back.
function tokenRow(app) {
  const onClock = store.state.clock.builtins?.[app]?.credentials;
  const input = h("input", { class: "field", type: "password", autocomplete: "off",
    placeholder: t("field.tokenPlaceholder"), "aria-label": t("field.token") });
  const send = async () => {
    try {
      await post("/api/social-token", { app, token: input.value });
      input.value = "";
      toast(t("field.tokenSent"));
    } catch (err) {
      toast(err.title, err.message, "error");
    }
  };
  return row(t("field.token"), t("field.tokenHint"),
    [onClock ? badge(t("field.tokenSet"), "ok") : null, input, button(t("field.tokenSend"), send, { ico: "send" })],
    { icon: "key-round" });
}

export function apps() {
  const focused = store.focus.type === "builtin" && APP_ICON[store.focus.key] ? store.focus.key : "clock";
  setFocus({ type: "builtin", key: focused });
  const live = store.state.clock.apps ?? {};

  const hidden = [];
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
      } else if (rule.kind === "text") {
        rows.push(row(t(`field.${key}`), t(`field.${key}Hint`),
          h("input", { class: "field wide-field", value: value(key) ?? "", autocomplete: "off",
            "aria-label": `${appName(app)} ${t(`field.${key}`)}`, onChange: (e) => set({ [key]: e.target.value.trim() }) }),
          { ...opts(key), icon: "user" }));
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
    if (store.state.schema.tokenApps.includes(app)) rows.push(tokenRow(app));
    const kept = store.draft.device.keep_builtins.includes(app);
    // social counters you have not kept would only lengthen the page: list them at the end
    if (!kept && "uid" in fields) { hidden.push(app); return []; }
    return [
      section([appIcon(app, "sm"), appName(app), kept ? null : h("span", { class: "muted" }, `· ${t("apps.off")}`)]),
      h("div", { class: `panel${focused === app ? " focused" : ""}`, onPointerdown: focus, onFocusin: focus }, ...rows),
    ];
  });

  return page(pageHead(t("page.apps"), t("desc.apps")),
    store.state.clock.online ? null : offlineNotice(store.state.clock), ...sections,
    hidden.length ? h("p", { class: "muted" }, t("apps.moreSocial", { list: hidden.map(appName).join(" · ") }),
      " ", h("a", { class: "link", href: "#builtins" }, `${t("page.builtins")} →`)) : null);
}

