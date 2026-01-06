# HDFC Mutual Funds Advisor Scheduler 📅

A next-generation, voice-enabled AI scheduling assistant designed for HDFC Mutual Funds. This application blends a generative AI chat experience with a traditional manual booking interface ("Hybrid UI"), allowing users to book appointments with financial advisors seamlessly.

## ✨ Key Features

### 🧠 Hybrid AI Interface
- **Generative Chat**: Context-aware AI assistant (powered by Gemini) that understands natural language booking requests.
- **Manual Schedule**: A traditional calendar view for users who prefer point-and-click.
- **Hybrid Mode**: The best of both worlds—AI chat with interactive widgets (calendar carousels, booking cards) rendered directly in the stream.

### 🎙️ Voice Interaction ("Agent Edge")
- **Hands-Free Booking**: Full speech-to-text (STT) and text-to-speech (TTS) integration using **Groq**.
- **Agent Edge UI**: Futuristic, breathing glow overlay that indicates active listening state.

### 📅 Robust Scheduling Engine
- **Real-time Availability**: Checks actual slots against a persisted database.
- **Waitlist Management**: Users can join a waitlist for fully booked slots.
- **Booking Management**: Lookup, reschedule, or cancel existing appointments.
- **Calendar Integration**: Automatically syncs confirmed bookings to a Google Calendar.

### 🔐 Admin Portal
- **Secure Access**: Password-protected dashboard for advisors.
- **Management**: View all bookings, see user names, and manage schedule capacity.
- **Cloud Sync**: Data persistence handling for cloud deployments (Render) via automated Git sync.

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Google Cloud Service Account (for Calendar integration)
- API Keys for: Gemini (Google), Groq (Voice), and GitHub (for data sync)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Atman-Deshmane/NextLeap_Voice_Assistant.git
   cd NextLeap_Voice_Assistant
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Required Variables:*
   - `GEMINI_API_KEY_NextLeap`: For the LLM brain.
   - `GROQ_API_KEY`: For voice capabilities.
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Path to your service account credential file.

### Running the Application

Start the Flask server:
```bash
python app.py
```
Open your browser to: `http://localhost:5001`

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JS (No heavy frameworks)
- **AI/LLM**: Google Gemini 2.0 Flash (via `google-genai` SDK)
- **Voice**: Groq API (Whisper for STT, Orpheus for TTS)
- **Database**: JSON-based flat file store (`store.json`) with Git-based cloud persistence.

## 📂 Project Structure

- `app.py`: Main Flask application entry point.
- `services/`: Core logic modules.
  - `llm_engine.py`: Manages the AI conversation loop and tool calling.
  - `db_manager.py`: Handles all booking, slot, and waitlist data.
  - `groq_voice.py`: Voice processing service.
- `templates/index.html`: The single-page responsive UI.
- `store.json`: The database file (tracked by Git for simple cloud persistence).

## 🔒 Admin Access
To access the admin panel, click the **"🔐 Admin"** button in the header and enter the configured admin password.
