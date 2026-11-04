import { useRef, useState } from "react";
import { MastheadMark } from "./components/MastheadMark";
import { QuarterPicker } from "./components/QuarterPicker";
import { ThemeToggle } from "./components/ThemeToggle";
import { footerDisclaimer, siteName } from "./config";
import { latestQuarter, needsHistoryMessage, quarterFixture } from "./quarters";

export function App() {
  const initial = latestQuarter(quarterFixture);
  const [quarterId, setQuarterId] = useState(initial?.id ?? "");
  const quarter = quarterFixture.find((item) => item.id === quarterId);
  const menuRoot = useRef<HTMLDivElement>(null);

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
            {quarter ? (
              <QuarterPicker
                quarters={quarterFixture}
                selectedId={quarter.id}
                onSelect={setQuarterId}
                menuRoot={menuRoot}
              />
            ) : null}
            <ThemeToggle />
          </div>
        </div>
        <div ref={menuRoot} className="canvas quarter-slot" />
      </header>
      <main id="content" className="canvas" tabIndex={-1}>
        <h1>Tesla's quarter, forecast and explained by an agent, checked against the filings.</h1>
        {quarter ? (
          <p className="lede">
            {quarter.hasForecast
              ? `${quarter.label} is selected. The forecast, the actual revenue, and the variance will sit under this heading once they are published.`
              : needsHistoryMessage}
          </p>
        ) : (
          <p className="lede">
            The forecast, the actual revenue, and the variance will sit under this heading once a
            quarter is published.
          </p>
        )}
        <hr className="ledger" />
        <section className="empty" aria-labelledby="quarter-status-title" aria-live="polite">
          {quarter?.hasForecast === false ? (
            <>
              <h2 id="quarter-status-title">Waiting on history</h2>
              <p>Select a later quarter, or wait until four earlier quarters are on file.</p>
            </>
          ) : quarter ? (
            <>
              <h2 id="quarter-status-title">Published figures are not here yet</h2>
              <p>
                The pipeline has not written the forecast or the actual revenue for this page. Run
                it, then reload.
              </p>
            </>
          ) : (
            <>
              <h2 id="quarter-status-title">No published quarter yet</h2>
              <p>The pipeline has not written a quarter for this page to show. Run it, then reload.</p>
            </>
          )}
        </section>
      </main>
      <footer className="colophon">
        <div className="canvas">
          <p className="disclaimer">{footerDisclaimer}</p>
        </div>
      </footer>
    </>
  );
}
