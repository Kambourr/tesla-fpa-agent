import { MethodSection } from "../components/MethodSection";
import type { Dashboard, QuarterView } from "../data/types";
import { BreakIt } from "../showcase/BreakIt";
import { Pipeline } from "../showcase/Pipeline";

type Props = {
  dashboard: Dashboard;
  quarter: QuarterView;
};

export function MethodView({ dashboard, quarter }: Props) {
  return (
    <div className="method-view">
      <MethodSection />
      <p className="method-writeup-link">
        <a href="how-it-was-built.html">How it was built</a>
      </p>
      <Pipeline dashboard={dashboard} quarter={quarter} />
      <BreakIt dashboard={dashboard} quarter={quarter} />
    </div>
  );
}
