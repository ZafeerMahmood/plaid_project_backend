
#funtion to check if a user exists
#@param: collection type of mongoDB collection, email type of string
#@return: True if the user exists, False if the user does not exist
def checkIfUserExits(collection, email):
    result=collection.find_one({"email": email})
    if result is None:
        return False
    else:
        return True

#funtion to add a user with no accounts[{access_token, item_id}}]
#@param: collection type of mongoDB collection, email type of string
#@return: True if the user is added successfully, False if the user already exists
def addUser(collection, email):
    if checkIfUserExits(collection, email):
        return False
    else:
        collection.insert_one({"email": email,'name':' '})
        return True
    
#funtion to add an account to a user who already exists append to the account array
#@param: collection type of mongoDB collection, email type of string, access_token type of string, item_id type of string
#@return: True if the account is added successfully, False if the user does not exist
def addAccount(collection, email, access_token, item_id):
    if checkIfUserExits(collection, email):
        query = {"email": email}
        newvalues = {"$push": {"account": {"access_token": access_token, "item_id": item_id}} }
        collection.update_one(query,newvalues,upsert=True)
        return True
    else:
        return False

#funtion to delete a user
#@param: collection type of mongoDB collection, email type of string
#@return: True if the user is deleted successfully, False if the user does not exist
def deleteUser(collection, email):  
    if checkIfUserExits(collection, email):
        collection.delete_one({"email": email})
        return True
    else:
        return False
    

#funtion to get user accounts
#@param: collection type of mongoDB collection, email type of string
#@return: list of accounts if the user exists, None if the user does not exist
def getUserAccounts(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result['account']

#funtion to get user
#@param: collection type of mongoDB collection, email type of string
#@return: user if the user exists, None if the user does not exist
def getUser(collection, email):
    result = collection.find_one({"email": email})
    if result is None:
        return None
    else:
        return result
    
#funtion to check of an access token exists for a user
#@param : collection type of mongoDB collection, email type of string, access_token type of string
#@return: True if the access token exists, False if the access token does not exist
def checkIfAccessTokenExits(collection, email, access_token):
    result = collection.find_one({"email": email})
    if result is None:
        return False
    else:
        for account in result['account']:
            if account['access_token'] == access_token:
                return True
        return False
    


