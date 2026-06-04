import unittest

from backend.main import app


class RouteMapTest(unittest.TestCase):
    def test_public_route_map_matches_frontend_contract(self):
        routes = {
            (method, route.path)
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
            if method in {"GET", "POST", "PUT", "DELETE"}
        }

        expected = {
            ("GET", "/"),
            ("GET", "/docs"),
            ("GET", "/openapi.json"),
            ("POST", "/api/research"),
            ("POST", "/api/explain"),
            ("POST", "/api/watchlist"),
            ("POST", "/api/trade"),
            ("POST", "/api/portfolio/analyze"),
            ("POST", "/api/portfolio/scenario"),
            ("POST", "/api/portfolio/scenarios/compare"),
            ("POST", "/api/portfolio/agent"),
            ("POST", "/api/portfolio/save"),
            ("GET", "/api/portfolio/current"),
            ("PUT", "/api/portfolio/current"),
            ("DELETE", "/api/portfolio/current"),
            ("GET", "/api/portfolio/list"),
            ("GET", "/api/investor/profile"),
            ("PUT", "/api/investor/profile"),
            ("GET", "/api/investor/memory"),
            ("POST", "/api/research/stream"),
            ("POST", "/api/explain/stream"),
            ("POST", "/api/trade/stream"),
        }

        self.assertTrue(expected.issubset(routes))
