from main import cafe


def test_homepage_responds():
    with cafe.test_client() as client:
        response = client.get("/")
        assert response.status_code < 500
