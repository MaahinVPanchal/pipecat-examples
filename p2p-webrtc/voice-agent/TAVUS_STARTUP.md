# 🤖 Tavus AI Avatar - Direct Access Guide

## 🚀 Quick Start

### 1. Start the Server
```bash
python server.py
```

### 2. Access Tavus Avatar Directly
Open your browser to: **http://localhost:7860/tavus**

This will load the Tavus conversation directly without any interface.

## 📋 Conversation Details

- **Conversation ID**: `c1ceaa9417df9413`
- **Direct URL**: `https://tavus.daily.co/c1ceaa9417df9413`
- **Status**: Active
- **Persona ID**: `p48fdf065d6b`
- **Replica ID**: `r62baeccd777`

## 🔧 Configuration

### Environment Variables (.env)
```
GOOGLE_API_KEY=AIzaSyDXOEcTO6wzvXbNlP1xRf1PWuvB88UO_P4
TAVUS_API_KEY=74dcf5156075462aaf67710f1eaad2e4
TAVUS_REPLICA_ID=rf4703150052
TAVUS_PERSONA_ID=p48fdf065d6b
```

## 🌐 Available Endpoints

- **Direct Tavus Access**: `http://localhost:7860/tavus`
- **Full Interface**: `http://localhost:7860/`
- **API Status**: `http://localhost:7860/api/tavus/status`
- **Debug Info**: `http://localhost:7860/api/debug/tavus-status`

## 🎯 Features

✅ **Direct video conversation** with Tavus AI Avatar  
✅ **Full-screen experience** - no UI distractions  
✅ **Auto-loading** - connects immediately  
✅ **Camera & microphone** access for interaction  
✅ **Real-time AI responses** powered by your replica  

## 🔄 To Update Conversation

If you want to use a different conversation, update the URL in `tavus-direct.html`:

```html
<iframe src="https://tavus.daily.co/YOUR_CONVERSATION_ID">
```

## 🎊 Usage

1. **Start server**: `python server.py`
2. **Open browser**: `http://localhost:7860/tavus`
3. **Allow camera/microphone** when prompted
4. **Start talking** to your AI avatar!

The avatar will respond in real-time with voice and video, powered by your Tavus replica and Gemini Live integration.