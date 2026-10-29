// Small DOM toolkit: one element helper and the handful of controls the pages share.

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key.startsWith("on")) el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "class") el.className = value;
    else if (key === "style") el.style.cssText = value; // CSSOM: allowed by the page's CSP
    else if (key === "html") el.innerHTML = value; // only ever used with our own SVG strings
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const ICONS = {
  overview: "M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z",
  playlist: "M4 6h12M4 12h12M4 18h8M18 15l4 3-4 3z",
  apps: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  display: "M12 3v2M12 19v2M5 12H3M21 12h-2M6.3 6.3 4.9 4.9M19.1 19.1l-1.4-1.4M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  settings: "M4 7h10M18 7h2M4 17h4M12 17h8M14 4v6M8 14v6",
  message: "M4 5h16v11H8l-4 4z",
  plug: "M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4",
  grip: "M9 5h.01M15 5h.01M9 12h.01M15 12h.01M9 19h.01M15 19h.01",
  plus: "M12 5v14M5 12h14",
  close: "M6 6l12 12M18 6 6 18",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  send: "M4 12 20 4l-6 16-3-7z",
};

export function icon(name) {
  const svg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICONS[name]}"/></svg>`;
  const span = h("span", { html: svg });
  return span.firstElementChild;
}

export function toggle(checked, onChange, { label, disabled } = {}) {
  return h("button", {
    class: "toggle",
    type: "button",
    role: "switch",
    "aria-checked": String(Boolean(checked)),
    "aria-label": label,
    disabled,
    onClick: (e) => {
      const next = e.currentTarget.getAttribute("aria-checked") !== "true";
      e.currentTarget.setAttribute("aria-checked", String(next));
      onChange(next);
    },
  });
}

export function segmented(options, value, onChange, label) {
  const group = h("div", { class: "segmented", role: "group", "aria-label": label });
  for (const [optValue, optLabel] of options) {
    group.append(
      h("button", {
        type: "button",
        "aria-pressed": String(optValue === value),
        onClick: () => {
          for (const b of group.children) b.setAttribute("aria-pressed", "false");
          group.querySelector(`[data-v="${CSS.escape(String(optValue))}"]`).setAttribute("aria-pressed", "true");
          onChange(optValue);
        },
        "data-v": String(optValue),
      }, optLabel),
    );
  }
  return group;
}

export function slider(min, max, value, onChange, label) {
  const out = h("output", {}, value);
  const input = h("input", {
    type: "range", min, max, step: 1, value, "aria-label": label,
    onInput: (e) => { out.textContent = e.target.value; onChange(Number(e.target.value)); },
  });
  return h("div", { class: "slider" }, input, out);
}

export function select(options, value, onChange, label) {
  const el = h("select", { class: "field", "aria-label": label, onChange: (e) => onChange(e.target.value) });
  for (const [v, text] of options) el.append(h("option", { value: v, selected: String(v) === String(value) }, text));
  return el;
}

export function row(title, hint, ...controls) {
  return h("div", { class: "row" },
    h("div", { class: "row-text" },
      h("div", { class: "row-title" }, title),
      hint && h("div", { class: `row-hint${hint.warn ? " warn" : ""}` }, hint.text ?? hint)),
    h("div", { class: "row-control" }, ...controls));
}

export function panel(...rows) {
  return h("div", { class: "panel" }, ...rows);
}

export function badge(text, tone) {
  return h("span", { class: "badge" }, h("span", { class: `dot ${tone ?? ""}` }), text);
}

export function toast(title, detail, kind = "info") {
  const el = h("div", { class: `toast ${kind}`, role: kind === "error" ? "alert" : "status" },
    title, detail && h("span", { class: "muted" }, detail));
  document.getElementById("toasts").append(el);
  setTimeout(() => el.remove(), kind === "error" ? 8000 : 4000);
}

export function menu(anchor, groups, onPick) {
  document.querySelector(".menu")?.remove();
  const box = anchor.getBoundingClientRect();
  const el = h("div", { class: "menu", role: "menu",
    style: `top:${box.bottom + window.scrollY + 4}px;left:${box.left + window.scrollX}px` });
  for (const [label, items] of groups) {
    if (!items.length) continue;
    el.append(h("div", { class: "menu-label" }, label));
    for (const [value, text] of items) {
      el.append(h("button", { type: "button", role: "menuitem",
        onClick: () => { el.remove(); onPick(value); } }, text));
    }
  }
  if (!el.querySelector("button")) el.append(h("div", { class: "menu-label" }, "Nothing to add"));
  document.body.append(el);
  el.querySelector("button")?.focus();
  const close = (e) => {
    if (!el.contains(e.target) && e.target !== anchor) { el.remove(); document.removeEventListener("pointerdown", close); }
  };
  setTimeout(() => document.addEventListener("pointerdown", close));
  el.addEventListener("keydown", (e) => { if (e.key === "Escape") { el.remove(); anchor.focus(); } });
}
