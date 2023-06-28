"""
    #This module contains the Flask server that handles the Plaid API calls.

    #dependencies:
        - flask
        - plaid-python
        - pymongo
        - python-dotenv
        - flask-cors
    #environment variables:
        - PLAID_CLIENT_ID
        - PLAID_SECRET_ID
        - PLAID_ENV
        - MONGODB_URI
    
    
    #To run the server, run the following command in the terminal:
        python server.py

"""

import json
import plaid
import datetime
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.products import Products
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import time
from plaid.model.country_code import CountryCode
from flask_cors import CORS
from flask import request
from flask import Response as Response
from pymongo import MongoClient
from components import addUser, addAccount, getUserAccounts, checkIfUserExits, checkIfAccessTokenExits, getAllTransactions, getCursor, addTransactions, addTransactionsv1


load_dotenv()
app = Flask(__name__)
CORS(app)

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET_ID')
MONGODB_URI = os.getenv('MONGODB_URI')

# plaid.Environment.Sandbox change to plaid.Environment.Production for production and plaid.Environment.development for development
host = plaid.Environment.Sandbox
PLAID_REDIRECT_URI = 'http://localhost:3000/'


# Your api keys are stored in the .env file
configuration = plaid.Configuration(
    host=host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
        'plaidVersion': '2020-09-14'
    }
)


api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)
# mongo db connection
mongo_client = MongoClient(MONGODB_URI)
# database name is Plaid with a collection name users schema is {email:' ',name:' ',accounts:[ {access_token:' ',item_id:' '} ]}
db = mongo_client['Plaid']
collection = db['users']
transactionsdb = db['transactions']


@app.route('/', methods=['GET'])
def index():
    """
    #Root endpoint to check the status of the Flask server.
    
    #Returns:
        str: A message indicating the status of the Flask server.
    """
    return f"Flask server running on port {os.getenv('PORT', 8000)}"

@app.route('/api/linkToken', methods=['GET'])
def linkToken():
    """
    #Generate a link token to link a user account with Plaid.

    #Returns:
        dict: The link token as a dictionary, containing the link token value and other metadata.

    #Raises:
        plaid.ApiException: If an error occurs while generating the link token.
    """
    try:
        request = LinkTokenCreateRequest(
            products=[Products('auth'), Products('transactions')],
            client_name="Plaid Quickstart",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(time.time())
            )
        )
        response = client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        return json.loads(e.body)

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
    
    try:
        """# Check if the email exists, and if not, add a new user"""
        if checkIfUserExits(collection, email) is False:
            addUser(collection, email)

        """# Exchange the public token for an access token"""
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']

        """# Check if the access token exists for the user, and if not, add the account"""
        if checkIfAccessTokenExits(collection, email, access_token) is False:
            addAccount(collection, email, access_token, item_id)

        return jsonify({'error': None})
    except plaid.ApiException as e:
        pretty_print_response(e)
        return json.loads(e.body)

@app.route('/api/accounts', methods=['POST', 'GET'])
def get_accounts():
    """
    #Get user accounts associated with the access token.

    #Args:
        email (str): The email of the user.

    #Returns:
        dict: A dictionary containing a list of institution IDs.

    #Raises:
        plaid.ApiException: If an error occurs during the API call.
    """
    email = request.form['email']
    accounts = getUserAccounts(collection, email)

    if accounts is None:
        return jsonify({'error': 'User does not exist'}), 404

    institution_ids = []
    try:
        for access_token in accounts:
            requests = AccountsGetRequest(access_token=access_token['access_token'])
            response = client.accounts_get(requests)
            institution_id = response.item.institution_id
            institution_ids.append(institution_id)

        return jsonify(institution_ids), 200
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response), 500
    
@app.route('/api/balance', methods=['GET'])
def get_balance():
    """
    #Get the account balances for the user.

    #Args:
        email (str): The email of the user.

    #Returns:
        dict: A dictionary containing the total balance, total current balance, and
              a list of accounts from all access tokens with their balances and percentages.

    #Raises:
         plaid.ApiException: If an error occurs during the API call.
    """
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})

    account = getUserAccounts(collection, email)
    balance_obj = {}
    total_balance = 0
    total_current_balance = 0

    try:
        for access_token in account:
            requests = AccountsBalanceGetRequest(
                access_token=access_token['access_token']
            )
            response = client.accounts_balance_get(requests)

            # Extract account details and add them to balance_obj
            for account_details in response.accounts:
                account_id = account_details.account_id
                account_name = account_details.name
                balances = {
                    'available': account_details.balances.available,
                    'current': account_details.balances.current,
                    'iso_currency_code': account_details.balances.iso_currency_code,
                    'limit': account_details.balances.limit,
                    'unofficial_currency_code': account_details.balances.unofficial_currency_code
                }
                balance_obj.setdefault(account_id, []).append({
                    'name': account_name,
                    'balances': balances
                })

                total_balance += account_details.balances.available
                total_current_balance += account_details.balances.current

        response_data = {
            'total_balance': total_balance,
            'total_current_balance': total_current_balance,
            'accounts': []
        }

        # Add all accounts to the 'accounts' list
        for account_id, account_details in balance_obj.items():
            for account in account_details:
                response_data['accounts'].append(account)

        # Calculate and add percentages for each account balance
        for account in response_data['accounts']:
            available_balance = account['balances']['available']
            percentage = (available_balance / total_balance) * 100
            account['percentage'] = percentage

        return jsonify(response_data)

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response), 500

@app.route('/api/transactions/test', methods=['GET'])
def get_transactions():
    """
    #Retrieve transactions for testing purposes.

    This route is not in use and is only for testing purposes.
    It retrieves transactions for all the access tokens associated with a user and returns the transactions.

    #Args:
        None (retrieves email from request)

    #Returns:
        dict: A dictionary containing the transactions for each account.

    #Raises:
        None
    """
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    account = getUserAccounts(collection, email)
    obj = dict()
    i = 1
    try:
        for access_token in account:
            a = 'account_'+str(i)
            result = get_transactions_from_access_token(
                access_token['access_token'])
            obj[a] = result
            i = i+1
        return jsonify({'transactions': obj})
    except Exception as e:
        return jsonify({'error': e})

def get_transactions_from_access_token(access_token):
    """
    #Retrieve transactions for a specific access token.

    This function retrieves transactions for a specific access token using the transactions_sync endpoint of the Plaid API.
    It iterates through the transactions using pagination until there are no more transactions.
    It returns the latest 10 transactions sorted by date.

    #Note: This function is for testing purposes and is not currently in use.

    #Args:
        access_token (str): The access token for which transactions need to be retrieved.

    #Returns:
        list: The latest 10 transactions sorted by date.

    #Raises:
        None
    """
    cursor = ''
    has_more = True
    added = []
    try:
        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
            )
            response = client.transactions_sync(request).to_dict()
            pretty_print_response(response)
            has_more = response['has_more']
            added.extend(response['added'])
            cursor = response['next_cursor']

        latest_transactions = sorted(added, key=lambda t: t['date'])[-10:]
        return latest_transactions

    except plaid.ApiException as e:
        error_response = format_error(e)
        return error_response

@app.route('/api/transactions/update', methods=['POST'])
def get_transactionsUpdate():
    """
    #Retrieve updated transactions for the user.

    This function fetches updated transactions for the user. It first retrieves the user's email from the request.
    If the user does not exist, it returns an error response.
    If the user exists, it retrieves all access tokens associated with the user and checks if there are any stored cursors in the database.
    If cursors are not found, it retrieves all transactions for each access token and stores them in the database with their respective cursors.
    If cursors are found, it retrieves transactions starting from the stored cursors for each access token and updates the stored cursors in the database.
    The function returns a dictionary containing the updated transactions.

    #Args:
        None (retrieves email from request)

    #Returns:
        dict: Dictionary containing the updated transactions.

    #Raises:
         plaid.ApiException: If an error occurs during the API call.
    """
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'}), 404

    account = getUserAccounts(collection, email)
    obj = dict()
    i = 1
    try:
        for access_token in account:
            a = 'account_'+str(i)
            if getCursor(collection, email, a) is None:
                result = getTransactionsSync(
                    access_token['access_token'], cursorparam='')
                obj[a] = addTransactions(
                    collection, email, result['transactions'], result['cursor'], a)
            else:
                result = getTransactionsSync(
                    access_token['access_token'], cursorparam=getCursor(collection, email, a))
                obj[a] = addTransactions(
                    collection, email, result['transactions'], result['cursor'], a)
            i = i+1

        return jsonify({'transactions': obj})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response), 500

def getTransactionsSync(access_token, cursorparam):
    """
    #Retrieve transactions from Plaid using the transactions_sync endpoint.

    This function takes an access token and a cursor as input and retrieves all transactions associated with the access token.
    It uses the transactions_sync endpoint to fetch transactions in batches until there are no more transactions available.
    The function returns a dictionary containing the list of transactions and the updated cursor.

    #Args:
        access_token (str): Access token for the user's Plaid account.
        cursorparam (str): Cursor to paginate through transactions.

    #Returns:
        dict: Dictionary containing the list of transactions and the updated cursor.

    #Raises:
        plaid.ApiException: If an error occurs during the API request.
    """
    cursor = cursorparam
    has_more = True
    added = []
    try:
        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
            )
            response = client.transactions_sync(request).to_dict()
            has_more = response['has_more']
            added.extend(response['added'])
            cursor = response['next_cursor']

        for transaction in added:
            transaction['date'] = str(transaction['date'])
            transaction['authorized_date'] = str(transaction['authorized_date'])

        return {'transactions': added, 'cursor': cursor}

    except plaid.ApiException as e:
        error_response = format_error(e)
        return error_response

@app.route('/api/transactions', methods=['GET','POST'])
def get_transactions_from_db():
    """
    #Retrieve all transactions for a user from the database.

    This route accepts a GET request and expects the user's email to be provided in the request form.
    It retrieves all transactions associated with the user from the database and returns a list of transactions.

    #Args:
        None (retrieves email from request)

    #Returns:
        JSON response containing a list of transactions.

    #Raises:
        Exception: If an error occurs during the database query.
    """
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    try:
        result = getAllTransactions(collection, email)
        modified_result = []
        max_catorgey = {}

        for transaction in result:
            modified_transaction = {
                'amount': transaction['amount'],
                'name': transaction['merchant_name'],
                'date': transaction['date'],
                'category': transaction['category'],
            }
            modified_result.append(modified_transaction)

        return jsonify(modified_result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/expense', methods=['GET'])
def get_Expense():
    """
    #Retrieve a list of categories and the amount spent in each category, limited to 5.

    This route accepts a GET request and expects the user's email to be provided in the request form.
    It retrieves all transactions for the user, calculates the amount spent in each category,
    and returns a list of the top 5 categories with their corresponding amounts and percentages.

    #Args:
        None (retrieves email from request)

    #Returns:
        JSON response containing the list of categories and the amount spent in each category, limited to 5.

    #Raises:
       Exception : If an error occurs during the database query.
    """
    category_Size=5
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    try:
        result = getAllTransactions(collection, email)
        modified_result = []
        category_spending = {}
        total_spending = 0
        for transaction in result:
            if transaction['amount'] > 0:
                category = tuple(transaction['category'])
                amount = transaction['amount']
                if category in category_spending:
                    category_spending[category] += amount
                else:
                    category_spending[category] = amount
                total_spending += amount

        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:category_Size]
        top_categories_data = []

        for category, amount in top_categories:
            percentage = round((amount / total_spending) * 100, 2)
            top_categories_data.append({
                'category': category,
                'amount': amount,
                'percentage': percentage
            })

        return jsonify(top_categories_data)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/pattern', methods=['GET'])
def get_pattern():
    category_size = 4
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    try:
        result = getAllTransactions(collection, email)
        total_spending = 0
        current_month_transactions = {}
        previous_month_transactions = {}
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year
        flag = True

        # Find the last month for which the user has transactions
        last_month = current_month - 1
        for transaction in result:
            if transaction['amount'] > 0:
                category = tuple(transaction['category'])
                amount = transaction['amount']
                transaction_month = datetime.datetime.strptime(transaction['date'], '%Y-%m-%d').month
                transaction_year = datetime.datetime.strptime(transaction['date'], '%Y-%m-%d').year

                if current_month != transaction_month and flag:
                    current_month = transaction_month
                    flag = False

                if transaction_year == current_year:
                    if transaction_month == current_month:
                        if category in current_month_transactions:
                            current_month_transactions[category] += amount
                        else:
                            current_month_transactions[category] = amount
                    elif transaction_month == current_month-1:
                        if category in previous_month_transactions:
                            previous_month_transactions[category] += amount
                        else:
                            previous_month_transactions[category] = amount

                total_spending += amount

        top_categories = sorted(current_month_transactions.items(), key=lambda x: x[1], reverse=True)[:category_size]
        top_categories_data = []

        for category, amount in top_categories:
            current_month_spending = current_month_transactions.get(category, 0)
            previous_month_spending = previous_month_transactions.get(category, 0)
            percentage_change = round(((current_month_spending - previous_month_spending) / previous_month_spending) * 100, 2) if previous_month_spending != 0 else 0

            if percentage_change > 0:
                change_type = 'increase'
            elif percentage_change < 0:
                change_type = 'decrease'
            else:
                change_type = 'no change'

            top_categories_data.append({
                'category': category,
                'amount': current_month_spending,
                'percentage_change': percentage_change,
                'change_type': change_type
            })
        return jsonify(top_categories_data)
    except Exception as e:
        return jsonify({'error': str(e)})
   
@app.route('/api/Reauthenticate', methods=['POST', 'GET'])
def reauthenticate_User():
    """
    #Call any plaid service to check it access token is still valid.

    #Args:
        email (str): The email of the user.

    #Returns:
        string: A String message to indicate that the access token is valid.

    #Raises:
        plaid.ApiException: If an error occurs during the API call return an Link Token To reauthenticate User.
    """
    email = request.form['email']
    accounts = getUserAccounts(collection, email)
    access_token_reauthinticate=''

    if accounts is None:
        return jsonify({'error': 'User does not exist'}), 404

    institution_ids = []
    try:
        for access_token in accounts:
            access_token_reauthinticate=access_token['access_token']
            requests = AccountsGetRequest(access_token=access_token['access_token'])
            response = client.accounts_get(requests)
            institution_id = response.item.institution_id
            institution_ids.append(institution_id)

        return jsonify({"message":"Access Token Up to date"}), 200
    except plaid.ApiException as e:
        error_response = format_error(e)
        if error_response['error_code']=='ITEM_LOGIN_REQUIRED':
            request = LinkTokenCreateRequest(
            client_name="Plaid Quickstart",
            country_codes=[CountryCode('US')],
            language='en',
            access_token = access_token_reauthinticate,
            user=LinkTokenCreateRequestUser(
                client_user_id=str(time.time())
            ))
            response = client.link_token_create(request)
            return jsonify(response.to.dict),525
        else:
            return jsonify(error_response), 500

def pretty_print_response(response):
    """
    #Pretty print a JSON response.

    This function takes a JSON response and prints it in a pretty and readable format.

    #Args:
        response (dict): JSON response to be printed.

    #Returns:
        None

    #Raises:
        None
    """
    print(json.dumps(response, indent=2, sort_keys=True, default=str))

def format_error(e):
    """
    #Format the Plaid API error response.

    This function takes a Plaid API exception and extracts the relevant error information from the response.

    #Args:
        e (plaid.ApiException): Plaid API exception.

    #Returns:
        dict: A dictionary containing the formatted error details.

    #Raises:
        None
    """
    response = json.loads(e.body)
    return {
        'error': {
            'status_code': e.status,
            'display_message': response['error_message'],
            'error_code': response['error_code'],
            'error_type': response['error_type']
        }
    }

if __name__ == '__main__':
    """
    #The main entry point for the Flask application.

    #Starts the Flask server on the specified port.

    #Args:
        None

    #Returns:
        None

    #Raises:
        None
    """
    app.run(port=os.getenv('PORT', 8000))

