import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TickLegend } from "./TickLegend";

describe("TickLegend", () => {
  it("renders the three marks with their meanings", () => {
    render(<TickLegend />);
    const legend = screen.getByRole("region", { name: "Tickmark legend" });
    expect(within(legend).getAllByRole("term")).toHaveLength(3);
    const definitions = within(legend)
      .getAllByRole("definition")
      .map((node) => node.textContent);
    expect(definitions).toEqual([
      "Ties to the filing or computed table",
      "Flagged: does not match",
      "Unsupported: could not be traced",
    ]);
    expect(legend.querySelectorAll("svg")).toHaveLength(3);
  });
});
