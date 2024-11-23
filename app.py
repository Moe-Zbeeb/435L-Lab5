#!/usr/bin/env python3
import sqlite3
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Flask app setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE = 'database.db'

def connect_to_db():
    """
    Establish a connection to the SQLite database.
    Returns:
        sqlite3.Connection: Database connection object.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row  # Enable accessing columns by name
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection failed: {e}")
        return None

def create_db_table():
    """
    Create the 'users' table in the SQLite database if it doesn't exist.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    country TEXT NOT NULL
                );
                ''')
                conn.commit()
                logging.info("User table ensured in database.")
            except sqlite3.Error as e:
                logging.error(f"Failed to create users table: {e}")
        else:
            logging.error("No database connection available to create table.")

def insert_user(user):
    """
    Insert a new user into the database.
    
    Args:
        user (dict): User information.
    
    Returns:
        dict: Inserted user details or empty dict on failure.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, phone, address, country) VALUES (?, ?, ?, ?, ?)",
                    (user['name'], user['email'], user['phone'], user['address'], user['country'])
                )
                conn.commit()
                user_id = cursor.lastrowid
                logging.info(f"Inserted user with ID: {user_id}")
                return get_user_by_id(user_id)
            except sqlite3.IntegrityError as e:
                logging.error(f"Integrity Error inserting user: {e}")
                return {"error": "Email must be unique."}
            except sqlite3.Error as e:
                logging.error(f"Error inserting user: {e}")
                return {"error": "Failed to insert user."}
        else:
            return {"error": "Database connection failed."}

def get_users():
    """
    Retrieve all users from the database.
    
    Returns:
        list: List of user dictionaries.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
                rows = cursor.fetchall()
                users = [dict(row) for row in rows]
                logging.info(f"Fetched {len(users)} users from database.")
                return users
            except sqlite3.Error as e:
                logging.error(f"Error fetching users: {e}")
                return []
        else:
            logging.error("Database connection failed when fetching users.")
            return []

def get_user_by_id(user_id):
    """
    Retrieve a single user by their ID.
    
    Args:
        user_id (int): The user's ID.
    
    Returns:
        dict: User details or empty dict if not found.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    user = dict(row)
                    logging.info(f"Fetched user with ID: {user_id}")
                    return user
                else:
                    logging.warning(f"No user found with ID: {user_id}")
                    return {}
            except sqlite3.Error as e:
                logging.error(f"Error fetching user by ID: {e}")
                return {}
        else:
            logging.error("Database connection failed when fetching user by ID.")
            return {}

def update_user(user):
    """
    Update an existing user's information.
    
    Args:
        user (dict): Updated user information including 'user_id'.
    
    Returns:
        dict: Updated user details or empty dict on failure.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET name = ?, email = ?, phone = ?, address = ?, country = ?
                    WHERE user_id = ?
                    """,
                    (user['name'], user['email'], user['phone'], user['address'], user['country'], user['user_id'])
                )
                conn.commit()
                if cursor.rowcount == 0:
                    logging.warning(f"No user found to update with ID: {user['user_id']}")
                    return {"error": "User not found."}
                logging.info(f"Updated user with ID: {user['user_id']}")
                return get_user_by_id(user['user_id'])
            except sqlite3.IntegrityError as e:
                logging.error(f"Integrity Error updating user: {e}")
                return {"error": "Email must be unique."}
            except sqlite3.Error as e:
                logging.error(f"Error updating user: {e}")
                return {"error": "Failed to update user."}
        else:
            return {"error": "Database connection failed."}

def delete_user(user_id):
    """
    Delete a user from the database.
    
    Args:
        user_id (int): The user's ID.
    
    Returns:
        dict: Status message.
    """
    with connect_to_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn.commit()
                if cursor.rowcount == 0:
                    logging.warning(f"No user found to delete with ID: {user_id}")
                    return {"status": "User not found."}
                logging.info(f"Deleted user with ID: {user_id}")
                return {"status": "User deleted successfully."}
            except sqlite3.Error as e:
                logging.error(f"Error deleting user: {e}")
                return {"status": "Failed to delete user."}
        else:
            return {"status": "Database connection failed."}

# Initialize the database table
create_db_table()

# API Endpoints
@app.route('/api/users', methods=['GET'])
def api_get_users():
    users = get_users()
    return jsonify(users), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        return jsonify(user), 200
    else:
        return jsonify({"error": "User not found."}), 404

@app.route('/api/users/add', methods=['POST'])
def api_add_user():
    user = request.get_json()
    required_fields = ['name', 'email', 'phone', 'address', 'country']
    
    # Validate input
    if not user:
        logging.warning("No input data provided for adding user.")
        return jsonify({"error": "No input data provided."}), 400
    if not all(field in user for field in required_fields):
        missing = [field for field in required_fields if field not in user]
        logging.warning(f"Missing fields for adding user: {missing}")
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    inserted_user = insert_user(user)
    if "error" in inserted_user:
        return jsonify(inserted_user), 400
    return jsonify(inserted_user), 201

@app.route('/api/users/update', methods=['PUT'])
def api_update_user():
    user = request.get_json()
    required_fields = ['user_id', 'name', 'email', 'phone', 'address', 'country']
    
    # Validate input
    if not user:
        logging.warning("No input data provided for updating user.")
        return jsonify({"error": "No input data provided."}), 400
    if not all(field in user for field in required_fields):
        missing = [field for field in required_fields if field not in user]
        logging.warning(f"Missing fields for updating user: {missing}")
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    updated_user = update_user(user)
    if "error" in updated_user:
        return jsonify(updated_user), 400
    return jsonify(updated_user), 200

@app.route('/api/users/delete/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    result = delete_user(user_id)
    if result.get("status") == "User deleted successfully.":
        return jsonify(result), 200
    elif result.get("status") == "User not found.":
        return jsonify(result), 404
    else:
        return jsonify(result), 400

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
