# Installation and Setup Guide 🛠️

This guide will walk you through setting up and running the PK Schedule Sync project.

## 📋 Prerequisites

- Python 3.12 or higher
- [Ollama](https://ollama.ai) (optional, for AI features)
- Slack App Token (optional, for notifications)
- Google Cloud Service Account (optional, for Calendar sync)

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root and fill in the following values:

```env
DATABASE_URL=sqlite:///./schedule_sync.db

PK_SHEET_REGEX=NIESTACJONARNE
PK_SCHEDULE_URL=https://it.pk.edu.pl/studenci/na-studiach/rozklady-zajec/
SYNC_SCHEDULE="*/1 * * * *"

SLACK_BOT_TOKEN=[your-token]
SLACK_MENTIONS=[your-user-id]

SLACK_CHANNEL=[slack-channel]
SLACK_CHANNEL_JOB_STATUS=[slack-status-channel]
AI_SERVICE_URL=http://localhost:11434

GOOGLE_CALENDAR_ID=[google-calendar-id]
GOOGLE_SERVICE_ACCOUNT_FILE=[google-calendar-key]
```

### 3. AI Setup (Optional but Recommended)

The project uses a local Ollama instance for data enrichment.
1.  Install [Ollama](https://ollama.ai).
2.  Create the custom model from the provided `Modelfile`:
    ```bash
    ollama create pk-llama -f resources/model/Modelfile
    ```

### 4. Running the Application

To start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. You can access the automatic documentation (Swagger UI) at `http://localhost:8000/docs`.
