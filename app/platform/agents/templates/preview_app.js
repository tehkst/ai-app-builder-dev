const statusOutput = document.getElementById("status-output");
const primaryAction = document.getElementById("primary-action");
const secondaryAction = document.getElementById("secondary-action");

const safetyStatus = {
  writeMode: "db_preview_only",
  diskWritePerformed: false,
  filesystemWritePerformed: false,
  generatedCodeExecutionPerformed: false,
  externalDeploymentPerformed: false
};

function showStatus(message) {
  statusOutput.textContent = `${message}

${JSON.stringify(safetyStatus, null, 2)}`;
}

primaryAction?.addEventListener("click", () => showStatus("Generated app preview is ready for browser review."));
secondaryAction?.addEventListener("click", () => showStatus("Safety boundary verified for DB-preview-only generation."));
showStatus("Preview loaded from generated DB record content.");
