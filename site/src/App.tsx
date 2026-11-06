import { useEffect, useRef, useState, type ReactNode } from "react";
import { AboutSection } from "./components/AboutSection";
import { QuarterPicker } from "./components/QuarterPicker";
import { footerDisclaimer } from "./config";
import { type Dashboard, loadDashboard } from "./data/types";
import { latestQuarter, needsHistoryMessage, quarterRecords } from "./quarters";
import { AccuracySection } from "./sections/AccuracySection";
import { AskSection } from "./sections/AskSection";
import { ForecastChart } from "./sections/ForecastChart";
import { ForecastSection } from "./sections/ForecastSection";
import { HeroSection } from "./sections/HeroSection";
import { MemoSection } from "./sections/MemoSection";
import { MethodView } from "./shell/MethodView";
import { Overview } from "./shell/Overview";
import { Sidebar } from "./shell/Sidebar";
import {
  hashForView,
  initialView,
  viewFromHashChange,
  type ViewId,
} from "./shell/hashView";
import "./shell/shell.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; dashboard: Dashboard };

type AppProps = {
  /** Tests pass a dashboard directly. The page fetches dashboard.json. */
  initialDashboard?: Dashboard;
};

const DRAWER_QUERY = "(max-width: 768px)";

function isDrawerViewport(): boolean {
  try {
    return window.matchMedia(DRAWER_QUERY).matches;
  } catch {
    return false;
  }
}

function scrollToHashTarget(): void {
  const id = window.location.hash.replace(/^#/, "");
  if (!id || id.startsWith("/")) {
    return;
  }
  try {
    document.getElementById(decodeURIComponent(id))?.scrollIntoView();
  } catch {
    document.getElementById(id)?.scrollIntoView();
  }
}

export function App({ initialDashboard }: AppProps = {}) {
  const [state, setState] = useState<LoadState>(
    initialDashboard ? { status: "ready", dashboard: initialDashboard } : { status: "loading" },
  );
  const [quarterId, setQuarterId] = useState("");
  const [view, setView] = useState<ViewId>(() => initialView(window.location.hash));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const menuRoot = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

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

  useEffect(() => {
    const onHash = () => {
      const next = viewFromHashChange(window.location.hash);
      if (next) {
        setView(next);
      }
      requestAnimationFrame(scrollToHashTarget);
    };
    window.addEventListener("hashchange", onHash);
    requestAnimationFrame(scrollToHashTarget);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (!drawerOpen) {
      document.body.classList.remove("drawer-open");
      return;
    }
    document.body.classList.add("drawer-open");
    const root = drawerRef.current;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusable = () => {
      if (!root) {
        return [];
      }
      return [...root.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')];
    };
    focusable()[0]?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setDrawerOpen(false);
        return;
      }
      if (event.key !== "Tab" || !isDrawerViewport()) {
        return;
      }
      const items = focusable();
      if (items.length === 0) {
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.classList.remove("drawer-open");
      document.removeEventListener("keydown", onKey);
      if (isDrawerViewport()) {
        (previouslyFocused ?? menuButtonRef.current)?.focus();
      }
    };
  }, [drawerOpen]);

  const goTo = (next: ViewId) => {
    setView(next);
    const hash = hashForView(next);
    if (window.location.hash !== hash) {
      window.location.hash = hash;
    }
  };

  const dashboard = state.status === "ready" ? state.dashboard : null;
  const records = dashboard ? quarterRecords(dashboard) : [];
  const selectedId = quarterId || latestQuarter(records)?.id || "";
  const record = records.find((item) => item.id === selectedId);
  const quarter = dashboard?.quarters.find((item) => item.quarter === selectedId);
  const sectionProps =
    dashboard && quarter
      ? { dashboard, quarter, onSelectQuarter: setQuarterId }
      : null;

  let panel: ReactNode = null;
  if (sectionProps && quarter?.has_forecast) {
    if (view === "overview") {
      panel = <Overview {...sectionProps} />;
    } else if (view === "bridge") {
      panel = <HeroSection {...sectionProps} />;
    } else if (view === "memo") {
      panel = <MemoSection {...sectionProps} />;
    } else if (view === "forecast") {
      panel = (
        <>
          <ForecastSection {...sectionProps} />
          <ForecastChart {...sectionProps} />
        </>
      );
    } else if (view === "accuracy") {
      panel = <AccuracySection {...sectionProps} />;
    } else if (view === "ask") {
      panel = <AskSection {...sectionProps} />;
    } else {
      panel = <MethodView dashboard={sectionProps.dashboard} quarter={sectionProps.quarter} />;
    }
  }

  return (
    <div className="app-shell">
      <a className="skip" href="#content">
        Skip to content
      </a>
      <button
        type="button"
        className={drawerOpen ? "nav-scrim is-open" : "nav-scrim"}
        aria-hidden={drawerOpen ? undefined : true}
        tabIndex={-1}
        aria-label="Close menu"
        onClick={() => setDrawerOpen(false)}
      />
      <Sidebar
        view={view}
        open={drawerOpen}
        onNavigate={goTo}
        onClose={() => setDrawerOpen(false)}
        drawerRef={drawerRef}
      />
      <div className="workspace">
        <header className="workspace-bar">
          <div className="workspace-tools">
            <button
              ref={menuButtonRef}
              type="button"
              className="nav-open"
              aria-expanded={drawerOpen}
              aria-controls="site-nav"
              onClick={() => setDrawerOpen((value) => !value)}
            >
              Menu
            </button>
            {record ? <p className="workspace-quarter">{record.label}</p> : null}
            {record ? (
              <QuarterPicker
                quarters={records}
                selectedId={record.id}
                onSelect={setQuarterId}
                menuRoot={menuRoot}
              />
            ) : null}
          </div>
          <div ref={menuRoot} className="quarter-slot" />
        </header>
        <main id="content" className="workspace-main" tabIndex={-1}>
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
          {dashboard && !quarter ? (
            <section className="empty" aria-labelledby="quarter-status-title">
              <h2 id="quarter-status-title">No published quarter yet</h2>
              <p>The pipeline has not written a quarter for this page to show. Run it, then reload.</p>
            </section>
          ) : null}
          {dashboard && quarter && !quarter.has_forecast ? (
            <>
              <p className="lede">{needsHistoryMessage}</p>
              <section className="empty" aria-labelledby="quarter-status-title" aria-live="polite">
                <h2 id="quarter-status-title">Waiting on history</h2>
                <p>Select a later quarter, or wait until four earlier quarters are on file.</p>
              </section>
            </>
          ) : null}
          {panel ? <div className="view">{panel}</div> : null}
        </main>
        <footer className="colophon">
          <div className="canvas">
            <AboutSection />
            <p className="disclaimer">{footerDisclaimer}</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
