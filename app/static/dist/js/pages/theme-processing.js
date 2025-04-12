/**
 * theme-processing.js
 * Handles the theme and document processing workflow
 */

// Global state
const state = {
  currentStep: 1,
  selectedTheme: null,
  uploadedFiles: [],
  downloadedFiles: [],
  processedFiles: [],
  currentThemeId: null,
};

$(document).ready(function () {
  console.log("Theme Processing initialized");

  // Disable Dropzone auto-discovery before any initialization
  // This should be set before any Dropzone is initialized
  Dropzone.autoDiscover = false;

  // Initialize Dropzone
  initDropzone();

  // Load initial themes
  loadThemes();

  // Setup event listeners
  setupEventListeners();
});

/**
 * Setup event listeners for all UI interactions
 */
function setupEventListeners() {
  // Theme form submission
  $("#create-theme-form").on("submit", handleThemeFormSubmit);

  // Navigation buttons
  $("#upload-back-btn").on("click", () => navigateToStep(1));
  $("#upload-next-btn").on("click", () => navigateToStep(3));
  $("#download-back-btn").on("click", () => navigateToStep(2));
  $("#download-next-btn").on("click", () => navigateToStep(4));
  $("#read-back-btn").on("click", () => navigateToStep(3));
  $("#read-next-btn").on("click", () => navigateToStep(5));
  $("#process-back-btn").on("click", () => navigateToStep(4));
  $("#finish-btn").on("click", showSuccessModal);

  // Process buttons
  $("#start-download-btn").on("click", startDownloadProcess);
  $("#start-read-btn").on("click", startReadProcess);
  $("#start-process-btn").on("click", startEmbeddingProcess);

  // File selector for preview
  $("#file-selector").on("change", showFileContentPreview);
}

/**
 * Initialize Dropzone file uploader
 */
/**
 * Initialize Dropzone file uploader
 */
function initDropzone() {
  // Check if the element exists before trying to initialize Dropzone
  if ($("#file-upload-form").length === 0) {
    console.error("Dropzone target element #file-upload-form not found.");
    return;
  }

  // Check if Dropzone is already initialized on the element to prevent the "already attached" error
  // This check might be redundant if autoDiscover is properly disabled, but it's good practice.
  if ($("#file-upload-form")[0].dropzone) {
    console.log("Dropzone instance already exists on #file-upload-form, skipping initialization.");
    // Optionally, you might want to ensure the existing instance is configured correctly
    // or destroy and recreate it if necessary.
    // state.dropzone = $("#file-upload-form")[0].dropzone; // Assign existing instance
    return;
  }

  // Check if Dropzone library is loaded
  if (typeof Dropzone === "undefined") {
    console.error("Dropzone library is not loaded.");
    alertify.error("File uploader component failed to load. Please refresh the page or contact support.");
    return;
  }

  try {
    const myDropzone = new Dropzone("#file-upload-form", {
      url: "/api/v1/files/upload", // Make sure this URL is correct and reachable
      paramName: "file",
      maxFilesize: 50, // MB
      acceptedFiles: ".pdf,.txt,.docx,.html,.md,.csv",
      addRemoveLinks: true,
      dictDefaultMessage:
        "<i class='fas fa-cloud-upload-alt fa-3x mb-3'></i><br>Drop files here or click to upload<br><span class='text-muted small'>Supported: PDF, TXT, DOCX, HTML, MD, CSV</span>", // Optional: Customize message
      dictRemoveFile: "Remove",
      autoProcessQueue: true, // Set to false if you want to trigger uploads manually
      parallelUploads: 5,
      headers: {
        "X-CSRF-Token": getCsrfToken(), // Ensure getCsrfToken() is defined and returns a valid token
      },
      init: function () {
        const dzInstance = this; // Reference to the dropzone instance

        // Ensure theme_id is set *before* sending
        this.on("processing", function (file) {
          if (!state.currentThemeId) {
            alertify.error("Error: No theme selected. Cannot upload file.");
            dzInstance.removeFile(file); // Prevent upload if no theme ID
          }
        });

        this.on("sending", function (file, xhr, formData) {
          // Append theme_id only if it exists
          if (state.currentThemeId) {
            formData.append("theme_id", state.currentThemeId);
            console.log(`Sending file ${file.name} for theme ID: ${state.currentThemeId}`);
          } else {
            console.error("Cannot send file - theme_id is missing.");
            // Optionally cancel the upload here if needed, though the 'processing' event handler is better
            // xhr.abort();
          }
        });

        this.on("success", function (file, response) {
          // Make sure the response is the expected object/data
          console.log("File upload success response:", response);
          if (response && typeof response === "object") {
            state.uploadedFiles.push(response); // Assuming response is the file metadata object
            file.previewElement.classList.add("dz-success");
            // You might want to add a file ID to the preview element for removal later
            file.previewElement.setAttribute("data-file-id", response.id || file.upload.uuid);
            alertify.success(`File "${file.name}" uploaded successfully.`);
          } else {
            console.error("Received unexpected success response:", response);
            alertify.error(`Upload succeeded for ${file.name}, but received invalid server response.`);
            file.previewElement.classList.add("dz-error"); // Mark as error visually
            $(file.previewElement).find(".dz-error-message").text("Invalid server response");
          }
          // Enable next button if needed after *any* successful upload
          $("#upload-next-btn").prop("disabled", false);
        });

        this.on("error", function (file, errorMessage, xhr) {
          file.previewElement.classList.add("dz-error");
          let displayMessage = errorMessage;
          if (typeof errorMessage === "object" && errorMessage.error) {
            displayMessage = errorMessage.error; // Handle JSON error responses
          } else if (xhr && xhr.responseText) {
            try {
              const jsonResponse = JSON.parse(xhr.responseText);
              displayMessage = jsonResponse.detail || jsonResponse.error || xhr.responseText;
            } catch (e) {
              displayMessage = xhr.statusText || "Server error";
            }
          }

          alertify.error(`Error uploading ${file.name}: ${displayMessage}`);
          console.error("Upload error:", file.name, errorMessage, xhr);
        });

        this.on("queuecomplete", function () {
          console.log("Upload queue complete.");
          // Check if there are actually successful uploads, not just an empty queue completion
          if (this.getAcceptedFiles().length > 0 && this.getRejectedFiles().length === 0) {
            // alertify.success("All files processed successfully."); // Might be too noisy if individual success alerts are shown
          }
          // Update button state based on *successful* uploads in the state array
          $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
        });

        this.on("removedfile", function (file) {
          console.log(`Removing file: ${file.name}`);
          // Add logic here to remove the file from your server if it was successfully uploaded
          // This usually requires knowing the file's ID from the server
          const fileId = file.previewElement.getAttribute("data-file-id");
          if (file.status === "success" && fileId) {
            console.log(`Attempting to delete file with ID: ${fileId} from server...`);
            // $.ajax({
            //     url: `/api/v1/files/${fileId}`, // Adjust URL as needed
            //     method: 'DELETE',
            //     headers: { "X-CSRF-Token": getCsrfToken() },
            //     success: function(response) {
            //         alertify.success(`File ${file.name} removed from server.`);
            //         // Remove from state.uploadedFiles as well
            //         state.uploadedFiles = state.uploadedFiles.filter(f => (f.id || f.uuid) !== fileId);
            //         $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
            //     },
            //     error: function(xhr, status, error) {
            //         alertify.error(`Failed to remove ${file.name} from server.`);
            //         console.error("Error deleting file:", error);
            //     }
            // });
          } else {
            // If the file was never uploaded successfully or has no ID, just remove from UI
            // Potentially remove from state.uploadedFiles if it somehow got added without success/ID
          }
        });
      },
      // Fallback for browsers that don't support xhr2
      fallback: function () {
        alertify.error("Your browser does not support drag'n'drop file uploads.");
        // Maybe hide the dropzone element or show an alternative upload method
      },
    });

    // Store the Dropzone instance in the state for later reference
    state.dropzone = myDropzone;
    console.log("Dropzone initialized successfully on #file-upload-form");
  } catch (error) {
    console.error("Failed to initialize Dropzone:", error);
    alertify.error("Error initializing the file uploader. Please try again.");
    // Specific check for the URL error, though disabling autoDiscover should prevent it here.
    if (error.message.includes("No URL provided")) {
      alertify.error("Configuration error: Upload URL is missing.");
    }
  }
}
/**
 * Handle theme creation form submission
 */
function handleThemeFormSubmit(e) {
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
 * Get CSRF token from meta tag
 */
function getCsrfToken() {
  return AuthManager.getCsrfToken();
}

/**
 * Handle theme creation form submission
 */
function handleThemeFormSubmit(e) {
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
function loadThemes() {
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
        <td><span class="badge badge-info">${theme.document_count}</span></td>
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
function selectTheme(themeId, themeName) {
  state.currentThemeId = themeId;
  state.selectedTheme = themeName;

  $("#selected-theme-name").text(themeName);
  navigateToStep(2);
}

/**
 * Delete a theme
 */
function deleteTheme(themeId) {
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
 * Navigate to a specific step in the workflow
 */
function navigateToStep(step) {
  // Update current step
  state.currentStep = step;

  // Hide all sections
  $("#theme-section, #upload-section, #download-section, #read-section, #process-section").addClass("d-none");

  // Update progress steps
  $(".progress-step").removeClass("active completed");

  // Show current section and update UI based on the step
  switch (step) {
    case 1: // Theme
      $("#theme-section").removeClass("d-none");
      $("#step-theme").addClass("active");
      $("#workflow-progress-bar").css("width", "20%").text("Step 1 of 5");
      break;

    case 2: // Upload
      $("#upload-section").removeClass("d-none");
      $("#step-theme").addClass("completed");
      $("#step-upload").addClass("active");
      $("#workflow-progress-bar").css("width", "40%").text("Step 2 of 5");
      $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
      break;

    case 3: // Download
      $("#download-section").removeClass("d-none");
      $("#step-theme, #step-upload").addClass("completed");
      $("#step-download").addClass("active");
      $("#workflow-progress-bar").css("width", "60%").text("Step 3 of 5");
      loadFilesTable();
      break;

    case 4: // Read
      $("#read-section").removeClass("d-none");
      $("#step-theme, #step-upload, #step-download").addClass("completed");
      $("#step-read").addClass("active");
      $("#workflow-progress-bar").css("width", "80%").text("Step 4 of 5");
      break;

    case 5: // Process
      $("#process-section").removeClass("d-none");
      $("#step-theme, #step-upload, #step-download, #step-read").addClass("completed");
      $("#step-process").addClass("active");
      $("#workflow-progress-bar").css("width", "100%").text("Step 5 of 5");
      break;
  }
}

/**
 * Load files table in the download section
 */
function loadFilesTable() {
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
function renderFilesTable(files) {
  const tableBody = $("#files-table tbody");
  tableBody.empty();

  if (files.length === 0) {
    tableBody.html(`<tr><td colspan="3" class="text-center">No files found in this theme</td></tr>`);
    $("#start-download-btn").prop("disabled", true);
    return;
  }

  files.forEach((file, index) => {
    const row = `
      <tr data-file-id="${file.id}">
        <td>${file.title || file.source || "Unknown"}</td>
        <td>${formatFileSize(getRandomFileSize())}</td>
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
 * Start the file download process
 */
function startDownloadProcess() {
  if (state.uploadedFiles.length === 0) {
    alertify.error("No files to download");
    return;
  }

  $("#start-download-btn").prop("disabled", true);

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

      // Check if all files are downloaded
      if (downloadedCount === totalFiles) {
        alertify.success("All files downloaded successfully");
        $("#download-next-btn").removeClass("d-none");

        // Populate file selector for reading step
        populateFileSelector();
      }
    }, 1000 + index * 500); // Staggered timing for visual effect
  });
}

/**
 * Populate file selector dropdown for the read step
 */
function populateFileSelector() {
  const selector = $("#file-selector");
  selector.empty();
  selector.append('<option value="">Select a file to preview content</option>');

  state.downloadedFiles.forEach((file) => {
    selector.append(`<option value="${file.id}">${file.title || file.source || "Unknown"}</option>`);
  });
}

/**
 * Show file content preview based on selection
 */
function showFileContentPreview() {
  const fileId = $(this).val();
  if (!fileId) {
    $("#file-content-preview").html('<p class="text-muted">No content to display</p>');
    return;
  }

  // In a real app, this would fetch the file content from the API
  $("#file-content-preview").html(
    '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading content...</div>'
  );

  // Simulate API request to get file content
  setTimeout(() => {
    const selectedFile = state.downloadedFiles.find((f) => f.id === fileId);

    if (selectedFile) {
      // Generate fake content based on file type
      let content = generateSampleContent(selectedFile);
      $("#file-content-preview").html(content);
    } else {
      $("#file-content-preview").html('<p class="text-danger">Error loading file content</p>');
    }
  }, 800);
}

/**
 * Generate sample content for preview
 */
function generateSampleContent(file) {
  const fileType = file.source ? file.source.split(".").pop().toLowerCase() : "txt";

  const lorem = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam auctor, nisl eget ultricies 
  aliquam, nunc nisl aliquet nunc, eget aliquam nisl nunc eget nisl. Nullam auctor, nisl eget ultricies aliquam, 
  nunc nisl aliquet nunc, eget aliquam nisl nunc eget nisl.`;

  switch (fileType) {
    case "pdf":
      return `<p><strong>PDF Content:</strong> ${file.title || "Document"}</p>
              <p>${lorem}</p>
              <p>Page 1 of estimated 5 pages</p>`;
    case "docx":
      return `<p><strong>Word Document:</strong> ${file.title || "Document"}</p>
              <p>${lorem}</p>
              <p>Contains text, formatting and possibly images</p>`;
    case "html":
      return `<p><strong>HTML Content:</strong> ${file.title || "Document"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                &lt;html&gt;<br>
                &nbsp;&nbsp;&lt;head&gt;<br>
                &nbsp;&nbsp;&nbsp;&nbsp;&lt;title&gt;Sample Document&lt;/title&gt;<br>
                &nbsp;&nbsp;&lt;/head&gt;<br>
                &nbsp;&nbsp;&lt;body&gt;<br>
                &nbsp;&nbsp;&nbsp;&nbsp;&lt;p&gt;${lorem.substring(0, 50)}...&lt;/p&gt;<br>
                &nbsp;&nbsp;&lt;/body&gt;<br>
                &lt;/html&gt;
              </div>`;
    case "md":
      return `<p><strong>Markdown Content:</strong> ${file.title || "Document"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                # ${file.title || "Document Title"}<br><br>
                ## Introduction<br><br>
                ${lorem.substring(0, 100)}...<br><br>
                ## Section 1<br><br>
                * Point 1<br>
                * Point 2<br>
                * Point 3
              </div>`;
    case "csv":
      return `<p><strong>CSV Data:</strong> ${file.title || "Data File"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                id,name,value,date<br>
                1,Item 1,42.5,2023-01-15<br>
                2,Item 2,18.3,2023-01-16<br>
                3,Item 3,27.8,2023-01-17<br>
                4,Item 4,35.2,2023-01-18<br>
                ...(additional rows not shown)
              </div>`;
    default:
      return `<p><strong>Text Content:</strong> ${file.title || "Document"}</p>
              <p>${lorem}</p>`;
  }
}

/**
 * Start the reading process
 */
function startReadProcess() {
  $("#start-read-btn").prop("disabled", true);
  $("#read-progress").css("width", "0%");

  const totalFiles = state.downloadedFiles.length;
  let processedCount = 0;

  // Add log message
  appendProcessLog("Starting document reading process...");

  // Simulate processing for each file
  state.downloadedFiles.forEach((file, index) => {
    setTimeout(() => {
      processedCount++;

      // Update progress
      const progress = Math.round((processedCount / totalFiles) * 100);
      $("#read-progress").css("width", `${progress}%`);

      // Add to processed files
      state.processedFiles.push(file);

      // Add log message
      appendProcessLog(`Read document: ${file.title || file.source || "Unknown document"}`);

      // Check if all files are processed
      if (processedCount === totalFiles) {
        appendProcessLog("All documents read successfully!");
        alertify.success("All files processed successfully");
        $("#read-next-btn").removeClass("d-none");
      }
    }, 1200 + index * 800); // Staggered timing for visual effect
  });
}

/**
 * Start the embedding process
 */
function startEmbeddingProcess() {
  $("#start-process-btn").prop("disabled", true);
  $("#process-progress").css("width", "0%");

  // Reset step statuses
  $("#step-data-ingestion, #step-chunk-text, #step-generate-embeddings, #step-store-vectors")
    .find(".badge")
    .removeClass("badge-success badge-warning badge-danger")
    .addClass("badge-secondary")
    .text("Pending");

  // Clear log
  $("#process-log-content").html("> System ready to process files...");

  // Start the steps
  processDataIngestion();
}

/**
 * Process data ingestion step
 */
function processDataIngestion() {
  appendProcessLog("Starting data ingestion process...");
  updateStepStatus("step-data-ingestion", "warning", "Processing");

  $("#process-progress").css("width", "10%");

  setTimeout(() => {
    appendProcessLog("Converting documents to processable formats...");
    $("#process-progress").css("width", "20%");

    setTimeout(() => {
      updateStepStatus("step-data-ingestion", "success", "Completed");
      appendProcessLog("Data ingestion completed successfully!");
      processTextChunking();
    }, 2000);
  }, 1500);
}

/**
 * Process text chunking step
 */
function processTextChunking() {
  appendProcessLog("Starting text chunking process...");
  updateStepStatus("step-chunk-text", "warning", "Processing");

  $("#process-progress").css("width", "30%");

  setTimeout(() => {
    appendProcessLog("Dividing text into semantic chunks...");
    $("#process-progress").css("width", "40%");

    setTimeout(() => {
      updateStepStatus("step-chunk-text", "success", "Completed");
      appendProcessLog("Text chunking completed. Generated 143 chunks across all documents.");
      processGenerateEmbeddings();
    }, 2500);
  }, 1800);
}

/**
 * Process generate embeddings step
 */
function processGenerateEmbeddings() {
  appendProcessLog("Starting embedding generation...");
  updateStepStatus("step-generate-embeddings", "warning", "Processing");

  $("#process-progress").css("width", "50%");

  setTimeout(() => {
    appendProcessLog("Generating vector embeddings using model...");
    $("#process-progress").css("width", "60%");

    setTimeout(() => {
      appendProcessLog("Processing batch 1 of 3...");
      $("#process-progress").css("width", "70%");

      setTimeout(() => {
        appendProcessLog("Processing batch 2 of 3...");
        $("#process-progress").css("width", "80%");

        setTimeout(() => {
          appendProcessLog("Processing batch 3 of 3...");
          $("#process-progress").css("width", "85%");

          setTimeout(() => {
            updateStepStatus("step-generate-embeddings", "success", "Completed");
            appendProcessLog("Embedding generation completed. Generated 143 embeddings.");
            processStoreVectors();
          }, 1500);
        }, 1500);
      }, 1500);
    }, 2000);
  }, 1800);
}

/**
 * Process store vectors step
 */
function processStoreVectors() {
  appendProcessLog("Starting vector storage process...");
  updateStepStatus("step-store-vectors", "warning", "Processing");

  $("#process-progress").css("width", "90%");

  setTimeout(() => {
    appendProcessLog("Storing vector embeddings in database...");

    setTimeout(() => {
      updateStepStatus("step-store-vectors", "success", "Completed");
      appendProcessLog("Vector storage completed. All embeddings stored successfully.");
      $("#process-progress").css("width", "100%");

      appendProcessLog("RAG pipeline processing completed successfully!");
      $("#finish-btn").removeClass("d-none");
    }, 2000);
  }, 1500);
}

/**
 * Update the status of a processing step
 */
function updateStepStatus(stepId, status, text) {
  $(`#${stepId}`)
    .find(".badge")
    .removeClass("badge-secondary badge-warning badge-success badge-danger")
    .addClass(`badge-${status}`)
    .text(text);
}

/**
 * Append a log message to the process log
 */
function appendProcessLog(message) {
  const timestamp = new Date().toLocaleTimeString();
  const logMessage = `> [${timestamp}] ${message}`;

  const logContent = $("#process-log-content");
  logContent.append(`<div>${logMessage}</div>`);

  // Auto-scroll to bottom
  const processLog = $(".process-log");
  processLog.scrollTop(processLog[0].scrollHeight);
}

/**
 * Show success modal
 */
function showSuccessModal() {
  $("#success-message").text(
    `Your ${state.processedFiles.length} documents in theme "${state.selectedTheme}" have been successfully processed and are ready for use in the RAG system.`
  );
  $("#success-modal").modal("show");
}

/**
 * Format date to a readable format
 */
function formatDate(dateString) {
  if (!dateString) return "-";

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString; // Return as-is if invalid

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
