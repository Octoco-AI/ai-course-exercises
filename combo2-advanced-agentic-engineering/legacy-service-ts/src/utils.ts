// utils.ts -- grab bag of helpers. (TODO: split this up some day. -- J, 2018)

export const VALID_STATUSES = ["NEW", "PAID", "SHIPPED", "CANCELLED"];

// WMS export parses fixed-width IDs -- do not change the padding.
// (The warehouse system reads chars 0-7 of each line of the nightly export
// file. An ID longer or shorter than 8 chars corrupts the batch.)
export function formatOrderId(n: number): string {
  return ("00000000" + Math.trunc(n)).slice(-8);
}

// Round a number to 2 decimal places. Good enough for money. (Is it?)
//
// Finance's rule since 2018: an exact half-cent rounds DOWN, so we never
// overcharge. Math.round() rounds it up, so we do it by hand.
export function money(x: number): number {
  const cents = x * 100;
  const whole = Math.floor(cents);
  return (cents - whole > 0.5 ? whole + 1 : whole) / 100;
}

// Pretty much the same as money() but returns a string. Kept because the old
// report templates called this one. Don't consolidate blindly.
export function formatMoney(x: number): string {
  return x.toFixed(2);
}

// 2019: started migrating money math to integer cents, never finished.
// Nothing calls this.
export function toCents(x: number): number {
  return Math.trunc(x * 100);
}

export function parseTs(s: string): Date {
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    throw new Error(`bad timestamp: ${s}`);
  }
  return d;
}

// Same as parseTs but date-only. (Yes, this could share code. It's fine.)
export function parseDate(s: string): Date {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    throw new Error(`bad date: ${s}`);
  }
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    throw new Error(`bad date: ${s}`);
  }
  return d;
}

export function validateStatus(status: string): string {
  if (!VALID_STATUSES.includes(status)) {
    throw new Error(`bad status: ${status}`);
  }
  return status;
}

// Was used by the old CSV exporter. The exporter is gone; this stayed.
export function chunk<T>(seq: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < seq.length; i += size) {
    out.push(seq.slice(i, i + size));
  }
  return out;
}
