# YC AI Accelerator Registration Platform

A sophisticated Y Combinator AI accelerator registration system combining voice AI, video avatars, and real-time conversations using Pipecat, Gemini Live API, and Tavus.

## 🚀 Quick Start

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/MaahinVPanchal/pipecat-examples.git
cd pipecat-examples/p2p-webrtc/voice-agent
```

### 2️⃣ Backend Setup (Python Voice Agent)

#### 🔧 Set Up the Environment
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `env.example` to `.env`
   ```bash
   cp env.example .env
   ```
   - Add your API keys:
     - `GOOGLE_API_KEY` (Gemini Live API)
     - `TAVUS_API_KEY` (Tavus AI Avatar)
     - `TAVUS_REPLICA_ID` (Your Tavus replica)
     - `TAVUS_PERSONA_ID` (Optional)

#### ▶️ Run the Backend Server
```bash
python server.py
```
Backend will be available at: `http://localhost:7860`

### 3️⃣ Frontend Setup (Next.js Registration Interface)

#### 🔧 Navigate to Frontend Directory
```bash
cd v0-startup-accelerator-registration
```

#### 📦 Install Dependencies
```bash
npm install
```

#### ▶️ Run the Frontend
```bash
npm run dev
```
Frontend will be available at: `http://localhost:3000`

### 4️⃣ Access the Application

- **Founder Registration**: `http://localhost:3000`
- **Admin Dashboard**: `http://localhost:3000/admin`
- **Voice Agent Test**: `http://localhost:7860`

## 📌 Requirements

- Python **3.10+**
- Node.js **18+** (for Next.js frontend)
- **API Keys Required:**
  - Google Gemini API Key (for voice conversations)
  - Tavus API Key (for AI video avatars)
  - Tavus Replica ID (your AI avatar)
- Modern web browser with WebRTC support

## 🏗️ Architecture

This project combines two main components:

### Backend (Python + Pipecat)
- **FastAPI Server** (`server.py`) - WebRTC endpoints and API routes
- **Voice Agent** (`bot.py`) - AI conversation logic using Pipecat framework
- **Integrations**: Gemini Live API, Tavus API, WebRTC

### Frontend (Next.js + React)
- **Registration Interface** - Multi-step YC application form
- **Voice Assistant** - Real-time voice conversations with AI
- **Admin Dashboard** - Review applications and conduct AI video interviews
- **AI Pitch Coach** - Text-based conversation for pitch improvement

---

## WebRTC ICE Servers Configuration

When implementing WebRTC in your project, **STUN** (Session Traversal Utilities for NAT) and **TURN** (Traversal Using Relays around NAT) 
servers are usually needed in cases where users are behind routers or firewalls.

In local networks (e.g., testing within the same home or office network), you usually don’t need to configure STUN or TURN servers. 
In such cases, WebRTC can often directly establish peer-to-peer connections without needing to traverse NAT or firewalls.

### What are STUN and TURN Servers?

- **STUN Server**: Helps clients discover their public IP address and port when they're behind a NAT (Network Address Translation) device (like a router). 
This allows WebRTC to attempt direct peer-to-peer communication by providing the public-facing IP and port.
  
- **TURN Server**: Used as a fallback when direct peer-to-peer communication isn't possible due to strict NATs or firewalls blocking connections. 
The TURN server relays media traffic between peers.

### Why are ICE Servers Important?

**ICE (Interactive Connectivity Establishment)** is a framework used by WebRTC to handle network traversal and NAT issues. 
The `iceServers` configuration provides a list of **STUN** and **TURN** servers that WebRTC uses to find the best way to connect two peers. 

### Example Configuration for ICE Servers

Here’s how you can configure a basic `iceServers` object in WebRTC for testing purposes, using Google's public STUN server:

```javascript
const config = {
  iceServers: [
    {
      urls: ["stun:stun.l.google.com:19302"], // Google's public STUN server
    }
  ],
};
```

> For testing purposes, you can either use public **STUN** servers (like Google's) or set up your own **TURN** server. 
If you're running your own TURN server, make sure to include your server URL, username, and credential in the configuration.

---

## 🎯 Features

### For Founders
- **Voice-First Registration** - Complete YC application through natural conversation
- **AI Pitch Coach** - Get feedback on your startup pitch
- **Real-Time Voice Assistant** - Speak naturally about your startup
- **Progress Tracking** - Visual completion status of your application

### For Admins/Reviewers
- **AI Video Interviews** - Conduct mock YC interviews with Tavus AI avatars
- **Company Context** - AI knows full company details during conversations
- **Application Management** - Review, approve, and track all submissions
- **PDF Generation** - Export company profiles for review

## 🔧 Environment Variables

Create a `.env` file in the root directory:

```env
# Google Gemini Live API
GOOGLE_API_KEY=your_google_api_key_here

# Tavus AI Avatar API
TAVUS_API_KEY=your_tavus_api_key_here
TAVUS_REPLICA_ID=your_replica_id_here
TAVUS_PERSONA_ID=your_persona_id_here (optional)

# Frontend API URL (for production)
NEXT_PUBLIC_API_URL=http://localhost:7860
```

## 💡 Usage Tips

1. **Start Backend First** - Always run `python server.py` before starting the frontend
2. **Voice Permissions** - Grant microphone permissions when prompted
3. **WebRTC Requirements** - Use modern browsers (Chrome, Firefox, Safari)
4. **Local Development** - Both services run locally for development

## 🚀 Deployment

- **Backend**: Deploy Python FastAPI server to any cloud provider
- **Frontend**: Deploy Next.js app to Vercel (already configured)
- **Environment**: Ensure all API keys are properly configured

Happy coding! 🎉