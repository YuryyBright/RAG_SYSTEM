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
export function refreshTaskStatus(taskId) {
  if (!taskId) return;
  $.ajax({
    url: `/api/tasks/${taskId}`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (task) {
      state.processingTask = task;
      updateTaskUI(task);

      if (task.metadata && task.metadata.vectorDBStatus) {
        state.vectorDBStatus = task.metadata.vectorDBStatus;
        updateVectorDBStatusUI();
      }

      if (task.logs && task.logs.length > 0) {
        const existingLogs = new Set(state.processingLogs || []);
        const newLogs = task.logs.filter((log) => !existingLogs.has(log));
        newLogs.forEach((log) => {
          $("#process-log-content").append(`<div>> ${log}</div>`);
          state.processingLogs.push(log);
        });

        const logContainer = $("#process-log-content").parent();
        logContainer.scrollTop(logContainer[0].scrollHeight);
      }
    },
    error: function (xhr, status, error) {
      console.error("Failed to refresh task status:", error);
    },
  });
}

import { updateVectorDBStatusUI } from "./vectorDB.js";
