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
/**
 * Create a full processing report as a DOM element (ready for logging)
 * @param {object} report - The processing report
 * @returns {HTMLElement} - A ready-to-insert DOM element
 */
/**
 * Create a full processing report as a DOM element (ready for logging)
 * @param {object} report - The processing report
 * @returns {HTMLElement} - A ready-to-insert DOM element
 */
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
    const successList = report.details.successful_files.map(file => `
      <li><strong>${file.filename}</strong> (${file.language || "Unknown Language"})</li>
    `).join("");
    $container.append(`<div class="mb-2"><h5>✅ Successful Files</h5><ul>${successList}</ul></div>`);
  }

  // Unreadable files
  if (report.details.unreadable_files?.length > 0) {
    const unreadableList = report.details.unreadable_files.map(file => `
      <li><strong>${file.filename}</strong>: ${file.error}</li>
    `).join("");
    $container.append(`<div class="mb-2"><h5>❌ Unreadable Files</h5><ul>${unreadableList}</ul></div>`);
  }

  // Files with warnings
  if (report.details.files_with_warnings?.length > 0) {
    const warningsList = report.details.files_with_warnings.map(file => `
      <li><strong>${file.filename}</strong>: ${file.warnings.join(", ")}</li>
    `).join("");
    $container.append(`<div class="mb-2"><h5>⚠️ Files with Warnings</h5><ul>${warningsList}</ul></div>`);
  }

  // Recommendations
  if (report.recommendations.files_to_review?.length > 0) {
    const reviewList = report.recommendations.files_to_review.map(f => `<li>${f}</li>`).join("");
    $container.append(`<div class="mb-2"><h5>🧐 Files Recommended for Review</h5><ul>${reviewList}</ul></div>`);
  }
  if (report.recommendations.files_to_consider_removing?.length > 0) {
    const removeList = report.recommendations.files_to_consider_removing.map(f => `<li>${f}</li>`).join("");
    $container.append(`<div class="mb-2"><h5>🗑️ Files Recommended for Removal</h5><ul>${removeList}</ul></div>`);
  }

  // Small footer
  $container.append(`<hr><small>Report generated on ${new Date().toLocaleString()}</small>`);

  return $container[0]; // Return as pure DOM element
}
/**
 * Process files with individual progress tracking
 * Alternative function that updates progress for each file
 */
export function processFilesWithProgress() {
  if (!state.currentThemeId || !state.uploadedFiles.length) {
    alertify.error("No files available for processing");
    return;
  }

  $("#start-process-btn").prop("disabled", true);
  addLogMessage("Starting file processing with detailed progress tracking...");

  // Update initial status
  state.vectorDBStatus.dataIngestion = "completed";
  state.vectorDBStatus.textChunking = "in_progress";
  updateVectorDBStatusUI();

  let processedCount = 0;
  const totalFiles = state.uploadedFiles.length;

  // Create a function that processes files one by one
  function processNextFile(index) {
    if (index >= totalFiles) {
      // All files processed
      finishProcessing(true);
      return;
    }

    const file = state.uploadedFiles[index];
    addLogMessage(`Processing file (${index + 1}/${totalFiles}): ${file.filename || file.title}`);

    // Process current file
    $.ajax({
      url: `/api/files/${file.id}/process`,
      method: "POST",
      headers: { "X-CSRF-Token": getCsrfToken() },
      data: JSON.stringify({
        chunk_size: 1000,
        chunk_overlap: 200,
        theme_id: state.currentThemeId,
      }),
      contentType: "application/json",
      success: function () {
        processedCount++;
        const progress = Math.round((processedCount / totalFiles) * 100);

        // Update progress bar
        $("#process-progress").css("width", `${progress}%`);

        // Process next file
        processNextFile(index + 1);
      },
      error: function (xhr, status, error) {
        addLogMessage(`Error processing file ${file.filename}: ${xhr.responseJSON?.detail || error}`);
        // Continue with next file despite error
        processNextFile(index + 1);
      },
    });
  }

  // Function to update UI when processing is complete
  function finishProcessing(success) {
    if (success) {
      state.vectorDBStatus.textChunking = "completed";
      state.vectorDBStatus.generateEmbeddings = "completed";
      state.vectorDBStatus.storeVectors = "completed";
      addLogMessage(`Completed processing ${processedCount} out of ${totalFiles} files`);
      alertify.success("File processing complete");
    } else {
      state.vectorDBStatus.textChunking = "failed";
      alertify.error("File processing had some errors");
    }

    updateVectorDBStatusUI();
    $("#start-process-btn").prop("disabled", false);
    // В функції updateTaskUI, коли task.status === "completed"
    saveWorkflowState();
  }

  // Start processing with the first file
  processNextFile(0);
}
export function startProcessingWith() {
  if (!state.currentThemeId) {
    alertify.error("No theme selected for processing");
    return;
  }

  const files = state.downloadedFiles.map((f) => f.id);

  // Create task before processing
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
      "Content-Type": "application/json",
    },
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "processing",
      files: files,
      description: `Processing files for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "processing",
        vectorDBStatus: state.vectorDBStatus,
        filesCount: files.length,
      },
    }),
    success: function (task) {
      state.processingTask = task;

      $("#start-processing-btn").prop("disabled", true);
      addLogMessage("Starting file processing...");

      // Update UI
      state.vectorDBStatus.textChunking = "in_progress";
      updateVectorDBStatusUI();
      saveWorkflowState();

      // Fire actual processing request
      $.ajax({
        url: "/api/files/process",
        method: "POST",
        headers: {
          "X-CSRF-Token": getCsrfToken(),
          "Content-Type": "application/json",
        },
        data: JSON.stringify({
          directory_path: `/themes/${state.currentThemeId}/files`,
          recursive: true,
          additional_metadata: {
            theme_id: state.currentThemeId,
            theme_name: state.selectedTheme,
          },
          chunk_size: 1000,
          chunk_overlap: 200,
        }),
        success: function (response) {
          addLogMessage("File processing complete.");
          alertify.success("Files successfully processed.");
        },
        error: function (xhr, status, error) {
          console.error("Processing error:", error);
          alertify.error(`Processing failed: ${xhr.responseJSON?.detail || error}`);
          state.vectorDBStatus.textChunking = "failed";
          updateVectorDBStatusUI();
        },
      });
    },
    error: function (xhr, status, error) {
      alertify.error("Failed to create task: " + (xhr.responseJSON?.detail || error));
    },
  });
}
/**
 * Connect function to UI button
 */
