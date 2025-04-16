/**
 * ui-state.js
 * Integrated UI navigation, updates and state management for theme processing workflow
 */

/**
 * Fetch file data from server using IDs
 */
function fetchFileDataFromIds(themeId, fileIds) {
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
 * Updated navigation function for ui.js
 * Adds support for direct jump from step 2 to step 5
 */
export function navigateToStep(step, saveState = true) {
  // Update current step
  state.currentStep = step;

  // Hide all sections
  $("#theme-section, #upload-section, #download-section, #read-section, #process-section").addClass("d-none");

  // Update progress steps
  $(".progress-step").removeClass("active completed");

  // Show current section and update UI based on the step
  switch (step) {
    case 1: // Theme
      $("#theme-section").removeClass("d-none");
      $("#step-theme").addClass("active");
      $("#workflow-progress-bar").css("width", "20%").text("Step 1 of 5");
      break;

    case 2: // Upload
      $("#upload-section").removeClass("d-none");
      $("#step-theme").addClass("completed");
      $("#step-upload").addClass("active");
      $("#workflow-progress-bar").css("width", "40%").text("Step 2 of 5");
      $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0 && state.dropZoneFiles.length === 0);

      // Restore dropzone files if they exist
      if (state.dropZoneFiles && state.dropZoneFiles.length > 0) {
        restoreDropZoneFiles();
      }
      break;

    case 3: // Download
      $("#download-section").removeClass("d-none");
      $("#step-theme, #step-upload").addClass("completed");
      $("#step-download").addClass("active");
      $("#workflow-progress-bar").css("width", "60%").text("Step 3 of 5");
      loadFilesTable();
      break;

    case 4: // Read
      $("#read-section").removeClass("d-none");
      $("#step-theme, #step-upload, #step-download").addClass("completed");
      $("#step-read").addClass("active");
      $("#workflow-progress-bar").css("width", "80%").text("Step 4 of 5");
      break;

    case 5: // Process - Direct jump from step 2 or 3
      $("#process-section").removeClass("d-none");
      // Mark all previous steps as completed
      $("#step-theme, #step-upload, #step-download, #step-read").addClass("completed");
      $("#step-process").addClass("active");
      $("#workflow-progress-bar").css("width", "100%").text("Step 5 of 5");
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
 * Update UI based on task status
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

  let progress = 0;

  if (task.current_step !== null && task.current_step !== undefined) {
    const stepMapping = {
      0: 2,
      1: 3,
      2: 4,
      3: 5,
    };

    progress = (task.current_step / 4) * 100;

    const uiStep = stepMapping[task.current_step];
    if (uiStep && task.progress !== null && task.progress !== undefined) {
      switch (uiStep) {
        case 3:
          $("#download-progress").css("width", `${task.progress}%`);
          break;
        case 4:
          $("#read-progress").css("width", `${task.progress}%`);
          break;
        case 5:
          $("#process-progress").css("width", `${task.progress}%`);
          break;
      }
    }
  }

  $("#task-progress-bar").css("width", `${progress}%`);
  $("#cancel-task-btn").toggle(["pending", "in_progress", "paused"].includes(task.status));
  $("#resume-task-btn").toggle(task.status === "paused");

  if (task.error_message) {
    $("#task-error-message").removeClass("d-none").text(task.error_message);
  } else {
    $("#task-error-message").addClass("d-none").text("");
  }

  // Update state and save
  state.processingTask = task;
  saveWorkflowState();
}

/**
 * Show success modal when the workflow is complete
 */
export function showSuccessModal() {
  $("#success-modal-theme-name").text(state.selectedTheme);
  $("#success-modal-file-count").text(state.processedFiles.length);
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
 * Load files table in the download section
 */
function loadFilesTable() {
  if (state.currentThemeId) {
    $.ajax({
      url: `/api/themes/${state.currentThemeId}/files`,
      method: "GET",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function (files) {
        renderFilesTable(files);
      },
      error: function (xhr, status, error) {
        console.error("Error loading files:", error);
        alertify.error(`Error loading files: ${xhr.responseJSON?.detail || error}`);
      },
    });
  } else {
    alertify.error("No theme selected");
  }
}

/**
 * Render files to the table
 */
function renderFilesTable(files) {
  const tableBody = $("#files-table tbody");
  tableBody.empty();

  if (files.length === 0) {
    tableBody.html(`<tr><td colspan="3" class="text-center">No files found in this theme</td></tr>`);
    $("#start-download-btn").prop("disabled", true);
    return;
  }

  files.forEach((file) => {
    const row = `
      <tr data-file-id="${file.id}">
        <td>${file.title || file.filename || file.source || "Unknown"}</td>
        <td>${formatFileSize(file.size || getRandomFileSize())}</td>
        <td><span class="badge badge-secondary">Pending</span></td>
      </tr>
    `;
    tableBody.append(row);
  });

  // Enable the download button
  $("#start-download-btn").prop("disabled", false);

  // Store files for later use
  state.uploadedFiles = files;
  saveWorkflowState();
}

/**
 * Add a log message to the processing logs
 */
export function addLogMessage(message) {
  state.processingLogs.push(message);
  $("#process-log-content").append(`<div>> ${message}</div>`);

  // Auto-scroll to bottom of log
  const logContainer = document.getElementById("process-log-content");
  if (logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  saveWorkflowState();
}

/**
 * Setup event listeners for all UI interactions
 */
export function setupEventListeners() {
  // Theme form submission
  $("#create-theme-form").on("submit", handleThemeFormSubmit);

  // Navigation buttons
  $("#upload-back-btn").on("click", () => navigateToStep(1));
  $("#upload-next-btn").on("click", () => navigateToStep(3));
  $("#download-back-btn").on("click", () => navigateToStep(2));
  $("#download-next-btn").on("click", () => navigateToStep(4));
  $("#read-back-btn").on("click", () => navigateToStep(3));
  $("#read-next-btn").on("click", () => navigateToStep(5));
  $("#process-back-btn").on("click", () => navigateToStep(4));
  $("#finish-btn").on("click", showSuccessModal);

  // Process buttons
  $("#start-download-btn").on("click", startDownloadProcess);
  $("#start-read-btn").on("click", startReadProcess);
  $("#start-process-btn").on("click", startEmbeddingProcess);

  // File selector for preview
  $("#file-selector").on("change", showFileContentPreview);

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
import { startDownloadProcess } from "./file-download.js";
import { startReadProcess } from "./file-read.js";
import { startEmbeddingProcess } from "./vectorDB.js";
import { showFileContentPreview } from "./file-preview.js";
import { cancelCurrentTask, resumeCurrentTask } from "./task.js";
import { handleWindowFocus, handleWindowBlur, handleBeforeUnload } from "./websocket.js";
import { getCsrfToken, formatFileSize, getRandomFileSize } from "./utils.js";
import { saveWorkflowState, state, restoreWorkflowState } from "./state.js";
