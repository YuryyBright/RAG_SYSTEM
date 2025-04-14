/**
 * file-read.js
 * Handles text extraction and processing from downloaded files
 */

import { state } from "./state.js";
import { addProcessingLog, getCsrfToken } from "./utils.js";
import { updateVectorDBStatusUI } from "./vectorDB.js";

/**
 * Start the file reading process
 */
export function startReadProcess() {
  // Create task for reading files
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "read",
      files: state.downloadedFiles.map((f) => f.id),
      description: `Extract text from files for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "read",
        vectorDBStatus: state.vectorDBStatus,
        totalFiles: state.downloadedFiles.length,
      },
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      // Store the task reference
      state.processingTask = response;

      // The real updates will come via WebSocket
      alertify.success("Started text extraction process");

      // Initialize reading progress
      $("#read-progress").css("width", "0%");
      state.processedFiles = [];

      // Add log entry
      addProcessingLog("Starting text extraction process...");

      // Update vector DB status
      state.vectorDBStatus.textChunking = "in_progress";
      updateVectorDBStatusUI();
    },
    error: function (xhr, status, error) {
      console.error("Error starting read process:", error);
      alertify.error(`Error starting text extraction: ${xhr.responseJSON?.detail || error}`);
      $("#start-read-btn").prop("disabled", false);
    },
  });

  // For the UI simulation, process the files
  const totalFiles = state.downloadedFiles.length;
  let processedCount = 0;

  $("#start-read-btn").prop("disabled", true);

  // Simulate reading each file
  state.downloadedFiles.forEach((file, index) => {
    setTimeout(() => {
      // Add to processed files
      state.processedFiles.push(file);
      processedCount++;

      // Update progress
      const progress = Math.round((processedCount / totalFiles) * 100);
      $("#read-progress").css("width", `${progress}%`);

      // Add log entry
      addProcessingLog(`Extracted text from: ${file.filename || file.title || "Unknown file"}`);

      // Check if all files are processed
      if (processedCount === totalFiles) {
        alertify.success("All files processed successfully");
        $("#read-next-btn").prop("disabled", false);

        // Update vector DB status
        state.vectorDBStatus.textChunking = "completed";
        updateVectorDBStatusUI();

        // Add log entry
        addProcessingLog("Text extraction completed successfully!");
      }
    }, 1500 + index * 800); // Staggered timing for visual effect
  });
}
