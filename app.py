

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import re
import os

app = Flask(__name__)

DATABASE = "lost_found.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con


# ---------------- CREATE / UPDATE DATABASE ----------------

def create_table():
    con = get_db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            item_type TEXT,
            phone TEXT,
            status TEXT DEFAULT 'Open'
        )
    """)

    # Add phone column to an existing database if missing
    columns = [
        row["name"]
        for row in con.execute(
            "PRAGMA table_info(items)"
        ).fetchall()
    ]

    if "phone" not in columns:
        con.execute("ALTER TABLE items ADD COLUMN phone TEXT")

    con.commit()
    con.close()


# ---------------- PHONE NUMBER MASKING ----------------

def mask_phone(phone):
    if not phone:
        return "Not provided"

    return "******" + phone[-4:]


# ---------------- FRONTEND ----------------

HTML = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Campus Lost and Found</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            background: #eef2f7;
            padding: 20px;
            margin: 0;
            color: #333;
        }

        .container {
            max-width: 700px;
            margin: auto;
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 3px 12px rgba(0,0,0,0.1);
        }

        header {
            text-align: center;
            background: #174ea6;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 25px;
        }

        header h1 {
            margin-bottom: 8px;
        }

        h2 {
            color: #174ea6;
        }

        label {
            display: block;
            margin-top: 12px;
            font-weight: bold;
        }

        input, textarea, select, button {
            width: 100%;
            padding: 12px;
            margin-top: 8px;
            border-radius: 6px;
            font-size: 15px;
        }

        input, textarea, select {
            border: 1px solid #ccc;
        }

        textarea {
            min-height: 90px;
            resize: vertical;
        }

        button {
            background: #1769aa;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background: #104d82;
        }

        .item {
            background: #e7f1fa;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 5px solid #1769aa;
            overflow-wrap: anywhere;
        }

        .recovered {
            border-left-color: #218838;
            background: #e8f5e9;
        }

        .message {
            padding: 12px;
            margin: 12px 0;
            background: #e8f5e9;
            color: #176b2c;
            border-radius: 6px;
            display: none;
        }

        .privacy {
            font-size: 13px;
            color: #666;
            margin-top: 8px;
        }

        footer {
            text-align: center;
            margin-top: 25px;
            color: #666;
            font-size: 13px;
        }

        @media(max-width: 600px) {
            body {
                padding: 10px;
            }

            .container {
                padding: 15px;
            }

            header h1 {
                font-size: 23px;
            }
        }

    </style>
</head>

<body>

<div class="container">

    <header>
        <h1>Campus Lost and Found</h1>
        <p>Find your missing belongings easily!</p>
    </header>

    <h2>Report an Item</h2>

    <div id="message" class="message"></div>

    <form id="itemForm">

        <label>Item Name</label>
        <input id="name"
               placeholder="Example: Water Bottle"
               maxlength="100"
               required>

        <label>Item Description</label>
        <textarea id="description"
                  placeholder="Describe your item"
                  maxlength="1000"
                  required></textarea>

        <label>Location</label>
        <input id="location"
               placeholder="Example: College Library"
               maxlength="200"
               required>

        <label>Lost or Found</label>
        <select id="type" required>
            <option value="">Select an option</option>
            <option value="Lost">Lost Item</option>
            <option value="Found">Found Item</option>
        </select>

        <label>Contact Number</label>
        <input id="phone"
               type="tel"
               placeholder="Enter 10-digit mobile number"
               pattern="[0-9]{10}"
               maxlength="10"
               inputmode="numeric"
               required>

        <p class="privacy">
            Your full contact number is stored privately.
            Only a masked number is displayed publicly.
        </p>

        <button type="submit">Submit Report</button>

    </form>

    <hr>

    <h2>Reported Items</h2>

    <input id="search"
           placeholder="Search items..."
           oninput="loadItems()">

    <div id="items">
        Loading reports...
    </div>

    <footer>
        Campus Lost and Found Project
    </footer>

</div>


<script>

const form = document.getElementById("itemForm");

const message = document.getElementById("message");


// ---------------- SUBMIT ITEM ----------------

form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const phone = document.getElementById("phone").value.trim();

    if (!/^[0-9]{10}$/.test(phone)) {
        showMessage("Enter a valid 10-digit mobile number.");
        return;
    }

    const data = {
        name: document.getElementById("name").value.trim(),

        description:
            document.getElementById("description").value.trim(),

        location:
            document.getElementById("location").value.trim(),

        item_type:
            document.getElementById("type").value,

        phone: phone
    };

    try {

        const response = await fetch("/api/items", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        showMessage(result.message || result.error);

        if (response.ok) {
            form.reset();
            loadItems();
        }

    } catch (error) {
        showMessage("Unable to submit report. Try again.");
    }

});


// ---------------- DISPLAY MESSAGE ----------------

function showMessage(text) {

    message.textContent = text;
    message.style.display = "block";

}


// ---------------- LOAD ITEMS ----------------

async function loadItems() {

    const container = document.getElementById("items");

    try {

        const response = await fetch("/api/items");

        if (!response.ok) {
            throw new Error("Unable to load items");
        }

        const items = await response.json();

        const search = document.getElementById("search")
                             .value.toLowerCase();

        container.innerHTML = "";

        const filteredItems = items.filter(item =>
            item.name.toLowerCase().includes(search)
        );

        if (filteredItems.length === 0) {
            container.textContent = "No matching items found.";
            return;
        }

        filteredItems.forEach(item => {

            const div = document.createElement("div");

            div.className = "item";

            if (item.status === "Recovered") {
                div.classList.add("recovered");
            }

            const title = document.createElement("h3");
            title.textContent = item.name;

            const description = document.createElement("p");
            description.textContent =
                "Description: " + item.description;

            const location = document.createElement("p");
            location.textContent =
                "Location: " + item.location;

            const type = document.createElement("p");
            type.textContent =
                "Type: " + item.item_type;

            const phone = document.createElement("p");
            phone.textContent =
                "Contact: " + item.phone;

            const status = document.createElement("p");
            status.textContent =
                "Status: " + item.status;

            div.append(
                title,
                description,
                location,
                type,
                phone,
                status
            );

            // Recovery option
            if (item.status === "Open") {

                const button = document.createElement("button");

                button.textContent = "Mark as Recovered";

                button.onclick = async function() {

                    const confirmed = confirm(
                        "Confirm that this item has been recovered?"
                    );

                    if (!confirmed) {
                        return;
                    }

                    try {

                        const response = await fetch(
                            `/api/items/${item.id}/recover`,
                            { method: "POST" }
                        );

                        const result = await response.json();

                        showMessage(
                            result.message || result.error
                        );

                        if (response.ok) {
                            loadItems();
                        }

                    } catch (error) {
                        showMessage("Unable to update recovery status.");
                    }

                };

                div.appendChild(button);

            } else {

                const recoveredText = document.createElement("strong");

                recoveredText.textContent =
                    "Item successfully recovered!";

                div.appendChild(recoveredText);

            }

            container.appendChild(div);

        });

    } catch (error) {

        container.textContent =
            "Unable to load reports. Please refresh the page.";

    }

}


// Load reports when page opens
loadItems();

</script>

</body>
</html>
"""


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template_string(HTML)


# ---------------- ADD ITEM API ----------------

@app.route("/api/items", methods=["POST"])
def add_item():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request data"}), 400

    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    location = str(data.get("location", "")).strip()
    item_type = str(data.get("item_type", "")).strip()
    phone = str(data.get("phone", "")).strip()

    if not all([name, description, location, item_type, phone]):
        return jsonify({
            "error": "Please fill in all fields."
        }), 400

    if len(name) > 100 or len(description) > 1000 or len(location) > 200:
        return jsonify({
            "error": "One or more fields are too long."
        }), 400

    if item_type not in ["Lost", "Found"]:
        return jsonify({
            "error": "Select Lost or Found."
        }), 400

    if not re.fullmatch(r"[0-9]{10}", phone):
        return jsonify({
            "error": "Enter a valid 10-digit mobile number."
        }), 400

    con = get_db()

    con.execute("""
        INSERT INTO items
        (name, description, location, item_type, phone)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        description,
        location,
        item_type,
        phone
    ))

    con.commit()
    con.close()

    return jsonify({
        "message": "Item reported successfully!"
    }), 201


# ---------------- GET ALL ITEMS API ----------------

@app.route("/api/items", methods=["GET"])
def get_items():

    con = get_db()

    rows = con.execute("""
        SELECT * FROM items
        ORDER BY id DESC
    """).fetchall()

    con.close()

    items = []

    for row in rows:

        items.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "location": row["location"],
            "item_type": row["item_type"],
            "phone": mask_phone(row["phone"]),
            "status": row["status"]
        })

    return jsonify(items)


# ---------------- MARK ITEM AS RECOVERED ----------------

@app.route("/api/items/<int:item_id>/recover", methods=["POST"])
def recover(item_id):

    con = get_db()

    cursor = con.execute("""
        UPDATE items
        SET status = 'Recovered'
        WHERE id = ? AND status = 'Open'
    """, (item_id,))

    con.commit()
    updated = cursor.rowcount

    con.close()

    if updated == 0:
        return jsonify({
            "error": "Item not found or already recovered."
        }), 404

    return jsonify({
        "message": "Item marked as recovered successfully!"
    })


# ---------------- START APPLICATION ----------------

create_table()

if __name__ == "__main__":
    app.run(debug=True)