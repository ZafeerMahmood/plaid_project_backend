import json
import plaid
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
from flask import Flask , jsonify
from dotenv import load_dotenv
import time
from plaid.model.country_code import CountryCode
from flask_cors import CORS
from flask import request
from flask import Response as Response
from pymongo import MongoClient
from components import addUser,addAccount,getUserAccounts,checkIfUserExits,checkIfAccessTokenExits


load_dotenv()
app =Flask(__name__)
CORS(app)

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET_ID')
MONGODB_URI = os.getenv('MONGODB_URI')

#plaid.Environment.Sandbox change to plaid.Environment.Production for production and plaid.Environment.development for development
host = plaid.Environment.Sandbox 
PLAID_REDIRECT_URI = 'http://localhost:3000/'


#Your api keys are stored in the .env file
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
#mongo db connection
mongo_client = MongoClient(MONGODB_URI)
#database name is Plaid with a collection name users schema is {email:' ',name:' ',accounts:[ {access_token:' ',item_id:' '} ]}
db = mongo_client['Plaid']
collection = db['users']



#TODO will delete later after testing with data base and updating the code 
access_token = None
payment_id = None
transfer_id = None
item_id = None




@app.route('/', methods=['get'])
def index():
    return f"Flast sever Runing on {os.getenv('PORT', 8000)}"

#@param :None Get the link token to link the user account with plaid
#@return the link token to the client
@app.route('/api/linkToken', methods=['GET'])
def linkToken():
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
    

#* TODO include Database integration in monogb to store access token on the specific user
#route to set the access token to the user
#@param : must have a feild of email in request body along with public_token from the client (plaid_public_token,email)
#@return : None
@app.route('/api/setAccessToken', methods=['POST'])
def setAccessToken():
    global access_token
    global item_id
    public_token = request.form['public_token']
    email=request.form['email']
    #* Todo call a funtion to check if email exits if it does then return if not make a new user with that email
    try:
        if checkIfUserExits(collection,email) is False:
            addUser(collection,email)

        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)

        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']

        #* TODO check this access token exits to email 
        if checkIfAccessTokenExits(collection,email,access_token) is False:
            addAccount(collection,email,access_token,item_id)

        return jsonify({'error': None,})

    except plaid.ApiException as e:
        pretty_print_response(e)
        return json.loads(e.body)
   
    



#TODO update the code to get all the accounts from the user and return it to the client
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




#TODO update the code to get all the accounts from the user and return it to the client
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
#* TODO: append all tractions from different access token from one user to one list 
#* TODO steps first get access the request to get user if exist then get all access token from that user and then get all transactions from all access token
@app.route('/api/transactions', methods=['GET'])
def get_transactions():

    email = request.form['email']

    if checkIfUserExits(collection,email) is False:
        return jsonify({'error':'User does not exist'})
    
    account=getUserAccounts(collection,email)
    #* TODO get all the transactions from all the access token and append it to one list and return it to the client
    obj = dict()
    i=1
    try:
        for access_token in account:
            a='account_'+str(i)
            result=get_transactions_from_access_token(access_token['access_token'])
            obj[a]=result
            i=i+1

        return jsonify({'transactions': obj})
        
    except Exception as e:
        return  jsonify({'error':e})
    

    
@app.route('/api/accounts', methods=['POST','GET'])
def get_accounts():
    email =request.form['email']
    accounts=getUserAccounts(collection,email)
    if accounts is None:
        return jsonify({'error':'User does not exist'}),404 
    obj=[]
    i=1
    try:
        for access_token in accounts:
            Request = AccountsGetRequest(
                 access_token=access_token['access_token']
            )
            response = client.accounts_get(Request)
            r=response.to_dict()
            id=r['item']['institution_id']
            obj.append(id)
            i=i+1

        return jsonify(obj),200
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response),500


    
#Function to format json response
def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True, default=str))

#Function to format error response
def format_error(e):
    response = json.loads(e.body)
    return {'error': {'status_code': e.status, 'display_message':
                      response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}


#Function to get transactions from an access_token with Plaid
def get_transactions_from_access_token(access_token):
    cursor = ''
    has_more = True
    added=[]
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

        latest_transactions = sorted(added, key=lambda t: t['date'])[-10:]
        return latest_transactions

    except plaid.ApiException as e:
        error_response = format_error(e)
        return error_response
    


#main function
if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))