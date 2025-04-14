// dashboard.js - Dashboard page functionality
$(document).ready(function () {
  // Initialize dashboard components
  initDashboard();

  // Set up event listeners
  $("#refresh-activities").on("click", refreshRecentActivities);
});

/**
 * Initialize all dashboard components
 */
function initDashboard() {
  // Load dashboard statistics
  loadDashboardStats();

  // Load recent activities
  loadRecentActivities();

  // Initialize storage usage chart
  initStorageChart();
}

/**
 * Load dashboard statistics via AJAX
 */
function loadDashboardStats() {
  $.ajax({
    url: "/api/dashboard/stats",
    method: "GET",
    dataType: "json",
    success: function (response) {
      if (response.success) {
        // Update statistics counts
        $("#document-count").text(response.stats.document_count || 0);
        $("#shared-count").text(response.stats.shared_count || 0);

        // Update storage usage
        const usagePercent = response.stats.storage_usage_percent || 0;
        $("#storage-usage").html(`${usagePercent}<small>%</small>`);

        // Update chart if available
        updateStorageChart(response.stats.storage);
      } else {
        console.error("Failed to load dashboard stats:", response.error);
        alertify.error("Failed to load dashboard statistics");
      }
    },
    error: function (xhr, status, error) {
      console.error("Dashboard stats error:", error);
      alertify.error("Error loading dashboard data");
    },
  });
}

/**
 * Load recent user activities
 */
function loadRecentActivities() {
  let activityPage = 1;
  const activityLimit = 10;
  const activityType = $("#activity-filter").val();
  const url =
    "/api/user/activity?limit=" +
    activityLimit +
    "&page=" +
    activityPage +
    (activityType ? "&activity_type=" + activityType : "");

  $.ajax({
    url: url,
    method: "GET",
    dataType: "json",
    success: function (response) {
      if (activityPage === 1) {
        $("#recent-activity-table tbody").empty();
      }

      if (!Array.isArray(response.activities)) {
        $("#recent-activity-table tbody").html(
          `<tr><td colspan="4" class="text-center">Failed to load activities</td></tr>`
        );
        $("#load-more-activity").hide();
        return;
      }

      if (response.activities.length === 0) {
        $("#recent-activity-table tbody").html(
          `<tr><td colspan="4" class="text-center">No recent activities found</td></tr>`
        );
        $("#load-more-activity").hide();
        return;
      }

      response.activities.forEach(function (activity) {
        const activityDate = new Date(activity.timestamp).toLocaleString();
        let badgeClass = "badge-secondary";
        let icon = "fa-info-circle";

        switch (activity.type) {
          case "login":
            badgeClass = "badge-success";
            icon = "fa-sign-in-alt";
            break;
          case "logout":
            badgeClass = "badge-dark";
            icon = "fa-sign-out-alt";
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
          case "password_change":
            badgeClass = "badge-warning";
            icon = "fa-key";
            break;
        }

        const row = `
          <tr>
            <td><span class="badge ${badgeClass}"><i class="fas ${icon} mr-1"></i> ${activity.type}</span></td>
            <td>${activity.description}</td>
            <td>${activityDate}</td>
            <td>${activity.user || "N/A"}</td>
          </tr>
        `;

        $("#recent-activity-table tbody").append(row);
      });

      if (response.activities.length < activityLimit) {
        $("#load-more-activity").hide();
      } else {
        $("#load-more-activity").show();
      }
    },
    error: function (xhr, status, error) {
      console.error("Activities error:", error);
      $("#recent-activity-table tbody").html(
        '<tr><td colspan="4" class="text-center">Error loading activities</td></tr>'
      );
      $("#load-more-activity").hide();
    },
  });
}

/**
 * Refresh the recent activities table
 */
function refreshRecentActivities() {
  $("#recent-activity-table tbody").html(
    '<tr><td colspan="4" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>'
  );
  loadRecentActivities();
}

/**
 * Render the activities into the table
 * @param {Array} activities - List of activity objects
 */
function renderActivityTable(activities) {
  const tableBody = $("#recent-activity-table tbody");
  tableBody.empty();

  if (!activities || activities.length === 0) {
    tableBody.html('<tr><td colspan="4" class="text-center">No recent activities</td></tr>');
    return;
  }

  activities.forEach(function (activity) {
    // Create status badge based on activity status
    let statusBadge = "";
    switch (activity.status) {
      case "completed":
        statusBadge = '<span class="badge badge-success">Completed</span>';
        break;
      case "pending":
        statusBadge = '<span class="badge badge-warning">Pending</span>';
        break;
      case "failed":
        statusBadge = '<span class="badge badge-danger">Failed</span>';
        break;
      default:
        statusBadge = '<span class="badge badge-info">Unknown</span>';
    }

    // Create table row
    const row = `
      <tr>
        <td>${activity.description}</td>
        <td>${activity.type}</td>
        <td>${formatDate(activity.timestamp)}</td>
        <td>${statusBadge}</td>
      </tr>
    `;

    tableBody.append(row);
  });
}

/**
 * Initialize the storage usage chart
 */
function initStorageChart() {
  const ctx = document.getElementById("storage-usage-chart").getContext("2d");
  window.storageChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Used", "Available"],
      datasets: [
        {
          data: [0, 100],
          backgroundColor: ["#f56954", "#00a65a"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      legend: {
        position: "bottom",
        labels: {
          fontColor: "#efefef",
        },
      },
    },
  });
}

/**
 * Update the storage chart with new data
 * @param {Object} storageData - Storage usage data
 */
function updateStorageChart(storageData) {
  if (!window.storageChart || !storageData) return;

  const usedPercent = storageData.used_percent || 0;
  const availablePercent = 100 - usedPercent;

  window.storageChart.data.datasets[0].data = [usedPercent, availablePercent];
  window.storageChart.update();
}

/**
 * Format a date string or timestamp
 * @param {string|number} dateValue - Date value to format
 * @returns {string} Formatted date string
 */
function formatDate(dateValue) {
  const date = new Date(dateValue);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString();
}
