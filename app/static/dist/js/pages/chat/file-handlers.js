// File handling functionality

export const FileHandlers = {
    // Track attached files
    attachedFiles: [],

    // Initialize file handling events
    init() {
        const $fileDropArea = $("#fileDropArea");
        const $fileInput = $("#fileInput");
        const $attachedFilesList = $("#attachedFilesList");

        // User clicks drop area: manually trigger file input click
        $fileDropArea.on("click", () => {
            $fileInput[0].click(); // Use [0] to call native `click()` instead of jQuery trigger
        });


        // File input change
        $fileInput.on("change", (e) => {
            this.handleFiles(e.target.files);
        });

        // Drag and drop events
        $fileDropArea.on("dragover", (e) => {
            e.preventDefault();
            $fileDropArea.addClass("dragover");
        });

        $fileDropArea.on("dragleave", () => {
            $fileDropArea.removeClass("dragover");
        });

        $fileDropArea.on("drop", (e) => {
            e.preventDefault();
            $fileDropArea.removeClass("dragover");

            if (e.originalEvent.dataTransfer.files.length > 0) {
                this.handleFiles(e.originalEvent.dataTransfer.files);
            }
        });
    },

    // Handle selected files
    handleFiles(files) {
        if (!files || files.length === 0) return;

        const $attachedFilesList = $("#attachedFilesList");
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
            const $fileElement = $(
                `<div class="attached-file">
          <span title="${file.name}">${file.name}</span>
          <button class="remove-file" data-file-index="${this.attachedFiles.length - 1}">
            <i class="fas fa-times"></i>
          </button>
        </div>`
            );

            $attachedFilesList.append($fileElement);
        });

        // Reset file input
        $("#fileInput").val("");

        // Setup remove buttons
        this.setupRemoveButtons();
    },

    // Setup remove file buttons
    setupRemoveButtons() {
        $(".remove-file").off("click").on("click", (e) => {
            const index = parseInt($(e.currentTarget).data("file-index"));
            this.removeFile(index);
        });
    },

    // Remove a file
    removeFile(index) {
        if (index >= 0 && index < this.attachedFiles.length) {
            // Remove from array
            this.attachedFiles.splice(index, 1);

            // Rebuild UI
            const $attachedFilesList = $("#attachedFilesList");
            $attachedFilesList.empty();

            this.attachedFiles.forEach((file, idx) => {
                const $fileElement = $(
                    `<div class="attached-file">
            <span title="${file.name}">${file.name}</span>
            <button class="remove-file" data-file-index="${idx}">
              <i class="fas fa-times"></i>
            </button>
          </div>`
                );

                $attachedFilesList.append($fileElement);
            });

            // Setup remove buttons again
            this.setupRemoveButtons();
        }
    },

    // Clear all attached files
    clearFiles() {
        this.attachedFiles = [];
        $("#attachedFilesList").empty();
    },

    // Get currently attached files
    getFiles() {
        return [...this.attachedFiles];
    },
};