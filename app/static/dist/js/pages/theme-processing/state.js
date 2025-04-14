/**
 * state.js
 * Central state management for theme processing application
 */

// Global state object that's shared across modules
export const state = {
  currentStep: 1,
  selectedTheme: null,
  uploadedFiles: [],
  downloadedFiles: [],
  processedFiles: [],
  currentThemeId: null,
  processingTask: null,
  taskSocket: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 3000,
  dropzone: null,
  vectorDBStatus: {
    dataIngestion: "pending",
    textChunking: "pending",
    generateEmbeddings: "pending",
    storeVectors: "pending",
  },
  vectorDBProgress: 0,
  processingLogs: [],
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
  state.vectorDBProgress = 0;
  state.processingLogs = [];
  state.vectorDBStatus = {
    dataIngestion: "pending",
    textChunking: "pending",
    generateEmbeddings: "pending",
    storeVectors: "pending",
  };
}

/**
 * Save current state to local storage for persistence
 * This can be useful for restoring state after page reloads
 */
export function saveStateToStorage() {
  // Create a copy without circular references or large objects
  const stateToPersist = {
    currentStep: state.currentStep,
    selectedTheme: state.selectedTheme,
    currentThemeId: state.currentThemeId,
    uploadedFiles: state.uploadedFiles.map((file) => ({
      id: file.id,
      title: file.title,
      filename: file.filename,
      source: file.source,
      size: file.size,
    })),
    downloadedFiles: state.downloadedFiles.map((file) => ({
      id: file.id,
      title: file.title,
      filename: file.filename,
      source: file.source,
      size: file.size,
    })),
    processedFiles: state.processedFiles.map((file) => ({
      id: file.id,
      title: file.title,
      filename: file.filename,
      source: file.source,
      size: file.size,
    })),
    vectorDBStatus: state.vectorDBStatus,
    processingTask: state.processingTask
      ? {
          id: state.processingTask.id,
          status: state.processingTask.status,
          current_step: state.processingTask.current_step,
          progress: state.processingTask.progress,
        }
      : null,
  };

  try {
    localStorage.setItem("themeProcessingState", JSON.stringify(stateToPersist));
  } catch (error) {
    console.error("Error saving state to local storage:", error);
  }
}

/**
 * Load state from local storage
 * @returns {boolean} True if state was loaded successfully, false otherwise
 */
export function loadStateFromStorage() {
  try {
    const savedState = localStorage.getItem("themeProcessingState");
    if (!savedState) return false;

    const parsedState = JSON.parse(savedState);

    // Restore values to the state object
    Object.keys(parsedState).forEach((key) => {
      state[key] = parsedState[key];
    });

    return true;
  } catch (error) {
    console.error("Error loading state from local storage:", error);
    return false;
  }
}
