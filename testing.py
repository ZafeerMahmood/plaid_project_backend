import unittest
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from components import checkIfUserExits, addUser, addAccount, getUserAccounts

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')

mongo_client = MongoClient(MONGODB_URI)

db = mongo_client['Plaid']

collection = db['users']

class TestApp(unittest.TestCase):
    def setUp(self):
        self.email = "user@example.com"
        self.access_token = "access_token"
        self.item_id = "item_id"

    def test_checkIfUserExits(self):
        # Test to check if the function returns True if user exists
        result = checkIfUserExits(collection, self.email)
        self.assertFalse(result)

        # Add a user
        addUser(collection, self.email)

        # Test to check if the function returns True if user exists
        result = checkIfUserExits(collection, self.email)
        self.assertTrue(result)

        # Test to check if the function returns False if user does not exist
        result = checkIfUserExits(collection, "nonexistinguser@example.com")
        self.assertFalse(result)

    def test_addUser(self):
        # Test to check if the function returns True if the user is added successfully
        result = addUser(collection, self.email)
        self.assertTrue(result)

        # Test to check if the function returns False if the user already exists
        result = addUser(collection, self.email)
        self.assertFalse(result)

    def test_addAccount(self):
        # Test to check if the function returns False if the user does not exist
        result = addAccount(collection, "nonexistinguser@example.com", self.access_token, self.item_id)
        self.assertFalse(result)

        # Add a user
        addUser(collection, self.email)

        # Test to check if the function returns True if the account is added successfully
        result = addAccount(collection, self.email, self.access_token, self.item_id)
        self.assertTrue(result)

        # Test to check if the account is added to the user's account list
        user_accounts = getUserAccounts(collection, self.email)
        self.assertEqual(len(user_accounts), 1)
        self.assertEqual(user_accounts[0]['access_token'], self.access_token)
        self.assertEqual(user_accounts[0]['item_id'], self.item_id)

    def test_getUserAccounts(self):
        # Test to check if the function returns None if the user does not exist
        user_accounts = getUserAccounts(collection, "nonexistinguser@example.com")
        self.assertIsNone(user_accounts)

        # Add a user and an account
        addUser(collection, self.email)
        addAccount(collection, self.email, self.access_token, self.item_id)

        # Test to check if the function returns the user's accounts list
        user_accounts = getUserAccounts(collection, self.email)
        self.assertEqual(len(user_accounts), 1)
        self.assertEqual(user_accounts[0]['access_token'], self.access_token)
        self.assertEqual(user_accounts[0]['item_id'], self.item_id)

if __name__ == '__main__':
    unittest.main()