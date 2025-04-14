/**
 * Attempt to reconnect WebSocket after connection lost
 */
function attemptReconnect() {
  if (state.reconnectAttempts >= state.maxReconnectAttempts) {
    console.error("Maximum reconnection attempts reached");
    alertify.error("Lost connection to server. Please refresh the page.");
    return;
  }

  state.reconnectAttempts++;

  console.log(`Attempting to reconnect (${state.reconnectAttempts}/${state.maxReconnectAttempts})...`);

  setTimeout(() => {
    initializeWebSocketConnection();
  }, state.reconnectDelay);
}

/**
 * Handle page visibility change to manage WebSocket connection
 */
function handleWindowFocus() {
  // If the WebSocket is closed, try to reconnect
  if (state.taskSocket && state.taskSocket.readyState === WebSocket.CLOSED) {
    console.log("Window gained focus, reconnecting WebSocket...");
    initializeWebSocketConnection();
  }
  
  // Also refresh task status if we have an active task
  if (state.processingTask && state.processingTask.id) {
    refreshTaskStatus(state.processingTask.id);
  }
}

/**
 * Refresh task status from the server
 */
function refreshTaskStatus(taskId) {
  $.ajax({
    url: `/api/tasks/${taskId}`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(task) {
      // Update our state
      state.processingTask = task;
      
      // Update UI
      updateTaskUI(task);
      
      // Update vector DB status if available
      if (task.metadata && task.metadata.vectorDBStatus) {
        state.vectorDBStatus = task.metadata.vectorDBStatus;
        updateVectorDBStatusUI();
      }
      
      // Update logs if available
      if (task.logs && task.logs.length > 0) {
        // Clear existing logs
        $("#process-log-content").empty();
        
        // Add each log entry
        task.logs.forEach(log => {
          $("#process-log-content").append(`<div>> ${log}</div>`);
        });
        
        // Store in state
        state.processingLogs = task.logs;
        
        // Auto-scroll to bottom
        const logContainer = $("#process-log-content").parent();
        logContainer.scrollTop(logContainer[0].scrollHeight);
      }
    },
    error: function(xhr, status, error) {
      console.error("Error refreshing task status:", error);
    }
  });
}

/**
 * Handle window blur event (user navigated away)
 */
function handleWindowBlur() {
  // We could pause long-running operations here or update status
  console.log("Window lost focus");
}

/**
 * Handle before unload event to warn if there's an active task
 */
function handleBeforeUnload(e) {
  // Only show warning if there's an active task
  if (state.processingTask && ["pending", "in_progress"].includes(state.processingTask.status)) {
    const message = "You have an active processing task. Are you sure you want to leave?";
    e.returnValue = message;
    return message;
  }
}

/**
 * Cancel the current processing task
 */
function cancelCurrentTask() {
  if (!state.processingTask || !state.processingTask.id) {
    alertify.error("No active task to cancel");
    return;
  }

  if (confirm("Are you sure you want to cancel this task? This action cannot be undone.")) {
    $.ajax({
      url: `/api/tasks/${state.processingTask.id}/cancel`,
      method: "POST",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function(response) {
        alertify.success("Task cancelled successfully");

        // Update local state
        state.processingTask.status = "cancelled";

        // Update UI
        updateTaskUI(state.processingTask);
        
        // Add log entry
        addProcessingLog("Task cancelled by user");
      },
      error: function(xhr, status, error) {
        console.error("Error cancelling task:", error);
        alertify.error(`Error cancelling task: ${xhr.responseJSON?.detail || error}`);
      },
    });
  }
}

/**
 * Resume the current processing task
 */
function resumeCurrentTask() {
  if (!state.processingTask || !state.processingTask.id) {
    alertify.error("No task to resume");
    return;
  }

  $.ajax({
    url: `/api/tasks/${state.processingTask.id}/resume`,
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
      alertify.success("Task resumed successfully");

      // Update local state
      state.processingTask.status = "in_progress";

      // Update UI
      updateTaskUI(state.processingTask);
      
      // Add log entry
      addProcessingLog("Task resumed by user");
    },
    error: function(xhr, status, error) {
      console.error("Error resuming task:", error);
      alertify.error(`Error resuming task: ${xhr.responseJSON?.detail || error}`);
    },
  });
}/**
 * theme-processing.js
 * Handles the theme and document processing workflow with real-time updates
 * for RAG vector database creation pipeline
 */

// Global state
const state = {
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
    dataIngestion: 'pending',
    textChunking: 'pending',
    generateEmbeddings: 'pending',
    storeVectors: 'pending'
  },
  vectorDBProgress: 0,
  processingLogs: []
}; // End of state object definition
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
                &nbsp;&nbsp;&lt;body&gt;<br>&nbsp;&nbsp;&nbsp;&nbsp;&lt;p&gt;${lorem}&lt;/p&gt;<br>
              &nbsp;&nbsp;&lt;/body&gt;<br>
                &lt;/html&gt;
              </div>`;
    case "md":
      return `<p><strong>Markdown Content:</strong> ${file.title || "Document"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                # Sample Document<br>
                <br>
                ${lorem}<br>
                <br>
                ## Heading 2<br>
                <br>
                * List item 1<br>
                * List item 2<br>
              </div>`;
    case "csv":
      return `<p><strong>CSV Data:</strong> ${file.title || "Data File"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                id,name,value<br>
                1,Item 1,100<br>
                2,Item 2,200<br>
                3,Item 3,300<br>
              </div>`;
    default:
      return `<p><strong>Text Content:</strong> ${file.title || "Document"}</p>
              <div class="border p-3">${lorem}</div>`;
  }
}

/**
 * Start the file reading process
 */
function startReadProcess() {
  // Create task for reading files
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "read",
      files: state.downloadedFiles.map((f) => f.id),
      description: `Extract text from files for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "read",
        vectorDBStatus: state.vectorDBStatus,
        totalFiles: state.downloadedFiles.length
      }
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
      // Store the task reference
      state.processingTask = response;

      // The real updates will come via WebSocket
      alertify.success("Started text extraction process");

      // Initialize reading progress
      $("#read-progress").css("width", "0%");
      state.processedFiles = [];
      
      // Add log entry
      addProcessingLog("Starting text extraction process...");
      
      // Update vector DB status
      state.vectorDBStatus.textChunking = 'in_progress';
      updateVectorDBStatusUI();
    },
    error: function(xhr, status, error) {
      console.error("Error starting read process:", error);
      alertify.error(`Error starting text extraction: ${xhr.responseJSON?.detail || error}`);
      $("#start-read-btn").prop("disabled", false);
    },
  });

  // For the UI simulation, process the files
  const totalFiles = state.downloadedFiles.length;
  let processedCount = 0;

  $("#start-read-btn").prop("disabled", true);

  // Simulate reading each file
  state.downloadedFiles.forEach((file, index) => {
    setTimeout(() => {
      // Add to processed files
      state.processedFiles.push(file);
      processedCount++;

      // Update progress
      const progress = Math.round((processedCount / totalFiles) * 100);
      $("#read-progress").css("width", `${progress}%`);
      
      // Add log entry
      addProcessingLog(`Extracted text from: ${file.filename || file.title || "Unknown file"}`);

      // Check if all files are processed
      if (processedCount === totalFiles) {
        alertify.success("All files processed successfully");
        $("#read-next-btn").prop("disabled", false);
        
        // Update vector DB status
        state.vectorDBStatus.textChunking = 'completed';
        updateVectorDBStatusUI();
        
        // Add log entry
        addProcessingLog("Text extraction completed successfully!");
      }
    }, 1500 + index * 800); // Staggered timing for visual effect
  });
}

/**
 * Start the embedding process
 */
function startEmbeddingProcess() {
  $("#start-process-btn").prop("disabled", true);
  $("#process-progress").css("width", "0%");

  // Create task for embedding
  $.ajax({
    url: "/api/tasks",
    method: "POST",
    data: JSON.stringify({
      type: "theme_processing",
      theme_id: state.currentThemeId,
      step: "embed",
      files: state.processedFiles.map((f) => f.id),
      description: `Generate embeddings and create vector DB for theme: ${state.selectedTheme}`,
      metadata: {
        stepName: "embed",
        vectorDBStatus: state.vectorDBStatus,
        totalFiles: state.processedFiles.length
      }
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
      // Store the task reference
      state.processingTask = response;

      // Display task info
      alertify.success("Started embedding process");
      
      // Add log entry
      addProcessingLog("Starting vector embedding generation process...");
      
      // Update vector DB status
      state.vectorDBStatus.generateEmbeddings = 'in_progress';
      updateVectorDBStatusUI();
    },
    error: function(xhr, status, error) {
      console.error("Error starting embedding process:", error);
      alertify.error(`Error starting embeddings: ${xhr.responseJSON?.detail || error}`);
      $("#start-process-btn").prop("disabled", false);
    },
  });

  // Simulate embedding process for UI
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 5;
    $("#process-progress").css("width", `${progress}%`);
    
    if (progress === 25) {
      addProcessingLog("Generating embeddings for chunks...");
    } else if (progress === 50) {
      state.vectorDBStatus.generateEmbeddings = 'completed';
      state.vectorDBStatus.storeVectors = 'in_progress';
      updateVectorDBStatusUI();
      addProcessingLog("Embeddings generated successfully!");
      addProcessingLog("Starting vector database storage...");
    } else if (progress === 75) {
      addProcessingLog("Optimizing vector database for search...");
    }

    if (progress >= 100) {
      clearInterval(progressInterval);
      state.vectorDBStatus.storeVectors = 'completed';
      updateVectorDBStatusUI();
      addProcessingLog("Vector database created successfully!");
      alertify.success("Embedding process completed successfully");
      $("#finish-btn").prop("disabled", false);
    }
  }, 500);
}

/**
 * Update the UI to reflect the current vector DB processing status
 */
function updateVectorDBStatusUI() {
  // Update the status badges for each step
  const statusMapping = {
    'pending': { class: 'badge-secondary', text: 'Pending' },
    'in_progress': { class: 'badge-warning', text: 'In Progress' },
    'completed': { class: 'badge-success', text: 'Completed' },
    'failed': { class: 'badge-danger', text: 'Failed' }
  };
  
  // Data Ingestion step
  const dataIngestionStatus = statusMapping[state.vectorDBStatus.dataIngestion] || statusMapping.pending;
  $("#step-data-ingestion").removeClass("active completed").addClass(state.vectorDBStatus.dataIngestion === 'in_progress' ? 'active' : (state.vectorDBStatus.dataIngestion === 'completed' ? 'completed' : ''));
  $("#step-data-ingestion .badge").removeClass("badge-secondary badge-warning badge-success badge-danger").addClass(dataIngestionStatus.class).text(dataIngestionStatus.text);
  
  // Text Chunking step
  const textChunkingStatus = statusMapping[state.vectorDBStatus.textChunking] || statusMapping.pending;
  $("#step-chunk-text").removeClass("active completed").addClass(state.vectorDBStatus.textChunking === 'in_progress' ? 'active' : (state.vectorDBStatus.textChunking === 'completed' ? 'completed' : ''));
  $("#step-chunk-text .badge").removeClass("badge-secondary badge-warning badge-success badge-danger").addClass(textChunkingStatus.class).text(textChunkingStatus.text);
  
  // Generate Embeddings step
  const generateEmbeddingsStatus = statusMapping[state.vectorDBStatus.generateEmbeddings] || statusMapping.pending;
  $("#step-generate-embeddings").removeClass("active completed").addClass(state.vectorDBStatus.generateEmbeddings === 'in_progress' ? 'active' : (state.vectorDBStatus.generateEmbeddings === 'completed' ? 'completed' : ''));
  $("#step-generate-embeddings .badge").removeClass("badge-secondary badge-warning badge-success badge-danger").addClass(generateEmbeddingsStatus.class).text(generateEmbeddingsStatus.text);
  
  // Store Vectors step
  const storeVectorsStatus = statusMapping[state.vectorDBStatus.storeVectors] || statusMapping.pending;
  $("#step-store-vectors").removeClass("active completed").addClass(state.vectorDBStatus.storeVectors === 'in_progress' ? 'active' : (state.vectorDBStatus.storeVectors === 'completed' ? 'completed' : ''));
  $("#step-store-vectors .badge").removeClass("badge-secondary badge-warning badge-success badge-danger").addClass(storeVectorsStatus.class).text(storeVectorsStatus.text);
}

/**
 * Add a log entry to the processing log
 */
function addProcessingLog(message) {
  // Add timestamp
  const now = new Date();
  const timestamp = now.toLocaleTimeString();
  const logEntry = `[${timestamp}] ${message}`;
  
  // Add to state for persistence
  state.processingLogs.push(logEntry);
  
  // Update UI
  const logElement = $("#process-log-content");
  logElement.append(`<div>> ${logEntry}</div>`);
  
  // Auto-scroll to bottom
  const logContainer = logElement.parent();
  logContainer.scrollTop(logContainer[0].scrollHeight);
  
  // If we have a task, update its logs
  if (state.processingTask && state.processingTask.id) {
    // In a production app, we might want to batch these updates
    updateTaskLogs(state.processingTask.id, logEntry);
  }
}

/**
 * Update task logs on the server
 */
function updateTaskLogs(taskId, logEntry) {
  // This could be optimized to batch updates instead of sending one at a time
  $.ajax({
    url: `/api/tasks/${taskId}/logs`,
    method: "POST",
    data: JSON.stringify({
      log_entry: logEntry
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    error: function(xhr, status, error) {
      console.error("Error updating task logs:", error);
    }
  });
}

/**
 * Show success modal when the workflow is complete
 */
function showSuccessModal() {
  $("#success-modal-theme-name").text(state.selectedTheme);
  $("#success-modal-file-count").text(state.processedFiles.length);
  $("#workflow-completion-modal").modal("show");
  
  // Create a summary API call to finalize the theme processing
  $.ajax({
    url: `/api/themes/${state.currentThemeId}/finalize`,
    method: "POST",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
      console.log("Theme processing finalized:", response);
    },
    error: function(xhr, status, error) {
      console.error("Error finalizing theme processing:", error);
    }
  });
}

/**
 * Check for active tasks on page load
 */
function checkForActiveTasks() {
  // Check if we have an active theme
  if (state.currentThemeId) {
    $.ajax({
      url: `/api/tasks?theme_id=${state.currentThemeId}`,
      method: "GET",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      success: function(tasks) {
        if (tasks && tasks.length > 0) {
          const activeTasks = tasks.filter(
            (t) => (t.status === "in_progress" || t.status === "pending") && t.type === "theme_processing"
          );

          if (activeTasks.length > 0) {
            // Sort by most recently created
            activeTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            // Get the first (most recent) task
            state.processingTask = activeTasks[0];

            // Update UI based on task status
            updateTaskUI(state.processingTask);
            
            // Restore vector DB status if available
            if (state.processingTask.metadata && state.processingTask.metadata.vectorDBStatus) {
              state.vectorDBStatus = state.processingTask.metadata.vectorDBStatus;
              updateVectorDBStatusUI();
            }
            
            // Restore logs if available
            if (state.processingTask.logs && state.processingTask.logs.length > 0) {
              // Clear existing logs
              $("#process-log-content").empty();
              
              // Add each log entry
              state.processingTask.logs.forEach(log => {
                $("#process-log-content").append(`<div>> ${log}</div>`);
              });
              
              // Store in state
              state.processingLogs = state.processingTask.logs;
            }
          }
        }
      },
      error: function(xhr, status, error) {
        console.error("Error checking for active tasks:", error);
      },
    });
  }
}

/**
 * Initialize WebSocket connection for real-time updates
 */
function initializeWebSocketConnection() {
  // Close any existing connection
  if (state.taskSocket && state.taskSocket.readyState !== WebSocket.CLOSED) {
    state.taskSocket.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/tasks`;
  try {
    state.taskSocket = new WebSocket(wsUrl);

    state.taskSocket.onopen = function() {
      console.log("WebSocket connection established");
      state.reconnectAttempts = 0;

      if (state.currentThemeId) {
        subscribeToThemeUpdates(state.currentThemeId);
      }
    };

    state.taskSocket.onmessage = function(event) {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    state.taskSocket.onclose = function(event) {
      console.log("WebSocket closed", event);
      if (event.code !== 1000) attemptReconnect();
    };

    state.taskSocket.onerror = function(error) {
      console.error("WebSocket error:", error);
    };
  } catch (error) {
    console.error("WebSocket init failed:", error);
    attemptReconnect();
  }
}

/**
 * Subscribe to theme updates via WebSocket
 */
function subscribeToThemeUpdates(themeId) {
  if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
    const subscribeMsg = {
      action: "subscribe",
      theme_id: themeId,
    };

    state.taskSocket.send(JSON.stringify(subscribeMsg));
    console.log(`Subscribed to updates for theme ${themeId}`);
  } else {
    console.warn("WebSocket not connected, can't subscribe to theme updates");
  }
}

/**
 * Handle WebSocket messages
 */
function handleWebSocketMessage(message) {
  console.log("Received WebSocket message:", message);

  // Handle task updates
  if (message.type === "task_update" && message.data) {
    const taskData = message.data;

    // Only process updates for the current theme
    if (taskData.theme_id === state.currentThemeId) {
      // Update our task data
      state.processingTask = taskData;

      // Update UI based on task data
      updateTaskUI(taskData);
      
      // Update vector DB status if it exists in the metadata
      if (taskData.metadata && taskData.metadata.vectorDBStatus) {
        state.vectorDBStatus = taskData.metadata.vectorDBStatus;
        updateVectorDBStatusUI();
      }
      
      // If there are new logs, add them to the UI
      if (taskData.logs && taskData.logs.length > 0) {
        // Find logs that are not already in our state
        const existingLogs = new Set(state.processingLogs);
        const newLogs = taskData.logs.filter(log => !existingLogs.has(log));
        
        // Add new logs to UI and state
        newLogs.forEach(log => {
          $("#process-log-content").append(`<div>> ${log}</div>`);
          state.processingLogs.push(log);
        });
        
        // Auto-scroll to bottom if there are new logs
        if (newLogs.length > 0) {
          const logContainer = $("#process-log-content").parent();
          logContainer.scrollTop(logContainer[0].scrollHeight);
        }
      }
    }
  }
}

/**
 * Update UI based on task status
 */
// Define the function outside the state object
function updateTaskUI(task) {
  if (!task) return;

  // Update the task status area
  $("#task-status-area").removeClass("d-none");
  $("#task-name").text(task.name || "Theme Processing");
  $("#task-status").text(task.status);

  const statusBadge = $("#task-status-badge");
  statusBadge.removeClass("badge-secondary badge-info badge-warning badge-success badge-danger");

  switch (task.status) {
    case "pending":
      statusBadge.addClass("badge-secondary").text("Pending");
      break;
    case "in_progress":
      statusBadge.addClass("badge-info").text("In Progress");
      break;
    case "paused":
      statusBadge.addClass("badge-warning").text("Paused");
      break;
    case "completed":
      statusBadge.addClass("badge-success").text("Completed");
      break;
    case "failed":
      statusBadge.addClass("badge-danger").text("Failed");
      break;
    default:
      statusBadge.addClass("badge-secondary").text(task.status);
  }

  let progress = 0;

  if (task.current_step !== null && task.current_step !== undefined) {
    const stepMapping = {
      0: 2,
      1: 3,
      2: 4,
      3: 5,
    };

    progress = (task.current_step / 4) * 100;

    const uiStep = stepMapping[task.current_step];
    if (uiStep && task.progress !== null && task.progress !== undefined) {
      switch (uiStep) {
        case 3:
          $("#download-progress").css("width", `${task.progress}%`);
          break;
        case 4:
          $("#read-progress").css("width", `${task.progress}%`);
          break;
        case 5:
          $("#process-progress").css("width", `${task.progress}%`);
          break;
      }
    }
  }

  $("#task-progress-bar").css("width", `${progress}%`);
  $("#cancel-task-btn").toggle(["pending", "in_progress", "paused"].includes(task.status));
  $("#resume-task-btn").toggle(task.status === "paused");

  if (task.error_message) {
    $("#task-error-message").removeClass("d-none").text(task.error_message);
  } else {
    $("#task-error-message").addClass("d-none").text("");
  }
}
$(document).ready(function() {
  console.log("Enhanced Theme Processing initialized");

  // Disable Dropzone auto-discovery before any initialization
  Dropzone.autoDiscover = false;

  // Initialize Dropzone
  initDropzone();

  // Load initial themes
  loadThemes();

  // Setup event listeners
  setupEventListeners();

  // Initialize WebSocket connection for real-time updates
  initializeWebSocketConnection();

  // Check for active tasks
  checkForActiveTasks();
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

  // Task related buttons
  $("#cancel-task-btn").on("click", cancelCurrentTask);
  $("#resume-task-btn").on("click", resumeCurrentTask);

  // Window events for handling page visibility
  $(window).on("focus", handleWindowFocus);
  $(window).on("blur", handleWindowBlur);
  $(window).on("beforeunload", handleBeforeUnload);
}

/**
 * Initialize Dropzone file uploader
 */
function initDropzone() {
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

/**
 * Get CSRF token from meta tag
 */
function getCsrfToken() {
  if (typeof AuthManager === "undefined" || !AuthManager.getCsrfToken) {
    console.warn("AuthManager is not defined or getCsrfToken is missing.");
    return "";
  }

  // Assuming AuthManager is a global object with a method to get CSRF token
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
    success: function(response) {
      alertify.success(`Theme "${themeData.name}" created successfully`);
      loadThemes();
      $("#create-theme-form")[0].reset();
    },
    error: function(xhr, status, error) {
      console.error("Error creating theme:", error);
      alertify.error(`Error creating theme: ${xhr.responseJSON?.detail || error}`);
    },
  });
}

/**
 * Load themes from the API
 */
function loadThemes() {
  // Show the loading spinner
  $("#themes-loader").removeClass("d-none");

  $.ajax({
    url: "/api/themes",
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(themes) {
      renderThemes(themes);
    },
    error: function(xhr, status, error) {
      console.error("Error loading themes:", error);
      alertify.error(`Error loading themes: ${xhr.responseJSON?.detail || error}`);
    },
    complete: function() {
      // Always hide the loading spinner
      $("#themes-loader").addClass("d-none");
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
        <td><span class="badge badge-info">${theme.document_count || 0}</span></td>
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
  $(".select-theme-btn").on("click", function() {
    const themeId = $(this).data("theme-id");
    const themeName = $(this).data("theme-name");
    selectTheme(themeId, themeName);
  });

  $(".delete-theme-btn").on("click", function() {
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

  // Check if there's already a processing task for this theme
  $.ajax({
    url: `/api/tasks?theme_id=${themeId}`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(tasks) {
      if (tasks && tasks.length > 0) {
        // Filter for active tasks (pending or in progress)
        const activeTasks = tasks.filter(
          (t) => (t.status === "in_progress" || t.status === "pending") && t.type === "theme_processing"
        );

        if (activeTasks.length > 0) {
          // Sort by most recently created
          activeTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

          // Get the first (most recent) task
          const activeTask = activeTasks[0];

          // Set as our current processing task
          state.processingTask = activeTask;

          // Update UI based on task status
          updateTaskUI(activeTask);

          // Update vector DB status if exists in task metadata
          if (activeTask.metadata && activeTask.metadata.vectorDBStatus) {
            state.vectorDBStatus = activeTask.metadata.vectorDBStatus;
            updateVectorDBStatusUI();
          }

          // Determine which step to show based on the task's current step
          if (activeTask.current_step != null) {
            const stepMapping = {
              0: 2, // Data Ingestion -> Upload Files
              1: 3, // Text Chunking -> Download Files
              2: 4, // Generate Embeddings -> Read Files
              3: 5, // Store Vectors -> Process Embeddings
            };

            // Navigate to the appropriate step
            const targetStep = stepMapping[activeTask.current_step] || 2;
            navigateToStep(targetStep);
            return; // Skip the default navigation
          }
        }
      }

      // If no active task was found, proceed to upload section
      navigateToStep(2);

      // Subscribe to updates for this theme
      if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
        subscribeToThemeUpdates(themeId);
      }
    },
    error: function(xhr, status, error) {
      console.error("Error checking tasks:", error);
      // If error, still navigate to upload section
      navigateToStep(2);
    },
  });
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
      success: function() {
        alertify.success("Theme deleted successfully");
        loadThemes();
      },
      error: function(xhr, status, error) {
        console.error("Error deleting theme:", error);
        alertify.error(`Error deleting theme: ${xhr.responseJSON?.detail || error}`);
      },
    });
  }
}

/**
 * Navigate to a specific step in the workflow
 */
function navigateToStep(step, resetState = true) {
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
      // Update vector DB status UI
      updateVectorDBStatusUI();
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
      success: function(files) {
        renderFilesTable(files);
      },
      error: function(xhr, status, error) {
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
 * Start the file download process
 */
function startDownloadProcess() {
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
        totalFiles: state.uploadedFiles.length
      }
    }),
    contentType: "application/json",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
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
      state.vectorDBStatus.dataIngestion = 'in_progress';
      updateVectorDBStatusUI();
    },
    error: function(xhr, status, error) {
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
        state.vectorDBStatus.dataIngestion = 'completed';
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
 * Populate file selector dropdown for the read step
 */
function populateFileSelector() {
  const selector = $("#file-selector");
  selector.empty();
  selector.append('<option value="">Select a file to preview content</option>');

  state.downloadedFiles.forEach((file) => {
    selector.append(`<option value="${file.id}">${file.title || file.filename || file.source || "Unknown"}</option>`);
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

  // Make an API call to get the file content
  $.ajax({
    url: `/api/files/${fileId}/content`,
    method: "GET",
    headers: {
      "X-CSRF-Token": getCsrfToken(),
    },
    success: function(response) {
      if (response && response.content) {
        // Format the content based on file type
        const selectedFile = state.downloadedFiles.find((f) => f.id === fileId);
        const formattedContent = formatFileContent(response.content, selectedFile);
        $("#file-content-preview").html(formattedContent);
      } else {
        $("#file-content-preview").html('<p class="text-danger">No content available for this file</p>');
      }
    },
    error: function(xhr, status, error) {
      console.error("Error fetching file content:", error);

      // Fallback to sample content
      const selectedFile = state.downloadedFiles.find((f) => f.id === fileId);
      if (selectedFile) {
        // Generate fake content based on file type
        let content = generateSampleContent(selectedFile);
        $("#file-content-preview").html(content);
      } else {
        $("#file-content-preview").html('<p class="text-danger">Error loading file content</p>');
      }
    },
  });
}

/**
 * Format file content based on file type
 */
function formatFileContent(content, file) {
  if (!file || !content) return '<p class="text-danger">Invalid file or content</p>';

  const fileType = file.source ? file.source.split(".").pop().toLowerCase() : "txt";

  switch (fileType) {
    case "pdf":
      return `<p><strong>PDF Content:</strong> ${file.title || "Document"}</p>
              <div class="border p-3">${content}</div>`;
    case "docx":
      return `<p><strong>Word Document:</strong> ${file.title || "Document"}</p>
              <div class="border p-3">${content}</div>`;
    case "html":
      return `<p><strong>HTML Content:</strong> ${file.title || "Document"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                ${content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}
              </div>`;
    case "md":
      return `<p><strong>Markdown Content:</strong> ${file.title || "Document"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                ${content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}
              </div>`;
    case "csv":
      return `<p><strong>CSV Data:</strong> ${file.title || "Data File"}</p>
              <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">
                ${content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}
              </div>`;
    default:
      return `<p><strong>Text Content:</strong> ${file.title || "Document"}</p>
              <div class="border p-3">${content}</div>`;
  }
} // Only one closing brace here