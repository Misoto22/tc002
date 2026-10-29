// Drag-to-reorder for a list of rows, with FLIP animation and keyboard support.
// Pointer: drag a row by its handle. Keyboard: focus a row, Alt+ArrowUp/Down moves it.
// Positions use offsetTop (layout, unaffected by transforms) so the maths stays simple:
// the dragged row is translated by (where the pointer wants it) - (where layout put it).

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
import { ms, token } from "./ui.js";

const ease = () => token("--ease");

function flip(list, mutate, skip) {
  const before = new Map([...list.children].map((el) => [el, el.offsetTop]));
  mutate();
  if (reduceMotion.matches) return;
  for (const el of list.children) {
    const dy = before.get(el) - el.offsetTop;
    if (el === skip || !dy) continue;
    el.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: ms("--normal"), easing: ease() });
  }
}

export function sortable(list, onReorder) {
  const order = () => [...list.children].map((el) => Number(el.dataset.index));

  list.addEventListener("pointerdown", (down) => {
    const handle = down.target.closest(".handle");
    if (!handle || down.button !== 0) return;
    const item = handle.closest(".slot");
    down.preventDefault();
    // Listen on window rather than capturing the pointer: moving the row in the DOM would
    // drop a capture, and window still hears the pointer once it leaves the list.
    item.classList.add("dragging");
    const listTop = list.getBoundingClientRect().top;
    const grab = down.clientY - listTop - item.offsetTop;

    const move = (e) => {
      const wantTop = e.clientY - listTop - grab;
      const centre = wantTop + item.offsetHeight / 2;
      // a fast pointer can pass several rows in one event: keep swapping until settled
      for (;;) {
        const prev = item.previousElementSibling;
        const next = item.nextElementSibling;
        if (prev && centre < prev.offsetTop + prev.offsetHeight / 2) {
          flip(list, () => list.insertBefore(item, prev), item);
        } else if (next && centre > next.offsetTop + next.offsetHeight / 2) {
          flip(list, () => list.insertBefore(next, item), item);
        } else break;
      }
      item.style.transform = `translateY(${wantTop - item.offsetTop}px) scale(1.01)`;
    };

    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      const from = item.style.transform;
      item.style.transform = "";
      // Commit at once; the settle animation is cosmetic and may never finish in a
      // background tab, so it must not gate the reorder.
      const settled = () => item.classList.remove("dragging");
      if (from && !reduceMotion.matches) {
        item.animate([{ transform: from }, { transform: "none" }], { duration: ms("--normal"), easing: ease() });
        setTimeout(settled, ms("--normal") + 10);
      } else settled();
      onReorder(order());
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  });

  list.addEventListener("keydown", (e) => {
    const item = e.target.closest(".slot");
    if (!item || !e.altKey || !["ArrowUp", "ArrowDown"].includes(e.key)) return;
    e.preventDefault();
    const sibling = e.key === "ArrowUp" ? item.previousElementSibling : item.nextElementSibling;
    if (!sibling) return;
    flip(list, () => (e.key === "ArrowUp" ? list.insertBefore(item, sibling) : list.insertBefore(sibling, item)));
    item.focus();
    onReorder(order());
  });
}
