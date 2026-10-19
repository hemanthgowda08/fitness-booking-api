from datetime import timedelta

from time_utils import now_ist
from .conftest import signup_and_token


def create_class(client, headers, name="Cancellation Yoga", slots=3):
    response = client.post("/classes", json={
        "name": name,
        "instructor": "Maya",
        "date_time": (now_ist() + timedelta(hours=2)).isoformat(),
        "total_slots": slots,
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_member_cannot_cancel_and_host_can_cancel_own_class(client):
    host = signup_and_token(client, "host@example.com", role="host")
    class_id = create_class(client, host)
    member = signup_and_token(client, "member@example.com")
    assert client.patch(f"/classes/{class_id}/cancel", headers=member).status_code == 403
    cancelled = client.patch(f"/classes/{class_id}/cancel", headers=host)
    assert cancelled.status_code == 200
    assert cancelled.json()["is_cancelled"] is True
    assert cancelled.json()["cancelled_at"].endswith("+05:30")
    assert client.patch(f"/classes/{class_id}/cancel", headers=host).status_code == 409
    assert client.get("/classes").json() == []


def test_host_cannot_cancel_another_hosts_class_but_admin_can(client):
    owner = signup_and_token(client, "owner@example.com", role="host")
    class_id = create_class(client, owner)
    another_host = signup_and_token(client, "other-host@example.com", role="host")
    assert client.patch(f"/classes/{class_id}/cancel", headers=another_host).status_code == 403
    admin = signup_and_token(client, "admin@example.com", role="admin")
    assert client.patch(f"/classes/{class_id}/cancel", headers=admin).status_code == 200


def test_cancelled_class_cannot_be_booked_and_history_is_preserved(client):
    host = signup_and_token(client, "host@example.com", role="host")
    class_id = create_class(client, host, slots=2)
    member = signup_and_token(client, "member@example.com")
    assert client.post("/book", json={"class_id": class_id}, headers=member).status_code == 201
    assert client.patch(f"/classes/{class_id}/cancel", headers=host).status_code == 200
    another_member = signup_and_token(client, "second@example.com")
    rejected = client.post("/book", json={"class_id": class_id}, headers=another_member)
    assert rejected.status_code == 409
    assert "cancelled" in rejected.json()["detail"]
    bookings = client.get("/bookings", headers=member).json()
    assert len(bookings) == 1
    assert bookings[0]["fitness_class"]["is_cancelled"] is True


def test_cancelling_a_missing_class_returns_404(client):
    admin = signup_and_token(client, "admin@example.com", role="admin")
    assert client.patch("/classes/999/cancel", headers=admin).status_code == 404
