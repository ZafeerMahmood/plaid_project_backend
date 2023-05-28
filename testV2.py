from components import addTransactionsv1, getCursor
from pymongo import MongoClient

client = MongoClient("")
db = client["Plaid"]  
collection = db["test"]  


def test_addTransactions():
    email = "example@example1.com"
    transactions = [
        {
            "transaction_id": "1",
            "amount": 100
        },
        {
            "transaction_id": "2",
            "amount": 200
        },
        {
            "transaction_id": "4",
            "amount": 3020
        }
    ]
    cursor = "12345"
    account_id = "account2"

    result = addTransactionsv1(collection, email, transactions, cursor, account_id)

    if result:
        print("Transactions added successfully!")
    else:
        print("Failed to add transactions.")

test_addTransactions()
