import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Dashboard, RunMetadata } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import {
  formatCost,
  formatRunDate,
  formatRunTime,
  formatStageSeconds,
} from "./AgentRunFormat";
import { AgentRunSection } from "./AgentRunSection";

const recorded: RunMetadata = {
  started_at: "2026-11-05T14:30:00+00:00",
  duration_seconds: 125,
  stages: [
    { name: "publish", seconds: 0.8 },
    { name: "ingest", seconds: 4 },
    { name: "explain", seconds: 38 },
    { name: "load", seconds: 1.2 },
    { name: "verify", seconds: 2 },
    { name: "forecast", seconds: 12 },
  ],
  model: "invented-model-x",
  input_tokens: 1000,
  output_tokens: 500,
  estimated_cost_usd: 0.06,
  data_as_of: "2026-09-30",
};

const unrecorded: RunMetadata = {
  started_at: null,
  duration_seconds: null,
  stages: [],
  model: null,
  input_tokens: null,
  output_tokens: null,
  estimated_cost_usd: null,
  data_as_of: null,
};

function renderWith(run: RunMetadata) {
  const dashboard: Dashboard = { ...makeTestDashboard(), run };
  const quarter = dashboard.quarters[0];
  return render(
    <AgentRunSection dashboard={dashboard} quarter={quarter} onSelectQuarter={() => undefined} />,
  );
}

function stageItems() {
  return screen.getAllByRole("listitem");
}

describe("stage sequence", () => {
  test("stages render in the fixed order with their durations", () => {
    renderWith(recorded);
    const items = stageItems();

    expect(items.map((item) => item.querySelector(".agent-run-name")?.textContent)).toEqual([
      "Ingest",
      "Load",
      "Forecast",
      "Explain",
      "Verify",
      "Publish",
    ]);
    expect(items.map((item) => item.querySelector(".agent-run-seconds")?.textContent)).toEqual([
      "4 s",
      "1.2 s",
      "12 s",
      "38 s",
      "2 s",
      "0.8 s",
    ]);
  });

  test("the rule above the section comes first", () => {
    const { container } = renderWith(recorded);
    const first = container.firstElementChild;
    expect(first?.tagName).toBe("HR");
    expect(first?.classList.contains("ledger")).toBe(true);
    expect(screen.getByRole("heading", { level: 2, name: "How the agent ran" })).toBeTruthy();
  });

  test("a null duration shows a dash and visually hidden not recorded text", () => {
    renderWith({
      ...recorded,
      stages: [
        { name: "ingest", seconds: null },
        { name: "load", seconds: 1.2 },
      ],
    });
    const [ingest, load] = stageItems();

    expect(within(ingest).getByText("—")).toBeTruthy();
    expect(within(ingest).getByText("not recorded").className).toContain("visually-hidden");
    expect(within(load).queryByText("not recorded")).toBeNull();
    // Stages missing from the array count as not recorded too.
    expect(screen.getAllByText("not recorded")).toHaveLength(5);
  });

  test("Explain is marked Model and the other stages Code", () => {
    renderWith(recorded);
    const items = stageItems();
    const kinds = items.map((item) => item.querySelector(".agent-run-kind")?.textContent);

    expect(kinds).toEqual(["Code", "Code", "Code", "Model", "Code", "Code"]);
    expect(within(items[3]).getByText("Model")).toBeTruthy();
  });
});

describe("run statistics", () => {
  test("shows date, time, cost, model and data as of", () => {
    renderWith(recorded);
    const scope = within(document.querySelector("dl") as HTMLElement);

    expect(scope.getByText("Last run").nextElementSibling?.textContent).toBe("Nov 5, 2026");
    expect(scope.getByText("Total run time").nextElementSibling?.textContent).toBe("2 min 5 s");
    expect(scope.getByText("AI cost").nextElementSibling?.textContent).toBe("$0.06");
    expect(scope.getByText("Model").nextElementSibling?.textContent).toBe("invented-model-x");
    expect(scope.getByText("Data as of").nextElementSibling?.textContent).toBe("Sep 30, 2026");
  });

  test("missing values show Not recorded yet while the rest still render", () => {
    renderWith({ ...recorded, estimated_cost_usd: null, data_as_of: null });
    const scope = within(document.querySelector("dl") as HTMLElement);

    expect(scope.getByText("AI cost").nextElementSibling?.textContent).toBe("Not recorded yet");
    expect(scope.getByText("Data as of").nextElementSibling?.textContent).toBe("Not recorded yet");
    expect(scope.getByText("Model").nextElementSibling?.textContent).toBe("invented-model-x");
  });

  test("all-null headline values show one sentence instead of the stat list", () => {
    const { container } = renderWith(unrecorded);

    expect(
      screen.getByText("The run details appear after the next full pipeline run."),
    ).toBeTruthy();
    expect(container.querySelector("dl")).toBeNull();
    // The six stages still render, each with a dash.
    expect(stageItems()).toHaveLength(6);
    expect(screen.getAllByText("—")).toHaveLength(6);
  });

  test("no sentence when at least one headline value is recorded", () => {
    renderWith({ ...unrecorded, model: "invented-model-x" });
    expect(screen.queryByText("The run details appear after the next full pipeline run.")).toBeNull();
    expect(document.querySelector("dl")).toBeTruthy();
  });
});

describe("formatting", () => {
  test("cost has two decimals and shows under a cent as <$0.01", () => {
    expect(formatCost(0.06)).toBe("$0.06");
    expect(formatCost(1.5)).toBe("$1.50");
    expect(formatCost(0.004)).toBe("<$0.01");
    expect(formatCost(null)).toBeNull();
  });

  test("run time reads in seconds, then minutes and seconds", () => {
    expect(formatRunTime(47)).toBe("47 seconds");
    expect(formatRunTime(1)).toBe("1 second");
    expect(formatRunTime(125)).toBe("2 min 5 s");
    expect(formatRunTime(120)).toBe("2 min");
    expect(formatRunTime(null)).toBeNull();
  });

  test("stage seconds keep one decimal below ten seconds", () => {
    expect(formatStageSeconds(4)).toBe("4 s");
    expect(formatStageSeconds(1.2)).toBe("1.2 s");
    expect(formatStageSeconds(38.4)).toBe("38 s");
    expect(formatStageSeconds(null)).toBeNull();
  });

  test("dates read in UTC, so an evening UTC run keeps its date", () => {
    expect(formatRunDate("2026-11-05T23:50:00+00:00")).toBe("Nov 5, 2026");
    expect(formatRunDate(null)).toBeNull();
  });
  test("a publish-only duration does not count as a recorded run", () => {
    renderWith({
      ...unrecorded,
      started_at: "2026-11-05T08:28:00+00:00",
      duration_seconds: 0.14,
      stages: [{ name: "publish", seconds: 0.14 }],
    });
    expect(screen.getByText("The run details appear after the next full pipeline run.")).toBeTruthy();
  });
});

describe("last full run", () => {
  test("shows the full run and says a cached refresh came after it", () => {
    const refresh: RunMetadata = {
      ...recorded,
      started_at: "2026-11-06T09:00:00+00:00",
      duration_seconds: 18,
      input_tokens: 0,
      output_tokens: 0,
      estimated_cost_usd: 0,
    };
    const dashboard: Dashboard = { ...makeTestDashboard(), run: refresh, last_full_run: recorded };
    render(
      <AgentRunSection
        dashboard={dashboard}
        quarter={dashboard.quarters[0]}
        onSelectQuarter={() => undefined}
      />,
    );
    expect(screen.getByText(formatCost(0.06) as string)).toBeTruthy();
    expect(screen.getByText(/The last full run, where the model wrote every memo and answer/)).toBeTruthy();
    expect(screen.getByText(/in 18 seconds, reusing/)).toBeTruthy();
  });

  test("with no full run recorded, shows the latest run without the note", () => {
    renderWith(recorded);
    expect(screen.queryByText(/The last full run/)).toBeNull();
  });
});
