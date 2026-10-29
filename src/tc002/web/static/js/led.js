// A 52x16 LED matrix in a <canvas>, using the Python renderer's pixel fonts and palette
// (served by /api/led), so previews drawn here match what tc002 pushes.

import { assets } from "./assets.js";

// The matrix size comes from the Python renderer (/api/led) at start-up; see assets.js.
export let W = 0;
export let H = 0;
export const SCALE = 10; // canvas pixels per LED in the previews

export function setSize({ width, height }) {
  W = width;
  H = height;
}
const font = () => assets.font;

const rgb = (c) => (typeof c === "number" ? c : parseInt(c.slice(1), 16));

function glyph(table, ch) {
  const spec = table[ch.toUpperCase()] ?? table["?"];
  return spec.split("|");
}

export class Frame {
  constructor() { this.px = new Uint32Array(W * H); }

  set(x, y, c) { if (x >= 0 && x < W && y >= 0 && y < H) this.px[y * W + x] = rgb(c); }

  rect(x, y, w, h, c) { for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) this.set(i, j, c); }

  sprite(x, y, rows, c) {
    rows.forEach((row, dy) => [...row].forEach((ch, dx) => { if (ch === "#") this.set(x + dx, y + dy, c); }));
  }

  width(text, big = true) {
    const table = big ? font().big : font().small;
    return [...text].reduce((w, ch) => w + glyph(table, ch)[0].length + 1, 0) - (text ? 1 : 0);
  }

  text(x, y, text, c, big = true) {
    const table = big ? font().big : font().small;
    for (const ch of text) {
      const rows = glyph(table, ch);
      this.sprite(x, y, rows, c);
      x += rows[0].length + 1;
    }
    return x;
  }

  centred(y, text, c, big = true) { this.text(Math.floor((W - this.width(text, big)) / 2), y, text, c, big); }
}

// Round lamps on a dark panel, like the real clock.
export function draw(canvas, frame) {
  const g = canvas.getContext("2d");
  const cell = canvas.width / W;
  const r = cell / 2 - Math.max(0.6, cell * 0.09);
  g.fillStyle = assets.palette.panel;
  g.fillRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const p = frame.px[y * W + x];
      g.fillStyle = p ? `#${p.toString(16).padStart(6, "0")}` : assets.palette.off;
      g.beginPath();
      g.arc(x * cell + cell / 2, y * cell + cell / 2, r, 0, Math.PI * 2);
      g.fill();
    }
  }
}
