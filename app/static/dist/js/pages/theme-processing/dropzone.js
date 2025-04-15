/**
 * dropzone.js
 * Handles the initialization and configuration of the Dropzone file uploader
 */

// Import state and utilities
import { state, restoreWorkflowState, saveWorkflowState } from "./state.js";
import { getCsrfToken } from "./utils.js";

/**
 * Initialize Dropzone file uploader
 */
export function initDropzone() {
  // First, try to load state from localStorage
  restoreWorkflowState();

  // Check if the element exists before trying to initialize Dropzone
  const dropzoneElement = $("#file-upload-form")[0];

  if (!dropzoneElement) {
    console.error("Dropzone target element #file-upload-form not found.");
    return;
  }

  // Check and destroy existing Dropzone instance
  if (dropzoneElement.dropzone) {
    console.log("Destroying existing Dropzone instance on #file-upload-form.");
    dropzoneElement.dropzone.destroy();
    // Also clear the element's inner HTML if needed
    $("#file-upload-form").html(`
      <div class="dz-message d-flex flex-column">
        <i class="fas fa-cloud-upload-alt fa-3x mb-3"></i>
        <span>Drop files here or click to upload</span>
        <span class="text-muted small">Supported formats: PDF, TXT, DOCX, HTML, MD, CSV</span>
      </div>
    `);
  }

  try {
    const myDropzone = new Dropzone("#file-upload-form", {
      url: "/api/files", // This will be dynamically updated before sending
      paramName: "files",
      maxFilesize: 50, // MB
      acceptedFiles: ".pdf,.txt,.docx,.html,.md,.csv",
      addRemoveLinks: true,
      dictDefaultMessage:
        "<i class='fas fa-cloud-upload-alt fa-3x mb-3'></i><br>Drop files here or click to upload<br><span class='text-muted small'>Supported: PDF, TXT, DOCX, HTML, MD, CSV</span>", // Optional: Customize message
      dictRemoveFile: "Remove",
      autoProcessQueue: true, // Set to false if you want to trigger uploads manually
      parallelUploads: 5,

      init: function () {
        const dzInstance = this; // Reference to the dropzone instance

        // Ensure theme_id is set *before* sending
        this.on("processing", function (file) {
          if (!state.currentThemeId) {
            alertify.error("Error: No theme selected. Cannot upload file.");
            dzInstance.removeFile(file); // Prevent upload if no theme ID
            return false; // Prevent processing
          }
        });

        this.on("sending", function (file, xhr, formData) {
          // Get the CSRF token
          const token = getCsrfToken();
          console.log("CSRF Token:", token);

          // Check if the token is valid
          if (!token) {
            console.error("CSRF Token is missing or invalid.");
            alertify.error("Error: Authentication token missing. Please refresh the page.");
            dzInstance.removeFile(file);
            return;
          }

          // Check if the file is valid
          if (!file) {
            console.error("File is missing or invalid.");
            alertify.error("Error: File is missing or invalid.");
            dzInstance.removeFile(file);
            return;
          }

          // Only proceed if we have theme ID
          if (!state.currentThemeId) {
            alertify.error("Error: No theme selected. Cannot upload file.");
            dzInstance.removeFile(file);
            return;
          }

          // Update URL with the correct theme ID endpoint
          this.options.url = `/api/themes/${state.currentThemeId}/documents`;

          // Append necessary data
          xhr.withCredentials = true; // ← this is required for cookies
          xhr.setRequestHeader("X-CSRF-Token", token);
          formData.append("theme_id", state.currentThemeId);
          console.log(`Sending file ${file.name} for theme ID: ${state.currentThemeId}`);
        });

        this.on("success", function (file, response) {
          console.log("File upload success response:", response);

          // Assume the server returns a list of uploaded files
          const uploadedFile = Array.isArray(response) ? response[0] : response;

          if (uploadedFile && uploadedFile.id) {
            // Store the uploaded file data
            state.uploadedFiles.push(uploadedFile);

            // Update preview element
            file.previewElement.classList.add("dz-success");
            file.previewElement.setAttribute("data-file-id", uploadedFile.id);

            alertify.success(`File "${file.name}" uploaded successfully.`);
          } else {
            console.error("Unexpected or missing file ID in server response:", response);
            file.previewElement.classList.add("dz-error");
            $(file.previewElement).find(".dz-error-message").text("Missing file ID from server.");
            alertify.error(`Upload succeeded for ${file.name}, but no file ID was returned.`);
          }

          // Save state to localStorage
          saveWorkflowState();

          // Enable next button if needed
          $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
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

            $.ajax({
              url: `/api/files/${fileId}`, // ✅ matches your FastAPI route
              method: "DELETE",
              headers: {
                "X-CSRF-Token": getCsrfToken(),
              },
              success: function (response) {
                alertify.success(`File "${file.name}" removed from server.`);
                console.log("Server response:", response);

                // Remove from uploaded state
                state.uploadedFiles = state.uploadedFiles.filter((f) => f.id !== fileId);

                // Save state to localStorage
                saveWorkflowState();

                // Update "next" button state
                $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
              },
              error: function (xhr, status, error) {
                alertify.error(`Failed to remove "${file.name}" from server.`);
                console.error("Error deleting file:", xhr.responseText || error);
              },
            });
          }
        });

        // Important: Restore previously uploaded files from state
        restorePreviousUploads(dzInstance);
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
 * Fetch files and documents for a theme from the server and add them to Dropzone
 * @param {string} themeId - The ID of the theme
 * @param {Dropzone} dropzoneInstance - The Dropzone instance
 */
function fetchThemeFiles(themeId, dropzoneInstance) {
  console.log(`Fetching files for theme ID: ${themeId}`);

  // First try to fetch from /files endpoint
  $.ajax({
    url: `/api/themes/${themeId}/files`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function (files) {
      console.log(`Retrieved ${files.length} files for theme ID: ${themeId}`);
      processFiles(files, dropzoneInstance);
    },
    error: function (xhr, status, error) {
      console.error("Error fetching theme files:", xhr.responseText || error);

      // Fallback to documents endpoint if files endpoint fails
      console.log("Falling back to documents endpoint...");
      $.ajax({
        url: `/api/themes/${themeId}/files`,
        method: "GET",
        headers: {
          "X-CSRF-Token": getCsrfToken(),
        },
        success: function (documents) {
          console.log(`Retrieved ${documents.length} documents for theme ID: ${themeId}`);
          processFiles(documents, dropzoneInstance);
        },
        error: function (xhr, status, error) {
          console.error("Error fetching theme documents:", xhr.responseText || error);
          alertify.error("Failed to fetch files from the server");
        },
      });
    },
  });
}

/**
 * Process files data and add them to Dropzone
 * @param {Array} files - Array of file data objects
 * @param {Dropzone} dropzoneInstance - The Dropzone instance
 */
function processFiles(files, dropzoneInstance) {
  if (files.length > 0) {
    // Update state with the fetched files
    state.uploadedFiles = files;

    // Save to localStorage
    saveWorkflowState();

    // Add each file to the Dropzone UI
    files.forEach((fileData) => {
      // Create a mock file object that Dropzone can use
      const mockFile = {
        name: fileData.filename || fileData.title || fileData.source || "Unknown file",
        size: fileData.size || 0,
        status: "success",
        accepted: true,
      };

      // Add the mock file to Dropzone
      dropzoneInstance.emit("addedfile", mockFile);
      dropzoneInstance.emit("complete", mockFile);

      // Add CSS classes to indicate it's a restored file
      mockFile.previewElement.classList.add("dz-success");
      mockFile.previewElement.classList.add("dz-restored");
      mockFile.previewElement.classList.add("dz-server-fetched");

      // Set the file ID as a data attribute for later reference
      mockFile.previewElement.setAttribute("data-file-id", fileData.id);

      // Add file type icon or thumbnail if available
      const thumbnailElement = mockFile.previewElement.querySelector(".dz-image");
      if (thumbnailElement) {
        // Get filename from either filename or title property
        const fileName = fileData.filename || fileData.title || "";
        const fileExtension = fileName.split(".").pop().toLowerCase();
        let iconClass = "fas fa-file"; // Default icon

        // Map file extensions to icons
        switch (fileExtension) {
          case "pdf":
            iconClass = "fas fa-file-pdf";
            break;
          case "doc":
          case "docx":
            iconClass = "fas fa-file-word";
            break;
          case "csv":
          case "xls":
          case "xlsx":
            iconClass = "fas fa-file-excel";
            break;
          case "txt":
          case "md":
            iconClass = "fas fa-file-alt";
            break;
          case "html":
          case "htm":
            iconClass = "fas fa-file-code";
            break;
          default:
            iconClass = "fas fa-file";
        }

        thumbnailElement.innerHTML = `<i class="${iconClass}" style="font-size: 2rem; margin-top: 1rem;"></i>`;
      }

      // Add file size display if available
      const fileSizeElement = mockFile.previewElement.querySelector(".dz-size");
      if (fileSizeElement && fileData.size) {
        const formattedSize = formatFileSize(fileData.size);
        fileSizeElement.innerHTML = `<span><strong>Size:</strong> ${formattedSize}</span>`;
      }
    });

    // Update next button state
    $("#upload-next-btn").prop("disabled", false);

    alertify.success(`Loaded ${files.length} files from theme`);
  } else {
    console.log("No files found for this theme");
    $("#upload-next-btn").prop("disabled", true);
  }
}
/**
 * Restore previously uploaded files to the Dropzone UI
 * @param {Dropzone} dropzoneInstance - The Dropzone instance
 */
function restorePreviousUploads(dropzoneInstance) {
  // More robust check for array existence and content
  if (!Array.isArray(state.uploadedFiles) || state.uploadedFiles.length === 0) {
    // Only proceed to fetch if we have a theme ID
    if (state.currentThemeId) {
      fetchThemeFiles(state.currentThemeId, dropzoneInstance);
    } else {
      console.log("No previously uploaded files to restore");
      return;
    }
  }

  console.log(`Restoring ${state.uploadedFiles.length} previously uploaded files to Dropzone UI`);

  state.uploadedFiles.forEach((fileData) => {
    // Create a mock file object that Dropzone can use
    const mockFile = {
      name: fileData.filename || fileData.title || fileData.source || "Unknown file",
      size: fileData.size || 0,
      status: "success",
      accepted: true,
    };

    // Add the mock file to Dropzone
    dropzoneInstance.emit("addedfile", mockFile);

    // Pass the fileData as second parameter to match the success handler's expectations
    // dropzoneInstance.emit("success", mockFile, fileData); // This is optional and can be used to simulate a successful upload
    dropzoneInstance.emit("complete", mockFile);

    // Add a CSS class to indicate it's a restored file
    mockFile.previewElement.classList.add("dz-success");
    mockFile.previewElement.classList.add("dz-restored");

    // Set the file ID as a data attribute for later reference
    mockFile.previewElement.setAttribute("data-file-id", fileData.id);

    // Add file type icon or thumbnail if available
    const thumbnailElement = mockFile.previewElement.querySelector(".dz-image");
    if (thumbnailElement) {
      // Get file extension and determine icon
      const fileExtension = (fileData.filename || "").split(".").pop().toLowerCase();
      let iconClass = "fas fa-file"; // Default icon

      // More comprehensive file type detection
      switch (fileExtension) {
        case "pdf":
          iconClass = "fas fa-file-pdf";
          break;
        case "doc":
        case "docx":
          iconClass = "fas fa-file-word";
          break;
        case "csv":
        case "xls":
        case "xlsx":
          iconClass = "fas fa-file-excel";
          break;
        case "txt":
        case "md":
          iconClass = "fas fa-file-alt";
          break;
        case "html":
        case "htm":
          iconClass = "fas fa-file-code";
          break;
        default:
          iconClass = "fas fa-file";
      }

      thumbnailElement.innerHTML = `<i class="${iconClass}" style="font-size: 2rem; margin-top: 1rem;"></i>`;
    }

    // Add file size display
    const fileSizeElement = mockFile.previewElement.querySelector(".dz-size");
    if (fileSizeElement && fileData.size) {
      // Format file size for display
      const formattedSize = formatFileSize(fileData.size);
      fileSizeElement.innerHTML = `<span><strong>Size:</strong> ${formattedSize}</span>`;
    }
  });

  // Update next button state
  $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
}

/**
 * Format file size into human-readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size with units
 */
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Disable Dropzone auto-discovery
export function disableDropzoneAutoDiscover() {
  if (typeof Dropzone !== "undefined") {
    Dropzone.autoDiscover = false;
  } else {
    console.warn("Dropzone is not defined. Make sure the library is loaded before using this function.");
  }
}
