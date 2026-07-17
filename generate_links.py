import requests
import json
import os

# Razorpay Payment Link Generator
def create_razorpay_link(key_id, key_secret, amount_in_rupees, name, phone, member_id):
    """
    Creates a Razorpay Payment Link.
    Suitable for pasting inside a 'Code by Zapier' Python block.
    """
    amount_in_paise = int(float(amount_in_rupees) * 100)
    url = "https://api.razorpay.com/v1/payment_links"
    headers = {
        "Content-type": "application/json"
    }
    payload = {
        "amount": amount_in_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Gabbar Gym Membership Fee - {name} ({member_id})",
        "customer": {
            "name": name,
            "contact": phone
        },
        "notify": {
            "sms": False,  # Zapier will handle notifications via WhatsApp instead
            "email": False
        },
        "reminder_enable": False,
        "notes": {
            "member_id": member_id
        }
    }
    
    response = requests.post(
        url, 
        headers=headers, 
        auth=(key_id, key_secret), 
        data=json.dumps(payload)
    )
    
    if response.status_code in [200, 201]:
        return response.json().get("short_url")
    else:
        raise Exception(f"Razorpay API Error: {response.text}")


# Stripe Payment Link Generator
def create_stripe_link(api_key, amount, currency, name, member_id):
    """
    Creates a Stripe Payment Link.
    Ensure you install stripe: pip install stripe
    """
    try:
        import stripe
    except ImportError:
        return "Error: stripe library not installed. Run 'pip install stripe'"

    stripe.api_key = api_key
    
    try:
        # Create a single-use Product
        product = stripe.Product.create(
            name=f"Gabbar Gym Monthly Fee - {name}",
            metadata={"member_id": member_id}
        )
        
        # Create a Price for the product
        price = stripe.Price.create(
            unit_amount=int(float(amount) * 100),
            currency=currency.lower(),
            product=product.id,
        )
        
        # Create the Payment Link pointing to the price
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata={"member_id": member_id}
        )
        
        return payment_link.url
    except Exception as e:
        raise Exception(f"Stripe API Error: {str(e)}")


if __name__ == "__main__":
    # Quick local test instructions
    print("Gabbar Gym payment link generator script initialized.")
    print("You can import and use create_razorpay_link or create_stripe_link in your scripts.")
    print("These functions are formatted so you can paste them into Zapier's Code blocks.")
