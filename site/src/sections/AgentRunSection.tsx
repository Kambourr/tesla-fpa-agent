import "./AgentRunSection.css";
import type { RunMetadata, StageName } from "../data/types";
import {
  STAGE_LABEL,
  STAGE_ORDER,
  formatCost,
  formatRunDate,
  formatRunTime,
  formatStageSeconds,
  isRunUnrecorded,
  stageKind,
} from "./AgentRunFormat";
import type { SectionProps } from "./types";

const NOT_RECORDED_YET = "Not recorded yet";

function StatValue({ value }: { value: string | null }) {
  return <dd>{value ?? NOT_RECORDED_YET}</dd>;
}

function RunStats({ run }: { run: RunMetadata }) {
  return (
    <dl className="agent-run-stats">
      <div>
        <dt>Last run</dt>
        <StatValue value={formatRunDate(run.started_at)} />
      </div>
      <div>
        <dt>Total run time</dt>
        <StatValue value={formatRunTime(run.duration_seconds)} />
      </div>
      <div>
        <dt>AI cost</dt>
        <StatValue value={formatCost(run.estimated_cost_usd)} />
      </div>
      <div>
        <dt>Model</dt>
        <StatValue value={run.model} />
      </div>
      <div>
        <dt>Data as of</dt>
        <StatValue value={formatRunDate(run.data_as_of)} />
      </div>
    </dl>
  );
}

function StageDuration({ seconds }: { seconds: number | null }) {
  const text = formatStageSeconds(seconds);
  if (text === null) {
    return (
      <span className="agent-run-seconds">
        <span aria-hidden="true">—</span>
        <span className="visually-hidden">not recorded</span>
      </span>
    );
  }
  return <span className="agent-run-seconds">{text}</span>;
}

export function AgentRunSection({ dashboard }: SectionProps) {
  // Show the run in which the model wrote everything; a cached refresh would
  // show a near-empty model stage and undersell what the pipeline does.
  const latest = dashboard.run;
  const run = dashboard.last_full_run ?? latest;
  const refreshedSince = run !== latest && latest.started_at !== null;
  const unrecorded = isRunUnrecorded(run);
  const secondsByStage = new Map<StageName, number | null>(
    run.stages.map((stage) => [stage.name, stage.seconds]),
  );

  return (
    <>
      <hr className="ledger" />
      <section className="agent-run" aria-labelledby="agent-run-title">
        <h2 id="agent-run-title">How the agent ran</h2>
        {unrecorded ? (
          <p className="agent-run-note">The run details appear after the next full pipeline run.</p>
        ) : null}
        <div className="agent-run-body">
          <ol className="agent-run-stages">
            {STAGE_ORDER.map((name, index) => (
              <li className="agent-run-stage" key={name}>
                <span className="agent-run-index">{index + 1}</span>
                <span className="agent-run-name">{STAGE_LABEL[name]}</span>
                <StageDuration seconds={secondsByStage.get(name) ?? null} />
                <span className="agent-run-kind">{stageKind(name)}</span>
              </li>
            ))}
          </ol>
          {unrecorded ? null : <RunStats run={run} />}
        </div>
        {refreshedSince ? (
          <p className="agent-run-note">
            The last full run, where the model wrote every memo and answer. Refreshed since on{" "}
            {formatRunDate(latest.started_at)} in {formatRunTime(latest.duration_seconds)}, reusing
            the verified narratives.
          </p>
        ) : null}
      </section>
    </>
  );
}
