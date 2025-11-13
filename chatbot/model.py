import random
from bson import ObjectId  # If you're working with MongoDB ObjectIds

# Simple NLP simulation function
def get_nlp_response(message, user_data=None, loan_data=None):
    """
    A function to process the user's query and generate an appropriate response.
    Args:
    - message (str): The query or message from the user.
    - user_data (dict): The user's account data (optional, passed from Flask).
    - loan_data (list): The list of loan options (optional, passed from Flask).
    
    Returns:
    - response (str): The chatbot response based on the input message.
    """
    
    # Default response
    response = "I am processing your request: " + message

    # Account balance query
    if "balance" in message.lower():
        if user_data:
            account_balance = user_data.get("account_balance", "No data available")
            response = f"Your current account balance is: {account_balance}"
        else:
            response = "Sorry, I couldn't retrieve your account balance. Please try again later."

    # Loan eligibility query
    elif "loan" in message.lower():
        if user_data and loan_data:
            account_balance = user_data.get("account_balance", 0)
            eligible_loans = []

            # Check eligibility for each loan based on account balance
            for loan in loan_data:
                if loan['eligibility_criteria']['min_account_balance'] <= account_balance:
                    eligible_loans.append({
                        "loan_type": loan['loan_type'],
                        "max_amount": loan['max_amount'],
                        "interest_rate": loan['interest_rate']
                    })
            
            if eligible_loans:
                response = "You are eligible for the following loans:\n"
                for loan in eligible_loans:
                    response += f"- {loan['loan_type']} (Max Amount: {loan['max_amount']}, Interest Rate: {loan['interest_rate']}%)\n"
            else:
                response = "You are not eligible for any loans based on your current balance."

        else:
            response = "Sorry, I couldn't retrieve loan options. Please try again later."

    # Transaction history query
    elif "transaction" in message.lower():
        if user_data:
            # Simulate recent transactions (could be improved with real transaction data)
            recent_transactions = user_data.get("recent_transactions", [])
            if recent_transactions:
                response = "Your recent transactions:\n"
                for txn in recent_transactions:
                    response += f"- {txn['transaction_date']}: {txn['amount']} {txn['transaction_type']}\n"
            else:
                response = "No recent transactions found."
        else:
            response = "Sorry, I couldn't retrieve your recent transactions."

    # Handle unrecognized queries
    else:
        response = "Sorry, I couldn't understand your query. Could you please rephrase?"

    return response
