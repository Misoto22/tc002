// Services the API screens connect to. Plain settings (an address) are saved to
// tc002.toml with the page; secrets go straight to the macOS Keychain and are never shown
// again, only whether one is saved. Testing a service reads it for real and shows the
// result in place: working or not (and why), how long it took, the picture the clock
// would get and what was read.

import { post } from "../api.js";
import { appName, t } from "../i18n.js";
import { liveCheck } from "../livecheck.js";
import { edit, load, setFocus, store } from "../store.js";
import { badge, button, h, pageHead, panel, row, section, toast } from "../ui.js";
import { page } from "./common.js";

const SCREEN_OF = { homeassistant: "home", calendar: "agenda" };
const OPEN = ["air", "crypto", "stocks", "hackernews", "github", "nowplaying"];
const opened = new Set(); // screens whose test result is showing, kept across redraws

// A result slot under a service, and the button that fills it.
function tester(screen) {
  const slot = h("div", { class: "conn-result" }, opened.has(screen) ? liveCheck(screen) : null);
  const open = () => { opened.add(screen); slot.replaceChildren(liveCheck(screen)); };
  return { slot, open };
}

const settingsLink = (screen) => h("a", { class: "btn ghost", href: `#rotation/${screen}` }, t("place.settings"));

function secretRow(connection, field, status) {
  const input = h("input", { class: "field wide-field", type: "password", autocomplete: "off",
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
    status.saved ? button(t("conn.remove"), () => save(""), { ico: "x" }) : null,
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
    const test = tester(screen);
    return [
      section(t(`conn.${name}`), h("span", { class: "muted" }, `· ${t(`conn.${name}Hint`)}`), h("span", { class: "spacer" }),
        settingsLink(screen), button(t("conn.try"), test.open, { ico: "play" })),
      panel(...Object.entries(fields).map(([field, s]) => (s.secret ? secretRow(name, field, s) : plainRow(name, field)))),
      test.slot,
    ];
  });
  return page(
    pageHead(t("page.connections"), t("desc.connections")),
    Object.keys(status).length ? known : h("p", { class: "muted" }, t("conn.noKeychain")),
    section(t("conn.open"), h("span", { class: "muted" }, `· ${t("conn.openHint")}`)),
    panel(...OPEN.map((screen) => {
      const test = tester(screen);
      return h("div", { class: "conn-item" }, row(appName(screen), t(`conn.about.${screen}`),
        [settingsLink(screen), button(t("conn.try"), test.open, { ico: "play" })], { app: screen }), test.slot);
    })),
  );
}
