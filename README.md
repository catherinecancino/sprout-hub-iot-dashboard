# 🌱 Sprout Hub — Smart IoT Soil Monitoring System

Sprout Hub is a smart agriculture monitoring platform that integrates IoT soil sensors, cloud data services, and AI-assisted crop analysis to support data-driven farming decisions.

The system collects real-time soil and environmental data from distributed sensor nodes and visualizes them through an interactive web dashboard. An integrated AI agronomist chatbot analyzes the data and provides recommendations using a knowledge base of crop requirements.

This project was developed as part of an IoT-based Smart Agriculture thesis project.

---

## 🚀 Key Features
📡 **Real-time Sensor Monitoring**

The system continuously collects environmental data from IoT sensor nodes, including:
- Soil moisture
- Soil temperature
- Soil pH
- Nitrogen (N)
- Phosphorus (P)
- Potassium (K)
- Air temperature
- Humidity

Sensor readings are transmitted to Firebase Firestore, enabling real-time updates on the dashboard.

---

🤖 **AI Agronomist Chatbot**

An AI assistant powered by OpenAI GPT models helps users interpret sensor readings and crop requirements.

Capabilities include:
- Soil condition interpretation
- Crop recommendations
- Environmental explanations
- Knowledge retrieval from uploaded documents

The chatbot uses Retrieval-Augmented Generation (RAG) with ChromaDB.

---

📚 **Knowledge Library**   

Users can upload crop-related documents (PDF/DOCX). The system processes these files to extract crop requirements such as:
- Optimal soil pH
- Ideal nitrogen levels
- Moisture requirements
- Temperature ranges

The extracted information is stored in a vector database and used by the AI chatbot.

---

🌾 **Crop-Based Node Monitoring**  

Each sensor node can be assigned a specific crop profile. The system evaluates sensor readings against the optimal thresholds for that crop.

This enables monitoring of multiple crop types across different nodes.

---

🔔 **Smart Alert System** 

Automated alerts are generated when readings fall outside the optimal crop thresholds, including:
- Low soil moisture
- Nutrient deficiencies
- Extreme pH values

---

🔋 **Node Status Monitoring**   

The system tracks Node connectivity status using APScheduler by tracking the last sent data based on a set time. Last sensor update timestamp will also be displayed.

---

🇵🇭 **Bilingual Support**  

The web interface supports both:
- English
- Filipino (Tagalog)

Language switching is implemented using a React context-based translation system.

---

📊 **Data Visualization**  

The dashboard includes interactive charts showing trends for:
- Soil moisture
- Temperature
- pH
- Nutrient levels
- Environmental conditions

Charts are implemented using Recharts.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django, Django REST Framework |
| Database | Firebase Firestore (real-time) |
| Frontend | React (Vite) |
| AI / LLM | OpenAI GPT-4o-mini |
| Vector Database | ChromaDB (RAG) |
| Charts | Recharts |
| IoT Hardware | Raspberry Pi |
| Sensors | 7-in-1 Soil Sensor (CWT NPKPHCTH-S), DHT11 |

---

## 📁 Project Structure

```
AGRITECH_IOT/
│
├── api/                     # Django backend app
│   ├── migrations/
│   ├── chroma_db/                         # Vector database for RAG
│   ├── ai_service.py                      # OpenAI chatbot service
│   ├── rag_service.py                     # Document retrieval system
│   ├── knowledge_library_service.py       # Crop Profile Library
│   ├── services.py                        # IoT data processing & alerts
│   ├── scheduler.py                       # Task for checking node connectivity
│   ├── models.py
│   ├── views.py                           # REST API Endpoints
│   └── urls.py                            # URL Routing
│
├── config/                  # Django project configuration
│   ├── settings.py          # Django Settings
│   ├── urls.py
│   ├── firebase.py          # Firebase initialization
│   └── asgi.py / wsgi.py
│
├── frontend/                # React + Vite dashboard
│   ├── public/
│   ├── src/
│   │   ├── components/              # UI components
│   │   │   ├── Chatbot.jsx          # AI Chatbot Widget
│   │   │   ├── CropSelector.jsx     # Crop to Node Widget
│   │   │   └── Settings.jsx         # Settings Page
│   │   ├── contexts/                # Language support
│   │   │   └── LanguageContext.jsx
│   │   ├── App.jsx                  # Main Dashboard
│   │   ├── main.jsx
│   │   └── firebase.js              # Firebase Client Config
│   ├── package.json
│   └── vite.config.js
│
├── media/                   # Uploaded files
│
├── manage.py                # Django entry point
├── requirements.txt         # Python dependencies
├── db.sqlite3               # Local development database
│
├── soil_main.py             # IoT sensor node script
│
├── serviceAccountKey.json   # Firebase credentials (gitignored)
└── .env / .env.example      # Environment variables
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

There are **two ways** to start the system locally.

### **Option 1 - Quick Start (Recommended)**

Use the batch script to automatically start both the backend and the frontend.

```bash
start-app.bat
```

This script will:
- activate the Python environment
- start the Django backend server
- start the React frontend server

This allows the dashboard to **run with a single command** instead of manually starting each service.

### **Option 2 - Manual Start (Development Mode)**

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
| GET | `/api/v1/ai-status/` | Check AI service status |
| POST | `/api/v1/check-connectivity/` | Manual connectivity check |
| GET | `/api/v1/compare-nodes/` | AI-powered node comparison |

---

## 🌿 Sensor Data Format

Send POST requests to `/api/v1/ingest/` with this JSON structure:

```json
{
  "node_id": "node_A",
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
