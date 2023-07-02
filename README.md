# README

This is a flask based server application using plaid services.

https://plaid.com/docs/

# Environment

```env
PLAID_CLIENT_ID=
PLAID_SECRET_ID=
MONGODB_URI=mongodb+srv:
```

# Requirments 

```py
flask
plaid-python
pymongo
python-dotenv
flask-cors
```

running the server 
```sh
py server.py
```

# component.py 

includes all the function used to communicate with monogdb atlas

example funtion
```py
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
```


# server.py 

includes all the routes and funtion used in the frontent link : https://github.com/ZafeerMahmood/plaid_project_frontend 
example route 
```py
@app.route('/api/setAccessToken', methods=['POST'])
def setAccessToken():
    """
    #Set the access token for a user.

    #Args:
        email (str): The email of the user.
        public_token (str): The public token received from the Plaid client.

    #Returns:
        dict: A dictionary with an 'error' key indicating the success of the operation.

    #Raises:
        plaid.ApiException: If an error occurs during the access token exchange or account addition.
    """
    global access_token
    global item_id
    public_token = request.form['public_token']
    email = request.form['email']
```

# pdoc

can be used with pdocs to generate a static site for server.py and component.py
for ease of understanting.
```sh
pdoc ./server.py -o ./serverDocs
pdoc ./components.py -o ./componentsDocs
```


