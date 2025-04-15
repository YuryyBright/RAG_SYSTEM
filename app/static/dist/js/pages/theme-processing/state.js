/**
 * ui-state.js
 * Integrated UI navigation, updates and state management for theme processing workflow
 */
import { updateVectorDBStatusUI } from "./vectorDB.js";
import { navigateToStep, updateTaskUI } from "./ui.js";
// Global state object that's shared across modules
export const state = {
  // Current workflow step (1-5)
  currentStep: 1,

  // Theme-related state
  currentThemeId: null,
  selectedTheme: "",

  // File-related state
  uploadedFiles: [], // Files uploaded to the theme
  downloadedFiles: [], // Files downloaded from the server
  processedFiles: [], // Files that have been processed
  dropZoneFiles: [], // Files currently shown in the drop zone

  // Task-related state
  processingTask: null,
  processingLogs: [],

  // WebSocket-related state
  taskSocket: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 2000,
  pendingSubscription: null,
  subscribedThemeId: null,

  // Vector DB status
  vectorDBStatus: {
    dataIngestion: "pending",
    textChunking: "pending",
    generateEmbeddings: "pending",
    storeVectors: "pending",
  },
};

/**
 * Reset state to initial values
 * Use this when starting a new workflow or clearing data
 */
export function resetState() {
  state.currentStep = 1;
  state.uploadedFiles = [];
  state.downloadedFiles = [];
  state.processedFiles = [];
  state.processingTask = null;
  state.reconnectAttempts = 0;
  state.processingLogs = [];
  state.dropZoneFiles = [];
  state.vectorDBStatus = {
    dataIngestion: "pending",
    textChunking: "pending",
    generateEmbeddings: "pending",
    storeVectors: "pending",
  };
}

/**
 * Save current workflow state to localStorage
 */
export function saveWorkflowState() {
  // Create a copy of state without circular references or large objects
  const stateToPersist = {
    currentStep: state.currentStep,
    currentThemeId: state.currentThemeId,
    selectedTheme: state.selectedTheme,
    processingTask: state.processingTask
      ? {
          id: state.processingTask.id,
          status: state.processingTask.status,
          current_step: state.processingTask.current_step,
          progress: state.processingTask.progress,
          name: state.processingTask.name,
          error_message: state.processingTask.error_message,
        }
      : null,
    vectorDBStatus: state.vectorDBStatus,
    processingLogs: state.processingLogs,

    // Save only the necessary data from files
    uploadedFiles: state.uploadedFiles.map((file) => ({
      id: file.id,
      title: file.title || file.filename || file.source || "Unknown file",
      filename: file.filename || file.title || file.source || "Unknown file",
      source: file.source || "",
      size: file.size || 0,
      type: file.type || file.mime_type || "application/octet-stream",
    })),

    // Remove the actual File objects from dropZoneFiles
    dropZoneFiles: (state.dropZoneFiles || []).map((file) => ({
      name: file.name,
      size: file.size,
      id: file.id || "",
      // Don't save the actual file object
    })),
  };

  try {
    localStorage.setItem("workflowState", JSON.stringify(stateToPersist));
    // console.log("Workflow state saved successfully");
  } catch (e) {
    // Handle potential localStorage quota errors
    console.error("Failed to save workflow state:", e);

    if (e.name === "QuotaExceededError" || e.toString().includes("exceeded")) {
      console.warn("LocalStorage quota exceeded. Saving minimal state.");
      // Save minimal state without large objects
      const minimalState = {
        currentStep: state.currentStep,
        currentThemeId: state.currentThemeId,
        selectedTheme: state.selectedTheme,
        // Just save IDs of uploaded files
        uploadedFileIds: state.uploadedFiles.map((file) => file.id),
      };
      try {
        localStorage.setItem("workflowState", JSON.stringify(minimalState));
      } catch (e2) {
        console.error("Failed to save even minimal state:", e2);
        alertify.error("Unable to save your progress locally. Files may not persist if you leave this page.");
      }
    }
  }
}

/**
 * Restore workflow state from localStorage
 * @returns {boolean} True if state was loaded successfully, false otherwise
 */
export function restoreWorkflowState() {
  try {
    const savedState = localStorage.getItem("workflowState");
    console.log("Retrieved state from localStorage:", savedState);
    if (!savedState) return false;

    const parsedState = JSON.parse(savedState);

    // Restore theme information
    if (parsedState.currentThemeId) {
      state.currentThemeId = parsedState.currentThemeId;
      state.selectedTheme = parsedState.selectedTheme;
      $("#selected-theme-name").text(parsedState.selectedTheme || "");
    }

    // Restore task information if available
    if (parsedState.processingTask) {
      state.processingTask = parsedState.processingTask;
      updateTaskUI(parsedState.processingTask);
    }

    // Restore vector DB status if available
    if (parsedState.vectorDBStatus) {
      state.vectorDBStatus = parsedState.vectorDBStatus;
      updateVectorDBStatusUI();
    }

    // Restore logs if available
    if (parsedState.processingLogs && parsedState.processingLogs.length > 0) {
      state.processingLogs = parsedState.processingLogs;
      $("#process-log-content").empty();
      state.processingLogs.forEach((log) => {
        $("#process-log-content").append(`<div>> ${log}</div>`);
      });
    }

    // Restore uploaded files if available
    if (parsedState.uploadedFiles && parsedState.uploadedFiles.length > 0) {
      state.uploadedFiles = parsedState.uploadedFiles;
      // Enable the next button if there are files
      $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
    } else if (parsedState.uploadedFileIds && parsedState.uploadedFileIds.length > 0 && parsedState.currentThemeId) {
      // If we only have file IDs, fetch the full file data
      fetchFileDataFromIds(parsedState.currentThemeId, parsedState.uploadedFileIds);
    }

    // Restore dropZoneFiles if available
    if (parsedState.dropZoneFiles && parsedState.dropZoneFiles.length > 0) {
      state.dropZoneFiles = parsedState.dropZoneFiles;
      restoreDropZoneFiles();
    }

    // Navigate to the saved step (if there is one)
    if (parsedState.currentStep) {
      navigateToStep(parsedState.currentStep, false);
      return true;
    }
    console.log("Workflow state restored successfully:", parsedState);
    return true;
  } catch (error) {
    console.error("Error restoring workflow state:", error);
    return false;
  }
}
