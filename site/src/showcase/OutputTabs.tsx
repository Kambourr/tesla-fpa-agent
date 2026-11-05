import { useEffect, useState, type ReactNode } from "react";
import { MethodSection } from "../components/MethodSection";
import type { Dashboard, QuarterView } from "../data/types";
import { AccuracySection } from "../sections/AccuracySection";
import { AskSection } from "../sections/AskSection";
import { ForecastChart } from "../sections/ForecastChart";
import { ForecastSection } from "../sections/ForecastSection";
import { HeroSection } from "../sections/HeroSection";
import { MemoSection } from "../sections/MemoSection";
import { useTabs } from "./useTabs";
import "./OutputTabs.css";

export const OUTPUT_TABS = ["bridge", "memo", "forecast", "accuracy", "qa", "method"] as const;
export type OutputTab = (typeof OUTPUT_TABS)[number];

const LABELS: Record<OutputTab, string> = {
  bridge: "Revenue bridge",
  memo: "Analyst memo",
  forecast: "Forecast and scenarios",
  accuracy: "Accuracy",
  qa: "Ask the analyst",
  method: "Method",
};

/** In-page anchors that live inside a tab: following one opens that tab. */
const ANCHOR_TAB: Record<string, OutputTab> = {
  "method-title": "method",
  "analyst-memo-title": "memo",
  "forecast-heading": "forecast",
  "accuracy-heading": "accuracy",
  "ask-heading": "qa",
};

const PANEL_ID = "outputs-panel";

type Props = {
  dashboard: Dashboard;
  quarter: QuarterView;
  onSelectQuarter: (id: string) => void;
};

function tabForHash(hash: string): OutputTab | null {
  return ANCHOR_TAB[decodeURIComponent(hash.replace(/^#/, ""))] ?? null;
}

/**
 * Everything the pipeline publishes, in one panel with tabs instead of a long
 * stack of sections. Only the open tab renders.
 */
export function OutputTabs({ dashboard, quarter, onSelectQuarter }: Props) {
  const [selected, setSelected] = useState<OutputTab>(() => tabForHash(window.location.hash) ?? "bridge");
  const { onKeyDown, tabProps } = useTabs(OUTPUT_TABS, selected, setSelected);

  // A link such as "See how the figures are checked" (#method-title) opens its tab, then scrolls.
  useEffect(() => {
    const open = () => {
      const tab = tabForHash(window.location.hash);
      if (!tab) return;
      setSelected(tab);
      requestAnimationFrame(() =>
        document.getElementById(decodeURIComponent(window.location.hash.slice(1)))?.scrollIntoView(),
      );
    };
    window.addEventListener("hashchange", open);
    return () => window.removeEventListener("hashchange", open);
  }, []);

  const props = { dashboard, quarter, onSelectQuarter };
  const panels: Record<OutputTab, () => ReactNode> = {
    bridge: () => <HeroSection {...props} />,
    memo: () => <MemoSection {...props} />,
    forecast: () => (
      <>
        <ForecastSection {...props} />
        <ForecastChart {...props} />
      </>
    ),
    accuracy: () => <AccuracySection {...props} />,
    qa: () => <AskSection {...props} />,
    method: () => <MethodSection />,
  };

  return (
    <section className="outputs" aria-labelledby="outputs-title">
      <div className="outputs-head">
        <h2 id="outputs-title" className="outputs-title">
          What it publishes for {quarter.label}
        </h2>
      </div>
      <div className="outputs-tabs" role="tablist" aria-label="Outputs" onKeyDown={onKeyDown}>
        {OUTPUT_TABS.map((tab) => (
          <button key={tab} className="outputs-tab" {...tabProps(tab, PANEL_ID)}>
            {LABELS[tab]}
          </button>
        ))}
      </div>
      <div
        className="outputs-panel"
        role="tabpanel"
        id={PANEL_ID}
        aria-labelledby={`${PANEL_ID}-tab-${selected}`}
        tabIndex={0}
      >
        {panels[selected]()}
      </div>
    </section>
  );
}
