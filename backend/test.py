#!/usr/bin/env python3
"""
Quick test script for MedGemma document extraction API.
"""
import requests
import sys
import json

API_URL = "http://localhost:8000"


def test_health():
    """Test if API is running."""
    print("🏥 Testing API health...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy!\n")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}\n")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?\n")
        print("Start the server with: ./start.sh\n")
        return False


def test_config():
    """Test API configuration."""
    print("⚙️  Testing API configuration...")
    try:
        response = requests.get(f"{API_URL}/api/v1/documents/test")
        if response.status_code == 200:
            config = response.json()
            print("✅ Configuration:")
            print(json.dumps(config, indent=2))
            print()
            return True
        else:
            print(f"❌ Config test failed: {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def upload_document(file_path):
    """Upload a document for extraction."""
    print(f"📤 Uploading document: {file_path}")

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{API_URL}/api/v1/documents/upload", files=files)

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Upload successful!")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ Upload failed: {response.status_code}")
            print(response.text)
            return False
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("🧪 MEDRIX API TEST SUITE")
    print("=" * 60 + "\n")

    # Test health
    if not test_health():
        sys.exit(1)

    # Test config
    if not test_config():
        sys.exit(1)

    # Test upload if file provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        upload_document(file_path)
    else:
        print("💡 To test document upload, run:")
        print(f"   python {sys.argv[0]} /path/to/your/medical-document.pdf")
        print()


if __name__ == "__main__":
    main()
