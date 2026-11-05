import { describe, expect, it } from "vitest";
import { formatClaimValue, formatExpected, metricLabel, periodLabel, unitKind } from "./tickFormat";

describe("metricLabel", () => {
  it.each([
    ["actual.total_revenue", "Actual total revenue"],
    ["variance_pct.total_revenue", "Variance in total revenue (%)"],
    ["bridge.revenue.volume", "Revenue bridge: volume"],
    ["backtest.total_revenue.abs_pct_error", "Backtest error: total revenue"],
    ["backtest.total_revenue.average_abs_pct_error", "Backtest average error: total revenue"],
    ["variance.total_revenue", "Variance in total revenue"],
    ["forecast.base.total_revenue", "Base forecast: total revenue"],
    ["bridge.gross_profit.price_mix", "Gross profit bridge: price mix"],
    ["something_else", "Something else"],
  ])("labels %s as %s", (metric, label) => {
    expect(metricLabel(metric)).toBe(label);
  });
});

describe("formatExpected", () => {
  it("formats USD in billions and millions", () => {
    expect(formatExpected(28_046_000_000, "USD")).toBe("$28.05B");
    expect(formatExpected(718_000_000, "USD")).toBe("$718M");
    expect(formatExpected(-7_480_000_000, "USD")).toBe("−$7.48B");
  });

  it("formats percent, units and USD per unit", () => {
    expect(formatExpected(19.6, "percent")).toBe("19.6%");
    expect(formatExpected(486_532, "units")).toBe("486,532");
    expect(formatExpected(41_302, "USD_per_unit")).toBe("$41,302");
  });

  it("rolls 999.6M up to billions instead of printing $1,000M", () => {
    expect(formatExpected(999_600_000, "USD")).toBe("$1.00B");
  });
});

describe("formatClaimValue", () => {
  it("writes the claim as it reads in prose", () => {
    expect(formatClaimValue(28.05, "USD billion")).toBe("$28.05B");
    expect(formatClaimValue(-7.48, "USD billion")).toBe("−$7.48B");
    expect(formatClaimValue(-21.1, "percent")).toBe("−21.1%");
    expect(formatClaimValue(486_532, "units")).toBe("486,532");
    expect(formatClaimValue(718, "USD million")).toBe("$718M");
  });
});

describe("unitKind", () => {
  it("maps fact units and claim unit words", () => {
    expect(unitKind("USD")).toBe("usd");
    expect(unitKind("USD billion")).toBe("usd");
    expect(unitKind("USD_per_unit")).toBe("usd_per_unit");
    expect(unitKind("USD per vehicle")).toBe("usd_per_unit");
    expect(unitKind("percent")).toBe("percent");
    expect(unitKind("units")).toBe("units");
  });
});

describe("periodLabel", () => {
  it("reads quarter ids and the 12-quarter period", () => {
    expect(periodLabel("2026-Q3")).toBe("Q3 2026");
    expect(periodLabel("12Q")).toBe("Last 12 quarters");
    expect(periodLabel("whenever")).toBeNull();
  });
});
