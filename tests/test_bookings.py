from datetime import timedelta
from .conftest import signup_and_token
from time_utils import now_ist


def create_class(client, headers, slots=2):
    payload = {"name": "Pilates", "instructor": "Sam", "date_time": (now_ist() + timedelta(hours=2)).isoformat(), "total_slots": slots}
    response = client.post("/classes", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_booking_updates_slots_and_duplicate_is_rolled_back(client):
    headers = signup_and_token(client, role="host")
    class_id = create_class(client, headers, slots=1)
    assert client.post("/book", json={"class_id": class_id}, headers=headers).status_code == 201
    assert client.post("/book", json={"class_id": class_id}, headers=headers).status_code == 409
    assert client.get("/classes").json()[0]["available_slots"] == 0


def test_booking_errors_and_full_class(client):
    headers = signup_and_token(client, role="host")
    assert client.post("/book", json={"class_id": 999}, headers=headers).status_code == 404
    class_id = create_class(client, headers, slots=1)
    other = signup_and_token(client, "other@example.com")
    assert client.post("/book", json={"class_id": class_id}, headers=headers).status_code == 201
    assert client.post("/book", json={"class_id": class_id}, headers=other).status_code == 409
    assert client.post("/book", json={"class_id": class_id}).status_code == 401


def test_users_only_see_their_own_bookings(client):
    first = signup_and_token(client, role="host")
    class_id = create_class(client, first)
    second = signup_and_token(client, "second@example.com")
    assert client.post("/book", json={"class_id": class_id}, headers=first).status_code == 201
    assert client.get("/bookings", headers=second).json() == []
    bookings = client.get("/bookings", headers=first).json()
    assert len(bookings) == 1
    assert bookings[0]["fitness_class"]["id"] == class_id
