# 🗄️ Smart Database Assistant

> Query, edit, and export any database using plain English — no SQL, no Python, no formulas.

Built with **Flask** · **Python** · **Google Gemini AI** · **SQLite**

---

## ✨ Features

- **Upload any data** — CSV, Excel (.xlsx, .xls), SQLite (.db), SQL dumps
- **Ask in plain English** — "Show employees earning more than ₹50,000"
- **Edit naturally** — "Delete duplicate rows", "Increase salary by 10%"
- **Safe by design** — Original file never modified; all edits on a working copy
- **Download anywhere** — Export as SQLite, CSV, or Excel
- **Conversation memory** — Multi-turn follow-up questions work naturally
- **One command** — Frontend and backend run together, no Node.js needed

---

## 🖼️ Example Queries

```
Show top 10 highest-paid employees
Count employees in each department
Average salary by department
Delete rows where salary is NULL
Increase salary by 10% for HR department
Rename column emp_name to employee_name
Show duplicate records
Products with rating above 4.5
```

---

## 🗂️ Project Structure

```
smart-db-v2/
├── app.py            # Flask app — all routes + serves frontend
├── database.py       # SQLite operations & file conversions
├── ai.py             # Gemini AI layer (modular, swap providers easily)
├── validator.py      # SQL safety validation
├── test.py           # API connection test
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html    # Complete frontend (HTML + CSS + JS)
├── uploads/          # Temporary uploaded files
└── working_db/       # Working database copies
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- A free [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Steps

```bash
# 1. Clone or download the project
cd smart-db-v2

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Test API connection
python3 test.py

# 6. Run the app
python3 app.py
```

Open **http://localhost:5000** in your browser.

---

## ☁️ Deploy on Render (Free)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/smart-db-assistant.git
git push -u origin main
```

### Step 2 — Deploy on Render
1. Go to [render.com](https://render.com) and sign up
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Set the following:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Python Version:** 3.11
5. Add environment variable:
   - Key: `GEMINI_API_KEY`
   - Value: your Gemini API key
6. Click **Deploy**

Your app will be live at `https://your-app-name.onrender.com`

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main UI |
| `POST` | `/upload` | Upload a file |
| `POST` | `/chat` | Send a natural language message |
| `GET` | `/preview` | Get current data preview |
| `GET` | `/download?format=sqlite\|csv\|xlsx` | Download modified database |
| `POST` | `/reset` | Restore original data |

---

## 🔒 Security

- Original uploaded file is **never modified**
- All edits happen on an isolated working copy
- SQL injection prevented via strict allowlist validation
- Blocked: `PRAGMA`, `ATTACH`, `DETACH`, `VACUUM`, multiple statements
- Files auto-deleted after session ends
- 50 MB upload limit

---

## 🔄 Swap the AI Provider

The AI layer is fully modular. To replace Gemini with OpenAI, Groq, or any other provider:

1. Open `ai.py`
2. Replace the `call_gemini()` function with your provider's API call
3. Keep the same `nl_to_sql()` and `fix_sql()` function signatures

No other files need to change.

---


