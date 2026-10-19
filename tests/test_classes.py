from datetime import timedelta
from time_utils import now_ist
from .conftest import signup_and_token


def class_payload(hours=2, slots=3):
    return {"name": "Yoga", "instructor": "Maya", "date_time": (now_ist() + timedelta(hours=hours)).isoformat(), "total_slots": slots}


def test_create_class_and_initial_slots(client):
    headers = signup_and_token(client, role="host")
    response = client.post("/classes", json=class_payload(), headers=headers)
    assert response.status_code == 201
    assert response.json()["available_slots"] == response.json()["total_slots"] == 3
    assert response.json()["date_time"].endswith("+05:30")


def test_class_validation_and_authentication(client):
    assert client.post("/classes", json=class_payload()).status_code == 401
    headers = signup_and_token(client, role="host")
    assert client.post("/classes", json=class_payload(slots=0), headers=headers).status_code == 422
    assert client.post("/classes", json=class_payload(hours=-1), headers=headers).status_code == 422
    naive = class_payload(); naive["date_time"] = "2030-01-01T10:00:00"
    assert client.post("/classes", json=naive, headers=headers).status_code == 422


def test_classes_are_upcoming_and_chronological(client):
    headers = signup_and_token(client, role="host")
    client.post("/classes", json=class_payload(hours=3), headers=headers)
    client.post("/classes", json=class_payload(hours=1), headers=headers)
    classes = client.get("/classes").json()
    assert [item["name"] for item in classes] == ["Yoga", "Yoga"]
    assert classes[0]["date_time"] < classes[1]["date_time"]


def test_member_cannot_create_but_host_and_admin_can(client):
    member = signup_and_token(client, "member@example.com")
    assert client.post("/classes", json=class_payload(), headers=member).status_code == 403
    host = signup_and_token(client, "host@example.com", role="host")
    assert client.post("/classes", json=class_payload(), headers=host).status_code == 201
    admin = signup_and_token(client, "admin@example.com", role="admin")
    assert client.post("/classes", json=class_payload(), headers=admin).status_code == 201
