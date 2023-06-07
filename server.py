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


@app.route('/', methods=['get'])
def index():
    return f"Flast sever Runing on {os.getenv('PORT', 8000)}"


# * Create a link token with plaid
# @param :None Get the link token to link the user account with plaid
# @return the link token to the client
@app.route('/api/linkToken', methods=['GET'])
def linkToken():
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


# * route to set the access token to the user
# @param : must have a feild of email in request body along with public_token from the client (plaid_public_token,email)
# @return : None
@app.route('/api/setAccessToken', methods=['POST'])
def setAccessToken():
    global access_token
    global item_id
    public_token = request.form['public_token']
    email = request.form['email']
    # call a funtion to check if email exits if it does then return if not make a new user with that email
    try:
        if checkIfUserExits(collection, email) is False:
            addUser(collection, email)

        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)

        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']

        # * check this access token exits to email
        if checkIfAccessTokenExits(collection, email, access_token) is False:
            addAccount(collection, email, access_token, item_id)

        return jsonify({'error': None, })

    except plaid.ApiException as e:
        pretty_print_response(e)
        return json.loads(e.body)


# * Get User accounts from the access token to see if account is already linked or Not
# @param : user email
# @return : list of [inititution_id]
@app.route('/api/accounts', methods=['POST', 'GET'])
def get_accounts():
    email = request.form['email']
    accounts = getUserAccounts(collection, email)
    print(accounts)
    if accounts is None:
        return jsonify({'error': 'User does not exist'}), 404
    obj = []
    i = 1
    try:
        for access_token in accounts:
            Request = AccountsGetRequest(
                access_token=access_token['access_token']
            )
            response = client.accounts_get(Request)
            r = response.to_dict()
            id = r['item']['institution_id']
            obj.append(id)
            i = i+1

        return jsonify(obj), 200
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response), 500

# * TODO update the code to get all the accounts from the user and return it to the client


@app.route('/api/balance', methods=['GET'])
def get_balance():
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    account = getUserAccounts(collection, email)
    balance_obj = {}
    total_balance = 0
    i = 1
    try:
        for access_token in account:
            account_key = 'account_'+str(i)
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
                balance_obj.setdefault(account_key, []).append({
                    'account_id': account_id,
                    'name': account_name,
                    'balances': balances
                })

                total_balance += account_details.balances.available

        response_data = {
            'accounts': balance_obj,
            'total_balance': total_balance
        }

        return jsonify(response_data)
    except plaid.ApiException as e:
        error_response = format_error(e)
        pretty_print_response(error_response)
        return jsonify(error_response)


# Function to get transactions
# route not in Use only for testing purpose
@app.route('/api/transactions/test', methods=['GET'])
def get_transactions():
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

# Function to get transactions from an access_token with Plaid
# testing Function Not in use


def get_transactions_from_access_token(access_token):
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


# Function to get transactions
# * get User Cursor from db if they exit pass the cursor the get new transactions, if not then add {account_1:{cursor,transcation[]},  account_2:{},account_3:{},...
# * steps first get email from request to get user if exist then get all access token from that user and then get all Cursors from db
# @param : email
# @return : list of Transactions
@app.route('/api/transactions/update', methods=['GET'])
def get_transactionsUpdate():
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'}), 404

    account = getUserAccounts(collection, email)
    # * TODO get all the transactions from all the access token and and store it in the db with the cursor and return
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
                print(result['transactions'])
            i = i+1

        return jsonify({'transactions': obj})

    except Exception as e:
        return jsonify({'error': e})

# * Function to get transactions from an access_token with Plaid
# * uses transactions_sync endpoint to get all transactions from an access token and returns the transactions and the cursor
# @param : access_token,cursor
# @return : list of Transactions and cursor


def getTransactionsSync(access_token, cursorparam):
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

        # mongoDB does not support datetime so we need to convert it to string
        for transaction in added:
            transaction['date'] = str(transaction['date'])
            transaction['authorized_date'] = str(
                transaction['authorized_date'])

        return ({'transactions': added, 'cursor': cursor})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return error_response

# * funtion to get all transactions from db
# @param : email
# @return : list of Transactions


@app.route('/api/transactions', methods=['GET'])
def get_transactions_from_db():
    email = request.form['email']
    if checkIfUserExits(collection, email) is False:
        return jsonify({'error': 'User does not exist'})
    try:
        result = getAllTransactions(collection, email, )
        modified_result = []
        max_catorgey ={}
        
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
        return jsonify({'error': e})


# * Function to format json response
# @param : response in json format
# @return : pretty print json response
def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True, default=str))

# * Function to format error response
# @param : error response in json format
# @return : error response in json format


def format_error(e):
    response = json.loads(e.body)
    return {'error': {'status_code': e.status, 'display_message':
                      response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}


# main function
if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))
