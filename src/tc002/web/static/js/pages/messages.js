import { t } from "../i18n.js";
import { send, setFocus, store } from "../store.js";
import { button, h, pageHead, panel, row, section, segmented } from "../ui.js";
import { page } from "./common.js";

// The draft survives page switches within a visit.
const draft = { type: "text", text: "", color: "green", kind: "done" };

function previewSrc() {
  const q = new URLSearchParams({ text: draft.text || (draft.type === "alert" ? "DONE" : "HELLO") });
  if (draft.type === "alert") q.set("kind", draft.kind);
  else q.set("color", draft.color);
  return `/api/preview/${draft.type}.gif?${q}`;
}

export function messages() {
  let timer;
  const refresh = () => setFocus({ type: "message", src: previewSrc() });
  const later = () => { clearTimeout(timer); timer = setTimeout(refresh, 250); };
  refresh();

  const swatches = h("div", { class: "swatches", role: "radiogroup", "aria-label": t("msg.colour") },
    ...Object.entries(store.state.colors).map(([key, hex]) => h("button", {
      class: "swatch", type: "button", role: "radio", style: `--swatch:${hex}`, title: key, "aria-label": key,
      "aria-checked": String(draft.color === key),
      onClick: (e) => {
        draft.color = key;
        for (const s of swatches.children) s.setAttribute("aria-checked", "false");
        e.currentTarget.setAttribute("aria-checked", "true");
        refresh();
      },
    })));

  const options = h("div", {});
  const renderOptions = () => options.replaceChildren(draft.type === "alert"
    ? row(t("msg.kind"), t("msg.kindHint"),
      segmented(store.state.alertKinds.map((k) => [k, t(`kind.${k}`)]), draft.kind, (k) => { draft.kind = k; refresh(); }, t("msg.kind")),
      { icon: "bell" })
    : row(t("msg.colour"), t("msg.colourHint"), swatches, { icon: "sparkles" }));
  renderOptions();

  return page(
    pageHead(t("page.messages"), t("desc.messages")),
    section(t("section.compose")),
    panel(
      row(t("msg.type"), null,
        segmented([["text", t("msg.text")], ["alert", t("msg.alert")]], draft.type, (v) => { draft.type = v; renderOptions(); refresh(); }, t("msg.type")),
        { icon: "message-square-text" }),
      row(t("msg.message"), t("msg.messageHint"),
        h("input", { class: "field wide-field", value: draft.text, maxlength: 60, placeholder: "BUILD OK",
          "aria-label": t("msg.message"), onInput: (e) => { draft.text = e.target.value; later(); } }),
        { icon: "keyboard" }),
      options,
      h("div", { class: "row row-end" },
        button(t("btn.send"), () => send({ ...draft, text: draft.text || "HELLO" }),
          { kind: "primary", ico: "send", disabled: !store.state.clock.online })),
    ),
  );
}
