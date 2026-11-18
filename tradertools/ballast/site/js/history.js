// Ballast: reading the account's closed deals in full. The platform answers one window at a time and may say
// "hasMore"; a window is then split in two until every part fits, or the read is reported incomplete. Pure apart
// from the `fetchWindow` function it is given; tested by `node --test`.

const WEEK = 7 * 86400000;

/**
 * fetchWindow(fromMs, toMs) -> Promise<{ deals: [...], hasMore: bool }>
 * returns Promise<{ deals (each once, by dealId), complete (false if any window failed or still had more) }>
 */
export async function readDeals(fetchWindow, fromMs, toMs, { window = WEEK, depth = 6 } = {}) {
  const seen = new Map();
  let complete = true;
  async function one(a, b, d) {
    let r;
    try {
      r = await fetchWindow(a, b);
    } catch {
      complete = false;
      return;
    }
    if (r && r.hasMore && d > 0 && b - a > 1000) {
      const mid = Math.floor((a + b) / 2);
      await one(a, mid, d - 1);
      await one(mid + 1, b, d - 1);
      return;
    }
    if (!r || r.hasMore) complete = false;
    for (const x of (r && r.deals) || []) seen.set(x.dealId, x);
  }
  for (let b = toMs; b > fromMs; b -= window) await one(Math.max(fromMs, b - window), b, depth);
  return { deals: [...seen.values()], complete };
}
