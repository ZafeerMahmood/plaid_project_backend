"""
# This file contains functions to interact with the MongoDB.

these Function have no dependencies on the Flask application object and can be imported directly from the server.components module.

components.py

"""



def checkIfUserExits(collection, email):
    """
    #Function to check if a user exists in a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        bool: True if the user exists, False if the user does not exist.
    """
    result = collection.find_one({"email": email})
    if result is None:
        return False
    else:
        return True


def addUser(collection, email):
    """
    #Function to add a user to a MongoDB collection with no accounts.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        bool: True if the user is added successfully, False if the user already exists.
    """
    if checkIfUserExits(collection, email):
        return False
    else:
        collection.insert_one({"email": email, 'name': ' '})
        return True


def addAccount(collection, email, access_token, item_id):
    """
    #Function to add an account to a user who already exists by appending to the account array.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.
        access_token (str): Access token for the account.
        item_id (str): ID of the account item.

    #Returns:
        bool: True if the account is added successfully, False if the user does not exist.
    """
    if checkIfUserExits(collection, email):
        query = {"email": email}
        newvalues = {"$push": {"account": {
            "access_token": access_token, "item_id": item_id}}}
        collection.update_one(query, newvalues, upsert=True)
        return True
    else:
        return False



def deleteUser(collection, email):
    """
    #Function to delete a user from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        bool: True if the user is deleted successfully, False if the user does not exist.
    """
    if checkIfUserExits(collection, email):
        collection.delete_one({"email": email})
        return True
    else:
        return False


def getUserAccounts(collection, email):
    """
    #Function to retrieve the accounts of a user from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        list: List of accounts if the user exists, None if the user does not exist.
    """
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result.get('account')



def getUser(collection, email):
    """
    #Function to retrieve a user from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        dict: User if the user exists, None if the user does not exist.
    """
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result


def checkIfAccessTokenExits(collection, email, access_token):
    """
    #Function to check if an access token exists for a user in a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.
        access_token (str): Access token to check.

    #Returns:
        bool: True if the access token exists, False if the access token does not exist.
    """
    result = collection.find_one({"email": email})
    try:
        for account in result['account']:
            if account['access_token'] == access_token:
                return True
    except:
        return False
    return False



def addTransactions(collection, email, transactions, cursor, account_id):
    """
    #Function to add transactions to a user's transactions array in a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.
        transactions (list): List of transactions to be added.
        cursor (str): Cursor value for the transactions.
        account_id (str): ID of the account for the transactions.

    #Returns:
        bool: True if the transactions are added successfully, False if the user does not exist.
    """
    if checkIfUserExits(collection, email):
        query = {"email": email}
        existing_transactions = collection.find_one(query, {"transactions": 1})

        if existing_transactions and "transactions" in existing_transactions:
            existing_transactions = existing_transactions["transactions"]
            for transaction in existing_transactions:
                if transaction.get("account_id") == account_id:
                    transaction["transactions"].extend(transactions)
                    transaction["cursor"] = cursor
                    break
            else:
                existing_transactions.append({
                    "account_id": account_id,
                    "transactions": transactions,
                    "cursor": cursor
                })

            update_operation = {"$set": {"transactions": existing_transactions}}
            array_filters = []
        else:
            update_operation = {
                "$push": {
                    "transactions": {
                        "account_id": account_id,
                        "transactions": transactions,
                        "cursor": cursor
                    }
                }
            }
            array_filters = []

        result = collection.update_one(query, update_operation, array_filters=array_filters, upsert=True)

        if result.modified_count > 0 or result.upserted_id:
            return True
        else:
            return False
    else:
        return False

    

def addTransactionsv1(collection, email, transactions, cursor, account_id):
    """
    #Function to add transactions to a user's transactions array in a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.
        transactions (list): List of transactions to be added.
        cursor (str): Cursor value for the transactions.
        account_id (str): ID of the account for the transactions.

    #Returns:
        bool: True if the transactions are added successfully, False if the user does not exist.
    """
    if checkIfUserExits(collection, email):
        query = {"email": email}
        existing_transactions = collection.find_one(query, {"transactions": 1})

        if existing_transactions and "transactions" in existing_transactions:
            existing_transactions = existing_transactions["transactions"]
            for transaction in existing_transactions:
                if transaction.get("account_id") == account_id:
                    existing_transaction_ids = [t.get("transaction_id") for t in transaction["transactions"]]
                    new_transactions = [t for t in transactions if t.get("transaction_id") not in existing_transaction_ids]
                    transaction["transactions"].extend(new_transactions)
                    transaction["cursor"] = cursor
                    break
            else:
                existing_transactions.append({
                    "account_id": account_id,
                    "transactions": transactions,
                    "cursor": cursor
                })

            update_operation = {"$set": {"transactions": existing_transactions}}
            array_filters = []
        else:
            update_operation = {
                "$push": {
                    "transactions": {
                        "account_id": account_id,
                        "transactions": transactions,
                        "cursor": cursor
                    }
                }
            }
            array_filters = []

        result = collection.update_one(query, update_operation, array_filters=array_filters, upsert=True)

        if result.modified_count > 0 or result.upserted_id:
            return True
        else:
            return False
    else:
        return False



def getCursor(collection, email, account_id):
    """
    #Function to retrieve the cursor of a user's account from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.
        account_id (str): ID of the account.

    #Returns:
        str: Cursor if the user exists and the account_id exists in the user transactions array, None if the user does not exist or the account_id does not exist.
    """
    query = {"email": email, "transactions.account_id": account_id}
    projection = {"_id": 0, "transactions.$": 1}
    result = collection.find_one(query, projection)

    if result is not None:
        transaction = result["transactions"][0]
        return transaction["cursor"]
    else:
        return None


def getAllTransactions(collection, email):
    """
    #Function to retrieve all the transactions of a user from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        list: List of transactions if the user exists, None if the user does not exist or transactions do not exist.
    """
    query = {"email": email}
    user = collection.find_one(query, {"transactions": 1})

    if user and "transactions" in user:
        transactions = user["transactions"]
        all_transactions = []
        for account in transactions:
            account_transactions = account.get("transactions", [])
            all_transactions.extend(account_transactions)
        return all_transactions
    else:
        return None



def getUserTransactions(collection, email):
    """
    #Function to retrieve the transactions of a user from a MongoDB collection.

    #Args:
        collection (collection): MongoDB collection object.
        email (str): User's email address.

    #Returns:
        list: List of transactions if the user exists, None if the user does not exist or transactions do not exist.
    """
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result.get('transactions')


