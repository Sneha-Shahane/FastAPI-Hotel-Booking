from fastapi import FastAPI, Query, Response
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# -------------------- DATA --------------------

rooms = [
    {"id": 1, "room_number": "101", "type": "Single", "price_per_night": 1000, "floor": 1, "is_available": True},
    {"id": 2, "room_number": "102", "type": "Double", "price_per_night": 2000, "floor": 1, "is_available": True},
    {"id": 3, "room_number": "201", "type": "Suite", "price_per_night": 4000, "floor": 2, "is_available": False},
    {"id": 4, "room_number": "202", "type": "Deluxe", "price_per_night": 3500, "floor": 2, "is_available": True},
    {"id": 5, "room_number": "301", "type": "Single", "price_per_night": 1200, "floor": 3, "is_available": True},
    {"id": 6, "room_number": "302", "type": "Double", "price_per_night": 2200, "floor": 3, "is_available": False}
]

bookings = []
booking_counter = 1

# -------------------- MODELS --------------------

class BookingRequest(BaseModel):
    guest_name: str = Field(..., min_length=2)
    room_id: int = Field(..., gt=0)
    nights: int = Field(..., gt=0, le=30)
    phone: str = Field(..., min_length=10)
    meal_plan: str = "none"
    early_checkout: bool = False

class NewRoom(BaseModel):
    room_number: str
    type: str
    price_per_night: int = Field(..., gt=0)
    floor: int = Field(..., gt=0)
    is_available: bool = True

# -------------------- HELPERS --------------------

def find_room(room_id):
    for r in rooms:
        if r["id"] == room_id:
            return r
    return None

def calculate_stay_cost(price, nights, meal_plan, early_checkout):
    extra = 0
    if meal_plan == "breakfast":
        extra = 500
    elif meal_plan == "all-inclusive":
        extra = 1200

    total = (price + extra) * nights

    if early_checkout:
        discount = total * 0.1
        total -= discount
        return total, discount

    return total, 0

def filter_rooms_logic(type=None, max_price=None, floor=None, is_available=None):
    result = rooms

    if type is not None:
        result = [r for r in result if r["type"].lower() == type.lower()]

    if max_price is not None:
        result = [r for r in result if r["price_per_night"] <= max_price]

    if floor is not None:
        result = [r for r in result if r["floor"] == floor]

    if is_available is not None:
        result = [r for r in result if r["is_available"] == is_available]

    return result

# -------------------- DAY 1 --------------------

@app.get("/")
def home():
    return {"message": "Welcome to Grand Stay Hotel"}

@app.get("/rooms")
def get_rooms():
    available = sum(1 for r in rooms if r["is_available"])
    return {"total": len(rooms), "available_count": available, "rooms": rooms}

@app.get("/rooms/summary")  # FIXED ROUTE FIRST
def room_summary():
    available = sum(1 for r in rooms if r["is_available"])
    occupied = len(rooms) - available
    prices = [r["price_per_night"] for r in rooms]

    types = {}
    for r in rooms:
        types[r["type"]] = types.get(r["type"], 0) + 1

    return {
        "total": len(rooms),
        "available": available,
        "occupied": occupied,
        "cheapest": min(prices),
        "expensive": max(prices),
        "types": types
    }

@app.get("/rooms/filter")
def filter_rooms(
    type: Optional[str] = None,
    max_price: Optional[int] = None,
    floor: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = filter_rooms_logic(type, max_price, floor, is_available)
    return {"count": len(result), "rooms": result}


@app.get("/rooms/search")
def search_rooms(keyword: str):
    result = [
        r for r in rooms
        if keyword.lower() in r["type"].lower() or keyword in r["room_number"]
    ]

    if not result:
        return {"message": "No rooms found"}

    return {"total_found": len(result), "rooms": result}

@app.get("/rooms/sort")
def sort_rooms(sort_by: str = "price_per_night", order: str = "asc"):
    valid_fields = ["price_per_night", "floor", "type"]

    if sort_by not in valid_fields:
        return {"error": "Invalid sort field"}

    reverse = True if order == "desc" else False
    sorted_rooms = sorted(rooms, key=lambda x: x[sort_by], reverse=reverse)

    return {"sorted_by": sort_by, "order": order, "rooms": sorted_rooms}


@app.get("/rooms/page")
def paginate_rooms(page: int = 1, limit: int = 2):
    start = (page - 1) * limit
    total = len(rooms)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "rooms": rooms[start:start + limit]
    }

@app.get("/rooms/browse")
def browse_rooms(
    keyword: Optional[str] = None,
    sort_by: str = "price_per_night",
    order: str = "asc",
    page: int = 1,
    limit: int = 2
):
    result = rooms

    if keyword:
        result = [r for r in result if keyword.lower() in r["type"].lower()]

    reverse = True if order == "desc" else False
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    start = (page - 1) * limit

    return {
        "total": len(result),
        "page": page,
        "rooms": result[start:start + limit]
    }

@app.get("/rooms/{room_id}")  # VARIABLE ROUTE AFTER
def get_room(room_id: int):
    room = find_room(room_id)
    if not room:
        return {"error": "Room not found"}
    return room


@app.get("/bookings")
def get_bookings():
    return {"total": len(bookings), "bookings": bookings}

# -------------------- DAY 2 + 3 --------------------

@app.post("/bookings")
def create_booking(data: BookingRequest):
    global booking_counter

    room = find_room(data.room_id)

    if not room:
        return {"error": "Room not found"}

    if not room["is_available"]:
        return {"error": "Room already booked"}

    total, discount = calculate_stay_cost(
        room["price_per_night"],
        data.nights,
        data.meal_plan,
        data.early_checkout
    )

    room["is_available"] = False

    booking = {
        "booking_id": booking_counter,
        "guest_name": data.guest_name,
        "room_id": data.room_id,
        "nights": data.nights,
        "total_cost": total,
        "discount": discount,
        "status": "confirmed"
    }

    bookings.append(booking)
    booking_counter += 1

    return booking


# -------------------- DAY 4 --------------------

@app.post("/rooms")
def add_room(room: NewRoom, response: Response):
    for r in rooms:
        if r["room_number"] == room.room_number:
            return {"error": "Room already exists"}

    new_room = room.dict()
    new_room["id"] = len(rooms) + 1

    rooms.append(new_room)
    response.status_code = 201

    return new_room

@app.put("/rooms/{room_id}")
def update_room(room_id: int, price_per_night: Optional[int] = None, is_available: Optional[bool] = None):
    room = find_room(room_id)
    if not room:
        return {"error": "Room not found"}

    if price_per_night is not None:
        room["price_per_night"] = price_per_night

    if is_available is not None:
        room["is_available"] = is_available

    return room

@app.delete("/rooms/{room_id}")
def delete_room(room_id: int):
    room = find_room(room_id)
    if not room:
        return {"error": "Room not found"}

    if not room["is_available"]:
        return {"error": "Room is occupied"}

    rooms.remove(room)
    return {"message": "Room deleted successfully"}

# -------------------- DAY 5 --------------------

@app.post("/checkin/{booking_id}")
def checkin(booking_id: int):
    for b in bookings:
        if b["booking_id"] == booking_id:
            b["status"] = "checked_in"
            return b
    return {"error": "Booking not found"}

@app.post("/checkout/{booking_id}")
def checkout(booking_id: int):
    for b in bookings:
        if b["booking_id"] == booking_id:
            b["status"] = "checked_out"
            room = find_room(b["room_id"])
            if room:
                room["is_available"] = True
            return b
    return {"error": "Booking not found"}

@app.get("/bookings/active")
def active_bookings():
    return [b for b in bookings if b["status"] in ["confirmed", "checked_in"]]

# -------------------- DAY 6 --------------------

