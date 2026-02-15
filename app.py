import streamlit as st
import google.generativeai as genai
import toml
import os
import hashlib
import datetime
import pandas as pd

# -------------------------------
# FILE PATHS
# -------------------------------
USERS_FILE = "users.toml"
USER_DATA_FOLDER = "user_data"

if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("[users]\n")

users = toml.load(USERS_FILE)

# -------------------------------
# HASH PASSWORD
# -------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------------
# SESSION INIT
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------
# AUTH UI
# -------------------------------
def show_auth():

    st.title("🔐 CoachBot AI Login System")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    # LOGIN
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            if username in users["users"]:
                if users["users"][username]["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful!")
                else:
                    st.error("Incorrect password")
            else:
                st.error("User not found")

    # SIGNUP
    with tab2:
        new_user = st.text_input("Create Username", key="new_user")
        new_pass = st.text_input("Create Password", type="password", key="new_pass")

        if st.button("Create Account"):
            if new_user in users["users"]:
                st.error("Username already exists")
            elif len(new_pass) < 6:
                st.warning("Password must be at least 6 characters")
            else:
                users["users"][new_user] = {
                    "password": hash_password(new_pass)
                }
                with open(USERS_FILE, "w") as f:
                    toml.dump(users, f)

                st.success("Account created! Please login.")

# -------------------------------
# IF NOT LOGGED IN → SHOW AUTH
# -------------------------------
if not st.session_state.logged_in:
    show_auth()
else:
    # -------------------------------
    # MAIN APP
    # -------------------------------
    st.title("🏋️‍♂️ CoachBot AI")
    st.write(f"Welcome, {st.session_state.username} 👋")

    if st.button("Logout"):
        st.session_state.logged_in = False

    # -------------------------------
    # USER DATA FILE
    # -------------------------------
    user_file = os.path.join(USER_DATA_FOLDER, f"{st.session_state.username}.toml")

    if not os.path.exists(user_file):
        with open(user_file, "w") as f:
            f.write("[history]\n")

    user_data = toml.load(user_file)

    # -------------------------------
    # USER INPUT
    # -------------------------------
    sport = st.selectbox("Sport", ["Football", "Cricket", "Basketball", "Athletics"])
    goal = st.text_input("Training Goal")

    if st.button("Save Session"):
        session_entry = {
            "date": str(datetime.datetime.now()),
            "sport": sport,
            "goal": goal
        }

        if "history" not in user_data:
            user_data["history"] = {}

        session_id = f"session_{len(user_data['history']) + 1}"
        user_data["history"][session_id] = session_entry

        with open(user_file, "w") as f:
            toml.dump(user_data, f)

        st.success("Session Saved Successfully!")

    # -------------------------------
    # DISPLAY HISTORY
    # -------------------------------
    st.subheader("📜 Your Training History")

    if "history" in user_data and user_data["history"]:
        history_list = list(user_data["history"].values())
        df = pd.DataFrame(history_list)
        st.dataframe(df)
    else:
        st.info("No sessions saved yet.")
