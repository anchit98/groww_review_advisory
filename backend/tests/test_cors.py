import unittest

from fastapi.testclient import TestClient

from review_advisory_api.main import app

VERCEL_ORIGIN = "https://groww-review-advisory.vercel.app"


class CorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_get_includes_allow_origin_for_vercel(self) -> None:
        response = self.client.get(
            "/api/runs/latest",
            headers={"Origin": VERCEL_ORIGIN},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), VERCEL_ORIGIN)

    def test_preflight_options_succeeds_for_vercel(self) -> None:
        response = self.client.options(
            "/api/runs/latest",
            headers={
                "Origin": VERCEL_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), VERCEL_ORIGIN)


if __name__ == "__main__":
    unittest.main()
