import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "orders.db")
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_and_seeded_orders(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    orders = client.get("/api/orders").json()
    assert len(orders) == 3
    assert {order["priority"] for order in orders} == {"standard", "express"}


def test_create_and_update_order(client):
    response = client.post(
        "/api/orders",
        json={"customer": "Taylor", "item": "Mug", "priority": "standard"},
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert client.get(f"/api/orders/{order_id}").json()["status"] == "received"
    updated = client.patch(f"/api/orders/{order_id}", json={"status": "shipped"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "shipped"


def test_missing_order(client):
    assert client.get("/api/orders/missing").status_code == 404


def test_express_order_estimate_rolls_over_month_end(client):
    # Seeded express-1002 is placed on the last day of the previous month.
    response = client.get("/api/orders/express-1002")
    assert response.status_code == 200
    order = response.json()
    placed_at = main.datetime.fromisoformat(order["created_at"])
    expected = (placed_at + main.timedelta(days=2)).date().isoformat()
    assert order["estimated_delivery"] == expected


@pytest.mark.parametrize(
    "created_at, expected",
    [
        ("2026-09-30T12:00:00+00:00", "2026-10-02"),
        ("2026-02-27T12:00:00+00:00", "2026-03-01"),
        ("2026-12-31T12:00:00+00:00", "2027-01-02"),
    ],
)
def test_order_detail_express_estimate_across_boundaries(created_at, expected):
    row = {"id": "express-x", "priority": "express", "status": "received", "created_at": created_at}
    assert main.order_detail(row)["estimated_delivery"] == expected
