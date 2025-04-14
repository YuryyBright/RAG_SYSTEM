// Description: This script handles the user dashboard functionalities with improved CSRF token handling
$(document).ready(function () {
  // Global variables
  let activityPage = 1;
  const activityLimit = 10;
  let currentPeriod = "month";

  // Initialize components
  initializePasswordToggle();
  initializePasswordStrength();
  initializeAvatarUpload();

  // Load initial data
  loadUserStats(currentPeriod);
  loadApiKeys();
  loadActivity();
  loadSessions();
  loadNotificationSettings();

  // Ensure we have a valid CSRF token before operations
  function ensureCsrfToken() {
    const csrfToken = AuthManager.getCsrfToken();
    if (!csrfToken) {
      return AuthManager.refreshCsrfToken().then(() => {
        return AuthManager.getCsrfToken();
      });
    }
    return Promise.resolve(csrfToken);
  }

  // Handle profile form submission with CSRF protection
  $("#profile-form").on("submit", function (e) {
    e.preventDefault();

    const userData = {
      name: $("#inputName").val().trim(),
      email: $("#inputEmail").val().trim(),
      timezone: $("#inputTimezone").val(),
      theme: $("#inputTheme").val(),
    };

    // Validation
    if (!userData.name) {
      alertify.error("Name cannot be empty");
      return;
    }

    if (!userData.email || !isValidEmail(userData.email)) {
      alertify.error("Please enter a valid email address");
      return;
    }

    // Ensure CSRF token before submission
    ensureCsrfToken().then(() => {
      $.ajax({
        url: "/api/user/profile",
        type: "PUT",
        contentType: "application/json",
        data: JSON.stringify(userData),
        success: function (response) {
          alertify.success("Profile updated successfully!");
          // Update profile name in the sidebar and header if applicable
          $(".user-panel .info strong").text(userData.name);
          // Apply theme change if selected
          if (userData.theme !== "{{ user.theme }}") {
            setTimeout(function () {
              window.location.reload();
            }, 1000);
          }
        },
        error: function (xhr) {
          handleAjaxError(xhr, "Error updating profile");
        },
      });
    });
  });

  // Handle password form submission with enhanced CSRF protection
  $("#password-form").on("submit", function (e) {
    e.preventDefault();

    const currentPassword = $("#currentPassword").val();
    const newPassword = $("#newPassword").val();
    const confirmPassword = $("#confirmPassword").val();

    // Validation
    if (!currentPassword) {
      alertify.error("Please enter your current password");
      return;
    }

    if (!newPassword) {
      alertify.error("Please enter a new password");
      return;
    }

    if (newPassword.length < 8) {
      alertify.error("Password must be at least 8 characters long");
      return;
    }

    if (newPassword !== confirmPassword) {
      alertify.error("New passwords do not match!");
      return;
    }

    // Ensure CSRF token before submission
    ensureCsrfToken().then(() => {
      $.ajax({
        url: "/api/user/change-password",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
        success: function (response) {
          alertify.success("Password changed successfully!");
          $("#password-form")[0].reset();
          $(".password-strength .progress-bar")
            .css("width", "0%")
            .removeClass("bg-danger bg-warning bg-success")
            .addClass("bg-danger");
        },
        error: function (xhr) {
          handleAjaxError(xhr, "Error changing password");
        },
      });
    });
  });

  // Handle notification form submission with CSRF token
  $("#notification-form").on("submit", function (e) {
    e.preventDefault();

    const notificationSettings = {
      email_notifications: $("#emailNotifications").is(":checked"),
      browser_notifications: $("#browserNotifications").is(":checked"),
      login_alerts: $("#loginAlerts").is(":checked"),
      api_usage_alerts: $("#apiUsageAlerts").is(":checked"),
      file_activity_notifications: $("#fileActivityNotifications").is(":checked"),
    };

    ensureCsrfToken().then(() => {
      $.ajax({
        url: "/api/user/notifications",
        type: "PUT",
        contentType: "application/json",
        data: JSON.stringify(notificationSettings),
        success: function (response) {
          alertify.success("Notification settings updated successfully!");
        },
        error: function (xhr) {
          handleAjaxError(xhr, "Error updating notification settings");
        },
      });
    });
  });

  // API Keys functionality with improved CSRF handling
  $("#generate-api-key").on("click", function () {
    $("#apiKeyModal").modal("show");
    $("#new-key-container").hide();
    $("#create-api-key").show();
    $("#api-key-form")[0].reset();
  });

  $("#create-api-key").on("click", function () {
    const keyName = $("#key-name").val().trim();
    const keyExpiry = $("#key-expiry").val();

    if (!keyName) {
      alertify.error("Please provide a name for your API key");
      return;
    }

    $(this).prop("disabled", true).html('<i class="fas fa-spinner fa-spin"></i> Generating...');

    ensureCsrfToken().then(() => {
      $.ajax({
        url: "/api/user/apikeys",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          name: keyName,
          expiry_days: keyExpiry ? parseInt(keyExpiry) : null,
        }),
        success: function (response) {
          $("#new-api-key").val(response.key);
          $("#new-key-container").show();
          $("#create-api-key").hide();

          // Reload the API keys list
          loadApiKeys();
        },
        error: function (xhr) {
          handleAjaxError(xhr, "Error generating API key");
        },
        complete: function () {
          $("#create-api-key").prop("disabled", false).html("Generate Key");
        },
      });
    });
  });

  $("#copy-api-key").on("click", function () {
    const keyInput = document.getElementById("new-api-key");
    keyInput.select();
    document.execCommand("copy");
    alertify.success("API key copied to clipboard!");
  });

  // Avatar functionality with enhanced CSRF handling
  function initializeAvatarUpload() {
    $("#avatar-upload").on("change", function () {
      const file = this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          $("#avatar-preview").attr("src", e.target.result);
          $("#avatar-preview-container").show();
        };
        reader.readAsDataURL(file);
        $(".custom-file-label").text(file.name);
      }
    });

    // In the initializeAvatarUpload function:
    $("#upload-avatar").on("click", function () {
      const fileInput = $("#avatar-upload")[0];
      if (!fileInput.files || !fileInput.files[0]) {
        alertify.error("Please select an image to upload");
        return;
      }

      ensureCsrfToken()
        .then((csrfToken) => {
          // Ensure we wait for the promise to resolve
          const formData = new FormData();
          formData.append("avatar", fileInput.files[0]);

          $.ajax({
            url: "/api/user/avatar",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            headers: {
              "X-CSRF-Token": csrfToken, // Explicitly add the CSRF token here
            },
            beforeSend: function () {
              $("#upload-avatar").prop("disabled", true).html('<i class="fas fa-spinner fa-spin"></i> Uploading...');
            },
            success: function (response) {
              $(".profile-user-img").attr("src", response.avatar_url + "?t=" + new Date().getTime());
              $("#avatarModal").modal("hide");
              alertify.success("Profile picture updated successfully!");
            },
            error: function (xhr) {
              handleAjaxError(xhr, "Error uploading image");
            },
            complete: function () {
              $("#upload-avatar").prop("disabled", false).html('<i class="fas fa-upload mr-1"></i> Upload');
            },
          });
        })
        .catch((error) => {
          alertify.error("Failed to prepare for upload. Please try again.");
          console.error("CSRF token error:", error);
        });
    });

    $("#remove-avatar").on("click", function () {
      if (confirm("Are you sure you want to remove your profile picture?")) {
        ensureCsrfToken().then(() => {
          $.ajax({
            url: "/api/user/avatar",
            type: "DELETE",
            success: function (response) {
              $(".profile-user-img").attr("src", "/static/dist/img/user.png");
              $("#avatarModal").modal("hide");
              alertify.success("Profile picture removed");
            },
            error: function (xhr) {
              handleAjaxError(xhr, "Error removing profile picture");
            },
          });
        });
      }
    });
  }

  // Enhanced error handling for AJAX requests
  function handleAjaxError(xhr, defaultMessage) {
    // Handle specific CSRF token errors
    if (xhr.status === 403 && xhr.responseJSON && xhr.responseJSON.error === "csrf_token_invalid") {
      alertify.error("Session error. Please try again in a moment.");
      // AuthManager will auto-refresh the token via the ajaxSetup handler
      return;
    }

    try {
      const error = JSON.parse(xhr.responseText);
      alertify.error(defaultMessage + ": " + error.detail);
    } catch (e) {
      alertify.error(defaultMessage + ". Please try again.");
    }
  }

  // Password strength and toggle functionality
  function initializePasswordToggle() {
    $(".toggle-password").on("click", function () {
      const input = $(this).closest(".input-group").find("input");
      const icon = $(this).find("i");

      if (input.attr("type") === "password") {
        input.attr("type", "text");
        icon.removeClass("fa-eye").addClass("fa-eye-slash");
      } else {
        input.attr("type", "password");
        icon.removeClass("fa-eye-slash").addClass("fa-eye");
      }
    });
  }

  function initializePasswordStrength() {
    $("#newPassword").on("keyup", function () {
      const password = $(this).val();
      let strength = 0;

      if (password.length >= 8) strength += 25;
      if (password.match(/[a-z]+/)) strength += 25;
      if (password.match(/[A-Z]+/)) strength += 25;
      if (password.match(/[0-9]+/) || password.match(/[^a-zA-Z0-9]+/)) strength += 25;

      const progressBar = $(".password-strength .progress-bar");
      progressBar.css("width", strength + "%");

      if (strength < 50) {
        progressBar.removeClass("bg-warning bg-success").addClass("bg-danger");
      } else if (strength < 75) {
        progressBar.removeClass("bg-danger bg-success").addClass("bg-warning");
      } else {
        progressBar.removeClass("bg-danger bg-warning").addClass("bg-success");
      }
    });
  }

  // Helpers for loading data
  function loadUserStats(period) {
    $.ajax({
      url: "/api/user/stats?period=" + period,
      type: "GET",
      success: function (data) {
        // Update counters
        $("#queries-count").text(data.total_queries);
        $("#logins-count").text(data.total_logins);

        // Update charts
        updateQueryChart(data.query_data);
        updateDocChart(data.document_types);
      },
      error: function (xhr) {
        handleAjaxError(xhr, "Error loading user statistics");
      },
    });
  }

  function loadApiKeys() {
    $.ajax({
      url: "/api/user/apikeys",
      type: "GET",
      success: function (keys) {
        if (keys.length === 0) {
          $("#api-keys-list").html(
            '<div class="text-center p-3"><p class="text-muted">No API keys generated yet</p></div>'
          );
          return;
        }

        let html = '<ul class="list-group list-group-flush">';
        keys.forEach(function (key) {
          const expiryDate = key.expires_at ? new Date(key.expires_at).toLocaleDateString() : "Never";
          html += `
              <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <strong>${key.name}</strong>
                  <br>
                  <small class="text-muted">Last used: ${
                    key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "Never"
                  }</small>
                  <br>
                  <small class="text-muted">Expires: ${expiryDate}</small>
                </div>
                <button class="btn btn-sm btn-danger delete-api-key" data-key-id="${key.id}">
                  <i class="fas fa-trash"></i>
                </button>
              </li>
            `;
        });
        html += "</ul>";

        $("#api-keys-list").html(html);

        // Add event handlers for delete buttons
        $(".delete-api-key").on("click", function () {
          const keyId = $(this).data("key-id");
          deleteApiKey(keyId);
        });
      },
      error: function (xhr) {
        handleAjaxError(xhr, "Error loading API keys");
      },
    });
  }

  function deleteApiKey(keyId) {
    if (confirm("Are you sure you want to delete this API key? This action cannot be undone.")) {
      ensureCsrfToken().then(() => {
        $.ajax({
          url: "/api/user/apikeys/" + keyId,
          type: "DELETE",
          success: function () {
            alertify.success("API key deleted successfully");
            loadApiKeys();
          },
          error: function (xhr) {
            handleAjaxError(xhr, "Error deleting API key");
          },
        });
      });
    }
  }

  function loadActivity() {
    const activityType = $("#activity-filter").val();
    const url =
      "/api/user/activity?limit=" +
      activityLimit +
      "&page=" +
      activityPage +
      (activityType ? "&activity_type=" + activityType : "");

    $.ajax({
      url: url,
      type: "GET",
      success: function (data) {
        if (activityPage === 1) {
          $("#activity-list").empty();
        }

        if (data.activities.length === 0 && activityPage === 1) {
          $("#activity-list").html('<tr><td colspan="3" class="text-center">No activity records found</td></tr>');
          $("#load-more-activity").hide();
          return;
        }

        data.activities.forEach(function (activity) {
          const activityDate = new Date(activity.timestamp).toLocaleString();
          let badgeClass = "badge-secondary";
          let icon = "fa-info-circle";

          switch (activity.type) {
            case "login":
              badgeClass = "badge-success";
              icon = "fa-sign-in-alt";
              break;
            case "query":
              badgeClass = "badge-primary";
              icon = "fa-search";
              break;
            case "file_upload":
              badgeClass = "badge-info";
              icon = "fa-file-upload";
              break;
            case "file_delete":
              badgeClass = "badge-danger";
              icon = "fa-file-excel";
              break;
          }

          const row = `
              <tr>
                <td><span class="badge ${badgeClass}"><i class="fas ${icon} mr-1"></i> ${activity.type}</span></td>
                <td>${activity.description}</td>
                <td>${activityDate}</td>
              </tr>
            `;

          $("#activity-list").append(row);
        });

        // Show/hide load more button
        if (data.activities.length < activityLimit) {
          $("#load-more-activity").hide();
        } else {
          $("#load-more-activity").show();
        }
      },
      error: function (xhr) {
        handleAjaxError(xhr, "Error loading activity data");
      },
    });
  }

  function loadSessions() {
    $.ajax({
      url: "/api/user/sessions",
      type: "GET",
      success: function (sessions) {
        if (sessions.length === 0) {
          $("#sessions-list").html('<div class="text-center p-3"><p class="text-muted">No active sessions</p></div>');
          return;
        }

        let html = '<ul class="list-group list-group-flush">';
        sessions.forEach(function (session) {
          const isCurrentSession = session.is_current;
          const lastActivity = new Date(session.last_activity).toLocaleString();

          html += `
              <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <div>
                    <i class="fas fa-${session.device_type === "mobile" ? "mobile-alt" : "desktop"}"></i>
                    ${session.browser} on ${session.os}
                    ${isCurrentSession ? '<span class="badge badge-success ml-2">Current</span>' : ""}
                  </div>
                  <small class="text-muted">IP: ${session.ip_address}</small>
                  <br>
                  <small class="text-muted">Last activity: ${lastActivity}</small>
                </div>
                ${
                  !isCurrentSession
                    ? `
                  <button class="btn btn-sm btn-outline-danger revoke-session" data-session-id="${session.id}">
                    <i class="fas fa-times"></i>
                  </button>
                `
                    : ""
                }
              </li>
            `;
        });
        html += "</ul>";

        $("#sessions-list").html(html);

        // Add event handlers for revoke buttons
        $(".revoke-session").on("click", function () {
          const sessionId = $(this).data("session-id");
          revokeSession(sessionId);
        });
      },
      error: function (xhr) {
        handleAjaxError(xhr, "Error loading active sessions");
      },
    });
  }

  function revokeSession(sessionId) {
    ensureCsrfToken().then(() => {
      $.ajax({
        url: "/api/user/sessions/" + sessionId,
        type: "DELETE",
        success: function () {
          alertify.success("Session revoked successfully");
          loadSessions();
        },
        error: function (xhr) {
          handleAjaxError(xhr, "Error revoking session");
        },
      });
    });
  }

  $("#revoke-all-sessions").on("click", function () {
    if (confirm("Are you sure you want to revoke all other sessions? This will log you out from all other devices.")) {
      ensureCsrfToken().then(() => {
        $.ajax({
          url: "/api/user/sessions",
          type: "DELETE",
          success: function () {
            alertify.success("All other sessions revoked successfully");
            loadSessions();
          },
          error: function (xhr) {
            handleAjaxError(xhr, "Error revoking sessions");
          },
        });
      });
    }
  });

  function loadNotificationSettings() {
    $.ajax({
      url: "/api/user/notifications",
      type: "GET",
      success: function (settings) {
        $("#emailNotifications").prop("checked", settings.email_notifications);
        $("#browserNotifications").prop("checked", settings.browser_notifications);
        $("#loginAlerts").prop("checked", settings.login_alerts);
        $("#apiUsageAlerts").prop("checked", settings.api_usage_alerts);
        $("#fileActivityNotifications").prop("checked", settings.file_activity_notifications);
      },
      error: function (xhr) {
        handleAjaxError(xhr, "Error loading notification settings");
      },
    });
  }

  // Initialize charts
  function updateQueryChart(data) {
    const ctx = document.getElementById("queryChart").getContext("2d");

    if (window.queryChart) {
      window.queryChart.destroy();
    }

    window.queryChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.map((d) => d.label),
        datasets: [
          {
            label: "Queries",
            data: data.map((d) => d.count),
            backgroundColor: "rgba(60, 141, 188, 0.2)",
            borderColor: "rgba(60, 141, 188, 1)",
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: "rgba(60, 141, 188, 1)",
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0,
            },
          },
        },
      },
    });
  }

  function updateDocChart(data) {
    const ctx = document.getElementById("docChart").getContext("2d");

    if (window.docChart) {
      window.docChart.destroy();
    }

    const colors = [
      "rgba(60, 141, 188, 0.8)",
      "rgba(210, 214, 222, 0.8)",
      "rgba(255, 193, 7, 0.8)",
      "rgba(40, 167, 69, 0.8)",
      "rgba(220, 53, 69, 0.8)",
      "rgba(108, 117, 125, 0.8)",
    ];

    window.docChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.map((d) => d.type),
        datasets: [
          {
            data: data.map((d) => d.count),
            backgroundColor: colors.slice(0, data.length),
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: {
            position: "right",
          },
        },
      },
    });
  }

  // Event handlers for time period selections
  $(".btn-group [data-period]").on("click", function () {
    $(".btn-group [data-period]").removeClass("btn-primary").addClass("btn-outline-primary");
    $(this).removeClass("btn-outline-primary").addClass("btn-primary");
    currentPeriod = $(this).data("period");
    loadUserStats(currentPeriod);
  });

  // Activity filter
  $("#activity-filter").on("change", function () {
    activityPage = 1;
    loadActivity();
  });

  // Load more activity button
  $("#load-more-activity").on("click", function () {
    activityPage++;
    loadActivity();
  });

  // Handle export data with improved CSRF handling
  // Handle export data with improved CSRF handling
  $("#export-data").on("click", function () {
    $(this).prop("disabled", true).html('<i class="fas fa-spinner fa-spin"></i> Downloading...');

    ensureCsrfToken()
      .then((csrfToken) => {
        // Use XMLHttpRequest for more control over the download
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/api/user/export", true);
        xhr.setRequestHeader("X-CSRF-Token", csrfToken);
        xhr.responseType = "blob"; // Important: set the response type to blob

        xhr.onload = function () {
          if (this.status === 200) {
            // Create a blob URL and trigger download
            var blob = new Blob([this.response], { type: "application/json" });
            var downloadUrl = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = downloadUrl;
            a.download = "user_export.json"; // Filename for the download
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);

            // Reset button state
            $("#export-data").prop("disabled", false).html("Request Export");
            alertify.success("Download complete!");
          } else {
            // Handle errors
            alertify.error("Download failed. Please try again.");
            $("#export-data").prop("disabled", false).html("Request Export");
          }
        };

        xhr.onerror = function () {
          alertify.error("Download failed. Please try again.");
          $("#export-data").prop("disabled", false).html("Request Export");
        };

        xhr.send();
      })
      .catch(() => {
        alertify.error("Failed to prepare download. Please try again.");
        $("#export-data").prop("disabled", false).html("Request Export");
      });
  });
  // Handle account deactivation with enhanced CSRF protection
  $("#deactivate-account").on("click", function () {
    if (
      confirm("Are you sure you want to deactivate your account? You can reactivate it later by contacting support.")
    ) {
      ensureCsrfToken().then(() => {
        $.ajax({
          url: "/api/user/account",
          type: "POST",
          contentType: "application/json",
          data: JSON.stringify({
            action: "deactivate",
          }),
          success: function () {
            alertify.success("Your account has been deactivated. You will be redirected to the login page.");
            setTimeout(function () {
              AuthManager.logout();
            }, 2000);
          },
          error: function (xhr) {
            handleAjaxError(xhr, "Error deactivating account");
          },
        });
      });
    }
  });

  // Helper function for email validation
  function isValidEmail(email) {
    const re =
      /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
  }
});
