#Todo
#data base funtions to return access token of a user
#check if a user exists
#add a user to the database
#schema for the database
# user{
#     email: string,
#     access_token:[{
#         access_token: string,
#         item_id: string
#}],}


from bson import json_util, ObjectId
import json

def testD(collection):
    result=collection.find_one({"email": "zafeer"})
    return parse_json(result)
    
    
    
    
def parse_json(data):
    return json.loads(json_util.dumps(data))





