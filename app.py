import streamlit as st
import google.generativeai as genai
import pandas as pd
import toml
import os
import hashlib

# -------------------------------
# Load or Create Users File
# -------------------------------
USERS_FILE = "users.toml"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("[users]\n")

users = toml.load(USERS_FILE)

# -------------------------------
# Password Hash Function
# -------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------------
# Session State Setup
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------
# Authentication UI
# -------------------------------
def auth_page():
    st.title("🔐 CoachBot AI Authentication")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    # ---------------- LOGIN ----------------
    with tab1:
        st.subheader("Login to Your Account")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            if login_user in users["users"]:
                stored_hash = users["users"][login_user]["password"]
                if stored_hash == hash_password(login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Incorrect Password")
            else:
                st.error("User not found")

    # ---------------- SIGNUP ----------------
    with tab2:
        st.subheader("Create New Account")
        new_user = st.text_input("Choose Username", key="new_user")
        new_pass = st.text_input("Choose Password", type="password", key="new_pass")

        if st.button("Sign Up"):
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
                st.success("Account created successfully! You can now login.")

# -------------------------------
# If Not Logged In → Show Auth
# -------------------------------
if not st.session_state.logged_in:
    auth_page()
    st.stop()
