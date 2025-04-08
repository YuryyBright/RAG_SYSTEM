Here you go — the full CLI usage template written directly here for quick reference:

---

# ✅ Admin CLI Usage Template

---

### #1 ➕ Add a New User
**Command:**
```bash
python admin.py add_user <username> <email> [--admin]
```
**Example:**
```bash
python admin.py add_user johndoe john@example.com --admin
```

---

### #2 ➖ Remove a User
**Command:**
```bash
python admin.py remove_user <username>
```
**Example:**
```bash
python admin.py remove_user johndoe
```

---

### #3 📋 List All Users
**Command:**
```bash
python admin.py list_users
```
**Example:**
```bash
python admin.py list_users
```

---

### #4 🗃 List All Tables and Row Counts
**Command:**
```bash
python admin.py list_tables
```
**Example:**
```bash
python admin.py list_tables
```

---

### #5 🔍 Find a User by Username
**Command:**
```bash
python admin.py find_user <username>
```
**Example:**
```bash
python admin.py find_user johndoe
```

---

### #6 🔄 Toggle User Active Status
**Command:**
```bash
python admin.py toggle_active <username> --active <true|false>
```
**Example:**
```bash
python admin.py toggle_active johndoe --active false
```

---

### #7 🔐 Change User Password
**Command:**
```bash
python admin.py change_password <username>
```
**Example:**
```bash
python admin.py change_password johndoe
```

---

### #8 🆙 Promote User to Admin
**Command:**
```bash
python admin.py promote_user <username>
```
**Example:**
```bash
python admin.py promote_user johndoe
```

---

### #9 🧾 Export Users to CSV
**Command:**
```bash
python admin.py export_users <filepath>
```
**Example:**
```bash
python admin.py export_users ./output/users.csv
```

---

Let me know if you'd like a Markdown, PDF, or HTML version of this too 🔥