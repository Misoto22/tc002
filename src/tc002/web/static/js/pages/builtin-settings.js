// The settings rows of one built-in app, from the server's schema: weather city, clock
// format, a social account's user ID and token, what the app shows. A token goes straight
// to the clock; tc002 never stores it or reads it back.

import { cityPicker } from "../citypicker.js";
import { appName, t } from "../i18n.js";
import { edit, store } from "../store.js";
import { post } from "../api.js";
import { badge, button, h, row, segmented, toast, toggle } from "../ui.js";

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

// Rows for `app`, or [] when it has nothing to set.
export function appSettings(app) {
  const fields = store.state.schema.apps[app] ?? {};
  const live = store.state.clock.apps ?? {};
  const value = (key) => store.draft.apps?.[app]?.[key] ?? live[app]?.[key];
  const set = (patch) => edit((dr) => { dr.apps[app] = { ...dr.apps[app], ...patch }; });
  const path = (key) => ({ path: `apps.${app}.${key}` });
  const rows = [];
  for (const [key, rule] of Object.entries(fields)) {
    if (key === "lat" || key === "lon") continue; // set by the city picker
    if (key === "city") {
      rows.push(row(t("field.city"), t("field.cityHint"),
        cityPicker({ city: value("city"), lat: value("lat"), lon: value("lon") }, (picked) => set(picked)),
        { ...path("city"), icon: "map-pin" }));
    } else if (rule.kind === "text") {
      rows.push(row(t(`field.${key}`), t(`field.${key}Hint`),
        h("input", { class: "field wide-field", value: value(key) ?? "", autocomplete: "off",
          "aria-label": `${appName(app)} ${t(`field.${key}`)}`, onChange: (e) => set({ [key]: e.target.value.trim() }) }),
        { ...path(key), icon: "user" }));
    } else if (rule.kind === "flags") {
      for (const flag of rule.options) {
        rows.push(row(t(`flag.${flag}`), t("field.displayInfo"),
          toggle(value(key)?.[flag], (on) => set({ [key]: { ...value(key), [flag]: on } }), { label: t(`flag.${flag}`) }),
          path(key)));
      }
    } else {
      rows.push(row(t(`field.${key}`), null,
        segmented(rule.options.map((o) => [o, o]), value(key), (v) => set({ [key]: v }), t(`field.${key}`)),
        { ...path(key), icon: key === "timeFormat" ? "clock" : "timer" }));
    }
  }
  if (store.state.schema.tokenApps.includes(app)) rows.push(tokenRow(app));
  return rows;
}
