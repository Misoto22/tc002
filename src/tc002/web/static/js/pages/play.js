// Play a game on the clock with this keyboard. The server runs the game and pushes each
// frame to the clock (games/session.py); this page sends key presses and mirrors frames.

import { get, post } from "../api.js";
import { t } from "../i18n.js";
import { H, SCALE, W, draw } from "../led.js";
import { setFocus, store } from "../store.js";
import { TIMING } from "../timing.js";
import { button, h, pageHead, toast } from "../ui.js";
import { offlineNotice, page } from "./common.js";

const KEYS = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down", " ": "space",
  a: "left", d: "right", w: "up", s: "down" };

let playing = null; // name of the game running, from this page
let poll = null;
let canvas = null;
let scoreEl = null;

function send(e, down) {
  const key = KEYS[e.key];
  if (!playing || !key || e.target.closest?.("input, textarea, select")) return;
  e.preventDefault();
  if (e.repeat && down) return; // held keys are tracked server-side
  post("/api/game/key", { key, down }).catch((err) => console.warn("tc002: key not sent", err));
}
addEventListener("keydown", (e) => send(e, true));
addEventListener("keyup", (e) => send(e, false));

async function mirror() {
  if (!playing || location.hash.slice(1) !== "play") return stop();
  try {
    const f = await get("/api/game/frame");
    if (!f.running) {
      if (f.error) toast(t("play.lost"), f.error, "error");
      playing = null;
      rerender();
      return;
    }
    draw(canvas, { px: f.px });
    scoreEl.textContent = f.over ? t("play.over", { score: f.score }) : t("play.score", { score: f.score });
  } catch (err) {
    console.warn("tc002: frame not read", err); // the next poll retries
  }
  poll = setTimeout(mirror, TIMING.gameFrameMs);
}

async function start(name) {
  try {
    await post("/api/game", { action: "start", game: name });
    playing = name;
    rerender();
    mirror();
  } catch (err) {
    toast(err.title, err.message, "error");
  }
}

async function stop() {
  clearTimeout(poll);
  if (!playing) return;
  playing = null;
  await post("/api/game", { action: "stop" }).catch((err) => console.warn("tc002: stop failed", err));
  rerender();
}

const rerender = () => {
  if (location.hash.slice(1) === "play") document.getElementById("page").replaceChildren(play());
};

// A game: a few seconds of it playing itself, its keys, and Play.
function card(name) {
  const online = store.state.clock.online;
  return h("div", { class: "game-card" },
    h("img", { class: "led-thumb game-thumb", alt: t("play.preview"), loading: "lazy", width: W * SCALE, height: H * SCALE,
      src: `/api/preview/game-${name}.gif` }),
    h("div", { class: "game-text" },
      h("div", { class: "choice-title" }, t(`play.${name}`)),
      h("div", { class: "muted" }, t(`play.${name}Hint`))),
    button(t("play.start"), () => start(name), { kind: "primary", ico: "play", disabled: !online }));
}

export function play() {
  setFocus({ type: "rotation" });
  if (!playing) {
    return page(pageHead(t("page.play"), t("desc.play")),
      store.state.clock.online ? null : offlineNotice(store.state.clock),
      h("div", { class: "games" }, ...Object.keys(store.state.games).map(card)));
  }
  canvas = h("canvas", { class: "led-canvas game-canvas", width: W * SCALE, height: H * SCALE, "aria-label": t(`play.${playing}`) });
  scoreEl = h("div", { class: "game-score mono" });
  return page(pageHead(t(`play.${playing}`), t("play.keys"), button(t("play.stop"), stop, { ico: "x" })),
    h("div", { class: "stage game-stage" }, canvas), scoreEl);
}
