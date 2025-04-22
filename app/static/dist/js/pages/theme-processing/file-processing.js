/**
 * file-processing.js
 * Handles file processing after uploading, including chunking and embedding
 */
import { state, saveWorkflowState } from "./state.js";
import { getCsrfToken } from "./utils.js";
import { updateVectorDBStatusUI } from "./vectorDB.js";
import { addLogMessage } from "./ui.js";

/**
 * Start file processing workflow (chunking and embedding)
 * This function is called after files have been uploaded and need to be processed
 */
/**
 * Start file processing workflow (chunking and embedding)
 * This function is called directly after button click
 */
export function startFileProcessing() {
  if (!state.currentThemeId) {
    alertify.error("No theme selected for processing");
    return;
  }
  state.vectorDBStatus = {
    dataIngestion: "pending",
    textChunking: "pending",
    generateEmbeddings: "pending",
    storeVectors: "pending",
  };
  updateVectorDBStatusUI();

  // Disable the process button while processing
  $("#start-process-btn").prop("disabled", true);
  // Clear previous logs
  // Clear any previous logs and progress
  state.processingLogs = [];
  $("#process-log-content").empty();

  // Reset progress bars
  $("#process-progress").css("width", "0%");
  $("#task-progress-bar").css("width", "0%");
  // Update UI with processing status
  addLogMessage("Starting file processing workflow...");
  state.vectorDBStatus.dataIngestion = "completed";
  state.vectorDBStatus.textChunking = "in_progress";
  updateVectorDBStatusUI();

  // Save state to persist the "in_progress" status
  saveWorkflowState();

  // Call the API to process files
  $.ajax({
    url: `/api/files/process`,
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
      "Content-Type": "application/json",
    },
    data: JSON.stringify({
      theme_id: state.currentThemeId,
      recursive: true,
      additional_metadata: {
        theme_id: state.currentThemeId,
        theme_name: state.selectedTheme,
      },
      chunk_size: 1000,
      chunk_overlap: 200,
    }),
    success: function (response) {
      // Enable the process button again
      $("#start-process-btn").prop("disabled", false);

      // Log the complete response to console for debugging
      console.log("Complete processing response:", response);

      // Save full report into UI state
      state.processingReport = response.report;
      // Continue your existing log messages
      addLogMessage("✅ Processing completed successfully");
      addLogMessage(`Successfully processed ${response.documents_count} files`);
      addLogMessage(`API message: ${response.message}`);

      // Add detailed response logging
      // Add the rich report block into logs
      const reportBlock = showProcessingReportDetails(response.report);
      if (reportBlock) {
        addLogMessage(reportBlock, "info"); // Now injected into logs
      }

      // Update state to mark all processing steps as completed
      state.vectorDBStatus.textChunking = "completed";
      state.vectorDBStatus.generateEmbeddings = "completed";
      state.vectorDBStatus.storeVectors = "completed";
      updateVectorDBStatusUI();

      // Enable the finish button
      $("#finish-btn")
        .prop("disabled", false)
        .removeClass("d-none btn-secondary btn-warning btn-danger")
        .addClass("btn-primary btn-success")
        .show();

      // Reset the download button text after processing completes
      $("#start-download-btn").text("Start Download").prop("disabled", false);

      addLogMessage("File processing completed successfully!");
      alertify.success("Processing complete. Your data is ready to use.");
      // Save the final state
      saveWorkflowState();
      setTimeout(() => {
        alertify.success("🎉 Processing finished! Returning to theme selection...");
        navigateToStep(1); // Move back to Step 1
      }, 3000);
    },
    complete: function () {
      // Re-enable the process button
      $("#start-process-btn").prop("disabled", false);
    },
  });
}
export function showProcessingReportDetails(report) {
  if (!report) {
    console.warn("No report to display");
    return null;
  }

  const $container = $("<div></div>").addClass("processing-report-block");

  // Summary block
  const summary = `
    <div class="mb-2">
      <h5>📋 Summary</h5>
      <ul>
        <li>Total files: ${report.summary.total_files}</li>
        <li>Successfully processed: ${report.summary.successful}</li>
        <li>Unreadable files: ${report.summary.unreadable}</li>
        <li>Language detection failures: ${report.summary.language_detection_failures}</li>
        <li>Files with warnings: ${report.summary.files_with_warnings}</li>
        <li>Total chunks created: ${report.summary.total_chunks_created}</li>
        <li>Total chunks vectorized: ${report.summary.chunks_vectorized}</li>
      </ul>
    </div>
  `;
  $container.append(summary);

  // Successful files
  if (report.details.successful_files?.length > 0) {
    const successList = report.details.successful_files
      .map(
        (file) => `
      <li><strong>${file.filename}</strong> (${file.language || "Unknown Language"})</li>
    `
      )
      .join("");
    $container.append(`<div class="mb-2"><h5>✅ Successful Files</h5><ul>${successList}</ul></div>`);
  }

  // Unreadable files
  if (report.details.unreadable_files?.length > 0) {
    const unreadableList = report.details.unreadable_files
      .map(
        (file) => `
      <li><strong>${file.filename}</strong>: ${file.error}</li>
    `
      )
      .join("");
    $container.append(`<div class="mb-2"><h5>❌ Unreadable Files</h5><ul>${unreadableList}</ul></div>`);
  }

  // Files with warnings
  if (report.details.files_with_warnings?.length > 0) {
    const warningsList = report.details.files_with_warnings
      .map(
        (file) => `
      <li><strong>${file.filename}</strong>: ${file.warnings.join(", ")}</li>
    `
      )
      .join("");
    $container.append(`<div class="mb-2"><h5>⚠️ Files with Warnings</h5><ul>${warningsList}</ul></div>`);
  }

  // Recommendations
  if (report.recommendations.files_to_review?.length > 0) {
    const reviewList = report.recommendations.files_to_review.map((f) => `<li>${f}</li>`).join("");
    $container.append(`<div class="mb-2"><h5>🧐 Files Recommended for Review</h5><ul>${reviewList}</ul></div>`);
  }
  if (report.recommendations.files_to_consider_removing?.length > 0) {
    const removeList = report.recommendations.files_to_consider_removing.map((f) => `<li>${f}</li>`).join("");
    $container.append(`<div class="mb-2"><h5>🗑️ Files Recommended for Removal</h5><ul>${removeList}</ul></div>`);
  }

  // Small footer
  $container.append(`<hr><small>Report generated on ${new Date().toLocaleString()}</small>`);

  return $container[0]; // Return as pure DOM element
}
/**
 * Connect function to UI button
 */
// export function finalizeProcessingTask() {
//   if (!state.processingTask) return;

//   console.log("[Task] Finalizing processing task...");

//   // Mark task status explicitly as completed
//   state.processingTask.status = "completed";

//   // Clear WebSocket subscription if active
//   if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
//     state.taskSocket.close();
//     state.taskSocket = null;
//   }

//   // Clear vector DB status
//   state.vectorDBStatus = {
//     dataIngestion: "completed",
//     textChunking: "completed",
//     generateEmbeddings: "completed",
//     storeVectors: "completed",
//   };

//   // Clear drop zone files if needed
//   state.dropZoneFiles = [];

//   // Reset UI parts
//   $("#start-process-btn").prop("disabled", false).show();
//   $("#task-status-area").addClass("d-none");
//   $("#process-progress").css("width", "0%");
//   $("#task-progress-bar").css("width", "0%");
//   $("#task-error-message").addClass("d-none").text("");
//   $("#task-completion-info").addClass("d-none").empty();
//   $("#process-log-content").empty();
//   $("#process-log-container").addClass("d-none");

//   // Navigate to the first step
//   import("./ui.js").then(({ navigateToStep }) => {
//     navigateToStep(1);
//   });

//   // Save updated workflow
//   state.processingTask = null;
//   saveWorkflowState();

//   // Show success
//   alertify.success("🎉 Task finalized. Ready for a new theme!");
// }
