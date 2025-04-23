// =====================================================================
// file-handlers.js - IMPROVED VERSION
// =====================================================================

export const FileHandlers = {
  // Track attached files
  attachedFiles: [],
  fileCounter: 0, // For keeping track of unique file indices

  // Initialize file handling events
  init() {
    const $fileDropArea = $("#fileDropArea");
    const $fileInput = $("#fileInput");
    const $attachedFilesList = $("#attachedFilesList");

    if (!$fileDropArea.length || !$fileInput.length) {
      console.error("File handling elements not found in DOM");
      return;
    }

    // Reset state
    this.attachedFiles = [];
    this.fileCounter = 0;
    $attachedFilesList.empty();

    // User clicks drop area: manually trigger file input click
    $fileDropArea.off("click").on("click", () => {
      $fileInput[0]?.click(); // Use [0] to call native `click()` instead of jQuery trigger
    });

    // File input change
    $fileInput.off("change").on("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        this.handleFiles(e.target.files);
      }
    });

    // Drag and drop events
    $fileDropArea.off("dragover").on("dragover", (e) => {
      e.preventDefault();
      $fileDropArea.addClass("dragover");
    });

    $fileDropArea.off("dragleave").on("dragleave", () => {
      $fileDropArea.removeClass("dragover");
    });

    $fileDropArea.off("drop").on("drop", (e) => {
      e.preventDefault();
      $fileDropArea.removeClass("dragover");

      if (e.originalEvent?.dataTransfer?.files?.length > 0) {
        this.handleFiles(e.originalEvent.dataTransfer.files);
      }
    });
  },

  // Handle selected files
  handleFiles(files) {
    if (!files || files.length === 0) return;

    const $attachedFilesList = $("#attachedFilesList");
    if (!$attachedFilesList.length) {
      console.error("Attached files list element not found in DOM");
      return;
    }

    const allowedExtensions = ["pdf", "txt", "docx", "md", "html", "csv", "json"];
    const maxFileSize = 10 * 1024 * 1024; // 10MB
    const maxFiles = 5; // Limit number of files

    // Check if adding these files would exceed the max
    if (this.attachedFiles.length + files.length > maxFiles) {
      window.UIHandlers.showToast(`You can only attach up to ${maxFiles} files`, "error");
      return;
    }

    Array.from(files).forEach((file) => {
      // Validate file size
      if (file.size > maxFileSize) {
        window.UIHandlers.showToast(`File ${file.name} exceeds 10MB size limit`, "error");
        return;
      }

      // Validate file extension
      const extension = file.name.split(".").pop().toLowerCase();
      if (!allowedExtensions.includes(extension)) {
        window.UIHandlers.showToast(`File type .${extension} is not supported`, "error");
        return;
      }

      // Add to attached files with unique index
      const fileIndex = this.fileCounter++;
      this.attachedFiles.push({
        file: file,
        index: fileIndex,
      });

      // Create UI element
      const $fileElement = $(
        `<div class="attached-file">
                    <span title="${file.name}">${file.name}</span>
                    <button class="remove-file" data-file-index="${fileIndex}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>`
      );

      $attachedFilesList.append($fileElement);

      // Setup remove button for this file
      $fileElement.find(".remove-file").on("click", (e) => {
        const index = parseInt($(e.currentTarget).data("file-index"), 10);
        this.removeFile(index);
      });
    });

    // Reset file input to allow selecting the same file again
    $("#fileInput").val("");
  },

  // Remove a file by index
  removeFile(index) {
    const fileIdx = this.attachedFiles.findIndex((item) => item.index === index);
    if (fileIdx >= 0) {
      // Remove from array
      this.attachedFiles.splice(fileIdx, 1);

      // Remove element from UI
      $(`.remove-file[data-file-index="${index}"]`).closest(".attached-file").remove();
    }
  },

  // Clear all attached files
  clearFiles() {
    this.attachedFiles = [];
    $("#attachedFilesList").empty();
  },

  // Get currently attached files for submission
  getFiles() {
    return this.attachedFiles.map((item) => item.file);
  },
};
