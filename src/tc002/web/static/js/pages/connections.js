// Services the API screens connect to. Plain settings (an address) are saved to
// tc002.toml with the page; secrets go straight to the macOS Keychain and are never shown
// again, only whether one is saved. Each screen can be tried without touching the clock.

import { post } from "../api.js";
import { appName, t } from "../i18n.js";
import { edit, load, setFocus, store } from "../store.js";
import { badge, button, h, pageHead, panel, row, section, toast } from "../ui.js";
import { page } from "./common.js";

const SCREEN_OF = { homeassistant: "home", calendar: "agenda" };
const OPEN = ["air", "crypto", "stocks", "hackernews", "github", "nowplaying"];

async function trial(screen, hint) {
  try {
    const r = await post("/api/try-screen", { screen });
    if (r.ok) toast(t("conn.works", { name: appName(screen) }));
    else toast(t("conn.fails", { name: appName(screen) }), r.error, "error");
  } catch (err) {
    toast(err.title, err.message, "error");
  }
  hint?.();
}

function secretRow(connection, field, status) {
  const input = h("input", { class: "field", type: "password", autocomplete: "off",
    placeholder: t(`conn.${connection}.${field}Placeholder`), "aria-label": t(`conn.${connection}.${field}`) });
  const save = async (value) => {
    try {
      await post("/api/secret", { connection, field, value });
      toast(value ? t("conn.saved") : t("conn.removed"));
      await load();
    } catch (err) {
      toast(err.title, err.message, "error");
    }
  };
  return row(t(`conn.${connection}.${field}`), t("conn.secretHint"), [
    status.saved ? badge(t("conn.inKeychain"), "ok") : null,
    input,
    button(t("conn.save"), () => save(input.value), { ico: "key-round" }),
    status.saved ? button(t("conn.remove"), () => save(""), { kind: "ghost" }) : null,
  ], { icon: "key-round" });
}

function plainRow(connection, field) {
  const value = store.draft.connections?.[connection]?.[field] ?? "";
  return row(t(`conn.${connection}.${field}`), null,
    h("input", { class: "field wide-field", value, autocomplete: "off",
      placeholder: t(`conn.${connection}.${field}Placeholder`), "aria-label": t(`conn.${connection}.${field}`),
      onChange: (e) => edit((dr) => {
        dr.connections = { ...dr.connections, [connection]: { ...dr.connections?.[connection], [field]: e.target.value.trim() } };
      }) }),
    { icon: "link", path: `connections.${connection}.${field}` });
}

export function connections() {
  setFocus({ type: "rotation" });
  const status = store.state.connections ?? {};
  const known = Object.entries(status).flatMap(([name, fields]) => {
    const screen = SCREEN_OF[name];
    return [
      section(t(`conn.${name}`), h("span", { class: "muted" }, `· ${t(`conn.${name}Hint`)}`), h("span", { class: "spacer" }),
        button(t("conn.try"), () => trial(screen), { kind: "ghost", ico: "play" })),
      panel(...Object.entries(fields).map(([field, s]) => (s.secret ? secretRow(name, field, s) : plainRow(name, field)))),
    ];
  });
  return page(
    pageHead(t("page.connections"), t("desc.connections")),
    Object.keys(status).length ? known : h("p", { class: "muted" }, t("conn.noKeychain")),
    section(t("conn.open"), h("span", { class: "muted" }, `· ${t("conn.openHint")}`)),
    panel(...OPEN.map((screen) => row(appName(screen), t(`conn.about.${screen}`),
      button(t("conn.try"), () => trial(screen), { kind: "ghost", ico: "play" }), { app: screen }))),
  );
}
