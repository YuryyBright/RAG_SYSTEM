// Main application entry point

// Define global state
const ChatState = {
  activeThemeId: 1, // Default to General Knowledge theme
  isRagMode: false,
  conversationId: null,
};

// Initialize application when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  // Initialize all modules
  FileHandlers.init();
  AdvancedSettings.init();

  // Load initial data
  APIService.loadThemes().catch(() => {
    alertify.error("Failed to load knowledge themes");
  });

  APIService.loadChatHistory().catch(() => {
    alertify.error("Failed to load chat history");
  });

  // Set up event handlers
  setupEventHandlers();

  // Initial scroll to bottom
  UIHandlers.scrollToBottom();
});

// Setup all event handlers
function setupEventHandlers() {
  // Send message form
  UIHandlers.elements.chatForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const messageText = UIHandlers.elements.messageInput.value.trim();
    const files = FileHandlers.getFiles();

    // Get advanced parameters if settings are open
    const advancedParams = {};
    if (document.getElementById("advancedSettings").classList.contains("active")) {
      Object.assign(advancedParams, AdvancedSettings.getParameters());
    }

    // Send message
    if (messageText || files.length > 0) {
      MessageHandlers.sendMessage(messageText, files, advancedParams).then(() => {
        // Clear attached files after sending
        FileHandlers.clearFiles();
      });
    }
  });

  // RAG mode toggle
  UIHandlers.elements.ragModeToggle.addEventListener("change", function (e) {
    ChatState.isRagMode = e.target.checked;
    UIHandlers.updateFileUploadVisibility(ChatState.isRagMode);

    // Show notification
    const modeText = ChatState.isRagMode ? "RAG Mode" : "Standard Mode";
    alertify.success(`Switched to ${modeText}`);
  });

  // Add keyboard shortcuts for sending messages (Ctrl+Enter or Command+Enter)
  UIHandlers.elements.messageInput.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      UIHandlers.elements.chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Theme selection
  document.getElementById("themesContainer").addEventListener("click", function (e) {
    const target = e.target.closest(".theme-pill");
    if (!target) return;

    // Update UI
    document.querySelectorAll(".theme-pill").forEach((pill) => {
      pill.classList.remove("badge-info");
      pill.classList.add("badge-secondary");
    });

    target.classList.remove("badge-secondary");
    target.classList.add("badge-info");

    // Update active theme ID
    ChatState.activeThemeId = parseInt(target.getAttribute("data-theme-id"));

    // Show notification if in RAG mode
    if (ChatState.isRagMode) {
      const themeName = target.textContent.trim();
      alertify.success(`Theme switched to "${themeName}"`);
    }
  });

  // Chat history selection
  document.getElementById("chatHistoryList").addEventListener("click", function (e) {
    const target = e.target.closest(".chat-history-item");
    if (!target) return;

    const chatId = target.getAttribute("data-id");
    MessageHandlers.loadChat(chatId);

    // Mark selected item
    document.querySelectorAll(".chat-history-item").forEach((item) => {
      item.classList.remove("active");
    });
    target.classList.add("active");
  });

  // Clear history button
  document.getElementById("clearHistoryBtn").addEventListener("click", function () {
    if (confirm("Are you sure you want to clear all chat history?")) {
      APIService.clearChatHistory()
        .then(() => {
          document.getElementById("chatHistoryList").innerHTML = "";
          alertify.success("Chat history cleared");

          // Start new conversation
          window.location.reload();
        })
        .catch(() => {
          alertify.error("Failed to clear chat history");
        });
    }
  });

  // Handle Enter key for new lines vs sending
  UIHandlers.elements.messageInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      UIHandlers.elements.chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Listen for code blocks in messages and apply syntax highlighting
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            // Element node
            const codeBlocks = node.querySelectorAll("pre code");
            if (codeBlocks.length > 0 && window.hljs) {
              codeBlocks.forEach((block) => {
                hljs.highlightElement(block);
              });
            }
          }
        });
      }
    });
  });

  observer.observe(UIHandlers.elements.chatContainer, {
    childList: true,
    subtree: true,
  });

  // Window resize handler for mobile optimization
  window.addEventListener("resize", function () {
    UIHandlers.scrollToBottom();
  });

  // New chat button
  const newChatBtn = document.createElement("button");
  newChatBtn.className = "btn btn-sm btn-outline-primary mr-2";
  newChatBtn.innerHTML = '<i class="fas fa-plus mr-1"></i> New Chat';
  newChatBtn.addEventListener("click", function () {
    // Start new conversation (reload page)
    window.location.reload();
  });

  // Insert new chat button next to clear history
  document
    .getElementById("clearHistoryBtn")
    .parentNode.insertBefore(newChatBtn, document.getElementById("clearHistoryBtn"));
}

// Export ChatState to make it accessible
window.ChatState = ChatState;
