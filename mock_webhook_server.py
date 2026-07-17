from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import csv
import os
from datetime import datetime, timedelta

PORT = 8000
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "members_template.csv")

class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        print(f"\n[Webhook Received] Processing event...")
        
        member_id = None
        payment_status = "Paid"
        
        # 1. Detect if it's Razorpay or Stripe
        # Razorpay typical event check
        if "event" in data and "payload" in data:
            event_type = data.get("event")
            print(f"Detected Razorpay Event: {event_type}")
            if event_type == "payment.captured":
                payment_entity = data["payload"]["payment"]["entity"]
                notes = payment_entity.get("notes", {})
                member_id = notes.get("member_id")
                amount = payment_entity.get("amount", 0) / 100
                contact = payment_entity.get("contact")
                print(f"Razorpay Payment Success: Member ID={member_id}, Contact={contact}, Amount={amount}")

        # Stripe typical event check
        elif "type" in data and "data" in data:
            event_type = data.get("type")
            print(f"Detected Stripe Event: {event_type}")
            if event_type == "payment_intent.succeeded" or event_type == "charge.succeeded":
                obj = data["data"]["object"]
                metadata = obj.get("metadata", {})
                member_id = metadata.get("member_id")
                amount = obj.get("amount", 0) / 100
                print(f"Stripe Payment Success: Member ID={member_id}, Amount={amount}")
                
        else:
            # Fallback direct webhook format (e.g. customized testing payload)
            member_id = data.get("member_id")
            print(f"Direct payload simulation: Member ID={member_id}")

        if not member_id:
            print("[-] Error: Could not extract member_id from webhook metadata.")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing member_id metadata")
            return

        # 2. Update the CSV Database
        success = update_member_payment_in_csv(member_id)
        
        if success:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Member ID not found in database")

def update_member_payment_in_csv(member_id):
    if not os.path.exists(CSV_FILE_PATH):
        print(f"[-] CSV Database not found at {CSV_FILE_PATH}")
        return False
    
    rows = []
    updated = False
    member_name = ""
    member_phone = ""
    fee_amount = ""
    new_due_date = ""

    # Read existing database
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["Member ID"] == member_id:
                updated = True
                row["Payment Status"] = "Paid"
                row["Last Paid Date"] = datetime.now().strftime("%Y-%m-%d")
                
                # Calculate next month's due date
                current_due = datetime.strptime(row["Due Date"], "%Y-%m-%d")
                next_due = current_due + timedelta(days=30)  # Simple 30 day extension
                row["Due Date"] = next_due.strftime("%Y-%m-%d")
                
                member_name = row["Name"]
                member_phone = row["Phone Number"]
                fee_amount = row["Fee Amount"]
                new_due_date = row["Due Date"]
                
            rows.append(row)

    if not updated:
        print(f"[-] Member ID '{member_id}' not found in CSV database.")
        return False

    # Write back to database
    with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] CSV Database updated successfully for {member_name} (ID: {member_id})")
    
    # 3. Simulate sending SMS confirmation
    simulate_sms_message(member_phone, member_name, fee_amount, new_due_date)
    return True

def simulate_sms_message(phone, name, amount, new_due):
    print("\n---------------- SMS Notification Simulated ----------------")
    print(f"Recipient: {phone}")
    print(f"Message:")
    print(f"  \"Thank you {name}! We received your payment of Rs.{amount}.")
    print(f"  Your Gabbar Gym membership has been renewed until {new_due}. Let's keep training!\"")
    print("------------------------------------------------------------\n")

if __name__ == "__main__":
    print(f"Starting Gabbar Gym Webhook Mock Server on port {PORT}...")
    print(f"Target CSV Database: {CSV_FILE_PATH}")
    server = HTTPServer(('localhost', PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
