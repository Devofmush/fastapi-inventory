# app/main.py
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from bson import ObjectId
from io import BytesIO
from app.models import create_user, create_item, get_items, mark_item_as_outgoing , get_item_by_guid , reserve_item
from app.auth import authenticate_user, login_required
from barcode import Code128
from barcode.writer import ImageWriter
import base64
from datetime import datetime
import random
import string
import datetime

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")  # Session middleware for session data
templates = Jinja2Templates(directory="app/templates")

# Register route
@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    if create_user(username, password):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("register.html", {"request": {}, "error": "Username already taken"})

# Login route
@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if user:
        request.session["user"] = str(user["_id"])  # Save user ID in session
        return RedirectResponse(url="/add-item", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

# Logout route
@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/login", status_code=303)

# Protected route for adding items
@app.get("/add-item")
async def add_item_form(request: Request, user=Depends(login_required)):
    return templates.TemplateResponse("add_item.html", {"request": request})

@app.post("/add-item")
async def add_item(request: Request, name: str = Form(...), serial: str = Form(...), location: str = Form(...), user=Depends(login_required)):
    # Generate GUID in format 'yymmdd-hhmm-guid'
    guid = datetime.datetime.now().strftime("%y%m%d-%H%M") + "-" + ''.join(random.choices(string.digits, k=4))
    
    # Create the item
    create_item(name, serial, location, guid)  # Ensure this function is defined correctly in models.py
    
    # Redirect to the print label page with the generated GUID
    return RedirectResponse(url=f"/print-label/{guid}", status_code=303)

@app.get("/print-label/{guid}", response_class=HTMLResponse)
async def print_label(request: Request, guid: str):
    item = get_item_by_guid(guid)  # Assuming `get_item_by_guid` can retrieve by GUID
    if not item:
        return HTMLResponse(content="Item not found", status_code=404)

    # Generate Barcode for GUID
    barcode_image = generate_barcode(guid)

    return templates.TemplateResponse("print_label.html", {"request": request, "item": item, "barcode": barcode_image})

# Barcode generator function
def generate_barcode(guid: str) -> str:
    """Generates a barcode for the given GUID and returns the image data as a base64 string."""
    barcode = Code128(guid, writer=ImageWriter())
    buffer = BytesIO()
    barcode.write(buffer, {"module_height": 5.0, "module_width": 0.3})
    return base64.b64encode(buffer.getvalue()).decode()

# Outgoing items route with separate search functionality
@app.get("/outgoing-items")
async def outgoing_items_form(request: Request, user=Depends(login_required), search: str = ""):
    # Fetch items with status "OUT" and all items for the table
    outgoing_items = get_items({"status": "OUT"})
    all_items = get_items()  # Fetch all items in the database

    return templates.TemplateResponse("outgoing_items.html", {
        "request": request,
        "outgoing_items": outgoing_items,
        "all_items": all_items
    })


# Route to handle search in outgoing items list
@app.post("/search-outgoing-items")
async def search_outgoing_items(request: Request, outgoing_search: str = Form(...), user=Depends(login_required)):
    # Define the query to include search conditions
    query = {
        "status": "OUT",
        "$or": [
            {"name": {"$regex": outgoing_search, "$options": "i"}},
            {"serial": {"$regex": outgoing_search, "$options": "i"}},
            {"location": {"$regex": outgoing_search, "$options": "i"}}
        ]
    }
    # Fetch items based on the search query
    outgoing_items = get_items(query)
    return templates.TemplateResponse("outgoing_items.html", {"request": request, "outgoing_items": outgoing_items})

# Mark item as outgoing route
@app.post("/outgoing-items")
async def outgoing_items(request: Request, item_id: str = Form(...), user=Depends(login_required)):
    mark_item_as_outgoing(ObjectId(item_id))
    return RedirectResponse(url="/outgoing-items", status_code=303)

@app.get("/reservation")
async def reservation_form(request: Request, user=Depends(login_required)):
    # Fetch reserved items from the database
    reserved_items = get_items({"status": "RESERVED"})
    return templates.TemplateResponse("reservation.html", {"request": request, "reserved_items": reserved_items})

@app.post("/reservation")
async def reserve_item_route(request: Request, property_code: str = Form(...), location: str = Form(...), reason: str = Form(...), user=Depends(login_required)):
    # Create a reserved item
    reserve_item(property_code, location, reason)
    return RedirectResponse(url="/reservation", status_code=303)
