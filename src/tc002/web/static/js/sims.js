// Approximate renderings of the clock's built-in apps, driven by the draft settings, so a
// change to time format, week start or weather items can be seen before it is saved.
// The firmware draws these itself; these are close stand-ins, labelled as such in the UI.

import { assets } from "./assets.js";
import { Frame, W } from "./led.js";
import { TIMING } from "./timing.js";

// colours by name from the shared LED palette (render/palette.py)
const c = (name) => assets.palette[name];

const SUN = ["..#..", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "..#.."];
const DROP = ["..#..", "..#..", ".###.", ".###.", "#####", "#####", ".###."];
const GAUGE = [".###.", "#...#", "#..##", "#.#.#", "#...#", ".###.", "....."];
const LEAF = ["...##", "..###", ".####", "####.", "###..", "#....", "#...."];
const TOMATO = ["..#..", ".###.", "#####", "#####", "#####", ".###.", "....."];
const pad = (n) => String(n).padStart(2, "0");

// Wall time in the clock's time zone ("UTC+8").
function clockTime(settings, now) {
  const offset = Number((settings.timezone ?? "UTC+0").slice(3)) || 0;
  return new Date(now + offset * 3600_000);
}

function weekBar(f, settings, d) {
  if (!settings.showWeek) return;
  const start = Number(settings.weekStart ?? 1);
  const today = (d.getUTCDay() - start + 7) % 7;
  const x0 = Math.floor((W - (7 * 5 + 6 * 2)) / 2);
  for (let i = 0; i < 7; i++) f.rect(x0 + i * 7, 15, 5, 1, i === today ? c("green") : c("dim"));
}

function clock(settings, apps, now) {
  const d = clockTime(settings, now);
  const f = new Frame();
  const showDate = Math.floor(now / 1000) % 10 >= 7; // 7 s time, 3 s date
  const y = settings.showWeek ? 3 : 4;
  if (showDate) {
    const [m, day] = [pad(d.getUTCMonth() + 1), pad(d.getUTCDate())];
    f.centred(y, settings.dateFormat === "DD/MM" ? `${day}/${m}` : `${m}/${day}`, c("sky"));
  } else {
    const fmt = apps.clock?.timeFormat ?? "HH:MM";
    let hours = d.getUTCHours();
    const blink = Math.floor(now / TIMING.clockBlinkMs) % 2 ? ":" : " ";
    if (fmt === "HH:MM AP") {
      const ap = hours < 12 ? "AM" : "PM";
      hours = hours % 12 || 12;
      const x = f.text(4, y, `${pad(hours)}${blink}${pad(d.getUTCMinutes())}`, c("soft_white"));
      f.text(x + 3, y + 2, ap, c("amber"), false);
    } else if (fmt === "HH:MM:SS") {
      f.centred(y, `${pad(hours)}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`, c("soft_white"));
    } else {
      f.centred(y, `${pad(hours)}${blink}${pad(d.getUTCMinutes())}`, c("soft_white"));
    }
  }
  weekBar(f, settings, d);
  return f;
}

function weather(settings, apps, now) {
  const flags = apps.weather?.displayInfo ?? { displayTemperature: true };
  const items = [
    ["displayTemperature", SUN, c("amber"), "23", true],
    ["displayHumidity", DROP, c("sky"), "48%", false],
    ["displayPressure", GAUGE, c("soft_white"), "1013", false],
    ["displayAqi", LEAF, c("green"), "AQI 42", false],
  ].filter(([key]) => flags[key]);
  const f = new Frame();
  if (!items.length) return f;
  const [, icon, colour, value, degree] = items[Math.floor(now / TIMING.simCycleMs) % items.length];
  f.sprite(3, 4, icon, colour);
  const x = f.text(12, 4, value, c("soft_white"), value.length <= 4);
  if (degree) f.rect(x, 4, 2, 2, c("soft_white"));
  return f;
}

function timer(settings, apps, now, key) {
  const minutes = Number(apps[key]?.focusTime ?? (key === "busy" ? 30 : 10));
  const left = minutes * 60 - (Math.floor(now / 1000) % (minutes * 60));
  const f = new Frame();
  if (key === "tomato") f.sprite(3, 4, TOMATO, c("red"));
  else f.text(2, 1, "BUSY", c("red"), false);
  f.text(key === "tomato" ? 12 : 14, key === "tomato" ? 4 : 7, `${pad(Math.floor(left / 60))}:${pad(left % 60)}`, c("soft_white"));
  return f;
}

// The built-in apps drawn here because their picture follows unsaved settings (format,
// city, timer lengths). Every other app's picture comes from the server
// (/api/preview/builtin-<key>.gif), the same one its list row shows.
export const SIMULATED = new Set(["clock", "weather", "busy", "tomato"]);

// One frame of built-in app `key` (one of SIMULATED) at time `now` (ms).
export function simulate(key, settings, apps, now) {
  if (key === "clock") return clock(settings, apps, now);
  if (key === "weather") return weather(settings, apps, now);
  return timer(settings, apps, now, key);
}
