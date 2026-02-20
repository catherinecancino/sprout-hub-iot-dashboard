# 🌱 Sprout Hub — Smart IoT Soil Monitoring System

A full-stack smart agriculture web application that monitors real-time soil and environmental conditions using IoT sensor nodes, powered by an AI agronomist chatbot.

---

## 📸 Features

- 📡 **Real-time Sensor Monitoring** — moisture, pH, temperature, NPK, air humidity
- 🤖 **AI Agronomist Chatbot** — powered by OpenAI GPT-4o-mini with RAG support
- 📚 **Knowledge Library** — upload crop documents to extract growing thresholds automatically
- 🌾 **Per-Node Crop Profiles** — assign different crops to different sensor nodes
- 🔔 **Smart Alert System** — automatic alerts when readings go out of range
- 🔋 **Battery & Connectivity Monitoring** — detects offline nodes and low battery
- 🇵🇭 **Bilingual Support** — English and Filipino (Tagalog)
- 📊 **Data Visualization** — live charts for soil and environmental trends

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django, Django REST Framework |
| Database | Firebase Firestore (real-time) |
| Frontend | React (Vite), Recharts |
| AI / LLM | OpenAI GPT-4o-mini |
| Vector Store | ChromaDB (RAG) |
| IoT Hardware | Arduino Gateway, 7-in-1 Soil Sensor (CWT NPKPHCTH-S), DHT11 |

---

## 📁 Project Structure

```
sprout-hub/
├── api/
│   ├── ai_service.py          # OpenAI chatbot logic
│   ├── rag_service.py         # ChromaDB document processing
│   ├── knowledge_library_service.py  # Crop profile management
│   ├── services.py            # IoT data ingestion & alerts
│   ├── views.py               # REST API endpoints
│   ├── urls.py                # URL routing
│   └── chroma_db/             # Vector store (auto-generated, gitignored)
├── config/
│   ├── settings.py            # Django settings
│   ├── firebase.py            # Firebase initialization
│   └── urls.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main dashboard
│   │   ├── components/
│   │   │   ├── Chatbot.jsx    # AI agronomist widget
│   │   │   ├── Settings.jsx   # Settings & knowledge library
│   │   │   └── CropSelector.jsx
│   │   ├── contexts/
│   │   │   └── LanguageContext.jsx  # EN/Filipino translations
│   │   └── firebase.js        # Firebase client config
│   └── package.json
├── .env.example               # Environment variable template
├── .gitignore
├── manage.py
└── requirements.txt
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Firebase project with Firestore enabled
- OpenAI account with API key

---

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/sprout-hub.git
cd sprout-hub
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-your-openai-api-key-here
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a project and enable **Firestore**
3. Go to **Project Settings → Service Accounts → Generate new private key**
4. Save the downloaded file as `serviceAccountKey.json` in the project root
5. Copy your Firebase web config into `frontend/src/firebase.js`

### 5. Frontend Setup

```bash
cd frontend
npm install
```

### 6. Create Required Directories

```bash
mkdir -p api/chroma_db
mkdir -p media/temp
```

---

## 🚀 Running the App

Open **two terminals**:

**Terminal 1 — Django backend:**
```bash
python manage.py runserver
```

**Terminal 2 — React frontend:**
```bash
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/ingest/` | Receive sensor data from nodes |
| POST | `/api/v1/chat/` | AI chatbot query |
| POST | `/api/v1/upload-document/` | Upload crop knowledge document |
| GET | `/api/v1/list-documents/` | List uploaded documents |
| DELETE | `/api/v1/delete-document/<name>/` | Remove a document |
| POST | `/api/v1/search-knowledge/` | Search knowledge base |
| GET | `/api/v1/knowledge-library/` | List all crop profiles |
| GET/DELETE | `/api/v1/knowledge-library/<crop_type>/` | Crop profile detail |
| POST/GET | `/api/v1/assign-crop/` | Assign crop to a node |
| GET | `/api/v1/ollama-status/` | Check AI service status |
| POST | `/api/v1/check-connectivity/` | Manual connectivity check |
| GET | `/api/v1/compare-nodes/` | AI-powered node comparison |

---

## 🌿 Sensor Data Format

Send POST requests to `/api/v1/ingest/` with this JSON structure:

```json
{
  "node_id": "soil_node_01",
  "battery_percentage": 85.5,
  "moisture": 45.5,
  "temperature": 28.2,
  "ph": 6.5,
  "nitrogen": 120,
  "phosphorus": 40,
  "potassium": 180,
  "air_temperature": 30.1,
  "humidity": 60
}
```

---

## 📦 Requirements

Generate your `requirements.txt` with:

```bash
pip freeze > requirements.txt
```

Key dependencies:
```
django
djangorestframework
firebase-admin
python-dotenv
django-cors-headers
openai
chromadb
PyPDF2
python-docx
```

---

## 🔒 Security Notes

- **Never commit** `.env` or `serviceAccountKey.json` — both are in `.gitignore`
- Set `DEBUG=False` and configure `ALLOWED_HOSTS` for production
- Apply proper Firebase Security Rules before deploying

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is for our thesis.

---

> Built with ❤️ for Philippine farmers 🇵🇭