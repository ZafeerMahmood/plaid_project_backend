from pymongo import MongoClient
from components import addTransactions, getCursor


client = MongoClient("")
db = client["Plaid"] 
collection = db["test"]  


def test_add_transactions():
    email = "example@example.com"
    transactions = [
        {"amount": 0, "type": "a"},
        
    ]
    cursor = "00_000"
    account_id = "account1"

    result = addTransactions(collection, email, transactions, cursor, account_id)
    if result:
        print("Transactions added successfully!")
    else:
        print("Failed to add transactions.")

def test_get_cursor():
    email = "example@example.com"
    account_id = "account24"

    cursor = getCursor(collection, email, account_id)
    if cursor is not None:
        print(f"The cursor for account '{account_id}' is: {cursor}")
    else:
        print(f"No cursor found for account '{account_id}'")


test_add_transactions()
test_get_cursor()


client.close()
