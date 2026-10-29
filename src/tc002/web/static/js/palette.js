// ⌘K command palette: fuzzy-search pages, actions, "show on clock" targets and preferences.

import { appName, lang, t } from "./i18n.js";
import { PALETTES } from "./prefs.js";
import { h, icon, ms } from "./ui.js";

let open = null;

// Subsequence match, so "plst" finds "Rotation"; earlier and tighter matches rank higher.
function score(query, text) {
  if (!query) return 1;
  const q = query.toLowerCase();
  const s = text.toLowerCase();
  if (s.includes(q)) return 100 - s.indexOf(q);
  let i = 0;
  let gaps = 0;
  for (const ch of s) {
    if (ch === q[i]) i++;
    else if (i) gaps++;
    if (i === q.length) return 50 - gaps;
  }
  return 0;
}

export function openPalette(commands) {
  if (open) return;
  let items = [];
  let active = 0;
  const input = h("input", { class: "palette-input", placeholder: t("pal.placeholder"),
    "aria-label": t("pal.placeholder"), role: "combobox", "aria-expanded": "true", "aria-controls": "palette-list" });
  const list = h("div", { class: "palette-list", id: "palette-list", role: "listbox" });
  const dialog = h("div", { class: "palette", role: "dialog", "aria-modal": "true", "aria-label": t("pal.dialog") },
    h("div", { class: "palette-search" }, icon("search"), input, h("kbd", {}, "esc")), list);
  const backdrop = h("div", { class: "backdrop", onPointerdown: (e) => { if (e.target === backdrop) close(); } }, dialog);

  function render() {
    const q = input.value.trim();
    items = commands
      // the group name counts, but far less than the command itself
      .map((c) => ({ ...c, s: Math.max(score(q, c.label), score(q, c.alt ?? ""), score(q, c.group) * 0.2) }))
      .filter((c) => c.s > 0)
      .sort((a, b) => (q ? b.s - a.s : 0));
    active = Math.min(active, Math.max(0, items.length - 1));
    const groups = new Map();
    items.forEach((c, i) => {
      if (!groups.has(c.group)) groups.set(c.group, []);
      groups.get(c.group).push(h("div", {
        class: "palette-item", role: "option", id: `pal-${i}`, "aria-selected": String(i === active),
        onPointermove: () => { if (active !== i) { active = i; paint(); } },
        onClick: () => run(i),
      }, icon(c.icon), h("span", {}, c.label), c.hint && h("span", { class: "muted palette-hint" }, c.hint)));
    });
    list.replaceChildren(...[...groups].flatMap(([g, els]) => [h("div", { class: "palette-group" }, g), ...els]));
    if (!items.length) list.append(h("div", { class: "palette-empty" }, t("pal.empty")));
    paint();
  }

  function paint() {
    list.querySelectorAll(".palette-item").forEach((el, i) => el.setAttribute("aria-selected", String(i === active)));
    input.setAttribute("aria-activedescendant", `pal-${active}`);
    list.querySelector(`#pal-${active}`)?.scrollIntoView({ block: "nearest" });
  }

  function run(i) {
    const cmd = items[i];
    close();
    cmd?.run();
  }

  function close() {
    dialog.classList.add("closing");
    backdrop.classList.add("closing");
    setTimeout(() => backdrop.remove(), ms("--fast") + 20);
    open = null;
    previous?.focus();
  }

  input.addEventListener("input", () => { active = 0; render(); });
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); active = (active + 1) % Math.max(1, items.length); paint(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = (active - 1 + items.length) % Math.max(1, items.length); paint(); }
    else if (e.key === "Enter") { e.preventDefault(); run(active); }
  });

  const previous = document.activeElement;
  document.body.append(backdrop);
  open = backdrop;
  render();
  input.focus();
}

// The command list for the current state; built fresh each time the palette opens.
export function commands({ pages, go, store, actions, setPref }) {
  const list = [];
  const other = lang() === "zh" ? "en" : "zh";
  for (const [id, , ico] of pages) list.push({ group: t("pal.go"), icon: ico, label: t(`page.${id}`), alt: id, run: () => go(id) });
  const dirty = actions.dirtyCount() > 0;
  if (dirty) {
    list.push({ group: t("pal.actions"), icon: "save", label: t("pal.save"), hint: "⌘S", run: actions.save });
    list.push({ group: t("pal.actions"), icon: "undo-2", label: t("pal.discard"), run: actions.discard });
  }
  list.push(
    { group: t("pal.actions"), icon: "refresh-cw", label: t("pal.apply"), run: actions.applySaved },
    { group: t("pal.actions"), icon: "radio", label: store.live.on ? t("pal.liveOff") : t("pal.liveOn"), run: () => actions.setLive(!store.live.on) },
    { group: t("pal.actions"), icon: "bell", label: t("pal.testAlert"), run: () => actions.send({ type: "alert", text: t("msg.sampleAlert"), kind: "done" }) },
    { group: t("pal.actions"), icon: "history", label: t("pal.activity"), run: actions.openActivity },
    { group: t("pal.actions"), icon: "refresh-cw", label: t("pal.refresh"), run: actions.refresh },
  );
  const targets = [
    ...store.draft.screens.enabled.map((s) => ({ screen: s })),
    ...store.draft.device.keep_builtins.map((b) => ({ builtin: b })),
  ];
  for (const target of targets) {
    const key = target.screen ?? target.builtin;
    list.push({ group: t("pal.show"), icon: "eye", label: appName(key), alt: key, run: () => actions.show(target) });
  }
  list.push(
    { group: t("pal.prefs"), icon: "monitor", label: t("pal.themeSystem"), alt: "theme system", run: () => setPref("theme", "system") },
    { group: t("pal.prefs"), icon: "sun", label: t("pal.themeLight"), alt: "theme light", run: () => setPref("theme", "light") },
    { group: t("pal.prefs"), icon: "moon", label: t("pal.themeDark"), alt: "theme dark", run: () => setPref("theme", "dark") },
    ...PALETTES.map((id) => ({ group: t("pal.prefs"), icon: "sun-moon", label: `${t("ui.palette")}: ${t(`palette.${id}`)}`,
      alt: `colour palette theme ${id}`, run: () => setPref("palette", id) })),
    { group: t("pal.prefs"), icon: "languages", label: t(other === "zh" ? "pal.langZh" : "pal.langEn"), alt: "language", run: () => setPref("lang", other) },
  );
  return list;
}
