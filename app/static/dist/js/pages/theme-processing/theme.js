/**
 * theme.js
 * Handles theme creation, selection, deletion and other theme-related operations
 */

// Import state and utilities
import { state } from "./state.js";
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
export function selectTheme(themeId, themeName) {
  state.currentThemeId = themeId;
  state.selectedTheme = themeName;

  $("#selected-theme-name").text(themeName);

  // Check if there's already a processing task for this theme
  $.ajax({
    url: `/api/tasks?theme_id=${themeId}`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (tasks) {
      if (tasks && tasks.length > 0) {
        // Filter for active tasks (pending or in progress)
        const activeTasks = tasks.filter(
          (t) => (t.status === "in_progress" || t.status === "pending") && t.type === "theme_processing"
        );

        if (activeTasks.length > 0) {
          // Sort by most recently created
          activeTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

          // Get the first (most recent) task
          const activeTask = activeTasks[0];

          // Set as our current processing task
          state.processingTask = activeTask;

          // Update UI based on task status
          updateTaskUI(activeTask);

          // Update vector DB status if exists in task metadata
          if (activeTask.metadata && activeTask.metadata.vectorDBStatus) {
            state.vectorDBStatus = activeTask.metadata.vectorDBStatus;
            updateVectorDBStatusUI();
          }

          // Determine which step to show based on the task's current step
          if (activeTask.current_step != null) {
            const stepMapping = {
              0: 2, // Data Ingestion -> Upload Files
              1: 3, // Text Chunking -> Download Files
              2: 4, // Generate Embeddings -> Read Files
              3: 5, // Store Vectors -> Process Embeddings
            };

            // Navigate to the appropriate step
            const targetStep = stepMapping[activeTask.current_step] || 2;
            navigateToStep(targetStep);
            return; // Skip the default navigation
          }
        }
      }

      // If no active task was found, proceed to upload section
      navigateToStep(2);

      // Subscribe to updates for this theme
      if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
        subscribeToThemeUpdates(themeId);
      }
    },
    error: function (xhr, status, error) {
      console.error("Error checking tasks:", error);
      // If error, still navigate to upload section
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

// Import ui-related functions
import { updateVectorDBStatusUI } from "./ui.js";
