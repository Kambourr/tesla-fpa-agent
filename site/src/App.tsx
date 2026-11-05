import { startTransition, useEffect, useRef, useState } from "react";
import { MastheadMark } from "./components/MastheadMark";
import { QuarterPicker } from "./components/QuarterPicker";
import { ThemeToggle } from "./components/ThemeToggle";
import { footerDisclaimer, siteName } from "./config";
import { type Dashboard, loadDashboard } from "./data/types";
import { latestQuarter, needsHistoryMessage, quarterRecords } from "./quarters";
import { BreakIt } from "./showcase/BreakIt";
import { OutputTabs } from "./showcase/OutputTabs";
import { Pipeline } from "./showcase/Pipeline";
import { AboutSection } from "./components/AboutSection";

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
  // The first screen (hero quote and build chain) renders at once; everything
  // below it renders in a transition right after, which React splits into short
  // tasks, so a slow phone is not blocked rendering sections it cannot see yet.
  const [restReady, setRestReady] = useState(false);

  useEffect(() => {
    startTransition(() => setRestReady(true));
  }, []);

  // A link straight to a section (#about-title) arrives before that section
  // exists; scroll to it once it does.
  useEffect(() => {
    if (!restReady || !window.location.hash) {
      return;
    }
    document.getElementById(decodeURIComponent(window.location.hash.slice(1)))?.scrollIntoView();
  }, [restReady]);

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
        <div className="intro">
          <h1 className="intro-title">
            An AI analyst for Tesla's quarter that cannot publish a number code has not checked.
          </h1>
          <p className="intro-sub">
            It pulls the SEC filings, forecasts the quarter, explains the miss, and writes the memo. A
            verifier checks every figure before anything ships. Built by Jacob Kambour.{" "}
            <a href="how-it-was-built.html">Read how it was built</a>
          </p>
        </div>
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
            <BreakIt dashboard={dashboard} quarter={view} />
            <Pipeline dashboard={dashboard} quarter={view} />
          </>
        ) : null}
        {!restReady ? <div className="rest-placeholder" aria-hidden="true" /> : null}
        {restReady && dashboard && view && view.has_forecast ? (
          <OutputTabs dashboard={dashboard} quarter={view} onSelectQuarter={setQuarterId} />
        ) : null}
      </main>
      <footer className="colophon">
        <div className="canvas">
          <AboutSection />
          <p className="disclaimer">{footerDisclaimer}</p>
        </div>
      </footer>
    </>
  );
}
