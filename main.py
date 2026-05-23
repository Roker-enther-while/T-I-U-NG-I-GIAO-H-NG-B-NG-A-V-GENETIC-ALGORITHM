"""Terminal demo for the A* + Genetic Algorithm delivery routing project.

Run:
    python main.py --demo
    python main.py --demo --verbose
    python main.py --explain
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT_DIR = Path(__file__).resolve().parent
DELIVERY_DIR = ROOT_DIR / "delivery_optimizer"
if str(DELIVERY_DIR) not in sys.path:
    sys.path.insert(0, str(DELIVERY_DIR))

from algorithms.astar import astar_with_steps  # noqa: E402
from algorithms.genetic import run_ga  # noqa: E402
from graph.distance import build_distance_matrix, heuristic  # noqa: E402
from graph.graph import add_obstacle_waypoints, build_graph, edge_is_allowed  # noqa: E402


CONFIG_FILE = ROOT_DIR / "configs" / "default.json"
OUTPUT_DIR = ROOT_DIR / "outputs" / "demo_terminal"


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


class TerminalLog:
    def __init__(self) -> None:
        self.lines: List[str] = []

    def write(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def build_demo_case() -> Tuple[List[dict], List[dict], List[dict], dict, List[dict]]:
    """Create a small deterministic map with obstacles and detour waypoints."""
    points = [
        {"id": 0, "x": 8, "y": 8, "name": "Kho trung tâm", "demand": 0},
        {"id": 1, "x": 18, "y": 82, "name": "P1 - Cổng Bắc", "demand": 2},
        {"id": 2, "x": 34, "y": 18, "name": "P2 - Chung cư A", "demand": 3},
        {"id": 3, "x": 54, "y": 82, "name": "P3 - Siêu thị", "demand": 2},
        {"id": 4, "x": 72, "y": 18, "name": "P4 - Trạm y tế", "demand": 4},
        {"id": 5, "x": 88, "y": 72, "name": "P5 - Trường học", "demand": 3},
        {"id": 6, "x": 42, "y": 58, "name": "P6 - Khu dân cư", "demand": 2},
        {"id": 7, "x": 78, "y": 48, "name": "P7 - Văn phòng", "demand": 2},
        {"id": 8, "x": 24, "y": 46, "name": "P8 - Nhà thuốc", "demand": 1},
    ]
    obstacles = [
        {"id": 1, "x_min": 30, "y_min": 30, "x_max": 48, "y_max": 48, "name": "Khu cấm 1"},
        {"id": 2, "x_min": 60, "y_min": 52, "x_max": 74, "y_max": 68, "name": "Khu cấm 2"},
    ]
    routing_points = add_obstacle_waypoints(points, obstacles, padding=5)
    graph = build_graph(routing_points, mode="full", obstacles=obstacles)
    return points, obstacles, routing_points, graph, routing_points[len(points):]


def build_euclidean_matrix(points: List[dict], speed_kmh: float) -> Dict[Tuple[int, int], Tuple[float, float]]:
    matrix: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for i, source in enumerate(points):
        for j, target in enumerate(points):
            dist = 0.0 if i == j else math.hypot(source["x"] - target["x"], source["y"] - target["y"])
            time_min = 0.0 if speed_kmh <= 0 else (dist / speed_kmh) * 60.0
            matrix[(i, j)] = (dist, time_min)
    return matrix


def route_distance(order: Iterable[int], matrix: Dict[Tuple[int, int], Tuple[float, float]]) -> float:
    order = list(order)
    return sum(matrix[(order[i], order[i + 1])][0] for i in range(len(order) - 1))


def routes_distance(routes: List[List[int]], matrix: Dict[Tuple[int, int], Tuple[float, float]]) -> float:
    return sum(route_distance(route, matrix) for route in routes)


def count_edges(graph: dict) -> int:
    return sum(len(neighbors) for neighbors in graph.values()) // 2


def format_route(route: List[int]) -> str:
    return " -> ".join(str(point) for point in route)


def sample_history(history: List[float], generation_count: int) -> List[Tuple[int, float]]:
    wanted = [1, 10, 50, generation_count]
    result = []
    for gen in wanted:
        index = min(max(gen - 1, 0), len(history) - 1)
        if history:
            result.append((gen, history[index]))
    return result


def path_avoids_obstacles(path: List[int], graph_points: List[dict], obstacles: List[dict]) -> bool:
    for i in range(len(path) - 1):
        if not edge_is_allowed(graph_points[path[i]], graph_points[path[i + 1]], obstacles):
            return False
    return True


def explain_verbose(log: TerminalLog) -> None:
    log.write("")
    log.write("GIẢI THÍCH BIẾN TRONG CODE KHI VERBOSE")
    log.write("- A* open_set: hàng đợi ưu tiên, luôn lấy node có f_score thấp nhất.")
    log.write("- A* came_from: bảng cha để truy vết ngược từ goal về start.")
    log.write("- A* g_score: chi phí thực tế đã đi từ start đến node hiện tại.")
    log.write("- A* f_score: tổng g_score + heuristic h(n), dùng để ưu tiên mở node.")
    log.write("- A* current: node đang được lấy ra khỏi priority queue để mở rộng.")
    log.write("- A* neighbor: node kề của current đang được xét cập nhật chi phí.")
    log.write("- GA chromosome: một hoán vị các điểm giao, ví dụ [3, 1, 5, 2].")
    log.write("- GA population: tập nhiều chromosome ứng viên.")
    log.write("- GA fitness: tổng quãng đường, càng thấp càng tốt.")
    log.write("- GA selection: chọn cá thể tốt làm cha mẹ, code dùng tournament_selection.")
    log.write("- GA crossover: lai thứ tự bằng order_crossover để tạo route con hợp lệ.")
    log.write("- GA mutation: swap_mutation đổi chỗ hai gene để tăng đa dạng.")
    log.write("- GA elitism: giữ lại một số cá thể tốt nhất qua thế hệ sau.")


def print_explain() -> None:
    configure_stdout()
    log = TerminalLog()
    log.write("============================================================")
    log.write("GIẢI THÍCH NHANH CODE A* VÀ GENETIC ALGORITHM")
    log.write("============================================================")
    log.write("1. A* trong code hoạt động thế nào?")
    log.write("   A* lấy node có f(n)=g(n)+h(n) nhỏ nhất từ priority queue, cập nhật chi phí cho các neighbor, rồi truy vết đường bằng came_from khi gặp goal.")
    log.write("2. Vì sao dùng priority queue?")
    log.write("   Vì cần lấy nhanh node có f_score nhỏ nhất. Code dùng heapq trong SimplePriorityQueue, thao tác lấy/thêm là O(log n).")
    log.write("3. came_from dùng để làm gì?")
    log.write("   came_from lưu node cha tốt nhất của mỗi node. Khi đến đích, reconstruct_path đi ngược từ goal về start để tạo path.")
    log.write("4. g_score và f_score khác nhau thế nào?")
    log.write("   g_score là chi phí thật đã đi. f_score = g_score + heuristic, là điểm ưu tiên để A* quyết định mở node nào trước.")
    log.write("5. GA mã hóa nghiệm ra sao?")
    log.write("   Một chromosome là hoán vị các điểm giao, không chứa depot 0. Khi tính route, depot được thêm ở đầu và cuối.")
    log.write("6. fitness tính gì?")
    log.write("   fitness tính tổng quãng đường của chromosome. Với nhiều xe, code tách chromosome thành routes rồi cộng chi phí từng route.")
    log.write("7. crossover và mutation giúp gì?")
    log.write("   crossover kết hợp thứ tự tốt từ hai cha mẹ; mutation hoán đổi hai điểm để tránh kẹt ở tối ưu cục bộ.")
    log.write("8. Vì sao cần A* + GA, không chỉ dùng một thuật toán?")
    log.write("   A* giải đường đi cục bộ hợp lệ trên bản đồ có vật cản. GA giải tối ưu thứ tự giao hàng. Kết hợp lại vừa đi đúng đường, vừa giảm tổng chi phí.")


def run_demo(verbose: bool = False) -> dict:
    configure_stdout()
    random.seed(42)
    config = load_config()
    common = config.get("common", {})
    astar_cfg = config.get("astar", {})
    ga_cfg = config.get("ga", {})
    speed_kmh = astar_cfg.get("speed_kmh", 40)
    vehicles = common.get("default_vehicle_count", 2)
    capacity = ga_cfg.get("capacity", 24)
    pop_size = min(int(ga_cfg.get("population_size", 100)), 80)
    generations = min(int(ga_cfg.get("generations", 300)), 80)
    cross_rate = float(ga_cfg.get("crossover_rate", 0.8))
    mut_rate = float(ga_cfg.get("mutation_rate", 0.05))
    elite_size = min(int(ga_cfg.get("elite_size", 10)), pop_size)
    heuristic_type = astar_cfg.get("heuristic_type", "euclidean")

    log = TerminalLog()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    points, obstacles, routing_points, graph, detours = build_demo_case()
    delivery_count = len(points) - 1
    baseline_order = [0] + list(range(1, len(points))) + [0]
    euclidean_matrix = build_euclidean_matrix(points, speed_kmh)

    log.write("============================================================")
    log.write("DEMO: TỐI ƯU ĐƯỜNG ĐI GIAO HÀNG BẰNG A* VÀ GENETIC ALGORITHM")
    log.write("============================================================")
    log.write("")
    log.write("[0] GIỚI THIỆU BÀI TOÁN")
    log.write(f"- Kho hàng: {points[0]['name']} tại ({points[0]['x']}, {points[0]['y']})")
    log.write(f"- Số điểm giao: {delivery_count}")
    log.write(f"- Số xe: {vehicles}")
    log.write(f"- Vật cản: {len(obstacles)} khu vực cấm")
    log.write("- Mục tiêu: giảm tổng quãng đường so với tuyến tuần tự.")

    log.write("")
    log.write("[1] CHUẨN BỊ DỮ LIỆU")
    log.write("- Tạo bản đồ demo cố định để báo cáo có thể lặp lại.")
    log.write("- Tạo danh sách điểm giao và thêm waypoint vòng tránh vật cản.")
    log.write(f"- Số node graph: {len(graph)}")
    log.write(f"- Số cạnh graph: {count_edges(graph)}")
    log.write(f"- Số waypoint tránh vật cản: {len(detours)}")
    log.write("- Một vài điểm giao mẫu:")
    for point in points[:5]:
        log.write(f"  + {point['id']}: {point['name']} ({point['x']}, {point['y']})")

    log.write("")
    log.write("[2] CHẠY TUYẾN TUẦN TỰ BAN ĐẦU")
    log.write("- Giải thích: đây là baseline thứ tự ban đầu, không gọi A*, không gọi GA.")
    baseline_dist = route_distance(baseline_order, euclidean_matrix)
    log.write(f"- Thứ tự điểm giao ban đầu: {format_route(baseline_order)}")
    log.write(f"- Tổng quãng đường baseline trực tiếp: {baseline_dist:.2f} km")
    log.write("- Ý nghĩa: dùng làm mốc so sánh trước khi tối ưu.")

    def h_func(u: int, v: int, pts: List[dict]) -> float:
        return heuristic(u, v, pts, heuristic_type)

    log.write("")
    log.write("[3] CHẠY A*")
    log.write("- A* dùng f(n) = g(n) + h(n).")
    log.write("- g(n) là chi phí đã đi, h(n) là ước lượng đến đích.")
    log.write("- Priority queue ưu tiên node có f thấp.")
    start, goal = 0, 5
    steps, path, astar_cost = astar_with_steps(graph, start, goal, routing_points, h_func)
    avoids = path_avoids_obstacles(path or [], routing_points, obstacles)
    log.write(f"- Start: {start} ({points[start]['name']})")
    log.write(f"- Goal: {goal} ({points[goal]['name']})")
    log.write(f"- Heuristic: {heuristic_type}")
    log.write(f"- Số bước mở rộng: {len(steps)}")
    log.write(f"- Path tìm được: {format_route(path or [])}")
    log.write(f"- Cost A*: {astar_cost:.2f} km")
    log.write(f"- Kết luận tránh vật cản: {'có, path không cắt khu vực cấm' if avoids else 'cảnh báo, path có cạnh cắt vật cản'}")
    for step in steps[:8]:
        log.write(
            "  Step {step}: current={current}, g={g:.2f}, h={h:.2f}, f={f:.2f}, open={open}, closed={closed}".format(**step)
        )

    log.write("")
    log.write("[4] XÂY MA TRẬN CHI PHÍ A*")
    log.write("- Muốn GA tối ưu thứ tự thì cần biết chi phí đi giữa mọi cặp điểm.")
    dist_matrix, path_matrix = build_distance_matrix(
        points,
        graph,
        h_type=heuristic_type,
        speed_kmh=speed_kmh,
        graph_points=routing_points,
        return_paths=True,
    )
    matrix_size = f"{len(points)}x{len(points)}"
    log.write(f"- Kích thước ma trận: {matrix_size}")
    warnings = []
    for pair in [(0, 1), (1, 2), (2, 3), (3, 4)]:
        cost = dist_matrix[pair][0]
        if math.isinf(cost):
            warnings.append(pair)
            log.write(f"  cost({pair[0]} -> {pair[1]}) = INF, không có đường")
        else:
            log.write(f"  cost({pair[0]} -> {pair[1]}) = {cost:.2f} km")
    if warnings:
        log.write(f"- Cảnh báo: có {len(warnings)} cặp mẫu không có đường.")
    else:
        log.write("- Không phát hiện cặp mẫu bị mất đường.")

    demands = {point["id"]: point.get("demand", 1) for point in points}
    demands[0] = 0

    log.write("")
    log.write("[5] CHẠY GA THƯỜNG")
    log.write("- GA dùng quần thể cá thể; mỗi cá thể là một thứ tự giao hàng.")
    log.write("- Fitness là tổng quãng đường, càng thấp càng tốt.")
    log.write("- GA dùng chọn lọc, lai ghép, đột biến để cải thiện nghiệm.")
    log.write(f"- population_size: {pop_size}")
    log.write(f"- generations: {generations}")
    log.write(f"- mutation_rate: {mut_rate}")
    log.write(f"- crossover_rate: {cross_rate}")
    log.write(f"- vehicles: {vehicles}")
    log.write(f"- capacity: {capacity}")
    ga_order, ga_dist, ga_time, ga_history, ga_routes = run_ga(
        euclidean_matrix,
        len(points),
        pop_size=pop_size,
        generations=generations,
        elite_size=elite_size,
        cross_rate=cross_rate,
        mut_rate=mut_rate,
        vehicles=vehicles,
        demands=demands,
        capacity=capacity,
        time_windows=None,
        speed_kmh=speed_kmh,
    )
    for gen, value in sample_history(ga_history, generations):
        log.write(f"  Generation {gen}: best distance = {value:.2f} km")
    ga_actual_dist = routes_distance(ga_routes, dist_matrix)
    log.write(f"- Best order GA thường: {format_route(ga_order)}")
    log.write("- Routes GA thường:")
    for index, route in enumerate(ga_routes, start=1):
        log.write(f"  Xe {index}: {format_route(route)}")
    log.write(f"- Distance theo Euclid: {ga_dist:.2f} km")
    log.write(f"- Actual distance tính lại bằng ma trận A*: {ga_actual_dist:.2f} km")

    log.write("")
    log.write("[6] CHẠY A* + GA")
    log.write("- Đây là phương pháp chính của đề tài.")
    log.write("- A* cung cấp chi phí/path thực tế, GA dùng ma trận đó để tối ưu thứ tự.")
    astar_ga_order, astar_ga_dist, astar_ga_time, astar_ga_history, astar_ga_routes = run_ga(
        dist_matrix,
        len(points),
        pop_size=pop_size,
        generations=generations,
        elite_size=elite_size,
        cross_rate=cross_rate,
        mut_rate=mut_rate,
        vehicles=vehicles,
        demands=demands,
        capacity=capacity,
        time_windows=None,
        speed_kmh=speed_kmh,
    )
    astar_seq_dist = route_distance(baseline_order, dist_matrix)
    improvement = ((astar_seq_dist - astar_ga_dist) / astar_seq_dist * 100.0) if astar_seq_dist > 0 else 0.0
    log.write(f"- Best order A* + GA: {format_route(astar_ga_order)}")
    log.write("- Routes A* + GA:")
    for index, route in enumerate(astar_ga_routes, start=1):
        log.write(f"  Xe {index}: {format_route(route)}")
    log.write("- route_paths: đã có trong path_matrix, mỗi chặng có danh sách node A* chi tiết.")
    log.write(f"- Total distance A* + GA: {astar_ga_dist:.2f} km")
    log.write(f"- Improvement so với tuyến tuần tự A*: {improvement:.2f}%")
    for gen, value in sample_history(astar_ga_history, generations):
        log.write(f"  Hội tụ generation {gen}: best = {value:.2f} km")
    log.write("- Kết luận: A* giúp tuyến hợp lệ trên bản đồ có vật cản; GA giảm chi phí bằng cách đổi thứ tự giao hàng.")

    log.write("")
    log.write("[7] BẢNG SO SÁNH CUỐI")
    rows = [
        ("Tuyến tuần tự", baseline_dist, "Không", "Không", "Baseline thứ tự ban đầu"),
        ("A*", astar_seq_dist, "Không", "Có", "Tìm đường cục bộ theo map"),
        ("GA thường", ga_actual_dist, "Có", "Đánh giá lại", "Tối ưu thứ tự theo Euclid"),
        ("A* + GA", astar_ga_dist, "Có", "Có", "Phương pháp đề xuất"),
    ]
    log.write(f"{'Phương án':<18} {'Tổng km':>12} {'Có tối ưu thứ tự':<20} {'Có xét vật cản':<16} Vai trò")
    for name, distance, optimizes_order, uses_obstacles, role in rows:
        log.write(f"{name:<18} {distance:>12.2f} {optimizes_order:<20} {uses_obstacles:<16} {role}")

    log.write("")
    log.write("[8] KẾT LUẬN DEMO")
    log.write("- Tuyến tuần tự chỉ là baseline.")
    log.write("- A* giải quyết tìm đường cục bộ.")
    log.write("- GA giải quyết tối ưu thứ tự giao hàng.")
    log.write("- A* + GA là phương pháp đề xuất vì kết hợp cả đường đi thực tế và tối ưu tổ hợp.")

    if verbose:
        explain_verbose(log)

    astar_steps_payload = {
        "start": start,
        "goal": goal,
        "heuristic": heuristic_type,
        "path": path,
        "cost": astar_cost,
        "steps": steps,
        "avoids_obstacles": avoids,
    }
    ga_payload = {
        "config": {
            "population_size": pop_size,
            "generations": generations,
            "mutation_rate": mut_rate,
            "crossover_rate": cross_rate,
            "vehicles": vehicles,
            "capacity": capacity,
        },
        "ga_euclidean_history": ga_history,
        "astar_ga_history": astar_ga_history,
    }
    astar_ga_payload = {
        "best_order": astar_ga_order,
        "routes": astar_ga_routes,
        "total_distance": astar_ga_dist,
        "improvement_percent": improvement,
        "route_paths": {
            f"{i}->{j}": path_matrix[(i, j)]
            for route in astar_ga_routes
            for i, j in zip(route, route[1:])
        },
    }
    summary = {
        "scenario": "terminal_astar_ga_demo",
        "point_count": len(points),
        "delivery_count": delivery_count,
        "vehicles": vehicles,
        "obstacles": obstacles,
        "baseline_direct_distance": baseline_dist,
        "astar_sequential_distance": astar_seq_dist,
        "ga_euclidean_distance": ga_dist,
        "ga_actual_astar_distance": ga_actual_dist,
        "astar_ga_distance": astar_ga_dist,
        "improvement_percent": improvement,
        "comparison_rows": [
            {
                "method": name,
                "distance": distance,
                "optimizes_order": optimizes_order,
                "uses_obstacles": uses_obstacles,
                "role": role,
            }
            for name, distance, optimizes_order, uses_obstacles, role in rows
        ],
    }

    (OUTPUT_DIR / "terminal_demo_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "astar_demo_steps.json").write_text(json.dumps(astar_steps_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "ga_demo_history.json").write_text(json.dumps(ga_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "astar_ga_result.json").write_text(json.dumps(astar_ga_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.write("")
    log.write(f"Đã lưu artifact demo tại: {OUTPUT_DIR}")
    log.save(OUTPUT_DIR / "terminal_demo_log.txt")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo terminal A* và Genetic Algorithm cho bài toán giao hàng.")
    parser.add_argument("--demo", action="store_true", help="Chạy demo thuật toán tuần tự từng bước.")
    parser.add_argument("--verbose", action="store_true", help="In thêm giải thích biến trong code A* và GA.")
    parser.add_argument("--explain", action="store_true", help="Chỉ in phần giải thích nhanh để trả lời câu hỏi.")
    args = parser.parse_args()

    if args.explain:
        print_explain()
        return
    if args.demo or not any(vars(args).values()):
        run_demo(verbose=args.verbose)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
