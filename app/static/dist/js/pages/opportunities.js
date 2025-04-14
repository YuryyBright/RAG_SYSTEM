// opportunities.js - Opportunities page functionality
$(document).ready(function () {
  // Initialize components
  initDateRangePicker();
  initDeadlinePicker();
  initOpportunitiesTable();

  // Set up event listeners
  setupEventListeners();
});

/**
 * Initialize date range picker for filtering
 */
function initDateRangePicker() {
  $("#date-range-picker").daterangepicker({
    autoUpdateInput: false,
    locale: {
      cancelLabel: "Clear",
      format: "MM/DD/YYYY",
    },
  });

  $("#date-range-picker").on("apply.daterangepicker", function (ev, picker) {
    $(this).val(picker.startDate.format("MM/DD/YYYY") + " - " + picker.endDate.format("MM/DD/YYYY"));
  });

  $("#date-range-picker").on("cancel.daterangepicker", function (ev, picker) {
    $(this).val("");
  });
}

/**
 * Initialize deadline date picker for form
 */
function initDeadlinePicker() {
  $("#deadline-datepicker").datetimepicker({
    format: "L",
    icons: {
      time: "far fa-clock",
    },
  });
}

/**
 * Initialize the opportunities data table
 */
function initOpportunitiesTable() {
  window.opportunitiesTable = $("#opportunities-table").DataTable({
    responsive: true,
    autoWidth: false,
    ajax: {
      url: "/api/opportunities",
      dataSrc: "opportunities",
    },
    columns: [
      { data: "title" },
      { data: "category" },
      {
        data: "deadline",
        render: function (data) {
          return moment(data).format("MM/DD/YYYY");
        },
      },
      {
        data: "status",
        render: function (data) {
          let badgeClass = "badge-info";

          if (data === "open") {
            badgeClass = "badge-success";
          } else if (data === "closing") {
            badgeClass = "badge-warning";
          } else if (data === "closed") {
            badgeClass = "badge-danger";
          }

          return `<span class="badge ${badgeClass}">${data.charAt(0).toUpperCase() + data.slice(1)}</span>`;
        },
      },
      {
        data: "id",
        render: function (data) {
          return `
            <div class="btn-group">
              <button type="button" class="btn btn-sm btn-info view-opportunity" data-id="${data}">
                <i class="fas fa-eye"></i>
              </button>
              <button type="button" class="btn btn-sm btn-primary edit-opportunity-btn" data-id="${data}">
                <i class="fas fa-edit"></i>
              </button>
              <button type="button" class="btn btn-sm btn-danger delete-opportunity" data-id="${data}">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          `;
        },
      },
    ],
  });
}

/**
 * Set up all event listeners for the page
 */
function setupEventListeners() {
  // Filter buttons
  $("#apply-filters").on("click", applyFilters);
  $("#reset-filters").on("click", resetFilters);

  // Add new opportunity
  $("#add-opportunity").on("click", showAddOpportunityModal);

  // View opportunity details
  $("#opportunities-table").on("click", ".view-opportunity", function () {
    const opportunityId = $(this).data("id");
    viewOpportunityDetails(opportunityId);
  });

  // Edit opportunity
  $("#opportunities-table").on("click", ".edit-opportunity-btn", function () {
    const opportunityId = $(this).data("id");
    editOpportunity(opportunityId);
  });

  // Edit from details modal
  $("#edit-opportunity").on("click", function () {
    const opportunityId = $(this).data("id");
    $("#opportunity-modal").modal("hide");
    editOpportunity(opportunityId);
  });

  // Delete opportunity
  $("#opportunities-table").on("click", ".delete-opportunity", function () {
    const opportunityId = $(this).data("id");
    confirmDeleteOpportunity(opportunityId);
  });

  // Apply for opportunity
  $("#apply-opportunity").on("click", function () {
    const opportunityId = $(this).data("id");
    applyForOpportunity(opportunityId);
  });

  // Save opportunity
  $("#save-opportunity").on("click", saveOpportunity);
}

/**
 * Apply the selected filters to the opportunities table
 */
function applyFilters() {
  const category = $("#filter-category").val();
  const status = $("#filter-status").val();
  const dateRange = $("#date-range-picker").val();
  const keywords = $("#filter-keywords").val();

  // Prepare filter parameters
  const params = {};
  if (category) params.category = category;
  if (status) params.status = status;
  if (keywords) params.keywords = keywords;

  if (dateRange) {
    const dates = dateRange.split(" - ");
    params.start_date = dates[0];
    params.end_date = dates[1];
  }

  // Update table with filters
  window.opportunitiesTable.ajax.url("/api/opportunities?" + $.param(params)).load();

  alertify.success("Filters applied");
}

/**
 * Reset all filters to default values
 */
function resetFilters() {
  $("#filter-category").val("");
  $("#filter-status").val("");
  $("#date-range-picker").val("");
  $("#filter-keywords").val("");

  // Reload table with default parameters
  window.opportunitiesTable.ajax.url("/api/opportunities").load();

  alertify.success("Filters reset");
}

/**
 * Show the modal for adding a new opportunity
 */
function showAddOpportunityModal() {
  // Clear the form
  $("#opportunity-form")[0].reset();
  $("#opportunity-id").val("");

  // Update modal title
  $(".modal-title", "#edit-opportunity-modal").text("Add New Opportunity");

  // Show the modal
  $("#edit-opportunity-modal").modal("show");
}

/**
 * Load and display opportunity details
 * @param {string|number} opportunityId - ID of the opportunity to view
 */
function viewOpportunityDetails(opportunityId) {
  $.ajax({
    url: `/api/opportunities/${opportunityId}`,
    method: "GET",
    dataType: "json",
    success: function (response) {
      if (response.success) {
        const opportunity = response.opportunity;

        // Format the details HTML
        const detailsHtml = `
          <h2>${opportunity.title}</h2>
          <p class="badge badge-${
            opportunity.status === "open" ? "success" : opportunity.status === "closing" ? "warning" : "danger"
          }">
            ${opportunity.status.charAt(0).toUpperCase() + opportunity.status.slice(1)}
          </p>
          
          <div class="row mt-3">
            <div class="col-md-6">
              <p><strong>Category:</strong> ${
                opportunity.category.charAt(0).toUpperCase() + opportunity.category.slice(1)
              }</p>
              <p><strong>Deadline:</strong> ${moment(opportunity.deadline).format("MMMM DD, YYYY")}</p>
              <p><strong>Contact:</strong> ${opportunity.contact || "N/A"}</p>
            </div>
            <div class="col-md-6">
              <p><strong>Public:</strong> ${opportunity.is_public ? "Yes" : "No"}</p>
              <p><strong>Created:</strong> ${moment(opportunity.created_at).format("MMMM DD, YYYY")}</p>
            </div>
          </div>
          
          <div class="mt-4">
            <h4>Description</h4>
            <p>${opportunity.description}</p>
          </div>
          
          <div class="row mt-4">
            <div class="col-md-6">
              <h4>Requirements</h4>
              <p>${opportunity.requirements || "No specific requirements listed."}</p>
            </div>
            <div class="col-md-6">
              <h4>Benefits</h4>
              <p>${opportunity.benefits || "No specific benefits listed."}</p>
            </div>
          </div>
        `;

        $(".opportunity-details").html(detailsHtml);
        $("#edit-opportunity").data("id", opportunityId);
        $("#apply-opportunity").data("id", opportunityId);

        // Show the modal
        $("#opportunity-modal").modal("show");
      } else {
        alertify.error("Failed to load opportunity details");
      }
    },
    error: function () {
      alertify.error("Failed to load opportunity details");
    },
  });
}

/**
 * Load opportunity data for editing
 * @param {string|number} opportunityId - ID of the opportunity to edit
 */
function editOpportunity(opportunityId) {
  $.ajax({
    url: `/api/opportunities/${opportunityId}`,
    method: "GET",
    dataType: "json",
    success: function (response) {
      if (response.success) {
        const opportunity = response.opportunity;

        // Populate the form
        $("#title").val(opportunity.title);
        $("#category").val(opportunity.category);
        $("#deadline").val(moment(opportunity.deadline).format("MM/DD/YYYY"));
        $("#description").val(opportunity.description);
        $("#requirements").val(opportunity.requirements);
        $("#benefits").val(opportunity.benefits);
        $("#contact").val(opportunity.contact);
        $("#is-public").prop("checked", opportunity.is_public);
        $("#opportunity-id").val(opportunityId);

        // Update modal title
        $(".modal-title", "#edit-opportunity-modal").text("Edit Opportunity");

        // Show the modal
        $("#edit-opportunity-modal").modal("show");
      } else {
        alertify.error("Failed to load opportunity data");
      }
    },
    error: function () {
      alertify.error("Failed to load opportunity data");
    },
  });
}

/**
 * Save opportunity data (create new or update existing)
 */
function saveOpportunity() {
  const opportunityId = $("#opportunity-id").val();
  const isNew = !opportunityId;

  // Validate the form
  if (!$("#opportunity-form")[0].checkValidity()) {
    $("#opportunity-form")[0].reportValidity();
    return;
  }

  // Gather form data
  const formData = {
    title: $("#title").val(),
    category: $("#category").val(),
    deadline: moment($("#deadline").val(), "MM/DD/YYYY").format("YYYY-MM-DD"),
    description: $("#description").val(),
    requirements: $("#requirements").val(),
    benefits: $("#benefits").val(),
    contact: $("#contact").val(),
    is_public: $("#is-public").prop("checked"),
  };

  // If editing, add the ID
  if (!isNew) {
    formData.id = opportunityId;
  }

  $.ajax({
    url: isNew ? "/api/opportunities" : `/api/opportunities/${opportunityId}`,
    method: isNew ? "POST" : "PUT",
    contentType: "application/json",
    data: JSON.stringify(formData),
    dataType: "json",
    success: function (response) {
      if (response.success) {
        // Close the modal
        $("#edit-opportunity-modal").modal("hide");

        // Refresh the table
        window.opportunitiesTable.ajax.reload();

        // Show success message
        alertify.success(isNew ? "Opportunity created successfully" : "Opportunity updated successfully");
      } else {
        alertify.error(response.message || "Failed to save opportunity");
      }
    },
    error: function () {
      alertify.error("Failed to save opportunity");
    },
  });
}

/**
 * Show confirmation dialog for deleting an opportunity
 * @param {string|number} opportunityId - ID of the opportunity to delete
 */
function confirmDeleteOpportunity(opportunityId) {
  alertify
    .confirm(
      "Delete Opportunity",
      "Are you sure you want to delete this opportunity? This action cannot be undone.",
      function () {
        deleteOpportunity(opportunityId);
      },
      function () {
        // User clicked cancel
      }
    )
    .set("labels", { ok: "Delete", cancel: "Cancel" });
}

/**
 * Delete an opportunity
 * @param {string|number} opportunityId - ID of the opportunity to delete
 */
function deleteOpportunity(opportunityId) {
  $.ajax({
    url: `/api/opportunities/${opportunityId}`,
    method: "DELETE",
    dataType: "json",
    success: function (response) {
      if (response.success) {
        // Refresh the table
        window.opportunitiesTable.ajax.reload();

        // Show success message
        alertify.success("Opportunity deleted successfully");
      } else {
        alertify.error(response.message || "Failed to delete opportunity");
      }
    },
    error: function () {
      alertify.error("Failed to delete opportunity");
    },
  });
}

/**
 * Handle applying for an opportunity
 * @param {string|number} opportunityId - ID of the opportunity to apply for
 */
function applyForOpportunity(opportunityId) {
  // Close the current modal
  $("#opportunity-modal").modal("hide");

  // Show application form in a new modal
  showApplicationForm(opportunityId);
}

/**
 * Show application form for an opportunity
 * @param {string|number} opportunityId - ID of the opportunity to apply for
 */
function showApplicationForm(opportunityId) {
  // Create application modal if it doesn't exist
  if ($("#application-modal").length === 0) {
    const modalHtml = `
      <div class="modal fade" id="application-modal">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h4 class="modal-title">Apply for Opportunity</h4>
              <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <div class="modal-body">
              <form id="application-form">
                <div class="form-group">
                  <label for="applicant-name">Full Name</label>
                  <input type="text" class="form-control" id="applicant-name" name="applicant_name" required>
                </div>
                <div class="form-group">
                  <label for="applicant-email">Email</label>
                  <input type="email" class="form-control" id="applicant-email" name="applicant_email" required>
                </div>
                <div class="form-group">
                  <label for="application-message">Message</label>
                  <textarea class="form-control" id="application-message" name="message" rows="5" required></textarea>
                </div>
                <div class="form-group">
                  <label for="application-resume">Resume/CV</label>
                  <div class="input-group">
                    <div class="custom-file">
                      <input type="file" class="custom-file-input" id="application-resume" name="resume">
                      <label class="custom-file-label" for="application-resume">Choose file</label>
                    </div>
                  </div>
                </div>
                <input type="hidden" id="application-opportunity-id" name="opportunity_id">
              </form>
            </div>
            <div class="modal-footer justify-content-between">
              <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-success" id="submit-application">Submit Application</button>
            </div>
          </div>
        </div>
      </div>
    `;

    $("body").append(modalHtml);

    // Set up file input behavior
    $(document).on("change", ".custom-file-input", function () {
      const fileName = $(this).val().split("\\").pop();
      $(this)
        .siblings(".custom-file-label")
        .addClass("selected")
        .html(fileName || "Choose file");
    });

    // Set up submit button behavior
    $("#submit-application").on("click", submitApplication);
  }

  // Clear form and set opportunity ID
  $("#application-form")[0].reset();
  $("#application-opportunity-id").val(opportunityId);
  $(".custom-file-label").text("Choose file");

  // Show the modal
  $("#application-modal").modal("show");
}

/**
 * Submit an application for an opportunity
 */
function submitApplication() {
  // Validate the form
  if (!$("#application-form")[0].checkValidity()) {
    $("#application-form")[0].reportValidity();
    return;
  }

  const opportunityId = $("#application-opportunity-id").val();

  // Create FormData object to handle file upload
  const formData = new FormData($("#application-form")[0]);

  $.ajax({
    url: `/api/opportunities/${opportunityId}/apply`,
    method: "POST",
    data: formData,
    processData: false,
    contentType: false,
    dataType: "json",
    success: function (response) {
      if (response.success) {
        // Close the modal
        $("#application-modal").modal("hide");

        // Show success message
        alertify.success("Application submitted successfully");
      } else {
        alertify.error(response.message || "Failed to submit application");
      }
    },
    error: function () {
      alertify.error("Failed to submit application");
    },
  });
}
