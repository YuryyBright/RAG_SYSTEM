/**
 * utils.js
 * Shared utility functions for the theme processing application
 */

/**
 * Get CSRF token from the authentication manager
 * @returns {string} CSRF token or empty string if not available
 */
export function getCsrfToken() {
  if (typeof AuthManager === "undefined" || !AuthManager.getCsrfToken) {
    console.warn("AuthManager is not defined or getCsrfToken is missing.");
    return "";
  }

  // Assuming AuthManager is a global object with a method to get CSRF token
  return AuthManager.getCsrfToken();
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size with appropriate unit
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * Generate a random file size for demo purposes
 * @returns {number} Random file size between 50KB and 10MB
 */
export function getRandomFileSize() {
  return Math.floor(Math.random() * 10000000) + 50000; // Between 50KB and 10MB
}

/**
 * Add a log entry to the processing log
 * @param {string} message - Log message to display
 */
export function addProcessingLog(message) {
  // Add timestamp
  const now = new Date();
  const timestamp = now.toLocaleTimeString();
  const logEntry = `[${timestamp}] ${message}`;

  // Import state dynamically to avoid circular dependency
  import("./state.js").then(({ state }) => {
    // Add to state for persistence
    state.processingLogs.push(logEntry);

    // Update UI
    const logElement = $("#process-log-content");
    logElement.append(`<div>> ${logEntry}</div>`);

    // Auto-scroll to bottom
    const logContainer = logElement.parent();
    logContainer.scrollTop(logContainer[0].scrollHeight);

    // If we have a task, update its logs
    if (state.processingTask && state.processingTask.id) {
      // In a production app, we might want to batch these updates
      updateTaskLogs(state.processingTask.id, logEntry);
    }
  });
}

/**
 * Update task logs on the server
 * @param {string} taskId - ID of the task to update
 * @param {string} logEntry - Log entry to add to the task
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
