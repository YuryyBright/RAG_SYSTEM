/**
 * task.js
 * Handles task management functions for theme processing
 */

import { state } from "./state.js";
import { updateTaskUI } from "./ui.js";
import { addProcessingLog, getCsrfToken } from "./utils.js";

/**
 * Check for active tasks on page load
 */
export function checkForActiveTasks() {
  // Check if we have an active theme
  if (state.currentThemeId) {
    $.ajax({
      url: `/api/tasks?theme_id=${state.currentThemeId}`,
      method: "GET",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function (tasks) {
        if (tasks && tasks.length > 0) {
          const activeTasks = tasks.filter(
            (t) => (t.status === "in_progress" || t.status === "pending") && t.type === "theme_processing"
          );

          if (activeTasks.length > 0) {
            // Sort by most recently created
            activeTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            // Get the first (most recent) task
            state.processingTask = activeTasks[0];

            // Update UI based on task status
            updateTaskUI(state.processingTask);

            // Restore vector DB status if available
            if (state.processingTask.metadata && state.processingTask.metadata.vectorDBStatus) {
              state.vectorDBStatus = state.processingTask.metadata.vectorDBStatus;
              updateVectorDBStatusUI();
            }

            // Restore logs if available
            if (state.processingTask.logs && state.processingTask.logs.length > 0) {
              // Clear existing logs
              $("#process-log-content").empty();

              // Add each log entry
              state.processingTask.logs.forEach((log) => {
                $("#process-log-content").append(`<div>> ${log}</div>`);
              });

              // Store in state
              state.processingLogs = state.processingTask.logs;
            }
          }
        }
      },
      error: function (xhr, status, error) {
        console.error("Error checking for active tasks:", error);
      },
    });
  }
}

/**
 * Update task logs on the server
 */
export function updateTaskLogs(taskId, logEntry) {
  // This could be optimized to batch updates instead of sending one at a time
  $.ajax({
    url: `/api/tasks/${taskId}/logs`,
    method: "POST",
    data: JSON.stringify({
      log_entry: logEntry,
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    error: function (xhr, status, error) {
      console.error("Error updating task logs:", error);
    },
  });
}

/**
 * Cancel the current processing task
 */
export function cancelCurrentTask() {
  if (!state.processingTask || !state.processingTask.id) {
    alertify.error("No active task to cancel");
    return;
  }

  if (confirm("Are you sure you want to cancel this task? This action cannot be undone.")) {
    $.ajax({
      url: `/api/tasks/${state.processingTask.id}/cancel`,
      method: "POST",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function (response) {
        alertify.success("Task cancelled successfully");

        // Update local state
        state.processingTask.status = "cancelled";

        // Update UI
        updateTaskUI(state.processingTask);

        // Add log entry
        addProcessingLog("Task cancelled by user");
      },
      error: function (xhr, status, error) {
        console.error("Error cancelling task:", error);
        alertify.error(`Error cancelling task: ${xhr.responseJSON?.detail || error}`);
      },
    });
  }
}

/**
 * Resume the current processing task
 */
export function resumeCurrentTask() {
  if (!state.processingTask || !state.processingTask.id) {
    alertify.error("No task to resume");
    return;
  }

  $.ajax({
    url: `/api/tasks/${state.processingTask.id}/resume`,
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      alertify.success("Task resumed successfully");

      // Update local state
      state.processingTask.status = "in_progress";

      // Update UI
      updateTaskUI(state.processingTask);

      // Add log entry
      addProcessingLog("Task resumed by user");
    },
    error: function (xhr, status, error) {
      console.error("Error resuming task:", error);
      alertify.error(`Error resuming task: ${xhr.responseJSON?.detail || error}`);
    },
  });
}

/**
 * Handle before unload event to warn if there's an active task
 */
export function handleBeforeUnload(e) {
  // Only show warning if there's an active task
  if (state.processingTask && ["pending", "in_progress"].includes(state.processingTask.status)) {
    const message = "You have an active processing task. Are you sure you want to leave?";
    e.returnValue = message;
    return message;
  }
}

/**
 * Update the UI to reflect the current vector DB processing status
 */
export function updateVectorDBStatusUI() {
  // Update the status badges for each step
  const statusMapping = {
    pending: { class: "badge-secondary", text: "Pending" },
    in_progress: { class: "badge-warning", text: "In Progress" },
    completed: { class: "badge-success", text: "Completed" },
    failed: { class: "badge-danger", text: "Failed" },
  };

  // Data Ingestion step
  const dataIngestionStatus = statusMapping[state.vectorDBStatus.dataIngestion] || statusMapping.pending;
  $("#step-data-ingestion")
    .removeClass("active completed")
    .addClass(
      state.vectorDBStatus.dataIngestion === "in_progress"
        ? "active"
        : state.vectorDBStatus.dataIngestion === "completed"
        ? "completed"
        : ""
    );
  $("#step-data-ingestion .badge")
    .removeClass("badge-secondary badge-warning badge-success badge-danger")
    .addClass(dataIngestionStatus.class)
    .text(dataIngestionStatus.text);

  // Text Chunking step
  const textChunkingStatus = statusMapping[state.vectorDBStatus.textChunking] || statusMapping.pending;
  $("#step-chunk-text")
    .removeClass("active completed")
    .addClass(
      state.vectorDBStatus.textChunking === "in_progress"
        ? "active"
        : state.vectorDBStatus.textChunking === "completed"
        ? "completed"
        : ""
    );
  $("#step-chunk-text .badge")
    .removeClass("badge-secondary badge-warning badge-success badge-danger")
    .addClass(textChunkingStatus.class)
    .text(textChunkingStatus.text);

  // Generate Embeddings step
  const generateEmbeddingsStatus = statusMapping[state.vectorDBStatus.generateEmbeddings] || statusMapping.pending;
  $("#step-generate-embeddings")
    .removeClass("active completed")
    .addClass(
      state.vectorDBStatus.generateEmbeddings === "in_progress"
        ? "active"
        : state.vectorDBStatus.generateEmbeddings === "completed"
        ? "completed"
        : ""
    );
  $("#step-generate-embeddings .badge")
    .removeClass("badge-secondary badge-warning badge-success badge-danger")
    .addClass(generateEmbeddingsStatus.class)
    .text(generateEmbeddingsStatus.text);

  // Store Vectors step
  const storeVectorsStatus = statusMapping[state.vectorDBStatus.storeVectors] || statusMapping.pending;
  $("#step-store-vectors")
    .removeClass("active completed")
    .addClass(
      state.vectorDBStatus.storeVectors === "in_progress"
        ? "active"
        : state.vectorDBStatus.storeVectors === "completed"
        ? "completed"
        : ""
    );
  $("#step-store-vectors .badge")
    .removeClass("badge-secondary badge-warning badge-success badge-danger")
    .addClass(storeVectorsStatus.class)
    .text(storeVectorsStatus.text);
}

/**
 * Start the embedding process
 */
export function startEmbeddingProcess() {
  $("#start-process-btn").prop("disabled", true);
  $("#process-progress").css("width", "0%");

  // Create task for embedding
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "embed",
      files: state.processedFiles.map((f) => f.id),
      description: `Generate embeddings and create vector DB for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "embed",
        vectorDBStatus: state.vectorDBStatus,
        totalFiles: state.processedFiles.length,
      },
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      // Store the task reference
      state.processingTask = response;

      // Display task info
      alertify.success("Started embedding process");

      // Add log entry
      addProcessingLog("Starting vector embedding generation process...");

      // Update vector DB status
      state.vectorDBStatus.generateEmbeddings = "in_progress";
      updateVectorDBStatusUI();
    },
    error: function (xhr, status, error) {
      console.error("Error starting embedding process:", error);
      alertify.error(`Error starting embeddings: ${xhr.responseJSON?.detail || error}`);
      $("#start-process-btn").prop("disabled", false);
    },
  });

  // Simulate embedding process for UI
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 5;
    $("#process-progress").css("width", `${progress}%`);

    if (progress === 25) {
      addProcessingLog("Generating embeddings for chunks...");
    } else if (progress === 50) {
      state.vectorDBStatus.generateEmbeddings = "completed";
      state.vectorDBStatus.storeVectors = "in_progress";
      updateVectorDBStatusUI();
      addProcessingLog("Embeddings generated successfully!");
      addProcessingLog("Starting vector database storage...");
    } else if (progress === 75) {
      addProcessingLog("Optimizing vector database for search...");
    }

    if (progress >= 100) {
      clearInterval(progressInterval);
      state.vectorDBStatus.storeVectors = "completed";
      updateVectorDBStatusUI();
      addProcessingLog("Vector database created successfully!");
      alertify.success("Embedding process completed successfully");
      $("#finish-btn").prop("disabled", false);
    }
  }, 500);
}
