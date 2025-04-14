import { initDropzone } from "./dropzone.js";
import { loadThemes } from "./theme.js";
import { setupEventListeners } from "./ui.js";
import { initializeWebSocketConnection } from "./websocket.js";
import { checkForActiveTasks } from "./task.js";

$(document).ready(() => {
  console.log("Theme Processor Initialized");
  Dropzone.autoDiscover = false;

  initDropzone();
  loadThemes();
  setupEventListeners();
  initializeWebSocketConnection();
  checkForActiveTasks();
});
