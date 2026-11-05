import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import { makeTestDashboard } from "./data/testDashboard";
import { needsHistoryMessage } from "./quarters";

afterEach(() => {
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

describe("page order", () => {
  test("states what it is, then the checker demo, the pipeline, and the outputs in tabs", async () => {
    const { default: published } = await import("../public/data/dashboard.json");
    render(<App initialDashboard={published as never} />);
    const headings = await screen.findAllByRole("heading", { level: 2 });
    const names = headings.map((item) => item.textContent ?? "");
    const index = (pattern: RegExp) => names.findIndex((name) => pattern.test(name));
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/cannot publish a number/);
    expect(index(/^Change a number the model wrote/)).toBe(0);
    expect(index(/^Six stages/)).toBe(1);
    await waitFor(() => expect(screen.getByRole("tablist", { name: "Outputs" })).toBeTruthy());
  });
});
