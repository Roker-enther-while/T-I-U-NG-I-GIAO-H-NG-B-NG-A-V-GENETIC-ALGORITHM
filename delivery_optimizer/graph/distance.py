import math

def euclidean(p1, p2):
    """
    Tính khoảng cách Euclid giữa 2 điểm p1(x,y) và p2(x,y).
    Công thức: sqrt((x2-x1)^2 + (y2-y1)^2)
    """
    return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)

def manhattan(p1, p2):
    """
    Tính khoảng cách Manhattan giữa 2 điểm.
    Công thức: |x2-x1| + |y2-y1|
    """
    return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

def heuristic(current_node_id, goal_node_id, points, h_type="euclidean"):
    """
    Hàm Heuristic h(n) cho thuật toán A*.
    """
    p1 = points[current_node_id]
    p2 = points[goal_node_id]
    if h_type == "manhattan":
        return manhattan(p1, p2)
    return euclidean(p1, p2)

def build_distance_matrix(
    points,
    graph,
    h_type="euclidean",
    speed_kmh=40,
    graph_points=None,
    return_paths=False,
):
    """
    Xây dựng ma trận khoảng cách giữa tất cả các cặp điểm giao hàng.
    """
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    from algorithms.astar import astar, calc_travel_time
    
    matrix = {}
    path_matrix = {}
    num_points = len(points)
    graph_points = graph_points or points
    
    # Hàm h_func wrap lại để truyền vào astar
    def h_func(u, v, pts):
        return heuristic(u, v, pts, h_type)

    for i in range(num_points):
        for j in range(num_points):
            if i == j:
                matrix[(i, j)] = (0, 0)
                continue
            
            # Tìm đường đi ngắn nhất từ i đến j bằng A*
            path, dist = astar(graph, i, j, graph_points, h_func)
            
            if path:
                time = calc_travel_time(dist, speed_kmh)
                matrix[(i, j)] = (dist, time)
                path_matrix[(i, j)] = path
            else:
                matrix[(i, j)] = (float("inf"), float("inf"))
                path_matrix[(i, j)] = None
                
    if return_paths:
        return matrix, path_matrix
    return matrix
