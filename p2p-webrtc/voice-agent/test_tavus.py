#!/usr/bin/env python3
"""
Test script for Tavus integration with SmallWebRTC
"""
import asyncio
import os
from dotenv import load_dotenv
from bot import TavusIntegration

load_dotenv()

async def test_tavus():
    """Test Tavus API connection and conversation creation"""
    api_key = os.getenv("TAVUS_API_KEY")
    replica_id = os.getenv("TAVUS_REPLICA_ID")
    
    if not api_key or not replica_id:
        print("❌ Tavus API key or replica ID not found in .env file")
        return False
    
    print(f"✅ Tavus API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
    print(f"✅ Replica ID: {replica_id}")
    
    # Test Tavus integration
    tavus = TavusIntegration(api_key, replica_id)
    
    print("\n🔄 Testing Tavus conversation creation...")
    conversation_id = await tavus.create_conversation()
    
    if conversation_id:
        print(f"✅ Successfully created conversation: {conversation_id}")
        
        # Test getting conversation status
        print("\n🔄 Testing conversation status...")
        status = await tavus.get_conversation_status()
        print(f"✅ Conversation status: {status.get('status', 'unknown')}")
        if 'conversation_url' in status:
            print(f"🔗 Conversation URL: {status['conversation_url']}")
        
        # Test ending conversation
        print("\n🔄 Testing conversation cleanup...")
        await tavus.end_conversation()
        print("✅ Conversation ended successfully")
        
        return True
    else:
        print("❌ Failed to create Tavus conversation")
        print("💡 This might be due to API limits or configuration issues")
        print("🚀 The bot will still work without Tavus conversation tracking")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tavus())
    if success:
        print("\n🎉 Tavus integration test passed!")
    else:
        print("\n⚠️  Tavus conversation creation failed, but bot will still work!")
    print("🚀 Ready to run the WebRTC Neural Voice Interface!")