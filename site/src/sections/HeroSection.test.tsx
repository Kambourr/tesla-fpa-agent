import { act, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { BridgeBar, PnlLine, QuarterView } from "../data/types";
import { HeroSection, bridgeDomain } from "./HeroSection";
import { formatSignedPercent, formatSignedUsd, formatUsd } from "./HeroSectionFormat";
import { makeTestDashboard } from "../data/testDashboard";

// Every number here is invented. The page itself reads only dashboard.json.
const REVENUE_BARS: BridgeBar[] = [
  { driver: "volume", label: "Volume", value: -400_000_000, favorable: false },
  { driver: "price_mix", label: "Price and mix", value: 50_000_000, favorable: true },
  { driver: "automotive_regulatory_credits", label: "Regulatory credits", value: -10_000_000, favorable: false },
  { driver: "automotive_leasing", label: "Leasing", value: 20_000_000, favorable: true },
  { driver: "energy_generation_and_storage", label: "Energy generation and storage", value: -120_000_000, favorable: false },
  { driver: "services_and_other", label: "Services and other", value: 60_000_000, favorable: true },
];

function makeQuarter(overrides: Partial<QuarterView> = {}): QuarterView {
  const totalRevenue: PnlLine = {
    metric: "total_revenue",
    label: "Total revenue",
    unit: "USD",
    forecast: 12_000_000_000,
    actual: 10_500_000_000,
    variance: -1_500_000_000,
    variance_pct: -12.5,
    favorable: false,
  };
  return {
    quarter: "2027-Q1",
    label: "Q1 2027",
    kind: "backtest",
    has_forecast: true,
    filing: null,
    lines: [totalRevenue],
    drivers: null,
    scenarios: {},
    bridges: { revenue: REVENUE_BARS, gross_profit: [], operating_income: [], free_cash_flow: [] },
    memo: null,
    ...overrides,
  } as QuarterView;
}

const props = {
  dashboard: makeTestDashboard(),
  onSelectQuarter: vi.fn(),
};

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const originalMatchMedia = window.matchMedia;

function stubReducedMotion(matches: boolean) {
  window.matchMedia = vi.fn((query: string) => ({
    matches: query === REDUCED_MOTION ? matches : false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

beforeEach(() => {
  stubReducedMotion(false);
});

afterEach(() => {
  window.matchMedia = originalMatchMedia;
  vi.useRealTimers();
});

describe("hero revenue bridge", () => {
  test("writes the lede for an invented quarter", () => {
    stubReducedMotion(true);
    render(<HeroSection {...props} quarter={makeQuarter()} />);

    expect(
      screen.getByText("Q1 2027: forecast $12.00B, actual $10.50B, −$1.50B (−12.5%)."),
    ).toBeTruthy();
  });

  test("the chart variant keeps the waterfall and drops the lede and seal", () => {
    stubReducedMotion(true);
    render(<HeroSection {...props} quarter={makeQuarter()} variant="chart" />);
    expect(screen.queryByText(/forecast \$12.00B, actual \$10.50B/)).toBeNull();
    expect(screen.queryByRole("link", { name: "See how the figures are checked" })).toBeNull();
    expect(screen.getByRole("img", { name: /Revenue bridge for Q1 2027/ })).toBeTruthy();
  });

  test("renders one bar per driver plus the forecast and actual totals", () => {
    stubReducedMotion(true);
    const { container } = render(<HeroSection {...props} quarter={makeQuarter()} />);

    expect(container.querySelectorAll('[data-kind="driver"]')).toHaveLength(REVENUE_BARS.length);
    expect(container.querySelectorAll('[data-kind="total"]')).toHaveLength(2);
    expect(container.querySelectorAll("svg rect.hero-bar")).toHaveLength(REVENUE_BARS.length + 2);
    expect(screen.getByRole("img", { name: /Revenue bridge for Q1 2027/ })).toBeTruthy();
  });

  test("labels each driver with its signed value in the chart", () => {
    stubReducedMotion(true);
    const { container } = render(<HeroSection {...props} quarter={makeQuarter()} />);

    const valueTexts = Array.from(container.querySelectorAll("svg text.hero-value")).map((node) =>
      node.textContent?.trim(),
    );
    expect(valueTexts).toContain("▼ −$400M");
    expect(valueTexts).toContain("▲ +$50M");
    expect(valueTexts).toContain("$12.00B");
    expect(valueTexts).toContain("$10.50B");
  });

  test("the hidden table lists every bar with its direction", () => {
    stubReducedMotion(true);
    const { container } = render(<HeroSection {...props} quarter={makeQuarter()} />);

    const table = container.querySelector("table");
    expect(table?.classList.contains("visually-hidden")).toBe(true);
    const rows = within(table as HTMLTableElement).getAllByRole("row");
    // One header row plus eight bars.
    expect(rows).toHaveLength(REVENUE_BARS.length + 3);
    expect(within(table as HTMLTableElement).getAllByText("unfavorable").length).toBe(3);
    expect(within(table as HTMLTableElement).getAllByText("favorable").length).toBe(3);
    expect(within(table as HTMLTableElement).getByText("−$400M")).toBeTruthy();
  });

  test("with reduced motion, sets data-drawn immediately and does not animate", () => {
    stubReducedMotion(true);
    const { container } = render(<HeroSection {...props} quarter={makeQuarter()} />);

    expect(container.querySelector("section")?.getAttribute("data-drawn")).toBe("true");
    expect(container.querySelectorAll(".is-drawing")).toHaveLength(0);
  });

  test("without reduced motion, draws the bars and sets data-drawn after about 1.2 s", () => {
    vi.useFakeTimers();
    const { container } = render(<HeroSection {...props} quarter={makeQuarter()} />);

    const section = container.querySelector("section") as HTMLElement;
    expect(section.hasAttribute("data-drawn")).toBe(false);
    expect(container.querySelectorAll(".is-drawing")).toHaveLength(REVENUE_BARS.length + 2);

    act(() => {
      vi.advanceTimersByTime(1199);
    });
    expect(section.hasAttribute("data-drawn")).toBe(false);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(section.getAttribute("data-drawn")).toBe("true");
    expect(container.querySelectorAll(".is-drawing")).toHaveLength(0);
  });

  test("a quarter switch after the first draw does not replay the animation", () => {
    vi.useFakeTimers();
    const { container, rerender } = render(<HeroSection {...props} quarter={makeQuarter()} />);
    act(() => {
      vi.advanceTimersByTime(1200);
    });

    const fewerBars = makeQuarter({
      quarter: "2027-Q2",
      label: "Q2 2027",
      bridges: {
        revenue: REVENUE_BARS.slice(0, 2),
        gross_profit: [],
        operating_income: [],
        free_cash_flow: [],
      },
    });
    rerender(<HeroSection {...props} quarter={fewerBars} />);

    expect(container.querySelector("section")?.getAttribute("data-drawn")).toBe("true");
    expect(container.querySelectorAll(".is-drawing")).toHaveLength(0);
    expect(container.querySelectorAll('[data-kind="driver"]')).toHaveLength(2);
  });

  test("shows the empty state when the revenue bridge is empty", () => {
    stubReducedMotion(false);
    const { container } = render(
      <HeroSection
        {...props}
        quarter={makeQuarter({
          bridges: { revenue: [], gross_profit: [], operating_income: [], free_cash_flow: [] },
        })}
      />,
    );

    expect(
      screen.getByText(
        "No revenue bridge for this quarter: the forecast or an actual revenue line is missing.",
      ),
    ).toBeTruthy();
    expect(container.querySelector("svg")).toBeNull();
    expect(container.querySelector("section")?.getAttribute("data-drawn")).toBe("true");
  });

  test("shows the empty state when the actual revenue line is missing", () => {
    stubReducedMotion(true);
    render(<HeroSection {...props} quarter={makeQuarter({ lines: [] })} />);

    expect(
      screen.getByText(
        "No revenue bridge for this quarter: the forecast or an actual revenue line is missing.",
      ),
    ).toBeTruthy();
  });
});

describe("hero formatters", () => {
  test("money and percent formats keep the true minus sign and the B or M units", () => {
    expect(formatUsd(28_046_000_000)).toBe("$28.05B");
    expect(formatUsd(718_000_000)).toBe("$718M");
    expect(formatSignedUsd(-7_481_465_181)).toBe("−$7.48B");
    expect(formatSignedUsd(24_000_000)).toBe("+$24M");
    expect(formatSignedPercent(-21.0583)).toBe("−21.1%");
  });
});

describe("bridgeDomain", () => {
  test("starts below the lowest level with a note when the bridge sits far from zero", () => {
    const steps = [
      { start: 0, end: 35.5e9 },
      { start: 35.5e9, end: 29.9e9 },
      { start: 29.9e9, end: 28.0e9 },
      { start: 0, end: 28.0e9 },
    ];
    const domain = bridgeDomain(steps);
    expect(domain.truncated).toBe(true);
    expect(domain.domainMin).toBeGreaterThan(0);
    expect(domain.domainMin).toBeLessThan(28.0e9);
    expect(domain.domainMax).toBeGreaterThan(35.5e9);
  });

  test("keeps zero when the bridge reaches it", () => {
    const steps = [
      { start: 0, end: 100 },
      { start: 100, end: 10 },
      { start: 0, end: 10 },
    ];
    const domain = bridgeDomain(steps);
    expect(domain.truncated).toBe(false);
    expect(domain.domainMin).toBe(0);
  });
});
