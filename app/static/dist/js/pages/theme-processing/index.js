import { initDropzone, disableDropzoneAutoDiscover } from "./dropzone.js";
import { loadThemes } from "./theme.js";
import { setupEventListeners } from "./ui.js";
import { initializeWebSocketConnection } from "./websocket.js";
import { checkForActiveTasks } from "./task.js";
import { state } from "./state.js";
// In index.js, modify this part to ensure state restoration works correctly
$(document).ready(() => {
  console.log("Theme Processor Initialized");

  // Disable Dropzone auto-discovery before anything else
  disableDropzoneAutoDiscover();

  setupEventListeners();

  // Initialize WebSocket connection for real-time updates
  initializeWebSocketConnection();
  initDropzone();

  loadThemes();

  // Check for active tasks for the current theme (if any)
  if (state.currentThemeId) {
    checkForActiveTasks();
  }

  console.log("RAG Pipeline UI initialized");
});
