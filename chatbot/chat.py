import random
from flask_pymongo import PyMongo
from flask import jsonify

# MongoDB connection setup
mongo = PyMongo()  # Initialize MongoDB client (this will be passed to the Flask app)

def process_query(user_input, user_id=None):
    """
    A function to process the user's query and generate an appropriate response.
    
    Args:
    - user_input (str): The query or message from the user.
    - user_id (str): The unique user identifier (e.g., email or username).
    
    Returns:
    - response (str): The chatbot response based on the input message.
    """
    # Convert input to lowercase to ensure case-insensitive comparison
    user_input = user_input.lower()

    # Handle specific queries
    if "account balance" in user_input:
        return handle_account_balance_query(user_id)
    
    elif "loan eligibility" in user_input or "loan amount" in user_input:
        return handle_loan_status_query(user_id)
    
    elif "transaction history" in user_input:
        return handle_transaction_history_query(user_id)

    else:
        return "Sorry, I didn't understand your request. Could you please clarify?"

# Function to handle account balance query
def handle_account_balance_query(user_id):
    """
    Returns a response for the account balance query.
    It fetches the account balance from the database using the user_id.
    """
    # Example: Fetch user data based on user_id (email or username)
    user_data = mongo.db.users.find_one({"username": user_id})  # Replace with dynamic user identification
    if user_data:
        account_balance = user_data.get("account_balance", "No data available")
        return f"Your account balance is {account_balance}."
    else:
        return "User not found."

# Function to handle loan status query
def handle_loan_status_query(user_id):
    """
    Returns a response for the loan status query.
    It checks loan eligibility and status based on the user's account balance.
    """
    user_data = mongo.db.users.find_one({"username": user_id})  # Replace with dynamic user identification
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
            response = "You are eligible for the following loans:\n"
            for loan in loan_details:
                response += f"- {loan['loan_type']} (Max Amount: {loan['max_amount']}, Interest Rate: {loan['interest_rate']}%)\n"
        else:
            response = "You are not eligible for any loans based on your current balance."
        return response
    else:
        return "User not found."

# Function to handle transaction history query
def handle_transaction_history_query(user_id):
    """
    Returns a response for the transaction history query.
    It fetches the user's transaction history from the database.
    """
    user_data = mongo.db.users.find_one({"username": user_id})  # Replace with dynamic user identification
    if user_data:
        # Example: Fetch recent transactions for the user
        recent_transactions = mongo.db.transactions.find({"user_id": user_id}).sort("date", -1).limit(1)
        
        if recent_transactions:
            transaction = recent_transactions[0]  # Get the latest transaction
            return f"Your last transaction was on {transaction['date']}: ${transaction['amount']} for {transaction['type']}."
        else:
            return "No transaction history found."
    else:
        return "User not found."

# Example of how the system could interact with the user
if __name__ == "__main__":
    user_input = input("Enter your query: ")
    user_id = "sample_user"  # Example user ID (can be dynamic)
    response = process_query(user_input, user_id)
    print(response)
