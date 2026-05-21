#!/usr/bin/env python3
"""
Test script for SRE Kubernetes Agent A2A Protocol
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_agent_card():
    """Test Agent Card retrieval via Well-Known URI"""
    print("🔍 Testing Agent Card (Well-Known URI)...")
    response = requests.get(f"{BASE_URL}/.well-known/agent-card.json")

    if response.status_code == 200:
        card = response.json()
        print(f"✅ Agent Card retrieved successfully")
        print(f"   Name: {card['name']}")
        print(f"   Version: {card['version']}")
        print(f"   Tools: {len(card['tools'])} available")
        print(f"   Capabilities: streaming={card['capabilities']['streaming']}, async={card['capabilities']['async']}")
        return True
    else:
        print(f"❌ Failed to retrieve Agent Card: {response.status_code}")
        return False

def test_health():
    """Test health endpoint"""
    print("\n🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        health = response.json()
        print(f"✅ Health check passed: {health['status']}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_cluster_health():
    """Test cluster health analysis"""
    print("\n🔧 Testing cluster health analysis...")

    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Analyze the cluster health"
            }
        ],
        "tools": ["analyze_cluster_health"],
        "stream": False
    }

    response = requests.post(f"{BASE_URL}/v1/agent", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Cluster health analysis completed")
        print(f"   Trace ID: {result.get('trace_id', 'N/A')}")
        if result.get('tool_calls'):
            print(f"   Tool calls: {len(result['tool_calls'])}")
        print(f"   Response preview: {result['message']['content'][:100]}...")
        return True
    else:
        print(f"❌ Cluster health analysis failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_tool_execution():
    """Test direct tool execution"""
    print("\n🛠️  Testing direct tool execution...")

    payload = {
        "include_metrics": True
    }

    response = requests.post(f"{BASE_URL}/v1/tools/analyze_cluster_health", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Tool execution successful")
        if result['status'] == 'success':
            data = result['data']
            print(f"   Nodes: {data['nodes']['ready']}/{data['nodes']['total']} ready")
            print(f"   Pods: {data['pods']['running']}/{data['pods']['total']} running")
        return True
    else:
        print(f"❌ Tool execution failed: {response.status_code}")
        return False

def test_streaming():
    """Test streaming response"""
    print("\n📡 Testing streaming response...")

    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Explain Kubernetes pod lifecycle"
            }
        ],
        "stream": True
    }

    try:
        response = requests.post(f"{BASE_URL}/v1/agent", json=payload, stream=True)

        if response.status_code == 200:
            print(f"✅ Streaming started")
            chunks = 0
            for line in response.iter_lines():
                if line:
                    chunks += 1
                    if chunks <= 3:  # Show first 3 chunks
                        print(f"   Chunk {chunks}: {line.decode()[:80]}...")
            print(f"   Total chunks received: {chunks}")
            return True
        else:
            print(f"❌ Streaming failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return False

def main():
    print("=" * 60)
    print("SRE Kubernetes Agent - A2A Protocol Test Suite")
    print("=" * 60)

    tests = [
        ("Agent Card (Well-Known URI)", test_agent_card),
        ("Health Check", test_health),
        ("Cluster Health Analysis", test_cluster_health),
        ("Direct Tool Execution", test_tool_execution),
        ("Streaming Response", test_streaming),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test '{name}' raised exception: {e}")
            results.append((name, False))
        time.sleep(1)  # Brief pause between tests

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
