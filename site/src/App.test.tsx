import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { App } from "./App";
import { needsHistoryMessage } from "./quarters";

describe("quarter picker", () => {
  test("selects the latest quarter and shows the history message for an earlier one", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("button", { name: "Quarter Q3 2026" })).toBeTruthy();
    expect(screen.queryByText(needsHistoryMessage)).toBeNull();
    expect(screen.getByText(/Q3 2026 is selected/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Quarter Q3 2026" }));
    await user.keyboard("{ArrowDown}{Enter}");

    expect(screen.getByRole("button", { name: "Quarter Q4 2025" })).toBeTruthy();
    expect(screen.getByText(needsHistoryMessage)).toBeTruthy();
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});
