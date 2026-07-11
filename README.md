# 🥗 IBM NutriBot — AI Nutrition Agent

> **Powered by IBM Watsonx.ai · IBM Granite 3 8B Instruct · Flask · Bootstrap 5**

A full-stack, AI-powered nutrition advisor web application that delivers personalised meal plans, calorie analysis, BMI/TDEE calculations, healthy recipe suggestions, and family diet recommendations — all through a modern chat UI with dark mode and mobile responsiveness.

---

## ✨ Features

| Module | Description |
|---|---|
| 💬 **AI Chat** | Conversational nutrition advice powered by IBM Granite on Watsonx.ai |
| ⚖️ **BMI & TDEE** | Mifflin-St Jeor calculator with macronutrient breakdown |
| 📅 **7-Day Meal Planner** | Personalised weekly plans for any diet, goal, and cuisine |
| 🍽️ **Meal Analyser** | Instant nutritional analysis of any described meal |
| 👨‍👩‍👧 **Family Plan** | Multi-member family nutrition planning with individual needs |
| 🍳 **Recipe Finder** | Healthy recipes generated from your available ingredients |
| 📊 **Dashboard** | Quick stats, tips, and usage overview |
| 🌙 **Dark Mode** | Persistent dark/light theme with smooth transition |

---

## 🗂️ Project Structure

```
ibmutrition/
├── app.py                  ← Flask backend + IBM Watsonx.ai + AGENT_INSTRUCTIONS
├── requirements.txt        ← Python dependencies
├── .env                    ← Secrets (NOT committed to git)
├── .env.example            ← Template for .env
├── .gitignore
├── templates/
│   └── index.html          ← Full frontend: chat, BMI, meal planner, family plan
└── static/
    ├── css/                ← (place custom CSS overrides here if needed)
    ├── js/                 ← (place custom JS here if needed)
    └── images/             ← (place images/icons here)
```

---

## 🚀 Quick Start

### 1 · Prerequisites

- Python 3.10+ installed
- An [IBM Cloud account](https://cloud.ibm.com/registration) (free tier available)
- An IBM Watsonx.ai project

### 2 · Clone / Download

```bash
git clone https://github.com/your-org/ibmutrition.git
cd ibmutrition
```

### 3 · Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4 · Install Dependencies

```bash
pip install -r requirements.txt
```

### 5 · Configure IBM Watsonx Credentials

**Get your credentials:**

1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Go to **Manage → Access (IAM) → API keys** → Create an API key
3. Open [IBM Watsonx.ai](https://dataplatform.cloud.ibm.com) → select or create a project
4. Copy the **Project ID** from the project settings

**Create your `.env` file** (copy from template):

```bash
cp .env.example .env
```

Edit `.env`:

```env
IBM_API_KEY=your_actual_ibm_cloud_api_key
IBM_PROJECT_ID=your_actual_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=any-random-string-here
```

> ⚠️ Never commit `.env` to version control. It is already listed in `.gitignore`.

### 6 · Run the Application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## 🎛️ Customising the Agent (AGENT_INSTRUCTIONS)

All agent behaviour is controlled by the `AGENT_INSTRUCTIONS` dictionary at the top of [`app.py`](app.py). No prompt engineering knowledge required — just edit the values:

```python
AGENT_INSTRUCTIONS = {

    # ── Change the agent's name and role
    "agent_name": "NutriBot",
    "agent_role": "Expert AI Nutrition Advisor and Dietitian",

    # ── Adjust tone: "formal", "casual", "clinical", etc.
    "tone": "friendly, empathetic, professional, and encouraging",

    # ── Turn emojis on/off (False for clinical deployments)
    "use_emojis": True,

    # ── Add or remove supported diet types
    "supported_diets": ["Vegetarian", "Vegan", "Keto", ...],

    # ── Indian food preferences
    "indian_food_expertise": {
        "enabled": True,
        "preferred_cuisines": ["North Indian", "South Indian", ...],
        "suggest_local_alternatives": True,
    },

    # ── Safety guardrails
    "safety_rules": [
        "Never diagnose medical conditions.",
        "Do not suggest below 1200 kcal/day.",
        ...
    ],

    # ── Meal plan defaults
    "meal_plan_structure": {
        "meals_per_day": 5,
        "include_water_intake": True,
        "include_macros": True,
    },

    # ── Extra instructions injected into every system prompt
    "system_prompt_extras": "Your custom instructions here...",
}
```

---

## 🌍 Deployment

### Option A · Local (Development)

```bash
python app.py
```

### Option B · Production with Gunicorn (Linux/macOS)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option C · Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t nutribot .
docker run -p 5000:5000 --env-file .env nutribot
```

### Option D · IBM Code Engine (Serverless)

```bash
# Install IBM Cloud CLI + Code Engine plugin first
ibmcloud login
ibmcloud ce project create --name nutribot-project
ibmcloud ce app create \
  --name nutribot \
  --image icr.io/your-ns/nutribot:latest \
  --env-from-secret nutribot-secrets \
  --port 5000 \
  --min-scale 0 \
  --max-scale 3
```

### Option E · Railway / Render / Fly.io

Set the following environment variables in the platform dashboard:
- `IBM_API_KEY`
- `IBM_PROJECT_ID`
- `IBM_WATSONX_URL`
- `FLASK_SECRET_KEY`

Start command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`

---

## 🔐 Security Notes

- API keys are loaded exclusively via `python-dotenv` from `.env` (never hard-coded)
- `.env` is excluded from git via `.gitignore`
- Session data is stored server-side using Flask's signed cookie session
- The `FLASK_SECRET_KEY` should be a long random string in production

---

## 🧪 Testing the API Endpoints

```bash
# Health check
curl http://localhost:5000/

# Chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a healthy breakfast plan for weight loss"}'

# BMI Calculator
curl -X POST http://localhost:5000/api/bmi \
  -H "Content-Type: application/json" \
  -d '{"weight": 70, "height": 170, "age": 28, "gender": "male", "activity": "moderately_active"}'

# 7-Day Meal Plan
curl -X POST http://localhost:5000/api/meal_plan \
  -H "Content-Type: application/json" \
  -d '{"goal": "weight loss", "diet": "vegetarian", "cuisine": "Indian", "calories": 1800}'

# Analyse a meal
curl -X POST http://localhost:5000/api/analyze_meal \
  -H "Content-Type: application/json" \
  -d '{"meal": "2 rotis with dal and salad"}'

# Recipe finder
curl -X POST http://localhost:5000/api/recipe \
  -H "Content-Type: application/json" \
  -d '{"ingredients": "spinach, paneer, tomato, garlic", "diet": "vegetarian"}'
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `flask` | 3.0.3 | Web framework |
| `python-dotenv` | 1.0.1 | Load `.env` secrets |
| `ibm-watsonx-ai` | 1.1.2 | IBM Watsonx.ai / Granite models |
| `requests` | 2.32.3 | HTTP client |
| `gunicorn` | 22.0.0 | Production WSGI server |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## ⚠️ Disclaimer

NutriBot provides general nutrition information for educational purposes only. It is **not** a substitute for professional medical or dietetic advice. Always consult a qualified healthcare provider before making significant dietary changes.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Built with ❤️ using IBM Watsonx.ai &amp; IBM Granite</strong>
</div>
