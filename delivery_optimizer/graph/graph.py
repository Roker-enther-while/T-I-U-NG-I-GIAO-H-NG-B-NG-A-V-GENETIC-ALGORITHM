import math

def add_edge(graph, u, v, weight):
    """
    Thêm cạnh có trọng số vào đồ thị dạng Adjacency List.
    Đồ thị được biểu diễn bằng dict: {node_id: {neighbor_id: weight, ...}, ...}
    """
    if u not in graph:
        graph[u] = {}
    graph[u][v] = weight
    
    # Đồ thị vô hướng (đi qua lại được)
    if v not in graph:
        graph[v] = {}
    graph[v][u] = weight

def point_inside_rect(point, rect):
    return rect["x_min"] <= point["x"] <= rect["x_max"] and rect["y_min"] <= point["y"] <= rect["y_max"]

def orientation(a, b, c):
    value = (b["y"] - a["y"]) * (c["x"] - b["x"]) - (b["x"] - a["x"]) * (c["y"] - b["y"])
    if abs(value) < 1e-9:
        return 0
    return 1 if value > 0 else 2

def on_segment(a, b, c):
    return (
        min(a["x"], c["x"]) <= b["x"] <= max(a["x"], c["x"])
        and min(a["y"], c["y"]) <= b["y"] <= max(a["y"], c["y"])
    )

def segments_intersect(p1, q1, p2, q2):
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_segment(p1, p2, q1):
        return True
    if o2 == 0 and on_segment(p1, q2, q1):
        return True
    if o3 == 0 and on_segment(p2, p1, q2):
        return True
    if o4 == 0 and on_segment(p2, q1, q2):
        return True
    return False

def edge_blocked_by_obstacle(p1, p2, obstacle):
    if point_inside_rect(p1, obstacle) or point_inside_rect(p2, obstacle):
        return True

    corners = [
        {"x": obstacle["x_min"], "y": obstacle["y_min"]},
        {"x": obstacle["x_max"], "y": obstacle["y_min"]},
        {"x": obstacle["x_max"], "y": obstacle["y_max"]},
        {"x": obstacle["x_min"], "y": obstacle["y_max"]},
    ]
    edges = [(corners[0], corners[1]), (corners[1], corners[2]), (corners[2], corners[3]), (corners[3], corners[0])]
    return any(segments_intersect(p1, p2, a, b) for a, b in edges)

def edge_is_allowed(p1, p2, obstacles):
    return not any(edge_blocked_by_obstacle(p1, p2, obstacle) for obstacle in obstacles)

def add_obstacle_waypoints(points, obstacles, padding=4):
    """
    Thêm các node phụ quanh góc vật cản để A* có đường đi vòng.
    Nếu không có các node này, đồ thị đầy đủ chỉ biết loại cạnh bị chặn
    nhưng không có điểm trung gian để tạo tuyến tránh.
    """
    routing_points = [point.copy() for point in points]
    next_id = len(routing_points)
    for obstacle in obstacles or []:
        candidates = [
            (obstacle["x_min"] - padding, obstacle["y_min"] - padding),
            (obstacle["x_max"] + padding, obstacle["y_min"] - padding),
            (obstacle["x_max"] + padding, obstacle["y_max"] + padding),
            (obstacle["x_min"] - padding, obstacle["y_max"] + padding),
        ]
        for x, y in candidates:
            point = {
                "id": next_id,
                "x": max(0, min(100, x)),
                "y": max(0, min(100, y)),
                "name": f"Detour {next_id}",
                "status": "detour",
            }
            if not any(point_inside_rect(point, rect) for rect in obstacles):
                routing_points.append(point)
                next_id += 1
    return routing_points

def build_graph(points, mode="full", obstacles=None):
    """
    Xây dựng đồ thị từ danh sách các điểm.
    - Chế độ 'full': Mọi điểm đều nối với nhau (đồ thị đầy đủ). 
      Thường dùng khi giả định có thể đi trực tiếp giữa các điểm giao.
    - Chế độ 'grid': Chỉ nối các điểm kề nhau trong lưới (4 hướng).
      Thường dùng để mô phỏng mạng lưới đường sá thực tế.
    """
    num_points = len(points)
    graph = {i: {} for i in range(num_points)}
    obstacles = obstacles or []
    
    if mode == "full":
        for i in range(num_points):
            for j in range(i + 1, num_points):
                p1 = points[i]
                p2 = points[j]
                # Tính khoảng cách Euclid làm trọng số
                dist = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
                if edge_is_allowed(p1, p2, obstacles):
                    add_edge(graph, i, j, dist)
                
    elif mode == "grid":
        # Giả sử các điểm được tạo từ generate_grid và sắp xếp theo hàng/cột
        # Ta cần biết số cột để xác định điểm trên/dưới
        # Ở đây ta sẽ tìm các điểm có khoảng cách bằng spacing (giả định spacing cố định)
        # Cách đơn giản hơn: nối các điểm nếu khoảng cách < ngưỡng (threshold)
        threshold = 11 # Cho spacing=10
        for i in range(num_points):
            for j in range(i + 1, num_points):
                p1 = points[i]
                p2 = points[j]
                dist = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
                if dist <= threshold and edge_is_allowed(p1, p2, obstacles):
                    add_edge(graph, i, j, dist)
                    
    return graph

if __name__ == "__main__":
    # Test độc lập Module 2
    from delivery_optimizer.data.generator import generate_points
    
    test_points = generate_points(3)
    g = build_graph(test_points, mode="full")
    print("Graph (full mode):")
    print(g)
