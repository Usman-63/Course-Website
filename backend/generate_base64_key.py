import base64
import json
import os
import sys

def generate_key():
    # Check for serviceAccountKey.json
    files = [f for f in os.listdir('.') if f.endswith('.json') and 'service' in f.lower()]
    
    if not files:
        print("No service account JSON file found in the current directory.")
        print("Please place your firebase service account json file here (e.g., serviceAccountKey.json)")
        return

    filename = files[0]
    print(f"Found file: {filename}")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            # Verify it's valid JSON
            json.loads(content)
            
            # Encode to base64
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            print("\nSUCCESS! Here is your base64 encoded string for FIREBASE_SERVICE_ACCOUNT_BASE64:\n")
            print(encoded)
            print("\nCopy the above string (without newlines) and paste it into your Render environment variables.")
            
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    generate_key()
