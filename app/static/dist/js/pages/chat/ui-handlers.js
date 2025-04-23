// =====================================================================
// ui-handlers.js - FIXED VERSION
// =====================================================================

export const UIHandlers = {
  // DOM Element references
  elements: {
    $chatContainer: $("#chatContainer"),
    $typingIndicator: $("#typingIndicator"),
    $messageInput: $("#messageInput"),
    $chatForm: $("#chatForm"),
    $ragModeToggle: $("#ragModeToggle"),
    $themesContainer: $("#themesContainer"),
    $chatHistoryList: $("#chatHistoryList"),
    $clearHistoryBtn: $("#clearHistoryBtn"),
    $fileUploadContainer: $("#fileUploadContainer"),
  },

  initElements: function () {
    // Re-initialize element references in case they were dynamically created
    this.elements.$chatContainer = $("#chatContainer");
    this.elements.$typingIndicator = $("#typingIndicator");
    this.elements.$messageInput = $("#messageInput");
    this.elements.$chatForm = $("#chatForm");
    this.elements.$ragModeToggle = $("#ragModeToggle");
    this.elements.$themesContainer = $("#themesContainer");
    this.elements.$chatHistoryList = $("#chatHistoryList");
    this.elements.$clearHistoryBtn = $("#clearHistoryBtn");
    this.elements.$fileUploadContainer = $("#fileUploadContainer");
  },

  formatMessage: function (text) {
    if (!text) return "";

    let formatted = text
      .replace(
        /```(\w+)\n([\s\S]*?)```/g,
        (match, lang, code) => `<pre><code class="language-${lang}">${this.escapeHtml(code.trim())}</code></pre>`
      )
      .replace(/```([\s\S]*?)```/g, (match, code) => `<pre><code>${this.escapeHtml(code.trim())}</code></pre>`)
      .replace(/`([^`]+)`/g, (match, code) => `<code>${this.escapeHtml(code)}</code>`)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/^\s*[\-\*]\s+(.+)$/gm, "<li>$1</li>")
      .replace(/^\s*(\d+)\.\s+(.+)$/gm, "<li>$2</li>")
      .replace(/\n/g, "<br>");

    formatted = formatted.replace(/<\/li>\s*<br><li>/g, "</li><li>");

    // Fix list formatting - wrap consecutive <li> elements in <ul>
    const liRegex = /<li>.*?<\/li>/g;
    const liMatches = formatted.match(liRegex);

    if (liMatches) {
      // Find consecutive li elements
      let currentHTML = formatted;
      let startIndex = currentHTML.indexOf("<li>");

      while (startIndex !== -1) {
        // Find the end of consecutive li tags
        let endIndex = startIndex;
        let liCount = 0;
        let nextLiPos = currentHTML.indexOf("<li>", endIndex);

        while (nextLiPos !== -1) {
          const endLiPos = currentHTML.indexOf("</li>", endIndex) + 5;
          if (nextLiPos - endLiPos > 10) break; // Not consecutive
          endIndex = endLiPos;
          liCount++;
          nextLiPos = currentHTML.indexOf("<li>", endLiPos);
        }

        if (liCount > 0) {
          // We found consecutive li elements
          const beforeList = currentHTML.substring(0, startIndex);
          const list = currentHTML.substring(startIndex, endIndex);
          const afterList = currentHTML.substring(endIndex);

          // Wrap in ul tags if not already wrapped
          if (!list.includes("<ul>")) {
            currentHTML = beforeList + "<ul>" + list + "</ul>" + afterList;
          }
        }

        // Find next li start
        startIndex = currentHTML.indexOf("<li>", startIndex + 1);
      }

      formatted = currentHTML;
    }

    return formatted;
  },

  escapeHtml: function (unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  addMessage: function (text, sender, isError = false, attachments = []) {
    const now = new Date();
    const timeString = now.getHours().toString().padStart(2, "0") + ":" + now.getMinutes().toString().padStart(2, "0");
    const formattedText = this.formatMessage(text);

    const messageClass = sender === "user" ? "user-message" : "ai-message";
    const errorClass = isError ? " text-danger" : "";

    let $message = $(`
      <div class="message ${messageClass}${errorClass}">
        <div class="message-content">${formattedText}</div>
      </div>
    `);

    if (attachments && attachments.length > 0) {
      let $attachments = $('<div class="message-attachments"></div>');
      attachments.forEach((attachment) => {
        let icon = "fa-file";
        const ext = attachment.name.split(".").pop().toLowerCase();
        if (["pdf"].includes(ext)) icon = "fa-file-pdf";
        if (["doc", "docx"].includes(ext)) icon = "fa-file-word";
        if (["xls", "xlsx", "csv"].includes(ext)) icon = "fa-file-excel";
        if (["txt", "md"].includes(ext)) icon = "fa-file-alt";
        if (["html", "css", "js"].includes(ext)) icon = "fa-file-code";
        if (["jpg", "jpeg", "png", "gif", "svg"].includes(ext)) icon = "fa-file-image";

        $attachments.append(`
          <div class="message-attachment">
            <i class="fas ${icon}"></i> ${attachment.name} (${this.formatFileSize(attachment.size)})
          </div>
        `);
      });
      $message.append($attachments);
    }

    $message.append(`<div class="message-time">${timeString}</div>`);

    // Make sure typing indicator exists
    if (this.elements.$typingIndicator.length === 0) {
      this.elements.$typingIndicator = $(
        '<div class="typing-indicator" id="typingIndicator"><span></span><span></span><span></span></div>'
      );
      this.elements.$chatContainer.append(this.elements.$typingIndicator);
    }

    this.elements.$typingIndicator.before($message);

    // Apply syntax highlighting if available
    if (window.hljs) {
      $message.find("pre code").each(function () {
        hljs.highlightElement(this);
      });
    }

    this.scrollToBottom();

    if (sender === "user") {
      this.elements.$messageInput.val("").css("height", "auto").focus();
    }
  },

  formatFileSize: function (bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  },

  showTypingIndicator: function (show = true) {
    if (this.elements.$typingIndicator.length === 0) {
      this.elements.$typingIndicator = $(
        '<div class="typing-indicator" id="typingIndicator"><span></span><span></span><span></span></div>'
      );
      this.elements.$chatContainer.append(this.elements.$typingIndicator);
    }
    this.elements.$typingIndicator.css("display", show ? "block" : "none");
    if (show) this.scrollToBottom();
  },

  // FIXED: This function now actually scrolls to the bottom
  scrollToBottom: function () {
    const $container = this.elements.$chatContainer;
    if ($container && $container.length) {
      $container.animate({ scrollTop: $container[0].scrollHeight }, 100);
    }
  },

  formatTimeAgo: function (date) {
    if (!(date instanceof Date)) {
      date = new Date(date);
      if (isNaN(date.getTime())) {
        return "unknown time";
      }
    }

    const now = new Date();
    const diffSecs = Math.floor((now - date) / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  },

  updateFileUploadVisibility: function (isRagMode) {
    if (!this.elements.$fileUploadContainer) {
      this.elements.$fileUploadContainer = $("#fileUploadContainer");
    }

    if (this.elements.$fileUploadContainer.length) {
      if (isRagMode) {
        this.elements.$fileUploadContainer.fadeOut(300);
      } else {
        this.elements.$fileUploadContainer.fadeIn(300);
      }
    }
  },

  initAutoResizeTextarea: function () {
    const $textarea = this.elements.$messageInput;
    if ($textarea && $textarea.length) {
      $textarea.off("input").on("input", function () {
        $(this).css("height", "auto");
        const maxHeight = 150;
        const scrollHeight = this.scrollHeight;
        $(this).css("height", (scrollHeight > maxHeight ? maxHeight : scrollHeight) + "px");
      });
    }
  },

  showToast: function (message, type = "success") {
    if (window.alertify) {
      alertify[type](message);
      return;
    }

    const $toast = $(`<div class="toast toast-${type}">${message}</div>`).appendTo("body");

    setTimeout(() => {
      $toast.addClass("show");
      setTimeout(() => {
        $toast.removeClass("show");
        setTimeout(() => $toast.remove(), 300);
      }, 3000);
    }, 100);
  },
};

// Initialize on document ready
$(function () {
  UIHandlers.initElements();
  UIHandlers.initAutoResizeTextarea();

  // Create toast styles if needed
  if (!window.alertify) {
    const style = `<style>
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
      .toast-success { background-color: #10b981; }
      .toast-error { background-color: #ef4444; }
      .toast-info { background-color: #3b82f6; }
    </style>`;
    $("head").append(style);
  }
});
