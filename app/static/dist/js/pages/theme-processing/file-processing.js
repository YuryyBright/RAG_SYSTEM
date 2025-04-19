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
      addLogMessage("✅ Processing completed successfully");
      // Update processing logs with details from the response
      addLogMessage(`Successfully processed ${response.documents_count} files`);

      // Display the full success message from the API
      addLogMessage(`API message: ${response.message}`);

      // Add detailed response logging
      if (response.report) {
        // Log summary information
        if (response.report.summary) {
          const summary = response.report.summary;
          addLogMessage(`Summary report:`);
          addLogMessage(`- Total files: ${summary.total_files}`);
          addLogMessage(`- Successfully processed: ${summary.successful}`);
          addLogMessage(`- Created ${summary.total_chunks_created || "?"} chunks`);
          addLogMessage(`- Vectorized ${summary.chunks_vectorized || "?"} chunks`);

          if (summary.unreadable > 0) {
            addLogMessage(`- Unreadable files: ${summary.unreadable}`);
          }

          if (summary.language_detection_failures > 0) {
            addLogMessage(`- Language detection failures: ${summary.language_detection_failures}`);
          }

          if (summary.files_with_warnings > 0) {
            addLogMessage(`- Files with warnings: ${summary.files_with_warnings}`);
          }
        }

        // Log file-by-file details if available
        if (response.report.details && response.report.details.length > 0) {
          addLogMessage(`Detailed file processing results:`);
          response.report.details.forEach((detail, index) => {
            addLogMessage(`File ${index + 1}: ${detail.filename}`);
            addLogMessage(`- Status: ${detail.success ? "Success" : "Failed"}`);
            addLogMessage(`- Chunks: ${detail.chunks_created || 0}`);
            if (detail.error) {
              addLogMessage(`- Error: ${detail.error}`);
            }
            if (detail.warnings && detail.warnings.length > 0) {
              addLogMessage(`- Warnings: ${detail.warnings.join(", ")}`);
            }
          });
        }

        // Log recommendations
        if (response.report.recommendations) {
          if (response.report.recommendations.files_to_review.length > 0) {
            addLogMessage(`Files to review: ${response.report.recommendations.files_to_review.join(", ")}`);
          }

          if (response.report.recommendations.files_to_consider_removing.length > 0) {
            addLogMessage(
              `Consider removing: ${response.report.recommendations.files_to_consider_removing.join(", ")}`
            );
          }
        }
      }

      // Update state to mark all processing steps as completed
      state.vectorDBStatus.textChunking = "completed";
      state.vectorDBStatus.generateEmbeddings = "completed";
      state.vectorDBStatus.storeVectors = "completed";
      updateVectorDBStatusUI();

      // Enable the finish button
      $("#finish-btn").prop("disabled", false).removeClass("btn-secondary").addClass("btn-primary").show(); // Явно показати кнопку

      // Reset the download button text after processing completes
      $("#start-download-btn").text("Start Download").prop("disabled", false);

      addLogMessage("File processing completed successfully!");
      alertify.success("Processing complete. Your data is ready to use.");

      // Save the final state
      saveWorkflowState();
    },
    complete: function () {
      // Re-enable the process button
      $("#start-process-btn").prop("disabled", false);
    },
  });
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
    $("#finish-btn").prop("disabled", false).removeClass("btn-secondary").addClass("btn-primary").show(); // Явно показати кнопку
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
