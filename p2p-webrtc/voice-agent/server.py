#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import asyncio
import sys
import os
from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from bot import run_bot, run_founder_bot, run_admin_tavus_bot, TavusIntegration
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pipecat.transports.smallwebrtc.connection import IceServer, SmallWebRTCConnection

# Load environment variables
load_dotenv(override=True)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:7860"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Store connections by pc_id
pcs_map: Dict[str, SmallWebRTCConnection] = {}

# Store Tavus integrations by connection
tavus_integrations: Dict[str, TavusIntegration] = {}

# Store latest Tavus conversation URL for quick access
latest_tavus_conversation: Dict[str, str] = {}


ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    )
]


@app.post("/api/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(sdp=request["sdp"], type=request["type"])
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)
            # Clean up Tavus integration if exists
            if webrtc_connection.pc_id in tavus_integrations:
                tavus = tavus_integrations[webrtc_connection.pc_id]
                await tavus.end_conversation()
                del tavus_integrations[webrtc_connection.pc_id]

        # Create Tavus integration for this connection
        tavus = TavusIntegration(
            api_key=os.getenv("TAVUS_API_KEY"),
            replica_id=os.getenv("TAVUS_REPLICA_ID"),
            persona_id=os.getenv("TAVUS_PERSONA_ID")
        )
        
        background_tasks.add_task(run_bot, pipecat_connection, tavus)

    answer = pipecat_connection.get_answer()
    pc_id = answer["pc_id"]
    
    # Store the connection
    pcs_map[pc_id] = pipecat_connection

    return answer




@app.get("/api/tavus/conversation/{pc_id}")
async def get_tavus_conversation_url(pc_id: str):
    """Get Tavus conversation URL for a specific connection"""
    if pc_id not in tavus_integrations:
        raise HTTPException(status_code=404, detail="Tavus conversation not found")
    
    tavus = tavus_integrations[pc_id]
    
    # Return stored conversation data if available
    if hasattr(tavus, 'conversation_data') and tavus.conversation_data:
        return JSONResponse(tavus.conversation_data)
    
    # Fallback to getting status
    status = await tavus.get_conversation_status()
    return JSONResponse({
        "conversation_id": tavus.conversation_id,
        "conversation_url": status.get("conversation_url"),
        "status": status.get("status")
    })


@app.get("/")
async def serve_index():
    return FileResponse("index.html")


@app.get("/api/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return JSONResponse({
        "message": "CORS is working!",
        "timestamp": "2025-01-19",
        "status": "success"
    })


@app.get("/register")
async def serve_registration():
    """Serve the startup registration interface"""
    return FileResponse("register.html")


@app.post("/api/register-founder")
async def register_founder(request: dict, background_tasks: BackgroundTasks):
    """Create Gemini Realtime connection for founder registration"""
    pc_id = request.get("pc_id")
    founder_data = request.get("founder_data", {})

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for founder registration: {pc_id}")
        await pipecat_connection.renegotiate(sdp=request["sdp"], type=request["type"])
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding founder connection: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)

        # Create founder-specific bot with registration context
        background_tasks.add_task(run_founder_bot, pipecat_connection, founder_data)

    answer = pipecat_connection.get_answer()
    pc_id = answer["pc_id"]
    
    # Store the connection
    pcs_map[pc_id] = pipecat_connection

    return answer


@app.options("/api/admin-tavus")
async def admin_tavus_options():
    """Handle OPTIONS request for admin-tavus endpoint"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.post("/api/admin-tavus")
async def create_admin_tavus_conversation(request: dict, background_tasks: BackgroundTasks):
    """Create Tavus conversation for admin with company PDF context"""
    company_data = request.get("company_data", {})
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for admin Tavus: {pc_id}")
        await pipecat_connection.renegotiate(sdp=request["sdp"], type=request["type"])
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding admin Tavus connection: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)
            if webrtc_connection.pc_id in tavus_integrations:
                tavus = tavus_integrations[webrtc_connection.pc_id]
                await tavus.end_conversation()
                del tavus_integrations[webrtc_connection.pc_id]

        # Create admin Tavus bot with company context
        background_tasks.add_task(run_admin_tavus_bot, pipecat_connection, company_data)

    answer = pipecat_connection.get_answer()
    pc_id = answer["pc_id"]
    
    # Store the connection
    pcs_map[pc_id] = pipecat_connection

    # Return with explicit CORS headers
    return JSONResponse(
        content=answer,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.get("/tavus")
async def serve_tavus_direct():
    return FileResponse("tavus-direct.html")


@app.get("/api/tavus/status")
async def get_tavus_status():
    """Get Tavus API status and configuration"""
    api_key = os.getenv("TAVUS_API_KEY")
    replica_id = os.getenv("TAVUS_REPLICA_ID")
    
    if not api_key or not replica_id:
        raise HTTPException(
            status_code=500, 
            detail="Tavus API key or replica ID not configured"
        )
    
    return JSONResponse({
        "status": "configured",
        "replica_id": replica_id,
        "api_key_present": bool(api_key),
        "active_connections": len(pcs_map),
        "tavus_integrations": len(tavus_integrations)
    })


@app.get("/api/debug/force-video")
async def force_video_display():
    """Debug endpoint to test video container display"""
    return JSONResponse({
        "message": "Use this endpoint to test video display",
        "instructions": "Call showTavusAvatar() from browser console"
    })


@app.get("/api/debug/tavus-status")
async def debug_tavus_status():
    """Debug endpoint to check Tavus integration status"""
    return JSONResponse({
        "tavus_integrations_count": len(tavus_integrations),
        "tavus_integration_keys": list(tavus_integrations.keys()),
        "pcs_map_count": len(pcs_map),
        "pcs_map_keys": list(pcs_map.keys()),
        "latest_conversation": latest_tavus_conversation
    })


@app.post("/api/create-tavus-conversation")
async def create_tavus_conversation(request: dict):
    """Create a new Tavus conversation with company context and return the URL"""
    company_data = request.get("company_data", {})
    company_name = company_data.get('companyName', 'Unknown Company')
    
    logger.info(f"🎬 Creating Tavus conversation for: {company_name}")
    logger.info(f"📊 Using replica: {os.getenv('TAVUS_REPLICA_ID')}")
    
    tavus = TavusIntegration(
        api_key=os.getenv("TAVUS_API_KEY"),
        replica_id=os.getenv("TAVUS_REPLICA_ID"),
        persona_id=os.getenv("TAVUS_PERSONA_ID")
    )
    
    # Set company context for the conversation
    tavus.company_context = company_data
    
    conversation_data = await tavus.create_conversation()
    if conversation_data:
        # Store for later access
        global latest_tavus_conversation
        latest_tavus_conversation = conversation_data
        
        conversation_id = conversation_data.get('conversation_id')
        conversation_url = conversation_data.get('conversation_url')
        
        logger.info(f"✅ Created Tavus conversation for {company_name}")
        logger.info(f"🆔 Conversation ID: {conversation_id}")
        logger.info(f"🔗 Conversation URL: {conversation_url}")
        
        return JSONResponse(conversation_data)
    else:
        logger.error(f"❌ Failed to create Tavus conversation for {company_name}")
        raise HTTPException(status_code=500, detail="Failed to create Tavus conversation")


@app.post("/api/tavus/create-conversation")
async def create_tavus_conversation_legacy():
    """Legacy endpoint - Create a new Tavus conversation and return the URL"""
    tavus = TavusIntegration(
        api_key=os.getenv("TAVUS_API_KEY"),
        replica_id=os.getenv("TAVUS_REPLICA_ID"),
        persona_id=os.getenv("TAVUS_PERSONA_ID")
    )
    
    conversation_data = await tavus.create_conversation()
    if conversation_data:
        # Store for later access
        global latest_tavus_conversation
        latest_tavus_conversation = conversation_data
        logger.info(f"Created Tavus conversation via legacy API: {conversation_data.get('conversation_id')}")
        return JSONResponse(conversation_data)
    else:
        raise HTTPException(status_code=500, detail="Failed to create Tavus conversation")


@app.get("/api/tavus/latest")
async def get_latest_tavus_conversation():
    """Get the most recent Tavus conversation data"""
    logger.info(f"Tavus integrations available: {len(tavus_integrations)}")
    logger.info(f"Tavus integration keys: {list(tavus_integrations.keys())}")
    
    if not tavus_integrations:
        raise HTTPException(status_code=404, detail="No Tavus conversations found")
    
    # Get the most recent conversation
    latest_pc_id = list(tavus_integrations.keys())[-1]
    tavus = tavus_integrations[latest_pc_id]
    
    logger.info(f"Latest Tavus conversation: {tavus.conversation_id}")
    logger.info(f"Conversation URL: {tavus.conversation_url}")
    
    if hasattr(tavus, 'conversation_data') and tavus.conversation_data:
        return JSONResponse({
            "pc_id": latest_pc_id,
            **tavus.conversation_data
        })
    
    return JSONResponse({
        "pc_id": latest_pc_id,
        "conversation_id": tavus.conversation_id,
        "conversation_url": tavus.conversation_url,
        "status": "active"
    })


@app.get("/api/tavus/conversations")
async def get_active_conversations():
    """Get status of all active Tavus conversations"""
    conversations = []
    
    for pc_id, tavus in tavus_integrations.items():
        status = await tavus.get_conversation_status()
        conversations.append({
            "pc_id": pc_id,
            "conversation_id": tavus.conversation_id,
            "status": status.get("status", "unknown")
        })
    
    return JSONResponse({"conversations": conversations})


@app.post("/api/tavus/end/{pc_id}")
async def end_tavus_conversation(pc_id: str):
    """End a specific Tavus conversation"""
    if pc_id not in tavus_integrations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    tavus = tavus_integrations[pc_id]
    await tavus.end_conversation()
    del tavus_integrations[pc_id]
    
    return JSONResponse({"status": "ended", "pc_id": pc_id})


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Run app
    coros = [pc.disconnect() for pc in pcs_map.values()]
    await asyncio.gather(*coros)
    pcs_map.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC demo")
    parser.add_argument(
        "--host", default="localhost", help="Host for HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Port for HTTP server (default: 7860)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    logger.remove(0)
    if args.verbose:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="DEBUG")

    uvicorn.run(app, host=args.host, port=args.port)
