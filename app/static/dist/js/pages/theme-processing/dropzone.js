/**
 * dropzone.js
 * Handles the initialization and configuration of the Dropzone file uploader
 */

// Import state and utilities
import { state } from './state.js';
import { getCsrfToken } from './utils.js';

/**
 * Initialize Dropzone file uploader
 */
export function initDropzone() {
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
      url: "/api/files", // Make sure this URL is correct and reachable
      paramName: "files",
      maxFilesize: 50, // MB
      acceptedFiles: ".pdf,.txt,.docx,.html,.md,.csv",
      addRemoveLinks: true,
      dictDefaultMessage:
        "<i class='fas fa-cloud-upload-alt fa-3x mb-3'></i><br>Drop files here or click to upload<br><span class='text-muted small'>Supported: PDF, TXT, DOCX, HTML, MD, CSV</span>", // Optional: Customize message
      dictRemoveFile: "Remove",
      autoProcessQueue: true, // Set to false if you want to trigger uploads manually
      parallelUploads: 5,

      init: function() {
        const dzInstance = this; // Reference to the dropzone instance

        // Ensure theme_id is set *before* sending
        this.on("processing", function(file) {
          if (!state.currentThemeId) {
            alertify.error("Error: No theme selected. Cannot upload file.");
            dzInstance.removeFile(file); // Prevent upload if no theme ID
          }
        });

        this.on("sending", function(file, xhr, formData) {
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
          // Only proceed if we have both theme ID and token
          if (!state.currentThemeId) {
            alertify.error("Error: No theme selected. Cannot upload file.");
            dzInstance.removeFile(file);
            return;
          }

          // Append necessary data
          xhr.withCredentials = true; // ← this is required for cookies
          xhr.setRequestHeader("X-CSRF-Token", token);
          formData.append("theme_id", state.currentThemeId);
          console.log(`Sending file ${file.name} for theme ID: ${state.currentThemeId}`);
        });

        this.on("success", function(file, response) {
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

          // Enable next button if needed
          $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
        });

        this.on("error", function(file, errorMessage, xhr) {
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

        this.on("queuecomplete", function() {
          console.log("Upload queue complete.");
          // Check if there are actually successful uploads, not just an empty queue completion
          if (this.getAcceptedFiles().length > 0 && this.getRejectedFiles().length === 0) {
            // alertify.success("All files processed successfully."); // Might be too noisy if individual success alerts are shown
          }
          // Update button state based on *successful* uploads in the state array
          $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
        });

        this.on("removedfile", function(file) {
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
              success: function(response) {
                alertify.success(`File "${file.name}" removed from server.`);
                console.log("Server response:", response);

                // Remove from uploaded state
                state.uploadedFiles = state.uploadedFiles.filter((f) => f.id !== fileId);

                // Update "next" button state
                $("#upload-next-btn").prop("disabled", state.uploadedFiles.length === 0);
              },
              error: function(xhr, status, error) {
                alertify.error(`Failed to remove "${file.name}" from server.`);
                console.error("Error deleting file:", xhr.responseText || error);
              },
            });
          }
        });
      },
      // Fallback for browsers that don't support xhr2
      fallback: function() {
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

// Disable Dropzone auto-discovery
export function disableDropzoneAutoDiscover() {
  if (typeof Dropzone !== 'undefined') {
    Dropzone.autoDiscover = false;
  } else {
    console.warn("Dropzone is not defined. Make sure the library is loaded before using this function.");
  }
}