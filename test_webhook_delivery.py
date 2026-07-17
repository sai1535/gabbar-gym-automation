import urllib.request
import json
import subprocess
import time
import os
import csv

CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "members_template.csv")

def reset_csv():
    # Helper to reset CSV to default values for test
    content = """Member ID,Name,Phone Number,Status,Fee Amount,Due Date,Payment Status,Payment Link,Last Paid Date
GG-001,Sai Kumar,+919876543210,Active,1500,2026-07-25,Unpaid,,2026-06-25
GG-002,John Doe,+919999999999,Active,2000,2026-07-28,Unpaid,,2026-06-28
GG-003,Jane Smith,+918888888888,Inactive,1500,2026-05-10,Paid,,2026-04-10
"""
    with open(CSV_FILE_PATH, "w", newline="", encoding="utf-8") as f:
        f.write(content)

def check_member_status(member_id):
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Member ID"] == member_id:
                return row["Payment Status"], row["Due Date"]
    return None, None

def run_test():
    print("[Test] Resetting members CSV template...")
    reset_csv()
    
    # 1. Start Server Subprocess
    print("[Test] Launching local Webhook Mock Server...")
    server_path = os.path.join(os.path.dirname(__file__), "mock_webhook_server.py")
    server_process = subprocess.Popen(["python", server_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to boot
    time.sleep(1.5)
    
    try:
        # Check initial state
        initial_status, initial_due = check_member_status("GG-001")
        print(f"[Test] Member GG-001 Initial Status: {initial_status}, Due Date: {initial_due}")
        assert initial_status == "Unpaid"
        
        # 2. Prepare mock webhook payload (Razorpay Style)
        mock_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "amount": 150000,
                        "contact": "+919876543210",
                        "notes": {
                            "member_id": "GG-001"
                        }
                    }
                }
            }
        }
        
        # 3. Post to local server
        print("[Test] Sending mock Razorpay Webhook to http://localhost:8000...")
        req = urllib.request.Request(
            "http://localhost:8000",
            data=json.dumps(mock_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode("utf-8")
            print(f"[Test] Server Response: {response.status} - {resp_body}")
            assert response.status == 200
            
        # 4. Check final state
        time.sleep(0.5)
        final_status, final_due = check_member_status("GG-001")
        print(f"[Test] Member GG-001 Final Status: {final_status}, Due Date: {final_due}")
        
        assert final_status == "Paid"
        # Due Date should be extended by 30 days (from 2026-07-25 to 2026-08-24)
        assert final_due == "2026-08-24"
        print("[Test] Verification Successful! Webhook processing, CSV update, and next-date calculations work correctly.")

    except AssertionError as e:
        print(f"[-] Test failed: Assertion Error. {e}")
    except Exception as e:
        print(f"[-] Test failed with error: {e}")
    finally:
        print("[Test] Shutting down Webhook Mock Server...")
        server_process.terminate()
        server_process.wait()
        print("[Test] Done.")

if __name__ == "__main__":
    run_test()
