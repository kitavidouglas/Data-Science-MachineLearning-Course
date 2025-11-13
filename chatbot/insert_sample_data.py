from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27018/coinbot"  # Adjust port if necessary
mongo = PyMongo(app)

def insert_sample_data():
    # Sample user data
    user_data = {
        "username": "sample_user",
        "email": "sample_user@example.com",
        "account_balance": 1500.00,
        "recent_transactions": [
            {"transaction_date": "2025-01-01", "amount": 100.00, "transaction_type": "Deposit"},
            {"transaction_date": "2025-01-02", "amount": 50.00, "transaction_type": "Withdrawal"}
        ]
    }
    # Insert user data into the 'users' collection
    mongo.db.users.insert_one(user_data)

    # Sample loan eligibility data
    loan_data = [
        {
            "loan_type": "Personal Loan",
            "max_amount": 5000,
            "interest_rate": 5,
            "eligibility_criteria": {
                "min_account_balance": 1000
            }
        },
        {
            "loan_type": "Car Loan",
            "max_amount": 15000,
            "interest_rate": 7,
            "eligibility_criteria": {
                "min_account_balance": 5000
            }
        }
    ]
    # Insert loan data into the 'loans' collection
    mongo.db.loans.insert_many(loan_data)

    print("Sample data inserted.")

if __name__ == "__main__":
    insert_sample_data()
