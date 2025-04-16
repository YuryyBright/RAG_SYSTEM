/**
 * file-download.js
 * Handles functions related to downloading multiple files for theme processing
 */

import { state } from "./state.js";
import { addProcessingLog, getCsrfToken } from "./utils.js";
import { updateVectorDBStatusUI } from "./vectorDB.js";
import { populateFileSelector } from "./file-preview.js";
import { startFileProcessing } from "./file-processing.js";
import { saveWorkflowState } from "./state.js";
import { navigateToStep } from "./ui.js";
/**
 * Configuration options for parallel downloads
 */
const DOWNLOAD_CONFIG = {
  maxConcurrentDownloads: 3, // Maximum number of concurrent downloads
  retryAttempts: 2, // Number of retry attempts for failed downloads
  retryDelay: 1000, // Delay between retry attempts (ms)
};

/**
 * Start the file download process with parallel downloads
 */
// export function startDownloadProcess() {
//   if (state.uploadedFiles.length === 0) {
//     alertify.error("No files to download");
//     return;
//   }

//   $("#start-download-btn").prop("disabled", true);

//   // Initialize download tracking state
//   state.downloadStatus = {
//     totalFiles: state.uploadedFiles.length,
//     completedFiles: 0,
//     failedFiles: 0,
//     inProgressFiles: 0,
//     queue: [...state.uploadedFiles],
//     activeDownloads: new Map(),
//     retryMap: new Map()
//   };

//   // Reset download array
//   state.downloadedFiles = [];

//   // Create a new task for file download process
//   $.ajax({
//     url: "/api/tasks",
//     method: "POST",
//     data: JSON.stringify({
//       type: "theme_processing",
//       theme_id: state.currentThemeId,
//       step: "download",
//       files: state.uploadedFiles.map((f) => f.id),
//       description: `Download files for theme: ${state.selectedTheme}`,
//       metadata: {
//         stepName: "download",
//         vectorDBStatus: state.vectorDBStatus,
//         totalFiles: state.uploadedFiles.length,
//         parallelDownloads: true
//       },
//     }),
//     contentType: "application/json",
//     headers: {
//       "X-CSRF-Token": getCsrfToken(),
//     },
//     success: function (response) {
//       // Store the task reference
//       state.processingTask = response;

//       // Initialize file download UI
//       $("#download-progress").css("width", "0%");

//       // Add log entry
//       addProcessingLog("Starting parallel file download process...");

//       // Set first step to in_progress
//       state.vectorDBStatus.dataIngestion = "in_progress";
//       updateVectorDBStatusUI();

//       // Start the parallel download process
//       processDownloadQueue();

//       alertify.success("Started download process");
//     },
//     error: function (xhr, status, error) {
//       console.error("Error starting download process:", error);
//       alertify.error(`Error starting download: ${xhr.responseJSON?.detail || error}`);
//       $("#start-download-btn").prop("disabled", false);
//     },
//   });
// }
/**
 * Start the download process and immediately jump to processing
 */
export function startDownloadProcess() {
  // Change button text to indicate processing is starting
  $("#start-download-btn").text("Starting Processing Files").prop("disabled", true);
  if (!state.currentThemeId) {
    alertify.error("No theme selected");
    $("#start-download-btn").text("Start Download").prop("disabled", false);
    return;
  }

  // Create a task for tracking
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
      "Content-Type": "application/json",
    },
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "download",
      description: `Processing theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "download",
      },
    }),
    success: function (task) {
      state.processingTask = task;
      saveWorkflowState();

      // Skip directly to step 5 (processing)
      navigateToStep(5);

      // Mark download and read steps as completed in the background
      state.downloadStatus = "completed";
      state.vectorDBStatus.dataIngestion = "completed";

      // Start file processing immediately
      startFileProcessing();
    },
    error: function (xhr, status, error) {
      alertify.error("Failed to create task: " + (xhr.responseJSON?.detail || error));
      $("#start-download-btn").text("Start Download").prop("disabled", false);
    },
  });
}
/**
 * Process the download queue and manage parallel downloads
 */
function processDownloadQueue() {
  const status = state.downloadStatus;

  // Check if we're done with all downloads
  if (status.completedFiles + status.failedFiles === status.totalFiles) {
    finishDownloadProcess();
    return;
  }

  // Start new downloads if we haven't reached the max concurrent limit
  while (status.inProgressFiles < DOWNLOAD_CONFIG.maxConcurrentDownloads && status.queue.length > 0) {
    const file = status.queue.shift();
    downloadFile(file);
    status.inProgressFiles++;
  }
}

/**
 * Download an individual file
 * @param {Object} file - The file object to download
 */
function downloadFile(file) {
  const rowElement = $(`#files-table tbody tr[data-file-id="${file.id}"]`);
  rowElement.find("td:last-child span").removeClass("badge-secondary").addClass("badge-warning").text("Downloading");

  // Track the start of this download
  state.downloadStatus.activeDownloads.set(file.id, {
    startTime: Date.now(),
    file: file,
  });

  // Simulate API call to download the file (in a real system, this would be an actual XHR request)
  const downloadPromise = new Promise((resolve, reject) => {
    // Simulate server download request with some randomness for realism
    setTimeout(() => {
      // 90% success rate for demonstration
      if (Math.random() > 0.1) {
        resolve(file);
      } else {
        reject(new Error("Network error during download"));
      }
    }, 1000 + Math.random() * 2000); // Random time between 1-3 seconds
  });

  downloadPromise
    .then((file) => {
      handleSuccessfulDownload(file);
    })
    .catch((error) => {
      handleFailedDownload(file, error);
    })
    .finally(() => {
      // Remove from active downloads
      state.downloadStatus.activeDownloads.delete(file.id);
      state.downloadStatus.inProgressFiles--;

      // Continue processing queue
      processDownloadQueue();
    });
}

/**
 * Handle a successful file download
 * @param {Object} file - The successfully downloaded file
 */
function handleSuccessfulDownload(file) {
  const status = state.downloadStatus;
  const rowElement = $(`#files-table tbody tr[data-file-id="${file.id}"]`);

  // Mark as downloaded in UI
  rowElement.find("td:last-child span").removeClass("badge-warning").addClass("badge-success").text("Downloaded");

  // Update state
  status.completedFiles++;
  state.downloadedFiles.push(file);

  // Update progress
  const progress = Math.round(((status.completedFiles + status.failedFiles) / status.totalFiles) * 100);
  $("#download-progress").css("width", `${progress}%`);

  // Add log entry
  addProcessingLog(`Downloaded file: ${file.filename || file.title || "Unknown file"}`);
}

/**
 * Handle a failed file download with retry logic
 * @param {Object} file - The file that failed to download
 * @param {Error} error - The error that occurred
 */
function handleFailedDownload(file, error) {
  const status = state.downloadStatus;
  const rowElement = $(`#files-table tbody tr[data-file-id="${file.id}"]`);

  // Check if we should retry
  const retryCount = state.downloadStatus.retryMap.get(file.id) || 0;

  if (retryCount < DOWNLOAD_CONFIG.retryAttempts) {
    // Increment retry count
    state.downloadStatus.retryMap.set(file.id, retryCount + 1);

    // Show retry status
    rowElement
      .find("td:last-child span")
      .removeClass("badge-warning")
      .addClass("badge-info")
      .text(`Retry ${retryCount + 1}/${DOWNLOAD_CONFIG.retryAttempts}`);

    addProcessingLog(
      `Retrying download for: ${file.filename || file.title || "Unknown file"} (Attempt ${retryCount + 1})`
    );

    // Wait a bit then add back to queue
    setTimeout(() => {
      status.queue.push(file);
      processDownloadQueue();
    }, DOWNLOAD_CONFIG.retryDelay);
  } else {
    // Mark as failed after retries
    rowElement
      .find("td:last-child span")
      .removeClass("badge-warning badge-info")
      .addClass("badge-danger")
      .text("Failed");

    // Update state
    status.failedFiles++;

    // Update progress
    const progress = Math.round(((status.completedFiles + status.failedFiles) / status.totalFiles) * 100);
    $("#download-progress").css("width", `${progress}%`);

    // Add log entry
    addProcessingLog(`Failed to download file: ${file.filename || file.title || "Unknown file"} - ${error.message}`);
    console.error(`Download failed for file ${file.id}:`, error);
  }
}

/**
 * Finish the download process and update the UI
 */
function finishDownloadProcess() {
  const status = state.downloadStatus;

  // Check if we had any successful downloads
  if (status.completedFiles > 0) {
    // Show completion message with success/failure counts
    if (status.failedFiles > 0) {
      alertify.warning(
        `Download completed with ${status.completedFiles} files successful and ${status.failedFiles} files failed`
      );
    } else {
      alertify.success("All files downloaded successfully");
    }

    // Add log entry
    addProcessingLog(
      `Download process completed: ${status.completedFiles} files successful, ${status.failedFiles} files failed`
    );

    // Show next button
    $("#download-next-btn").removeClass("d-none");

    // Update vector DB status
    state.vectorDBStatus.dataIngestion = status.failedFiles === 0 ? "completed" : "partial";
    updateVectorDBStatusUI();

    // Populate file selector for reading step
    populateFileSelector();
  } else {
    // All downloads failed
    alertify.error("All file downloads failed. Please check your connection and try again.");
    $("#start-download-btn").prop("disabled", false);

    // Add log entry
    addProcessingLog("All file downloads failed. Please retry the download process.");

    // Update vector DB status
    state.vectorDBStatus.dataIngestion = "failed";
    updateVectorDBStatusUI();
  }
}

/**
 * Load files table in the download section
 */
export function loadFilesTable() {
  if (state.currentThemeId) {
    $.ajax({
      url: `/api/themes/${state.currentThemeId}/files`,
      method: "GET",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function (files) {
        renderFilesTable(files);
      },
      error: function (xhr, status, error) {
        console.error("Error loading files:", error);
        alertify.error(`Error loading files: ${xhr.responseJSON?.detail || error}`);
      },
    });
  } else {
    alertify.error("No theme selected");
  }
}

/**
 * Render files to the table
 */
export function renderFilesTable(files) {
  const tableBody = $("#files-table tbody");
  tableBody.empty();

  if (files.length === 0) {
    tableBody.html(`<tr><td colspan="3" class="text-center">No files found in this theme</td></tr>`);
    $("#start-download-btn").prop("disabled", true);
    return;
  }

  files.forEach((file) => {
    const row = `
      <tr data-file-id="${file.id}">
        <td>${file.title || file.filename || file.source || "Unknown"}</td>
        <td>${formatFileSize(file.size || getRandomFileSize())}</td>
        <td><span class="badge badge-secondary">Pending</span></td>
      </tr>
    `;
    tableBody.append(row);
  });

  // Enable the download button
  $("#start-download-btn").prop("disabled", false);

  // Store files for later use
  state.uploadedFiles = files;
}

/**
 * Generate a random file size for demo purposes
 */
function getRandomFileSize() {
  return Math.floor(Math.random() * 10000000) + 50000; // Between 50KB and 10MB
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * Cancel all active downloads and reset the download process
 */
export function cancelDownloads() {
  if (!state.downloadStatus || state.downloadStatus.totalFiles === 0) {
    return;
  }

  // Mark as canceled in UI
  state.downloadStatus.activeDownloads.forEach((downloadInfo, fileId) => {
    const rowElement = $(`#files-table tbody tr[data-file-id="${fileId}"]`);
    rowElement
      .find("td:last-child span")
      .removeClass("badge-warning badge-info")
      .addClass("badge-secondary")
      .text("Canceled");
  });

  // Reset download status
  state.downloadStatus = null;

  // Enable restart
  $("#start-download-btn").prop("disabled", false);

  // Add log entry
  addProcessingLog("Download process canceled by user");

  // Update vector DB status
  state.vectorDBStatus.dataIngestion = "pending";
  updateVectorDBStatusUI();

  alertify.message("Downloads canceled");
}

/**
 * Update state.js to include downloadStatus
 */
// This should be added to state.js
/*
// Add to the state object:
downloadStatus: null, // Will hold download queue and progress information
*/
