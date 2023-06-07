from pymongo import MongoClient
from components import addTransactions, getCursor ,getAllTransactions
import json


client = MongoClient("mongodb+srv://zafeer:f7lriLMmKX2ErNhw@cluster0.tuaov.mongodb.net/?retryWrites=true&w=majority")
db = client["Plaid"] 
collection = db["test"]  


# def test_add_transactions():
#     email = "example@example.com"
#     transactions = [
#         {"amount": 0, "type": "a"},
        
#     ]
#     cursor = "00_000"
#     account_id = "account1"

#     result = addTransactions(collection, email, transactions, cursor, account_id)
#     if result:
#         print("Transactions added successfully!")
#     else:
#         print("Failed to add transactions.")

# def test_get_cursor(account_id):
#     email = "example@example.com"
    
#     cursor = getCursor(collection, email, account_id)
#     if cursor is not None:
#         print(f"The cursor for account '{account_id}' is: {cursor}")
#     else:
#         print(f"No cursor found for account '{account_id}'")


#test_add_transactions()
# test_get_cursor('account1')
# test_get_cursor('account2')
# test_get_cursor('account3')
# test_get_cursor('account4')
# test_get_cursor('account5')
def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True, default=str))

pretty_print_response(getAllTransactions(collection, "example@example.com"))


client.close()
