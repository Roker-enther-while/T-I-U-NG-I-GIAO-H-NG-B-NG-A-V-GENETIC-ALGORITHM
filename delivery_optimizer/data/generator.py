import random

def generate_points(n, x_range=(0, 100), y_range=(0, 100)):
    """
    Sinh n điểm giao hàng ngẫu nhiên trong phạm vi cho trước.
    Giải thuật: Sử dụng hàm random.uniform để tạo tọa độ x, y ngẫu nhiên.
    Mỗi điểm được biểu diễn bằng một dictionary chứa các thông tin cơ bản.
    """
    points = []
    # Điểm đầu tiên (id=0) luôn là Kho hàng (Depot)
    points.append({
        "id": 0,
        "x": (x_range[0] + x_range[1]) / 2,
        "y": (y_range[0] + y_range[1]) / 2,
        "name": "Kho hàng",
        "status": "depot"
    })
    
    for i in range(1, n):
        points.append({
            "id": i,
            "x": random.uniform(x_range[0], x_range[1]),
            "y": random.uniform(y_range[0], y_range[1]),
            "name": f"Điểm giao {i}",
            "status": "pending"
        })
    return points

def generate_grid(rows, cols, spacing=10):
    """
    Tạo lưới các điểm theo dạng ô vuông (Grid).
    Giải thuật: Sử dụng vòng lặp lồng nhau qua số hàng và số cột để tạo tọa độ cố định.
    Mỗi giao điểm của lưới là một vị trí tiềm năng.
    """
    points = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            points.append({
                "id": idx,
                "x": c * spacing,
                "y": r * spacing,
                "name": f"Node ({r},{c})",
                "status": "pending"
            })
            idx += 1
    return points

if __name__ == "__main__":
    # Test độc lập Module 1
    print("Testing generate_points:")
    pts = generate_points(5)
    for p in pts:
        print(p)
    
    print("\nTesting generate_grid:")
    grid = generate_grid(3, 3)
    for g in grid:
        print(g)
