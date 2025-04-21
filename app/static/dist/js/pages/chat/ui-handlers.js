// UI related functionality

const UIHandlers = {
  // DOM Element references
  elements: {
    chatContainer: document.getElementById("chatContainer"),
    typingIndicator: document.getElementById("typingIndicator"),
    messageInput: document.getElementById("messageInput"),
    chatForm: document.getElementById("chatForm"),
    ragModeToggle: document.getElementById("ragModeToggle"),
    themesContainer: document.getElementById("themesContainer"),
    chatHistoryList: document.getElementById("chatHistoryList"),
    clearHistoryBtn: document.getElementById("clearHistoryBtn"),
    fileUploadContainer: document.getElementById("fileUploadContainer"),
  },

  // Format chat message with markdown and code highlighting
  formatMessage(text) {
    if (!text) return "";

    // Basic formatting - replace code blocks with proper syntax highlighting
    let formatted = text
      // Code blocks with language
      .replace(/```(\w+)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang}">${this.escapeHtml(code.trim())}</code></pre>`;
      })
      // Code blocks without language
      .replace(/```([\s\S]*?)```/g, (match, code) => {
        return `<pre><code>${this.escapeHtml(code.trim())}</code></pre>`;
      })
      // Inline code
      .replace(/`([^`]+)`/g, (match, code) => {
        return `<code>${this.escapeHtml(code)}</code>`;
      })
      // Bold
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      // Italic
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      // Lists (unordered)
      .replace(/^\s*[\-\*]\s+(.+)$/gm, "<li>$1</li>")
      // Lists (ordered)
      .replace(/^\s*(\d+)\.\s+(.+)$/gm, "<li>$2</li>")
      // Line breaks
      .replace(/\n/g, "<br>");

    // Handle sequential list items
    formatted = formatted.replace(/<\/li>\s*<br><li>/g, "</li><li>");
    formatted = formatted.replace(/<li>(.+?)(<br>)?<\/li>/g, function (match) {
      if (match.includes("<li>") && !match.includes("<ul>")) {
        return "<ul>" + match + "</ul>";
      }
      return match;
    });

    return formatted;
  },

  // Escape HTML for code blocks
  escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  // Add a message to the chat
  addMessage(text, sender, isError = false, attachments = []) {
    const now = new Date();
    const timeString = now.getHours().toString().padStart(2, "0") + ":" + now.getMinutes().toString().padStart(2, "0");

    // Format message with markdown
    const formattedText = this.formatMessage(text);

    // Create message element
    const messageClass = sender === "user" ? "user-message" : "ai-message";
    const errorClass = isError ? " text-danger" : "";

    let messageHtml = `
      <div class="message ${messageClass}${errorClass}">
        <div class="message-content">${formattedText}</div>
    `;

    // Add attachments if any
    if (attachments && attachments.length > 0) {
      messageHtml += `<div class="message-attachments">`;

      attachments.forEach((attachment) => {
        // Get file icon based on extension
        const extension = attachment.name.split(".").pop().toLowerCase();
        let icon = "fa-file";

        if (["pdf"].includes(extension)) icon = "fa-file-pdf";
        if (["doc", "docx"].includes(extension)) icon = "fa-file-word";
        if (["xls", "xlsx", "csv"].includes(extension)) icon = "fa-file-excel";
        if (["txt", "md"].includes(extension)) icon = "fa-file-alt";
        if (["html", "css", "js"].includes(extension)) icon = "fa-file-code";
        if (["jpg", "jpeg", "png", "gif", "svg"].includes(extension)) icon = "fa-file-image";

        messageHtml += `
          <div class="message-attachment">
            <i class="fas ${icon}"></i>
            ${attachment.name} (${this.formatFileSize(attachment.size)})
          </div>
        `;
      });

      messageHtml += `</div>`;
    }

    messageHtml += `
        <div class="message-time">${timeString}</div>
      </div>
    `;

    // Insert before typing indicator
    this.elements.typingIndicator.insertAdjacentHTML("beforebegin", messageHtml);

    // Apply syntax highlighting if available
    if (window.hljs) {
      const codeBlocks = document.querySelectorAll("pre code");
      codeBlocks.forEach((block) => {
        hljs.highlightElement(block);
      });
    }

    // Scroll to bottom
    this.scrollToBottom();

    // Clear message input (only for user messages)
    if (sender === "user") {
      this.elements.messageInput.value = "";
      this.elements.messageInput.style.height = "auto";
      this.elements.messageInput.focus();
    }
  },

  // Format file size nicely
  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    else return (bytes / 1048576).toFixed(1) + " MB";
  },

  // Toggle typing indicator
  showTypingIndicator(show = true) {
    this.elements.typingIndicator.style.display = show ? "block" : "none";

    // Also scroll to bottom when showing the typing indicator
    if (show) {
      this.scrollToBottom();
    }
  },

  // Scroll chat to bottom with smooth animation
  scrollToBottom() {
    this.elements.chatContainer.scrollTo({
      top: this.elements.chatContainer.scrollHeight,
      behavior: "smooth",
    });
  },

  // Format time ago for chat history
  formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) {
      return "just now";
    } else if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  },

  // Toggle visibility of file upload based on RAG mode with animation
  updateFileUploadVisibility(isRagMode) {
    if (isRagMode) {
      // Fade out and hide
      this.elements.fileUploadContainer.style.opacity = "0";
      setTimeout(() => {
        this.elements.fileUploadContainer.style.display = "none";
      }, 300);
    } else {
      // Show and fade in
      this.elements.fileUploadContainer.style.display = "block";
      setTimeout(() => {
        this.elements.fileUploadContainer.style.opacity = "1";
      }, 10);
    }
  },

  // Auto-resize textarea as content grows
  initAutoResizeTextarea() {
    const textarea = this.elements.messageInput;
    textarea.addEventListener("input", function () {
      this.style.height = "auto";
      const maxHeight = 150; // max height in pixels
      const scrollHeight = this.scrollHeight;
      this.style.height = (scrollHeight > maxHeight ? maxHeight : scrollHeight) + "px";
    });
  },

  // Show a toast notification
  showToast(message, type = "success") {
    // Check if alertify is available
    if (window.alertify) {
      alertify[type](message);
      return;
    }

    // Fallback simple toast implementation
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("show");
      setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => document.body.removeChild(toast), 300);
      }, 3000);
    }, 100);
  },
};

// Initialize auto-resize for textarea
document.addEventListener("DOMContentLoaded", function () {
  UIHandlers.initAutoResizeTextarea();

  // Add CSS for toast notifications (fallback if alertify not available)
  if (!window.alertify) {
    const style = document.createElement("style");
    style.textContent = `
      .toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 9999;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
      }
      .toast.show {
        opacity: 1;
        transform: translateY(0);
      }
      .toast-success {
        background-color: #10b981;
      }
      .toast-error {
        background-color: #ef4444;
      }
      .toast-info {
        background-color: #3b82f6;
      }
    `;
    document.head.appendChild(style);
  }
});

// Export the module
window.UIHandlers = UIHandlers;
