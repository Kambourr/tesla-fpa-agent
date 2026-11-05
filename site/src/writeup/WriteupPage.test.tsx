import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import published from "../../public/data/dashboard.json";
import type { Dashboard } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import { WriteupPage, writeupFacts } from "./WriteupPage";

const live = published as unknown as Dashboard;

describe("WriteupPage", () => {
  it("states counts from the published file, not from copy", () => {
    const facts = writeupFacts(live);
    render(<WriteupPage dashboard={live} />);
    const result = screen.getByText(/On the latest run, the checker tested/);
    expect(result.textContent).toContain(`${facts.totals.total.toLocaleString("en-US")} figures`);
    expect(screen.getByText(facts.revenueError as string)).toBeTruthy();
  });

  it("has one h1, its sections, and links back to the dashboard", () => {
    render(<WriteupPage dashboard={live} />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const titles = screen.getAllByRole("heading", { level: 2 }).map((item) => item.textContent);
    expect(titles).toContain("What the checker catches");
    expect(titles).toContain("Limits");
    for (const link of screen.getAllByRole("link", { name: "Open the dashboard" })) {
      expect(link.getAttribute("href")).toBe("./");
    }
  });

  it("falls back to plain text when nothing is recorded", () => {
    const empty = { ...makeTestDashboard(), last_full_run: null } as Partial<Dashboard>;
    delete empty.sources;
    render(<WriteupPage dashboard={empty as Dashboard} />);
    expect(screen.getByText(/A full run takes a few minutes/)).toBeTruthy();
    expect(screen.getByText(/Tesla's 10-Q and 10-K filings from SEC EDGAR/)).toBeTruthy();
  });
});
