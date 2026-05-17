import json
import math
import unittest

import server
from delivery_optimizer.graph.graph import add_obstacle_waypoints, build_graph
from delivery_optimizer.graph.distance import build_distance_matrix


class BackendFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_astar_detours_around_obstacle(self):
        """A* phải tìm được đường đi vòng thay vì đi xuyên qua vùng cấm."""
        points = [
            {"id": 0, "x": 10, "y": 30, "name": "Kho"},
            {"id": 1, "x": 90, "y": 30, "name": "Điểm giao"},
        ]
        obstacles = [{"x_min": 40, "y_min": 20, "x_max": 60, "y_max": 40}]
        routing_points = add_obstacle_waypoints(points, obstacles)
        graph = build_graph(routing_points, obstacles=obstacles)
        matrix, paths = build_distance_matrix(
            points,
            graph,
            graph_points=routing_points,
            return_paths=True,
        )

        self.assertTrue(math.isfinite(matrix[(0, 1)][0]))
        self.assertGreater(len(paths[(0, 1)]), 2)

    def test_grid_mode_is_not_straight_line(self):
        """Chế độ lưới phải tạo đường gấp khúc theo ô, khác đường thẳng Euclid."""
        points = [
            {"id": 0, "x": 10, "y": 10, "name": "Kho"},
            {"id": 1, "x": 90, "y": 90, "name": "Điểm giao"},
        ]
        routing_points, graph = server.build_routing_graph(points, [], "grid")
        matrix, paths = build_distance_matrix(
            points,
            graph,
            graph_points=routing_points,
            return_paths=True,
        )

        straight_distance = math.hypot(80, 80)
        self.assertGreater(matrix[(0, 1)][0], straight_distance)
        self.assertGreater(len(paths[(0, 1)]), 2)

    def test_road_network_mode_follows_city_roads(self):
        """Chế độ mạng đường phải đi theo road_edges, không nối chéo điểm giao."""
        points = [
            {"id": 0, "x": 0, "y": 0, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 100, "y": 100, "name": "Điểm giao", "nodeId": 2},
        ]
        road_nodes = [
            {"id": 0, "x": 0, "y": 0},
            {"id": 1, "x": 100, "y": 0},
            {"id": 2, "x": 100, "y": 100},
        ]
        road_edges = [{"a": 0, "b": 1}, {"a": 1, "b": 2}]
        routing_points, graph = server.build_road_network_graph(points, road_nodes, road_edges, [])
        matrix, paths = build_distance_matrix(
            points,
            graph,
            graph_points=routing_points,
            return_paths=True,
        )

        self.assertAlmostEqual(matrix[(0, 1)][0], 200)
        self.assertGreater(len(paths[(0, 1)]), 3)

    def test_road_network_keeps_city_roads_when_building_blocks_exist(self):
        """Nhà nằm trong block không được làm đứt road_edges đã được UI xác định là đường."""
        points = [
            {"id": 0, "x": 0, "y": 50, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 100, "y": 50, "name": "Điểm giao", "nodeId": 1},
        ]
        road_nodes = [
            {"id": 0, "x": 0, "y": 50},
            {"id": 1, "x": 100, "y": 50},
        ]
        road_edges = [{"a": 0, "b": 1}]
        building = [{"id": "building-1", "x_min": 40, "y_min": 40, "x_max": 60, "y_max": 60, "name": "Nhà"}]
        routing_points, graph = server.build_road_network_graph(points, road_nodes, road_edges, building)

        road_node_0 = len(points)
        road_node_1 = len(points) + 1
        self.assertIn(road_node_1, graph[road_node_0])

    def test_explicit_obstacle_blocks_road_edge(self):
        """Vật cản/đường cấm do người dùng cấu hình vẫn phải đóng cạnh đường."""
        points = [
            {"id": 0, "x": 0, "y": 50, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 100, "y": 50, "name": "Điểm giao", "nodeId": 1},
        ]
        road_nodes = [
            {"id": 0, "x": 0, "y": 50},
            {"id": 1, "x": 100, "y": 50},
        ]
        road_edges = [{"a": 0, "b": 1}]
        obstacle = [{"id": 1, "x_min": 40, "y_min": 40, "x_max": 60, "y_max": 60, "name": "Đường cấm"}]
        routing_points, graph = server.build_road_network_graph(points, road_nodes, road_edges, obstacle)

        road_node_0 = len(points)
        road_node_1 = len(points) + 1
        self.assertNotIn(road_node_1, graph[road_node_0])

    def test_sync_marks_points_inside_forbidden_area_undeliverable(self):
        """Điểm giao nằm trong vùng cấm bị loại khỏi GA và báo giao thất bại."""
        points = [
            {"id": 0, "x": 0, "y": 0, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 50, "y": 50, "name": "Điểm cấm", "nodeId": 1, "undeliverable": True},
            {"id": 2, "x": 100, "y": 0, "name": "Điểm giao", "nodeId": 2},
        ]
        road_nodes = [
            {"id": 0, "x": 0, "y": 0},
            {"id": 1, "x": 50, "y": 50},
            {"id": 2, "x": 100, "y": 0},
        ]
        road_edges = [{"a": 0, "b": 2}]
        synced = self.client.post(
            "/api/sync_road_graph",
            json={"graph_mode": "road", "points": points, "road_nodes": road_nodes, "road_edges": road_edges, "obstacles": []},
        )

        self.assertEqual(synced.status_code, 200)
        self.assertEqual(synced.json["deliverable_points"], 2)
        self.assertEqual(synced.json["undeliverable_points"][0]["id"], 1)

        astar = self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "road"})
        self.assertEqual(astar.status_code, 422)
        self.assertEqual(astar.json["status"], "error")
        self.assertEqual(astar.json["undeliverable_points"][0]["id"], 1)


    def test_sync_rejects_invalid_road_edge_references(self):
        """road_edge references must point to existing road nodes."""
        points = [
            {"id": 0, "x": 0, "y": 0, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 20, "y": 0, "name": "P1", "nodeId": 1},
        ]
        road_nodes = [{"id": 0, "x": 0, "y": 0}, {"id": 1, "x": 20, "y": 0}]
        bad_edges = [{"a": 0, "b": 9}]
        synced = self.client.post(
            "/api/sync_road_graph",
            json={"graph_mode": "road", "points": points, "road_nodes": road_nodes, "road_edges": bad_edges, "obstacles": []},
        )
        self.assertEqual(synced.status_code, 422)
        self.assertEqual(synced.json["invalid_edges"][0]["b"], 9)

    def test_frontend_road_mode_has_no_visual_path_fallback(self):
        """Chế độ mạng đường không được fallback sang nối tắt frontend."""
        html = server.get_frontend_html()
        road_guard = "backendGraphMode === 'road'"
        self.assertIn(road_guard, html)
        self.assertIn("assertRunnableMap", html)
        self.assertNotIn("return{path:[src,dst_id]", html)
        self.assertIn("return{path:[],cost:Infinity,found:false}", html)

    def test_generate_astar_and_route_paths_api(self):
        """UI có thể đi từ sinh bản đồ -> A* -> lấy path chi tiết để vẽ."""
        generated = self.client.post("/api/generate", json={"n": 8, "obstacles": 2, "graph_mode": "road"})
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.json["status"], "success")
        self.assertEqual(len(generated.json["obstacles"]), 2)

        points = [
            {
                **point,
                "x": 100 + index * 25,
                "y": 100 + index * 25,
                "nodeId": index,
            }
            for index, point in enumerate(generated.json["points"])
        ]
        road_nodes = [{"id": index, "x": 100 + index * 25, "y": 100 + index * 25} for index in range(len(points))]
        road_edges = [{"a": index, "b": index + 1} for index in range(len(points) - 1)]
        synced = self.client.post(
            "/api/sync_road_graph",
            json={"graph_mode": "road", "points": points, "road_nodes": road_nodes, "road_edges": road_edges, "obstacles": []},
        )
        self.assertEqual(synced.status_code, 200)
        self.assertEqual(synced.json["status"], "success")

        astar = self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "road"})
        self.assertEqual(astar.status_code, 200)
        self.assertEqual(astar.json["status"], "success")
        self.assertEqual(astar.json["graph_mode"], "road")

        route_paths = self.client.post("/api/route_paths", json={"order": [0, 1, 2, 0]})
        self.assertEqual(route_paths.status_code, 200)
        self.assertEqual(route_paths.json["status"], "success")
        self.assertEqual(len(route_paths.json["route_paths"][0]), 3)

    def test_route_paths_rejects_unknown_point_ids(self):
        """Route có điểm không tồn tại phải bị chặn để tránh mất chặng âm thầm."""
        points = [
            {"id": 0, "x": 0, "y": 0, "name": "Kho", "nodeId": 0},
            {"id": 1, "x": 50, "y": 0, "name": "P1", "nodeId": 1},
        ]
        road_nodes = [{"id": 0, "x": 0, "y": 0}, {"id": 1, "x": 50, "y": 0}]
        road_edges = [{"a": 0, "b": 1}]
        synced = self.client.post(
            "/api/sync_road_graph",
            json={"graph_mode": "road", "points": points, "road_nodes": road_nodes, "road_edges": road_edges, "obstacles": []},
        )
        self.assertEqual(synced.status_code, 200)
        astar = self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "road"})
        self.assertEqual(astar.status_code, 200)

        route_paths = self.client.post("/api/route_paths", json={"order": [0, 99, 1, 0]})
        self.assertEqual(route_paths.status_code, 422)
        self.assertIn(99, route_paths.json["unknown_point_ids"])

    def test_astar_steps_rejects_invalid_nodes(self):
        """A* Step phải trả lỗi rõ khi start/goal không hợp lệ."""
        self.client.post("/api/generate", json={"n": 5, "obstacles": 0, "graph_mode": "straight"})

        bad_type = self.client.post("/api/astar_steps", json={"start": "x", "goal": 1, "heuristic": "euclidean"})
        self.assertEqual(bad_type.status_code, 400)

        missing_node = self.client.post("/api/astar_steps", json={"start": 9999, "goal": 10000, "heuristic": "euclidean"})
        self.assertEqual(missing_node.status_code, 422)

    def test_optimize_rejects_invalid_mut_rate(self):
        """mut_rate ngoài [0,100] phải bị chặn trước khi chạy GA."""
        self.client.post("/api/generate", json={"n": 8, "obstacles": 0, "graph_mode": "straight"})
        self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "straight"})
        response = self.client.get("/api/optimize?mut_rate=200")
        self.assertEqual(response.status_code, 400)
        self.assertIn("mut_rate", response.json["message"])

    def test_optimize_returns_multi_vehicle_routes_and_paths(self):
        """GA phải trả về tuyến xe và path A* tương ứng cho từng xe."""
        self.client.post("/api/generate", json={"n": 8, "obstacles": 1, "graph_mode": "straight"})
        self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "straight"})
        response = self.client.get(
            "/api/optimize?pop_size=20&generations=20&mut_rate=5"
            "&speed=40&vehicles=2&capacity=24&time_windows=1"
        )
        self.assertEqual(response.status_code, 200)

        done_event = None
        for line in response.get_data(as_text=True).splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if payload.get("type") == "done":
                    done_event = payload

        self.assertIsNotNone(done_event)
        self.assertEqual(len(done_event["routes"]), len(done_event["route_paths"]))
        self.assertGreaterEqual(len(done_event["routes"]), 1)


    def test_optimize_supports_euclidean_metric_mode(self):
        """GA API should support metric=euclidean for pure GA comparison."""
        self.client.post("/api/generate", json={"n": 8, "obstacles": 0, "graph_mode": "straight"})
        self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "straight"})
        response = self.client.get("/api/optimize?pop_size=20&generations=10&mut_rate=5&metric=euclidean")
        self.assertEqual(response.status_code, 200)

        done_event = None
        for line in response.get_data(as_text=True).splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if payload.get("type") == "done":
                    done_event = payload

        self.assertIsNotNone(done_event)
        self.assertEqual(done_event.get("metric"), "euclidean")
        self.assertIn("actual_dist", done_event)

    def test_optimize_rejects_unknown_metric_mode(self):
        """Unsupported optimize metric values should return 400."""
        self.client.post("/api/generate", json={"n": 5, "obstacles": 0, "graph_mode": "straight"})
        self.client.post("/api/astar", json={"heuristic": "euclidean", "speed": 40, "graph_mode": "straight"})
        response = self.client.get("/api/optimize?metric=unknown")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "error")
        self.assertIn("metric", response.json["message"])


if __name__ == "__main__":
    unittest.main()
