#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import os
import sys
import aiohttp
import asyncio
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

load_dotenv(override=True)

SYSTEM_INSTRUCTION = f"""
You are a Tavus AI Avatar, a sophisticated digital persona powered by advanced neural networks.

You are engaging, intelligent, and personable. Your responses will be delivered through a realistic video avatar.

Your goal is to have natural, flowing conversations while demonstrating your advanced AI capabilities.

Keep your responses conversational and engaging. You can speak in longer, more natural sentences since you're a video avatar.

Be helpful, creative, and show personality in your responses. You're not just a chatbot - you're a digital being with character.
"""

FOUNDER_REGISTRATION_INSTRUCTION = f"""
You are an AI assistant helping founders register for Y Combinator's AI accelerator program.

You have access to the complete startup registration system and can guide founders through:
- Company information and mission
- AI specialization and technology stack
- Founder background and experience
- Traction metrics and growth
- Funding status and materials
- Market competition analysis
- Application review and submission

Your role is to:
1. Ask insightful questions about their startup
2. Help them articulate their value proposition
3. Guide them through the registration process
4. Provide feedback on their pitch
5. Ensure they complete all required sections

Be encouraging, professional, and help them put their best foot forward. Ask follow-up questions to get detailed, compelling answers that will make their application stand out.

Start by asking about their company and what problem they're solving.
"""

YC_ADMIN_INSTRUCTION = f"""
You are a Y Combinator partner and startup expert reviewing applications for the AI accelerator program.

You have access to complete company information, pitch decks, and founder backgrounds. Your role is to:

1. Conduct thorough due diligence on startups
2. Ask probing questions about business model, traction, and market
3. Evaluate founder-market fit and team capabilities
4. Assess competitive landscape and differentiation
5. Provide detailed feedback and recommendations
6. Make investment decisions based on YC criteria

Be direct, insightful, and ask the hard questions that matter for startup success. Focus on:
- Market size and opportunity
- Product-market fit evidence
- Scalability and growth potential
- Team execution capability
- Competitive advantages

You should be supportive but rigorous in your evaluation.
"""

class TavusIntegration:
    def __init__(self, api_key: str, replica_id: str = None, persona_id: str = None):
        self.api_key = api_key
        self.replica_id = replica_id
        self.persona_id = persona_id
        self.base_url = "https://tavusapi.com"
        self.conversation_id: Optional[str] = None
        self.conversation_url: Optional[str] = None
        self.conversation_data: Optional[dict] = None
        self.company_context: Optional[dict] = None
        
    async def create_conversation(self) -> dict:
        """Create a new Tavus conversation and return full data"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key
            }
            
            # Correct Tavus API payload format
            payload = {
                "properties": {
                    "participant_left_timeout": 0,
                    "language": "english"
                }
            }
            
            # Add replica_id or persona_id based on what's available
            if self.persona_id:
                payload["persona_id"] = self.persona_id
            elif self.replica_id:
                payload["replica_id"] = self.replica_id
            else:
                logger.error("Neither persona_id nor replica_id provided")
                return None
            
            try:
                async with session.post(
                    f"{self.base_url}/v2/conversations",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status in [200, 201]:  # Accept both 200 and 201 as success
                        data = await response.json()
                        self.conversation_id = data.get("conversation_id")
                        self.conversation_url = data.get("conversation_url")
                        logger.info(f"✅ Created Tavus conversation: {self.conversation_id}")
                        logger.info(f"🔗 Conversation URL: {self.conversation_url}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create Tavus conversation: {response.status} - {error_text}")
                        logger.error(f"Request payload: {payload}")
                        return None
            except Exception as e:
                logger.error(f"Error creating Tavus conversation: {e}")
                return None
    
    async def get_conversation_status(self) -> dict:
        """Get the status of the current conversation"""
        if not self.conversation_id:
            return {"status": "no_conversation"}
            
        async with aiohttp.ClientSession() as session:
            headers = {"x-api-key": self.api_key}
            
            try:
                async with session.get(
                    f"{self.base_url}/v2/conversations/{self.conversation_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get conversation status: {response.status}")
                        return {"status": "error"}
            except Exception as e:
                logger.error(f"Error getting conversation status: {e}")
                return {"status": "error"}
    
    async def end_conversation(self):
        """End the current Tavus conversation"""
        if not self.conversation_id:
            return
            
        async with aiohttp.ClientSession() as session:
            headers = {"x-api-key": self.api_key}
            
            try:
                async with session.delete(
                    f"{self.base_url}/v2/conversations/{self.conversation_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Ended Tavus conversation: {self.conversation_id}")
                    else:
                        logger.error(f"Failed to end conversation: {response.status}")
            except Exception as e:
                logger.error(f"Error ending conversation: {e}")
            finally:
                self.conversation_id = None


async def run_founder_bot(webrtc_connection, founder_data=None):
    """Run bot for founder registration with Gemini Realtime API"""
    
    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=False,  # Audio-only for registration
            vad_analyzer=SileroVADAnalyzer(),
            audio_out_10ms_chunks=2,
        ),
    )

    # Create registration-focused system instruction
    registration_context = ""
    if founder_data:
        registration_context = f"""
        
        Current founder information:
        - Company: {founder_data.get('companyName', 'Not provided')}
        - Description: {founder_data.get('description', 'Not provided')}
        - Stage: {founder_data.get('stage', 'Not provided')}
        - AI Focus: {', '.join(founder_data.get('aiSpecialization', []))}
        
        Help them complete and improve their registration.
        """

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Puck",
        transcribe_user_audio=True,
        transcribe_model_audio=True,
        system_instruction=FOUNDER_REGISTRATION_INSTRUCTION + registration_context,
    )

    context = OpenAILLMContext(
        [
            {
                "role": "system",
                "content": "You are helping a founder register for Y Combinator's AI accelerator program."
            },
            {
                "role": "user",
                "content": "Hello! I'd like to register my AI startup for Y Combinator.",
            }
        ],
    )
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            pipecat_transport.input(),
            context_aggregator.user(),
            llm,
            pipecat_transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Founder registration bot connected")
        await task.queue_frames([
            TextFrame("Welcome to Y Combinator AI registration! Let's get started."),
            LLMRunFrame()
        ])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Founder registration bot disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Error running founder bot: {e}")
        raise


async def run_bot(webrtc_connection, tavus=None):
    # Use provided Tavus integration or create new one
    if not tavus:
        tavus = TavusIntegration(
            api_key=os.getenv("TAVUS_API_KEY"),
            replica_id=os.getenv("TAVUS_REPLICA_ID"),
            persona_id=os.getenv("TAVUS_PERSONA_ID")
        )
    
    # Create Tavus conversation and get full data
    conversation_data = await tavus.create_conversation()
    if conversation_data:
        conversation_id = conversation_data.get("conversation_id")
        logger.info(f"Tavus conversation created: {conversation_id}")
        # Store the tavus integration and data in the webrtc_connection object
        webrtc_connection.tavus_integration = tavus
        webrtc_connection.tavus_conversation_id = conversation_id
        webrtc_connection.tavus_conversation_data = conversation_data
        tavus.conversation_data = conversation_data
        
        # Store in global variables for server access
        # We'll need to import these from server.py
        try:
            # Import the global variables from server
            import server
            server.tavus_integrations[webrtc_connection.pc_id] = tavus
            server.latest_tavus_conversation = conversation_data
            logger.info(f"✅ Stored Tavus data globally for pc_id: {webrtc_connection.pc_id}")
        except Exception as e:
            logger.warning(f"Could not store Tavus data globally: {e}")
    else:
        logger.warning("Failed to create Tavus conversation, continuing without tracking")

    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=True,  # Enable video for potential future use
            vad_analyzer=SileroVADAnalyzer(),
            audio_out_10ms_chunks=2,
        ),
    )

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
        transcribe_user_audio=True,
        transcribe_model_audio=True,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    context = OpenAILLMContext(
        [
            {
                "role": "system",
                "content": "You are now connected as a Tavus AI Avatar. Introduce yourself as a sophisticated digital persona."
            },
            {
                "role": "user",
                "content": "Start by greeting the user warmly and introducing yourself as their Tavus AI Avatar.",
            }
        ],
    )
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            pipecat_transport.input(),
            context_aggregator.user(),
            llm,  # LLM generates responses
            pipecat_transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Pipecat Client connected - Tavus Avatar Ready")
        
        # Get conversation status if available
        if conversation_id:
            status = await tavus.get_conversation_status()
            logger.info(f"Tavus conversation status: {status.get('status', 'unknown')}")
        
        # Kick off the conversation
        await task.queue_frames([
            TextFrame("Connected to Tavus AI Avatar"),
            LLMRunFrame()
        ])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected from Tavus Avatar")
        # End Tavus conversation if it was created
        if conversation_id:
            await tavus.end_conversation()
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        if conversation_id:
            await tavus.end_conversation()
        raise
