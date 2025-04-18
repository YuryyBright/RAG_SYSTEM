/**
 * ui.js
 * Integrated UI navigation, updates and state management for theme processing workflow
 */

import { state, saveWorkflowState } from "./state.js";
import { getCsrfToken, formatFileSize, getRandomFileSize } from "./utils.js";

/**
 * Fetch file data from server using IDs
 */
export function fetchFileDataFromIds(themeId, fileIds) {
  if (!themeId || !fileIds || !fileIds.length) return;

  $.ajax({
    url: `/api/themes/${themeId}/documents`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (files) {
      // Filter to get only the files we want by ID
      const matchingFiles = files.filter((file) => fileIds.includes(file.id));
      if (matchingFiles.length > 0) {
        state.uploadedFiles = matchingFiles;
        $("#upload-next-btn").prop("disabled", false);
        console.log(`Restored ${matchingFiles.length} files from server`);
      }
    },
    error: function (xhr, status, error) {
      console.error("Error fetching files by ID:", error);
    },
  });
}

/**
 * Fetch all files for a theme
 */
export function fetchAllThemeFiles(themeId) {
  if (!themeId) return;

  $.ajax({
    url: `/api/themes/${themeId}/files`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (files) {
      if (files.length > 0) {
        state.uploadedFiles = files;
        $("#upload-next-btn").prop("disabled", false);
        console.log(`Fetched ${files.length} files for theme ${themeId}`);
      }
    },
    error: function (xhr, status, error) {
      console.error("Error fetching theme files:", error);
    },
  });
}

/**
 * Restore files to the drop zone UI from saved state
 */
export function restoreDropZoneFiles() {
  if (!state.dropZoneFiles || state.dropZoneFiles.length === 0) return;

  const $filesList = $("#upload-files-list");
  $filesList.empty();

  state.dropZoneFiles.forEach((file) => {
    // Create a file item element
    const fileItem = `
      <div class="file-item mb-2 p-2 border rounded" data-file-id="${file.id || ""}">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <i class="fas fa-file mr-2"></i>
            <span class="file-name">${file.name}</span>
            <span class="badge badge-info ml-2">${formatFileSize(file.size)}</span>
          </div>
          <button class="btn btn-sm btn-danger remove-file-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    `;
    $filesList.append(fileItem);
  });

  // Add event listeners to remove buttons
  $(".remove-file-btn").on("click", function (e) {
    e.preventDefault();
    const $fileItem = $(this).closest(".file-item");
    const fileId = $fileItem.data("file-id");

    // Remove from UI
    $fileItem.remove();

    // Remove from state
    if (fileId) {
      state.dropZoneFiles = state.dropZoneFiles.filter((file) => file.id !== fileId);
    } else {
      const fileName = $fileItem.find(".file-name").text();
      state.dropZoneFiles = state.dropZoneFiles.filter((file) => file.name !== fileName);
    }

    // Update next button state
    $("#upload-next-btn").prop("disabled", state.dropZoneFiles.length === 0);

    // Save the updated state
    saveWorkflowState();
  });

  // Update next button state
  $("#upload-next-btn").prop("disabled", state.dropZoneFiles.length === 0);
}

/**
 * Updated navigation function with simplified workflow
 * Removes step 4 (read) and simplifies navigation to 3 steps
 */
/**
 * Updated navigation function with simplified workflow
 * Removes step 4 (read) and simplifies navigation to 3 steps
 */
export function navigateToStep(step, saveState = true) {
  // Update current step
  state.currentStep = step;

  // Hide all sections
  $("#theme-section, #upload-section, #process-section").addClass("d-none");

  // Update progress steps
  $(".progress-step").removeClass("active completed");

  // Show current section and update UI based on the step
  switch (step) {
    case 1: // Theme
      $("#theme-section").removeClass("d-none");
      $("#step-theme").addClass("active");
      $("#workflow-progress-bar").css("width", "33%").text("Step 1 of 3");
      break;

    case 2: // Upload
      $("#upload-section").removeClass("d-none");
      $("#step-theme").addClass("completed");
      $("#step-upload").addClass("active");
      $("#workflow-progress-bar").css("width", "66%").text("Step 2 of 3");
      break;

    case 3: // Process - Direct jump from step 2
      $("#process-section").removeClass("d-none");
      // Mark all previous steps as completed
      $("#step-theme, #step-upload").addClass("completed");
      $("#step-process").addClass("active");
      $("#workflow-progress-bar").css("width", "100%").text("Step 3 of 3");
      // Update vector DB status UI
      updateVectorDBStatusUI();
      break;
  }

  // Save the current state to localStorage if requested
  if (saveState) {
    saveWorkflowState();
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
 * Update task UI with detailed logging
 */
export function updateTaskUI(task) {
  if (!task) return;

  // Update the task status area
  $("#task-status-area").removeClass("d-none");
  $("#task-name").text(task.name || "Theme Processing");
  $("#task-status").text(task.status);

  const statusBadge = $("#task-status-badge");
  statusBadge.removeClass("badge-secondary badge-info badge-warning badge-success badge-danger");

  switch (task.status) {
    case "pending":
      statusBadge.addClass("badge-secondary").text("Pending");
      break;
    case "in_progress":
      statusBadge.addClass("badge-info").text("In Progress");
      break;
    case "paused":
      statusBadge.addClass("badge-warning").text("Paused");
      break;
    case "completed":
      statusBadge.addClass("badge-success").text("Completed");
      break;
    case "failed":
      statusBadge.addClass("badge-danger").text("Failed");
      break;
    default:
      statusBadge.addClass("badge-secondary").text(task.status);
  }

  // Show message if available
  if (task.message) {
    addLogMessage(task.message);
  }

  // Calculate and update progress based on task data
  let progress = 0;

  if (task.current_step !== null && task.current_step !== undefined) {
    // Map steps to percentages for the progress bar
    const stepPercentages = {
      0: 25, // Reading files
      1: 50, // Chunking
      2: 75, // Embedding
      3: 100, // Finalizing
    };

    // Calculate progress based on step and individual progress
    const baseProgress = stepPercentages[task.current_step - 1] || 0;
    const nextStepProgress = stepPercentages[task.current_step] || 100;
    const stepRange = nextStepProgress - baseProgress;

    // Calculate final progress as base + percentage through current step
    progress = baseProgress + stepRange * (task.progress / 100);

    // Update process progress bar
    $("#process-progress").css("width", `${progress}%`);
  } else if (task.progress !== undefined) {
    // If no current_step but progress is available, use it directly
    progress = task.progress;
    $("#process-progress").css("width", `${progress}%`);
  }

  $("#task-progress-bar").css("width", `${progress}%`);
  $("#cancel-task-btn").toggle(["pending", "in_progress", "paused"].includes(task.status));
  $("#resume-task-btn").toggle(task.status === "paused");

  if (task.error_message) {
    $("#task-error-message").removeClass("d-none").text(task.error_message);
    addLogMessage(`Error: ${task.error_message}`);
  } else {
    $("#task-error-message").addClass("d-none").text("");
  }

  // Update state and save
  state.processingTask = task;
  saveWorkflowState();

  // Enable the finish button if processing is complete
  if (task.status === "completed") {
    $("#finish-btn").prop("disabled", false);
  }
}

/**
 * Show success modal when the workflow is complete
 */
export function showSuccessModal() {
  $("#success-modal-theme-name").text(state.selectedTheme);
  $("#success-modal-file-count").text(state.uploadedFiles.length);
  $("#workflow-completion-modal").modal("show");

  // Create a summary API call to finalize the theme processing
  $.ajax({
    url: `/api/themes/${state.currentThemeId}/finalize`,
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      console.log("Theme processing finalized:", response);
    },
    error: function (xhr, status, error) {
      console.error("Error finalizing theme processing:", error);
    },
  });
}

/**
 * Add a log message to the processing logs with timestamp
 */
export function addLogMessage(message) {
  const timestamp = new Date().toLocaleTimeString();
  const formattedMessage = `[${timestamp}] ${message}`;

  state.processingLogs = state.processingLogs || [];
  state.processingLogs.push(formattedMessage);
  $("#process-log-content").append(`<div class="log-entry">> ${formattedMessage}</div>`);

  // Auto-scroll to bottom of log
  const logContainer = document.getElementById("process-log-content");
  if (logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  // Log to console for better debugging
  console.log(message);

  saveWorkflowState();
}

/**
 * Set up event listeners for the updated workflow
 */
export function setupEventListeners() {
  // Theme form submission
  $("#create-theme-form").on("submit", handleThemeFormSubmit);

  // Navigation buttons - updated for simplified flow
  $("#theme-next-btn").on("click", () => navigateToStep(2));
  $("#upload-back-btn").on("click", () => navigateToStep(1));
  $("#upload-next-btn").on("click", () => navigateToStep(3));
  $("#process-back-btn").on("click", () => navigateToStep(2));
  $("#finish-btn").on("click", showSuccessModal);

  // Process button - direct processing from upload
  $("#start-process-btn").on("click", startFileProcessing);

  // Task related buttons
  $("#cancel-task-btn").on("click", cancelCurrentTask);
  $("#resume-task-btn").on("click", resumeCurrentTask);

  // Window events for handling page visibility
  $(window).on("focus", handleWindowFocus);
  $(window).on("blur", handleWindowBlur);
  $(window).on("beforeunload", handleBeforeUnload);
}
// Import dependencies from other modules for event handlers
import { handleThemeFormSubmit } from "./theme.js";
import { startFileProcessing } from "./file-processing.js";
import { cancelCurrentTask, resumeCurrentTask } from "./task.js";
import { handleWindowFocus, handleWindowBlur, handleBeforeUnload } from "./websocket.js";
