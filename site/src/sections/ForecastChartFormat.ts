const MINUS = "−";

/** Full money label for a value in USD, for example "$28.05B". */
export function formatBillions(value: number): string {
  const sign = value < 0 ? MINUS : "";
  return `${sign}$${(Math.abs(value) / 1e9).toFixed(2)}B`;
}

/** Axis tick label in billions, for example "$20B". */
export function formatAxisBillions(value: number, decimals: number): string {
  const sign = value < 0 ? MINUS : "";
  return `${sign}$${(Math.abs(value) / 1e9).toFixed(decimals)}B`;
}

/** "Q4 2023" becomes "Q4 23". Any other label is returned unchanged. */
export function shortQuarterLabel(label: string): string {
  const match = /^(Q[1-4])\s+(\d{4})$/.exec(label.trim());
  return match ? `${match[1]} ${match[2].slice(2)}` : label;
}
