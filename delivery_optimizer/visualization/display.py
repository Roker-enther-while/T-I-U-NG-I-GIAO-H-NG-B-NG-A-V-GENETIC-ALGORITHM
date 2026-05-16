import matplotlib.pyplot as plt
import time

def draw_map(points, graph):
    """
    Vẽ bản đồ các điểm giao hàng và các kết nối đồ thị.
    """
    plt.figure(figsize=(10, 8))
    
    # Vẽ các cạnh của đồ thị
    for u in graph:
        for v in graph[u]:
            p1, p2 = points[u], points[v]
            plt.plot([p1['x'], p2['x']], [p1['y'], p2['y']], color='gray', alpha=0.3, linestyle='--')
            
    # Vẽ các điểm
    for p in points:
        color = 'red' if p['id'] == 0 else 'blue'
        marker = 's' if p['id'] == 0 else 'o'
        plt.scatter(p['x'], p['y'], color=color, marker=marker, s=100, zorder=5)
        plt.text(p['x'] + 1, p['y'] + 1, f"{p['id']}", fontsize=12)
        
    plt.title("Bản đồ các điểm giao hàng và mạng lưới kết nối")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True)
    plt.show()

def draw_route(full_order, points, title="Lộ trình giao hàng tối ưu"):
    """
    Vẽ lộ trình tối ưu tìm được bởi GA.
    """
    plt.figure(figsize=(10, 8))
    
    # Tọa độ các điểm trong lộ trình
    x = [points[i]['x'] for i in full_order]
    y = [points[i]['y'] for i in full_order]
    
    # Vẽ các điểm
    for p in points:
        color = 'red' if p['id'] == 0 else 'blue'
        plt.scatter(p['x'], p['y'], color=color, s=100, zorder=5)
        plt.text(p['x'] + 1, p['y'] + 1, f"{p['id']}", fontsize=12)
        
    # Vẽ lộ trình có mũi tên
    for i in range(len(full_order) - 1):
        plt.annotate("", xy=(x[i+1], y[i+1]), xytext=(x[i], y[i]),
                     arrowprops=dict(arrowstyle="->", color="green", lw=2))
        
    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True)
    plt.show()

def print_stats(best_order, best_distance, best_time, num_points):
    """
    In bảng thống kê kết quả.
    """
    print("\n" + "="*50)
    print("      THỐNG KÊ KẾT QUẢ TỐI ƯU GIAO HÀNG")
    print("="*50)
    print(f"1. Thứ tự giao hàng: {' -> '.join(map(str, best_order))}")
    print(f"2. Tổng quãng đường: {best_distance:.2f} km")
    
    hours = int(best_time // 60)
    minutes = int(best_time % 60)
    print(f"3. Tổng thời gian di chuyển: {hours} giờ {minutes} phút")
    
    print(f"4. Số điểm hoàn thành: {num_points - 1}")
    print("="*50 + "\n")

def plot_convergence(history):
    """
    Vẽ đồ thị hội tụ của GA (Fitness qua các thế hệ).
    """
    plt.figure(figsize=(8, 5))
    plt.plot(history, color='orange', lw=2)
    plt.title("Đồ thị hội tụ của Genetic Algorithm")
    plt.xlabel("Thế hệ (Generations)")
    plt.ylabel("Tổng quãng đường (Fitness)")
    plt.grid(True)
    plt.show()

def animate_route(full_order, points, delay=0.5):
    """
    Minh họa từng bước di chuyển (Animation đơn giản).
    """
    print("Đang khởi tạo animation lộ trình...")
    # Trong môi trường script, việc animate plt thường cần plt.pause()
    plt.figure(figsize=(10, 8))
    
    # Vẽ nền
    for p in points:
        color = 'red' if p['id'] == 0 else 'blue'
        plt.scatter(p['x'], p['y'], color=color, s=100)
    
    for i in range(len(full_order) - 1):
        p1 = points[full_order[i]]
        p2 = points[full_order[i+1]]
        plt.plot([p1['x'], p2['x']], [p1['y'], p2['y']], color='green', lw=2)
        plt.title(f"Bước {i+1}: Từ {full_order[i]} đến {full_order[i+1]}")
        plt.pause(delay)
        
    plt.show()
