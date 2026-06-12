import React from "react";

export type WorkflowState =
  | "IDLE"
  | "SCOPING"
  | "AWAITING_APPROVAL"
  | "GENERATING"
  | "TESTING"
  | "SELF_HEAL"
  | "AWAITING_DEPLOYMENT";

type WorkflowStateVisualizerProps = {
  state: WorkflowState;
  scopeMarkdown?: string;
  generatedCode?: string;
  manualDeployInstructions?: string;
  alertMessage?: string;
  onStart: () => void;
  onConfirmScopeAndCode: () => void;
  onSelfHeal: () => void;
};

const states: WorkflowState[] = [
  "IDLE",
  "SCOPING",
  "AWAITING_APPROVAL",
  "GENERATING",
  "TESTING",
  "SELF_HEAL",
  "AWAITING_DEPLOYMENT",
];

export function WorkflowStateVisualizer({
  state,
  scopeMarkdown,
  generatedCode,
  manualDeployInstructions,
  alertMessage,
  onStart,
  onConfirmScopeAndCode,
  onSelfHeal,
}: WorkflowStateVisualizerProps) {
  const currentIndex = states.indexOf(state);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950 p-5 text-slate-100">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-indigo-300">Workflow Tracking Engine</p>
          <h2 className="text-xl font-bold">Admin Workspace Execution</h2>
        </div>
        <button className="rounded-md bg-rose-500 px-3 py-2 text-sm font-bold" onClick={onSelfHeal}>
          Self-Heal / Refresh Code Execution
        </button>
      </div>

      <ol className="mt-5 grid gap-2 md:grid-cols-7">
        {states.map((item, index) => (
          <li
            key={item}
            className={[
              "rounded-md border p-3 text-xs font-semibold",
              item === state ? "border-indigo-400 bg-indigo-500/20" : "border-slate-700",
              index < currentIndex ? "text-emerald-300" : "text-slate-300",
            ].join(" ")}
          >
            {item.replaceAll("_", " ")}
          </li>
        ))}
      </ol>

      {alertMessage && <p className="mt-4 rounded-md bg-amber-500/15 p-3 text-amber-200">{alertMessage}</p>}

      <div className="mt-5 flex flex-wrap gap-2">
        <button className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-bold" onClick={onStart}>
          Start Scoping
        </button>
        <button className="rounded-md bg-emerald-500 px-3 py-2 text-sm font-bold" onClick={onConfirmScopeAndCode}>
          Confirm Scope & Code
        </button>
      </div>

      {scopeMarkdown && <pre className="mt-5 overflow-auto rounded-md bg-slate-900 p-4 text-sm">{scopeMarkdown}</pre>}
      {generatedCode && <textarea className="mt-5 h-44 w-full rounded-md bg-slate-900 p-4 font-mono text-sm" readOnly value={generatedCode} />}
      {manualDeployInstructions && <p className="mt-3 text-sm text-slate-300">{manualDeployInstructions}</p>}
    </section>
  );
}
