/**
 * Main Application Entry Point (jQuery Version)
 * Handles Chat Initialization, Event Binding, and Dynamic Model Loading
 */

import { AdvancedSettings } from "./advanced-settings.js";
import { APIService } from "./api-service.js";
import { FileHandlers } from "./file-handlers.js";
import { UIHandlers } from "./ui-handlers.js";
import { MessageHandlers } from "./message-handlers.js";
import { SidebarHandlers } from "./sidebar-handlers.js"; // Import the new module

// Global ChatState for application state management
window.ChatState = {
  activeThemeId: 1, // Default: General Knowledge theme
  isRagMode: false,
  conversationId: null,
  activeModelId: null, // Will be set when models are loaded
};

// Export services to global scope for compatibility
window.APIService = APIService;
window.UIHandlers = UIHandlers;
window.MessageHandlers = MessageHandlers;
window.FileHandlers = FileHandlers;
window.SidebarHandlers = SidebarHandlers; // Export to global scope

$(document).ready(function () {
  // Initialize modules
  FileHandlers.init();
  AdvancedSettings.init();
  SidebarHandlers.init(); // Initialize the sidebar handlers
  UIHandlers.initToastSystem();

  // Load initial themes and chat history
  APIService.loadThemes().catch(() => alertify.error("Failed to load knowledge themes"));
  APIService.loadChatHistory().catch(() => alertify.error("Failed to load chat history"));

  // Always attach model click
  $("#LLMContainer").on("click", ".model-pill", function () {
    $(".model-pill", $("#LLMContainer")).removeClass("badge-info").addClass("badge-secondary");
    $(this).removeClass("badge-secondary").addClass("badge-info");

    window.ChatState.activeModelId = $(this).data("model-id");

    alertify.success(`Model switched to: ${$(this).text().trim()}`);
  });

  // Load models and render if possible
  APIService.loadModels()
    .then(renderModels)
    .catch(() => alertify.error("Failed to load models"));

  // Setup other handlers (excluding those now in SidebarHandlers)
  setupEventHandlers();

  // Scroll chat to bottom
  UIHandlers.scrollToBottom();
});

/**
 * Setup all event handlers
 */
function setupEventHandlers() {
  const $chatForm = $(UIHandlers.elements.$chatForm);
  const $messageInput = $(UIHandlers.elements.$messageInput);
  const $ragToggle = $(UIHandlers.elements.$ragModeToggle);

  // Submit message handler
  $chatForm.on("submit", function (e) {
    e.preventDefault();

    const messageText = $messageInput.val().trim();
    const files = FileHandlers.getFiles();
    const advancedParams = {};

    if ($("#advancedSettings").hasClass("active")) {
      Object.assign(advancedParams, AdvancedSettings.getParameters());
    }

    if (messageText || files.length > 0) {
      MessageHandlers.sendMessage(messageText, files, advancedParams).then(() => FileHandlers.clearFiles());
    }
  });

  // RAG mode toggle
  $ragToggle.on("change", function () {
    window.ChatState.isRagMode = this.checked;
    UIHandlers.updateFileUploadVisibility(window.ChatState.isRagMode);
    alertify.success(`Switched to ${window.ChatState.isRagMode ? "RAG Mode" : "Standard Mode"}`);
  });

  // Syntax highlighting observer
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) {
          $(node)
            .find("pre code")
            .each(function () {
              if (window.hljs) hljs.highlightElement(this);
            });
        }
      });
    });
  });

  // Use the jQuery object's get() method to access the DOM element
  observer.observe(UIHandlers.elements.$chatContainer.get(0), { childList: true, subtree: true });

  // Handle window resize
  $(window).on("resize", UIHandlers.scrollToBottom);
}

/**
 * Render available models dynamically into the LLM container.
 * @param {Array} models - Array of model objects [{ id: string, name: string }]
 */
function renderModels(models) {
  if (!models || models.length === 0) {
    console.error("No models available to render");
    return;
  }

  const $container = $("#LLMContainer");
  // Clear any existing content (including placeholders)
  $container.empty();

  models.forEach((model, index) => {
    const badgeClass = index === 0 ? "badge-info" : "badge-secondary";
    $container.append(`
      <div class="badge ${badgeClass} theme-pill m-1 p-2" data-model-id="${model.id}">
        ${model.name}
      </div>
    `);
  });

  // Set the active model to the first one by default
  window.ChatState.activeModelId = models[0].id;
}

// Initialize toast system if alertify is not available
UIHandlers.initToastSystem = function () {
  if (!window.alertify) {
    window.alertify = {
      success: function (message) {
        UIHandlers.showToast(message, "success");
      },
      error: function (message) {
        UIHandlers.showToast(message, "error");
      },
      info: function (message) {
        UIHandlers.showToast(message, "info");
      },
    };
  }
};
