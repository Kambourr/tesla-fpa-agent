import { describe, expect, it } from "vitest";
import type { Drivers, Scenario, ScenarioFlex } from "../data/types";
import {
  isFavorable,
  percentOfFraction,
  recomputeScenario,
  varianceOf,
  variancePercentOf,
} from "./scenarioMath";

/** The flexes the published dashboard carries (config/forecast.json). */
const FLEX: ScenarioFlex = {
  deliveries_pct: { bull: 10, base: 0, bear: -10 },
  automotive_asp_pct: { bull: 5, base: 0, bear: -5 },
  gross_margin_bp: { bull: 100, base: 0, bear: -100 },
};

/*
 * Expected values below come from agent/scenarios.py `_flex`, run with
 * `uv run python` on the driver sets shown. They are invented numbers, not
 * published ones. Strings keep the Decimal text exactly.
 */

const MID: Drivers = {
  deliveries: 500000.1234,
  automotive_asp: 40000.5555,
  gross_margin: 0.185,
  automotive_regulatory_credits: 100000000.1111,
  automotive_leasing: 300000000.0001,
  energy_generation_and_storage: 2000000000.5005,
  services_and_other: 4000000000.9999,
  operating_expenses: 4500000000.1234,
};

const MID_PYTHON: Record<Scenario, Record<string, string | null>> = {
  bear: {
    deliveries: "450000.1111",
    automotive_asp: "38000.5277",
    automotive_sales: "17100241696.5886",
    total_revenue: "23500241698.2002",
    gross_margin: "0.1750",
    gross_profit: "4112542297.1850",
    operating_income: "-387457702.9384",
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
  base: {
    deliveries: "500000.1234",
    automotive_asp: "40000.5555",
    automotive_sales: "20000282686.0685",
    total_revenue: "26400282687.6801",
    gross_margin: "0.1850",
    gross_profit: "4884052297.2208",
    operating_income: "384052297.0974",
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
  bull: {
    deliveries: "550000.1357",
    automotive_asp: "42000.5833",
    automotive_sales: "23100326502.4092",
    total_revenue: "29500326504.0208",
    gross_margin: "0.1950",
    gross_profit: "5752563668.2841",
    operating_income: "1252563668.1607",
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
};

const SMALL: Drivers = {
  deliveries: 12345.6789,
  automotive_asp: 1234.5678,
  gross_margin: 0.0512,
  automotive_regulatory_credits: 0,
  automotive_leasing: 0.5,
  energy_generation_and_storage: 1.25,
  services_and_other: 2.75,
  operating_expenses: 3.5,
};

const SMALL_PYTHON: Record<Scenario, Record<string, string | null>> = {
  bear: {
    deliveries: "11111.1110",
    automotive_asp: "1172.8394",
    automotive_sales: "13031548.8814",
    total_revenue: "13031553.3814",
    gross_margin: "0.0412",
    gross_profit: "536899.9993",
    operating_income: "536896.4993",
    automotive_regulatory_credits: "0.0000",
    automotive_leasing: "0.5000",
    energy_generation_and_storage: "1.2500",
    services_and_other: "2.7500",
    operating_expenses: "3.5000",
  },
  base: {
    deliveries: "12345.6789",
    automotive_asp: "1234.5678",
    automotive_sales: "15241577.6391",
    total_revenue: "15241582.1391",
    gross_margin: "0.0512",
    gross_profit: "780369.0055",
    operating_income: "780365.5055",
    automotive_regulatory_credits: "0.0000",
    automotive_leasing: "0.5000",
    energy_generation_and_storage: "1.2500",
    services_and_other: "2.7500",
    operating_expenses: "3.5000",
  },
  bull: {
    deliveries: "13580.2468",
    automotive_asp: "1296.2962",
    automotive_sales: "17604022.1731",
    total_revenue: "17604026.6731",
    gross_margin: "0.0612",
    gross_profit: "1077366.4324",
    operating_income: "1077362.9324",
    automotive_regulatory_credits: "0.0000",
    automotive_leasing: "0.5000",
    energy_generation_and_storage: "1.2500",
    services_and_other: "2.7500",
    operating_expenses: "3.5000",
  },
};

/* Half-way cases: bull sales is 0.17325 and bear sales is 0.12825. Half to even gives 0.1732 and 0.1282. */
const TIES: Drivers = {
  deliveries: 1.5,
  automotive_asp: 0.1,
  gross_margin: 0.3,
  automotive_regulatory_credits: 0.0001,
  automotive_leasing: 0,
  energy_generation_and_storage: 0,
  services_and_other: 0,
  operating_expenses: 0,
};

const TIES_PYTHON: Record<Scenario, Record<string, string | null>> = {
  bear: {
    deliveries: "1.3500",
    automotive_asp: "0.0950",
    automotive_sales: "0.1282",
    total_revenue: "0.1284",
    gross_margin: "0.2900",
    gross_profit: "0.0372",
    operating_income: "0.0372",
    automotive_regulatory_credits: "0.0001",
    automotive_leasing: "0.0000",
    energy_generation_and_storage: "0.0000",
    services_and_other: "0.0000",
    operating_expenses: "0.0000",
  },
  base: {
    deliveries: "1.5000",
    automotive_asp: "0.1000",
    automotive_sales: "0.1500",
    total_revenue: "0.1501",
    gross_margin: "0.3000",
    gross_profit: "0.0450",
    operating_income: "0.0450",
    automotive_regulatory_credits: "0.0001",
    automotive_leasing: "0.0000",
    energy_generation_and_storage: "0.0000",
    services_and_other: "0.0000",
    operating_expenses: "0.0000",
  },
  bull: {
    deliveries: "1.6500",
    automotive_asp: "0.1050",
    automotive_sales: "0.1732",
    total_revenue: "0.1734",
    gross_margin: "0.3100",
    gross_profit: "0.0537",
    operating_income: "0.0537",
    automotive_regulatory_credits: "0.0001",
    automotive_leasing: "0.0000",
    energy_generation_and_storage: "0.0000",
    services_and_other: "0.0000",
    operating_expenses: "0.0000",
  },
};

const NULL_ASP: Drivers = { ...MID, automotive_asp: null };

const NULL_ASP_PYTHON: Record<Scenario, Record<string, string | null>> = {
  bear: {
    deliveries: "450000.1111",
    automotive_asp: null,
    automotive_sales: null,
    total_revenue: null,
    gross_margin: "0.1750",
    gross_profit: null,
    operating_income: null,
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
  base: {
    deliveries: "500000.1234",
    automotive_asp: null,
    automotive_sales: null,
    total_revenue: null,
    gross_margin: "0.1850",
    gross_profit: null,
    operating_income: null,
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
  bull: {
    deliveries: "550000.1357",
    automotive_asp: null,
    automotive_sales: null,
    total_revenue: null,
    gross_margin: "0.1950",
    gross_profit: null,
    operating_income: null,
    automotive_regulatory_credits: "100000000.1111",
    automotive_leasing: "300000000.0001",
    energy_generation_and_storage: "2000000000.5005",
    services_and_other: "4000000000.9999",
    operating_expenses: "4500000000.1234",
  },
};

function expectMatchesPython(
  drivers: Drivers,
  python: Record<Scenario, Record<string, string | null>>,
) {
  for (const scenario of ["bear", "base", "bull"] as const) {
    const recomputed = recomputeScenario(drivers, FLEX, scenario);
    for (const [key, text] of Object.entries(python[scenario])) {
      expect(recomputed[key], `${scenario} ${key}`).toBe(text === null ? null : Number(text));
    }
  }
}

describe("recomputeScenario parity with agent/scenarios.py", () => {
  it("matches the Python output exactly on a mid-size driver set", () => {
    expectMatchesPython(MID, MID_PYTHON);
  });

  it("matches the Python output exactly on a small driver set", () => {
    expectMatchesPython(SMALL, SMALL_PYTHON);
  });

  it("rounds half to even as Python's Decimal quantize does", () => {
    expectMatchesPython(TIES, TIES_PYTHON);
  });

  it("matches the Python output when automotive ASP is null", () => {
    expectMatchesPython(NULL_ASP, NULL_ASP_PYTHON);
  });
});

describe("recomputeScenario null propagation", () => {
  it("nulls the lines that depend on a null driver and keeps the rest", () => {
    const bull = recomputeScenario(NULL_ASP, FLEX, "bull");
    expect(bull.automotive_asp).toBeNull();
    expect(bull.automotive_sales).toBeNull();
    expect(bull.total_revenue).toBeNull();
    expect(bull.gross_profit).toBeNull();
    expect(bull.operating_income).toBeNull();
    expect(bull.deliveries).not.toBeNull();
    expect(bull.gross_margin).not.toBeNull();
    expect(bull.operating_expenses).not.toBeNull();
  });

  it("nulls profit when the margin is null but keeps revenue", () => {
    const drivers = { ...MID, gross_margin: null };
    const base = recomputeScenario(drivers, FLEX, "base");
    expect(base.total_revenue).toBe(26400282687.6801);
    expect(base.gross_margin).toBeNull();
    expect(base.gross_profit).toBeNull();
    expect(base.operating_income).toBeNull();
  });

  it("nulls sales and everything after when deliveries are null", () => {
    const drivers = { ...MID, deliveries: null };
    const bear = recomputeScenario(drivers, FLEX, "bear");
    expect(bear.deliveries).toBeNull();
    expect(bear.automotive_sales).toBeNull();
    expect(bear.total_revenue).toBeNull();
    expect(bear.operating_income).toBeNull();
    expect(bear.automotive_asp).not.toBeNull();
  });
});

describe("recomputed values against the published scenarios", () => {
  it("are within 0.0001 of the published bull, base and bear values", () => {
    for (const scenario of ["bear", "base", "bull"] as const) {
      const recomputed = recomputeScenario(MID, FLEX, scenario);
      for (const [key, text] of Object.entries(MID_PYTHON[scenario])) {
        const published = text === null ? null : Number(text);
        const value = recomputed[key];
        if (published === null || value === null) {
          expect(value, `${scenario} ${key}`).toBe(published);
        } else {
          expect(Math.abs(value - published), `${scenario} ${key}`).toBeLessThanOrEqual(0.0001);
        }
      }
    }
  });
});

describe("variance helpers", () => {
  it("computes a percent line in percent units from a fraction", () => {
    expect(percentOfFraction(0.1867)).toBe(18.67);
    expect(percentOfFraction(null)).toBeNull();
  });

  it("computes the variance and the variance percent as publish does", () => {
    const variance = varianceOf(480000, 500000.1234);
    expect(variance).toBe(-20000.1234);
    expect(variancePercentOf(variance, 500000.1234)).toBe(-4);
  });

  it("returns null for a variance percent when the forecast is zero", () => {
    expect(variancePercentOf(5, 0)).toBeNull();
  });

  it("marks cost lines favorable when below forecast and other lines when above", () => {
    expect(isFavorable("operating_expenses", -100)).toBe(true);
    expect(isFavorable("operating_expenses", 100)).toBe(false);
    expect(isFavorable("total_revenue", 100)).toBe(true);
    expect(isFavorable("total_revenue", -100)).toBe(false);
    expect(isFavorable("total_revenue", 0)).toBeNull();
    expect(isFavorable("total_revenue", null)).toBeNull();
  });
});
