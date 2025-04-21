// File handling functionality

const FileHandlers = {
  // Track attached files
  attachedFiles: [],

  // Initialize file handling events
  init() {
    const fileDropArea = document.getElementById("fileDropArea");
    const fileInput = document.getElementById("fileInput");
    const attachedFilesList = document.getElementById("attachedFilesList");

    // Click to upload
    fileDropArea.addEventListener("click", () => {
      fileInput.click();
    });

    // File input change
    fileInput.addEventListener("change", (e) => {
      this.handleFiles(e.target.files);
    });

    // Drag and drop events
    fileDropArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      fileDropArea.classList.add("dragover");
    });

    fileDropArea.addEventListener("dragleave", () => {
      fileDropArea.classList.remove("dragover");
    });

    fileDropArea.addEventListener("drop", (e) => {
      e.preventDefault();
      fileDropArea.classList.remove("dragover");

      if (e.dataTransfer.files.length > 0) {
        this.handleFiles(e.dataTransfer.files);
      }
    });
  },

  // Handle selected files
  handleFiles(files) {
    if (!files || files.length === 0) return;

    const attachedFilesList = document.getElementById("attachedFilesList");
    const allowedExtensions = ["pdf", "txt", "docx", "md", "html", "csv", "json"];
    const maxFileSize = 10 * 1024 * 1024; // 10MB

    Array.from(files).forEach((file) => {
      // Validate file size
      if (file.size > maxFileSize) {
        alertify.error(`File ${file.name} exceeds 10MB size limit`);
        return;
      }

      // Validate file extension
      const extension = file.name.split(".").pop().toLowerCase();
      if (!allowedExtensions.includes(extension)) {
        alertify.error(`File type .${extension} is not supported`);
        return;
      }

      // Add to attached files
      this.attachedFiles.push(file);

      // Create UI element
      const fileElement = document.createElement("div");
      fileElement.className = "attached-file";
      fileElement.innerHTML = `
        <span title="${file.name}">${file.name}</span>
        <button class="remove-file" data-file-index="${this.attachedFiles.length - 1}">
          <i class="fas fa-times"></i>
        </button>
      `;

      attachedFilesList.appendChild(fileElement);
    });

    // Reset file input
    document.getElementById("fileInput").value = "";

    // Setup remove buttons
    this.setupRemoveButtons();
  },

  // Setup remove file buttons
  setupRemoveButtons() {
    document.querySelectorAll(".remove-file").forEach((button) => {
      button.addEventListener("click", (e) => {
        const index = parseInt(e.currentTarget.getAttribute("data-file-index"));
        this.removeFile(index);
      });
    });
  },

  // Remove a file
  removeFile(index) {
    if (index >= 0 && index < this.attachedFiles.length) {
      // Remove from array
      this.attachedFiles.splice(index, 1);

      // Rebuild UI
      const attachedFilesList = document.getElementById("attachedFilesList");
      attachedFilesList.innerHTML = "";

      this.attachedFiles.forEach((file, idx) => {
        const fileElement = document.createElement("div");
        fileElement.className = "attached-file";
        fileElement.innerHTML = `
          <span title="${file.name}">${file.name}</span>
          <button class="remove-file" data-file-index="${idx}">
            <i class="fas fa-times"></i>
          </button>
        `;

        attachedFilesList.appendChild(fileElement);
      });

      // Setup remove buttons again
      this.setupRemoveButtons();
    }
  },

  // Clear all attached files
  clearFiles() {
    this.attachedFiles = [];
    document.getElementById("attachedFilesList").innerHTML = "";
  },

  // Get currently attached files
  getFiles() {
    return [...this.attachedFiles];
  },
};

// Export the module
window.FileHandlers = FileHandlers;
