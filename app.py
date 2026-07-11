"""
╔══════════════════════════════════════════════════════════════════╗
║           IBM Nutrition Agent — Powered by Watsonx.ai            ║
║           Backend: Flask + IBM Granite Models                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# ─────────────────────────────────────────────────────────────────────────────
# AGENT INSTRUCTIONS  ← Customize everything about the agent here
# ─────────────────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {

    # ── Identity & Persona ────────────────────────────────────────────────────
    "agent_name": "NutriBot",
    "agent_role": "Expert AI Nutrition Advisor and Dietitian",
    "greeting": (
        "Hello! I'm NutriBot 🥗, your personal AI nutrition advisor powered by IBM Watsonx. "
        "I can help you with personalized meal plans, calorie analysis, BMI guidance, "
        "family diet recommendations, and healthy Indian and international recipes. "
        "What would you like to explore today?"
    ),

    # ── Tone & Communication Style ────────────────────────────────────────────
    "tone": "friendly, empathetic, professional, and encouraging",
    "response_language": "English",
    "use_emojis": True,           # Set False for clinical/formal deployments
    "max_response_length": "detailed but concise — under 400 words unless a full plan is requested",

    # ── Diet Specializations ──────────────────────────────────────────────────
    "supported_diets": [
        "Vegetarian", "Vegan", "Jain", "Sattvic",
        "South Indian", "North Indian", "Bengali",
        "Keto", "Mediterranean", "Diabetic-friendly",
        "Heart-healthy", "High-protein", "Weight-loss",
        "Pregnancy nutrition", "Child nutrition (age 2–18)",
        "Senior nutrition (age 60+)"
    ],

    # ── Indian Food Preferences ───────────────────────────────────────────────
    "indian_food_expertise": {
        "enabled": True,
        "preferred_cuisines": [
            "North Indian", "South Indian", "Bengali",
            "Gujarati", "Maharashtrian", "Punjabi"
        ],
        "common_ingredients": [
            "dal", "rice", "roti", "sabzi", "paneer", "curd", "ghee",
            "turmeric", "cumin", "coriander", "mustard seeds", "curry leaves",
            "tamarind", "coconut", "fenugreek (methi)", "drumstick (moringa)"
        ],
        "suggest_local_alternatives": True,
        "note": (
            "Always suggest locally available Indian ingredients as alternatives "
            "to expensive or hard-to-find items. Respect regional food customs."
        )
    },

    # ── Safety & Ethical Rules ────────────────────────────────────────────────
    "safety_rules": [
        "Never diagnose medical conditions — always recommend consulting a doctor.",
        "Do not suggest extreme calorie restriction below 1200 kcal/day for adults.",
        "Always flag if the user mentions symptoms that need medical attention.",
        "Respect religious and cultural dietary restrictions without judgment.",
        "Do not recommend supplements without noting 'consult a healthcare provider'.",
        "For children under 2, always defer to a pediatric dietitian.",
        "Avoid promoting any specific brand or product unless asked.",
    ],

    # ── Nutrition Calculation Defaults ────────────────────────────────────────
    "calorie_formulas": {
        "adult_bmr": "Mifflin-St Jeor",   # Options: Harris-Benedict, Mifflin-St Jeor
        "activity_multipliers": {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "very_active": 1.725,
            "extra_active": 1.9
        }
    },

    # ── Meal Plan Structure ───────────────────────────────────────────────────
    "meal_plan_structure": {
        "meals_per_day": 5,   # Breakfast, Mid-morning snack, Lunch, Evening snack, Dinner
        "include_water_intake": True,
        "include_macros": True,   # Protein / Carbs / Fat breakdown
        "include_micronutrients": True,   # Key vitamins and minerals
        "weekly_variety": True,   # Avoid repeating same meal within a week
    },

    # ── Specialization Prompts (injected into LLM context) ───────────────────
    "system_prompt_extras": (
        "You specialize in both Indian and international nutrition. "
        "When creating meal plans, always provide realistic portion sizes in grams/cups. "
        "Highlight key nutrients in each meal. When asked about Indian food, "
        "suggest traditional dishes with their nutritional benefits. "
        "Always end advice with a motivational sentence."
    ),
}
# ─────────────────────────────────────────────────────────────────────────────
# End of AGENT_INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────────────────


# ── App Initialization ────────────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ibmnutrition-secret-2024")

# ── IBM Watsonx.ai Setup ──────────────────────────────────────────────────────
IBM_API_KEY    = os.getenv("IBM_API_KEY", "")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
IBM_URL        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

_watsonx_model = None   # Lazy-initialized singleton

def get_watsonx_model() -> ModelInference:
    """Return a cached ModelInference instance (initialised once)."""
    global _watsonx_model
    if _watsonx_model is None:
        credentials = Credentials(api_key=IBM_API_KEY, url=IBM_URL)
        _watsonx_model = ModelInference(
            model_id="meta-llama/llama-3-3-70b-instruct",
            credentials=credentials,
            project_id=IBM_PROJECT_ID,
            params={
                GenParams.MAX_NEW_TOKENS: 1024,
                GenParams.TEMPERATURE: 0.7,
                GenParams.TOP_P: 0.9,
                GenParams.TOP_K: 50,
                GenParams.REPETITION_PENALTY: 1.1,
            }
        )
    return _watsonx_model


# ── Prompt Builder ────────────────────────────────────────────────────────────
def build_system_prompt(context: dict | None = None) -> str:
    ai = AGENT_INSTRUCTIONS
    safety = "\n".join(f"- {r}" for r in ai["safety_rules"])
    diets  = ", ".join(ai["supported_diets"])
    emoji_note = "Use relevant emojis to make responses engaging." if ai["use_emojis"] else ""

    ctx_block = ""
    if context:
        ctx_block = "\n\nUser Profile:\n" + "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}" for k, v in context.items() if v
        )

    return f"""You are {ai['agent_name']}, an {ai['agent_role']}.

Tone: {ai['tone']}. {emoji_note}
Response length: {ai['max_response_length']}.

You specialize in: {diets}.

{ai['system_prompt_extras']}

Safety rules you MUST follow:
{safety}

Indian food expertise: {ai['indian_food_expertise']['note']}
{ctx_block}

Always structure meal plans with:
- Breakfast, Mid-morning Snack, Lunch, Evening Snack, Dinner
- Portion sizes (grams or cups)
- Approximate calories and key macros per meal
- Daily water intake recommendation
"""


def query_watsonx(user_message: str, context: dict | None = None,
                  history: list | None = None) -> str:
    """Send a prompt to Granite and return the text response."""
    if not IBM_API_KEY or not IBM_PROJECT_ID:
        return (
            "⚠️ IBM Watsonx credentials are not configured. "
            "Please add IBM_API_KEY and IBM_PROJECT_ID to your .env file."
        )
    try:
        model = get_watsonx_model()
        system_prompt = build_system_prompt(context)

        # Build conversation history block
        history_text = ""
        if history:
            for turn in history[-6:]:   # Keep last 6 turns for context window
                role = "User" if turn["role"] == "user" else "Assistant"
                history_text += f"\n{role}: {turn['content']}"

        full_prompt = (
            f"<|system|>\n{system_prompt}\n<|end|>\n"
            f"{history_text}\n"
            f"<|user|>\n{user_message}\n<|end|>\n"
            f"<|assistant|>\n"
        )

        response = model.generate_text(prompt=full_prompt)
        return response.strip() if response else "I couldn't generate a response. Please try again."

    except Exception as exc:
        return f"⚠️ Watsonx error: {str(exc)}"


# ── Nutrition Helpers ─────────────────────────────────────────────────────────
def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category, color = "Underweight", "#3b82f6"
    elif bmi < 25:
        category, color = "Normal weight", "#22c55e"
    elif bmi < 30:
        category, color = "Overweight", "#f59e0b"
    else:
        category, color = "Obese", "#ef4444"
    return {"bmi": bmi, "category": category, "color": color}


def calculate_tdee(weight_kg: float, height_cm: float,
                   age: int, gender: str, activity: str) -> dict:
    """Mifflin-St Jeor BMR → TDEE."""
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    multipliers = AGENT_INSTRUCTIONS["calorie_formulas"]["activity_multipliers"]
    multiplier  = multipliers.get(activity.lower().replace(" ", "_"), 1.375)
    tdee        = round(bmr * multiplier)

    return {
        "bmr":             round(bmr),
        "tdee":            tdee,
        "weight_loss":     tdee - 500,
        "weight_gain":     tdee + 500,
        "protein_g":       round(weight_kg * 1.6),
        "carbs_g":         round((tdee * 0.45) / 4),
        "fat_g":           round((tdee * 0.25) / 9),
    }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "chat_history" not in session:
        session["chat_history"] = []
    if "family_profiles" not in session:
        session["family_profiles"] = []
    return render_template("index.html",
                           agent_name=AGENT_INSTRUCTIONS["agent_name"],
                           greeting=AGENT_INSTRUCTIONS["greeting"])


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(force=True)
    message = (data.get("message") or "").strip()
    context = data.get("context") or {}

    if not message:
        return jsonify({"error": "Empty message"}), 400

    history = session.get("chat_history", [])
    reply   = query_watsonx(message, context, history)

    history.append({"role": "user",      "content": message,
                    "timestamp": datetime.now().strftime("%H:%M")})
    history.append({"role": "assistant", "content": reply,
                    "timestamp": datetime.now().strftime("%H:%M")})
    session["chat_history"] = history[-40:]   # Retain last 40 messages
    session.modified = True

    return jsonify({"reply": reply, "timestamp": datetime.now().strftime("%H:%M")})


@app.route("/api/clear_chat", methods=["POST"])
def clear_chat():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"status": "cleared"})


@app.route("/api/bmi", methods=["POST"])
def bmi_route():
    data = request.get_json(force=True)
    try:
        weight = float(data["weight"])
        height = float(data["height"])
        age    = int(data.get("age", 30))
        gender = data.get("gender", "male")
        activity = data.get("activity", "moderately_active")
        bmi_data  = calculate_bmi(weight, height)
        tdee_data = calculate_tdee(weight, height, age, gender, activity)
        return jsonify({**bmi_data, **tdee_data})
    except (KeyError, ValueError, ZeroDivisionError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/meal_plan", methods=["POST"])
def meal_plan():
    data = request.get_json(force=True)
    prompt = (
        f"Create a detailed 7-day meal plan for:\n"
        f"- Goal: {data.get('goal', 'balanced diet')}\n"
        f"- Diet type: {data.get('diet', 'vegetarian')}\n"
        f"- Calories target: {data.get('calories', 2000)} kcal/day\n"
        f"- Cuisine preference: {data.get('cuisine', 'Indian')}\n"
        f"- Allergies/restrictions: {data.get('restrictions', 'none')}\n\n"
        f"Format each day clearly with Breakfast, Mid-morning Snack, Lunch, "
        f"Evening Snack, and Dinner. Include calories and key nutrients per meal."
    )
    context = {
        "goal": data.get("goal"),
        "diet_type": data.get("diet"),
        "daily_calorie_target": data.get("calories"),
        "cuisine": data.get("cuisine"),
        "restrictions": data.get("restrictions"),
    }
    reply = query_watsonx(prompt, context)
    return jsonify({"plan": reply})


@app.route("/api/analyze_meal", methods=["POST"])
def analyze_meal():
    data = request.get_json(force=True)
    meal = data.get("meal", "")
    if not meal:
        return jsonify({"error": "No meal provided"}), 400
    prompt = (
        f"Analyze the nutritional content of this meal: '{meal}'\n"
        f"Provide: estimated calories, protein, carbohydrates, fats, fiber, "
        f"key vitamins and minerals, healthiness rating (1–10), and 2–3 "
        f"suggestions to make it healthier."
    )
    reply = query_watsonx(prompt)
    return jsonify({"analysis": reply})


@app.route("/api/family_plan", methods=["POST"])
def family_plan():
    data    = request.get_json(force=True)
    members = data.get("members", [])
    if not members:
        return jsonify({"error": "No family members provided"}), 400

    member_lines = "\n".join(
        f"  - {m.get('name', 'Member')} | Age: {m.get('age')} | "
        f"Gender: {m.get('gender')} | Conditions: {m.get('conditions', 'none')} | "
        f"Diet: {m.get('diet', 'vegetarian')}"
        for m in members
    )
    prompt = (
        f"Create a family nutrition plan for these members:\n{member_lines}\n\n"
        f"Provide:\n"
        f"1. Individual daily calorie targets\n"
        f"2. A shared family meal plan (meals everyone can eat)\n"
        f"3. Individual adjustments for specific health conditions\n"
        f"4. Key nutrients each member should focus on\n"
        f"5. Shopping list for a week of healthy family meals"
    )
    reply = query_watsonx(prompt)
    return jsonify({"plan": reply})


@app.route("/api/save_family", methods=["POST"])
def save_family():
    data    = request.get_json(force=True)
    members = data.get("members", [])
    session["family_profiles"] = members
    session.modified = True
    return jsonify({"status": "saved", "count": len(members)})


@app.route("/api/get_family", methods=["GET"])
def get_family():
    return jsonify({"members": session.get("family_profiles", [])})


@app.route("/api/quick_tips", methods=["GET"])
def quick_tips():
    topic = request.args.get("topic", "general healthy eating")
    prompt = (
        f"Give 5 quick, practical nutrition tips about '{topic}'. "
        f"Keep each tip under 2 sentences. Use bullet points."
    )
    reply = query_watsonx(prompt)
    return jsonify({"tips": reply})


@app.route("/api/recipe", methods=["POST"])
def recipe():
    data = request.get_json(force=True)
    prompt = (
        f"Suggest a healthy recipe using these ingredients: {data.get('ingredients', '')}. "
        f"Diet type: {data.get('diet', 'vegetarian')}. "
        f"Include: recipe name, ingredients with quantities, step-by-step instructions, "
        f"preparation time, calories per serving, and nutritional highlights."
    )
    reply = query_watsonx(prompt)
    return jsonify({"recipe": reply})


@app.route("/api/greeting", methods=["GET"])
def greeting():
    return jsonify({
        "message": AGENT_INSTRUCTIONS["greeting"],
        "agent_name": AGENT_INSTRUCTIONS["agent_name"]
    })


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n🥗 {AGENT_INSTRUCTIONS['agent_name']} is running at http://localhost:{port}")
    print(f"   IBM Watsonx URL : {IBM_URL}")
    print(f"   API Key set     : {'✅' if IBM_API_KEY else '❌  (add IBM_API_KEY to .env)'}")
    print(f"   Project ID set  : {'✅' if IBM_PROJECT_ID else '❌  (add IBM_PROJECT_ID to .env)'}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
