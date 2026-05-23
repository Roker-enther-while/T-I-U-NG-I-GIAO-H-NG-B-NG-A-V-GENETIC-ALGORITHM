import heapq

"""
Nguồn tham khảo cho thuật toán:
- A*: Hart, Nilsson, Raphael (1968), "A Formal Basis for the Heuristic Determination
  of Minimum Cost Paths".
- Hàng đợi ưu tiên: tài liệu Python `heapq`, dùng min-heap để lấy phần tử có ưu tiên nhỏ nhất.

Phần tự triển khai trong đề tài:
- Điều chỉnh A* cho cấu trúc graph của bài toán giao hàng: graph[u][v] là chi phí đi từ u đến v.
- Tách `astar_with_steps` để ghi lại từng bước mở rộng node, phục vụ phần minh họa trên giao diện.
- Bổ sung hàm tính thời gian di chuyển để dùng chung với báo cáo và demo.
"""

class SimplePriorityQueue:
    """
    Hàng đợi ưu tiên (Priority Queue) thủ công.
    Tham khảo: Python `heapq` triển khai Min-Heap.
    Ý tưởng lập trình: lưu tuple (priority, item), trong đó priority chính là f_score.
    Nhờ vậy A* luôn lấy được node hứa hẹn nhất với độ phức tạp O(log n).
    """
    def __init__(self):
        self.elements = []
    
    def empty(self):
        return len(self.elements) == 0
    
    def put(self, item, priority):
        # heapq.heappush lưu theo thứ tự (priority, item)
        heapq.heappush(self.elements, (priority, item))
    
    def get(self):
        # heapq.heappop lấy phần tử nhỏ nhất
        return heapq.heappop(self.elements)[1]

    def get_with_priority(self):
        return heapq.heappop(self.elements)

def reconstruct_path(came_from, start, goal):
    """
    Truy vết ngược đường đi từ đích về điểm đầu.
    Phần tự triển khai: `came_from` chỉ lưu cha tốt nhất của mỗi node, nên cần đi ngược
    từ goal về start rồi đảo danh sách để có đúng thứ tự start -> goal.
    """
    current = goal
    path = []
    while current != start:
        path.append(current)
        current = came_from[current]
    path.append(start)
    path.reverse() # Đảo ngược lại để có start -> goal
    return path

def astar(graph, start, goal, points, h_func):
    """
    Thuật toán A* tìm đường đi ngắn nhất giữa 2 điểm trên đồ thị.
    Tham khảo công thức g(n), h(n), f(n)=g(n)+h(n) từ thuật toán A* gốc.
    Phần tự triển khai theo bài toán:
    1. Khởi tạo mọi chi phí là vô cực để chỉ cập nhật khi tìm được đường tốt hơn.
    2. Mỗi lần lấy node có f_score nhỏ nhất ra khỏi priority queue.
    3. Nếu gặp goal thì truy vết đường đi bằng `came_from`.
    4. Nếu một neighbor có chi phí mới thấp hơn, cập nhật cha và đưa lại vào hàng đợi.
    """
    open_set = SimplePriorityQueue()
    open_set.put(start, 0)
    
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0
    
    f_score = {node: float('inf') for node in graph}
    f_score[start] = h_func(start, goal, points)
    
    while not open_set.empty():
        current_priority, current = open_set.get_with_priority()
        if current_priority > f_score[current]:
            continue
        
        if current == goal:
            return reconstruct_path(came_from, start, goal), g_score[goal]
        
        for neighbor, weight in graph[current].items():
            tentative_g_score = g_score[current] + weight
            
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + h_func(neighbor, goal, points)
                open_set.put(neighbor, f_score[neighbor])
                
    return None, float('inf')

def astar_with_steps(graph, start, goal, points, h_func):
    """
    Phiên bản A* trả về danh sách các bước để phục vụ việc minh họa (visualization).
    Phần này là tự triển khai cho demo: ngoài kết quả cuối, code còn lưu current/open/closed/path
    ở từng bước để giao diện giải thích được vì sao A* chọn node tiếp theo.
    """
    steps = []
    open_set_data = [{ 'node': start, 'f': h_func(start, goal, points), 'g': 0 }]
    open_set = SimplePriorityQueue()
    open_set.put(start, 0)
    
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0
    
    f_score = {node: float('inf') for node in graph}
    f_score[start] = h_func(start, goal, points)
    
    closed_set = set()
    step_count = 0
    
    while not open_set.empty():
        current_priority, current = open_set.get_with_priority()
        if current in closed_set or current_priority > f_score[current]:
            continue
        step_count += 1
        closed_set.add(current)
        
        # Tạo path hiện tại để viz
        path = []
        temp = current
        while temp in came_from:
            path.append(temp)
            temp = came_from[temp]
        path.append(start)
        path.reverse()

        # Lưu bước
        steps.append({
            'step': step_count,
            'current': current,
            'g': g_score[current],
            'h': h_func(current, goal, points),
            'f': f_score[current],
            'open': [item['node'] for item in open_set_data if item['node'] not in closed_set],
            'closed': list(closed_set),
            'path': path
        })

        if current == goal:
            return steps, reconstruct_path(came_from, start, goal), g_score[goal]
        
        for neighbor, weight in graph[current].items():
            if neighbor in closed_set:
                continue
                
            tentative_g_score = g_score[current] + weight
            
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                h_val = h_func(neighbor, goal, points)
                f_score[neighbor] = g_score[neighbor] + h_val
                open_set.put(neighbor, f_score[neighbor])
                
                # Cập nhật open_set_data để tracking
                found = False
                for item in open_set_data:
                    if item['node'] == neighbor:
                        item['f'] = f_score[neighbor]
                        item['g'] = g_score[neighbor]
                        found = True
                        break
                if not found:
                    open_set_data.append({ 'node': neighbor, 'f': f_score[neighbor], 'g': g_score[neighbor] })
                
    return steps, None, float('inf')

def calc_travel_time(distance, speed_kmh=40):
    """
    Tính thời gian di chuyển (phút).
    Phần tự triển khai: đổi đơn vị từ giờ sang phút theo công thức
    (khoảng cách / tốc độ) * 60.
    """
    if speed_kmh <= 0:
        raise ValueError("speed_kmh must be greater than 0")
    return (distance / speed_kmh) * 60

def calc_path_time(path, graph, speed_kmh=40):
    """
    Tính tổng thời gian di chuyển của toàn bộ danh sách các node.
    """
    total_dist = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        total_dist += graph[u][v]
    return calc_travel_time(total_dist, speed_kmh)

if __name__ == "__main__":
    # Test A* đơn giản
    from delivery_optimizer.graph.graph import build_graph
    from delivery_optimizer.graph.distance import heuristic
    
    pts = [
        {'id': 0, 'x': 0, 'y': 0},
        {'id': 1, 'x': 10, 'y': 0},
        {'id': 2, 'x': 10, 'y': 10}
    ]
    g = build_graph(pts, mode="full")
    path, cost = astar(g, 0, 2, pts, heuristic)
    print(f"Path: {path}, Cost: {cost}")
