/**
 * Example pipeline shape for the methods section.
 * Not a recorded run, not published JSON, and not a dollar amount.
 */
export const pipelineExampleNote = "Example of the pipeline. Not a recorded run.";

export const pipelineStages = [
  { step: "1", name: "Ingest", actor: "Code" },
  { step: "2", name: "Load", actor: "Code" },
  { step: "3", name: "Forecast", actor: "Code" },
  { step: "4", name: "Explain", actor: "Model" },
  { step: "5", name: "Verify", actor: "Code" },
  { step: "6", name: "Publish", actor: "Code" },
] as const;
