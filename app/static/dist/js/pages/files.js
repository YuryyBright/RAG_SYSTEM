// Базовий URL до вашого бекенду
const baseUrl = "";
let currentPath = "/";

// Завантаження вмісту поточної директорії
function loadFolder(path) {
  $.get(`/folder${path}`, function (data) {
    currentPath = path;
    $("#file-list").empty();
    updateBreadcrumb(path);

    if (data.length === 0) {
      $("#file-list").append(`
        <div class="alert alert-info" role="alert">
          <i class="fas fa-info-circle"></i> Папка порожня.
        </div>
      `);
    } else {
      data.forEach((item) => {
        if (item.mime) {
          // Файл
          $("#file-list").append(`
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span><i class="fas fa-file"></i> ${item.name}</span>
                <div>
                    <button class="btn btn-sm btn-primary view-file" data-info='${JSON.stringify(item)}'>
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <button class="btn btn-sm btn-info download-file" data-path="${path}/${item.name}">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-sm btn-warning rename-file" data-path="${path}/${item.name}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger delete-file" data-path="${path}/${item.name}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
          `);
        } else {
          // Папка
          $("#file-list").append(`
            <div class="list-group-item d-flex justify-content-between align-items-center folder">
                <span class="open-folder" data-path="${path}/${item.name}"><i class="fas fa-folder"></i> ${item.name}</span>
                <button class="btn btn-sm btn-danger delete-folder" data-path="${path}/${item.name}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
          `);
        }
      });
    }
  });
}

// Оновлення хлібних крихт
function updateBreadcrumb(path) {
  const segments = path.split("/").filter(Boolean);
  const breadcrumb = $("#breadcrumbs");
  breadcrumb.empty();

  let accumulatedPath = "";
  breadcrumb.append(`<li class="breadcrumb-item"><a href="#" class="breadcrumb-link" data-path="/">Root</a></li>`);
  segments.forEach((segment) => {
    accumulatedPath += `/${segment}`;
    breadcrumb.append(
      `<li class="breadcrumb-item"><a href="#" class="breadcrumb-link" data-path="${accumulatedPath}">${segment}</a></li>`
    );
  });
}

// Показ модального вікна для повідомлень
function showAlertModal(message) {
  $("#alertModalMessage").text(message);
  $("#alertModal").modal("show");
}

// Показ модального вікна для підтвердження
function showConfirmModal(message, onConfirm) {
  $("#confirmModalMessage").text(message);
  $("#confirmModal").modal("show");
  $("#confirmModalConfirm")
    .off("click")
    .on("click", function () {
      $("#confirmModal").modal("hide");
      onConfirm();
    });
}

// Показ модального вікна для вводу
// Показ сповіщення
function showAlert(message, isError = false) {
  $("#alertModalMessage").text(message);
  $("#alertModal").modal("show");
  if (isError) {
    $("#alertModal .modal-header").addClass("bg-danger text-white");
  } else {
    $("#alertModal .modal-header").removeClass("bg-danger text-white");
  }
}

// Відкрити модальне вікно підтвердження
function showConfirm(message, onConfirm) {
  $("#confirmModalMessage").text(message);
  $("#confirmModal").modal("show");
  $("#confirmModalConfirm")
    .off("click")
    .on("click", () => {
      $("#confirmModal").modal("hide");
      onConfirm();
    });
}

// Відкрити модальне вікно введення
function showPrompt(message, onSubmit) {
  $("#promptModalLabel").text(message);
  $("#promptModal").modal("show");
  $("#promptModalInput")
    .val("")
    .off("keypress")
    .on("keypress", (e) => {
      if (e.key === "Enter") {
        const value = $("#promptModalInput").val().trim();
        if (value) {
          $("#promptModal").modal("hide");
          onSubmit(value);
        }
      }
    });
  $("#promptModalSubmit")
    .off("click")
    .on("click", () => {
      const value = $("#promptModalInput").val().trim();
      if (value) {
        $("#promptModal").modal("hide");
        onSubmit(value);
      }
    });
}

// Завантаження файлу
$(document).on("click", ".download-file", function () {
  const path = $(this).data("path");
  window.location.href = `${baseUrl}/file${path}`; // Завантажує файл через браузер
});

// Редагування файлу
$(document).on("click", ".rename-file", function () {
  const path = $(this).data("path");

  showPrompt("Enter new file name:", function (newName) {
    console.log(`${baseUrl}/file${path}`);
    $.ajax({
      url: `${baseUrl}/file${path}`,
      type: "PUT",
      data: { new_path: newName },
      success: function () {
        loadFolder(currentPath);
      },
      error: function (err) {
        showAlertModal(err.responseJSON.detail);
      },
    });
  });
});
// Завантаження файлу
$("#upload-file").click(function () {
  const fileInput = $('<input type="file">');
  fileInput.click();
  fileInput.on("change", function () {
    const file = this.files[0];
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      $.ajax({
        url: `${baseUrl}/file${currentPath}`,
        type: "POST",
        data: formData,
        processData: false,
        contentType: false,
        success: function () {
          loadFolder(currentPath);
        },
        error: function (err) {
          showAlertModal(err.responseJSON.detail);
        },
      });
    }
  });
});

// Створення папки
$("#create-folder").click(function () {
  showPrompt("Enter folder name:", function (folderName) {
    $.post(`${baseUrl}/folder${currentPath}`, { dirname: folderName }, function () {
      loadFolder(currentPath);
    }).fail(function (err) {
      showAlertModal(err.responseJSON.detail);
    });
  });
});
$("#go-back").on("click", () => {
  const pathParts = currentPath.split("/").filter((p) => p !== "");
  if (pathParts.length > 0) {
    pathParts.pop();
    currentPath = `/${pathParts.join("/")}`;
  } else {
    currentPath = "/";
  }
  loadFolder(currentPath);
});
// Видалення файлу
$(document).on("click", ".delete-file", function () {
  const path = $(this).data("path");
  showConfirmModal("Ви впевнені, що хочете видалити цей файл?", function () {
    $.ajax({
      url: `${baseUrl}/file${path}`,
      type: "DELETE",
      success: function () {
        loadFolder(currentPath);
      },
      error: function (err) {
        showAlertModal(err.responseJSON.detail);
      },
    });
  });
});

// Видалення папки
$(document).on("click", ".delete-folder", function () {
  const path = $(this).data("path");
  showConfirmModal("Ви впевнені, що хочете видалити цю папку?", function () {
    $.ajax({
      url: `${baseUrl}/folder${path}`,
      type: "DELETE",
      success: function () {
        loadFolder(currentPath);
      },
      error: function (err) {
        showAlertModal(err.responseJSON.detail);
      },
    });
  });
});

// Перейменування файлу
$(document).on("click", ".rename-file", function () {
  const path = $(this).data("path");
  showPrompt("Enter new file name:", function (newName) {
    $.ajax({
      url: `${baseUrl}/file${path}`,
      type: "PUT",
      data: { new_path: newName },
      success: function () {
        loadFolder(currentPath);
      },
      error: function (err) {
        showAlertModal(err.responseJSON.detail);
      },
    });
  });
});

// Виведення інформації про файл
$(document).on("click", ".view-file", function () {
  const fileInfo = $(this).data("info");
  const { name, size, mime, mtime, ctime } = fileInfo;
  $("#fileInfoModal .modal-body").html(`
    <p><strong>Name:</strong> ${name}</p>
    <p><strong>Size:</strong> ${size}</p>
    <p><strong>MIME:</strong> ${mime || "N/A"}</p>
    <p><strong>Modified:</strong> ${new Date(mtime).toLocaleString()}</p>
    <p><strong>Created:</strong> ${new Date(ctime).toLocaleString()}</p>
  `);
  $("#fileInfoModal").modal("show");
});

// Перехід між папками
$(document).on("click", ".open-folder", function () {
  const path = $(this).data("path");
  loadFolder(path);
});

// Перехід за хлібними крихтами
$(document).on("click", ".breadcrumb-link", function () {
  const path = $(this).data("path");
  loadFolder(path);
});
$(document).on("click", "#export-archive", function () {
  const archiveName = "backup.zip"; // Default archive name

  // Check if currentPath is defined
  if (!currentPath) {
    showAlert("Current path is not defined.");
    return;
  }

  const payload = {
    current_path: currentPath,
    archive_name: archiveName,
  };

  $.ajax({
    url: "/users/archive", // Correct API endpoint
    type: "POST",
    data: JSON.stringify(payload), // Sending data as JSON
    contentType: "application/json",
    success: function (data) {
      // Check if archive URL is returned
      if (data.archive_url) {
        // Create a link for downloading the archive
        const link = document.createElement("a");
        link.href = data.archive_url; // The URL to download the archive
        link.download = archiveName; // Set the default name for the downloaded file
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Show a success message
        showAlert(data.message || "Archive created and downloaded successfully.");
      } else {
        showAlert("No archive URL returned.");
      }
    },
    error: function (xhr) {
      const errorMessage = xhr.responseJSON?.detail || "Error creating archive.";
      console.log(errorMessage);
    },
  });
});

$(document).on("click", "#import-archive", function () {
  // Відкрити модальне вікно для завантаження архіву
  const $input = $('<input type="file" accept=".zip">').on("change", function () {
    const file = this.files[0];
    if (!file) {
      showAlert("No file selected for import.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    $.ajax({
      url: "/unarchive",
      type: "POST",
      data: formData,
      contentType: false,
      processData: false,
      success: function () {
        updateFileList(); // Оновити список файлів після імпорту
        showAlert("Files imported successfully.");
      },
      error: function () {
        showAlert("Error importing files.");
      },
    });
  });

  $input.click(); // Запуск вікна вибору файлу
});

// Початкове завантаження
$(document).ready(function () {
  loadFolder(currentPath);
});
