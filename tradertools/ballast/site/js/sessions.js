// Ballast: the market sessions clock. The four conventional trading sessions in their own cities' time (so daylight
// saving is right in every country), the forex week (Sunday 17:00 to Friday 17:00 New York time), and when each opens
// or closes next. These are conventions: a broker's own trading hours for a symbol can differ. Pure; tested.
import { tzOffset, zonedTime } from "./limits.js";

export const SESSIONS = [
  { name: "Sydney", tz: "Australia/Sydney", open: 7, close: 16 },
  { name: "Tokyo", tz: "Asia/Tokyo", open: 9, close: 18 },
  { name: "London", tz: "Europe/London", open: 8, close: 17 },
  { name: "New York", tz: "America/New_York", open: 8, close: 17 },
];

function localParts(ms, tz) {
  const d = new Date(ms + tzOffset(ms, tz));
  return { y: d.getUTCFullYear(), m: d.getUTCMonth(), d: d.getUTCDate(), wd: d.getUTCDay(), h: d.getUTCHours() + d.getUTCMinutes() / 60 };
}

/** Is the forex market's week open at `ms` (Sunday 17:00 to Friday 17:00, New York time)? */
export function fxWeekOpen(ms) {
  const p = localParts(ms, "America/New_York");
  if (p.wd === 6) return false;
  if (p.wd === 0) return p.h >= 17;
  if (p.wd === 5) return p.h < 17;
  return true;
}

function isOpen(s, ms) {
  const p = localParts(ms, s.tz);
  return p.wd >= 1 && p.wd <= 5 && p.h >= s.open && p.h < s.close && fxWeekOpen(ms);
}

/** Every moment in the next ten days when `s` could change: its own opens and closes, and the forex week's edges. */
function edges(s, ms) {
  const out = [];
  const p = localParts(ms, s.tz);
  const ny = localParts(ms, "America/New_York");
  for (let k = -1; k <= 10; k++) {
    const day = new Date(Date.UTC(p.y, p.m, p.d + k));
    out.push(zonedTime(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), s.open, s.tz));
    out.push(zonedTime(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), s.close, s.tz));
    const nd = new Date(Date.UTC(ny.y, ny.m, ny.d + k));
    out.push(zonedTime(nd.getUTCFullYear(), nd.getUTCMonth(), nd.getUTCDate(), 17, "America/New_York"));
  }
  return out.filter((t) => t > ms).sort((a, b) => a - b);
}

/** The next moment after `ms` when `s` opens (edge = "open") or closes (edge = "close"). */
function nextEdge(s, ms, edge) {
  for (const t of edges(s, ms)) {
    const before = isOpen(s, t - 60000);
    const after = isOpen(s, t + 60000);
    if (edge === "open" ? !before && after : before && !after) return t;
  }
  return null;
}

/** Each session now: { name, open, next (ms of the next open or close), local (its city's clock, "HH:MM") }. */
export function sessionState(ms) {
  return SESSIONS.map((s) => {
    const open = isOpen(s, ms);
    const p = localParts(ms, s.tz);
    const hh = String(Math.floor(p.h)).padStart(2, "0");
    const mm = String(Math.round((p.h % 1) * 60) % 60).padStart(2, "0");
    return { name: s.name, open, next: nextEdge(s, ms, open ? "close" : "open"), local: `${hh}:${mm}` };
  });
}

/** "2 h 05 min" for a span in ms. */
export function span(ms) {
  const m = Math.max(0, Math.round(ms / 60000));
  const h = Math.floor(m / 60);
  return h ? `${h} h ${String(m % 60).padStart(2, "0")} min` : `${m} min`;
}
