import { MastheadMark } from "./components/MastheadMark";
import { ThemeToggle } from "./components/ThemeToggle";
import { footerDisclaimer, siteName } from "./config";

export function App() {
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
          <ThemeToggle />
        </div>
      </header>
      <main id="content" className="canvas" tabIndex={-1}>
        <h1>Tesla's quarter, forecast and explained by an agent, checked against the filings.</h1>
        <p className="lede">
          The forecast, the actual revenue, and the variance will sit under this heading once a
          quarter is published.
        </p>
        <hr className="ledger" />
        <section className="empty" aria-labelledby="empty-title">
          <h2 id="empty-title">No published quarter yet</h2>
          <p>The pipeline has not written a quarter for this page to show. Run it, then reload.</p>
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
