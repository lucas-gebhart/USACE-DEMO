const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const num0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const num1 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

export function money(v: number | null | undefined): string {
  return v == null ? "—" : usd0.format(v);
}

export function moneyCompact(v: number | null | undefined): string {
  if (v == null) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e9) return `$${num1.format(v / 1e9)}B`;
  if (abs >= 1e6) return `$${num1.format(v / 1e6)}M`;
  if (abs >= 1e3) return `$${num0.format(v / 1e3)}K`;
  return usd0.format(v);
}

export function int(v: number | null | undefined): string {
  return v == null ? "—" : num0.format(v);
}

export function dec1(v: number | null | undefined): string {
  return v == null ? "—" : num1.format(v);
}

export function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${num1.format(v * 100)}%`;
}

export function day(v: string | null | undefined): string {
  return v ? v.slice(0, 10) : "—";
}

export function when(v: string | null | undefined): string {
  if (!v) return "—";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export const BUSINESS_LINES: Record<string, string> = {
  NAV: "Navigation",
  FRM: "Flood Risk Mgmt",
  HYD: "Hydropower",
  REC: "Recreation",
  ENS: "Environment",
  WTR: "Water Supply",
};
