// =====================================================================
// main.js - IMPROVED VERSION
// =====================================================================

/**
 * Main Application Entry Point (jQuery Version)
 * Handles Chat Initialization, Event Binding, and Dynamic Model Loading
 */

import { AdvancedSettings } from "./advanced-settings.js";
import { APIService } from "./api-service.js";
import { FileHandlers } from "./file-handlers.js";
import { UIHandlers } from "./ui-handlers.js";
import { MessageHandlers } from "./message-handlers.js";
import { SidebarHandlers } from "./sidebar-handlers.js";

// Global ChatState for application state management
window.ChatState = {
  activeThemeId: 1, // Default: General Knowledge theme
  isRagMode: false,
  conversationId: null,
  activeModelId: null, // Will be set when models are loaded
  models: [], // Store all available models
};

// Export services to global scope for compatibility
window.APIService = APIService;
window.UIHandlers = UIHandlers;
window.MessageHandlers = MessageHandlers;
window.FileHandlers = FileHandlers;
window.SidebarHandlers = SidebarHandlers;

// Initialize application when DOM is ready
$(document).ready(function () {
  // Initialize UI elements
  UIHandlers.initElements();

  // Initialize modules
  FileHandlers.init();
  AdvancedSettings.init();
  SidebarHandlers.init();
  UIHandlers.initToastSystem();
  UIHandlers.initAutoResizeTextarea();

  // Load initial data with proper error handling
  Promise.all([
    APIService.loadThemes().catch((err) => {
      console.error("Theme loading error:", err);
      UIHandlers.showToast("Failed to load knowledge themes", "error");
      return [];
    }),
    APIService.loadChatHistory().catch((err) => {
      console.error("Chat history loading error:", err);
      UIHandlers.showToast("Failed to load chat history", "error");
      return { history: [] };
    }),
    APIService.loadModels().catch((err) => {
      console.error("Model loading error:", err);
      UIHandlers.showToast("Failed to load models", "error");
      return [];
    }),
  ]).then(([themes, history, models]) => {
    // Render models after loading
    if (models && models.length > 0) {
      renderModels(models);
    }

    // Initialize other components after data is loaded
    setupEventHandlers();

    // Scroll chat to bottom
    UIHandlers.scrollToBottom();
  });
});

/**
 * Setup all event handlers
 */
function setupEventHandlers() {
  // Attach model click handler
  $("#LLMContainer")
    .off("click")
    .on("click", ".model-pill", function () {
      $(".model-pill", $("#LLMContainer")).removeClass("badge-info").addClass("badge-secondary");
      $(this).removeClass("badge-secondary").addClass("badge-info");

      const previousModelId = window.ChatState.activeModelId;
      window.ChatState.activeModelId = $(this).data("model-id");

      if (previousModelId !== window.ChatState.activeModelId) {
        UIHandlers.showToast(`Model switched to: ${$(this).text().trim()}`, "success");
      }
    });

  const $chatForm = $(UIHandlers.elements.$chatForm);
  const $messageInput = $(UIHandlers.elements.$messageInput);
  const $ragToggle = $(UIHandlers.elements.$ragModeToggle);

  // Submit message handler
  $chatForm.off("submit").on("submit", function (e) {
    e.preventDefault();

    const messageText = $messageInput.val().trim();
    const files = FileHandlers.getFiles();
    const advancedParams = {};

    if ($("#advancedSettings").hasClass("active")) {
      Object.assign(advancedParams, AdvancedSettings.getParameters());
    }

    if (messageText || (files && files.length > 0)) {
      MessageHandlers.sendMessage(messageText, files, advancedParams)
        .then(() => FileHandlers.clearFiles())
        .catch((err) => console.error("Message sending error:", err));
    }
  }); // RAG mode toggle
  $ragToggle.off("change").on("change", function () {
    window.ChatState.isRagMode = this.checked;
    UIHandlers.updateFileUploadVisibility(window.ChatState.isRagMode);
    UIHandlers.showToast(`Switched to ${window.ChatState.isRagMode ? "RAG Mode" : "Standard Mode"}`, "success");
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

  // Start observing chat container for code blocks
  const chatContainer = UIHandlers.elements.$chatContainer.get(0);
  if (chatContainer) {
    observer.observe(chatContainer, { childList: true, subtree: true });
  }

  // Handle window resize
  $(window).off("resize.chatScroll").on("resize.chatScroll", UIHandlers.scrollToBottom.bind(UIHandlers));
}

/**
 * Render available models dynamically into the LLM container.
 * @param {Array} models - Array of model objects [{ id: string, name: string }]
 */
function renderModels(models) {
  if (!models || !Array.isArray(models) || models.length === 0) {
    console.error("No valid models available to render");
    return;
  }

  const $container = $("#LLMContainer");
  if (!$container.length) {
    console.error("LLM container not found in DOM");
    return;
  }

  // Clear any existing content (including placeholders)
  $container.empty();

  models.forEach((model, index) => {
    if (!model || !model.id || !model.name) {
      console.warn("Invalid model object:", model);
      return;
    }

    const badgeClass = index === 0 ? "badge-info" : "badge-secondary";
    $container.append(`
      <div class="badge ${badgeClass} model-pill m-1 p-2" data-model-id="${model.id}">
        ${model.name}
      </div>
    `);
  });

  // Set the active model to the first one by default
  if (models.length > 0) {
    window.ChatState.activeModelId = models[0].id;
  }
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
