/**
 * theme.js
 * Handles theme creation, selection, deletion and other theme-related operations
 */

// Import state and utilities
import { state, saveWorkflowState } from "./state.js";
import { getCsrfToken } from "./utils.js";
import { navigateToStep, updateTaskUI } from "./ui.js";
import { subscribeToThemeUpdates } from "./websocket.js";

/**
 * Handle theme creation form submission
 */
export function handleThemeFormSubmit(e) {
  e.preventDefault();

  const themeData = {
    name: $("#theme-name").val(),
    description: $("#theme-description").val(),
    is_public: $("#theme-public").is(":checked"),
  };

  // Create theme via API
  $.ajax({
    url: "/api/themes",
    method: "POST",
    data: JSON.stringify(themeData),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      alertify.success(`Theme "${themeData.name}" created successfully`);

      // Store the newly created theme ID in the state
      state.currentThemeId = response.id;
      state.selectedTheme = response.name;

      // Update the UI to show the selected theme
      $("#selected-theme-name").text(response.name);

      // Create an initial processing task for this theme
      createInitialThemeTask(response.id);

      // Subscribe to updates for this theme
      if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
        subscribeToThemeUpdates(response.id);
      }

      loadThemes();
      $("#create-theme-form")[0].reset();
    },
    error: function (xhr, status, error) {
      console.error("Error creating theme:", error);
      alertify.error(`Error creating theme: ${xhr.responseJSON?.detail || error}`);
    },
  });
}

/**
 * Create an initial task for a newly created theme
 */
function createInitialThemeTask(themeId) {
  if (!themeId) return;

  const uploadedFileIds = state.uploadedFiles.map((f) => f.id);

  const taskData = {
    type: "theme_processing",
    theme_id: themeId,
    description: `Initial processing task for theme ${themeId}`,
    step: "upload",
    files: uploadedFileIds,
    current_step: 0,
    setps: 4,
    metadata: {
      vectorDBStatus: {
        dataIngestion: "pending",
        textChunking: "pending",
        generateEmbeddings: "pending",
        storeVectors: "pending",
      },
      files: uploadedFileIds,
    },
  };

  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify(taskData),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (taskResponse) {
      console.log("Initial theme task created:", taskResponse);

      // Store the task in our state
      state.processingTask = taskResponse;

      // Update the UI to reflect the task
      updateTaskUI(taskResponse);

      // Save to workflow state
      saveWorkflowState();
    },
    error: function (xhr, status, error) {
      console.error("Error creating initial task:", error);
      alertify.error(`Error initializing theme process: ${xhr.responseJSON?.detail || error}`);
    },
  });
}

/**
 * Load themes from the API
 */
export function loadThemes() {
  // Show the loading spinner
  $("#themes-loader").removeClass("d-none");

  $.ajax({
    url: "/api/themes",
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (themes) {
      renderThemes(themes);
    },
    error: function (xhr, status, error) {
      console.error("Error loading themes:", error);
      alertify.error(`Error loading themes: ${xhr.responseJSON?.detail || error}`);
    },
    complete: function () {
      // Always hide the loading spinner
      $("#themes-loader").addClass("d-none");
    },
  });
}

/**
 * Render themes to the table
 */
function renderThemes(themes) {
  const tableBody = $("#themes-table tbody");
  tableBody.empty();

  if (themes.length === 0) {
    tableBody.html(`<tr><td colspan="5" class="text-center">No themes found. Create your first theme!</td></tr>`);
    return;
  }

  themes.forEach((theme) => {
    const row = `
      <tr>
        <td>${theme.name}</td>
        <td>${theme.description || "-"}</td>
        <td><span class="badge badge-info">${theme.document_count || 0}</span></td>
        <td>${
          theme.is_public
            ? '<span class="badge badge-success">Public</span>'
            : '<span class="badge badge-secondary">Private</span>'
        }</td>
        <td>
          <button class="btn btn-sm btn-primary select-theme-btn" data-theme-id="${theme.id}" data-theme-name="${
      theme.name
    }">
            <i class="fas fa-folder-open"></i> Select
          </button>
          <button class="btn btn-sm btn-danger delete-theme-btn" data-theme-id="${theme.id}">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
    tableBody.append(row);
  });

  // Add event listeners to the new buttons
  $(".select-theme-btn").on("click", function () {
    const themeId = $(this).data("theme-id");
    const themeName = $(this).data("theme-name");
    selectTheme(themeId, themeName);
  });

  $(".delete-theme-btn").on("click", function () {
    const themeId = $(this).data("theme-id");
    deleteTheme(themeId);
  });
}

/**
 * Select a theme and proceed to file upload
 */
/**
 * Select a theme and proceed to file upload
 */
import { resetThemeState } from "./state.js";
import { updateVectorDBStatusUI, restoreDropZoneFiles } from "./ui.js";
import { fetchAllThemeFiles } from "./ui.js";

export function selectTheme(themeId, themeName) {
  // 1. Clear previous theme state before switching
  resetThemeState();

  // 2. Set new theme
  state.currentThemeId = themeId;
  state.selectedTheme = themeName;

  $("#selected-theme-name").text(themeName);

  // 3. Fetch tasks for this theme
  $.ajax({
    url: `/api/tasks?theme_id=${themeId}`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (tasks) {
      if (tasks && tasks.length > 0) {
        const activeTasks = tasks.filter(
          (t) =>
            (t.status === "in_progress" || t.status === "pending" || t.status === "completed") &&
            t.type === "theme_processing"
        );

        if (activeTasks.length > 0) {
          activeTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          const activeTask = activeTasks[0];

          state.processingTask = activeTask;
          updateTaskUI(activeTask);

          // 🛠 Restore vectorDB status if present
          if (activeTask.metadata && activeTask.metadata.vectorDBStatus) {
            state.vectorDBStatus = activeTask.metadata.vectorDBStatus;
            updateVectorDBStatusUI();
          }

          // 🛠 Restore uploaded files if files array exists in metadata
          if (activeTask.metadata && activeTask.metadata.files && activeTask.metadata.files.length > 0) {
            // Optionally re-fetch files from server to get file details
            fetchAllThemeFiles(themeId);
          }

          // 🛠 Restore logs if they exist
          if (activeTask.logs && activeTask.logs.length > 0) {
            state.processingLogs = activeTask.logs;

            $("#process-log-content").empty();
            state.processingLogs.forEach((log) => {
              const { text, type } = log;
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

              const logEntry = `
      <div class="log-entry ${messageClass}">
        <i class="fas ${icon} mr-1"></i>
        <span>${text}</span>
      </div>
    `;

              $("#process-log-content").append(logEntry);
            });

            $("#process-log-container").removeClass("d-none");
          }

          // 🛠 Restore dropzone files if needed (optional)
          if (state.dropZoneFiles.length > 0) {
            restoreDropZoneFiles();
          }

          // 🛠 Restore current step navigation based on task progress
          if (activeTask.current_step != null) {
            const stepMapping = {
              0: 2,
              1: 3,
              2: 3,
              3: 3,
            };
            const targetStep = stepMapping[activeTask.current_step] || 2;
            navigateToStep(targetStep);
            return;
          }
        }
      }

      // No active task found: fallback
      navigateToStep(2);

      if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
        subscribeToThemeUpdates(themeId);
      }
    },
    error: function (xhr, status, error) {
      console.error("Error checking tasks:", error);
      navigateToStep(2);
    },
  });
}

/**
 * Delete a theme
 */
export function deleteTheme(themeId) {
  if (confirm("Are you sure you want to delete this theme? This action cannot be undone.")) {
    $.ajax({
      url: `/api/themes/${themeId}`,
      method: "DELETE",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function () {
        alertify.success("Theme deleted successfully");

        // Clear theme-specific state
        state.currentThemeId = null;
        state.selectedTheme = null;
        state.uploadedFiles = [];
        state.processingTask = null;
        saveWorkflowState();

        // Clear the Dropzone files if it exists
        if (state.dropzone) {
          state.dropzone.removeAllFiles(true);
        }

        // Update UI
        $("#selected-theme-name").text("No theme selected");
        $("#upload-next-btn").prop("disabled", true);

        loadThemes();
      },
      error: function (xhr, status, error) {
        console.error("Error deleting theme:", error);
        alertify.error(`Error deleting theme: ${xhr.responseJSON?.detail || error}`);
      },
    });
  }
}

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
