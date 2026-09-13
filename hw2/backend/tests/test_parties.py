from datetime import timedelta

from waitlist.store import store, utcnow


def add(client, **overrides):
    body = {"name": "Marsh", "party_size": 2}
    body.update(overrides)
    response = client.post("/api/parties", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_parties_empty_by_default(client):
    response = client.get("/api/parties")
    assert response.status_code == 200
    assert response.json() == []


class TestAddParty:
    def test_minimal(self, client):
        party = add(client, name="Okafor", party_size=2)
        assert party["name"] == "Okafor"
        assert party["party_size"] == 2
        assert party["phone"] is None
        assert party["quoted_minutes"] is None
        assert party["status"] == "waiting"
        assert party["ended_at"] is None
        assert party["position"] == 1
        assert party["waiting_minutes"] == 0
        assert party["is_overdue"] is False

    def test_full(self, client):
        party = add(client, name="Delgado", party_size=6, phone="555-0198", quoted_minutes=40)
        assert party["phone"] == "555-0198"
        assert party["quoted_minutes"] == 40

    def test_strips_name(self, client):
        party = add(client, name="  Whitfield  ")
        assert party["name"] == "Whitfield"

    def test_rejects_empty_name(self, client):
        response = client.post("/api/parties", json={"name": "   ", "party_size": 2})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_rejects_name_too_long(self, client):
        response = client.post("/api/parties", json={"name": "x" * 81, "party_size": 2})
        assert response.status_code == 400

    def test_rejects_party_size_below_one(self, client):
        response = client.post("/api/parties", json={"name": "Marsh", "party_size": 0})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_rejects_negative_quote(self, client):
        response = client.post("/api/parties", json={"name": "Marsh", "party_size": 2, "quoted_minutes": -1})
        assert response.status_code == 400

    def test_rejects_phone_too_long(self, client):
        response = client.post("/api/parties", json={"name": "Marsh", "party_size": 2, "phone": "5" * 33})
        assert response.status_code == 400

    def test_appends_to_bottom_of_queue(self, client):
        first = add(client, name="Marsh")
        second = add(client, name="Okafor")
        assert first["position"] == 1
        assert second["position"] == 2


class TestListParties:
    def test_orders_by_created_at_ascending(self, client):
        add(client, name="Marsh")
        add(client, name="Okafor")
        add(client, name="Delgado")
        response = client.get("/api/parties", params={"status": "waiting"})
        names = [p["name"] for p in response.json()]
        assert names == ["Marsh", "Okafor", "Delgado"]

    def test_filters_by_status(self, client):
        waiting = add(client, name="Marsh")
        seated = add(client, name="Okafor")
        client.post(f"/api/parties/{seated['id']}/seat")

        waiting_list = client.get("/api/parties", params={"status": "waiting"}).json()
        seated_list = client.get("/api/parties", params={"status": "seated"}).json()

        assert [p["id"] for p in waiting_list] == [waiting["id"]]
        assert [p["id"] for p in seated_list] == [seated["id"]]

    def test_non_waiting_parties_have_no_position(self, client):
        party = add(client, name="Marsh")
        client.post(f"/api/parties/{party['id']}/seat")
        seated_list = client.get("/api/parties", params={"status": "seated"}).json()
        assert seated_list[0]["position"] is None

    def test_positions_renumber_after_seat(self, client):
        first = add(client, name="Marsh")
        second = add(client, name="Okafor")
        third = add(client, name="Delgado")

        client.post(f"/api/parties/{first['id']}/seat")

        waiting_list = client.get("/api/parties", params={"status": "waiting"}).json()
        positions = {p["id"]: p["position"] for p in waiting_list}
        assert positions[second["id"]] == 1
        assert positions[third["id"]] == 2


class TestUpdateParty:
    def test_updates_fields(self, client):
        party = add(client, name="Marsh", party_size=2)
        response = client.patch(
            f"/api/parties/{party['id']}",
            json={"party_size": 5, "phone": "555-0100", "quoted_minutes": 20},
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["party_size"] == 5
        assert updated["phone"] == "555-0100"
        assert updated["quoted_minutes"] == 20
        assert updated["name"] == "Marsh"

    def test_does_not_change_queue_position(self, client):
        first = add(client, name="Marsh")
        second = add(client, name="Okafor")

        client.patch(f"/api/parties/{first['id']}", json={"party_size": 9})

        waiting_list = client.get("/api/parties", params={"status": "waiting"}).json()
        positions = {p["id"]: p["position"] for p in waiting_list}
        assert positions[first["id"]] == 1
        assert positions[second["id"]] == 2

    def test_partial_update_leaves_other_fields(self, client):
        party = add(client, name="Marsh", party_size=2, phone="555-0100", quoted_minutes=10)
        response = client.patch(f"/api/parties/{party['id']}", json={"quoted_minutes": 15})
        updated = response.json()
        assert updated["quoted_minutes"] == 15
        assert updated["phone"] == "555-0100"
        assert updated["party_size"] == 2

    def test_can_clear_phone_with_explicit_null(self, client):
        party = add(client, name="Marsh", phone="555-0100")
        response = client.patch(f"/api/parties/{party['id']}", json={"phone": None})
        assert response.json()["phone"] is None

    def test_allowed_on_non_waiting_party(self, client):
        party = add(client, name="Marsh")
        client.post(f"/api/parties/{party['id']}/seat")
        response = client.patch(f"/api/parties/{party['id']}", json={"name": "Marsh Jr."})
        assert response.status_code == 200
        assert response.json()["name"] == "Marsh Jr."

    def test_rejects_status_field(self, client):
        party = add(client, name="Marsh")
        response = client.patch(f"/api/parties/{party['id']}", json={"status": "seated"})
        assert response.status_code == 400

    def test_rejects_invalid_party_size(self, client):
        party = add(client, name="Marsh")
        response = client.patch(f"/api/parties/{party['id']}", json={"party_size": 0})
        assert response.status_code == 400

    def test_unknown_id_is_404(self, client):
        response = client.patch("/api/parties/does-not-exist", json={"name": "X"})
        assert response.status_code == 404


class TestTransitions:
    def test_seat_waiting_party(self, client):
        party = add(client, name="Marsh")
        response = client.post(f"/api/parties/{party['id']}/seat")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "seated"
        assert body["ended_at"] is not None
        assert body["position"] is None

    def test_seat_already_seated_is_409(self, client):
        party = add(client, name="Marsh")
        first = client.post(f"/api/parties/{party['id']}/seat")
        second = client.post(f"/api/parties/{party['id']}/seat")
        assert second.status_code == 409
        seated = client.get("/api/parties", params={"status": "seated"}).json()[0]
        assert first.json()["ended_at"] == seated["ended_at"]

    def test_no_show(self, client):
        party = add(client, name="Marsh")
        response = client.post(f"/api/parties/{party['id']}/no-show")
        assert response.status_code == 200
        assert response.json()["status"] == "no_show"

    def test_cancel(self, client):
        party = add(client, name="Marsh")
        response = client.post(f"/api/parties/{party['id']}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_no_show_and_cancel_are_distinguishable(self, client):
        a = add(client, name="Marsh")
        b = add(client, name="Okafor")
        client.post(f"/api/parties/{a['id']}/no-show")
        client.post(f"/api/parties/{b['id']}/cancel")

        no_show_list = client.get("/api/parties", params={"status": "no_show"}).json()
        cancelled_list = client.get("/api/parties", params={"status": "cancelled"}).json()

        assert [p["id"] for p in no_show_list] == [a["id"]]
        assert [p["id"] for p in cancelled_list] == [b["id"]]

    def test_seat_unknown_id_is_404(self, client):
        response = client.post("/api/parties/does-not-exist/seat")
        assert response.status_code == 404

    def test_cannot_seat_a_cancelled_party(self, client):
        party = add(client, name="Marsh")
        client.post(f"/api/parties/{party['id']}/cancel")
        response = client.post(f"/api/parties/{party['id']}/seat")
        assert response.status_code == 409


class TestRestore:
    def test_restore_terminal_party(self, client):
        party = add(client, name="Marsh")
        client.post(f"/api/parties/{party['id']}/cancel")
        response = client.post(f"/api/parties/{party['id']}/restore")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "waiting"
        assert body["ended_at"] is None

    def test_restore_returns_to_original_position_not_back_of_line(self, client):
        first = add(client, name="Marsh")
        second = add(client, name="Okafor")
        third = add(client, name="Delgado")

        client.post(f"/api/parties/{second['id']}/cancel")
        client.post(f"/api/parties/{second['id']}/restore")

        waiting_list = client.get("/api/parties", params={"status": "waiting"}).json()
        positions = {p["id"]: p["position"] for p in waiting_list}
        assert positions[first["id"]] == 1
        assert positions[second["id"]] == 2
        assert positions[third["id"]] == 3

    def test_restore_waiting_party_is_409(self, client):
        party = add(client, name="Marsh")
        response = client.post(f"/api/parties/{party['id']}/restore")
        assert response.status_code == 409

    def test_restore_unknown_id_is_404(self, client):
        response = client.post("/api/parties/does-not-exist/restore")
        assert response.status_code == 404


class TestDerivedFields:
    def test_waiting_minutes_reflects_elapsed_time(self, client):
        party = add(client, name="Marsh")
        record = store.get(party["id"])
        record.created_at = utcnow() - timedelta(minutes=31)

        response = client.get("/api/parties", params={"status": "waiting"})
        assert response.json()[0]["waiting_minutes"] == 31

    def test_is_overdue_when_elapsed_exceeds_quote(self, client):
        party = add(client, name="Marsh", quoted_minutes=25)
        record = store.get(party["id"])
        record.created_at = utcnow() - timedelta(minutes=31)

        response = client.get("/api/parties", params={"status": "waiting"})
        body = response.json()[0]
        assert body["waiting_minutes"] == 31
        assert body["is_overdue"] is True

    def test_not_overdue_without_a_quote(self, client):
        party = add(client, name="Marsh")
        record = store.get(party["id"])
        record.created_at = utcnow() - timedelta(minutes=999)

        response = client.get("/api/parties", params={"status": "waiting"})
        assert response.json()[0]["is_overdue"] is False

    def test_closed_party_waiting_minutes_uses_ended_at_not_now(self, client):
        party = add(client, name="Marsh")
        record = store.get(party["id"])
        record.created_at = utcnow() - timedelta(minutes=20)

        client.post(f"/api/parties/{party['id']}/seat")
        record.ended_at = record.created_at + timedelta(minutes=5)

        response = client.get("/api/parties", params={"status": "seated"})
        assert response.json()[0]["waiting_minutes"] == 5
