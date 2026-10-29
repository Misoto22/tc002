// Pages. Each takes the context from app.js and returns a DOM subtree.
// Reads come from ctx.state (server truth); edits go to ctx.draft (tc002.toml) via ctx.edit.

import { badge, h, icon, menu, panel, row, segmented, select, slider, toggle } from "./ui.js";
import { sortable } from "./sortable.js";

const NAMES = {
  claude: "Claude Code", sys: "System", clock: "Clock", weather: "Weather", busy: "Busy light",
  scoreboard: "Scoreboard", tomato: "Pomodoro", stopwatch: "Stopwatch", battery: "Battery",
  soundlight: "Sound light", ipshow: "IP address", xhs: "Xiaohongshu", douyin: "Douyin",
  bilibili: "Bilibili", weibo: "Weibo", youtube: "YouTube", instagram: "Instagram",
  facebook: "Facebook", tiktok: "TikTok", x: "X", feishu: "Feishu", dingding: "DingTalk",
  wecom: "WeCom", google: "Google Calendar", icloud: "iCloud", outlook: "Outlook",
};
const CATEGORY_NAMES = { tools: "Tools", social: "Social", calendar: "Calendar" };
const PREVIEWS = { claude: "claude-busy", sys: "sys" };
const name = (key) => NAMES[key] ?? key;

function head(title, subtitle, ...actions) {
  return h("div", { class: "page-head" },
    h("div", {}, h("h1", {}, title), subtitle && h("p", {}, subtitle)),
    actions.length ? h("div", { class: "actions" }, ...actions) : null);
}

function led(screen, cls = "led") {
  return h("img", { class: cls, src: `/api/preview/${PREVIEWS[screen] ?? screen}.gif`, alt: `${name(screen)} preview` });
}

function offline(ctx) {
  const c = ctx.state.clock;
  return panel(row("Clock unreachable", { text: c.error ?? "unknown error", warn: true },
    h("button", { class: "btn", type: "button", onClick: ctx.refresh }, icon("refresh"), "Retry")));
}

// ---- Overview ------------------------------------------------------------------

export function overview(ctx) {
  const { clock, integrations } = ctx.state;
  const slots = ctx.draft.playlist.slots;
  const first = slots.find((s) => s.screen)?.screen ?? "claude";
  const hooks = integrations.hooks ?? {};
  const hooksOn = Object.values(hooks).filter((v) => v === true).length;
  const drift = clock.drift ?? [];

  const status = panel(
    row("Clock", clock.online ? `${clock.host} · firmware ${clock.base.appVer}` : { text: clock.error, warn: true },
      badge(clock.online ? "Online" : "Offline", clock.online ? "ok" : "bad")),
    row("Background service", integrations.service.split("\n")[0],
      badge(integrations.service.startsWith("state: running") ? "Running" : "Stopped",
        integrations.service.startsWith("state: running") ? "ok" : "warn")),
    row("Claude Code hooks", integrations.lastEvent
      ? `Last event: ${integrations.lastEvent.kind}, ${ago(integrations.lastEvent.secondsAgo)}` : "No event yet",
      badge(`${hooksOn}/3 installed`, hooksOn === 3 ? "ok" : "warn")),
    row("Clock matches tc002.toml", drift.length ? { text: `Differs: ${drift.join(", ")}`, warn: true } : "Everything in sync",
      drift.length
        ? h("button", { class: "btn primary", type: "button", onClick: ctx.applySaved }, "Apply now")
        : badge("In sync", "ok")),
  );

  const facts = clock.online && h("dl", { class: "panel facts" },
    ...[["IP", clock.base.ip], ["Wi-Fi", clock.base.ssid], ["Firmware", clock.base.appVer],
      ["MCU", clock.base.mcuVer], ["MAC", clock.base.mac], ["Serial", clock.base.devSn]]
      .map(([k, v]) => h("div", { class: "fact" }, h("dt", {}, k), h("dd", {}, v ?? "—"))));

  return h("div", { class: "page" },
    head("Overview", "What your clock is doing and whether it matches tc002.toml.",
      h("button", { class: "btn", type: "button", onClick: ctx.refresh }, icon("refresh"), "Refresh")),
    h("div", { class: "panel hero" }, led(first),
      h("div", { class: "row-hint" }, `Playlist: ${slots.map((s) => `${name(s.screen ?? s.builtin)} ${s.seconds}s`).join(" → ") || "empty — the device carousel is in charge"}`)),
    h("div", { class: "section-title" }, "Status"), status,
    facts && h("div", { class: "section-title" }, "Device"), facts,
    clock.online && h("div", { class: "section-title" }, "Custom apps on the clock"),
    clock.online && panel(row(clock.customApps.join(", ") || "None", "Pushed by tc002 and other tools")),
  );
}

function ago(s) {
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  return `${Math.round(s / 3600)} h ago`;
}

// ---- Playlist -------------------------------------------------------------------

export function playlist(ctx) {
  const d = ctx.draft;
  const slots = d.playlist.slots;
  const total = slots.reduce((t, s) => t + Number(s.seconds), 0);

  const list = h("div", { class: "panel slots" });
  slots.forEach((slot, i) => {
    const key = slot.screen ?? slot.builtin;
    list.append(h("div", { class: "row slot", tabindex: "0", "data-index": i,
      "aria-label": `${name(key)}, ${slot.seconds} seconds. Alt+Arrow keys to move.` },
      h("span", { class: "handle", title: "Drag to reorder" }, icon("grip")),
      slot.screen ? led(slot.screen, "led led-thumb") : h("span", { class: "builtin-tile" }, name(key)),
      h("div", { class: "row-text" },
        h("div", { class: "row-title" }, name(key)),
        h("div", { class: "row-hint" }, slot.screen ? "tc002 screen" : "Built-in app")),
      h("div", { class: "row-control" },
        h("input", { class: "field num", type: "number", min: 3, max: 600, value: slot.seconds,
          "aria-label": `${name(key)} seconds`,
          onChange: (e) => ctx.edit((dr) => { dr.playlist.slots[i].seconds = Math.max(3, Number(e.target.value) || 3); }) }),
        h("span", { class: "muted" }, "s"),
        h("button", { class: "btn ghost icon", type: "button", title: "Show on the clock now",
          onClick: () => ctx.show(slot) }, icon("eye")),
        h("button", { class: "btn ghost icon", type: "button", title: "Remove",
          onClick: () => ctx.edit((dr) => { dr.playlist.slots.splice(i, 1); }, true) }, icon("close")))));
  });
  if (!slots.length) list.append(h("div", { class: "empty" }, "No slots: the clock's own carousel decides what to show."));
  sortable(list, (order) => ctx.edit((dr) => { dr.playlist.slots = order.map((i) => slots[i]); }, true));

  const addBtn = h("button", { class: "btn", type: "button", onClick: (e) => menu(e.currentTarget, [
    ["Screens", d.screens.enabled.map((s) => [{ screen: s }, name(s)])],
    ["Built-in apps", d.device.keep_builtins.map((b) => [{ builtin: b }, name(b)])],
  ], (pick) => ctx.edit((dr) => { dr.playlist.slots.push({ ...pick, seconds: 15 }); }, true)) },
  icon("plus"), "Add slot");

  const cycle = h("div", { class: "cycle", "aria-hidden": "true" },
    ...slots.map((s, i) => h("span", { style: `width:${(100 * s.seconds) / total}%;background:hsl(${235 + i * 37} 55% ${s.screen ? 62 : 45}%)` })));

  return h("div", { class: "page" },
    head("Playlist", "What the clock shows, in order. Drag to reorder; the background service follows it.", addBtn),
    list,
    slots.length ? h("div", {}, cycle, h("div", { class: "row-hint", style: "margin-top:6px" }, `One cycle: ${total}s`)) : null,
    h("div", { class: "section-title" }, "Behaviour"),
    panel(
      row("Alerts take over", "DONE and WAIT from Claude Code jump to the Claude screen at once",
        toggle(d.alerts.takeover, (v) => ctx.edit((dr) => { dr.alerts.takeover = v; }), { label: "Alerts take over" })),
      ...ctx.state.screens.map((s) => row(`${name(s)} screen`, "Run this screen in the background service",
        toggle(d.screens.enabled.includes(s), (on) => ctx.edit((dr) => {
          dr.screens.enabled = on ? [...dr.screens.enabled, s] : dr.screens.enabled.filter((x) => x !== s);
          if (!on) dr.playlist.slots = dr.playlist.slots.filter((x) => x.screen !== s);
        }, true), { label: `${name(s)} screen` }))),
    ),
  );
}

// ---- Built-in apps --------------------------------------------------------------

export function builtins(ctx) {
  const d = ctx.draft;
  const live = ctx.state.clock.builtins ?? {};
  const inPlaylist = new Set(d.playlist.slots.map((s) => s.builtin).filter(Boolean));
  const groups = Object.keys(CATEGORY_NAMES).map((cat) => {
    const apps = ctx.state.catalogue.filter((a) => a.category === cat);
    return [h("div", { class: "section-title" }, CATEGORY_NAMES[cat]), panel(...apps.map(({ key }) => {
      const kept = d.device.keep_builtins.includes(key);
      const used = inPlaylist.has(key);
      const hints = [];
      if (live[key]) hints.push(live[key].enabled ? "On the clock now" : "Off on the clock");
      if (live[key]?.credentials) hints.push("account linked in Ulanzi Studio");
      if (used) hints.push("in the playlist");
      return row(name(key), hints.join(" · "),
        toggle(kept, (on) => ctx.edit((dr) => {
          dr.device.keep_builtins = on ? [...dr.device.keep_builtins, key] : dr.device.keep_builtins.filter((k) => k !== key);
        }, true), { label: `Keep ${name(key)}`, disabled: used && kept }));
    }))];
  });
  return h("div", { class: "page" },
    head("Built-in apps", "Apps that stay on the clock. Everything switched off here is hidden from the device."),
    ...groups.flat());
}

// ---- Display --------------------------------------------------------------------

function managed(ctx, key, clockValue) {
  const set = key in ctx.draft.display;
  const differs = set && ctx.state.clock.online && JSON.stringify(clockValue) !== JSON.stringify(ctx.draft.display[key]);
  return { text: set ? (differs ? "Set in tc002.toml · not yet on the clock" : "Set in tc002.toml") : "Clock's own value", warn: differs };
}

export function display(ctx) {
  const clock = ctx.state.clock.settings ?? {};
  const schema = ctx.state.schema;
  const value = (key) => ctx.draft.display[key] ?? clock[key];
  const set = (key, v) => ctx.edit((dr) => { dr.display[key] = v; });
  const bright = { level: "high", low: 50, mid: 80, high: 100, ...clock.brightness, ...ctx.draft.display.brightness };
  const setBright = (patch) => ctx.edit((dr) => { dr.display.brightness = { ...bright, ...patch }; Object.assign(bright, patch); });

  const rows = Object.entries(schema.display).map(([key, rule]) => {
    let control;
    if (rule.kind === "bool") control = toggle(value(key), (v) => set(key, v), { label: rule.label });
    else if (rule.kind === "int") control = slider(rule.options[0], rule.options[1], value(key) ?? rule.options[0], (v) => set(key, v), rule.label);
    else if (key === "weekStart") control = segmented([[1, "Monday"], [0, "Sunday"]], value(key), (v) => set(key, v), rule.label);
    else if (rule.options.length <= 3) control = segmented(rule.options.map((o) => [o, o]), value(key), (v) => set(key, v), rule.label);
    else control = select(rule.options.map((o) => [o, o]), value(key), (v) => set(key, v), rule.label);
    return row(rule.label, managed(ctx, key, clock[key]), control);
  });

  return h("div", { class: "page" },
    head("Display", "Clock-wide settings. Changes are saved to tc002.toml and applied to the clock."),
    ctx.state.clock.online ? null : offline(ctx),
    h("div", { class: "section-title" }, "Brightness"),
    panel(
      row("Active level", managed(ctx, "brightness", clock.brightness),
        segmented(schema.brightnessLevels.map((l) => [l, l[0].toUpperCase() + l.slice(1)]), bright.level, (v) => setBright({ level: v }), "Brightness level")),
      ...schema.brightnessLevels.map((l) => row(`${l[0].toUpperCase() + l.slice(1)} level`, "Percent; low < mid < high",
        slider(5, 100, bright[l], (v) => setBright({ [l]: v }), `${l} brightness`))),
    ),
    h("div", { class: "section-title" }, "General"),
    panel(...rows,
      row("Device carousel", ctx.draft.playlist.slots.length ? "Off — the tc002 playlist drives the screen" : "Set by the clock (no playlist)",
        badge(ctx.draft.playlist.slots.length ? "Playlist" : `${clock.carouselSpeed ?? "?"}s`))),
  );
}

// ---- App settings ---------------------------------------------------------------

export function appSettings(ctx) {
  const live = ctx.state.clock.apps ?? {};
  const sections = Object.entries(ctx.state.schema.apps).map(([app, fields]) => {
    const value = (key) => ctx.draft.apps?.[app]?.[key] ?? live[app]?.[key];
    const set = (key, v) => ctx.edit((dr) => { dr.apps[app] = { ...dr.apps[app], [key]: v }; });
    const rows = Object.entries(fields).flatMap(([key, rule]) => {
      if (rule.kind === "flags") {
        return rule.options.map((flag) => row(flag.replace("display", ""), rule.label,
          toggle(value(key)?.[flag], (on) => set(key, { ...value(key), [flag]: on }), { label: flag })));
      }
      if (rule.kind === "text") {
        return [row(rule.label, null, h("input", { class: "field", value: value(key) ?? "", "aria-label": rule.label,
          onChange: (e) => set(key, e.target.value.trim()) }))];
      }
      return [row(rule.label, null, segmented(rule.options.map((o) => [o, o]), value(key), (v) => set(key, v), rule.label))];
    });
    const kept = ctx.draft.device.keep_builtins.includes(app);
    return [h("div", { class: "section-title" }, `${name(app)}${kept ? "" : " · switched off"}`), panel(...rows)];
  });
  return h("div", { class: "page" },
    head("App settings", "Options of the built-in apps. Accounts and API keys stay in Ulanzi Studio."),
    ctx.state.clock.online ? null : offline(ctx), ...sections.flat());
}

// ---- Messages -------------------------------------------------------------------

export function messages(ctx) {
  const msg = ctx.message;
  const img = h("img", { class: "led", alt: "Message preview" });
  const refresh = () => {
    const q = new URLSearchParams({ text: msg.text || (msg.type === "alert" ? "DONE" : "HELLO") });
    if (msg.type === "alert") q.set("kind", msg.kind); else q.set("color", msg.color);
    img.src = `/api/preview/${msg.type}.gif?${q}`;
  };
  let timer;
  const later = () => { clearTimeout(timer); timer = setTimeout(refresh, 250); };
  refresh();

  const colors = h("div", { class: "swatches" }, ...Object.entries(ctx.state.colors).map(([key, hex]) =>
    h("button", { class: "swatch", type: "button", style: `background:${hex}`, title: key, "aria-label": key,
      "aria-pressed": String(msg.color === key),
      onClick: (e) => { msg.color = key; for (const s of colors.children) s.setAttribute("aria-pressed", "false"); e.currentTarget.setAttribute("aria-pressed", "true"); refresh(); } })));

  const options = h("div", {});
  const renderOptions = () => options.replaceChildren(msg.type === "alert"
    ? row("Kind", "Icon and colour", segmented(ctx.state.alertKinds.map((k) => [k, k[0].toUpperCase() + k.slice(1)]), msg.kind, (k) => { msg.kind = k; refresh(); }, "Alert kind"))
    : row("Colour", "Long text scrolls across", colors));
  renderOptions();

  return h("div", { class: "page" },
    head("Messages", "Send a one-off message. It plays, then clears itself."),
    h("div", { class: "panel hero" }, img),
    h("div", { class: "section-title" }, "Compose"),
    panel(
      row("Type", null, segmented([["text", "Text"], ["alert", "Alert"]], msg.type, (t) => { msg.type = t; renderOptions(); refresh(); }, "Message type")),
      row("Message", "ASCII, shown upper case", h("input", { class: "field", style: "width:260px", value: msg.text,
        maxlength: 60, placeholder: "BUILD OK", "aria-label": "Message text",
        onInput: (e) => { msg.text = e.target.value; later(); } })),
      options,
      row("", null, h("button", { class: "btn primary", type: "button", disabled: !ctx.state.clock.online,
        onClick: () => ctx.send({ ...msg }) }, icon("send"), "Send to clock")),
    ));
}

// ---- Integrations ---------------------------------------------------------------

export function integrations(ctx) {
  const { integrations: it, config } = ctx.state;
  const hookRows = Object.entries(it.hooks).map(([event, on]) =>
    row(event, { Stop: "Turn finished → DONE", Notification: "Claude needs you → WAIT", UserPromptSubmit: "You replied → clear" }[event] ?? String(on),
      badge(on === true ? "Installed" : "Missing", on === true ? "ok" : "warn")));
  return h("div", { class: "page" },
    head("Integrations", "How tc002 is wired into this Mac."),
    h("div", { class: "section-title" }, "Background service"),
    panel(row("launchd agent dev.tc002.watch", it.service.split("\n")[0],
      badge(it.service.startsWith("state: running") ? "Running" : "Stopped", it.service.startsWith("state: running") ? "ok" : "warn"))),
    h("div", { class: "section-title" }, "Claude Code hooks"), panel(...hookRows),
    h("div", { class: "section-title" }, "Configuration"),
    panel(row("tc002.toml", h("span", { class: "mono" }, config.path ?? "not set — run tc002 setup --config")),
      row("Command line", h("span", { class: "mono" }, "tc002 doctor · tc002 layout apply · tc002 uninstall"))),
  );
}
