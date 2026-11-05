import { pipelineExampleNote, pipelineStages } from "../methodExample";

const wideStep = 180;

export function MethodSection() {
  return (
    <section className="method" aria-labelledby="method-title">
      <h2 id="method-title">How it works and how it is controlled</h2>
      <p className="example-note">{pipelineExampleNote}</p>
      <figure className="method-figure">
        <div className="method-scroll">
          <PipelineWide />
          <PipelineNarrow />
        </div>
        <figcaption className="visually-hidden">
          <ol>
            {pipelineStages.map((stage) => (
              <li key={stage.step}>
                {stage.step}. {stage.name}. {stage.actor}.
              </li>
            ))}
          </ol>
        </figcaption>
      </figure>
      <div className="method-prose">
        <h3>What the code does</h3>
        <p>
          The code ingests the filings, calculates the forecast, and checks each figure. The model
          writes the memo and the answers. It does not fetch data, and it does not decide whether a
          figure ties.
        </p>
        <h3>What a visitor can do</h3>
        <p>Visitors read the published files. This page does not call the model.</p>
        <h3>What gets checked</h3>
        <p>
          Every figure in the commentary is verified, flagged, or unsupported. A verified figure
          ties to the filing. A flagged figure stays on the page and shows the value the code
          expected. An unsupported figure is one the code could not trace.
        </p>
        <h3>Where the numbers come from</h3>
        <p>
          The sources are public SEC filings and the investor-relations production and delivery
          releases. No other feed is used.
        </p>
        <h3>One limit on the revenue bridge</h3>
        <p>
          Leased units are counted in total deliveries. Automotive ASP is automotive sales revenue
          divided by that total, so the volume bar treats a leased unit like a sold one. Leasing
          stays its own bar on the bridge.
        </p>
      </div>
    </section>
  );
}

function PipelineWide() {
  const width = wideStep * pipelineStages.length;
  return (
    <svg
      className="method-diagram"
      viewBox={`0 0 ${width} 132`}
      role="img"
      aria-hidden="true"
      focusable="false"
    >
      <line x1="24" y1="78" x2={width - 24} y2="78" className="diagram-rule" />
      {pipelineStages.map((stage, index) => {
        const x = wideStep * index + wideStep / 2;
        return (
          <g key={stage.step}>
            <line x1={x} y1="70" x2={x} y2="86" className="diagram-rule" />
            <text x={x} y="28" className="diagram-step" textAnchor="middle">
              {stage.step}
            </text>
            <text x={x} y="56" className="diagram-name" textAnchor="middle">
              {stage.name}
            </text>
            <text
              x={x}
              y="112"
              className={stage.actor === "Model" ? "diagram-actor is-model" : "diagram-actor"}
              textAnchor="middle"
            >
              {stage.actor}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function PipelineNarrow() {
  const row = 64;
  const height = row * pipelineStages.length;
  return (
    <svg
      className="method-diagram-narrow"
      viewBox={`0 0 320 ${height}`}
      role="img"
      aria-hidden="true"
      focusable="false"
    >
      <line x1="28" y1="16" x2="28" y2={height - 16} className="diagram-rule" />
      {pipelineStages.map((stage, index) => {
        const y = row * index + 36;
        return (
          <g key={stage.step}>
            <text x="48" y={y} className="diagram-step">
              {stage.step}
            </text>
            <text x="76" y={y} className="diagram-name">
              {stage.name}
            </text>
            <text
              x="210"
              y={y}
              className={stage.actor === "Model" ? "diagram-actor is-model" : "diagram-actor"}
            >
              {stage.actor}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
