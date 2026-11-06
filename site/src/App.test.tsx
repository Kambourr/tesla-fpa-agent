import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import { makeTestDashboard } from "./data/testDashboard";
import { needsHistoryMessage } from "./quarters";
import { OVERVIEW_HEADLINE } from "./shell/Overview";

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("quarter picker", () => {
  test("selects the latest quarter and shows the history message for an earlier one", async () => {
    const user = userEvent.setup();
    render(<App initialDashboard={makeTestDashboard()} />);

    expect(screen.getByRole("button", { name: "Quarter Q3 2026" })).toBeTruthy();
    expect(screen.queryByText(needsHistoryMessage)).toBeNull();

    await user.click(screen.getByRole("button", { name: "Quarter Q3 2026" }));
    await user.keyboard("{ArrowUp}{Enter}");

    expect(screen.getByRole("button", { name: "Quarter Q4 2025" })).toBeTruthy();
    expect(screen.getByText(needsHistoryMessage)).toBeTruthy();
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});

describe("loading dashboard.json", () => {
  test("fetches the published file and shows the latest quarter", async () => {
    const fetchMock = vi.fn(async (_url: string) => new Response(JSON.stringify(makeTestDashboard())));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    expect(screen.getByText("Loading the published quarters.")).toBeTruthy();
    await waitFor(() => expect(screen.getByRole("button", { name: "Quarter Q3 2026" })).toBeTruthy());
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/data\/dashboard\.json$/);
  });

  test("explains what is missing when the file does not load", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("missing", { status: 404 })));
    render(<App />);
    await waitFor(() => expect(screen.getByText("The published data did not load")).toBeTruthy());
  });
});

describe("overview shell", () => {
  test("opens on the quarter, not the verifier, with labeled figures and the waterfall", async () => {
    const { default: published } = await import("../public/data/dashboard.json");
    render(<App initialDashboard={published as never} />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(OVERVIEW_HEADLINE);
    const kpis = document.querySelector(".kpis");
    expect(kpis?.textContent).toMatch(/Actual revenue/);
    expect(kpis?.textContent).toMatch(/Forecast/);
    expect(kpis?.textContent).toMatch(/Variance/);
    expect(document.querySelector(".kpi-sub")?.textContent).toMatch(/unfavorable/);
    expect(screen.getByRole("img", { name: /Revenue bridge/ })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /Change a number the model wrote/ })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Six stages/ })).toBeNull();
    expect(screen.queryByText(/cannot publish a number/)).toBeNull();
  });

  test("sidebar destinations change the hash and the view", async () => {
    const user = userEvent.setup();
    const { default: published } = await import("../public/data/dashboard.json");
    render(<App initialDashboard={published as never} />);

    await user.click(screen.getByRole("link", { name: "Analyst memo" }));
    expect(window.location.hash).toBe("#/memo");
    expect(screen.getByRole("heading", { name: "Analyst memo" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: OVERVIEW_HEADLINE })).toBeNull();

    await user.click(screen.getByRole("link", { name: "How it works" }));
    expect(window.location.hash).toBe("#/method");
    expect(screen.getByRole("heading", { name: /How it works/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Change a number the model wrote/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: "How it was built" })).toBeTruthy();
  });

  test("an old method anchor opens How it works", async () => {
    window.location.hash = "#method-title";
    const { default: published } = await import("../public/data/dashboard.json");
    render(<App initialDashboard={published as never} />);
    expect(screen.getByRole("link", { name: "How it works" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("heading", { name: /How it works/ })).toBeTruthy();
  });
});
