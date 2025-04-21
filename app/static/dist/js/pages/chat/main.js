/**
 * Main Application Entry Point (jQuery Version)
 * Handles Chat Initialization, Event Binding, and Dynamic Model Loading
 */

// Define global chat state
const ChatState = {
  activeThemeId: 1, // Default: General Knowledge theme
  isRagMode: false,
  conversationId: null,
};

$(document).ready(function () {
  // Initialize modules
  FileHandlers.init();
  AdvancedSettings.init();

  // Load initial themes and chat history
  APIService.loadThemes().catch(() => alertify.error("Failed to load knowledge themes"));
  APIService.loadChatHistory().catch(() => alertify.error("Failed to load chat history"));
  APIService.loadModels()
    .then(renderModels)
    .catch(() => alertify.error("Failed to load models"));

  // Setup event handlers
  setupEventHandlers();

  // Scroll chat to bottom
  UIHandlers.scrollToBottom();
});

/**
 * Setup all event handlers
 */
function setupEventHandlers() {
  const $chatForm = $(UIHandlers.elements.chatForm);
  const $messageInput = $(UIHandlers.elements.messageInput);
  const $ragToggle = $(UIHandlers.elements.ragModeToggle);

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
    ChatState.isRagMode = this.checked;
    UIHandlers.updateFileUploadVisibility(ChatState.isRagMode);
    alertify.success(`Switched to ${ChatState.isRagMode ? "RAG Mode" : "Standard Mode"}`);
  });

  // Ctrl+Enter or Cmd+Enter to send
  $messageInput.on("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      $chatForm.submit();
    }
  });

  // Theme selection
  $("#themesContainer").on("click", ".theme-pill", function () {
    $(".theme-pill").removeClass("badge-info").addClass("badge-secondary");
    $(this).removeClass("badge-secondary").addClass("badge-info");
    ChatState.activeThemeId = parseInt($(this).data("theme-id"));

    if (ChatState.isRagMode) {
      alertify.success(`Theme switched to "${$(this).text().trim()}"`);
    }
  });

  // Chat history load
  $("#chatHistoryList").on("click", ".chat-history-item", function () {
    const chatId = $(this).data("id");
    MessageHandlers.loadChat(chatId);

    $(".chat-history-item").removeClass("active");
    $(this).addClass("active");
  });

  // Clear chat history
  $("#clearHistoryBtn").on("click", function () {
    if (confirm("Are you sure you want to clear all chat history?")) {
      APIService.clearChatHistory()
        .then(() => {
          $("#chatHistoryList").empty();
          alertify.success("Chat history cleared");
          location.reload();
        })
        .catch(() => alertify.error("Failed to clear chat history"));
    }
  });

  // Handle Enter vs Shift+Enter
  $messageInput.on("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $chatForm.submit();
    }
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

  observer.observe(UIHandlers.elements.chatContainer[0], { childList: true, subtree: true });

  // Handle window resize
  $(window).on("resize", UIHandlers.scrollToBottom);

  // New chat button
  const $newChatBtn = $(
    '<button class="btn btn-sm btn-outline-primary mr-2"><i class="fas fa-plus mr-1"></i> New Chat</button>'
  );
  $newChatBtn.on("click", function () {
    location.reload();
  });
  $("#clearHistoryBtn").before($newChatBtn);
}

/**
 * Render models dynamically into the LLM container
 * @param {Array} models - Array of models [{id, name}]
 */
function renderModels(models) {
  const $container = $("#LLMContainer");
  $container.empty();

  models.forEach((model, index) => {
    const $badge = $("<div></div>", {
      class: "badge badge-secondary theme-pill m-1",
      "data-theme-id": model.id,
      text: model.name,
    });

    if (index === 0) $badge.removeClass("badge-secondary").addClass("badge-info");

    $container.append($badge);
  });
}

/**
 * API Service for fetching backend data
 */
const APIService = {
  loadThemes() {
    return fetch("/api/v1/themes").then((res) => (res.ok ? res.json() : Promise.reject()));
  },

  loadChatHistory() {
    return fetch("/api/v1/chat/history").then((res) => (res.ok ? res.json() : Promise.reject()));
  },

  clearChatHistory() {
    return fetch("/api/v1/chat/clear", { method: "POST" }).then((res) => (res.ok ? res.json() : Promise.reject()));
  },

  loadModels() {
    return fetch("/api/v1/models")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load models");
        return res.json();
      })
      .then((data) => data.models);
  },
};

// Export ChatState globally
window.ChatState = ChatState;
