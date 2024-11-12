# app/models.py
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import datetime
import random
import string

# Initialize MongoDB client
client = MongoClient("mongodb://localhost:27017/")
db = client["inventory_db"]["items"]
reserved_items_collection = client["inventory_db"]["reserved_items"]
users_collection = db["users"]
collection = db["items"]

# Password hashing utility
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def create_user(username, password):
    if db.users.find_one({"username": username}):
        return None  # User already exists
    hashed_password = hash_password(password)
    user = {"username": username, "password": hashed_password}
    db.users.insert_one(user)
    return user

def get_user(username):
    return db.users.find_one({"username": username})

def generate_guid():
    now = datetime.datetime.now()
    datetime_part = now.strftime("%y%m%d-%H%M")
    unique_part = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return f"{datetime_part}-{unique_part}"

def reserve_item(property_code: str, location: str, reason: str):
    """
    Reserve an item by adding a new entry with a 'RESERVED' status in the 'reserved_items' collection.
    """
    reserved_item = {
        "property_code": property_code,
        "location": location,
        "reason": reason,
        "status": "RESERVED",
        "date_reserved": datetime.datetime.now(),  # This should work now
        "reserved_out_date": None  # Initially set to None until reserved out
    }
    result = reserved_items_collection.insert_one(reserved_item)  # Insert into 'reserved_items'
    return str(result.inserted_id)  # Return the inserted item's ID as a strin

def create_item(name, serial, location, guid=None):
    if not guid:
        guid = generate_guid()
    item = {
        "name": name,
        "serial": serial,
        "location": location,
        "guid": guid,
        "date_time": datetime.datetime.now(),
        "status": "IN"
    }
    db.items.insert_one(item)
    return item

def get_item_by_guid(guid):
    return db.items.find_one({"guid": guid})

def get_items(query=None):
    if query is None:
        query = {}
    items = list(collection.find(query))  # Retrieves items based on the provided query
    print(f"Querying items with query: {query}")  # Debugging line
    print(f"Fetched items: {items}")  # Debugging line
    return items  # Ensure it returns the list of items


def mark_item_as_outgoing(item_id):
    db.items.update_one({"_id": ObjectId(item_id)}, {"$set": {"status": "OUT", "date_time": datetime.datetime.now()}})
