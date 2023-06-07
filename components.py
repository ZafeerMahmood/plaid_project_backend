
# funtion to check if a user exists
# @param: collection type of mongoDB collection, email type of string
# @return: True if the user exists, False if the user does not exist
def checkIfUserExits(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return False
    else:
        return True


# funtion to add a user with no accounts[{access_token, item_id}}]
# @param: collection type of mongoDB collection, email type of string
# @return: True if the user is added successfully, False if the user already exists
def addUser(collection, email):
    if checkIfUserExits(collection, email):
        return False
    else:
        collection.insert_one({"email": email, 'name': ' '})
        return True


# funtion to add an account to a user who already exists append to the account array
# @param: collection type of mongoDB collection, email type of string, access_token type of string, item_id type of string
# @return: True if the account is added successfully, False if the user does not exist

def addAccount(collection, email, access_token, item_id):
    if checkIfUserExits(collection, email):
        query = {"email": email}
        newvalues = {"$push": {"account": {
            "access_token": access_token, "item_id": item_id}}}
        collection.update_one(query, newvalues, upsert=True)
        return True
    else:
        return False


# funtion to delete a user
# @param: collection type of mongoDB collection, email type of string
# @return: True if the user is deleted successfully, False if the user does not exist
def deleteUser(collection, email):
    if checkIfUserExits(collection, email):
        collection.delete_one({"email": email})
        return True
    else:
        return False


# funtion to get user accounts
# @param: collection type of mongoDB collection, email type of string
# @return: list of accounts if the user exists, None if the user does not exist
def getUserAccounts(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result.get('account')



# funtion to get user
# @param: collection type of mongoDB collection, email type of string
# @return: user if the user exists, None if the user does not exist
def getUser(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result


# funtion to check of an access token exists for a user
# @param : collection type of mongoDB collection, email type of string, access_token type of string
# @return: True if the access token exists, False if the access token does not exist
def checkIfAccessTokenExits(collection, email, access_token):
    result = collection.find_one({"email": email})
    try:
        for account in result['account']:
            if account['access_token'] == access_token:
                return True
    except:
        return False
    return False



#funtion to add transactions to a user based on email 
#it addes an array of transactions to a user transactions array{account_id, transactions[], cursor}
#it checks if the user exists and if the account_id exists in the user transactions array if so it apends the new transactions to the existing transactions
#if the in transactions account_id does not exist it adds a new object to the transactions array
#also updates the cursor
# @param: collection type of mongoDB collection, email type of string, transactions type of array, cursor type of string, account_id type of string
# @return: True if the transactions are added successfully, False if the user does not exist
def addTransactions(collection, email, transactions, cursor, account_id):
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
    

#funtion to add transactions to a user based on email
#it addes an array of transactions to a user transactions array{account_id, transactions[], cursor}
#it checks if the user exists and if the account_id exists in the user transactions array if so it apends the new transactions to the existing transactions only if the transaction_id does not exist
#if the in transactions account_id does not exist it adds a new object to the transactions array
#also updates the cursor
# @param: collection type of mongoDB collection, email type of string, transactions type of array, cursor type of string, account_id type of string
# @return: True if the transactions are added successfully, False if the user does not exist
def addTransactionsv1(collection, email, transactions, cursor, account_id):
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


# function to get the cursor of a user
# @param: collection type of mongoDB collection, email type of string, account_id type of string
# @return: cursor if the user exists and the account_id exists in the user transactions array, None if the user does not exist or the account_id does not exist
def getCursor(collection, email, account_id):
    query = {"email": email, "transactions.account_id": account_id}
    projection = {"_id": 0, "transactions.$": 1}
    result = collection.find_one(query, projection)

    if result is not None:
        transaction = result["transactions"][0]
        return transaction["cursor"]
    else:
        return None
    


# function to return all the transactions of a user in a single list
# @param: collection type of mongoDB collection, email type of string
# @return: list of transactions if the user exists, None if the user does not exist and None if Transactions does not exist
def getAllTransactions(collection, email):
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


# funtion to get user transactions
# @param: collection type of mongoDB collection, email type of string
# @return: list of transactions if the user exists, None if the user does not exist and None if Transactions does not exist
def getUserTransactions(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result.get('transactions')
