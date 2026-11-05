import { buildSteps } from "./heroModel";
import type { SectionProps } from "./types";
import "./BuildChain.css";

/**
 * "What went into it": the pipeline as a numbered sequence (it is one), each
 * step stated as a short sentence with its real count, then the stack.
 */
export function BuildChain({ dashboard }: SectionProps) {
  const steps = buildSteps(dashboard);
  return (
    <section className="build" aria-labelledby="build-title">
      <h2 id="build-title">What went into it</h2>
      <ol className="build-steps">
        {steps.map((step) => (
          <li key={step.number} className="build-step">
            <span className="build-number" aria-hidden="true">
              {step.number}
            </span>
            <h3>{step.title}</h3>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
      <p className="build-stack">
        Built with Python, SQL in DuckDB, the OpenAI API with structured outputs, React with D3,
        and GitHub Actions, by <a href="#about-title">Jacob Kambour</a>.{" "}
        <a href="how-it-was-built.html">Read how it was built</a>.
      </p>
    </section>
  );
}
