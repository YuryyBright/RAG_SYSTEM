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
/**
 * Enhanced navigation function with animation and state preservation
 * @param {number} step - The step to navigate to (1-3)
 * @param {boolean} saveState - Whether to save state to localStorage
 * @param {boolean} animate - Whether to animate the transition
 */
export function navigateToStep(step, saveState = true, animate = true) {
  // Validate step input
  if (step < 1 || step > 3) {
    console.error(`Invalid step: ${step}. Must be between 1 and 3.`);
    return;
  }

  // Store previous step for animation direction
  const previousStep = state.currentStep;

  // Update current step
  state.currentStep = step;

  // Prepare animation classes if needed
  if (animate) {
    const animationDirection = step > previousStep ? "slide-in-right" : "slide-in-left";

    // Add transition class to sections
    $("#theme-section, #upload-section, #process-section").addClass("section-transition");

    // Apply animation class based on direction
    $(`#${getStepName(step)}`).addClass(animationDirection);

    // Remove animation classes after transition completes
    setTimeout(() => {
      $("#theme-section, #upload-section, #process-section").removeClass("section-transition");
      $(`#${getStepName(step)}`).removeClass(animationDirection);
    }, 500); // Match this with your CSS transition duration
  }

  // Hide all sections
  $("#theme-section, #upload-section, #process-section").addClass("d-none");

  // Reset progress steps
  $(".progress-step").removeClass("active completed");

  // Show current section and update UI based on the step
  switch (step) {
    case 1: // Theme
      $("#theme-section").removeClass("d-none");
      $("#step-theme").addClass("active");
      $("#workflow-progress-bar").css("width", "33%").text("Step 1 of 3").attr("aria-valuenow", 33);
      break;

    case 2: // Upload
      $("#upload-section").removeClass("d-none");
      $("#step-theme").addClass("completed");
      $("#step-upload").addClass("active");
      $("#workflow-progress-bar").css("width", "66%").text("Step 2 of 3").attr("aria-valuenow", 66);
      break;

    case 3: // Process - Direct jump from step 2
      $("#process-section").removeClass("d-none");
      // Mark all previous steps as completed
      $("#step-theme, #step-upload").addClass("completed");
      $("#step-process").addClass("active");
      $("#workflow-progress-bar").css("width", "100%").text("Step 3 of 3").attr("aria-valuenow", 100);

      // Check if we need to restore or initialize a task
      refreshProcessingView();
      break;
  }

  // Update page title to reflect current step
  document.title = `${getStepName(step)} - Document Processing`;

  // Save the current state to localStorage if requested
  if (saveState) {
    saveWorkflowState();
  }

  // Scroll to top of the page for better UX
  window.scrollTo(0, 0);
}
/**
 * Refresh the processing view when navigating to step 3
 * Checks for active tasks and restores UI state
 */
function refreshProcessingView() {
  // Update vector DB status UI
  updateVectorDBStatusUI();

  // Check if there's an active task
  if (state.processingTask) {
    // Show the task status area
    $("#task-status-area").removeClass("d-none");

    // If task is in progress, ensure WebSocket connection is active
    if (["pending", "in_progress", "paused"].includes(state.processingTask.status)) {
      if (!state.taskSocket || state.taskSocket.readyState !== WebSocket.OPEN) {
        // Attempt to reconnect WebSocket
        import("./websocket.js").then(({ initializeWebSocketConnection }) => {
          initializeWebSocketConnection();
        });
      }

      // Refresh task status from server
      import("./task.js").then(({ refreshTaskStatus }) => {
        refreshTaskStatus(state.processingTask.id);
      });
    }
  } else {
    // No active task - show the start button
    $("#task-status-area").addClass("d-none");
    $("#start-process-btn").prop("disabled", false).show();
  }

  // Show processing logs if available
  if (state.processingLogs && state.processingLogs.length > 0) {
    $("#process-log-container").removeClass("d-none");
  }
}

/**
 * Helper function to get step name based on step number
 */
function getStepName(step) {
  switch (step) {
    case 1:
      return "Select Theme";
    case 2:
      return "Upload Files";
    case 3:
      return "Process Files";
    default:
      return "Document Processing";
  }
}
/**
 * Enhanced UI update function with animation and better status tracking
 * Adds visual feedback for status changes
 */
export function updateVectorDBStatusUI() {
  // Store previous statuses for animation
  const previousStatuses = {
    dataIngestion: $("#step-data-ingestion").attr("data-status") || state.vectorDBStatus.dataIngestion,
    textChunking: $("#step-chunk-text").attr("data-status") || state.vectorDBStatus.textChunking,
    generateEmbeddings: $("#step-generate-embeddings").attr("data-status") || state.vectorDBStatus.generateEmbeddings,
    storeVectors: $("#step-store-vectors").attr("data-status") || state.vectorDBStatus.storeVectors,
  };

  // Update the status badges for each step
  const statusMapping = {
    pending: { class: "badge-secondary", text: "Pending", icon: "fa-clock" },
    in_progress: { class: "badge-warning", text: "In Progress", icon: "fa-spinner fa-spin" },
    completed: { class: "badge-success", text: "Completed", icon: "fa-check" },
    failed: { class: "badge-danger", text: "Failed", icon: "fa-times" },
  };

  // Helper function to update a single step's UI
  function updateStepUI(stepId, statusKey, previousStatus) {
    const currentStatus = state.vectorDBStatus[statusKey];
    const statusInfo = statusMapping[currentStatus] || statusMapping.pending;

    // Store the current status as a data attribute
    $(`#${stepId}`).attr("data-status", currentStatus);

    // Update step status classes
    $(`#${stepId}`)
      .removeClass("active completed failed")
      .addClass(
        currentStatus === "in_progress"
          ? "active"
          : currentStatus === "completed"
          ? "completed"
          : currentStatus === "failed"
          ? "failed"
          : ""
      );

    // Update badge and text
    $(`#${stepId} .badge`)
      .removeClass("badge-secondary badge-warning badge-success badge-danger")
      .addClass(statusInfo.class)
      .html(`<i class="fas ${statusInfo.icon} mr-1"></i> ${statusInfo.text}`);

    // Add animation if status changed
    if (previousStatus !== currentStatus) {
      $(`#${stepId}`).addClass("status-changed");
      setTimeout(() => $(`#${stepId}`).removeClass("status-changed"), 1000);
    }
  }

  // Update each processing step
  updateStepUI("step-data-ingestion", "dataIngestion", previousStatuses.dataIngestion);
  updateStepUI("step-chunk-text", "textChunking", previousStatuses.textChunking);
  updateStepUI("step-generate-embeddings", "generateEmbeddings", previousStatuses.generateEmbeddings);
  updateStepUI("step-store-vectors", "storeVectors", previousStatuses.storeVectors);

  // Update overall status summary
  updateProcessingSummary();
}
/**
 * Update the processing summary based on current status
 */
function updateProcessingSummary() {
  const statusCounts = {
    pending: 0,
    in_progress: 0,
    completed: 0,
    failed: 0,
  };

  // Count statuses
  Object.values(state.vectorDBStatus).forEach((status) => {
    statusCounts[status]++;
  });

  // Determine overall status
  let overallStatus, statusText, progressPercent;

  if (statusCounts.failed > 0) {
    overallStatus = "failed";
    statusText = "Processing Failed";
    progressPercent = 100;
  } else if (statusCounts.completed === 4) {
    overallStatus = "completed";
    statusText = "Processing Complete";
    progressPercent = 100;
  } else if (statusCounts.in_progress > 0) {
    overallStatus = "in_progress";
    statusText = "Processing...";
    // Calculate progress: completed steps + half of in-progress steps
    progressPercent = statusCounts.completed * 25 + statusCounts.in_progress * 12.5;
  } else {
    overallStatus = "pending";
    statusText = "Ready to Process";
    progressPercent = 0;
  }

  // Update summary display
  $("#processing-status-summary")
    .removeClass("text-secondary text-warning text-success text-danger")
    .addClass(
      overallStatus === "pending"
        ? "text-secondary"
        : overallStatus === "in_progress"
        ? "text-warning"
        : overallStatus === "completed"
        ? "text-success"
        : "text-danger"
    )
    .text(statusText);

  // Update overall progress bar if not being controlled directly by task
  if (!state.processingTask || state.processingTask.current_step === undefined) {
    $("#process-progress").css("width", `${progressPercent}%`).attr("aria-valuenow", progressPercent);
  }
}

/**
 * Enhanced task UI update with improved status indication and animations
 */
export function updateTaskUI(task) {
  if (!task) return;

  // Check if task changed
  const taskChanged =
    !state.processingTask ||
    state.processingTask.status !== task.status ||
    state.processingTask.progress !== task.progress ||
    state.processingTask.current_step !== task.current_step;

  // Update the task status area
  $("#task-status-area").removeClass("d-none");
  $("#task-name").text(task.name || "Theme Processing");

  // Status text with animation for changes
  if (taskChanged && state.processingTask && state.processingTask.status !== task.status) {
    $("#task-status").addClass("status-changed");
    setTimeout(() => $("#task-status").removeClass("status-changed"), 1000);
  }
  $("#task-status").text(task.status);

  // Update status badge
  const statusBadge = $("#task-status-badge");
  statusBadge.removeClass("badge-secondary badge-info badge-warning badge-success badge-danger");

  switch (task.status) {
    case "pending":
      statusBadge.addClass("badge-secondary").html('<i class="fas fa-clock mr-1"></i> Pending');
      break;
    case "in_progress":
      statusBadge.addClass("badge-info").html('<i class="fas fa-spinner fa-spin mr-1"></i> In Progress');
      break;
    case "paused":
      statusBadge.addClass("badge-warning").html('<i class="fas fa-pause mr-1"></i> Paused');
      break;
    case "completed":
      statusBadge.addClass("badge-success").html('<i class="fas fa-check mr-1"></i> Completed');
      break;
    case "failed":
      statusBadge.addClass("badge-danger").html('<i class="fas fa-times mr-1"></i> Failed');
      break;
    default:
      statusBadge.addClass("badge-secondary").text(task.status);
  }

  // Show message if available
  if (task.message && (!state.processingTask || task.message !== state.processingTask.message)) {
    addLogMessage(task.message);
  }

  // Calculate and update progress based on task data
  let progress = 0;
  let stepName = "";

  if (task.current_step !== null && task.current_step !== undefined) {
    // Map steps to percentages for the progress bar
    const stepPercentages = {
      0: 25, // Reading files
      1: 50, // Chunking
      2: 75, // Embedding
      3: 100, // Finalizing
    };

    // Map steps to names
    const stepNames = {
      0: "Reading Files",
      1: "Chunking Text",
      2: "Generating Embeddings",
      3: "Finalizing",
    };

    // Get step name
    stepName = stepNames[task.current_step] || "Processing";

    // Calculate progress based on step and individual progress
    const baseProgress = stepPercentages[task.current_step - 1] || 0;
    const nextStepProgress = stepPercentages[task.current_step] || 100;
    const stepRange = nextStepProgress - baseProgress;

    // Calculate final progress as base + percentage through current step
    progress = baseProgress + stepRange * (task.progress / 100);
  } else if (task.progress !== undefined) {
    // If no current_step but progress is available, use it directly
    progress = task.progress;
  }

  // Update progress bars with smooth animation
  const progressBar = $("#process-progress");
  const taskProgressBar = $("#task-progress-bar");

  // Only animate if progress has changed
  if (!state.processingTask || progress !== state.processingTask.progress) {
    // Add transition class for smooth animation
    progressBar.addClass("progress-bar-animated");
    taskProgressBar.addClass("progress-bar-animated");

    // Update progress values
    progressBar.css("width", `${progress}%`).attr("aria-valuenow", progress);
    taskProgressBar.css("width", `${progress}%`).attr("aria-valuenow", progress);

    // Update progress text with step name
    if (stepName) {
      $("#task-progress-text").text(`${stepName}: ${Math.round(progress)}%`);
    } else {
      $("#task-progress-text").text(`${Math.round(progress)}%`);
    }

    // Remove animation class after transition
    setTimeout(() => {
      progressBar.removeClass("progress-bar-animated");
      taskProgressBar.removeClass("progress-bar-animated");
    }, 1000);
  }

  // Toggle action buttons based on status
  $("#cancel-task-btn").toggle(["pending", "in_progress", "paused"].includes(task.status));
  $("#resume-task-btn").toggle(task.status === "paused");
  $("#start-process-btn").toggle(task.status === "completed" || task.status === "failed");

  // Handle error messages
  if (task.error_message) {
    // Only show error if it's new
    if (!state.processingTask || task.error_message !== state.processingTask.error_message) {
      $("#task-error-message").removeClass("d-none").text(task.error_message);
      addLogMessage(`Error: ${task.error_message}`, "error");
    }
  } else {
    $("#task-error-message").addClass("d-none").text("");
  }

  // Update task completion info
  if (task.status === "completed" && (!state.processingTask || state.processingTask.status !== "completed")) {
    // Task just completed - show completion information
    $("#task-completion-info").removeClass("d-none").html(`<div class="alert alert-success">
        <i class="fas fa-check-circle mr-2"></i>
        Processing completed successfully at ${new Date().toLocaleTimeString()}
      </div>`);

    // Add completion message to log
    addLogMessage("Processing completed successfully!", "success");

    // Enable the finish button
    $("#finish-btn").prop("disabled", false).removeClass("btn-secondary").addClass("btn-primary");

    // Maybe play a sound notification
    if (window.Audio && state.userPreferences?.enableSounds) {
      const completeSound = new Audio("/static/sounds/complete.mp3");
      completeSound.play().catch((e) => console.log("Could not play completion sound"));
    }
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
 * Enhanced log message function with message types
 * @param {string} message - The message to add to the log
 * @param {string} type - Message type (info, success, warning, error)
 */
export function addLogMessage(message, type = "info") {
  const timestamp = new Date().toLocaleTimeString();

  // Format the message based on type
  let icon, messageClass;
  switch (type) {
    case "success":
      icon = "fa-check-circle text-success";
      messageClass = "log-success";
      break;
    case "warning":
      icon = "fa-exclamation-triangle text-warning";
      messageClass = "log-warning";
      break;
    case "error":
      icon = "fa-times-circle text-danger";
      messageClass = "log-error";
      break;
    default: // info
      icon = "fa-info-circle text-info";
      messageClass = "log-info";
  }

  const formattedMessage = `[${timestamp}] ${message}`;

  // Add to state
  state.processingLogs = state.processingLogs || [];
  state.processingLogs.push({
    text: formattedMessage,
    type: type,
    timestamp: new Date().toISOString(),
  });

  // Limit log size to prevent memory issues
  if (state.processingLogs.length > 100) {
    state.processingLogs = state.processingLogs.slice(-100);
  }

  // Create log entry HTML
  const logEntry = `
    <div class="log-entry ${messageClass} animate-new-log">
      <i class="fas ${icon} mr-1"></i>
      <span>${formattedMessage}</span>
    </div>
  `;

  // Add to DOM
  $("#process-log-content").append(logEntry);

  // Show log container if it was hidden
  $("#process-log-container").removeClass("d-none");

  // Auto-scroll to bottom of log
  const logContainer = document.getElementById("process-log-content");
  if (logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  // Remove animation class after animation completes
  setTimeout(() => {
    $(".animate-new-log").removeClass("animate-new-log");
  }, 1000);

  // Log to console for better debugging
  console.log(`[${type.toUpperCase()}] ${message}`);

  // Save state
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
  $("#upload-next-btn").on("click", () => {
    navigateToStep(3); // switch to the “Process” screen
    startFileProcessing(); // fire the backend job immediately
  });
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
