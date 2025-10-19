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

You are a friendly, knowledgeable guide who helps founders create compelling applications. Your role is to:

REGISTRATION GUIDANCE:
1. Help founders articulate their startup vision clearly
2. Guide them through each section of the application
3. Ask clarifying questions to get detailed, specific answers
4. Provide suggestions to strengthen their responses
5. Ensure they highlight their unique value proposition
6. Help them present traction and metrics effectively

KEY AREAS TO COVER:
- Company mission and problem being solved
- AI specialization and technical approach
- Founder background and relevant experience
- Current traction (users, revenue, growth)
- Market size and competitive landscape
- Funding needs and use of capital
- Demo materials and pitch deck

CONVERSATION STYLE:
- Be encouraging and supportive
- Ask follow-up questions for clarity
- Suggest improvements to strengthen their application
- Help them think through potential investor questions
- Keep the tone professional but friendly
- Focus on helping them succeed

Start by asking them to describe their company and the problem they're solving. Then guide them through building a strong application step by step.
"""

YC_INTERVIEW_INSTRUCTION = f"""
You are a Y Combinator partner conducting an interview for the AI accelerator program.

You have reviewed the company's complete application and are now conducting a live interview to evaluate their potential for YC.

YOUR INTERVIEW APPROACH:
1. Start with a warm but professional greeting
2. Ask them to give you a 2-minute pitch of their company
3. Dive deep into specific areas based on their responses
4. Challenge assumptions and ask for evidence
5. Evaluate founder-market fit and execution capability
6. Assess scalability and market opportunity

KEY EVALUATION CRITERIA:
- Business Model: How do they make money? Unit economics?
- Traction: What's their growth rate? Customer acquisition?
- Market: How big is the opportunity? Who are the competitors?
- Team: Why are they the right team to solve this problem?
- Product: What's their technical advantage? How defensible?
- Funding: How much do they need? What will they use it for?

INTERVIEW STYLE:
- Be direct and ask for specific numbers
- Follow up on vague answers with "Can you be more specific?"
- Ask "What if Google/Microsoft builds this?" type questions
- Challenge their assumptions respectfully
- Look for evidence of product-market fit
- Evaluate their ability to think on their feet

TYPICAL YC QUESTIONS:
- "What's your monthly growth rate?"
- "How do you acquire customers?"
- "What's your biggest risk?"
- "How do you differentiate from competitors?"
- "What would you do with $500K?"
- "Why will you succeed when others have failed?"

Be tough but fair. Your goal is to determine if this startup has YC potential.
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
        self.conversation_type: str = "general"  # Default to general conversation
    
    def set_conversation_type(self, conversation_type: str):
        """Set the conversation type (yc_interview, registration, or general)"""
        self.conversation_type = conversation_type
        
    async def create_conversation(self) -> dict:
        """Create a new Tavus conversation and return full data"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key
            }
            
            # Create context based on conversation type
            conversational_context = ""
            conversation_name = "AI Conversation"
            custom_greeting = ""
            
            # Handle different conversation types
            if self.conversation_type == "yc_interview" and self.company_context:
                company = self.company_context
                company_name = company.get('companyName', 'your startup')
                
                # Create conversation name
                conversation_name = f"YC Interview: {company_name}"
                
                # Extract founder name from email or background
                founder_name = ""
                user_email = company.get('userEmail', '')
                founder_background = company.get('founderBackground', '')
                
                # Try to extract name from email (before @)
                if user_email:
                    email_name = user_email.split('@')[0]
                    # Capitalize and clean up the name
                    founder_name = email_name.replace('.', ' ').replace('_', ' ').title()
                
                # If we have founder background, try to extract name from it
                if founder_background and not founder_name:
                    # Look for common name patterns in founder background
                    words = founder_background.split()
                    if len(words) >= 2:
                        founder_name = f"{words[0]} {words[1]}"
                
                # Create personalized greeting with company and founder name
                if founder_name:
                    custom_greeting = f"Hello {founder_name}! Great to meet you. I'm here to discuss {company_name} for our YC AI accelerator program. I've reviewed your application and I'm impressed by what you're building. Can you start by giving me an overview of {company_name} and your business model?"
                else:
                    custom_greeting = f"Hello! Great to meet you. I'm here to discuss {company_name} for our YC AI accelerator program. I've reviewed your application and I'm impressed by what you're building. Can you start by giving me an overview of {company_name} and your business model?"
                
                # Create detailed conversational context for YC interview
                conversational_context = f"""{YC_INTERVIEW_INSTRUCTION}

COMPANY BEING INTERVIEWED:
- Company Name: {company.get('companyName', 'Unknown')}
- Description: {company.get('description', 'Not provided')}
- Mission: {company.get('mission', 'Not provided')}
- Business Stage: {company.get('stage', 'Not provided')}
- AI Specialization: {', '.join(company.get('aiSpecialization', []))}
- Funding Status: {company.get('fundingStatus', 'Not provided')}
- Current Users: {company.get('users', 'Not provided')}
- Monthly Revenue: ${company.get('revenue', 'Not provided')}
- Growth Rate: {company.get('growthRate', 'Not provided')}
- Tech Stack: {company.get('techStack', 'Not provided')}
- Founder Background: {company.get('founderBackground', 'Not provided')}
- Unique Advantage: {company.get('uniqueAdvantage', 'Not provided')}
- Main Competitors: {company.get('competitors', 'Not provided')}
- Website: {company.get('website', 'Not provided')}
- Location: {company.get('location', 'Not provided')}
- Funding Amount Needed: {company.get('fundingAmount', 'Not provided')}
- Intended Batch: {company.get('intendedBatch', 'Not provided')}

INTERVIEW FOCUS AREAS:
{', '.join(company.get('interview_context', {}).get('focus_areas', []))}

Remember: You have reviewed their full application. Now conduct a thorough interview to evaluate their YC potential."""
            
            elif self.conversation_type == "registration":
                # Registration assistance context
                conversational_context = f"""{FOUNDER_REGISTRATION_INSTRUCTION}
                
You are helping a founder complete their Y Combinator AI accelerator application. Guide them through each section and help them create a compelling application.

If they have started their application, help them improve and complete it. If they're just beginning, walk them through the process step by step.

Focus on helping them articulate their vision clearly and present their startup in the best possible light."""
                
                conversation_name = "YC Registration Assistant"
                custom_greeting = "Hello! I'm here to help you create an outstanding Y Combinator application. Let's start by telling me about your company and the problem you're solving."
            
            else:
                # Default general conversation
                conversational_context = SYSTEM_INSTRUCTION
                conversation_name = "AI Assistant"
                custom_greeting = "Hello! I'm your AI assistant. How can I help you today?"

            # Correct Tavus API payload format
            payload = {
                "properties": {
                    "participant_left_timeout": 0,
                    "language": "english"
                }
            }
            
            # Add conversational context, name, and custom greeting
            if conversational_context:
                payload["conversational_context"] = conversational_context
                payload["conversation_name"] = conversation_name
            
            if custom_greeting:
                payload["custom_greeting"] = custom_greeting
            
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
                        
                        # Log context information
                        if self.company_context:
                            company_name = self.company_context.get('companyName', 'Unknown')
                            user_email = self.company_context.get('userEmail', 'Unknown')
                            logger.info(f"🎯 YC Interview context loaded for: {company_name}")
                            logger.info(f"👤 Founder email: {user_email}")
                            logger.info(f"📋 AI will act as YC partner with full company knowledge")
                            logger.info(f"💬 Custom greeting configured for personalized introduction")
                        
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


async def run_admin_tavus_bot(webrtc_connection, company_data=None, conversation_type="yc_interview"):
    """Run Tavus bot for admin with company context"""
    
    tavus = TavusIntegration(
        api_key=os.getenv("TAVUS_API_KEY"),
        replica_id=os.getenv("TAVUS_REPLICA_ID"),
        persona_id=os.getenv("TAVUS_PERSONA_ID")
    )
    
    # Set company context and conversation type
    tavus.company_context = company_data
    tavus.set_conversation_type(conversation_type)
    
    # Create company-specific system instruction
    company_context = ""
    if company_data:
        company_context = f"""
        
        You are reviewing the following company:
        
        Company: {company_data.get('companyName', 'Unknown')}
        Description: {company_data.get('description', 'Not provided')}
        Mission: {company_data.get('mission', 'Not provided')}
        Stage: {company_data.get('stage', 'Not provided')}
        AI Specialization: {', '.join(company_data.get('aiSpecialization', []))}
        Funding Status: {company_data.get('fundingStatus', 'Not provided')}
        Users: {company_data.get('users', 'Not provided')}
        Revenue: ${company_data.get('revenue', 'Not provided')}
        Tech Stack: {company_data.get('techStack', 'Not provided')}
        Founder Background: {company_data.get('founderBackground', 'Not provided')}
        Unique Advantage: {company_data.get('uniqueAdvantage', 'Not provided')}
        Competitors: {company_data.get('competitors', 'Not provided')}
        
        Conduct a thorough review and ask probing questions about this startup.
        """
    
    # Create Tavus conversation
    conversation_data = await tavus.create_conversation()
    if conversation_data:
        conversation_id = conversation_data.get("conversation_id")
        logger.info(f"Admin Tavus conversation created: {conversation_id}")
        webrtc_connection.tavus_integration = tavus
        webrtc_connection.tavus_conversation_id = conversation_id
        webrtc_connection.tavus_conversation_data = conversation_data
        tavus.conversation_data = conversation_data
        
        try:
            import server
            server.tavus_integrations[webrtc_connection.pc_id] = tavus
            server.latest_tavus_conversation = conversation_data
            logger.info(f"✅ Stored admin Tavus data for pc_id: {webrtc_connection.pc_id}")
        except Exception as e:
            logger.warning(f"Could not store admin Tavus data: {e}")
    
    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            audio_out_10ms_chunks=2,
        ),
    )

    # Choose appropriate instruction based on conversation type
    if conversation_type == "yc_interview":
        system_instruction = YC_INTERVIEW_INSTRUCTION + company_context
    elif conversation_type == "registration":
        system_instruction = FOUNDER_REGISTRATION_INSTRUCTION + company_context
    else:
        system_instruction = SYSTEM_INSTRUCTION + company_context

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Puck",
        transcribe_user_audio=True,
        transcribe_model_audio=True,
        system_instruction=system_instruction,
    )

    context = OpenAILLMContext(
        [
            {
                "role": "system",
                "content": f"You are a Y Combinator partner reviewing {company_data.get('companyName', 'this startup')} for the AI accelerator program."
            },
            {
                "role": "user",
                "content": f"Hello! I'm here to discuss {company_data.get('companyName', 'the startup')} application.",
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
        logger.info("YC Admin Tavus bot connected")
        await task.queue_frames([
            TextFrame(f"Welcome! I'm your YC partner. Let's discuss {company_data.get('companyName', 'this startup')}."),
            LLMRunFrame()
        ])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("YC Admin Tavus bot disconnected")
        if conversation_id:
            await tavus.end_conversation()
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Error running admin Tavus bot: {e}")
        if conversation_id:
            await tavus.end_conversation()
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
