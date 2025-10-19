#!/usr/bin/env python3
"""
Test script to verify Tavus API format
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_tavus_api():
    """Test Tavus API with correct format"""
    api_key = os.getenv("TAVUS_API_KEY")
    replica_id = os.getenv("TAVUS_REPLICA_ID")
    persona_id = os.getenv("TAVUS_PERSONA_ID")
    
    if not api_key:
        print("❌ TAVUS_API_KEY not found in .env")
        return False
    
    print(f"✅ API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
    print(f"✅ Replica ID: {replica_id}")
    print(f"✅ Persona ID: {persona_id}")
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    # Test with replica_id first
    if replica_id:
        print(f"\n🔄 Testing with replica_id: {replica_id}")
        data = {
            "replica_id": replica_id,
            "properties": {
                "participant_left_timeout": 0,
                "language": "english"
            }
        }
        
        try:
            response = requests.post('https://tavusapi.com/v2/conversations', headers=headers, json=data)
            print(f"📊 Response Status: {response.status_code}")
            print(f"📋 Response: {response.json()}")
            
            if response.status_code in [200, 201]:
                print("✅ Replica ID works!")
                return True
            else:
                print("❌ Replica ID failed")
        except Exception as e:
            print(f"💥 Error with replica_id: {e}")
    
    # Test with persona_id if available
    if persona_id:
        print(f"\n🔄 Testing with persona_id: {persona_id}")
        data = {
            "persona_id": persona_id,
            "properties": {
                "participant_left_timeout": 0,
                "language": "english"
            }
        }
        
        try:
            response = requests.post('https://tavusapi.com/v2/conversations', headers=headers, json=data)
            print(f"📊 Response Status: {response.status_code}")
            print(f"📋 Response: {response.json()}")
            
            if response.status_code in [200, 201]:
                print("✅ Persona ID works!")
                return True
            else:
                print("❌ Persona ID failed")
        except Exception as e:
            print(f"💥 Error with persona_id: {e}")
    
    return False

if __name__ == "__main__":
    success = test_tavus_api()
    if success:
        print("\n🎉 Tavus API test passed!")
    else:
        print("\n💥 Tavus API test failed!")
        print("💡 Check your API key and replica/persona IDs")