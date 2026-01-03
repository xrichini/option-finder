#!/usr/bin/env python3
"""
Test script to call the hybrid scan API endpoint
"""

import requests
import json

def test_hybrid_scan():
    """Test the hybrid scan API endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/hybrid/scan-all"
    
    # Request payload
    payload = {
        "symbols": ["AAPL", "TSLA"],
        "max_dte": 30,
        "min_volume": 50,
        "min_oi": 25,
        "min_whale_score": 50.0
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🔍 Testing hybrid scan API...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)
    
    try:
        # Make the request
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            # Parse JSON response
            try:
                data = response.json()
                print("✅ SUCCESS - Response received:")
                print(json.dumps(data, indent=2))
                
                # Show summary
                if "opportunities" in data:
                    opportunities = data["opportunities"]
                    print("\n📊 SUMMARY:")
                    print(f"Total opportunities found: {len(opportunities)}")
                    
                    if opportunities:
                        print("Top 3 opportunities:")
                        for i, opp in enumerate(opportunities[:3]):
                            print(f"  {i+1}. {opp.get('option_symbol', 'N/A')} - Score: {opp.get('hybrid_score', 'N/A')}")
                else:
                    print("No opportunities field in response")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response.text}")
        else:
            print(f"❌ ERROR - Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR - Is the FastAPI server running on localhost:8000?")
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT ERROR - Request took too long")
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    test_hybrid_scan()