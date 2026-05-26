<div align="center">
  <h1>🛡️ C3MS - Anti-Corruption Monitoring Dashboard</h1>
  <p><strong>An advanced, AI-driven, multi-modal anti-corruption reporting platform with blockchain integrity.</strong></p>
</div>

---

## 📖 Overview
**C3MS (Kerala Corruption Reporting Bot)** is a sophisticated complaint management system designed to track, mitigate, and analyze corruption cases securely. By integrating multi-modal data intake (Text, Voice, PDF, Images) via a Telegram Bot, analyzing complaints using Agentic AI (LangGraph & LLaMA 3), and guaranteeing data tamper-proofing through Blockchain Integrity algorithms, C3MS ensures robust, fair, and secure issue resolution.

## 🏗️ Architecture
The system follows a highly modular, decoupled microservices-inspired architecture:

```mermaid
graph TD
    A[Telegram Bot<br/>Interface Layer] -->|Multi-modal Inputs<br/>Text, Voice, Image, PDF| B(FastAPI Backend)
    B --> C{Preprocessing Layer}
    C -->|Images| D[OCR Extraction]
    C -->|PDFs| E[PDF Parsing]
    C -->|Voice| F[Audio Transcription]
    D & E & F -.-> G[Normalized Text]
    G --> H[Data Layer]
    H --> I[PII Redactor<br/>spaCy NLP]
    I --> J[Blockchain Integrity<br/>Tamper-proofing]
    J --> K[(Pinecone Vector DB<br/>Legal Context Retrieval)]
    K --> L[LangGraph AI Logic]
    L --> M[Categorization Node]
    L --> N[Risk Analysis Node]
    L --> O[Escalation Node]
    M & N & O --> P[LLaMA 3 Model]
    P --> Q[Processed Complaint]
    Q --> R[Streamlit Dashboard<br/>KPIs & Analytics]
    Q -.->|High Risk| S[Telegram Admin Alert]
    B --> T[Redis/Celery Queue]
    T --> U[Background Worker]
    U --> Q
```

## 🧩 Modules
- **Telegram Interface (`interface_layer/app.py`):** FastAPI + `python-telegram-bot` webhook-driven ingestion point that stages uploads, persists a pending record, and publishes processing tasks to Redis.
- **Background Worker (`backend/tasks.py`):** Celery task runner that performs LangGraph analysis, updates complaint status, and sends the final Telegram notification.
- **Data Processor (`data_layer/`):**
  - `pii_redactor`: Masks PII from complaints using NLP (`spaCy`) to ensure user privacy.
  - `blockchain`: Computes cryptographic block hashes for complaint texts, enforcing data integrity.
  - `vector_db`: Interacts with **Pinecone** to seamlessly augment AI with state laws and regulations (Retrieval-Augmented Generation).
- **AI Backend (`backend/logic/`):** Implements a **LangGraph StateGraph** pipeline containing conditional edges to categorize, process, and optionally escalate high-risk complaints.
- **Preprocessing (`preprocessing/`):** Media intelligence layer extending parsing to Images, PDFs, and Voice Messages.
- **Monitoring Dashboard (`dashboard/app.py`):** Real-time analytics, Live Feed UI, and KPIs powered by **Streamlit** and **Plotly**.

## 🧠 AI Usage
C3MS relies on cutting-edge local AI usage tailored to privacy and robustness:
- **Local Large Language Models (LLMs):** Powered by **Ollama (LLaMA 3)** running locally via `llm_wrapper.py` to ensure complete privacy, zero data leakage, and high-quality NLP inferences.
- **Agentic Workflows (LangGraph):** Synthesizes AI tasks through dedicated nodes:
  - `Categorization Node`: Determines the nature of the corruption.
  - `Retrieval Node`: Consults the vector database for related laws.
  - `Risk Analysis Node`: Diagnoses the severity of the submission and flags for escalation.
  - `Escalation Node`: Evaluates conditional bounds and notifies administrators directly inside Telegram.
- **Retrieval-Augmented Generation (RAG):** Employs `sentence-transformers` and **Pinecone** to anchor LLM responses firmly in actual regulations, reducing hallucination bounds.
- **NLP Entity Masking (`spaCy`):** Detects and anonymizes Names, Locations, and Organizations dynamically.

## ⚙️ Setup & Requirements

### Prerequisites
- **Python 3.9+**
- **[Ollama](https://ollama.com/)** running locally with the `llama3` model. Make sure to pull it: `ollama run llama3`
- **Pinecone** Account & API Key
- **Telegram Bot Token** (obtain from BotFather)

### 1. Clone the repository
```bash
git clone https://github.com/AbhijithPM507/ksum-hackathon.git
cd ksum-hackathon
```

### 2. Install Requirements
Install all required Python dependencies globally or in a virtual environment:
```bash
pip install -r requirements.txt
```
Additionally, download the required Natural Language Processing model for `spaCy` PII redaction:
```bash
python -m spacy download en_core_web_sm
```

### 3. Environment Variables
Create a `.env` file in the root directory and map your configuration keys:
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
ADMIN_CHAT_ID="your_telegram_chat_id"
PINECONE_API_KEY="your_pinecone_api_key_here"
PINECONE_INDEX="your_pinecone_index_name"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

### 4. Running the Application
Because of the decoupled nature, you will run the API, Celery worker, and dashboard independently.

**Terminal 1 — Start Redis:**
Run Redis locally so Celery can queue tasks. If Redis is installed:
```bash
redis-server
```

**Terminal 2 — Start the Celery Worker:**
Run the background worker that processes complaints asynchronously:
```bash
celery -A backend.celery_app worker --loglevel=info
```

**Terminal 3 — Start the Backend API:**
Start the FastAPI server which manages Telegram Bot webhooks:
```bash
uvicorn interface_layer.app:app --reload
```

**Terminal 4 — Start the Dashboard:**
Start the Streamlit Monitoring Dashboard:
```bash
streamlit run dashboard/app.py
```
> **Note:** The Telegram webhook now stages uploads, enqueues a Celery task, and returns `HTTP 200` immediately. The final complaint analysis and user notification are handled by the background worker.
