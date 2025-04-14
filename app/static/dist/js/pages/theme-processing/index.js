import { initDropzone, disableDropzoneAutoDiscover } from "./dropzone.js";
import { loadThemes } from "./theme.js";
import { setupEventListeners } from "./ui.js";
import { restoreWorkflowState } from "./ui.js";
import { navigateToStep } from "./ui.js";
import { initializeWebSocketConnection } from "./websocket.js";
import { checkForActiveTasks } from "./task.js";
import { initFileUpload } from "./file-upload.js";

$(document).ready(() => {
  console.log("Theme Processor Initialized");
  Dropzone.autoDiscover = false;
  // Disable Dropzone auto-discovery before anything else
  disableDropzoneAutoDiscover();
  setupEventListeners();
  // Initialize WebSocket connection for real-time updates
  initializeWebSocketConnection();
  initDropzone();

  loadThemes();

  // Initialize file upload functionality
  initFileUpload();

  // Try to restore saved workflow state
  const stateRestored = restoreWorkflowState();

  if (!stateRestored) {
    // If we couldn't restore state, start from the beginning
    navigateToStep(1);
  }

  // Check for active tasks for the current theme (if any)
  // Check for active tasks
  if (state.currentThemeId) {
    checkForActiveTasks();
  }
  console.log("RAG Pipeline UI initialized");
});
