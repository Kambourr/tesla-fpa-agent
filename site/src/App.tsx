import { useEffect, useRef, useState } from "react";
import { AboutSection } from "./components/AboutSection";
import { MastheadMark } from "./components/MastheadMark";
import { MethodSection } from "./components/MethodSection";
import { QuarterPicker } from "./components/QuarterPicker";
import { ThemeToggle } from "./components/ThemeToggle";
import { footerDisclaimer, siteName } from "./config";
import { type Dashboard, loadDashboard } from "./data/types";
import { latestQuarter, needsHistoryMessage, quarterRecords } from "./quarters";
import { AccuracySection } from "./sections/AccuracySection";
import { AgentRunSection } from "./sections/AgentRunSection";
import { AskSection } from "./sections/AskSection";
import { BuildChain } from "./sections/BuildChain";
import { ForecastChart } from "./sections/ForecastChart";
import { ForecastSection } from "./sections/ForecastSection";
import { HeroQuote } from "./sections/HeroQuote";
import { HeroSection } from "./sections/HeroSection";
import { MemoSection } from "./sections/MemoSection";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; dashboard: Dashboard };

type AppProps = {
  /** Tests pass a dashboard directly. The page fetches dashboard.json. */
  initialDashboard?: Dashboard;
};

export function App({ initialDashboard }: AppProps = {}) {
  const [state, setState] = useState<LoadState>(
    initialDashboard ? { status: "ready", dashboard: initialDashboard } : { status: "loading" },
  );
  const [quarterId, setQuarterId] = useState("");
  const menuRoot = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialDashboard) {
      return;
    }
    let cancelled = false;
    loadDashboard(import.meta.env.BASE_URL)
      .then((dashboard) => {
        if (!cancelled) {
          setState({ status: "ready", dashboard });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ status: "error", message: String(error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialDashboard]);

  const dashboard = state.status === "ready" ? state.dashboard : null;
  const records = dashboard ? quarterRecords(dashboard) : [];
  const selectedId = quarterId || latestQuarter(records)?.id || "";
  const record = records.find((item) => item.id === selectedId);
  const view = dashboard?.quarters.find((item) => item.quarter === selectedId);

  return (
    <>
      <a className="skip" href="#content">
        Skip to content
      </a>
      <header className="masthead">
        <div className="canvas masthead-bar">
          <div className="site-name">
            <MastheadMark />
            <span>{siteName}</span>
          </div>
          <div className="masthead-tools">
            {record ? (
              <QuarterPicker
                quarters={records}
                selectedId={record.id}
                onSelect={setQuarterId}
                menuRoot={menuRoot}
              />
            ) : null}
            <a className="masthead-author" href="#about-title">
              Jacob Kambour
            </a>
            <ThemeToggle />
          </div>
        </div>
        <div ref={menuRoot} className="canvas quarter-slot" />
      </header>
      <main id="content" className="canvas" tabIndex={-1}>
        <h1>Tesla's quarter, forecast and explained by an agent, checked against the filings.</h1>
        {state.status === "loading" ? <p className="lede">Loading the published quarters.</p> : null}
        {state.status === "error" ? (
          <section className="empty" aria-labelledby="load-error-title">
            <h2 id="load-error-title">The published data did not load</h2>
            <p>
              The page could not read data/dashboard.json. Reload the page. If it still fails, the
              pipeline has not published a quarter yet.
            </p>
          </section>
        ) : null}
        {dashboard && !view ? (
          <section className="empty" aria-labelledby="quarter-status-title">
            <h2 id="quarter-status-title">No published quarter yet</h2>
            <p>The pipeline has not written a quarter for this page to show. Run it, then reload.</p>
          </section>
        ) : null}
        {dashboard && view && !view.has_forecast ? (
          <>
            <p className="lede">{needsHistoryMessage}</p>
            <section className="empty" aria-labelledby="quarter-status-title" aria-live="polite">
              <h2 id="quarter-status-title">Waiting on history</h2>
              <p>Select a later quarter, or wait until four earlier quarters are on file.</p>
            </section>
          </>
        ) : null}
        {dashboard && view && view.has_forecast ? (
          <>
            <HeroQuote dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <BuildChain dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <hr className="ledger" />
            <HeroSection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <MemoSection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <ForecastSection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <ForecastChart dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <AskSection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <AccuracySection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
            <AgentRunSection dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
          </>
        ) : null}
        <hr className="ledger" />
        <MethodSection />
        <hr className="ledger" />
        <AboutSection />
      </main>
      <footer className="colophon">
        <div className="canvas">
          <p className="disclaimer">{footerDisclaimer}</p>
        </div>
      </footer>
    </>
  );
}
