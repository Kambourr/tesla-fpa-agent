import { describe, expect, it } from "vitest";
import parity from "./parity.json";
import { canonicalUnit, checkFigure, parseDecimal } from "./verifier";

interface ParityCase {
  expected: number;
  expected_unit: string;
  value: number;
  value_text: string;
  unit: string;
  status: string;
}

describe("verifier parity with agent/verifier.py", () => {
  it.each(parity as ParityCase[])(
    "$value_text $unit vs $expected $expected_unit is $status",
    (item) => {
      expect(checkFigure(item.value_text, item.unit, item.expected, item.expected_unit).status).toBe(
        item.status,
      );
    },
  );
});

describe("verifier details", () => {
  it("parses decimals exactly, including exponents", () => {
    expect(parseDecimal("28.05")).toEqual({ n: 2805n, s: 2 });
    expect(parseDecimal("-1.5e3")).toEqual({ n: -1500n, s: 0 });
    expect(parseDecimal("abc")).toBeNull();
    expect(parseDecimal(".")).toBeNull();
  });

  it("normalises unit spelling like the Python verifier", () => {
    expect(canonicalUnit("  $ Billion ")).toBe("usd billion");
  });

  it("explains a wrong sign and an incompatible unit", () => {
    expect(checkFigure("7.48", "USD billion", -7481465181.4722, "USD").reason).toMatch(/sign/);
    expect(checkFigure("19.6", "USD", 19.6, "percent").reason).toMatch(/unit/);
  });
});
