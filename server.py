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

load_dotenv()

app =Flask(__name__)
CORS(app)

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET_ID')

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

@app.route('/api/create_link_token', methods=['GET'])
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
        products=[Products('auth'), Products('transactions'),Products('identity')],
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
    


@app.route('/api/set_access_token', methods=['POST'])
def get_access_token():
    global access_token
    global item_id
    public_token = request.form['public_token']
    uid=request.form['uid']
    print(uid)
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)

        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']

        return jsonify(exchange_response.to_dict())
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
    
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    # Set cursor to empty to receive all historical updates
    cursor = ''

    # New transaction updates since "cursor"
    added = []
    modified = []
    removed = [] # Removed transaction ids
    has_more = True
    try:
        # Iterate through each page of new transaction updates for item
        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
            )
            response = client.transactions_sync(request).to_dict()
            # Add this page of results
            added.extend(response['added'])
            modified.extend(response['modified'])
            removed.extend(response['removed'])
            has_more = response['has_more']
            # Update cursor to the next cursor
            cursor = response['next_cursor']
            pretty_print_response(response)

        # Return the 8 most recent transactions
        latest_transactions = sorted(added, key=lambda t: t['date'])[-8:]
        return jsonify({
            'latest_transactions': latest_transactions})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

    

def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True, default=str))

def format_error(e):
    response = json.loads(e.body)
    return {'error': {'status_code': e.status, 'display_message':
                      response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}

    

if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))