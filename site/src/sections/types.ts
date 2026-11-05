import type { Dashboard, QuarterView } from "../data/types";

/** Every page section receives the whole dashboard and the selected quarter. */
export type SectionProps = {
  dashboard: Dashboard;
  quarter: QuarterView;
  /** Switch the page to another quarter id (for example the latest one). */
  onSelectQuarter: (id: string) => void;
};
