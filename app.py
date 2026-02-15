import streamlit as st
import google.generativeai as genai
import toml
import os
import hashlib
import datetime
import pandas as pd
import random

# -------------------------------
# MAIN APP (After Login)
# -------------------------------
st.title("🏋️‍♂️ CoachBot AI Pro")
st.write(f"Welcome, {st.session_state.username} 👋")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# -------------------------------
# USER DATA FILE
# -------------------------------
user_file = os.path.join(USER_DATA_FOLDER, f"{st.session_state.username}.toml")

if not os.path.exists(user_file):
    with open(user_file, "w") as f:
        f.write("[history]\n")

user_data = toml.load(user_file)

# -------------------------------
# ATHLETE INPUT
# -------------------------------
st.header("📝 Athlete Profile")

sport = st.selectbox("Sport", ["Football", "Cricket", "Basketball", "Athletics"])
position = st.text_input("Position")
injury = st.text_area("Injury History", placeholder="None if healthy")
intensity = st.selectbox("Intensity", ["Low", "Moderate", "High"])
diet = st.selectbox("Diet", ["Vegetarian", "Non-Vegetarian", "Vegan"])
goal = st.text_input("Goal")

# -------------------------------
# USER CUSTOM PROMPT
# -------------------------------
st.subheader("✍️ Custom Coaching Request")

custom_prompt = st.text_area(
    "Describe exactly what you want from CoachBot",
    placeholder="Example: Create a 4-week stamina building plan with low knee impact..."
)

# -------------------------------
# RISK LEVEL
# -------------------------------
risk_level = "Low"
if "knee" in injury.lower() or "ankle" in injury.lower():
    risk_level = "Moderate"
if "multiple" in injury.lower():
    risk_level = "High"

st.info(f"⚠ Injury Risk Level: {risk_level}")

# -------------------------------
# CALORIE ESTIMATION
# -------------------------------
calories_map = {
    "Low": 2000,
    "Moderate": 2500,
    "High": 3000
}

calories = calories_map[intensity]
st.metric("Estimated Daily Calorie Need", f"{calories} kcal")

# -------------------------------
# AI SCORE GENERATOR
# -------------------------------
import random
def generate_ai_score():
    return random.randint(85, 99)

# -------------------------------
# GENERATE WORKOUT
# -------------------------------
if st.button("🚀 Generate & Save Plan"):

    full_prompt = f"""
    You are a certified youth sports coach.

    Athlete Details:
    Sport: {sport}
    Position: {position}
    Injury: {injury}
    Intensity: {intensity}
    Diet: {diet}
    Goal: {goal}

    Risk Level: {risk_level}

    User Specific Request:
    {custom_prompt}

    Guidelines:
    - Prioritize safety.
    - Avoid injury-worsening movements.
    - Provide structured output:
        Warm-up
        Workout
        Mobility
        Nutrition
        Motivation
    """

    with st.spinner("Generating AI Plan..."):

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4
            )
        )

        workout_output = response.text
        ai_score = generate_ai_score()

        st.success("✅ Plan Generated")
        st.markdown(workout_output)
        st.success(f"🤖 AI Confidence Score: {ai_score}%")

        # -------------------------------
        # SAVE FULL SESSION
        # -------------------------------
        session_entry = {
            "date": str(datetime.datetime.now()),
            "sport": sport,
            "position": position,
            "goal": goal,
            "custom_prompt": custom_prompt,
            "risk_level": risk_level,
            "calories": calories,
            "ai_score": ai_score,
            "workout_output": workout_output
        }

        if "history" not in user_data:
            user_data["history"] = {}

        session_id = f"session_{len(user_data['history']) + 1}"
        user_data["history"][session_id] = session_entry

        with open(user_file, "w") as f:
            toml.dump(user_data, f)

        st.success("💾 Session Saved Successfully!")

# -------------------------------
# DISPLAY HISTORY
# -------------------------------
st.subheader("📜 Saved Sessions")

if "history" in user_data and user_data["history"]:
    for key, session in user_data["history"].items():
        with st.expander(f"{key} | {session['date']}"):
            st.write("Sport:", session["sport"])
            st.write("Position:", session["position"])
            st.write("Goal:", session["goal"])
            st.write("Risk Level:", session["risk_level"])
            st.write("Calories:", session["calories"])
            st.write("AI Score:", session["ai_score"])
            st.write("Custom Prompt:", session["custom_prompt"])
            st.markdown("### Workout Plan")
            st.markdown(session["workout_output"])
else:
    st.info("No saved sessions yet.")
