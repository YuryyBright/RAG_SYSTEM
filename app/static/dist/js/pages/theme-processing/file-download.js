/**
 * file-download.js
 * Handles functions related to downloading files for theme processing
 */

import { state } from "./state.js";
import { addProcessingLog, getCsrfToken } from "./utils.js";
import { updateVectorDBStatusUI } from "./vectorDB.js";
import { populateFileSelector } from "./file-preview.js";

/**
 * Start the file download process
 */
export function startDownloadProcess() {
  if (state.uploadedFiles.length === 0) {
    alertify.error("No files to download");
    return;
  }

  $("#start-download-btn").prop("disabled", true);

  // Create a new task for file download process
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "download",
      files: state.uploadedFiles.map((f) => f.id),
      description: `Download files for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "download",
        vectorDBStatus: state.vectorDBStatus,
        totalFiles: state.uploadedFiles.length,
      },
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (response) {
      // Store the task reference
      state.processingTask = response;

      // The real updates will come via WebSocket
      alertify.success("Started download process");

      // Initialize file download UI
      $("#download-progress").css("width", "0%");
      state.downloadedFiles = [];

      // Add log entry
      addProcessingLog("Starting file download process...");

      // Set first step to in_progress
      state.vectorDBStatus.dataIngestion = "in_progress";
      updateVectorDBStatusUI();
    },
    error: function (xhr, status, error) {
      console.error("Error starting download process:", error);
      alertify.error(`Error starting download: ${xhr.responseJSON?.detail || error}`);
      $("#start-download-btn").prop("disabled", false);
    },
  });

  // Traditional UI update for backward compatibility
  const totalFiles = state.uploadedFiles.length;
  let downloadedCount = 0;

  // Simulate downloading each file (in a real app this would be an API call)
  state.uploadedFiles.forEach((file, index) => {
    const rowElement = $(`#files-table tbody tr[data-file-id="${file.id}"]`);
    rowElement.find("td:last-child span").removeClass("badge-secondary").addClass("badge-warning").text("Downloading");

    // Simulate API request to download the file
    setTimeout(() => {
      // Mark as downloaded
      rowElement.find("td:last-child span").removeClass("badge-warning").addClass("badge-success").text("Downloaded");
      downloadedCount++;

      // Add to downloaded files
      state.downloadedFiles.push(file);

      // Update progress
      const progress = Math.round((downloadedCount / totalFiles) * 100);
      $("#download-progress").css("width", `${progress}%`);

      // Add log entry
      addProcessingLog(`Downloaded file: ${file.filename || file.title || "Unknown file"}`);

      // Check if all files are downloaded
      if (downloadedCount === totalFiles) {
        alertify.success("All files downloaded successfully");
        $("#download-next-btn").removeClass("d-none");

        // Update vector DB status
        state.vectorDBStatus.dataIngestion = "completed";
        updateVectorDBStatusUI();

        // Add log entry
        addProcessingLog("All files downloaded successfully!");

        // Populate file selector for reading step
        populateFileSelector();
      }
    }, 1000 + index * 500); // Staggered timing for visual effect
  });
}

/**
 * Load files table in the download section
 */
export function loadFilesTable() {
  if (state.currentThemeId) {
    $.ajax({
      url: `/api/themes/${state.currentThemeId}/documents`,
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
