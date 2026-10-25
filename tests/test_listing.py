"""Visibility, filtering, pagination, and ordering for GET /expenses."""


def ids(response):
    return [item["id"] for item in response.json()["items"]]


def test_employee_sees_only_their_own_expenses(api, world):
    own = api.make_expense(world.employee_token)
    api.make_expense(world.manager_token)
    api.make_expense(world.other_employee_token)

    response = api.list_expenses(world.employee_token)

    assert response.status_code == 200
    assert ids(response) == [own["id"]]
    assert response.json()["total"] == 1


def test_manager_sees_own_expenses_and_direct_reports(api, world):
    report = api.make_expense(world.employee_token)
    own = api.make_expense(world.manager_token)
    api.make_expense(world.other_employee_token)

    response = api.list_expenses(world.manager_token)

    assert set(ids(response)) == {report["id"], own["id"]}
    assert response.json()["total"] == 2


def test_admin_sees_every_expense(api, world):
    api.make_expense(world.employee_token)
    api.make_expense(world.manager_token)
    api.make_expense(world.other_employee_token)

    response = api.list_expenses(world.admin_token)

    assert response.json()["total"] == 3


def test_filter_by_status(api, world):
    api.make_expense(world.employee_token)
    submitted = api.submitted_expense(world.employee_token)

    response = api.list_expenses(world.employee_token, status="submitted")

    assert ids(response) == [submitted["id"]]
    assert response.json()["total"] == 1


def test_filter_by_category(api, world):
    api.make_expense(world.employee_token, category="travel")
    meals = api.make_expense(world.employee_token, category="meals")

    response = api.list_expenses(world.employee_token, category="meals")

    assert ids(response) == [meals["id"]]


def test_filter_by_owner(api, world):
    report_expense = api.make_expense(world.employee_token)
    api.make_expense(world.manager_token)

    response = api.list_expenses(world.manager_token, owner_id=world.employee["id"])

    assert ids(response) == [report_expense["id"]]


def test_filter_by_invisible_owner_is_empty(api, world):
    api.make_expense(world.other_manager_token)

    response = api.list_expenses(world.employee_token, owner_id=world.other_manager["id"])

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_pagination_slices_items(api, world):
    created = [api.make_expense(world.employee_token) for _ in range(5)]

    response = api.list_expenses(world.employee_token, page=2, page_size=2)

    assert ids(response) == [created[2]["id"], created[3]["id"]]
    assert response.json()["total"] == 5
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 2


def test_page_beyond_the_end_is_empty(api, world):
    for _ in range(3):
        api.make_expense(world.employee_token)

    response = api.list_expenses(world.employee_token, page=99, page_size=2)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 3


def test_default_page_size_is_twenty(api, world):
    for _ in range(21):
        api.make_expense(world.employee_token)

    response = api.list_expenses(world.employee_token)

    assert len(response.json()["items"]) == 20
    assert response.json()["total"] == 21


def test_page_zero_is_422(api, world):
    assert api.list_expenses(world.employee_token, page=0).status_code == 422


def test_page_size_zero_is_422(api, world):
    assert api.list_expenses(world.employee_token, page_size=0).status_code == 422


def test_page_size_above_hundred_is_422(api, world):
    assert api.list_expenses(world.employee_token, page_size=101).status_code == 422


def test_invalid_status_filter_is_422(api, world):
    assert api.list_expenses(world.employee_token, status="pending").status_code == 422


def test_invalid_category_filter_is_422(api, world):
    assert api.list_expenses(world.employee_token, category="entertainment").status_code == 422


def test_results_are_oldest_first(api, world):
    created = [api.make_expense(world.employee_token) for _ in range(3)]

    response = api.list_expenses(world.employee_token)

    assert ids(response) == [expense["id"] for expense in created]


def test_empty_list_shape(api, world):
    response = api.list_expenses(world.employee_token)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
    }


def test_unauthenticated_listing_is_401(client):
    assert client.get("/expenses").status_code == 401
