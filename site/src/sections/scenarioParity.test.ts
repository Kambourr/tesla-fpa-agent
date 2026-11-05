/**
 * M5-T9: the browser scenario math matches the Python model on a shared fixture.
 *
 * The fixture is written by scripts/make_scenario_fixture.py, which runs
 * agent/scenarios.py `_flex` on the published four-decimal drivers. This test
 * feeds the same drivers to recomputeScenario and compares each bull and bear
 * metric as a four-decimal string.
 *
 * recomputeScenario returns numbers that are already rounded half to even to
 * four places, so value.toFixed(4) is only formatting. That holds while the
 * spacing of doubles is well under 0.00005, which the guard test below checks.
 */
import { describe, expect, it } from "vitest";
import fixtureJson from "../data/scenarioParity.fixture.json";
import type { Drivers, Scenario, ScenarioFlex } from "../data/types";
import { recomputeScenario } from "./scenarioMath";

type Text = string | null;

interface ParityCase {
  quarter: string;
  drivers: Record<keyof Drivers, Text>;
  expected: Record<"bull" | "bear", Record<string, Text>>;
}

interface ParityFixture {
  generated_by: string;
  note: string;
  flex: ScenarioFlex;
  cases: ParityCase[];
}

const fixture: ParityFixture = fixtureJson;

const SCENARIOS: readonly ("bull" | "bear")[] = ["bull", "bear"];
const METRICS = [
  "deliveries",
  "automotive_asp",
  "automotive_sales",
  "total_revenue",
  "gross_margin",
  "gross_profit",
  "operating_income",
] as const;
const DRIVER_KEYS = Object.keys(fixture.cases[0].drivers) as (keyof Drivers)[];

/** Doubles this far below 1e11 are spaced under 0.00002, so toFixed(4) returns the four-place value. */
const EXACT_FORMAT_LIMIT = 1e11;

function fourPlaces(value: number | null | undefined): Text {
  return value === null || value === undefined ? null : value.toFixed(4);
}

function toDrivers(text: Record<keyof Drivers, Text>): Drivers {
  const drivers = {} as Record<keyof Drivers, number | null>;
  for (const key of DRIVER_KEYS) {
    const value = text[key];
    drivers[key] = value === null ? null : Number(value);
  }
  return drivers as Drivers;
}

describe("scenario parity fixture", () => {
  it("is the Python fixture: four cases, bull and bear for every metric", () => {
    expect(fixture.generated_by).toBe("scripts/make_scenario_fixture.py");
    expect(fixture.cases).toHaveLength(4);
    for (const testCase of fixture.cases) {
      for (const scenario of SCENARIOS) {
        expect(Object.keys(testCase.expected[scenario]).sort()).toEqual([...METRICS].sort());
      }
    }
  });

  it("keeps every expected value where toFixed(4) is exact", () => {
    for (const testCase of fixture.cases) {
      for (const scenario of SCENARIOS) {
        for (const [metric, text] of Object.entries(testCase.expected[scenario])) {
          if (text !== null) {
            expect(Math.abs(Number(text)), `${testCase.quarter} ${scenario} ${metric}`).toBeLessThan(
              EXACT_FORMAT_LIMIT,
            );
          }
        }
      }
    }
  });

  for (const testCase of fixture.cases) {
    for (const scenario of SCENARIOS) {
      it(`${testCase.quarter} ${scenario} matches Python to four decimals`, () => {
        const recomputed = recomputeScenario(toDrivers(testCase.drivers), fixture.flex, scenario);
        for (const metric of METRICS) {
          expect(fourPlaces(recomputed[metric]), `${testCase.quarter} ${scenario} ${metric}`).toBe(
            testCase.expected[scenario][metric],
          );
        }
      });
    }

    it(`${testCase.quarter} base passes the published drivers through unchanged`, () => {
      const base: Scenario = "base";
      const recomputed = recomputeScenario(toDrivers(testCase.drivers), fixture.flex, base);
      expect(fourPlaces(recomputed.deliveries)).toBe(testCase.drivers.deliveries);
      expect(fourPlaces(recomputed.automotive_asp)).toBe(testCase.drivers.automotive_asp);
      expect(fourPlaces(recomputed.gross_margin)).toBe(testCase.drivers.gross_margin);
    });
  }
});
