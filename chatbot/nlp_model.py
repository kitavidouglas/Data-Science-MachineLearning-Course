import spacy

# Load a pre-trained NLP model from spaCy
nlp = spacy.load("en_core_web_sm")

def get_nlp_response(user_input):
    """
    A function to process the user's query and generate an appropriate response.
    Args:
    - user_input (str): The query or message from the user.
    
    Returns:
    - response (str): The chatbot response based on the input message.
    """
    
    # Process the user input with spaCy
    doc = nlp(user_input)

    # Check if the query is about balance
    if "balance" in user_input.lower():
        return "check_balance"
    
    # Check if the query is about loan eligibility or borrowing a loan
    elif "loan" in user_input.lower() and "borrow" in user_input.lower():
        return "loan_eligibility"
    
    # Handle general financial-related queries
    elif "transaction" in user_input.lower():
        return "transaction_history"

    # If the query doesn't match any known pattern, return "unknown"
    else:
        return "unknown"

# Example usage
if __name__ == "__main__":
    user_input = input("Enter your query: ")
    response = get_nlp_response(user_input)
    print(f"Response: {response}")
