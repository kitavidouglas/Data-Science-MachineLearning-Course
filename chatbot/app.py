from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS  # Import CORS for handling cross-origin requests
import json
from model import get_nlp_response  # Assuming this is your NLP function
from bson.json_util import dumps  # For converting MongoDB documents to JSON

app = Flask(__name__)

# Enable CORS for all routes to allow communication with the React frontend
CORS(app)

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27018/coinbot"  # MongoDB URI with correct port
mongo = PyMongo(app)

# Route to handle the user's query
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    message = data['message']
    user_email = data.get('email', 'unknown')  # Getting email from the request, default to 'unknown'

    # Process the message using your NLP model
    response = get_nlp_response(message)

    # Fetch user data based on the query message
    if "account balance" in message.lower():
        # Dynamically get the username or email from the request if necessary
        user_data = mongo.db.users.find_one({"email": user_email})  # Use email to identify the user
        if user_data:
            account_balance = user_data.get("account_balance", "No data available")
            response += f"\nYour current account balance is: {account_balance}"
        else:
            response += "\nUser not found."

    elif "loan eligibility" in message.lower() or "loan amount" in message.lower():
        # Check loan eligibility based on user's account balance
        user_data = mongo.db.users.find_one({"email": user_email})  # Use email to identify the user
        if user_data:
            account_balance = user_data.get("account_balance", 0)
            eligible_loans = mongo.db.loans.find({
                "eligibility_criteria.min_account_balance": {"$lte": account_balance}
            })

            loan_details = []
            for loan in eligible_loans:
                loan_details.append({
                    "loan_type": loan['loan_type'],
                    "max_amount": loan['max_amount'],
                    "interest_rate": loan['interest_rate']
                })

            if loan_details:
                response += "\nYou are eligible for the following loans:\n"
                for loan in loan_details:
                    response += f"- {loan['loan_type']} (Max Amount: {loan['max_amount']}, Interest Rate: {loan['interest_rate']}%)\n"
            else:
                response += "\nYou are not eligible for any loans based on your current balance."
        else:
            response += "\nUser not found."

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
