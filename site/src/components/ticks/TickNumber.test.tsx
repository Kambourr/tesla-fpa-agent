import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ClaimView } from "../../data/types";
import { TickNumber } from "./TickNumber";

const verifiedClaim: ClaimView = {
  metric: "actual.total_revenue",
  period: "2026-Q3",
  value: 28.05,
  unit: "USD billion",
  sentence_ref: "1",
  status: "verified",
  expected: 28_046_000_000,
  expected_unit: "USD",
  source: "10-Q 0000000000-26-000001",
  source_url: "https://example.com/filing",
};

const flaggedClaim: ClaimView = {
  ...verifiedClaim,
  value: 29.1,
  status: "flagged",
  source_url: null,
};

const unsupportedClaim: ClaimView = {
  metric: "bridge.revenue.volume",
  period: "2026-Q3",
  value: 12.3,
  unit: "USD billion",
  sentence_ref: "2",
  status: "unsupported",
  expected: null,
  expected_unit: null,
  source: null,
  source_url: null,
};

function tooltipText(): string {
  return screen.getByRole("tooltip").textContent ?? "";
}

describe("TickNumber", () => {
  it("renders a verified tick as a link that opens the filing in a new tab", () => {
    render(<TickNumber text="$28.05B" claim={verifiedClaim} />);
    const link = screen.getByRole("link", {
      name: "Verified: ties to 10-Q 0000000000-26-000001, actual total revenue $28.05B",
    });
    expect(link.getAttribute("href")).toBe("https://example.com/filing");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByText("$28.05B")).toBeTruthy();
  });

  it("renders a verified tick as a button when there is no source_url", () => {
    render(<TickNumber text="$28.05B" claim={{ ...verifiedClaim, source_url: null }} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(
      screen.getByRole("button", {
        name: "Verified: ties to 10-Q 0000000000-26-000001, actual total revenue $28.05B",
      }),
    ).toBeTruthy();
  });

  it("names a flagged tick with the formatted expected value and shows it on keyboard focus", async () => {
    const user = userEvent.setup();
    render(<TickNumber text="$29.1B" claim={flaggedClaim} />);
    const trigger = screen.getByRole("button", { name: "Flagged: the filing shows $28.05B" });
    expect(screen.queryByRole("tooltip")).toBeNull();

    await user.tab();
    expect(document.activeElement).toBe(trigger);
    expect(tooltipText()).toContain("$28.05B");
    expect(tooltipText()).toContain("Actual total revenue");
    expect(tooltipText()).toContain("Q3 2026");
    expect(trigger.getAttribute("aria-describedby")).toBe(screen.getByRole("tooltip").id);
  });

  it("marks the number of a flagged tick with an amber dotted underline class", () => {
    const { container } = render(<TickNumber text="$29.1B" claim={flaggedClaim} />);
    expect(container.querySelector(".tick-text.is-flagged")?.textContent).toBe("$29.1B");
  });

  it("names an unsupported tick and shows its tooltip on hover", async () => {
    const user = userEvent.setup();
    render(<TickNumber text="$12.3B" claim={unsupportedClaim} />);
    const trigger = screen.getByRole("button", {
      name: "Unsupported: this figure could not be traced to the data",
    });
    await user.hover(trigger);
    expect(tooltipText()).toContain("Could not be traced to the data");
    await user.unhover(trigger);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("closes the tooltip on Escape while focused", async () => {
    const user = userEvent.setup();
    render(<TickNumber text="$28.05B" claim={verifiedClaim} />);
    await user.tab();
    expect(screen.getByRole("tooltip")).toBeTruthy();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});
