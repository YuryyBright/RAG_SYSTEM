/**
 * file-preview.js
 * Handles file content preview functionality for the RAG pipeline
 */

import { state } from "./state.js";
import { getCsrfToken } from "./utils.js";

/**
 * Populate file selector dropdown for the read step
 */
export function populateFileSelector() {
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
export function showFileContentPreview() {
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
    success: function (response) {
      if (response && response.content) {
        // Format the content based on file type
        const selectedFile = state.downloadedFiles.find((f) => f.id === fileId);
        const formattedContent = formatFileContent(response.content, selectedFile);
        $("#file-content-preview").html(formattedContent);
      } else {
        $("#file-content-preview").html('<p class="text-danger">No content available for this file</p>');
      }
    },
    error: function (xhr, status, error) {
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
}

/**
 * Generate sample content for preview
 */
export function generateSampleContent(file) {
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
