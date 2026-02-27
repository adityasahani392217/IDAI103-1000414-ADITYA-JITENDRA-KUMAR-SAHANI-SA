# 🏋️ Next Gen Sports Lab — Smart Fitness Coaching Assistant

**Student Name:** Aditya Jitendra Kumar Sahani  
**Registration No:** 1000414  
**Course:** Generative AI  
**Assessment:** Formative Assessment (FA-2)  
**Project Title:** AI Powered Sports Coaching Assistant

---

## 🔗 Live App Access

Access the deployed app here: https://idai103-1000414-aditya-jitendra-kumar-sahani-sa.streamlit.app/

---

## � App Journey & Screenshots

Here is a walkthrough of the CoachBot AI experience:

### 1. Welcome & Start
The journey begins with an engaging startup screen.
![Start Screen](assets/App%20Screenshots/Start.png)

### 2. Authentication
Users can securely log in or create a new account.
![Login Screen](assets/App%20Screenshots/Login%20Screen.png)
![Signup Screen](assets/App%20Screenshots/Signup.png)

### 3. Athlete Profile Creation
New users set up their personalized profile, including sport, position, goals, and injury history.
![Athlete Profile Creation](assets/App%20Screenshots/Athlete%20Profile%20Creation%20.png)

### 4. Dashboard & AI Chat
The main hub where athletes can chat with their AI coach for personalized advice.
![Dashboard](assets/App%20Screenshots/Dashboard.png)

### 5. Daily Tracker
Athletes can log their daily progress, including water intake, meals, and exercises.
![Water Tracker](assets/App%20Screenshots/Water%20Tracker.png)
![Food Tracker](assets/App%20Screenshots/Food%20Tracker.png)
![Exercise Tracker](assets/App%20Screenshots/Exercise%20Tracker.png)

### 6. Feedback
Users can provide feedback to help improve the AI coaching experience.
![Feedback](assets/App%20Screenshots/Feedback.png)

---

## �📌 Project Overview

CoachBot AI is a smart web-based fitness coaching assistant built with **Python**, **Streamlit**, and **Google Gemini AI**.

It generates personalized coaching guidance for young athletes based on:
- Sport
- Player position
- Injury history
- Training intensity
- Diet preference
- Fitness goal
- Custom coaching request

The system simulates practical youth coaching support for users who may not have access to professional trainers.

---

## 🎯 Problem Definition

Many young athletes do not have access to expert coaching. Unsafe workouts and poor injury management can lead to long-term health issues.

CoachBot AI addresses this by:
- Generating personalized workout plans
- Adapting guidance for injury-safe recovery
- Promoting safe and consistent training habits
- Improving nutrition awareness
- Making coaching support more accessible using AI

---

## 🔎 In-Depth Research Conducted

To make the assistant practical and realistic, in-depth research was carried out in four areas:

### 1) Sport-Specific Workout Needs

- **Football:** agility, acceleration, repeated sprint ability, lower-body power, change-of-direction drills, and match-day recovery protocols.
- **Cricket:** role-specific conditioning (batting endurance, bowling workload management, shoulder and core stability, rotational strength).
- **Athletics:** event-driven periodization (sprints, middle distance, jumps, throws), technique-first training blocks, and controlled load progression.
- **Cross-sport principles:** warm-up quality, progressive overload, recovery windows, hydration, and sleep-aware training schedules.

### 2) Position-Based Training Differences

- **Goalkeeper vs Striker (Football):**
   - Goalkeeper plans emphasize reaction speed, lateral explosiveness, diving mechanics, shoulder mobility, and short-burst power.
   - Striker plans emphasize sprint repeatability, finishing under fatigue, acceleration-deceleration control, and hamstring resilience.
- **Cricket positions:**
   - Fast bowlers require workload caps, posterior-chain strength, ankle/knee control, and recovery-centric mobility.
   - Batters and wicketkeepers require reflex training, hand-eye coordination, trunk stability, and sustained concentration drills.

### 3) Youth Injury Patterns and Safe Adaptations

- Research covered high-frequency youth sports injuries such as ankle sprains, knee strain, overuse shoulder pain, hamstring tightness, and lower-back stress.
- Adaptation rules were mapped into prompt logic:
   - reduce impact volume during pain flare-ups,
   - switch to low-load mobility and stability blocks,
   - apply return-to-play progression rather than sudden full-intensity training,
   - always include caution notes and professional referral reminders for persistent pain.

### 4) AI as a Real Coach Simulation

- Prompt templates were structured to mirror coach-like reasoning: assess athlete context → select safe load → output actionable session plan.
- Output design intentionally includes warm-up, main work, cooldown/recovery, and nutrition guidance to feel like a complete coaching conversation.
- Tone engineering focuses on youth-friendly motivation, clarity, and practical next steps.

These research findings directly guided the model prompts, safety checks, and output format.

---

## 🎯 Defined Objectives

- **Empower youth with AI-based personal training:** deliver personalized guidance even when expert coaching access is limited.
- **Generate adaptive routines by condition and position:** tailor workout intensity and exercise selection using sport, role, and injury context.
- **Promote safety, motivation, and nutrition awareness:** keep recommendations practical, injury-conscious, and behavior-focused.
- **Improve accessibility in low-resource settings:** transform simple athlete inputs into meaningful, structured coaching output.

---

## ⚙️ Model Integration (Gemini AI)

- **Model Used:** `gemini-3-flash-preview`
- **SDK:** `google-generativeai`
- **Configuration:** low temperature for safer, structured workout output

The app constructs context-aware prompts from athlete inputs and generates structured coaching plans.

---

## 🧠 User Inputs Captured

The system collects:
- Sport (Football, Cricket, Basketball, Athletics)
- Player position
- Injury history
- Training intensity (Low / Moderate / High)
- Diet preference (Vegetarian / Non-Vegetarian / Vegan)
- Fitness goal
- Custom coaching request

**Example scenario:** Cricket fast bowler recovering from knee injury, aiming to improve stamina safely.

---

## ✨ Core Features

### ✅ Personalized Workout Generation
AI generates:
- Warm-up routine
- Main workout plan
- Mobility/recovery guidance
- Nutrition advice
- Motivation guidance

### 🔐 Authentication System
- User sign-up and login
- Password hashing using SHA-256
- Per-user session history storage

### 📊 Athlete Risk Analysis
Automatic injury risk classification from injury text:
- Low Risk
- Moderate Risk
- High Risk

### 🔥 Session History Tracking
Each session stores:
- Date/time
- Sport and position
- Goal and custom prompt
- Risk level
- Estimated calories
- AI confidence score
- Full generated workout output

### 📄 PDF Export
Workout plans can be exported as downloadable PDF reports.

### 📈 Progress Analytics
Visualizes AI score trend across sessions using Matplotlib.

---

## 🧩 Prompt Engineering

Structured prompts were designed for sports coaching use cases, including:
- Sport-specific workouts
- Injury recovery plans
- Warm-up and cooldown guidance
- Mobility and flexibility routines
- Nutrition and hydration planning
- Motivation and discipline coaching

**Prompt style example:**

> You are a certified youth sports coach.  
> Sport: Cricket  
> Position: Fast Bowler  
> Injury: Knee strain  
> Goal: Improve stamina safely  
> Provide: Warm-up, Workout, Mobility, Nutrition, Motivation.

---

## ✅ Model Validation & Testing

The app was tested with:
- Multiple sport categories
- Different injury conditions
- Various intensity levels
- Edge-case scenarios involving recovery

Outputs were reviewed for:
- Safety
- Practical usefulness
- Coaching realism

Prompts were iteratively refined after testing.

---

## 🚀 Deployment

### Local Run

1. Clone your repository
   ```bash
   git clone <your-repository-link>
   cd Next-Gen-Sports-Lab
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Add Streamlit secrets in `.streamlit/secrets.toml`
   ```toml
   GOOGLE_API_KEY = "your_google_gemini_api_key"
   ```

4. Run app
   ```bash
   streamlit run app.py
   ```

### Streamlit Cloud Deployment

1. Push project to GitHub
2. Open Streamlit Cloud
3. Create New App
4. Select repository and branch
5. Set `app.py` as entry point
6. Add `GOOGLE_API_KEY` in Streamlit secrets
7. Deploy

---

## 🧱 Technologies Used

- Python
- Streamlit
- Google Generative AI (Gemini)
- Pandas
- Matplotlib
- TOML
- ReportLab

---

## 📁 Project Structure

```text
CoachBot-AI/
│
├── app.py
├── requirements.txt
├── README.md
├── users.toml           # auto-created at first run
└── user_data/           # auto-created at first run
```

---

## 🌍 Ethical Considerations

- AI guidance is educational and assistive in nature.
- Injury safety and responsible training are prioritized.
- Users are encouraged to consult professionals for medical conditions.
- The system supports accessibility for young athletes with limited coaching access.

---

## 📚 References

- Google Gemini Documentation: https://ai.google.dev
- Streamlit Documentation: https://docs.streamlit.io
- Sports injury prevention and youth training research literature

---

## ✅ Conclusion

CoachBot AI demonstrates how Generative AI can deliver practical, safe, and accessible sports coaching support. It combines prompt engineering, authentication, analytics, PDF reporting, and cloud deployment into a complete real-world educational project.

**⭐ AI Coaching for Everyone — Train Smart, Stay Safe.**
