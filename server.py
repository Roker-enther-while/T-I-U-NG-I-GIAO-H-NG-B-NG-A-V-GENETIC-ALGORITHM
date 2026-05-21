from flask import Flask, render_template_string, request, jsonify, Response
import json
import math
import threading
import queue
import sys
import os

# ThĂªm thÆ° má»¥c delivery_optimizer vĂ o sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DELIVERY_DIR = os.path.join(ROOT_DIR, "delivery_optimizer")
DEMO_FILE = os.path.join(ROOT_DIR, "delivery_optimizer_demo.html")
if DELIVERY_DIR not in sys.path:
    sys.path.insert(0, DELIVERY_DIR)

from data.generator import generate_points
from graph.graph import add_edge, add_obstacle_waypoints, build_graph, edge_is_allowed, point_inside_rect
from graph.distance import build_distance_matrix
from algorithms.genetic import run_ga
from logging_utils import AlgorithmRunLogger, matrix_summary, route_summary


def enrich_delivery_points(points, enable_time_windows=True, enable_demands=True):
    for point in points:
        if point["id"] == 0:
            point["demand"] = 0
            point["time_window"] = None
            continue
        if enable_demands:
            point["demand"] = 1 + (point["id"] * 3) % 8
        if enable_time_windows:
            start = 30 + ((point["id"] - 1) % 6) * 25
            point["time_window"] = [start, start + 120]
    return points


def generate_obstacles(count):
    presets = [
        {"id": 1, "x_min": 22, "y_min": 18, "x_max": 38, "y_max": 42, "name": "Khu cam 1"},
        {"id": 2, "x_min": 58, "y_min": 55, "x_max": 78, "y_max": 74, "name": "Khu cam 2"},
        {"id": 3, "x_min": 42, "y_min": 8, "x_max": 52, "y_max": 30, "name": "Duong cam 3"},
    ]
    return presets[:max(0, min(int(count or 0), len(presets)))]


def normalize_graph_mode(mode):
    """Chuáº©n hĂ³a tĂªn cháº¿ Ä‘á»™ Ä‘á»“ thá»‹ nháº­n tá»« UI/API."""
    value = str(mode).lower()
    if value in {"straight", "line", "thang", "tháº³ng"}:
        return "straight"
    if value in {"grid", "luoi", "lÆ°á»›i"}:
        return "grid"
    return "road"


def build_straight_routing_graph(points, obstacles):
    """
    Dá»±ng Ä‘á»“ thá»‹ Ä‘Æ°á»ng tháº³ng: cĂ¡c Ä‘iá»ƒm cĂ³ thá»ƒ ná»‘i trá»±c tiáº¿p náº¿u cáº¡nh khĂ´ng cáº¯t váº­t cáº£n.
    Khi cĂ³ váº­t cáº£n, thĂªm node phá»¥ quanh gĂ³c Ä‘á»ƒ A* cĂ³ thá»ƒ chá»n Ä‘Æ°á»ng vĂ²ng.
    """
    routing_points = add_obstacle_waypoints(points, obstacles)
    return routing_points, build_graph(routing_points, mode="full", obstacles=obstacles)


def build_grid_routing_graph(points, obstacles, spacing=10):
    """
    Dá»±ng Ä‘á»“ thá»‹ lÆ°á»›i Ă´ cho A*.
    - CĂ¡c Ä‘iá»ƒm giao tháº­t giá»¯ id 0..n-1 Ä‘á»ƒ ma tráº­n khoáº£ng cĂ¡ch váº«n khá»›p vá»›i GA.
    - CĂ¡c node lÆ°á»›i Ä‘Æ°á»£c thĂªm sau Ä‘Ă³ vĂ  chá»‰ ná»‘i ngang/dá»c.
    - Node/cáº¡nh náº±m trong hoáº·c cáº¯t váº­t cáº£n bá»‹ loáº¡i bá».
    """
    routing_points = [point.copy() for point in points]
    graph = {index: {} for index in range(len(routing_points))}
    grid_index = {}

    for x in range(0, 101, spacing):
        for y in range(0, 101, spacing):
            point = {
                "id": len(routing_points),
                "x": x,
                "y": y,
                "name": f"Grid {x},{y}",
                "status": "grid",
            }
            if any(point_inside_rect(point, obstacle) for obstacle in obstacles):
                continue
            grid_index[(x, y)] = len(routing_points)
            graph[len(routing_points)] = {}
            routing_points.append(point)

    for (x, y), node_id in grid_index.items():
        for neighbor_key in ((x + spacing, y), (x, y + spacing)):
            neighbor_id = grid_index.get(neighbor_key)
            if neighbor_id is None:
                continue
            p1 = routing_points[node_id]
            p2 = routing_points[neighbor_id]
            if edge_is_allowed(p1, p2, obstacles):
                add_edge(graph, node_id, neighbor_id, spacing)

    grid_nodes = list(grid_index.values())
    for point_index, point in enumerate(points):
        candidates = sorted(
            grid_nodes,
            key=lambda node_id: math.hypot(
                point["x"] - routing_points[node_id]["x"],
                point["y"] - routing_points[node_id]["y"],
            ),
        )
        connected = 0
        for node_id in candidates:
            grid_point = routing_points[node_id]
            if not edge_is_allowed(point, grid_point, obstacles):
                continue
            distance = math.hypot(point["x"] - grid_point["x"], point["y"] - grid_point["y"])
            add_edge(graph, point_index, node_id, distance)
            connected += 1
            if connected >= 4:
                break

    return routing_points, graph


def build_routing_graph(points, obstacles, graph_mode):
    """Táº¡o Ä‘á»“ thá»‹ theo lá»±a chá»n UI: Ä‘Æ°á»ng tháº³ng hoáº·c lÆ°á»›i Ă´."""
    graph_mode = normalize_graph_mode(graph_mode)
    if graph_mode == "grid":
        return build_grid_routing_graph(points, obstacles)
    return build_straight_routing_graph(points, obstacles)


def build_road_network_graph(points, road_nodes, road_edges, obstacles):
    """
    Dá»±ng Ä‘á»“ thá»‹ tá»« chĂ­nh máº¡ng Ä‘Æ°á»ng/háº»m Ä‘ang Ä‘Æ°á»£c UI váº½.
    CĂ¡c Ä‘iá»ƒm giao hĂ ng giá»¯ id 0..n-1 Ä‘á»ƒ GA dĂ¹ng á»•n Ä‘á»‹nh; node Ä‘Æ°á»ng tháº­t
    Ä‘Æ°á»£c Ä‘áº·t sau Ä‘Ă³ theo offset. Má»—i Ä‘iá»ƒm giao ná»‘i vĂ o node Ä‘Æ°á»ng gáº§n nháº¥t.
    """
    routing_points = [point.copy() for point in points]
    graph = {index: {} for index in range(len(points))}
    node_offset = len(points)
    road_id_to_graph_id = {}

    for node in road_nodes:
        graph_id = node_offset + int(node["id"])
        road_id_to_graph_id[int(node["id"])] = graph_id
        graph[graph_id] = {}
        routing_points.append({
            "id": graph_id,
            "x": float(node["x"]),
            "y": float(node["y"]),
            "name": f"Road {node['id']}",
            "status": "road",
        })

    # Vá»›i cháº¿ Ä‘á»™ máº¡ng Ä‘Æ°á»ng, road_edges lĂ  cĂ¡c Ä‘oáº¡n Ä‘Æ°á»ng/háº»m Ä‘Ă£ Ä‘Æ°á»£c UI váº½.
    # NhĂ /cĂ´ng trĂ¬nh náº±m trong block nĂªn khĂ´ng dĂ¹ng Ä‘á»ƒ xĂ³a road_edges, trĂ¡nh lĂ m
    # Ä‘á»©t máº¡ng Ä‘Æ°á»ng. Chá»‰ váº­t cáº£n/Ä‘Æ°á»ng cáº¥m do ngÆ°á»i dĂ¹ng cáº¥u hĂ¬nh má»›i Ä‘Ă³ng Ä‘Æ°á»ng.
    road_closure_obstacles = [
        obstacle for obstacle in obstacles
        if not str(obstacle.get("id", "")).startswith(("building-", "water-"))
    ]

    for edge in road_edges:
        a_original = int(edge["a"])
        b_original = int(edge["b"])
        a = road_id_to_graph_id.get(a_original)
        b = road_id_to_graph_id.get(b_original)
        if a is None or b is None:
            continue
        p1 = routing_points[a]
        p2 = routing_points[b]
        weight = math.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"])
        if not edge_is_allowed(p1, p2, road_closure_obstacles):
            continue
        add_edge(graph, a, b, weight)

    for point_index, point in enumerate(points):
        road_node_id = point.get("nodeId")
        if road_node_id is None:
            continue
        road_graph_id = road_id_to_graph_id.get(int(road_node_id))
        if road_graph_id is None:
            continue
        road_point = routing_points[road_graph_id]
        weight = math.hypot(point["x"] - road_point["x"], point["y"] - road_point["y"])
        add_edge(graph, point_index, road_graph_id, weight)

    return routing_points, graph


def generate_feasible_points(delivery_count, obstacles, max_attempts=50):
    for _ in range(max_attempts):
        points = enrich_delivery_points(generate_points(delivery_count + 1))
        if all(
            point["id"] == 0 or not any(point_inside_rect(point, obstacle) for obstacle in obstacles)
            for point in points
        ):
            return points
    points = enrich_delivery_points(generate_points(delivery_count + 1))
    for point in points:
        if point["id"] != 0 and any(point_inside_rect(point, obstacle) for obstacle in obstacles):
            point["x"] = 10 + (point["id"] * 17) % 80
            point["y"] = 10 + (point["id"] * 29) % 80
    return points


def unreachable_pairs_from_matrix(matrix, point_count):
    pairs = []
    for i in range(point_count):
        for j in range(point_count):
            if i != j and matrix.get((i, j), (float("inf"),))[0] == float("inf"):
                pairs.append([i, j])
    return pairs


def build_euclidean_distance_matrix(points, speed_kmh):
    """Tao ma tran khoang cach Euclid cho GA thuáº§n (khong dua tren A* matrix)."""
    matrix = {}
    for i, source in enumerate(points):
        for j, target in enumerate(points):
            if i == j:
                dist = 0.0
            else:
                dist = math.hypot(source["x"] - target["x"], source["y"] - target["y"])
            travel_time = 0.0 if speed_kmh <= 0 else (dist / speed_kmh) * 60.0
            matrix[(i, j)] = (dist, travel_time)
    return matrix


def path_to_coordinates(path, routing_points):
    """Chuyá»ƒn path A* dáº¡ng node id sang danh sĂ¡ch tá»a Ä‘á»™ Ä‘á»ƒ UI váº½ Ä‘Ăºng Ä‘Æ°á»ng backend."""
    if not path:
        return []
    return [
        {
            "id": node_id,
            "x": routing_points[node_id]["x"],
            "y": routing_points[node_id]["y"],
        }
        for node_id in path
    ]


def build_route_path_payload(routes, path_matrix, routing_points):
    """Táº¡o payload path chi tiáº¿t cho tá»«ng tuyáº¿n xe vĂ  tá»«ng cháº·ng giao hĂ ng."""
    route_payload = []
    for route in routes:
        segments = []
        for index in range(len(route) - 1):
            start = route[index]
            goal = route[index + 1]
            path = path_matrix.get((start, goal))
            segments.append({
                "from": start,
                "to": goal,
                "coords": path_to_coordinates(path, routing_points),
            })
        route_payload.append(segments)
    return route_payload


def split_deliverable_points(points):
    """TĂ¡ch Ä‘iá»ƒm giao Ä‘Æ°á»£c vĂ  khĂ´ng giao Ä‘Æ°á»£c do náº±m trong khu vá»±c cáº¥m."""
    deliverable = []
    undeliverable = []
    id_map = {}
    for point in points:
        if point.get("id") == 0 or not point.get("undeliverable"):
            id_map[point["id"]] = len(deliverable)
            normalized = point.copy()
            normalized["id"] = len(deliverable)
            deliverable.append(normalized)
        else:
            undeliverable.append(point)
    return deliverable, undeliverable, id_map


def parse_int_param(value, name):
    """Parse sá»‘ nguyĂªn tá»« input API; nĂ©m ValueError vá»›i thĂ´ng bĂ¡o rĂµ rĂ ng náº¿u sai."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Gia tri {name} khong hop le")


def normalize_positive_param(value, name, minimum=1):
    parsed = parse_int_param(value, name)
    if parsed < minimum:
        raise ValueError(f"Gia tri {name} phai >= {minimum}")
    return parsed


def find_missing_route_segments(routes, path_matrix):
    """TĂ¬m cĂ¡c cháº·ng khĂ´ng cĂ³ path backend Ä‘á»ƒ tráº£ lá»—i sá»›m thay vĂ¬ Ä‘á»ƒ UI váº½ há»ng."""
    missing = []
    for route_index, route in enumerate(routes):
        for index in range(len(route) - 1):
            start = route[index]
            goal = route[index + 1]
            if (start, goal) not in path_matrix:
                missing.append({"route": route_index, "from": start, "to": goal})
    return missing


def remap_route_to_original_ids(route, deliverable_points):
    return [deliverable_points[point].get("original_id", deliverable_points[point]["id"]) for point in route]


def remap_routes_to_original_ids(routes, deliverable_points):
    return [remap_route_to_original_ids(route, deliverable_points) for route in routes]


def sequential_baseline_route(num_points):
    if num_points <= 1:
        return [0, 0] if num_points == 1 else []
    return [0] + list(range(1, num_points)) + [0]


def route_total_distance(route, distance_matrix):
    total = 0
    for index in range(len(route) - 1):
        total += distance_matrix[(route[index], route[index + 1])][0]
    return total


def route_total_time(route, distance_matrix):
    total = 0
    for index in range(len(route) - 1):
        total += distance_matrix[(route[index], route[index + 1])][1]
    return total

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>DelivRoute v2 â€” Tá»‘i Æ°u giao hĂ ng A* & GA (Python Backend)</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<style>
:root {
  --bg:#0b0f1a; --surface:#111827; --surface2:#1a2235; --border:#1f2d45;
  --accent:#00e5ff; --accent2:#ff6b35; --accent3:#a8ff3e;
  --text:#e2e8f0; --muted:#64748b;
  --font-mono:'Space Mono',monospace; --font-body:'DM Sans',sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--font-body);min-height:100vh;overflow-x:hidden;}

header{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;border-bottom:1px solid var(--border);background:rgba(11,15,26,.97);backdrop-filter:blur(12px);position:sticky;top:0;z-index:200;}
.logo{font-family:var(--font-mono);font-size:17px;font-weight:700;color:var(--accent);}
.logo span{color:var(--accent2);}
.badge{font-family:var(--font-mono);font-size:9px;padding:3px 8px;border:1px solid var(--border);border-radius:4px;color:var(--muted);letter-spacing:1px;}
.header-right{display:flex;gap:8px;align-items:center;}

.layout{display:grid;grid-template-columns:300px 1fr;height:calc(100vh - 53px);}

.sidebar{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;}
.sb-sec{padding:14px 16px;border-bottom:1px solid var(--border);}
.sec-lbl{font-family:var(--font-mono);font-size:9px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:10px;}
.ctrl{margin-bottom:10px;}
.ctrl-lbl{font-size:11px;color:var(--muted);margin-bottom:4px;display:flex;justify-content:space-between;}
.ctrl-lbl span{font-family:var(--font-mono);color:var(--accent);font-size:10px;}
input[type=range]{width:100%;accent-color:var(--accent);cursor:pointer;}
select{width:100%;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px;font-family:var(--font-mono);font-size:10px;cursor:pointer;}

.btn{width:100%;padding:9px;border:none;border-radius:5px;font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:1px;cursor:pointer;transition:all .18s;text-transform:uppercase;margin-top:6px;display:block;}
.btn:first-child{margin-top:0;}
.btn-cyan{background:var(--accent);color:#000;}
.btn-cyan:hover{background:#33eaff;transform:translateY(-1px);}
.btn-orange{background:transparent;color:var(--accent2);border:1px solid var(--accent2);}
.btn-orange:hover{background:rgba(255,107,53,.1);}
.btn-lime{background:var(--accent3);color:#000;}
.btn-lime:hover{background:#bfff5a;transform:translateY(-1px);}
.btn-dim{background:var(--surface2);color:var(--accent);border:1px solid var(--border);}
.btn-dim:hover{border-color:var(--accent);background:rgba(0,229,255,.06);}
.btn-violet{background:transparent;color:#a78bfa;border:1px solid #a78bfa;}
.btn-violet:hover{background:rgba(167,139,250,.1);}
.btn:disabled{opacity:.32;cursor:not-allowed;transform:none !important;}

.preset-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}
.pre-btn{padding:9px 6px;border-radius:5px;border:1px solid var(--border);background:var(--surface2);color:var(--muted);font-family:var(--font-mono);font-size:9px;cursor:pointer;text-align:center;transition:all .18s;letter-spacing:.4px;line-height:1.5;}
.pre-btn:hover,.pre-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(0,229,255,.07);}

.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}
.stat-card{background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:8px 10px;}
.sv{font-family:var(--font-mono);font-size:14px;font-weight:700;color:var(--accent);line-height:1;margin-bottom:2px;}
.sv.o{color:var(--accent2);}.sv.g{color:var(--accent3);}.sv.p{color:#a78bfa;}
.sl{font-size:9px;color:var(--muted);}

/* A* step panel */
.step-panel{background:rgba(0,229,255,.04);border-bottom:1px solid var(--border);padding:12px 16px;display:none;}
.step-info{font-family:var(--font-mono);font-size:9px;color:var(--accent3);line-height:1.6;margin-bottom:8px;min-height:28px;}
.step-row{display:flex;gap:6px;}
.step-row .btn{flex:1;margin-top:0;font-size:9px;padding:7px 4px;}

.route-list{padding:10px 14px;flex:1;overflow-y:auto;}
.ri{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px;animation:fi .3s ease forwards;opacity:0;}
.ri:last-child{border-bottom:none;}
.rstep{font-family:var(--font-mono);font-size:8px;width:19px;height:19px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--surface2);color:var(--accent);border:1px solid var(--accent);flex-shrink:0;font-weight:700;}
.rstep.dep{background:var(--accent2);border-color:var(--accent2);color:#000;}
.rdist{margin-left:auto;font-family:var(--font-mono);font-size:8px;color:var(--muted);}
@keyframes fi{to{opacity:1;}}

.main{display:flex;flex-direction:column;background:var(--bg);overflow:hidden;}
.cwrap{flex:1;position:relative;}
canvas#mc{width:100%;height:100%;display:block;cursor:crosshair;}

.bot{height:172px;border-top:1px solid var(--border);background:var(--surface);display:grid;grid-template-columns:1fr 1fr 1fr;}
.panel{padding:11px 14px;border-right:1px solid var(--border);overflow:hidden;}
.panel:last-child{border-right:none;}
.ptitle{font-family:var(--font-mono);font-size:8px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:7px;}
#log{font-family:var(--font-mono);font-size:9.5px;color:var(--accent3);line-height:1.7;overflow-y:auto;height:130px;}
.ll{opacity:0;animation:fi .2s ease forwards;}
.ll.w{color:var(--accent2);}.ll.i{color:var(--accent);}
canvas#cc{width:100%;height:130px;display:block;}
#cpanel{overflow-y:auto;height:130px;}
.ctbl{width:100%;border-collapse:collapse;font-size:9px;}
.ctbl th{font-family:var(--font-mono);font-size:7.5px;letter-spacing:1px;color:var(--muted);padding:3px 5px;text-align:left;border-bottom:1px solid var(--border);}
.ctbl td{padding:4px 5px;border-bottom:1px solid rgba(31,45,69,.4);font-family:var(--font-mono);}
.ctbl .g{color:var(--accent3);}.ctbl .r{color:var(--accent2);}

.legend{position:absolute;top:12px;right:12px;background:rgba(11,15,26,.92);backdrop-filter:blur(8px);border:1px solid var(--border);border-radius:7px;padding:10px 12px;font-size:9.5px;}
.li{display:flex;align-items:center;gap:7px;margin-bottom:5px;color:var(--muted);}
.li:last-child{margin-bottom:0;}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.lp{width:20px;height:2px;flex-shrink:0;border-radius:1px;}

.asov{position:absolute;top:12px;left:12px;background:rgba(11,15,26,.93);border:1px solid var(--accent);border-radius:7px;padding:10px 14px;font-family:var(--font-mono);font-size:9px;display:none;max-width:210px;z-index:10;}
.asov h4{color:var(--accent);font-size:9px;margin-bottom:6px;}
.ovr{display:flex;justify-content:space-between;gap:10px;margin-bottom:2px;color:var(--muted);}
.ovr span{color:var(--text);}

#tip{position:absolute;background:rgba(11,15,26,.97);border:1px solid var(--border);border-radius:5px;padding:6px 9px;font-size:9.5px;pointer-events:none;display:none;z-index:50;font-family:var(--font-mono);}

/* Modal */
.moverlay{position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:500;display:none;align-items:center;justify-content:center;}
.moverlay.show{display:flex;}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:26px;max-width:1040px;width:94%;box-shadow:0 24px 90px rgba(0,0,0,.45);}
.modal h3{font-family:var(--font-mono);color:var(--accent);margin-bottom:16px;font-size:16px;line-height:1.35;}
.mcls{float:right;background:none;border:none;color:var(--muted);cursor:pointer;font-size:17px;line-height:1;margin-top:-4px;}
.modal table{width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:12px;}
.modal table th{color:var(--muted);font-size:10px;letter-spacing:.8px;text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);}
.modal table td{padding:10px;border-bottom:1px solid rgba(31,45,69,.35);vertical-align:top;}
.modal .g{color:var(--accent3);}.modal .o{color:var(--accent2);}
.ibanner{margin-top:14px;background:rgba(168,255,62,.07);border:1px solid rgba(168,255,62,.25);border-radius:6px;padding:12px;text-align:center;}
.ibanner .pct{font-family:var(--font-mono);font-size:32px;font-weight:700;color:var(--accent3);}
.ibanner p{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.5;}
.mbtns{display:flex;gap:8px;margin-top:14px;}
.mbtns button{flex:1;padding:9px;border-radius:5px;font-family:var(--font-mono);font-size:9px;font-weight:700;cursor:pointer;letter-spacing:1px;border:none;transition:all .18s;}
.mbtn-close{background:var(--surface2);color:var(--muted);}
.mbtn-dl{background:var(--accent3);color:#000;}
.mbtn-dl:hover{background:#bfff5a;}
.routes-compare{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;}
.route-card{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:10px;}
.route-card.best{border-color:var(--accent3);}
.route-card h4{font-family:var(--font-mono);font-size:9px;color:var(--accent2);margin-bottom:5px;}
.route-card.best h4{color:var(--accent3);}
.route-card .tag{font-family:var(--font-mono);font-size:7px;color:var(--muted);margin-bottom:7px;letter-spacing:1px;}
.route-card.best .tag{color:var(--accent3);}
.route-card p{font-size:9px;color:var(--text);line-height:1.5;}
</style>
</head>
<body>

<header>
  <div class="logo">Deliv<span>Route</span> <span style="font-size:11px;color:var(--muted);font-weight:400;">v2</span></div>
  <div class="header-right">
    <span class="badge">A* + GENETIC ALGORITHM (PYTHON BACKEND)</span>
    <span class="badge" id="mbadge">READY</span>
  </div>
</header>

<div class="layout">
<aside class="sidebar">

  <div class="sb-sec">
    <div class="sec-lbl">đŸ“ Ká»‹ch báº£n máº«u</div>
    <div class="preset-grid">
      <div class="pre-btn" onclick="loadPreset('urban')" id="pre-urban">đŸ™ï¸ Ná»™i thĂ nh<br><small>dĂ y Ä‘áº·c Â· 18 Ä‘iá»ƒm</small></div>
      <div class="pre-btn" onclick="loadPreset('suburb')" id="pre-suburb">đŸŒ¿ Ngoáº¡i Ă´<br><small>thÆ°a thá»›t Â· 8 Ä‘iá»ƒm</small></div>
      <div class="pre-btn" onclick="loadPreset('mixed')" id="pre-mixed">đŸ—ºï¸ Há»—n há»£p<br><small>thá»±c táº¿ Â· 14 Ä‘iá»ƒm</small></div>
      <div class="pre-btn" onclick="loadPreset('custom')" id="pre-custom">â™ï¸ Tuá»³ chá»‰nh<br><small>slider bĂªn dÆ°á»›i</small></div>
    </div>
  </div>

  <div class="sb-sec" id="custom-sec">
    <div class="sec-lbl">Cáº¥u hĂ¬nh báº£n Ä‘á»“</div>
    <div class="ctrl">
      <div class="ctrl-lbl">Sá»‘ Ä‘iá»ƒm giao hĂ ng <span id="nv">12</span></div>
      <input type="range" id="np" min="4" max="30" value="12"/>
    </div>
    <div class="ctrl">
      <div class="ctrl-lbl">Tá»‘c Ä‘á»™ xe (km/h) <span id="sv">40</span></div>
      <input type="range" id="spd" min="20" max="80" value="40" step="5"/>
    </div>
    <button class="btn btn-cyan" id="btn-gen">âŸ³ Táº¡o báº£n Ä‘á»“ má»›i</button>
  </div>

  <div class="sb-sec">
    <div class="sec-lbl">Thuáº­t toĂ¡n A*</div>
    <div class="ctrl">
      <div class="ctrl-lbl">Heuristic</div>
      <select id="heur">
        <option value="euclidean">Euclidean distance</option>
        <option value="manhattan">Manhattan distance</option>
      </select>
    </div>
    <button class="btn btn-orange" id="btn-astar" disabled>â–¶ Cháº¡y A* â€” xĂ¢y ma tráº­n</button>
    <button class="btn btn-dim" id="btn-step" disabled>â­ Cháº¿ Ä‘á»™ Step-by-step</button>
  </div>

  <div class="step-panel" id="step-panel">
    <div class="step-info" id="sinfo">â€”</div>
    <div class="step-row">
      <button class="btn btn-dim" id="bprev">â—€ Prev</button>
      <button class="btn btn-dim" id="bnext">Next â–¶</button>
      <button class="btn btn-orange" id="bfin">âœ“ Finish</button>
    </div>
  </div>

  <div class="sb-sec">
    <div class="sec-lbl">Genetic Algorithm</div>
    <div class="ctrl">
      <div class="ctrl-lbl">Quáº§n thá»ƒ <span id="pv">80</span></div>
      <input type="range" id="ps" min="20" max="200" value="80" step="10"/>
    </div>
    <div class="ctrl">
      <div class="ctrl-lbl">Tháº¿ há»‡ <span id="gv">300</span></div>
      <input type="range" id="gens" min="50" max="800" value="300" step="50"/>
    </div>
    <div class="ctrl">
      <div class="ctrl-lbl">Tá»· lá»‡ Ä‘á»™t biáº¿n <span id="mv">3%</span></div>
      <input type="range" id="mr" min="1" max="15" value="3"/>
    </div>
    <button class="btn btn-lime" id="btn-ga" disabled>â¡ Cháº¡y GA tá»‘i Æ°u lá»™ trĂ¬nh</button>
  </div>

  <div class="sb-sec">
    <div class="sec-lbl">Káº¿t quáº£</div>
    <div class="stat-grid">
      <div class="stat-card"><div class="sv" id="sd">â€”</div><div class="sl">Tá»•ng km (GA)</div></div>
      <div class="stat-card"><div class="sv o" id="st">â€”</div><div class="sl">Thá»i gian</div></div>
      <div class="stat-card"><div class="sv g" id="ss">â€”</div><div class="sl">Äiá»ƒm giao</div></div>
      <div class="stat-card"><div class="sv p" id="si">â€”</div><div class="sl">Cáº£i thiá»‡n %</div></div>
      <div class="stat-card"><div class="sv" id="sbase">â€”</div><div class="sl">Tuyáº¿n ban Ä‘áº§u</div></div>
    </div>
    <button class="btn btn-violet" id="btn-cmp" disabled style="margin-top:8px;">đŸ“ So sĂ¡nh tuáº§n tá»± vs A* + GA</button>
    <button class="btn btn-violet" id="btn-exp" disabled>đŸ“· Xuáº¥t PNG bĂ¡o cĂ¡o</button>
  </div>

  <div class="route-list" id="rlist">
    <div style="color:var(--muted);font-size:10px;text-align:center;padding:14px 0;">Chá»n ká»‹ch báº£n â†’ A* â†’ GA</div>
  </div>
</aside>

<main class="main">
  <div class="cwrap">
    <canvas id="mc"></canvas>
    <div class="legend">
      <div class="li"><div class="dot" style="background:#ff6b35"></div>Kho hĂ ng</div>
      <div class="li"><div class="dot" style="background:#00e5ff"></div>Äiá»ƒm giao</div>
      <div class="li"><div class="lp" style="background:#a8ff3e"></div>Lá»™ trĂ¬nh GA</div>
      <div class="li"><div class="dot" style="background:#a8ff3e;border-radius:2px;width:8px;height:8px"></div>ÄĂ£ giao</div>
      <div class="li"><div class="dot" style="background:rgba(255,107,53,.5)"></div>Open list (A*)</div>
      <div class="li"><div class="dot" style="background:#64748b"></div>Closed list (A*)</div>
    </div>
    <div class="asov" id="asov">
      <h4>â–¸ A* Step-by-step</h4>
      <div class="ovr">BÆ°á»›c: <span id="ov-s">â€”</span></div>
      <div class="ovr">Node hiá»‡n táº¡i: <span id="ov-c">â€”</span></div>
      <div class="ovr">g(n): <span id="ov-g">â€”</span></div>
      <div class="ovr">h(n): <span id="ov-h">â€”</span></div>
      <div class="ovr">f(n) = g+h: <span id="ov-f">â€”</span></div>
      <div class="ovr">Open list: <span id="ov-o">â€”</span></div>
      <div class="ovr">Closed list: <span id="ov-cl">â€”</span></div>
    </div>
    <div id="tip"></div>
  </div>

  <div class="bot">
    <div class="panel">
      <div class="ptitle">â–¸ Log thuáº­t toĂ¡n</div>
      <div id="log"></div>
    </div>
    <div class="panel">
      <div class="ptitle">â–¸ GA â€” ÄÆ°á»ng cong há»™i tá»¥</div>
      <canvas id="cc"></canvas>
    </div>
    <div class="panel">
      <div class="ptitle">â–¸ So sĂ¡nh lá»™ trĂ¬nh</div>
      <div id="cpanel"><div style="color:var(--muted);font-size:9px;font-family:var(--font-mono);padding-top:6px;">Cháº¡y GA Ä‘á»ƒ xem so sĂ¡nh</div></div>
    </div>
  </div>
</main>
</div>

<div class="moverlay" id="moverlay">
  <div class="modal">
    <button class="mcls" onclick="closeModal()">âœ•</button>
    <h3>đŸ“ So sĂ¡nh chi tiáº¿t: Tuáº§n tá»± vs A* + GA</h3>
    <table>
      <thead><tr><th>CHá»ˆ Sá»</th><th>TUáº¦N Tá»°</th><th>A* + GA</th><th>CHĂNH Lá»†CH</th></tr></thead>
      <tbody id="cbody"></tbody>
    </table>
    <div class="routes-compare">
      <div class="route-card" id="route-base-card">
        <h4 id="route-base-title">Lá»™ trĂ¬nh tuáº§n tá»±</h4>
        <div class="tag" id="route-base-tag">TUYáº¾N Äá»I CHIáº¾U</div>
        <p id="route-base-text">â€”</p>
      </div>
      <div class="route-card" id="route-ga-card">
        <h4 id="route-ga-title">Lá»™ trĂ¬nh A* + GA</h4>
        <div class="tag" id="route-ga-tag">Tá»I Æ¯U HÆ N</div>
        <p id="route-ga-text">â€”</p>
      </div>
    </div>
    <div class="ibanner">
      <div class="pct" id="cpct">â€”</div>
      <p>A* + GA cáº£i thiá»‡n tá»•ng quĂ£ng Ä‘Æ°á»ng so vá»›i thá»© tá»± tuáº§n tá»±</p>
    </div>
    <div class="mbtns">
      <button class="mbtn-close" onclick="closeModal()">ÄĂ“NG</button>
      <button class="mbtn-dl" onclick="exportPNG()">đŸ“· XUáº¤T PNG</button>
    </div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
const rand=(a,b)=>Math.random()*(b-a)+a;
const dst=(a,b)=>Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2);

function log(msg,t=''){
  const el=$('log'),d=document.createElement('div');
  d.className='ll'+(t?' '+t:'');d.textContent='> '+msg;
  el.appendChild(d);el.scrollTop=el.scrollHeight;
  if(el.children.length>80)el.removeChild(el.firstChild);
}

let pts=[],dm=[],best=[],conv=[],delivered=new Set(),animSt=0;
let randOrd=[],randFit=0;
let stepMode=false,steps=[],stepIdx=0;
const SC=1.0;

const cv=$('mc'),ctx=cv.getContext('2d');
const CC=$('cc'),cctx=CC.getContext('2d');

function resizeCanvas(){
  cv.width=cv.parentElement.clientWidth;cv.height=cv.parentElement.clientHeight;
  CC.width=CC.offsetWidth;CC.height=CC.offsetHeight;draw();
  drawConvergence();
}
window.addEventListener('resize',resizeCanvas);

function loadPreset(k){
  document.querySelectorAll('.pre-btn').forEach(b=>b.classList.remove('active'));
  $('pre-'+k).classList.add('active');
  const map={urban:{n:18,s:30},suburb:{n:8,s:60},mixed:{n:14,s:40}};
  if(map[k]){
    $('np').value=map[k].n;$('nv').textContent=map[k].n;
    $('spd').value=map[k].s;$('sv').textContent=map[k].s;
    gen();
  }
}

async function gen(){
  const n=parseInt($('np').value);
  log(`Táº¡o báº£n Ä‘á»“ má»›i vá»›i ${n} Ä‘iá»ƒm...`);
  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ n })
    });
    const data = await res.json();
    pts = data.points;
    best=[];conv=[];delivered.clear();animSt=0;randOrd=[];
    stepMode=false;$('asov').style.display='none';$('step-panel').style.display='none';
    $('btn-astar').disabled=false;$('btn-step').disabled=false;
    $('btn-ga').disabled=true;$('btn-cmp').disabled=true;$('btn-exp').disabled=true;
    $('sd').textContent=$('st').textContent=$('ss').textContent=$('si').textContent='â€”';
    $('mbadge').textContent='READY';
    $('rlist').innerHTML='<div style="color:var(--muted);font-size:10px;text-align:center;padding:14px 0;">Nháº¥n A* Ä‘á»ƒ xĂ¢y ma tráº­n</div>';
    $('cpanel').innerHTML='<div style="color:var(--muted);font-size:9px;font-family:var(--font-mono);padding-top:6px;">Cháº¡y GA Ä‘á»ƒ xem so sĂ¡nh</div>';
    draw();
  } catch (e) { log('Lá»—i táº¡o báº£n Ä‘á»“: '+e.message,'w'); }
}

function draw(asSt=null){
  if(!cv.width)return;
  ctx.clearRect(0,0,cv.width,cv.height);
  ctx.strokeStyle='rgba(31,45,69,.3)';ctx.lineWidth=.5;
  for(let x=0;x<cv.width;x+=50){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,cv.height);ctx.stroke();}
  for(let y=0;y<cv.height;y+=50){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cv.width,y);ctx.stroke();}
  if(!pts.length)return;

  if(asSt){
    asSt.closed.forEach(i=>{const p=pts[i];ctx.beginPath();ctx.arc(p.x,p.y,24,0,Math.PI*2);ctx.fillStyle='rgba(100,116,139,.13)';ctx.fill();});
    asSt.open.forEach(i=>{const p=pts[i];ctx.beginPath();ctx.arc(p.x,p.y,24,0,Math.PI*2);ctx.fillStyle='rgba(255,107,53,.16)';ctx.fill();});
    if(asSt.path&&asSt.path.length>1){
      ctx.beginPath();ctx.strokeStyle='rgba(0,229,255,.45)';ctx.lineWidth=2;ctx.setLineDash([5,4]);
      asSt.path.forEach((i,j)=>{const p=pts[i];j===0?ctx.moveTo(p.x,p.y):ctx.lineTo(p.x,p.y);});
      ctx.stroke();ctx.setLineDash([]);
    }
  }

  if(best.length&&!asSt){
    const ord=[0,...best,0];
    ctx.beginPath();ctx.strokeStyle='#a8ff3e';ctx.lineWidth=2.5;ctx.setLineDash([]);
    ctx.shadowColor='#a8ff3e';ctx.shadowBlur=7;
    ord.forEach((i,j)=>{const p=pts[i];j===0?ctx.moveTo(p.x,p.y):ctx.lineTo(p.x,p.y);});
    ctx.stroke();ctx.shadowBlur=0;
    for(let i=0;i<ord.length-1;i++){
      const a=pts[ord[i]],b=pts[ord[i+1]];
      const mx=(a.x+b.x)/2,my=(a.y+b.y)/2,ang=Math.atan2(b.y-a.y,b.x-a.x);
      ctx.save();ctx.translate(mx,my);ctx.rotate(ang);
      ctx.fillStyle='#a8ff3e';ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(-8,-3.5);ctx.lineTo(-8,3.5);ctx.closePath();ctx.fill();
      ctx.restore();
    }
  }

  pts.forEach((p,i)=>{
    const done=delivered.has(p.id),isCur=asSt&&asSt.current===i;
    const r=p.id===0?13:8;
    const col=p.id===0?'#ff6b35':done?'#a8ff3e':isCur?'#ffffff':'#00e5ff';
    const grd=ctx.createRadialGradient(p.x,p.y,r,p.x,p.y,r+9);
    grd.addColorStop(0,col+'55');grd.addColorStop(1,col+'00');
    ctx.beginPath();ctx.arc(p.x,p.y,r+9,0,Math.PI*2);ctx.fillStyle=grd;ctx.fill();
    ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fillStyle=col;ctx.fill();
    ctx.strokeStyle='rgba(255,255,255,.2)';ctx.lineWidth=1.5;ctx.stroke();
    ctx.font=p.id===0?'bold 9px DM Sans':'8px DM Sans';ctx.fillStyle='#000';ctx.textAlign='center';
    ctx.fillText(p.id===0?'KHO':`P${i}`,p.x,p.y+3);
    ctx.font='8.5px DM Sans';ctx.fillStyle='rgba(200,220,240,.6)';
    const sn=p.name.length>13?p.name.slice(0,13)+'â€¦':p.name;
    ctx.fillText(sn,p.x,p.y-r-5);
  });
}

async function runAStar(){
  log('Báº¯t Ä‘áº§u A* â€” xĂ¢y ma tráº­n...');
  $('btn-astar').disabled=true;$('btn-step').disabled=true;
  const h = $('heur').value;
  try {
    const res = await fetch('/api/astar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ heuristic: h, speed: parseInt($('spd').value) })
    });
    const data = await res.json();
    dm = data.dist_matrix;
    log(`A* hoĂ n táº¥t: ma tráº­n ${data.matrix_size}`,'i');
    $('btn-ga').disabled=false;$('mbadge').textContent='A* DONE';
  } catch(e) { log('Lá»—i A*: '+e.message,'w'); }
  finally { $('btn-astar').disabled=false;$('btn-step').disabled=false; }
}

async function enterStep(){
  const to = 1 + Math.floor(Math.random()*(pts.length-1));
  const h = $('heur').value;
  log(`A* Step: 0 -> ${to} (${h})`);
  try {
    const res = await fetch('/api/astar_steps', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ start: 0, goal: to, heuristic: h })
    });
    const data = await res.json();
    steps = data.steps;
    stepIdx=0;stepMode=true;
    $('asov').style.display='block';$('step-panel').style.display='block';
    $('btn-astar').disabled=true;$('btn-step').textContent='âœ• ThoĂ¡t Step mode';
    $('btn-step').onclick=exitStep;$('mbadge').textContent='A* STEP';
    renderStep();
  } catch(e) { log('Lá»—i A* Step: '+e.message,'w'); }
}

function exitStep(){
  stepMode=false;$('asov').style.display='none';$('step-panel').style.display='none';
  $('btn-astar').disabled=false;$('btn-step').textContent='â­ Cháº¿ Ä‘á»™ Step-by-step';
  $('btn-step').onclick=enterStep;$('mbadge').textContent='READY';draw();
}

function renderStep(){
  const s=steps[Math.min(stepIdx,steps.length-1)];
  draw(s);
  $('ov-s').textContent=`${s.step}/${steps.length}`;
  $('ov-c').textContent=pts[s.current].name;
  $('ov-g').textContent=s.g.toFixed(1)+' km';
  $('ov-h').textContent=s.h.toFixed(1)+' km';
  $('ov-f').textContent=s.f.toFixed(1)+' km';
  $('ov-o').textContent=s.open.length+' nodes';
  $('ov-cl').textContent=s.closed.length+' nodes';
  $('sinfo').textContent=`BÆ°á»›c ${s.step}: XĂ©t "${pts[s.current].name}"\nf=${s.f.toFixed(0)} = g=${s.g.toFixed(0)} + h=${s.h.toFixed(0)}`;
  $('bprev').disabled=stepIdx<=0;$('bnext').disabled=stepIdx>=steps.length-1;
}
$('bnext').onclick=()=>{if(stepIdx<steps.length-1){stepIdx++;renderStep();}};
$('bprev').onclick=()=>{if(stepIdx>0){stepIdx--;renderStep();}};
$('bfin').onclick=()=>{exitStep();runAStar();};

function runGA(){
  const ps=parseInt($('ps').value), g=parseInt($('gens').value), mr=parseInt($('mr').value), spd=parseInt($('spd').value);
  log(`GA khá»Ÿi Ä‘á»™ng: pop=${ps}, gen=${g}, mut=${mr}%...`);
  $('btn-ga').disabled=true;$('btn-astar').disabled=true;$('btn-gen').disabled=true;
  best=[];conv=[];delivered.clear();animSt=0;
  
  const source = new EventSource(`/api/optimize?pop_size=${ps}&generations=${g}&mut_rate=${mr}&speed=${spd}`);
  source.onmessage = e => {
    const data = JSON.parse(e.data);
    if(data.type==='progress'){
      conv=data.history;best=data.best_order.slice(1,-1);
      $('sd').textContent=data.best_fit.toFixed(1)+' km';
      draw();drawConvergence();
    } else if(data.type==='done'){
      conv=data.history;best=data.best_order.slice(1,-1);
      $('sd').textContent=data.best_dist+' km';
      $('st').textContent=data.best_time;
      $('ss').textContent=(pts.length-1)+' Ä‘iá»ƒm';
      log(`GA hoĂ n táº¥t: ${data.best_dist} km`,'i');
      source.close();
      $('btn-ga').disabled=false;$('btn-astar').disabled=false;$('btn-gen').disabled=false;
      $('btn-cmp').disabled=false;$('btn-exp').disabled=false;
      renderRouteList(); animStep = 0; animateDelivery();
    }
  };
}

function animateDelivery(){
  const ord=[0,...best,0];
  if(animStep>=ord.length){animStep=ord.length;draw();return;}
  if(animStep>0)delivered.add(ord[animStep-1]);
  animStep++;draw();
  if(animStep<ord.length)setTimeout(animateDelivery,350);
}

function drawConvergence(){
  const W=CC.width,H=CC.height;
  cctx.clearRect(0,0,W,H);cctx.fillStyle='#0b0f1a';cctx.fillRect(0,0,W,H);
  if(conv.length<2){
    cctx.fillStyle='rgba(100,116,139,.4)';cctx.font='9px Space Mono';cctx.textAlign='center';
    cctx.fillText('Cháº¡y GA Ä‘á»ƒ xem Ä‘Æ°á»ng há»™i tá»¥',W/2,H/2);return;
  }
  const pd={t:7,r:7,b:18,l:36};
  const cW=W-pd.l-pd.r,cH=H-pd.t-pd.b;
  const mn=Math.min(...conv),mx=Math.max(...conv),rng=mx-mn||1;
  cctx.strokeStyle='rgba(31,45,69,.8)';cctx.lineWidth=.5;
  for(let i=0;i<=4;i++){
    const y=pd.t+cH*(i/4);
    cctx.beginPath();cctx.moveTo(pd.l,y);cctx.lineTo(pd.l+cW,y);cctx.stroke();
    cctx.fillStyle='rgba(100,116,139,.45)';cctx.font='7px Space Mono';cctx.textAlign='right';
    cctx.fillText((mx-(mx-mn)*(i/4)).toFixed(0),pd.l-3,y+3);
  }
  const g2=cctx.createLinearGradient(0,pd.t,0,pd.t+cH);
  g2.addColorStop(0,'rgba(168,255,62,.26)');g2.addColorStop(1,'rgba(168,255,62,0)');
  cctx.beginPath();
  conv.forEach((v,i)=>{const x=pd.l+(i/(conv.length-1))*cW,y=pd.t+cH-((v-mn)/rng)*cH;i===0?cctx.moveTo(x,y):cctx.lineTo(x,y);});
  cctx.lineTo(pd.l+cW,pd.t+cH);cctx.lineTo(pd.l,pd.t+cH);cctx.closePath();cctx.fillStyle=g2;cctx.fill();
  cctx.beginPath();cctx.strokeStyle='#a8ff3e';cctx.lineWidth=1.5;cctx.shadowColor='#a8ff3e';cctx.shadowBlur=3;
  conv.forEach((v,i)=>{const x=pd.l+(i/(conv.length-1))*cW,y=pd.t+cH-((v-mn)/rng)*cH;i===0?cctx.moveTo(x,y):cctx.lineTo(x,y);});
  cctx.stroke();cctx.shadowBlur=0;
}

function renderRouteList(){
  const el=$('rlist');el.innerHTML='';
  const ord=[0,...best,0];
  ord.forEach((idx,step)=>{
    const p=pts[idx],div=document.createElement('div');
    div.className='ri';div.style.animationDelay=(step*35)+'ms';
    const se=document.createElement('div');se.className='rstep'+(p.id===0?' dep':'');
    se.textContent=step===0||step===ord.length-1?'?':step;div.appendChild(se);
    const nm=document.createElement('span');nm.style.fontSize='10px';nm.textContent=p.name;div.appendChild(nm);
    el.appendChild(div);
  });
}

function routeDistanceFromMatrix(order) {
  return order.slice(0, -1).reduce((sum, idx, i) => sum + (dm[idx]?.[order[i + 1]] || 0), 0);
}

function formatMinutes(totalMinutes) {
  const h = Math.floor(totalMinutes / 60), m = Math.floor(totalMinutes % 60);
  return `${h}h ${m}m`;
}

function routeNames(order) {
  return order.map(idx => pts[idx]?.name || `P${idx}`).join(' ? ');
}

function fillComparisonTable() {
  if(!best.length) return;
  const gaOrder = [0, ...best, 0];
  const baseOrder = [0, ...pts.slice(1).map((_, i) => i + 1), 0];
  const distGA = routeDistanceFromMatrix(gaOrder);
  const distBase = routeDistanceFromMatrix(baseOrder);
  const speed = parseInt($('spd').value);
  const timeGA = $('st').textContent;
  const timeBase = formatMinutes((distBase / speed) * 60);
  
  const cbody = $('cbody');
  cbody.innerHTML = `
    <tr><td>Tá»•ng quĂ£ng Ä‘Æ°á»ng</td><td class="r">${distBase.toFixed(1)} km</td><td class="g">${distGA.toFixed(1)} km</td><td class="g">-${(distBase-distGA).toFixed(1)} km</td></tr>
    <tr><td>Thá»i gian Æ°á»›c tĂ­nh</td><td>${timeBase}</td><td>${timeGA}</td><td class="g">Nhanh hÆ¡n</td></tr>
    <tr><td>Äá»™ phá»©c táº¡p</td><td>O(n)</td><td>O(gen * pop)</td><td>N/A</td></tr>
  `;
  
  const imp = distBase > 0 ? ((distBase - distGA) / distBase * 100).toFixed(1) : '0.0';
  $('cpct').textContent = imp + '%';
  $('si').textContent = imp + '%';

  $('route-base-title').textContent = `Lá»™ trĂ¬nh tuáº§n tá»± Â· ${distBase.toFixed(1)} km`;
  $('route-ga-title').textContent = `Lá»™ trĂ¬nh A* + GA Â· ${distGA.toFixed(1)} km`;
  $('route-base-text').textContent = routeNames(baseOrder);
  $('route-ga-text').textContent = routeNames(gaOrder);

  const gaBest = distGA <= distBase;
  $('route-base-card').classList.toggle('best', !gaBest);
  $('route-ga-card').classList.toggle('best', gaBest);
  $('route-base-tag').textContent = gaBest ? 'TUYáº¾N Äá»I CHIáº¾U' : 'Tá»I Æ¯U HÆ N';
  $('route-ga-tag').textContent = gaBest ? 'Tá»I Æ¯U HÆ N' : 'TUYáº¾N Äá»I CHIáº¾U';
}

function showModal(){ 
  fillComparisonTable();
  $('moverlay').classList.add('show'); 
}
function closeModal(){ $('moverlay').classList.remove('show'); }
function exportPNG(){ log('TĂ­nh nÄƒng Xuáº¥t PNG Ä‘ang Ä‘Æ°á»£c cáº­p nháº­t...'); closeModal(); }

$('np').oninput=e=>$('nv').textContent=e.target.value;
$('spd').oninput=e=>$('sv').textContent=e.target.value;
$('ps').oninput=e=>$('pv').textContent=e.target.value;
$('gens').oninput=e=>$('gv').textContent=e.target.value;
$('mr').oninput=e=>$('mv').textContent=e.target.value+'%';
$('btn-gen').onclick=gen;
$('btn-astar').onclick=runAStar;
$('btn-step').onclick=enterStep;
$('btn-ga').onclick=runGA;
$('btn-cmp').onclick=showModal;
$('btn-exp').onclick=exportPNG;

window.addEventListener('load',()=>{
  resizeCanvas(); log('DelivRoute v2.0 sáºµn sĂ ng','i');
  setTimeout(()=>loadPreset('mixed'),200);
});
</script>
</body>
</html>
"""

app = Flask(__name__)

PYTHON_BACKEND_OVERRIDE = r"""
<script>
(function(){
  'use strict';

  const PY_SCALE = 0.04;
  let pyDM = [];
  let backendObstacles = [];
  let backendGraphMode = 'road';
  let backendGenVersion = 0;
  window.__userChangedBackendConfig = false;
  window.__backendOverrideStartedAt = Date.now();
  const CP1252_REVERSE = {
    0x20AC: 0x80, 0x201A: 0x82, 0x0192: 0x83, 0x201E: 0x84, 0x2026: 0x85,
    0x2020: 0x86, 0x2021: 0x87, 0x02C6: 0x88, 0x2030: 0x89, 0x0160: 0x8A,
    0x2039: 0x8B, 0x0152: 0x8C, 0x017D: 0x8E, 0x2018: 0x91, 0x2019: 0x92,
    0x201C: 0x93, 0x201D: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97,
    0x02DC: 0x98, 0x2122: 0x99, 0x0161: 0x9A, 0x203A: 0x9B, 0x0153: 0x9C,
    0x017E: 0x9E, 0x0178: 0x9F
  };

  function decodeMojibakeOnce(input){
    if(typeof input !== 'string' || input.length === 0) return input;
    const bytes = [];
    for(const ch of input){
      const code = ch.codePointAt(0);
      if(code <= 0xFF){
        bytes.push(code);
        continue;
      }
      const mapped = CP1252_REVERSE[code];
      if(mapped == null) return input;
      bytes.push(mapped);
    }
    try{
      return new TextDecoder('utf-8', {fatal:true}).decode(new Uint8Array(bytes));
    }catch(_error){
      return input;
    }
  }

  function normalizeBrokenText(input){
    if(typeof input !== 'string') return input;
    let out = input;
    for(let i=0;i<3;i++){
      const next = decodeMojibakeOnce(out);
      if(next === out) break;
      out = next;
    }
    return out;
  }

  function repairDomText(root=document.body){
    if(!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const original = node.nodeValue;
      const fixed = normalizeBrokenText(original);
      if(fixed !== original) node.nodeValue = fixed;
    });
  }

  const originalAlert = window.alert?.bind(window);
  if(originalAlert){
    window.alert = function(message){
      return originalAlert(normalizeBrokenText(String(message)));
    };
  }

  function markUserConfigChanged(){
    window.__userChangedBackendConfig = true;
  }

  function installConfigChangeGuards(){
    ['np','spd','ps','gens','mr','astarGraph','vehicles','capacity','obstacles'].forEach(id=>{
      const element = $(id);
      if(!element || element.__backendGuardInstalled) return;
      element.__backendGuardInstalled = true;
      element.addEventListener('input', markUserConfigChanged);
      element.addEventListener('change', markUserConfigChanged);
    });
  }

  function addUpgradeControlsV2(){
    const setupBody = document.querySelector('#dr-setup .drbody');
    if(!setupBody) return;
    setupBody.style.overflowY = 'auto';
    setupBody.style.minHeight = '0';
    const groups = Array.from(setupBody.querySelectorAll(':scope > .DG'));
    const mapGroup = groups[1];
    const gaGroup = groups[2];
    if(!mapGroup || !gaGroup) return;

    const mapLabel = mapGroup.querySelector('.DGL');
    if(mapLabel) mapLabel.textContent = '1. Thi\u1ebft l\u1eadp b\u1ea3n \u0111\u1ed3';

    const createMapButton = mapGroup.querySelector('button.Btn.Bc') ||
      Array.from(mapGroup.querySelectorAll('button')).find(button => /tao|táº¡o|gen|map/i.test(button.textContent || ''));
    const speedControl = $('spd')?.closest('.DC');
    const simSpeedControl = $('aspd')?.closest('.DC');
    const heuristicControl = $('heur')?.closest('.DC');
    const vehicleControl = $('vehicles')?.closest('.DC');
    const capacityControl = $('capacity')?.closest('.DC');
    const timeWindowToggle = $('timeWindowsToggle');

    if(createMapButton && !document.getElementById('obstacles')){
      const obstacleControl = document.createElement('div');
      obstacleControl.className = 'DC';
      obstacleControl.innerHTML = `
        <div class="DCL">V\u1eadt c\u1ea3n / \u0111\u01b0\u1eddng c\u1ea5m <b id="obsv">0</b></div>
        <input type="range" id="obstacles" min="0" max="3" value="0" oninput="$('obsv').textContent=this.value"/>
      `;
      mapGroup.insertBefore(obstacleControl, createMapButton);
    }

    const hasReworkedGroups = Boolean(document.getElementById('vehicles')) && Boolean(document.getElementById('astarGraph'));
    if(hasReworkedGroups){
      const vehicleLabel = $('vehicles')?.closest('.DC')?.querySelector('.DCL');
      if(vehicleLabel && /GA\/A\*\+GA/i.test(vehicleLabel.textContent || '')){
        const badgeId = vehicleLabel.querySelector('b')?.id || 'vehs_v';
        vehicleLabel.innerHTML = 'S\u1ed1 xe giao h\u00e0ng <b id="' + badgeId + '">' + ($('vehicles')?.value || '1') + '</b>';
      }
      if(createMapButton) createMapButton.textContent = 'T\u1ea1o / c\u1eadp nh\u1eadt b\u1ea3n \u0111\u1ed3';
      return;
    }

    if(createMapButton) {
      [speedControl, simSpeedControl, heuristicControl].forEach(control => control && control.remove());
      createMapButton.textContent = 'T\u1ea1o / c\u1eadp nh\u1eadt b\u1ea3n \u0111\u1ed3';
    }

    const astarGroup = document.createElement('div');
    astarGroup.className = 'DG';
    astarGroup.innerHTML = `
      <div class="DGL">2. Thu\u1eadt to\u00e1n A*</div>
      <div class="DC">
        <div class="DCL">M\u00f4 h\u00ecnh \u0111\u01b0\u1eddng \u0111i</div>
        <div class="DCL" style="font-size:11px;color:var(--t1);font-weight:600;">M\u1ea1ng \u0111\u01b0\u1eddng / h\u1ebbm th\u00e0nh ph\u1ed1 (m\u1eb7c \u0111\u1ecbnh)</div>
        <input type="hidden" id="astarGraph" value="road"/>
        <input type="hidden" id="heur" value="euclidean"/>
      </div>
    `;

    const constraintGroup = document.createElement('div');
    constraintGroup.className = 'DG';
    constraintGroup.innerHTML = `
      <div class="DGL">3. R\u00e0ng bu\u1ed9c giao h\u00e0ng</div>
    `;
    if(speedControl) constraintGroup.insertBefore(speedControl, constraintGroup.children[1]);
    if(simSpeedControl) constraintGroup.insertBefore(simSpeedControl, constraintGroup.children[2] || null);

    if(vehicleControl){
      const vehicleLabel = vehicleControl.querySelector('.DCL');
      const badgeId = vehicleLabel?.querySelector('b')?.id || 'vehs_v';
      if(vehicleLabel) vehicleLabel.innerHTML = 'S\u1ed1 xe giao h\u00e0ng <b id="' + badgeId + '">' + ($('vehicles')?.value || '1') + '</b>';
      constraintGroup.appendChild(vehicleControl);
    }else{
      const newVehicleControl = document.createElement('div');
      newVehicleControl.className = 'DC';
      newVehicleControl.innerHTML = `
        <div class="DCL">S\u1ed1 xe giao h\u00e0ng <b id="vehs_v">1</b></div>
        <input type="range" id="vehicles" min="1" max="5" value="1" oninput="$('vehs_v').textContent=this.value"/>
      `;
      constraintGroup.appendChild(newVehicleControl);
    }

    if(capacityControl){
      const capacityLabel = capacityControl.querySelector('.DCL');
      const badgeId = capacityLabel?.querySelector('b')?.id || 'cap_v';
      if(capacityLabel) capacityLabel.innerHTML = 'T\u1ea3i tr\u1ecdng m\u1ed7i xe <b id="' + badgeId + '">' + ($('capacity')?.value || '24') + '</b>';
      constraintGroup.appendChild(capacityControl);
    }else{
      const newCapacityControl = document.createElement('div');
      newCapacityControl.className = 'DC';
      newCapacityControl.innerHTML = `
        <div class="DCL">T\u1ea3i tr\u1ecdng m\u1ed7i xe <b id="cap_v">24</b></div>
        <input type="range" id="capacity" min="8" max="60" value="24" step="2" oninput="$('cap_v').textContent=this.value"/>
      `;
      constraintGroup.appendChild(newCapacityControl);
    }

    if(timeWindowToggle){
      timeWindowToggle.classList.remove('Bc');
      timeWindowToggle.classList.add('Bd');
      timeWindowToggle.textContent = timeWindowToggle.dataset.on === '1' ? 'D\u00f9ng khung gi\u1edd giao' : 'B\u1ecf khung gi\u1edd giao';
      timeWindowToggle.onclick = function(){
        this.dataset.on=this.dataset.on==='1'?'0':'1';
        this.textContent=this.dataset.on==='1'?'D\u00f9ng khung gi\u1edd giao':'B\u1ecf khung gi\u1edd giao';
      };
      constraintGroup.appendChild(timeWindowToggle);
    }else{
      const newTimeToggle = document.createElement('button');
      newTimeToggle.className = 'Btn Bd';
      newTimeToggle.id = 'timeWindowsToggle';
      newTimeToggle.dataset.on = '1';
      newTimeToggle.textContent = 'D\u00f9ng khung gi\u1edd giao';
      newTimeToggle.onclick = function(){
        this.dataset.on=this.dataset.on==='1'?'0':'1';
        this.textContent=this.dataset.on==='1'?'D\u00f9ng khung gi\u1edd giao':'B\u1ecf khung gi\u1edd giao';
      };
      constraintGroup.appendChild(newTimeToggle);
    }

    setupBody.insertBefore(astarGroup, gaGroup);
    setupBody.insertBefore(constraintGroup, gaGroup);
  }

  function syncVehicleControlsForMode(mode){
    const algorithmUsesVehicles = Number(mode) === 0 || Number(mode) === 2 || Number(mode) === 3;
    ['vehicles','capacity','timeWindowsToggle'].forEach(id => {
      const element = $(id);
      if(!element) return;
      element.disabled = !algorithmUsesVehicles;
      const group = element.closest('.DC') || element;
      group.style.opacity = algorithmUsesVehicles ? '1' : '.45';
      group.title = algorithmUsesVehicles
        ? 'Dung cho GA hoac A*+GA khi chia nhieu xe'
        : 'A* tuan tu va tuyen ban dau chi la mot thu tu tham chieu, khong chia xe';
    });
  }

  const kmToCost = km => km / PY_SCALE;
  const costToKm = cost => cost * PY_SCALE;

  function resetRunState(){
    dm=[]; conv=[]; doneSet.clear(); vehs=[]; animDist=0; animSeg=0;
    results={
      0:{dist:0,time:0,order:[],roadPaths:[]},
      1:{dist:0,time:0,order:[],roadPaths:[]},
      2:{dist:0,time:0,order:[],roadPaths:[]},
      3:{dist:0,time:0,order:[],roadPaths:[]},
      4:{dist:0,time:0,order:[],roadPaths:[]}
    };
    setText('sbase','—');
    if(animRAF){cancelAnimationFrame(animRAF);animRAF=null;}
  }

  function mapBackendObstacle(obstacle){
    const mapX = x => 160 + (Number(x) / 100) * (CW - 320);
    const mapY = y => 160 + (Number(y) / 100) * (CH - 320);
    const x0 = mapX(obstacle.x_min);
    const y0 = mapY(obstacle.y_min);
    const x1 = mapX(obstacle.x_max);
    const y1 = mapY(obstacle.y_max);
    return {
      id: obstacle.id,
      name: normalizeBrokenText(obstacle.name || `Vung cam ${obstacle.id}`),
      x: Math.min(x0, x1),
      y: Math.min(y0, y1),
      w: Math.abs(x1 - x0),
      h: Math.abs(y1 - y0)
    };
  }

  function roadGraphPayload(){
    const buildingObstacles = buildings.map((building, index) => ({
      id:`building-${index}`,
      x_min:building.x,
      y_min:building.y,
      x_max:building.x + building.w,
      y_max:building.y + building.h,
      name:'NhĂ  / cĂ´ng trĂ¬nh'
    }));
    const waterObstacles = waterBodies.map((water, index) => ({
      id:`water-${index}`,
      x_min:water.x,
      y_min:water.y,
      x_max:water.x + water.w,
      y_max:water.y + water.h,
      name:'VĂ¹ng nÆ°á»›c'
    }));
    buildingObstacles.forEach(obstacle => { obstacle.name = 'Nha / cong trinh'; });
    waterObstacles.forEach(obstacle => { obstacle.name = 'Vung nuoc'; });
    return {
      graph_mode:'road',
      points:pts.map(point => ({
        id:point.id,
        original_id:point.id,
        x:point.x,
        y:point.y,
        name:point.name,
        isDepot:!!point.isDepot,
        nodeId:point.nodeId,
        demand:point.demand || 0,
        time_window:point.time_window || null,
        undeliverable: backendObstacles.some(obstacle =>
          !point.isDepot &&
          point.x >= obstacle.x &&
          point.x <= obstacle.x + obstacle.w &&
          point.y >= obstacle.y &&
          point.y <= obstacle.y + obstacle.h
        )
      })),
      road_nodes:roadNodes.map(node => ({id:node.id, x:node.x, y:node.y})),
      road_edges:roadEdges.map(edge => ({a:edge.a, b:edge.b})),
      obstacles:[
        ...backendObstacles.map(obstacle => ({
          id:obstacle.id,
          x_min:obstacle.x,
          y_min:obstacle.y,
          x_max:obstacle.x + obstacle.w,
          y_max:obstacle.y + obstacle.h,
          name:obstacle.name
        })),
        ...buildingObstacles,
        ...waterObstacles
      ]
    };
  }

  function mapBackendPointV2(point, index){
    const rawX = 160 + (Number(point.x) / 100) * (CW - 320);
    const rawY = 160 + (Number(point.y) / 100) * (CH - 320);
    const nodeId = nearestNode(rawX, rawY);
    const node = roadNodes[nodeId];
    return {
      id:index,
      x:node.x,
      y:node.y,
      name:index===0 ? 'KHO H\u00c0NG' : (point.name || `\u0110i\u1ec3m giao ${index}`),
      isDepot:index===0,
      nodeId,
      demand:point.demand || 0,
      time_window:point.time_window || null
    };
  }

  function normalizeUiLabels(){
    pts.forEach(point => {
      point.name = normalizeBrokenText(point.name);
    });
    backendObstacles.forEach(obstacle => {
      obstacle.name = normalizeBrokenText(obstacle.name);
    });
  }

  function getSelectedGraphMode(){
    return 'road';
  }

  async function syncBackendRoadGraph(requestedMode){
    const graphMode = requestedMode || getSelectedGraphMode();
    if(graphMode !== 'road'){
      backendGraphMode = graphMode;
      return;
    }
    const payload = roadGraphPayload();
    payload.graph_mode = 'road';
    const response = await fetch('/api/sync_road_graph', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    const data = await response.json();
    if(data.status !== 'success') throw new Error(normalizeBrokenText(data.message || 'KhĂ´ng Ä‘á»“ng bá»™ Ä‘Æ°á»£c Ä‘á»“ thá»‹ máº¡ng Ä‘Æ°á»ng'));
    backendGraphMode = data.graph_mode || 'road';
  }

  function drawBackendObstacles(){
    if(!backendObstacles.length || !ctx || !cv) return;
    ctx.save();
    ctx.setTransform(cam.s,0,0,cam.s,cam.x,cam.y);
    backendObstacles.forEach(ob=>{
      ctx.fillStyle='rgba(255,76,76,.22)';
      ctx.fillRect(ob.x, ob.y, ob.w, ob.h);
      ctx.strokeStyle='rgba(255,123,53,.9)';
      ctx.lineWidth=2;
      ctx.setLineDash([10,6]);
      ctx.strokeRect(ob.x, ob.y, ob.w, ob.h);
      ctx.setLineDash([]);
      ctx.fillStyle='rgba(255,230,180,.9)';
      ctx.font='bold 9px Space Mono';
      ctx.textAlign='center';
      ctx.fillText(ob.name, ob.x + ob.w / 2, ob.y + ob.h / 2);
    });
    ctx.restore();
  }

  function drawBackendGrid(){
    if(backendGraphMode !== 'grid' || !ctx || !cv) return;
    ctx.save();
    ctx.setTransform(cam.s,0,0,cam.s,cam.x,cam.y);
    ctx.strokeStyle='rgba(0,212,255,.10)';
    ctx.lineWidth=1;
    for(let value=0; value<=100; value+=10){
      const x = 160 + (value / 100) * (CW - 320);
      const y = 160 + (value / 100) * (CH - 320);
      ctx.beginPath();ctx.moveTo(x,160);ctx.lineTo(x,CH-160);ctx.stroke();
      ctx.beginPath();ctx.moveTo(160,y);ctx.lineTo(CW-160,y);ctx.stroke();
    }
    ctx.restore();
  }

  function routeKm(order){
    let total = 0;
    for(let i=0;i<order.length-1;i++) total += Number(pyDM[order[i]][order[i+1]] || 0);
    return total;
  }

  function directRouteKm(order){
    let total = 0;
    for(let i=0;i<order.length-1;i++){
      const from = pts[order[i]];
      const to = pts[order[i + 1]];
      if(from && to) total += (Math.abs(to.x - from.x) + Math.abs(to.y - from.y)) * PY_SCALE;
    }
    return total;
  }

  function lineHitsRect(a, b, rect, padding=10){
    const left = rect.x - padding;
    const right = rect.x + rect.w + padding;
    const top = rect.y - padding;
    const bottom = rect.y + rect.h + padding;
    if(Math.abs(a.y - b.y) < 0.001){
      const minX = Math.min(a.x, b.x);
      const maxX = Math.max(a.x, b.x);
      return a.y >= top && a.y <= bottom && maxX >= left && minX <= right;
    }
    if(Math.abs(a.x - b.x) < 0.001){
      const minY = Math.min(a.y, b.y);
      const maxY = Math.max(a.y, b.y);
      return a.x >= left && a.x <= right && maxY >= top && minY <= bottom;
    }
    return false;
  }

  function routeHitsObstacles(points){
    for(let i=0;i<points.length-1;i++){
      if(backendObstacles.some(obstacle => lineHitsRect(points[i], points[i + 1], obstacle))) return true;
    }
    return false;
  }

  function roadLikeBaselineSegment(from, to, index){
    const horizontalFirst = [from, {x:to.x, y:from.y}, to];
    const verticalFirst = [from, {x:from.x, y:to.y}, to];
    const preferred = index % 2 === 0 ? horizontalFirst : verticalFirst;
    const alternate = index % 2 === 0 ? verticalFirst : horizontalFirst;
    return routeHitsObstacles(preferred) && !routeHitsObstacles(alternate) ? alternate : preferred;
  }

  function roadLikeBaselineWaypoints(order){
    const waypoints = [];
    for(let i=0;i<order.length-1;i++){
      const from = pts[order[i]];
      const to = pts[order[i + 1]];
      if(!from || !to) continue;
      const segment = roadLikeBaselineSegment(from, to, i);
      segment.forEach((point, pointIndex) => {
        if(i > 0 && pointIndex === 0) return;
        waypoints.push(point);
      });
    }
    return waypoints.length >= 2 ? waypoints : order.map(index => pts[index]).filter(Boolean);
  }

  function getUndeliverablePoints(){
    return pts.filter(point => point && point.id !== 0 && point.undeliverable);
  }

  function assertRunnableMap(){
    const blocked = getUndeliverablePoints();
    if(!blocked.length) return true;
    const preview = blocked.slice(0, 3).map(point => point.name || `P${point.id}`).join(', ');
    const tail = blocked.length > 3 ? ` va ${blocked.length - 3} diem khac` : '';
    const message = `Co ${blocked.length} diem giao nam trong khu vuc cam: ${preview}${tail}. Hay tao ban do moi hoac chinh lai vung cam.`;
    setText('hbadge','BLOCKED');
    setStatus(message);
    alert(message);
    return false;
  }

  function getRoadPath(src, dst_id) {
    if (backendGraphMode === 'road') {
      return{path:[],cost:Infinity,found:false};
    }
    return [src, dst_id];
  }

  function visualPaths(order){
    const paths = [];
    for(let i=0;i<order.length-1;i++) paths.push(getRoadPath(order[i], order[i+1]));
    return paths;
  }

  function backendCoordToCanvas(coord){
    if(backendGraphMode === 'road'){
      return {
        id: coord.id,
        x: clamp(Number(coord.x), 0, CW),
        y: clamp(Number(coord.y), 0, CH)
      };
    }
    return {
      id: coord.id,
      x: 160 + (Number(coord.x) / 100) * (CW - 320),
      y: 160 + (Number(coord.y) / 100) * (CH - 320)
    };
  }

  function backendSegmentWaypoints(segment, segmentIndex){
    const mapped = (segment.coords || [])
      .map(backendCoordToCanvas)
      .filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
    if(!mapped.length) return [];
    if(pts[segment.from]) mapped[0] = {...pts[segment.from], id:pts[segment.from].nodeId, deliveryId:segment.from};
    if(pts[segment.to]) mapped[mapped.length - 1] = {...pts[segment.to], id:pts[segment.to].nodeId, deliveryId:segment.to};
    const deduped = mapped.filter((point, index, list) => {
      if(index === 0) return true;
      const prev = list[index - 1];
      return Math.abs(point.x - prev.x) > 0.5 || Math.abs(point.y - prev.y) > 0.5;
    });
    return segmentIndex === 0 ? deduped : deduped.slice(1);
  }

  function makeVehicleFromWaypoints(order, waypoints, col, label){
    if(backendGraphMode !== 'road' && waypoints.length < 2 && order.length) {
      const fallbackPaths = visualPaths(order);
      waypoints = [];
      fallbackPaths.forEach((path, pathIndex) => {
        path.forEach((nodeId, nodeIndex) => {
          if(pathIndex > 0 && nodeIndex === 0) return;
          const node = roadNodes[nodeId];
          if(node) waypoints.push(node);
        });
      });
    }
    if(backendGraphMode !== 'road' && waypoints.length < 2 && order.length) waypoints = order.map(index => pts[index]).filter(Boolean);
    if(backendGraphMode === 'road' && waypoints.length < 2) {
      throw new Error('Thieu route path tu backend cho mang duong/hem. Khong ve noi tat qua nha.');
    }
    if(waypoints.length < 2) {
      waypoints = [{x:CW / 2, y:CH / 2, id:-1}, {x:CW / 2 + 1, y:CH / 2 + 1, id:-2}];
    }
    return {
      on:true,wpIdx:0,t:0,
      x:waypoints[0].x,y:waypoints[0].y,
      ang:0,trail:[],
      waypoints,order,paths:[],
      col,label,
      deliveredPts:new Set(),
      totalDist:0,distKm:0,
      wheelRot:0,
      nextPtIdx:1
    };
  }

  function routeDistanceKm(route){
    let total = 0;
    for(let i=0;i<route.length-1;i++) total += Number(pyDM[route[i]]?.[route[i+1]] || 0);
    return total;
  }

  function decorateVehicle(vehicle, route, index){
    vehicle.routeIndex = index;
    vehicle.assignedStops = route.filter(point => point > 0);
    vehicle.totalKm = routeDistanceKm(route);
    return vehicle;
  }

  function makeDirectBaselineVehicle(order, km){
    const waypoints = roadLikeBaselineWaypoints(order);
    const vehicle = decorateVehicle(makeVehicleFromWaypoints(order, waypoints, '#facc15', 'TUYEN TUAN TU BAN DAU'), order, 0);
    vehicle.totalKm = km;
    vehicle.algorithmKey = 'baseline';
    vehicle.algorithmLabel = 'Tuyen ban dau';
    vehicle.shortLabel = 'Xe 1';
    return vehicle;
  }

  function updateVehicleProgress(){
    vehs.forEach(vehicle => {
      const nextIndex = vehicle.order.findIndex((point, index) => index > 0 && point > 0 && !vehicle.deliveredPts.has(point));
      vehicle.nextPtIdx = nextIndex === -1 ? vehicle.order.length - 1 : nextIndex;
    });
  }

  function formatDurationMinutes(totalMinutes){
    const mins = Math.max(0, Math.round(Number(totalMinutes) || 0));
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return `${h}h${m}m`;
  }

  function getCompareSeries(){
    return [
      {id:'baseline', index:3, title:'Tuyen ban dau', color:'#facc15'},
      {id:'astar', index:1, title:'A*', color:'#ff7b35'},
      {id:'ga_only', index:2, title:'GA', color:'#a78bfa'},
      {id:'ga_opt', index:0, title:'A* + GA', color:'#7ee787'}
    ];
  }

  function bestSeriesBy(series, selector){
    const valid = series.filter(item => item && item.result && item.result.dist > 0);
    if(!valid.length) return null;
    return valid.reduce((best, current) => selector(current.result) < selector(best.result) ? current : best);
  }

  function renderCompareIndicators(){
    const section = $('cmp-section');
    const quick = $('cmp-quick');
    const panel = $('cpanel');
    if(!quick && !panel) return;

    const series = getCompareSeries().map(meta => ({...meta, result: results[meta.index] || null}));
    const complete = series.filter(item => item.result && item.result.order && item.result.order.length > 0);
    const baseline = complete.find(item => item.id === 'baseline') || complete.find(item => item.id === 'astar');
    const bestKm = bestSeriesBy(complete, result => result.dist);
    const bestTime = bestSeriesBy(complete, result => result.time || Number.MAX_SAFE_INTEGER);
    const spd = +($('spd')?.value || 40);
    const rowHtml = complete.map(item => {
      const km = costToKm(item.result.dist || 0);
      const mins = Number(item.result.time || Math.round((km / spd) * 60));
      const stopCount = Math.max(0, (item.result.order?.length || 2) - 2);
      const improve = baseline && baseline !== item && baseline.result?.dist > 0
        ? ((baseline.result.dist - item.result.dist) / baseline.result.dist * 100)
        : null;
      const improveLabel = improve != null ? `${improve >= 0 ? 'â†“' : 'â†‘'} ${Math.abs(improve).toFixed(1)}%` : 'â€”';
      const badges = [
        bestKm && bestKm.id === item.id ? '<span style="color:#7ee787">tá»‘t nháº¥t km</span>' : '',
        bestTime && bestTime.id === item.id ? '<span style="color:#00d4ff">nhanh nháº¥t</span>' : ''
      ].filter(Boolean).join(' Â· ');
      return `
        <div style="border:1px solid rgba(100,116,139,.35);border-left:3px solid ${item.color};border-radius:8px;padding:8px 10px;background:rgba(15,23,42,.35);">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">
            <b style="color:${item.color};font-size:11px;font-family:var(--fm,Consolas,monospace)">${item.title}</b>
            <span style="font-size:10px;color:var(--t2,#94a3b8)">${km.toFixed(1)} km</span>
          </div>
          <div style="display:flex;justify-content:space-between;gap:8px;font-size:10px;color:var(--t1,#dff0e8);line-height:1.6;">
            <span>${formatDurationMinutes(mins)}</span>
            <span>${stopCount} Ä‘iá»ƒm</span>
            <span>${improveLabel}</span>
          </div>
          ${badges ? `<div style="margin-top:5px;font-size:9px;color:var(--t2,#94a3b8)">${badges}</div>` : ''}
        </div>
      `;
    }).join('');

    if(quick){
      quick.innerHTML = complete.length
        ? `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px">${rowHtml}</div>`
        : '<div style="color:var(--t2);font-size:10px;">ChÆ°a cĂ³ dá»¯ liá»‡u so sĂ¡nh 3 mĂ´ hĂ¬nh.</div>';
    }
    if(section) section.style.display = complete.length ? 'block' : 'none';

    if(panel){
      panel.innerHTML = complete.length
        ? `<div style="display:grid;grid-template-columns:1fr;gap:8px">${rowHtml}</div>`
        : '<div style="color:var(--t2);font-size:10px;font-family:var(--fm);padding-top:6px;">Cháº¡y cháº¿ Ä‘á»™ so sĂ¡nh Ä‘á»ƒ xem chá»‰ sá»‘ lá»™ trĂ¬nh.</div>';
    }
  }

  function refreshCompareUiShell(){
    const sequentialButton = $('mb1');
    if(sequentialButton) sequentialButton.innerHTML = '<span class="mic">â˜…</span>TUYEN TUAN TU BAN DAU';
    const modeButton = $('mb3');
    if(modeButton) modeButton.innerHTML = '<span class="mic">â¡</span>SO SĂNH A*, GA, A*+GA';
    const compareButton = $('fp-cmp');
    if(compareButton) compareButton.textContent = 'â¡ SO SĂNH 3 MĂ” HĂŒNH';
    const modalTitle = document.querySelector('#modal-overlay .modal h3');
    if(modalTitle) modalTitle.textContent = 'â¡ So sĂ¡nh chi tiáº¿t: A*, GA, A*+GA';
    const tableHead = document.querySelector('#modal-overlay .modal table thead');
    if(tableHead){
      tableHead.innerHTML = '<tr><th>Chá»‰ sá»‘</th><th>A*</th><th>GA</th><th>A*+GA</th><th>Káº¿t luáº­n</th></tr>';
    }
  }
  refreshCompareUiShell = function(){
    const sequentialButton = $('mb1');
    const modeButton = $('mb3');
    const compareButton = $('fp-cmp');
    if(sequentialButton) sequentialButton.innerHTML = '<span class="mic">*</span>A*';
    if(modeButton) modeButton.innerHTML = '<span class="mic">!</span>SO S\u00c1NH BAN \u0110\u1ea6U, A*, GA, A*+GA';
    if(compareButton) compareButton.textContent = 'SO S\u00c1NH 4 M\u00d4 H\u00ccNH';
    const modesContainer = document.getElementById('modes');
    if(modesContainer && !document.getElementById('mb4')){
      const baselineButton = document.createElement('div');
      baselineButton.className = 'modeBtn panel';
      baselineButton.id = 'mb4';
      baselineButton.innerHTML = '<span class="mic">⊕</span>TUYEN TUAN TU BAN DAU';
      baselineButton.onclick = function(){ setMode(4); };
      const compareModeButton = document.getElementById('mb3');
      if(compareModeButton && compareModeButton.parentNode === modesContainer){
        compareModeButton.insertAdjacentElement('afterend', baselineButton);
      }else{
        modesContainer.appendChild(baselineButton);
      }
    }
    const activeModalTitle = document.querySelector('#moverlay .modal h3, #modal-overlay .modal h3');
    if(activeModalTitle) activeModalTitle.textContent = 'So s\u00e1nh chi ti\u1ebft: Tuy\u1ebfn ban \u0111\u1ea7u, A*, GA, A*+GA';
    const activeTableHead = document.querySelector('#moverlay .modal table thead, #modal-overlay .modal table thead');
    if(activeTableHead){
      activeTableHead.innerHTML = '<tr><th>Ch\u1ec9 s\u1ed1</th><th>Ban \u0111\u1ea7u</th><th>A*</th><th>GA</th><th>A*+GA</th><th>K\u1ebft lu\u1eadn</th></tr>';
    }
  };

  let baseVhudBottomPx = null;
  function adjustVehicleHudPosition(forceCompareMode){
    const hud = $('vhud');
    if(!hud) return;
    if(baseVhudBottomPx == null){
      const currentBottom = parseFloat(getComputedStyle(hud).bottom || '100');
      baseVhudBottomPx = Number.isFinite(currentBottom) ? currentBottom : 100;
    }
    const inCompare = forceCompareMode != null
      ? !!forceCompareMode
      : (typeof MODE === 'number' && MODE === 3);
    const targetBottom = inCompare ? (baseVhudBottomPx * 1.5) : baseVhudBottomPx;
    hud.style.bottom = `${Math.round(targetBottom)}px`;
  }

  function renderVehicleRoutes(){
    const el = $('rlist');
    if(!el) return;
    el.style.display = 'block';
    el.style.visibility = 'visible';
    el.style.opacity = '1';
    if(!vehs.length){
      const activeResult = (results[MODE] && results[MODE].order && results[MODE].order.length)
        ? results[MODE]
        : (results[0] && results[0].order && results[0].order.length ? results[0] : null);
      if(activeResult && typeof renderRouteList === 'function'){
        renderRouteList(activeResult.order);
      }else{
        const status = (document.getElementById('topstatus')?.textContent || '').trim();
        const msg = status && /loi|error|blocked|khong/i.test(status)
          ? status
          : 'Chua co du lieu lo trinh. Hay chay thuat toan truoc.';
        el.innerHTML = `<div style="color:var(--t2);font-size:12px;text-align:center;padding:18px 8px;line-height:1.6;">${msg}</div>`;
      }
      return;
    }
    el.innerHTML = '';
    el.scrollTop = 0;
    const grouped = new Map();
    vehs.forEach(vehicle => {
      const key = vehicle.algorithmKey || 'single';
      if(!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(vehicle);
    });

    const groupDefs = MODE === 3
      ? [
          {key:'baseline', title:'Tuyen tuan tu ban dau'},
          {key:'astar_base', title:'Lo trinh A* tuan tu'},
          {key:'ga_only', title:'Lo trinh GA'},
          {key:'ga_opt', title:'Lo trinh A* + GA'}
        ]
      : [
          {key:'baseline', title:'Tuyen tuan tu ban dau'},
          {key:'single', title:'Lo trinh toi uu'}
        ];

    let renderedGroups = 0;
    const appendGroupCard = (title, list) => {
      if(!list || !list.length) return false;
      const card = document.createElement('div');
      card.className = 'RI';
      card.style.display = 'block';
      card.style.opacity = '1';
      card.style.animation = 'none';
      card.style.borderLeft = `3px solid ${list[0].col}`;
      card.style.padding = '8px 10px 8px 10px';
      card.style.marginBottom = '10px';
      card.style.background = 'rgba(15,23,42,.42)';
      card.style.color = 'var(--t1, #dff0e8)';

      const totalKm = list.reduce((sum, vehicle) => sum + (vehicle.totalKm || 0), 0);
      const totalStops = list.reduce((sum, vehicle) => sum + (vehicle.assignedStops?.length || 0), 0);
      const delivered = list.reduce((sum, vehicle) => sum + vehicle.assignedStops.filter(point => vehicle.deliveredPts.has(point)).length, 0);

      const head = document.createElement('div');
      head.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:7px;';
      head.innerHTML = `
        <b style="color:${list[0].col};font-family:var(--fm, Consolas, monospace);font-size:11px">${title}</b>
        <span style="color:var(--t2, #94a3b8);font-size:10px">${list.length} xe · ${delivered}/${totalStops} diem · ${totalKm.toFixed(1)} km</span>
      `;
      card.appendChild(head);

      list.forEach(vehicle => {
        const nextStop = vehicle.order[vehicle.nextPtIdx];
        const fromStop = vehicle.order[Math.max(0, vehicle.nextPtIdx - 1)];
        const status = vehicle.on && nextStop != null
          ? `Dang di: ${pts[fromStop]?.name || 'Kho'} -> ${pts[nextStop]?.name || 'Kho'}`
          : 'Da hoan thanh tuyen';
        const row = document.createElement('div');
        row.style.cssText = 'padding:5px 0;border-top:1px dashed rgba(100,116,139,.35);';
        row.innerHTML = `
          <div style="display:flex;justify-content:space-between;gap:6px;align-items:center;margin-bottom:4px;">
            <span style="display:flex;align-items:center;gap:6px;color:var(--t1, #dff0e8);font-size:10px;">
              <i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${vehicle.col}"></i>
              <b style="color:${vehicle.col};font-family:var(--fm, Consolas, monospace);font-size:10px">${vehicle.shortLabel || vehicle.label}</b>
            </span>
            <span style="font-size:10px;color:var(--t2, #94a3b8);">${status}</span>
          </div>
          <div style="font-size:10px;line-height:1.65;color:var(--t1, #dff0e8);">${vehicle.order.map(point => pts[point]?.name || `P${point}`).join(' -> ')}</div>
        `;
        card.appendChild(row);
      });
      el.appendChild(card);
      return true;
    };

    groupDefs.forEach(def => {
      const list = grouped.get(def.key) || [];
      if(appendGroupCard(def.title, list)) renderedGroups += 1;
    });
    if(!renderedGroups && vehs.length){
      appendGroupCard('Lo trinh hien tai', vehs);
    }

    const failedStops = pts.filter(point => point.undeliverable);
    if(failedStops.length){
      const failed = document.createElement('div');
      failed.className = 'RI';
      failed.style.display = 'block';
      failed.style.opacity = '1';
      failed.style.animation = 'none';
      failed.style.borderLeft = '3px solid #ff7b35';
      failed.style.paddingLeft = '10px';
      failed.style.marginTop = '12px';
      failed.innerHTML = `
        <b style="color:#ff7b35;font-family:var(--fm);font-size:11px">Giao khong thanh cong</b>
        <div style="font-size:10px;color:var(--t2);margin-top:6px;line-height:1.6">
          ${failedStops.map(point => `${point.name}: nam trong khu vuc cam, tra hang ve kho`).join('<br>')}
        </div>
      `;
      el.appendChild(failed);
    }
  }

  function setBackendResult(modeIdx, order, km){
    const paths = backendGraphMode === 'road' ? [] : visualPaths(order);
    const cost = kmToCost(km);
    const spd = +($('spd')?.value || 40);
    const mins = Math.round(km / spd * 60);
    results[modeIdx] = {dist:cost, time:mins, order, roadPaths:paths};
    setResult(modeIdx, cost);
    return paths;
  }

  function makeBackendVehicles(routes, defaultOrder, baseLabel, routePaths){
    const options = arguments[4] || {};
    const colors = options.palette || ['#7ee787', '#00d4ff', '#ffd166', '#a78bfa', '#ff7b72', '#5eead4'];
    const algorithmKey = options.algorithmKey || 'single';
    const algorithmLabel = options.algorithmLabel || baseLabel;
    const usableRoutes = (routes && routes.length ? routes : [defaultOrder]).filter(route => route && route.length > 1);
    return usableRoutes.map((route, idx) => {
      const shortLabel = `Xe ${idx + 1}`;
      const label = usableRoutes.length > 1 ? `${baseLabel} - ${shortLabel}` : baseLabel;
      const backendSegments = routePaths && routePaths[idx];
      if(backendSegments && backendSegments.length){
        const waypoints = backendSegments.flatMap((segment, segIdx) => backendSegmentWaypoints(segment, segIdx));
        if(backendGraphMode === 'road' && waypoints.length < 2) {
          throw new Error(`Khong co duong backend hop le cho ${label}`);
        }
        const vehicle = decorateVehicle(makeVehicleFromWaypoints(route, waypoints, colors[idx % colors.length], label), route, idx);
        vehicle.shortLabel = shortLabel;
        vehicle.algorithmKey = algorithmKey;
        vehicle.algorithmLabel = algorithmLabel;
        return vehicle;
      }
      if(backendGraphMode === 'road') {
        throw new Error(`Backend khong tra route path cho ${label}. Khong dung duong noi tat.`);
      }
      const vehicle = decorateVehicle(makeVeh(route, visualPaths(route), colors[idx % colors.length], label), route, idx);
      vehicle.shortLabel = shortLabel;
      vehicle.algorithmKey = algorithmKey;
      vehicle.algorithmLabel = algorithmLabel;
      return vehicle;
    });
  }

  async function fetchBackendRoutePaths(routes){
    const response = await fetch('/api/route_paths', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({routes})
    });
    const data = await response.json();
    if(data.status !== 'success') throw new Error(normalizeBrokenText(data.message || 'Khong lay duoc path A*'));
    return data.route_paths || [];
  }

  async function buildBackendMatrix(){
    const graphMode = getSelectedGraphMode();
    await syncBackendRoadGraph(graphMode);
    if(!assertRunnableMap()){
      throw new Error('Co diem giao nam trong khu vuc cam nen khong the chay.');
    }
    setStatus('Python backend: chay A* va xay ma tran khoang cach...');
    const response = await fetch('/api/astar', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        heuristic:$('heur') ? $('heur').value : 'euclidean',
        speed:+($('spd')?.value || 40),
        graph_mode:graphMode
      })
    });
    const data = await response.json();
    if(data.status !== 'success') throw new Error(normalizeBrokenText(data.message || 'Khong xay duoc ma tran A*'));
    backendGraphMode = data.graph_mode || graphMode;
    pyDM = data.dist_matrix;
    dm = pyDM.map(row => row.map(kmToCost));
    return pyDM;
  }

  function runBackendGA(options){
    const opts = options || {};
    return new Promise((resolve, reject)=>{
      const popSize = +(opts.popSize ?? $('ps').value);
      const generations = +(opts.generations ?? $('gens').value);
      const mutRate = +(opts.mutRate ?? $('mr').value);
      const speed = +(opts.speed ?? ($('spd')?.value || 40));
      const vehicles = +(opts.forceVehicles ?? ($('vehicles')?.value || 1));
      const capacity = +(opts.forceCapacity ?? ($('capacity')?.value || 24));
      const metric = String(opts.metric || 'astar').toLowerCase();
      const timeWindows = (opts.forceTimeWindows != null)
        ? !!opts.forceTimeWindows
        : ($('timeWindowsToggle')?.dataset.on !== '0');
      setText('ga-max', generations);
      setText('ga-cur', 0);
      setText('ga-fit', '--');
      setStyle('ga-bar', 'width', '0%');
      conv = [];

      const source = new EventSource(`/api/optimize?pop_size=${popSize}&generations=${generations}&mut_rate=${mutRate}&speed=${speed}&vehicles=${vehicles}&capacity=${capacity}&time_windows=${timeWindows ? 1 : 0}&metric=${encodeURIComponent(metric)}`);
      source.onmessage = event => {
        const data = JSON.parse(event.data);
        if(data.type === 'progress'){
          conv = data.history.map(kmToCost);
          setText('ga-cur', data.gen + 1);
          setStyle('ga-bar', 'width', Math.min(100, ((data.gen + 1) / generations) * 100) + '%');
          setText('ga-fit', Number(data.best_fit).toFixed(1) + ' km');
          drawConv();
        }
        if(data.type === 'done'){
          source.close();
          conv = data.history.map(kmToCost);
          setText('ga-cur', generations);
          setStyle('ga-bar', 'width', '100%');
          setText('ga-fit', Number(data.best_dist).toFixed(1) + ' km');
          drawConv();
          resolve({
            order:data.best_order,
            km:Number(data.best_dist),
            actualKm:Number(data.actual_dist ?? data.best_dist),
            routes:data.routes || [data.best_order],
            routePaths:data.route_paths || [],
            baselineOrder:data.baseline_order || [],
            baselineKm:Number(data.baseline_dist || 0),
            baselineTime:data.baseline_time || '',
            baselineRoutes:data.baseline_routes || (data.baseline_order ? [data.baseline_order] : []),
            baselineRoutePaths:data.baseline_route_paths || [],
            metric:data.metric || metric,
            constraints:data.constraints || {}
          });
        }
      };
      source.onerror = () => {
        source.close();
        reject(new Error('Mat ket noi khi chay GA backend'));
      };
    });
  }

  window.doGen = async function(){
    const genVersion = ++backendGenVersion;
    const n = +$('np').value;
    buildCity();
    resetRunState();
    setStatus('Python backend: sinh ban do giao hang...');
    setText('hbadge','LOADING');

    const response = await fetch('/api/generate', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        n,
        obstacles:+($('obstacles')?.value || 0),
        graph_mode:getSelectedGraphMode()
      })
    });
    const data = await response.json();
    if(genVersion !== backendGenVersion) return;
    if(data.status !== 'success') throw new Error(normalizeBrokenText(data.message || 'Khong tao duoc ban do'));

    pts = data.points.map(mapBackendPointV2);
    backendObstacles = (data.obstacles || []).map(mapBackendObstacle);
    normalizeUiLabels();
    pts.forEach(point => {
      point.undeliverable = backendObstacles.some(obstacle =>
        !point.isDepot &&
        point.x >= obstacle.x &&
        point.x <= obstacle.x + obstacle.w &&
        point.y >= obstacle.y &&
        point.y <= obstacle.y + obstacle.h
      );
    });
    backendGraphMode = data.graph_mode || getSelectedGraphMode();
    await syncBackendRoadGraph(backendGraphMode);
    if(genVersion !== backendGenVersion) return;
    setStatus(`Python backend: ${pts.length-1} diem giao, ${backendObstacles.length} vat can, A* ${backendGraphMode}`);
    setText('hbadge','READY');
    setStyle('fp-step','display','flex');
    setStyle('fp-result','display','none');
    setStyle('fp-cmp','display','none');
    setStyle('fp-export','display','none');
    setStyle('fp-replay','display','none');
    setStyle('fp-route','display','none');
    if($('cmp-quick')) $('cmp-quick').innerHTML = '';
    if($('cmp-section')) $('cmp-section').style.display = 'none';
    if($('cpanel')) $('cpanel').innerHTML = '<div style="color:var(--t2);font-size:10px;font-family:var(--fm);padding-top:6px;">Chay che do so sanh de xem chi so lo trinh.</div>';
    resizeCV();
    fitPts();
  };

  window.loadPreset = function(k){
    const map={urban:{n:18,s:30},suburb:{n:8,s:60},mixed:{n:14,s:40},stress:{n:24,s:25}};
    if(!map[k]) return;
    const isEarlyAutoMixed = k === 'mixed' && window.__userChangedBackendConfig && (Date.now() - window.__backendOverrideStartedAt < 2000);
    if(isEarlyAutoMixed) return;
    $('np').value=map[k].n; $('nv').textContent=map[k].n;
    $('spd').value=map[k].s; $('sv').textContent=map[k].s;
    window.doGen();
    closeDrawer('dr-setup');
  };

  const RUN_MODE = {
    HYBRID: 0,
    ASTAR: 1,
    GA_ONLY: 2,
    COMPARE: 3,
    BASELINE: 4
  };

  function sequentialOrder(){
    return [0,...Array.from({length:pts.length-1},(_,i)=>i+1),0];
  }

  function setBaselineResult(order, km){
    const speed = +($('spd')?.value || 40);
    const result = {
      dist: kmToCost(km),
      time: Math.round(km / speed * 60),
      execMs: 0,
      order,
      roadPaths: [],
      label: 'Tuyen ban dau',
      col: '#facc15'
    };
    results[3] = {...result};
    results[4] = {...result};
    setText('sbase', `${km.toFixed(1)} km`);
    return result;
  }

  async function runBaselineMode(){
    const order = sequentialOrder();
    const km = directRouteKm(order);
    setBaselineResult(order, km);
    setResult(3, kmToCost(km));
    results[3].label = 'Tuyen ban dau';
    results[3].col = '#facc15';
    results[3].execMs = 0;
    results[4] = {...results[3]};
    vehs = [makeDirectBaselineVehicle(order, km)];
    renderVehicleRoutes();
    setStatus(`Hoan tat tuyen tuan tu ban dau: ${km.toFixed(1)} km, khong dung A* / GA`);
  }

  async function runAstarMode(){
    await buildBackendMatrix();
    const order = sequentialOrder();
    const km = routeKm(order);
    setBackendResult(1, order, km);
    const routePaths = await fetchBackendRoutePaths([order]);
    vehs = makeBackendVehicles([order], order, 'A* Tuan tu', routePaths, {
      algorithmKey:'single',
      algorithmLabel:'A* tuan tu',
      palette:['#ff7b35', '#fb923c', '#f59e0b', '#facc15']
    });
    renderVehicleRoutes();
    setStatus('Python backend: hoan tat A* tuan tu');
  }

  async function runCompareMode(){
    await buildBackendMatrix();
    const orderA = sequentialOrder();
    const aStarExecStart = performance.now();
    const kmA = routeKm(orderA);
    const routePathsA = await fetchBackendRoutePaths([orderA]);
    const speed = +($('spd')?.value || 40);
    const aStarExecMs = Math.max(1, performance.now() - aStarExecStart);

    results[1] = {
      dist:kmToCost(kmA),
      time:Math.round(kmA/speed*60),
      execMs:aStarExecMs,
      order:orderA,
      roadPaths:[],
      label:'A* Tuan tu',
      col:'#ff7b35'
    };

    setStatus('Python backend: chay GA thuong (metric Euclid)...');
    const gaOnlyStart = performance.now();
    const gaOnly = await runBackendGA({
      metric:'euclidean',
      forceTimeWindows:false
    });
    const gaOnlyExecMs = Math.max(1, performance.now() - gaOnlyStart);
    const gaOnlyKm = routeKm(gaOnly.order);
    setBackendResult(2, gaOnly.order, gaOnlyKm);
    results[2].label = 'GA';
    results[2].col = '#a78bfa';
    results[2].execMs = gaOnlyExecMs;

    setStatus('Python backend: chay A* + GA tren ma tran A*...');
    const gaHybridStart = performance.now();
    const gaHybrid = await runBackendGA({
      metric:'astar'
    });
    const gaHybridExecMs = Math.max(1, performance.now() - gaHybridStart);
    const gaHybridKm = routeKm(gaHybrid.order);
    setBackendResult(0, gaHybrid.order, gaHybridKm);
    results[0].label = 'A* + GA';
    results[0].col = '#7ee787';
    results[0].execMs = gaHybridExecMs;

    const baselineOrder = sequentialOrder();
    const baselineKm = directRouteKm(baselineOrder);
    setBaselineResult(baselineOrder, baselineKm);

    vehs = [
      makeDirectBaselineVehicle(baselineOrder, baselineKm),
      ...makeBackendVehicles([orderA], orderA, 'A* Tuan tu', routePathsA, {
        algorithmKey:'astar_base',
        algorithmLabel:'A* tuan tu',
        palette:['#ff7b35', '#fb923c', '#f59e0b', '#facc15']
      }),
      ...makeBackendVehicles(gaOnly.routes, gaOnly.order, 'GA', gaOnly.routePaths, {
        algorithmKey:'ga_only',
        algorithmLabel:'GA',
        palette:['#a78bfa', '#c084fc', '#818cf8', '#38bdf8']
      }),
      ...makeBackendVehicles(gaHybrid.routes, gaHybrid.order, 'GA Toi uu', gaHybrid.routePaths, {
        algorithmKey:'ga_opt',
        algorithmLabel:'A* + GA',
        palette:['#7ee787', '#34d399', '#00d4ff', '#5eead4']
      })
    ];
    renderVehicleRoutes();
    renderCompareIndicators();
    const impHybrid = kmA > 0 ? ((kmA - gaHybridKm) / kmA * 100).toFixed(1) : '0.0';
    const impGa = kmA > 0 ? ((kmA - gaOnlyKm) / kmA * 100).toFixed(1) : '0.0';
    setText('rs-imp','↓' + Math.max(Number(impHybrid), Number(impGa)).toFixed(1) + '%');
    setStatus(`Python backend: so sanh xong (A*: ${kmA.toFixed(1)} km | GA: ${gaOnlyKm.toFixed(1)} km | A*+GA: ${gaHybridKm.toFixed(1)} km)`);
    setTimeout(showCompareModal, 800);
  }

  async function runOptimizationMode(mode){
    await buildBackendMatrix();
    const isGaOnly = mode === RUN_MODE.GA_ONLY;
    const ga = await runBackendGA({
      metric: isGaOnly ? 'euclidean' : 'astar'
    });
    const displayKm = Number(ga.actualKm || ga.km);
    setBackendResult(isGaOnly ? 2 : 0, ga.order, displayKm);
    const algoLabel = isGaOnly ? 'GA di truyen' : 'A* + GA';
    vehs = makeBackendVehicles(ga.routes, ga.order, isGaOnly ? 'GA Di truyen' : 'A*+GA', ga.routePaths, {
      algorithmKey:'single',
      algorithmLabel:algoLabel,
      palette:['#7ee787', '#00d4ff', '#ffd166', '#a78bfa', '#ff7b72', '#5eead4']
    });
    renderVehicleRoutes();
    renderCompareIndicators();
    setStatus('Python backend: hoan tat toi uu GA');
  }

  async function runActiveMode(){
    if(MODE === RUN_MODE.BASELINE) return runBaselineMode();
    if(MODE === RUN_MODE.ASTAR) return runAstarMode();
    if(MODE === RUN_MODE.COMPARE) return runCompareMode();
    return runOptimizationMode(MODE);
  }

  function finishRunUi(){
    setStyle('fp-result','display','flex');
    setStyle('fp-cmp','display',MODE===RUN_MODE.COMPARE?'flex':'none');
    setStyle('fp-export','display','flex');
    setStyle('fp-replay','display','flex');
    setStyle('fp-route','display','flex');
    setText('hbadge','DONE');
    startAnim();
  }

  window.doRun = async function(){
    if(!pts.length) await window.doGen();
    exitStepMode();
    doneSet.clear(); vehs=[]; animDist=0;
    if(animRAF){cancelAnimationFrame(animRAF);animRAF=null;}
    if(!assertRunnableMap()){
      return;
    }

    setStyle('fp-run','pointerEvents','none');
    setText('fp-run','Dang chay...');
    setText('hbadge','PYTHON');
    if(MODE !== 3){
      if($('cmp-quick')) $('cmp-quick').innerHTML = '';
      if($('cmp-section')) $('cmp-section').style.display = 'none';
    }

    try{
      await runActiveMode();
      finishRunUi();
    }catch(error){
      console.error(error);
      setText('hbadge','ERROR');
      setStatus('Loi backend Python: ' + error.message);
      alert('Loi backend Python: ' + error.message);
    }finally{
      setStyle('fp-run','pointerEvents','');
      setText('fp-run','Chay');
    }
  };

  window.toggleStepMode = async function(){
    if(stepMode){exitStepMode();return;}
    if(!pts.length) await window.doGen();
    if(!assertRunnableMap()){
      return;
    }
    try{
      await buildBackendMatrix();
      const currentResult = results[MODE] && results[MODE].order && results[MODE].order.length ? results[MODE] : results[0];
      const order=currentResult && currentResult.order && currentResult.order.length
        ? currentResult.order
        : [0,...Array.from({length:pts.length-1},(_,i)=>i+1),0];
      stepSegs=buildAllSegments(order);
      stepSegIdx=0; stepIdx=0; stepMode=true;
      setStyle('asoverlay','display','block');
      setText('fp-step','A* STEP - THOAT');
      renderStepState();
      const modeLabel = backendGraphMode === 'road' ? 'mang duong/hem' : (backendGraphMode === 'grid' ? 'luoi o' : 'duong thang ne vat can');
      setStatus(`A* Step dang minh hoa tren ${modeLabel}; chi phi ma tran lay tu Python backend`);
    }catch(error){
      console.error(error);
      setText('hbadge','ERROR');
      setStatus('Loi backend Python: ' + error.message);
      alert('Loi backend Python: ' + error.message);
    }
  };

  const originalSetText = window.setText?.bind(window);
  if(originalSetText){
    window.setText = function(id, value){
      return originalSetText(id, normalizeBrokenText(value));
    };
  }
  const originalSetStatus = window.setStatus?.bind(window);
  if(originalSetStatus){
    window.setStatus = function(message){
      return originalSetStatus(normalizeBrokenText(message));
    };
  }

  window.showCompareModal = function(){
    adjustVehicleHudPosition(true);
    const overlay = $('moverlay') || $('modal-overlay');
    const tbody = $('cbody') || $('cmp-body');
    const spd = +($('spd')?.value || 40);
    const series = getCompareSeries().map(meta => ({...meta, result: results[meta.index] || null}));
    const initial = series.find(item => item.id === 'baseline');
    const astar = series.find(item => item.id === 'astar');
    const gaOnly = series.find(item => item.id === 'ga_only');
    const hybrid = series.find(item => item.id === 'ga_opt');
    const available = series.filter(item => item.result && item.result.order && item.result.order.length > 0);

    if(!tbody || available.length < 2){
      if(tbody){
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--sub);padding:20px;">Chạy chế độ so sĂ¡nh Ä‘á»ƒ xem Ä‘á»§ dá»¯ liá»‡u tuyáº¿n ban Ä‘áº§u, A*, GA, A*+GA.</td></tr>';
      }
      setText('cmp-pct','â€”');
      setText('cmp-sub','ChÆ°a Ä‘á»§ dá»¯ liá»‡u so sĂ¡nh 4 mĂ´ hĂ¬nh');
      if(overlay) overlay.classList.add(overlay.id === 'moverlay' ? 'show' : 'on');
      return;
    }

    const kmOf = item => costToKm(item?.result?.dist || 0);
    const minsOf = item => Number(item?.result?.time || Math.round((kmOf(item) / spd) * 60));
    const execOf = item => Number(item?.result?.execMs || 0);
    const stopOf = item => Math.max(0, (item?.result?.order?.length || 2) - 2);
    const better = (value, best) => value === best ? '<span style="color:#7ee787;font-weight:700">âœ“ tá»‘t nháº¥t</span>' : '';
    const bestKm = Math.min(...available.map(kmOf));
    const bestMins = Math.min(...available.map(minsOf));
    const baselineDist = kmOf(initial);
    const gaImprove = baselineDist > 0 ? ((baselineDist - kmOf(gaOnly)) / baselineDist * 100) : 0;
    const astarImprove = baselineDist > 0 ? ((baselineDist - kmOf(astar)) / baselineDist * 100) : 0;
    const hybridImprove = baselineDist > 0 ? ((baselineDist - kmOf(hybrid)) / baselineDist * 100) : 0;

    const row = (label, valB, valA, valG, valH, conclusion, note='') => `
      <tr>
        <td style="color:var(--sub);font-size:12px;line-height:1.55">${label}${note ? `<br><small style="font-size:10px;opacity:.68">${note}</small>` : ''}</td>
        <td style="color:#facc15;font-weight:800">${valB}</td>
        <td style="color:#ff7b35;font-weight:700">${valA}</td>
        <td style="color:#a78bfa;font-weight:700">${valG}</td>
        <td style="color:#7ee787;font-weight:700">${valH}</td>
        <td>${conclusion}</td>
      </tr>
    `;

    tbody.innerHTML =
      row(
        'Tá»•ng quĂ£ng Ä‘Æ°á»ng',
        `${kmOf(astar).toFixed(2)} km`,
        `${kmOf(gaOnly).toFixed(2)} km`,
        `${kmOf(hybrid).toFixed(2)} km`,
        better(kmOf(astar), bestKm) || better(kmOf(gaOnly), bestKm) || better(kmOf(hybrid), bestKm),
        'ÄĂ¡nh giĂ¡ theo lá»™ trĂ¬nh Ä‘Æ°á»ng/háº»m thá»±c táº¿'
      ) +
      row(
        'Thá»i gian di chuyá»ƒn',
        formatDurationMinutes(minsOf(astar)),
        formatDurationMinutes(minsOf(gaOnly)),
        formatDurationMinutes(minsOf(hybrid)),
        better(minsOf(astar), bestMins) || better(minsOf(gaOnly), bestMins) || better(minsOf(hybrid), bestMins),
        `Æ¯á»›c tĂ­nh theo ${spd} km/h`
      ) +
      row(
        'Cáº£i thiá»‡n so vá»›i A*',
        'Baseline',
        `${gaImprove >= 0 ? 'â†“' : 'â†‘'} ${Math.abs(gaImprove).toFixed(1)}%`,
        `${hybridImprove >= 0 ? 'â†“' : 'â†‘'} ${Math.abs(hybridImprove).toFixed(1)}%`,
        hybridImprove >= gaImprove
          ? '<span style="color:#7ee787;font-weight:700">A*+GA tá»‘t hÆ¡n</span>'
          : '<span style="color:#a78bfa;font-weight:700">GA tá»‘t hÆ¡n</span>',
        'Giáº£m quĂ£ng Ä‘Æ°á»ng cĂ ng cao cĂ ng tá»‘t'
      ) +
      row(
        'Thá»i gian tĂ­nh toĂ¡n',
        execOf(astar) ? `${execOf(astar).toFixed(0)} ms` : 'â€”',
        execOf(gaOnly) ? `${execOf(gaOnly).toFixed(0)} ms` : 'â€”',
        execOf(hybrid) ? `${execOf(hybrid).toFixed(0)} ms` : 'â€”',
        '<span style="color:var(--sub)">Tham kháº£o</span>',
        'Äo trá»±c tiáº¿p trĂªn trĂ¬nh duyá»‡t'
      ) +
      row(
        'Sá»‘ Ä‘iá»ƒm giao',
        `${stopOf(astar)} Ä‘iá»ƒm`,
        `${stopOf(gaOnly)} Ä‘iá»ƒm`,
        `${stopOf(hybrid)} Ä‘iá»ƒm`,
        '<span style="color:var(--sub)">NhÆ° nhau</span>'
      ) +
      row(
        'MĂ´ táº£ thuáº­t toĂ¡n',
        'A* tuáº§n tá»±',
        'GA (metric Euclid)',
        'GA + ma tráº­n A*',
        '<span style="color:var(--sub)">3 cĂ¡ch khĂ¡c nhau</span>'
      );

    tbody.innerHTML =
      row(
        'T\u1ed5ng qu\u00e3ng \u0111\u01b0\u1eddng',
        `${kmOf(initial).toFixed(2)} km`,
        `${kmOf(astar).toFixed(2)} km`,
        `${kmOf(gaOnly).toFixed(2)} km`,
        `${kmOf(hybrid).toFixed(2)} km`,
        better(kmOf(initial), bestKm) || better(kmOf(astar), bestKm) || better(kmOf(gaOnly), bestKm) || better(kmOf(hybrid), bestKm),
        '\u0110\u00e1nh gi\u00e1 theo l\u1ed9 tr\u00ecnh \u0111\u01b0\u1eddng/h\u1ebbm th\u1ef1c t\u1ebf'
      ) +
      row(
        'Th\u1eddi gian di chuy\u1ec3n',
        formatDurationMinutes(minsOf(initial)),
        formatDurationMinutes(minsOf(astar)),
        formatDurationMinutes(minsOf(gaOnly)),
        formatDurationMinutes(minsOf(hybrid)),
        better(minsOf(initial), bestMins) || better(minsOf(astar), bestMins) || better(minsOf(gaOnly), bestMins) || better(minsOf(hybrid), bestMins),
        `\u01af\u1edbc t\u00ednh theo ${spd} km/h`
      ) +
      row(
        'C\u1ea3i thi\u1ec7n so v\u1edbi tuy\u1ebfn ban \u0111\u1ea7u',
        'Baseline',
        `${astarImprove >= 0 ? 'down' : 'up'} ${Math.abs(astarImprove).toFixed(1)}%`,
        `${gaImprove >= 0 ? 'down' : 'up'} ${Math.abs(gaImprove).toFixed(1)}%`,
        `${hybridImprove >= 0 ? 'down' : 'up'} ${Math.abs(hybridImprove).toFixed(1)}%`,
        hybridImprove >= gaImprove && hybridImprove >= astarImprove
          ? '<span style="color:#7ee787;font-weight:700">A*+GA t\u1ed1t h\u01a1n</span>'
          : '<span style="color:var(--sub)">Xem c\u1ed9t t\u1ed1t nh\u1ea5t</span>',
        'Gi\u1ea3m qu\u00e3ng \u0111\u01b0\u1eddng c\u00e0ng cao c\u00e0ng t\u1ed1t'
      ) +
      row(
        'Th\u1eddi gian t\u00ednh to\u00e1n',
        execOf(initial) ? `${execOf(initial).toFixed(0)} ms` : '0 ms',
        execOf(astar) ? `${execOf(astar).toFixed(0)} ms` : '-',
        execOf(gaOnly) ? `${execOf(gaOnly).toFixed(0)} ms` : '-',
        execOf(hybrid) ? `${execOf(hybrid).toFixed(0)} ms` : '-',
        '<span style="color:var(--sub)">Tham kh\u1ea3o</span>',
        '\u0110o tr\u1ef1c ti\u1ebfp tr\u00ean tr\u00ecnh duy\u1ec7t'
      ) +
      row(
        'S\u1ed1 \u0111i\u1ec3m giao',
        `${stopOf(initial)} \u0111i\u1ec3m`,
        `${stopOf(astar)} \u0111i\u1ec3m`,
        `${stopOf(gaOnly)} \u0111i\u1ec3m`,
        `${stopOf(hybrid)} \u0111i\u1ec3m`,
        '<span style="color:var(--sub)">Nh\u01b0 nhau</span>'
      ) +
      row(
        'M\u00f4 t\u1ea3 thu\u1eadt to\u00e1n',
        'Tuy\u1ebfn tu\u1ea7n t\u1ef1 ch\u01b0a t\u1ed1i \u01b0u',
        'A* t\u00ecm \u0111\u01b0\u1eddng tr\u00ean \u0111\u1ed3 th\u1ecb',
        'GA metric Euclid',
        'GA + ma tran A*',
        '<span style="color:var(--sub)">4 c\u00e1ch kh\u00e1c nhau</span>'
      );

    const bestGain = Math.max(astarImprove, gaImprove, hybridImprove);
    setText('cmp-pct', `â†“ ${Math.max(0, bestGain).toFixed(1)}%`);
    setText('cmp-sub', `Ban dau: ${kmOf(initial).toFixed(1)} km | A*: ${kmOf(astar).toFixed(1)} km | GA: ${kmOf(gaOnly).toFixed(1)} km | A*+GA: ${kmOf(hybrid).toFixed(1)} km`);
    renderCompareIndicators();
    if(overlay) overlay.classList.add(overlay.id === 'moverlay' ? 'show' : 'on');
  };

  const originalSetMode = window.setMode?.bind(window);
  if(originalSetMode && !window.__compareModePatched){
    window.__compareModePatched = true;
    window.setMode = function(mode){
      const result = originalSetMode(mode);
      if(Number(mode) === 1){
        setText('sh-mode','A*');
        setStatus('Che do: Tuyen tuan tu ban dau truoc toi uu â€” nhan Chay');
      }
      if(Number(mode) === 3){
        setText('sh-mode','SO SANH 4');
        setStatus('Che do: So sanh A*, GA, A*+GA â€” nhan Chay');
      }
      if(Number(mode) === 4){
        setText('sh-mode','TUYEN TUAN TU BAN DAU');
        setStatus('Che do: Tuyen tuan tu ban dau â€” nhan Chay');
      }
      if(Number(mode) === 1) setStatus('Che do: A* tuan tu - nhan Chay');
      if(Number(mode) === 3) setStatus('Che do: So sanh tuyen ban dau, A*, GA, A*+GA - nhan Chay');
      if(Number(mode) === 4) setStatus('Che do: Tuyen tuan tu ban dau â€” nhan Chay');
      adjustVehicleHudPosition(Number(mode) === 3);
      syncVehicleControlsForMode(mode);
      return result;
    };
  }

  const originalToggleDrawer = window.toggleDrawer?.bind(window);
  if(originalToggleDrawer && !window.__routeDrawerRenderHooked){
    window.__routeDrawerRenderHooked = true;
    window.toggleDrawer = function(id){
      if(id === 'dr-route'){
        try{
          renderVehicleRoutes();
        }catch(_error){}
      }
      return originalToggleDrawer(id);
    };
  }
  const routeButton = $('fp-route');
  if(routeButton){
    routeButton.onclick = function(){
      try{
        renderVehicleRoutes();
      }catch(_error){}
      const routeDrawer = $('dr-route');
      if(routeDrawer){
        document.querySelectorAll('.drawer').forEach(drawer => drawer.classList.remove('open'));
        routeDrawer.classList.add('open');
      }else if(originalToggleDrawer){
        originalToggleDrawer('dr-route');
      }
    };
  }
  if(!document.getElementById('route-list-force-visible')){
    const routeStyle = document.createElement('style');
    routeStyle.id = 'route-list-force-visible';
    routeStyle.textContent = '#rlist .RI,#rlist .ri{opacity:1 !important;visibility:visible !important;animation:none !important;}';
    document.head.appendChild(routeStyle);
  }

  refreshCompareUiShell();
  adjustVehicleHudPosition(false);
  addUpgradeControlsV2();
  syncVehicleControlsForMode(typeof MODE === 'number' ? MODE : 0);
  installConfigChangeGuards();
  repairDomText();
  const uiObserver = new MutationObserver(() => repairDomText());
  uiObserver.observe(document.body, {childList:true, subtree:true, characterData:true});
  const originalTickVehs = window.tickVehs;
  if(typeof originalTickVehs === 'function' && !window.__backendVehiclePanelInstalled){
    window.__backendVehiclePanelInstalled = true;
    window.tickVehs = function(){
      originalTickVehs.apply(this, arguments);
      updateVehicleProgress();
      renderVehicleRoutes();
      if(vehs.length > 1){
        const active = vehs.find(vehicle => vehicle.on) || vehs[0];
        const fromStop = active.order[Math.max(0, active.nextPtIdx - 1)];
        const nextStop = active.order[Math.min(active.nextPtIdx, active.order.length - 1)];
        setText('vfrom', `${active.label}: ${pts[fromStop]?.name || 'Kho'}`);
        setText('vto', pts[nextStop]?.name || 'Kho');
      }
    };
  }
  const originalDraw = window.draw;
  if(typeof originalDraw === 'function' && !window.__backendObstacleDrawInstalled){
    window.__backendObstacleDrawInstalled = true;
    window.draw = function(){
      originalDraw.apply(this, arguments);
      drawBackendGrid();
      drawBackendObstacles();
    };
  }
  setStatus('UI da ket noi Python backend');
})();
</script>
"""


def get_frontend_html():
    if os.path.exists(DEMO_FILE):
        with open(DEMO_FILE, "r", encoding="utf-8") as file:
            html = file.read()
        return html.replace("</body>", PYTHON_BACKEND_OVERRIDE + "\n</body>")
    return HTML_TEMPLATE.replace("</body>", PYTHON_BACKEND_OVERRIDE + "\n</body>")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
    response.headers.add('Pragma', 'no-cache')
    return response

# â”€â”€â”€ Global state â”€â”€â”€
STATE = {
    "points": [],
    "all_points": [],
    "undeliverable_points": [],
    "id_map": {},
    "routing_points": [],
    "graph": {},
    "graph_mode": "road",
    "road_nodes": [],
    "road_edges": [],
    "dist_matrix": {},
    "path_matrix": {},
    "obstacles": [],
}

@app.route('/')
def index():
    return get_frontend_html()

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/generate', methods=['POST', 'OPTIONS'])
def api_generate():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.get_json()
    delivery_count = int(data.get('n', 10))
    obstacles = generate_obstacles(int(data.get('obstacles', 0)))
    graph_mode = normalize_graph_mode(data.get('graph_mode', 'road'))
    points = generate_feasible_points(delivery_count, obstacles)
    fallback_mode = "straight" if graph_mode == "road" else graph_mode
    routing_points, graph = build_routing_graph(points, obstacles, fallback_mode)
    STATE["points"] = points
    STATE["all_points"] = points
    STATE["undeliverable_points"] = []
    STATE["id_map"] = {point["id"]: point["id"] for point in points}
    STATE["routing_points"] = routing_points
    STATE["graph"] = graph
    STATE["graph_mode"] = graph_mode
    STATE["dist_matrix"] = {}
    STATE["path_matrix"] = {}
    STATE["obstacles"] = obstacles
    return jsonify({
        "status": "success",
        "points": points,
        "obstacles": obstacles,
        "graph_mode": graph_mode,
    })


@app.route('/api/sync_road_graph', methods=['POST', 'OPTIONS'])
def api_sync_road_graph():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.get_json() or {}
    graph_mode = normalize_graph_mode(data.get("graph_mode", "road"))
    if graph_mode != "road":
        return jsonify({"status": "success", "graph_mode": STATE.get("graph_mode", graph_mode)})

    points = data.get("points") or []
    road_nodes = data.get("road_nodes") or []
    road_edges = data.get("road_edges") or []
    obstacles = data.get("obstacles") or []
    if not points or not road_nodes or not road_edges:
        return jsonify({"status": "error", "message": "Missing road graph data"}), 400

    road_node_ids = set()
    try:
        for node in road_nodes:
            road_node_ids.add(parse_int_param(node.get("id"), "road_node.id"))
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    invalid_road_edges = []
    for edge in road_edges:
        try:
            edge_a = parse_int_param(edge.get("a"), "road_edge.a")
            edge_b = parse_int_param(edge.get("b"), "road_edge.b")
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        if edge_a not in road_node_ids or edge_b not in road_node_ids:
            invalid_road_edges.append({"a": edge_a, "b": edge_b})
    if invalid_road_edges:
        return jsonify({
            "status": "error",
            "message": "Co road_edge tham chieu node duong/hem khong ton tai.",
            "invalid_edges": invalid_road_edges[:12],
        }), 422

    deliverable_points, undeliverable_points, id_map = split_deliverable_points(points)
    invalid_point_node_ids = []
    for point in deliverable_points:
        point["original_id"] = point.get("original_id", point["id"])
        node_id = point.get("nodeId")
        if node_id is None:
            invalid_point_node_ids.append(point.get("original_id", point.get("id")))
            continue
        try:
            if parse_int_param(node_id, "point.nodeId") not in road_node_ids:
                invalid_point_node_ids.append(point.get("original_id", point.get("id")))
        except ValueError:
            invalid_point_node_ids.append(point.get("original_id", point.get("id")))

    if invalid_point_node_ids:
        return jsonify({
            "status": "error",
            "message": "Co diem giao chua gan dung node duong/hem.",
            "invalid_point_ids": invalid_point_node_ids[:12],
        }), 422

    routing_points, graph = build_road_network_graph(deliverable_points, road_nodes, road_edges, obstacles)
    STATE["points"] = deliverable_points
    STATE["all_points"] = points
    STATE["undeliverable_points"] = undeliverable_points
    STATE["id_map"] = id_map
    STATE["routing_points"] = routing_points
    STATE["graph"] = graph
    STATE["graph_mode"] = "road"
    STATE["road_nodes"] = road_nodes
    STATE["road_edges"] = road_edges
    STATE["obstacles"] = obstacles
    STATE["dist_matrix"] = {}
    STATE["path_matrix"] = {}
    return jsonify({
        "status": "success",
        "graph_mode": "road",
        "road_nodes": len(road_nodes),
        "road_edges": len(road_edges),
        "deliverable_points": len(deliverable_points),
        "undeliverable_points": undeliverable_points,
    })

@app.route('/api/astar', methods=['POST', 'OPTIONS'])
def api_astar():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.get_json() or {}
    h_type = data.get('heuristic', 'euclidean')
    points = STATE.get("points")
    if not points: return jsonify({"status": "error", "message": "No map"}), 400
    undeliverable_points = STATE.get("undeliverable_points") or []
    if undeliverable_points:
        return jsonify({
            "status": "error",
            "message": "Co diem giao nam trong khu vuc cam nen khong the chay A*. Hay tao ban do moi hoac chinh lai vung cam.",
            "undeliverable_points": undeliverable_points,
        }), 422
    graph_mode = normalize_graph_mode(data.get('graph_mode', STATE.get("graph_mode", "road")))
    if graph_mode != STATE.get("graph_mode"):
        if graph_mode == "road":
            return jsonify({"status": "error", "message": "Road graph has not been synced from UI"}), 400
        routing_points, graph = build_routing_graph(points, STATE.get("obstacles") or [], graph_mode)
        STATE["routing_points"] = routing_points
        STATE["graph"] = graph
        STATE["graph_mode"] = graph_mode
    routing_points = STATE.get("routing_points") or points
    graph = STATE.get("graph")
    try:
        speed_kmh = normalize_positive_param(data.get('speed', 40), 'speed', minimum=1)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    logger = AlgorithmRunLogger("astar", {
        "heuristic": h_type,
        "speed_kmh": speed_kmh,
        "graph_mode": graph_mode,
        "point_count": len(points),
        "routing_node_count": len(routing_points or []),
        "edge_count": sum(len(neighbors) for neighbors in (graph or {}).values()) // 2,
    })
    logger.event(
        "graph_ready",
        point_count=len(points),
        routing_node_count=len(routing_points or []),
        edge_count=sum(len(neighbors) for neighbors in (graph or {}).values()) // 2,
    )
    matrix, path_matrix = build_distance_matrix(
        points,
        graph,
        h_type=h_type,
        speed_kmh=speed_kmh,
        graph_points=routing_points,
        return_paths=True,
    )
    unreachable = unreachable_pairs_from_matrix(matrix, len(points))
    if unreachable:
        logger.event("unreachable_pairs", count=len(unreachable), sample=unreachable[:12])
        logger.close()
        return jsonify({
            "status": "error",
            "message": "A* khong tim duoc duong hop le cho mot so cap diem. Hay giam vat can hoac tao ban do moi.",
            "unreachable_pairs": unreachable[:12],
        }), 422
    STATE["dist_matrix"] = matrix
    STATE["path_matrix"] = path_matrix
    size = len(points)
    matrix_2d = []
    for i in range(size):
        row = []
        for j in range(size):
            val = matrix.get((i, j), (0, 0))
            row.append(round(val[0], 2))
        matrix_2d.append(row)
    logger.event(
        "matrix_done",
        matrix_size=f"{size}x{size}",
        matrix=matrix_summary(matrix, size),
        path_pair_count=len(path_matrix),
    )
    logger.event("done", status="success", latest_log=str(logger.latest_path), history_log=str(logger.history_path))
    logger.close()
    return jsonify({
        "status": "success",
        "matrix_size": f"{size}x{size}",
        "dist_matrix": matrix_2d,
        "graph_mode": graph_mode,
        "undeliverable_points": STATE.get("undeliverable_points", []),
    })

@app.route('/api/astar_steps', methods=['POST'])
def api_astar_steps():
    data = request.get_json() or {}
    points = STATE.get("routing_points") or STATE.get("points")
    graph = STATE.get("graph")
    if not points or not graph:
        return jsonify({"status": "error", "message": "No graph data"}), 400
    try:
        start = parse_int_param(data.get('start', 0), 'start')
        goal = parse_int_param(data.get('goal', 1), 'goal')
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    if start not in graph or goal not in graph:
        return jsonify({"status": "error", "message": "start/goal khong ton tai trong do thi hien tai"}), 422
    h_type = data.get('heuristic', 'euclidean')
    from graph.distance import heuristic as h_func_base
    def h_func(u, v, pts): return h_func_base(u, v, pts, h_type)
    from algorithms.astar import astar_with_steps
    steps, path, dist = astar_with_steps(graph, start, goal, points, h_func)
    if not path or dist == float("inf"):
        return jsonify({
            "status": "error",
            "message": "Khong tim duoc duong hop le cho cap node A* Step",
            "start": start,
            "goal": goal,
        }), 422
    return jsonify({"status": "success", "steps": steps, "path": path, "distance": dist})


@app.route('/api/route_paths', methods=['POST', 'OPTIONS'])
def api_route_paths():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.get_json() or {}
    path_matrix = STATE.get("path_matrix") or {}
    routing_points = STATE.get("routing_points") or STATE.get("points")
    if not path_matrix:
        return jsonify({"status": "error", "message": "No A* path matrix"}), 400

    routes = data.get("routes")
    if not routes:
        order = data.get("order")
        routes = [order] if order else []
    if not routes:
        return jsonify({"status": "error", "message": "Missing route/order payload"}), 400
    id_map = STATE.get("id_map") or {}
    mapped_routes = []
    unknown_point_ids = set()
    for route_index, route in enumerate(routes):
        if not isinstance(route, list):
            return jsonify({"status": "error", "message": f"Route {route_index} khong hop le"}), 400
        mapped_route = []
        for point in route:
            try:
                original_id = parse_int_param(point, "route point")
            except ValueError as exc:
                return jsonify({"status": "error", "message": str(exc)}), 400
            if original_id not in id_map:
                unknown_point_ids.add(original_id)
                continue
            mapped_route.append(id_map[original_id])
        if len(mapped_route) >= 2:
            mapped_routes.append(mapped_route)
    if unknown_point_ids:
        return jsonify({
            "status": "error",
            "message": "Route chua diem khong ton tai hoac bi loai khoi ban do hien tai.",
            "unknown_point_ids": sorted(unknown_point_ids)[:12],
        }), 422
    if not mapped_routes:
        return jsonify({"status": "error", "message": "Khong co route hop le de dung duong di"}), 422
    missing_segments = find_missing_route_segments(mapped_routes, path_matrix)
    if missing_segments:
        return jsonify({
            "status": "error",
            "message": "Thieu path backend cho mot so chang route.",
            "missing_segments": missing_segments[:12],
        }), 422
    return jsonify({
        "status": "success",
        "route_paths": build_route_path_payload(mapped_routes, path_matrix, routing_points),
    })


@app.route('/api/optimize')
def api_optimize():
    dist_matrix, points = STATE.get("dist_matrix"), STATE.get("points")
    path_matrix = STATE.get("path_matrix") or {}
    routing_points = STATE.get("routing_points") or points
    if not points:
        return jsonify({"status": "error", "message": "No map"}), 400
    if not dist_matrix:
        return jsonify({"status": "error", "message": "No matrix"}), 400
    undeliverable_points = STATE.get("undeliverable_points") or []
    if undeliverable_points:
        return jsonify({
            "status": "error",
            "message": "Co diem giao nam trong khu vuc cam nen khong the chay toi uu. Hay tao ban do moi hoac chinh lai vung cam.",
            "undeliverable_points": undeliverable_points,
        }), 422
    try:
        pop_size = normalize_positive_param(request.args.get('pop_size', 100), 'pop_size', minimum=2)
        generations = normalize_positive_param(request.args.get('generations', 300), 'generations', minimum=1)
        speed_kmh = normalize_positive_param(request.args.get('speed', 40), 'speed', minimum=1)
        vehicles = normalize_positive_param(request.args.get('vehicles', 1), 'vehicles', minimum=1)
        capacity = normalize_positive_param(request.args.get('capacity', 24), 'capacity', minimum=1)
        mut_rate_percent = float(request.args.get('mut_rate', 3))
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except TypeError:
        return jsonify({"status": "error", "message": "Gia tri mut_rate khong hop le"}), 400
    if mut_rate_percent < 0 or mut_rate_percent > 100:
        return jsonify({"status": "error", "message": "Gia tri mut_rate phai nam trong [0, 100]"}), 400
    mut_rate = mut_rate_percent / 100.0
    ga_metric = str(request.args.get('metric', 'astar')).strip().lower()
    if ga_metric not in {"astar", "euclidean"}:
        return jsonify({"status": "error", "message": "metric chi ho tro: astar hoac euclidean"}), 400
    use_time_windows = request.args.get('time_windows', '1') != '0'
    demands = {point["id"]: point.get("demand", 0) for point in points}
    time_windows = {
        point["id"]: tuple(point["time_window"])
        for point in points
        if point.get("time_window") and use_time_windows
    }
    metric_matrix = dist_matrix if ga_metric == "astar" else build_euclidean_distance_matrix(points, speed_kmh)
    if not metric_matrix:
        return jsonify({"status": "error", "message": "Khong tao duoc ma tran metric GA"}), 400
    algorithm_name = "astar_ga" if ga_metric == "astar" else "ga"
    logger = AlgorithmRunLogger(algorithm_name, {
        "metric": ga_metric,
        "point_count": len(points),
        "pop_size": pop_size,
        "generations": generations,
        "mut_rate_percent": mut_rate_percent,
        "speed_kmh": speed_kmh,
        "vehicles": vehicles,
        "capacity": capacity,
        "time_windows": use_time_windows,
        "graph_mode": STATE.get("graph_mode"),
    })
    logger.event("metric_matrix_ready", matrix=matrix_summary(metric_matrix, len(points)))
    baseline_order = sequential_baseline_route(len(points))
    baseline_routes = [baseline_order] if len(baseline_order) >= 2 else []
    baseline_dist = route_total_distance(baseline_order, dist_matrix) if baseline_routes else 0
    baseline_time = route_total_time(baseline_order, dist_matrix) if baseline_routes else 0
    original_baseline_order = remap_route_to_original_ids(baseline_order, points) if baseline_routes else []
    original_baseline_routes = remap_routes_to_original_ids(baseline_routes, points) if baseline_routes else []
    logger.event(
        "baseline_ready",
        baseline_dist=round(baseline_dist, 2),
        baseline_time_minutes=round(baseline_time, 2),
        baseline_order=original_baseline_order,
        **route_summary(original_baseline_routes),
    )
    q = queue.Queue()
    def ga_worker():
        try:
            def callback(gen, best_fit, best_chromo, history):
                progress = {
                    "type": "progress",
                    "gen": gen,
                    "best_fit": round(best_fit, 2),
                    "best_order": [0] + best_chromo + [0],
                    "history": history,
                }
                logger.event(
                    "generation_progress",
                    generation=gen,
                    best_fit=round(best_fit, 2),
                    best_order=progress["best_order"],
                )
                q.put(progress)
            full_order, best_dist, best_route_time, history, routes = run_ga(
                metric_matrix,
                len(points),
                pop_size=pop_size,
                generations=generations,
                mut_rate=mut_rate,
                progress_callback=callback,
                vehicles=vehicles,
                demands=demands,
                capacity=capacity,
                time_windows=time_windows,
                speed_kmh=speed_kmh,
            )
            actual_dist = 0
            for route in routes:
                for i in range(len(route) - 1):
                    actual_dist += dist_matrix[(route[i], route[i + 1])][0]
            original_full_order = remap_route_to_original_ids(full_order, points)
            original_routes = remap_routes_to_original_ids(routes, points)
            route_paths = build_route_path_payload(routes, path_matrix, routing_points)
            hours, mins = int(best_route_time // 60), int(best_route_time % 60)
            done_payload = {
                "type": "done",
                "best_order": original_full_order,
                "routes": original_routes,
                "route_paths": route_paths,
                "baseline_order": original_baseline_order,
                "baseline_routes": original_baseline_routes,
                "baseline_route_paths": build_route_path_payload(baseline_routes, path_matrix, routing_points),
                "baseline_dist": round(baseline_dist, 2),
                "baseline_time": f"{int(baseline_time // 60)}h{int(baseline_time % 60)}m",
                "best_dist": round(best_dist, 2),
                "actual_dist": round(actual_dist, 2),
                "best_time": f"{hours}h{mins}m",
                "undeliverable_points": STATE.get("undeliverable_points", []),
                "history": history,
                "metric": ga_metric,
                "constraints": {
                    "vehicles": vehicles,
                    "capacity": capacity,
                    "time_windows": use_time_windows,
                }
            }
            logger.event(
                "done",
                best_dist=round(best_dist, 2),
                actual_dist=round(actual_dist, 2),
                best_time=done_payload["best_time"],
                best_order=original_full_order,
                route_path_count=len(route_paths),
                history_points=len(history),
                latest_log=str(logger.latest_path),
                history_log=str(logger.history_path),
                **route_summary(original_routes),
            )
            logger.close()
            q.put(done_payload)
        except Exception as exc:
            logger.event("error", message=str(exc), error_type=type(exc).__name__)
            logger.close()
            q.put({"type": "error", "message": str(exc)})
    threading.Thread(target=ga_worker, daemon=True).start()
    def event_stream():
        while True:
            try: msg = q.get(timeout=60)
            except queue.Empty: break
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("type") in {"done", "error"}: break
    return Response(event_stream(), mimetype='text/event-stream', headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True, use_reloader=False)



