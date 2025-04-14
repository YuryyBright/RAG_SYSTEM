$(document).ready(function () {
  // Sample user data (replace with real data from the backend)
  $.ajax({
    url: "/users/all_users", // Your API endpoint to fetch users
    method: "GET",
    success: function (data) {
      renderUserList(data); // Assuming the response contains an array of users
    },
    error: function () {
      alert("Error fetching users.");
    },
  });

  // Function to render the user list
  function renderUserList(users) {
    const userList = $("#user-list");
    userList.empty(); // Clear previous list

    users.forEach((user, index) => {
      const status = user.banned ? "Banned" : "Active";
      const verified = user.verified ? "Verified" : "Unverified";

      const row = `
                <tr data-user-id="${user.id}">
                    <td>${index + 1}</td>
                    <td>${user.first_name} ${user.last_name}</td>
                    <td>${user.email}</td>
                    <td>
                        <span class="badge badge-${user.banned ? "danger" : "success"}">${status}</span>
                        <span class="badge badge-${user.verified ? "success" : "warning"}">${verified}</span>
                    </td>
                    <td class="text-center">
                        <button class="btn btn-primary btn-sm view-user" data-user-id="${
                          user.id
                        }"><i class="fas fa-folder"></i> View</button>
                        <button class="btn btn-info btn-sm edit-user" data-user-id="${
                          user.id
                        }"><i class="fas fa-pencil-alt"></i> Edit</button>
                        <button class="btn btn-danger btn-sm delete-user" data-user-id="${
                          user.id
                        }"><i class="fas fa-trash"></i> Delete</button>
                    </td>
                </tr>
            `;
      userList.append(row);
    });
  }

  // Event listeners for the buttons
  $("#user-list").on("click", ".view-user", function () {
    const userId = $(this).data("user-id");
    alert(`Viewing user with ID: ${userId}`);
  });

  $("#user-list").on("click", ".edit-user", function () {
    const userId = $(this).data("user-id");
    alert(`Editing user with ID: ${userId}`);
  });

  $("#user-list").on("click", ".delete-user", function () {
    const userId = $(this).data("user-id");
    const row = $(this).closest("tr");
    if (confirm(`Are you sure you want to delete user with ID: ${userId}?`)) {
      row.remove(); // Remove the row from the table (replace with an API call to delete on the server)
      alert(`User with ID: ${userId} has been deleted.`);
    }
  });
});
