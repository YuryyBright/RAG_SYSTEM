// profile.js - Enhanced JavaScript for the user profile page

$(document).ready(function () {
  // Toggle visibility of API key when generated
  let apiKeyVisible = false;

  // Handle API key generation
  $(".btn-primary.btn-block").on("click", function (e) {
    e.preventDefault();

    // Show modal for API key name
    Swal.fire({
      title: "Generate API Key",
      input: "text",
      inputLabel: "API Key Name",
      inputPlaceholder: "Enter a name for this API key",
      showCancelButton: true,
      inputValidator: (value) => {
        if (!value) {
          return "You need to provide a name for the API key";
        }
      },
    }).then((result) => {
      if (result.isConfirmed) {
        generateApiKey(result.value);
      }
    });
  });

  // Function to generate API key
  function generateApiKey(keyName) {
    $.ajax({
      url: "/api/user/apikeys",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify({ name: keyName }),
      success: function (response) {
        // Show the API key with copy button
        Swal.fire({
          title: "API Key Generated",
          html: `
            <div class="alert alert-warning">
              <p><strong>Important:</strong> Copy this API key now. You won't be able to see it again!</p>
            </div>
            <div class="input-group mb-3">
              <input id="api-key-display" type="text" class="form-control" value="${response.key}" readonly>
              <div class="input-group-append">
                <button id="copy-api-key" class="btn btn-outline-secondary" type="button">
                  <i class="fas fa-copy"></i> Copy
                </button>
              </div>
            </div>
          `,
          didOpen: () => {
            // Add copy functionality
            $("#copy-api-key").on("click", function () {
              const apiKeyInput = document.getElementById("api-key-display");
              apiKeyInput.select();
              document.execCommand("copy");
              Swal.fire({
                position: "top-end",
                icon: "success",
                title: "API key copied to clipboard",
                showConfirmButton: false,
                timer: 1500,
              });
            });
          },
        });

        // Reload API keys list
        loadApiKeys();
      },
      error: function (xhr) {
        alertify.error("Error generating API key: " + xhr.responseText);
      },
    });
  }

  // Enhanced theme switching
  $("#inputTheme").on("change", function () {
    const newTheme = $(this).val();
    $("body")
      .removeClass("dark-mode light-mode")
      .addClass(newTheme + "-mode");

    // Save theme preference to localStorage
    localStorage.setItem("theme", newTheme);
  });

  // Apply saved theme on page load
  const savedTheme = localStorage.getItem("theme") || "light";
  $("body")
    .removeClass("dark-mode light-mode")
    .addClass(savedTheme + "-mode");
  $("#inputTheme").val(savedTheme);

  // Password strength meter
  $("#newPassword").on("input", function () {
    const password = $(this).val();
    const strength = calculatePasswordStrength(password);
    updatePasswordStrengthMeter(strength);
  });

  function calculatePasswordStrength(password) {
    let strength = 0;

    // Length check
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;

    // Complexity checks
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[a-z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;

    return Math.min(5, strength);
  }

  function updatePasswordStrengthMeter(strength) {
    const meterClasses = ["bg-danger", "bg-warning", "bg-info", "bg-primary", "bg-success"];
    const meterLabels = ["Very Weak", "Weak", "Fair", "Good", "Strong"];

    // Add password strength meter if it doesn't exist
    if ($("#password-strength-meter").length === 0) {
      $("#newPassword").after(`
        <div class="mt-2">
          <div class="progress" style="height: 10px;">
            <div id="password-strength-meter" class="progress-bar" role="progressbar" style="width: 0%"></div>
          </div>
          <small id="password-strength-text" class="form-text text-muted"></small>
        </div>
      `);
    }

    // Update meter
    const percentage = (strength / 5) * 100;
    const meter = $("#password-strength-meter");

    meter
      .removeClass(meterClasses.join(" "))
      .addClass(meterClasses[strength])
      .css("width", percentage + "%");

    $("#password-strength-text").text(meterLabels[strength]);
  }

  // Improve tabs handling
  $(".nav-pills a").on("shown.bs.tab", function (e) {
    // Save active tab to localStorage
    localStorage.setItem("activeProfileTab", $(e.target).attr("href"));
  });

  // Restore active tab from localStorage
  const activeTab = localStorage.getItem("activeProfileTab");
  if (activeTab) {
    $('.nav-pills a[href="' + activeTab + '"]').tab("show");
  }

  // Handle avatar uploads
  $(".profile-user-img")
    .parent()
    .on("click", function () {
      // Create file input if it doesn't exist
      if ($("#avatar-upload").length === 0) {
        $("body").append('<input type="file" id="avatar-upload" style="display: none;" accept="image/*">');
      }

      // Trigger click on hidden file input
      $("#avatar-upload").trigger("click");
    });

  $(document).on("change", "#avatar-upload", function () {
    const file = this.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function (e) {
        $(".profile-user-img").attr("src", e.target.result);

        // Upload image to server
        uploadAvatarImage(file);
      };
      reader.readAsDataURL(file);
    }
  });

  function uploadAvatarImage(file) {
    const formData = new FormData();
    formData.append("avatar", file);

    $.ajax({
      url: "/api/user/avatar",
      type: "POST",
      data: formData,
      processData: false,
      contentType: false,
      success: function () {
        alertify.success("Profile picture updated successfully!");
      },
      error: function (xhr) {
        alertify.error("Error updating profile picture: " + xhr.responseText);
      },
    });
  }
});
