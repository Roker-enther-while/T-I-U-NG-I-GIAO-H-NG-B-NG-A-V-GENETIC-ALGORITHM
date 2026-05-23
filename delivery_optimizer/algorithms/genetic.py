import random

"""
Nguồn tham khảo cho thuật toán:
- Genetic Algorithm: Holland (1975), "Adaptation in Natural and Artificial Systems".
- Order Crossover (OX): Davis (1985), kỹ thuật lai ghép phổ biến cho bài toán hoán vị/TSP.
- Tournament selection và elitism là các toán tử chuẩn trong nhóm Genetic Algorithm.

Phần tự triển khai trong đề tài:
- Mã hóa chromosome là thứ tự các điểm giao hàng, bỏ depot 0 để tránh tạo nghiệm sai.
- Fitness dùng ma trận chi phí do A* tạo ra, nhờ đó GA tối ưu thứ tự giao trên đường đi hợp lệ.
- Bổ sung nhiều xe, tải trọng và time window bằng cách tách route và cộng penalty khi vi phạm.
"""

def random_chromosome(num_points):
    """
    Tạo 1 cá thể (chromosome) ngẫu nhiên.
    Tham khảo: cách mã hóa hoán vị trong GA cho bài toán định tuyến/TSP.
    Phần tự triển khai: điểm 0 là kho hàng (Depot), nên chỉ xáo trộn các điểm còn lại.
    Chromosome là một hoán vị (permutation) của các chỉ số điểm giao hàng.
    """
    indices = list(range(1, num_points))
    random.shuffle(indices)
    return indices

def init_population(size, num_points):
    """
    Khởi tạo quần thể ban đầu với 'size' cá thể.
    """
    return [random_chromosome(num_points) for _ in range(size)]

def fitness(chromosome, distance_matrix):
    """
    Tính hàm thích nghi (Fitness) của một cá thể.
    Tham khảo: GA thường chuyển chất lượng nghiệm thành một điểm fitness.
    Phần tự triển khai: bài toán đang cần minimize, nên fitness chính là tổng quãng đường
    Depot -> P1 -> P2 -> ... -> Pn -> Depot, lấy từ `distance_matrix`.
    """
    if not chromosome:
        return 0

    total_dist = 0
    # Từ Depot đến điểm đầu tiên
    total_dist += distance_matrix[(0, chromosome[0])][0]
    
    # Giữa các điểm giao hàng
    for i in range(len(chromosome) - 1):
        u, v = chromosome[i], chromosome[i+1]
        total_dist += distance_matrix[(u, v)][0]
    
    # Từ điểm cuối cùng quay về Depot
    total_dist += distance_matrix[(chromosome[-1], 0)][0]
    
    return total_dist

def split_routes(chromosome, vehicles=1, demands=None, capacity=None):
    """
    Tách một chromosome thành nhiều tuyến xe.
    Phần tự triển khai:
    1. Nếu chỉ có 1 xe thì giữ nguyên toàn bộ thứ tự giao.
    2. Nếu có tải trọng, ưu tiên không vượt capacity và vẫn chia tương đối đều cho các xe.
    3. Nếu không có tải trọng, chia vòng tròn theo chỉ số để các xe đều có điểm giao.
    """
    vehicles = max(1, int(vehicles or 1))
    if vehicles == 1:
        return [chromosome[:]]

    routes = [[] for _ in range(vehicles)]
    if capacity and demands:
        vehicle_idx = 0
        load = 0
        for index, point in enumerate(chromosome):
            demand = demands.get(point, 0)
            remaining_points = len(chromosome) - index
            remaining_vehicles = vehicles - vehicle_idx
            max_current_size = max(1, (remaining_points + remaining_vehicles - 1) // remaining_vehicles)
            should_balance = (
                routes[vehicle_idx]
                and len(routes[vehicle_idx]) >= max_current_size
                and remaining_points >= remaining_vehicles - 1
            )
            should_split_capacity = routes[vehicle_idx] and load + demand > capacity
            if (should_balance or should_split_capacity) and vehicle_idx < vehicles - 1:
                vehicle_idx += 1
                load = 0
            routes[vehicle_idx].append(point)
            load += demand
        return routes

    for index, point in enumerate(chromosome):
        routes[index % vehicles].append(point)
    return routes

def route_distance(route, distance_matrix):
    """
    Tính quãng đường một tuyến xe đơn lẻ.
    Phần tự triển khai: tự thêm depot 0 ở đầu/cuối để route con vẫn là một chuyến hoàn chỉnh.
    """
    if not route:
        return 0
    total = distance_matrix[(0, route[0])][0]
    for i in range(len(route) - 1):
        total += distance_matrix[(route[i], route[i + 1])][0]
    total += distance_matrix[(route[-1], 0)][0]
    return total

def constrained_fitness(
    chromosome,
    distance_matrix,
    vehicles=1,
    demands=None,
    capacity=None,
    time_windows=None,
    speed_kmh=40,
    service_time=5,
    overload_penalty=10000,
    late_penalty=100,
):
    """
    Fitness có ràng buộc cho nhiều xe, tải trọng và khung giờ.
    Phần tự triển khai:
    1. Tách chromosome thành các route theo số xe.
    2. Cộng quãng đường thực tế của từng route.
    3. Nếu vượt tải hoặc giao trễ, cộng penalty để GA tự loại nghiệm kém.
    """
    routes = split_routes(chromosome, vehicles, demands, capacity)
    total = 0
    penalty = 0

    for route in routes:
        total += route_distance(route, distance_matrix)

        if capacity and demands:
            load = sum(demands.get(point, 0) for point in route)
            if load > capacity:
                penalty += (load - capacity) * overload_penalty

        if time_windows:
            elapsed = 0
            current = 0
            for point in route:
                dist = distance_matrix[(current, point)][0]
                elapsed += (dist / speed_kmh) * 60
                start, end = time_windows.get(point, (0, float("inf")))
                if elapsed < start:
                    elapsed = start
                if elapsed > end:
                    penalty += (elapsed - end) * late_penalty
                elapsed += service_time
                current = point

    return total + penalty

def evaluate_population(population, distance_matrix, fitness_func=None):
    """
    Đánh giá toàn bộ quần thể. Trả về danh sách (fitness, chromosome) được sắp xếp.
    """
    evaluated = []
    fitness_func = fitness_func or (lambda chromo: fitness(chromo, distance_matrix))
    for chromo in population:
        fit = fitness_func(chromo)
        evaluated.append((fit, chromo))
    # Sắp xếp theo fitness tăng dần (tốt nhất ở đầu)
    evaluated.sort(key=lambda x: x[0])
    return evaluated

def tournament_selection(evaluated_pop, k=3):
    """
    Chọn lọc tự nhiên bằng phương pháp Tournament.
    Tham khảo: tournament selection trong GA.
    Ý tưởng lập trình: chọn ngẫu nhiên k cá thể, rồi lấy cá thể có fitness thấp nhất.
    Cách này tạo áp lực chọn lọc nhưng vẫn giữ được tính đa dạng.
    """
    selection = random.sample(evaluated_pop, min(k, len(evaluated_pop)))
    selection.sort(key=lambda x: x[0])
    return selection[0][1]

def order_crossover(parent1, parent2):
    """
    Lai ghép thứ tự (OX Crossover).
    Tham khảo: Order Crossover (OX) của Davis cho chromosome dạng hoán vị.
    Các bước triển khai trong code:
    1. Chọn một đoạn con ngẫu nhiên từ Parent 1 và giữ nguyên vị trí trong Child.
    2. Điền các gen còn lại từ Parent 2 vào Child theo đúng thứ tự xuất hiện của chúng trong P2,
       nhằm giữ lại cấu trúc thứ tự tương đối.
    """
    size = len(parent1)
    if size < 2:
        return parent1[:]

    child = [None] * size
    
    # Chọn đoạn cắt
    start, end = sorted(random.sample(range(size), 2))
    child[start:end+1] = parent1[start:end+1]
    
    # Điền các vị trí còn lại từ parent 2
    p2_pointer = 0
    for i in range(size):
        if child[i] is None:
            while parent2[p2_pointer] in child:
                p2_pointer += 1
            child[i] = parent2[p2_pointer]
            
    return child

def swap_mutation(chromosome, rate=0.05):
    """
    Đột biến hoán đổi (Swap Mutation).
    Tham khảo: mutation là toán tử chuẩn trong GA.
    Phần tự triển khai: với xác suất `rate`, chọn 2 vị trí ngẫu nhiên và hoán đổi giá trị
    để tạo biến thể mới, giúp thuật toán giảm nguy cơ kẹt ở tối ưu cục bộ.
    """
    if len(chromosome) >= 2 and random.random() < rate:
        idx1, idx2 = random.sample(range(len(chromosome)), 2)
        chromosome[idx1], chromosome[idx2] = chromosome[idx2], chromosome[idx1]
    return chromosome

def run_ga(
    distance_matrix,
    num_points,
    pop_size=100,
    generations=500,
    elite_size=10,
    cross_rate=0.8,
    mut_rate=0.05,
    progress_callback=None,
    vehicles=1,
    demands=None,
    capacity=None,
    time_windows=None,
    speed_kmh=40,
    service_time=5,
):
    """
    Vòng lặp chính của Giải thuật Di truyền (Genetic Algorithm).
    Các bước song song với code:
    1. Khởi tạo quần thể ban đầu.
    2. Đánh giá fitness và lưu lịch sử nghiệm tốt nhất.
    3. Giữ lại elite để không mất nghiệm tốt.
    4. Chọn cha mẹ bằng tournament, lai ghép OX, sau đó đột biến swap.
    5. Lặp qua nhiều thế hệ rồi trả về thứ tự giao hàng tốt nhất.
    """
    if num_points < 1:
        return [], 0, 0, [], []
    if num_points == 1:
        return [0, 0], 0, 0, [0], [[0, 0]]

    pop_size = max(1, pop_size)
    elite_size = max(0, min(elite_size, pop_size))

    # 1. Khởi tạo quần thể
    population = init_population(pop_size, num_points)
    best_history = []
    use_constraints = vehicles > 1 or bool(demands) or bool(time_windows)

    def fitness_func(chromo):
        if use_constraints:
            return constrained_fitness(
                chromo,
                distance_matrix,
                vehicles=vehicles,
                demands=demands,
                capacity=capacity,
                time_windows=time_windows,
                speed_kmh=speed_kmh,
                service_time=service_time,
            )
        return fitness(chromo, distance_matrix)
    
    for gen in range(generations):
        # 2. Đánh giá
        evaluated = evaluate_population(population, distance_matrix, fitness_func)
        best_fit, best_chromo = evaluated[0]
        best_history.append(best_fit)
        
        # Gọi callback để cập nhật giao diện
        if progress_callback and gen % 10 == 0:
            progress_callback(gen, best_fit, best_chromo, best_history)
        
        # 3. Tạo thế hệ mới
        new_population = []
        
        # Elitism: Giữ lại những cá thể tốt nhất
        for i in range(elite_size):
            new_population.append(evaluated[i][1])
            
        # Lai ghép và đột biến để lấp đầy quần thể
        while len(new_population) < pop_size:
            p1 = tournament_selection(evaluated)
            p2 = tournament_selection(evaluated)
            
            if random.random() < cross_rate:
                child = order_crossover(p1, p2)
            else:
                child = p1[:]
            
            child = swap_mutation(child, mut_rate)
            new_population.append(child)
            
        population = new_population
        
        if (gen + 1) % 100 == 0:
            print(f"Generation {gen+1}: Best Fitness = {best_fit:.2f}")
            
    # Kết quả cuối cùng
    final_eval = evaluate_population(population, distance_matrix, fitness_func)
    _best_score, best_order = final_eval[0]
    routes = split_routes(best_order, vehicles, demands, capacity)
    best_fit = sum(route_distance(route, distance_matrix) for route in routes)
    
    # Tính tổng thời gian cho lộ trình tốt nhất
    total_time = 0
    for route in routes:
        if not route:
            continue
        route_time = distance_matrix[(0, route[0])][1]
        for i in range(len(route) - 1):
            route_time += distance_matrix[(route[i], route[i+1])][1]
        route_time += distance_matrix[(route[-1], 0)][1]
        total_time = max(total_time, route_time)
    
    # Trả về: (thứ tự, quãng đường, thời gian, lịch sử)
    # Thứ tự đầy đủ bao gồm Depot ở đầu và cuối
    full_routes = [[0] + route + [0] for route in routes if route]
    full_order = []
    for route in full_routes:
        if not full_order:
            full_order.extend(route)
        else:
            full_order.extend(route[1:])
    return full_order, best_fit, total_time, best_history, full_routes

if __name__ == "__main__":
    # Test GA với dữ liệu giả lập
    fake_matrix = {}
    n = 5
    for i in range(n):
        for j in range(n):
            fake_matrix[(i,j)] = (random.uniform(5, 20), random.uniform(10, 30))
    
    res = run_ga(fake_matrix, n, generations=50)
    print(f"Best Order: {res[0]}")
    print(f"Best Distance: {res[1]:.2f}")
