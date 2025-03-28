
import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free Plan",
        "price": 0,
        "bot_limit": 1,
        "trade_limit": 4,
        "duration": 30  # days
    },
    "basic": {
        "name": "Basic Plan",
        "price": 999,
        "bot_limit": 5,
        "trade_limit": -1,  # unlimited
        "duration": 30  # days
    },
    "premium": {
        "name": "Premium Plan",
        "price": 1999,
        "bot_limit": 6,
        "trade_limit": -1,  # unlimited
        "duration": 30  # days
    }
}

def create_payment_intent(plan_id: str):
    plan = SUBSCRIPTION_PLANS[plan_id]
    try:
        order_data = {
            'amount': plan["price"] * 100,  # amount in paisa
            'currency': 'INR',
            'notes': {
                'plan_id': plan_id
            }
        }
        order = client.order.create(data=order_data)
        return {
            "orderId": order['id'],
            "amount": order['amount'],
            "keyId": RAZORPAY_KEY_ID
        }
    except Exception as e:
        raise Exception(f"Failed to create order: {str(e)}")
