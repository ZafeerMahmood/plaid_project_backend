import json
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.products import Products
import os 
from flask import Flask , jsonify
from dotenv import load_dotenv
import time
from plaid.model.country_code import CountryCode
from flask_cors import CORS
from flask import request
from components import infoT 

load_dotenv()

app =Flask(__name__)
CORS(app)

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET_ID')

#plaid.Environment.Sandbox
host = plaid.Environment.Sandbox 

PLAID_REDIRECT_URI = 'http://localhost:3000/'

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

access_token = None
payment_id = None
transfer_id = None
item_id = None




@app.route('/', methods=['get'])
def index():
    return f"Flast sever Runing on {os.getenv('PORT', 8000)}"

@app.route('/api/linkToken', methods=['GET'])
def linkToken():
    try:
        request = LinkTokenCreateRequest(
        products=[Products('auth'), Products('transactions'),Products('identity'),Products('balance')],
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
    

#TODO include Database integration in monogb to store access token on the specific user
@app.route('/api/setAccessToken', methods=['POST'])
def setAccessToken():
    global access_token
    global item_id
    public_token = request.form['public_token']
    email=request.form['email']
    #Todo call a funtion to check if email exits if it does then return if not make a new user with that email
    try:
        #append the accesstoken to the user {account[{}]}
        
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)

        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']

        #TODO check this access token exits to email 

        #TODO set the access token & item id to the user in the database


    except plaid.ApiException as e:
        pretty_print_response(e)
        return json.loads(e.body)
    



@app.route('/api/identity', methods=['GET'])
def get_identity():
    try:
        request = IdentityGetRequest(
            access_token=access_token
        )
        response = client.identity_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(
            {'error': None, 'identity': response.to_dict()['accounts']})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)





@app.route('/api/balance', methods=['GET'])
def get_balance():
    try:
        request = AccountsBalanceGetRequest(
            access_token=access_token
        )
        response = client.accounts_balance_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)
    

#Function to get transactions 
# TODO: append all tractions from different access token from one user to one list 
#steps first get access the request to get user if exist then get all access token from that user and then get all transactions from all access token
@app.route('/api/transactions', methods=['GET'])
def get_transactions():

    cursor = ''
    added = []
    # modified = []
    # removed = []
    has_more = True
    try:
        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
            )
            response = client.transactions_sync(request).to_dict()
            # Add this page of results
            #added.extend(response['added'])
            # modified.extend(response['modified'])
            # removed.extend(response['removed'])
            # has_more = response['has_more']
            # cursor = response['next_cursor']
            # pretty_print_response(response)

        latest_transactions = sorted(response, key=lambda t: t['date'])
        return jsonify({
            'transactions': latest_transactions})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

    
#Function to format json response
def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True, default=str))

#Function to format error response
def format_error(e):
    response = json.loads(e.body)
    return {'error': {'status_code': e.status, 'display_message':
                      response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}
    
#main function
if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))