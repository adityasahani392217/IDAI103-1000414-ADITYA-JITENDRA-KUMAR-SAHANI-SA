# ==========================================
# IMPORTS
# ==========================================
import streamlit as st
import google.generativeai as genai
import toml
import os
import hashlib
import datetime
import pandas as pd
import random
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# ==========================================
# STORAGE CONFIG
# ==========================================
USER_DATA_FOLDER = "user_data"
USERS_FILE = "users.toml"

if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("[users]\n")

users = toml.load(USERS_FILE)

# ==========================================
# PASSWORD HASHING
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# SESSION INIT
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ==========================================
# AUTHENTICATION
# ==========================================
def show_auth():
    st.title("🔐 CoachBot AI Authentication")
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
                    st.success("Login Successful")
                else:
                    st.error("Incorrect Password")
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

# ==========================================
# SHOW AUTH IF NOT LOGGED IN
# ==========================================
if not st.session_state.logged_in:
    show_auth()
    st.stop()

# ==========================================
# GEMINI CONFIG
# ==========================================
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-pro")

# ==========================================
# MAIN APP
# ==========================================
st.title("🏋️‍♂️ CoachBot AI Pro")
st.write(f"Welcome, {st.session_state.username} 👋")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# USER FILE
# ==========================================
username = st.session_state.username
user_file = os.path.join(USER_DATA_FOLDER, f"{username}.toml")

if not os.path.exists(user_file):
    with open(user_file, "w") as f:
        f.write("[history]\n")

user_data = toml.load(user_file)

# ==========================================
# ATHLETE INPUT
# ==========================================
st.header("📝 Athlete Profile")

sport = st.selectbox("Sport", ["Football", "Cricket", "Basketball", "Athletics"])
position = st.text_input("Position")
injury = st.text_area("Injury History")
intensity = st.selectbox("Intensity", ["Low", "Moderate", "High"])
diet = st.selectbox("Diet", ["Vegetarian", "Non-Vegetarian", "Vegan"])
goal = st.text_input("Goal")

custom_prompt = st.text_area("✍️ Custom Coaching Request")

# ==========================================
# CALORIE ESTIMATE
# ==========================================
calories_map = {"Low": 2000, "Moderate": 2500, "High": 3000}
calories = calories_map[intensity]
st.metric("Estimated Calories", f"{calories} kcal")

# ==========================================
# GENERATE AI SCORE
# ==========================================
def generate_ai_score():
    return random.randint(85, 99)

# ==========================================
# GENERATE WORKOUT
# ==========================================
if st.button("🚀 Generate & Save Plan"):

    full_prompt = f"""
    You are a certified youth coach.

    Sport: {sport}
    Position: {position}
    Injury: {injury}
    Intensity: {intensity}
    Diet: {diet}
    Goal: {goal}

    User Request:
    {custom_prompt}

    Provide:
    - Warm-up
    - Workout
    - Mobility
    - Nutrition
    - Motivation
    """

    with st.spinner("Generating plan..."):
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.4)
        )

        workout_output = response.text
        ai_score = generate_ai_score()

        st.success("Plan Generated")
        st.markdown(workout_output)
        st.success(f"AI Confidence Score: {ai_score}%")

        session_entry = {
            "date": str(datetime.datetime.now()),
            "ai_score": ai_score,
            "calories": calories,
            "workout_output": workout_output
        }

        if "history" not in user_data:
            user_data["history"] = {}

        session_id = f"session_{len(user_data['history']) + 1}"
        user_data["history"][session_id] = session_entry

        with open(user_file, "w") as f:
            toml.dump(user_data, f)

# ==========================================
# DISPLAY HISTORY
# ==========================================
st.header("📜 Session History")

if "history" in user_data and user_data["history"]:
    scores = []
    dates = []

    for key, session in user_data["history"].items():
        scores.append(session["ai_score"])
        dates.append(key)

        with st.expander(f"{key}"):
            st.write("Calories:", session["calories"])
            st.write("AI Score:", session["ai_score"])
            st.markdown(session["workout_output"])

            # PDF Export
            if st.button(f"Download PDF - {key}"):

                pdf_file = f"{key}.pdf"
                doc = SimpleDocTemplate(pdf_file, pagesize=letter)
                elements = []

                styles = getSampleStyleSheet()
                elements.append(Paragraph("CoachBot AI Workout Plan", styles["Heading1"]))
                elements.append(Spacer(1, 0.3 * inch))
                elements.append(Paragraph(session["workout_output"], styles["Normal"]))

                doc.build(elements)

                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="Download Workout PDF",
                        data=f,
                        file_name=pdf_file,
                        mime="application/pdf"
                    )

    # ==========================================
    # PROGRESS GRAPH
    # ==========================================
    st.subheader("📈 AI Score Progress")

    fig, ax = plt.subplots()
    ax.plot(dates, scores, marker='o')
    ax.set_ylabel("AI Score")
    ax.set_xlabel("Session")
    ax.set_title("Progress Over Time")
    st.pyplot(fig)

else:
    st.info("No sessions saved yet.")
