# Báo Cáo Ánh Xạ Thuật Toán A* và GA Lên Giao Diện (UI)

Dưới đây là chi tiết cách các tham số lõi của mã nguồn Python (`astar.py` và `genetic.py`) được kết nối (map) trực tiếp lên giao diện HTML (`delivery_optimizer_demo.html`). Bạn có thể dùng tài liệu này để giải thích cho giảng viên về việc phần mềm thực sự truyền biến từ front-end xuống back-end như thế nào.

---

## 1. Thuật Toán A* (`astar.py`)

### Tham số đầu vào (Input)
*   **Hàm `h_func` (Heuristic)**:
    *   *Trên UI:* Nằm trong ngăn kéo `⚙ CẤU HÌNH` > **Heuristic A***.
    *   *Ánh xạ:* Chuyển đổi giữa `EUCLIDEAN DISTANCE` (Đường thẳng) và `MANHATTAN DISTANCE` (Vuông góc). Khi người dùng đổi dropdown này, biến `heuristic` ở backend sẽ thay đổi công thức tính.
*   **`speed_kmh` (Tốc độ)**:
    *   *Trên UI:* Nằm trong ngăn kéo cấu hình > Thanh kéo **Tốc độ xe (km/h)**.
    *   *Ánh xạ:* Biến đổi `distance` thành `time` để tính toán khung giờ giao hàng cho VRP.

### Đầu ra trực quan hóa (Visualization / Output)
Toàn bộ logic của hàm `astar_with_steps()` được ánh xạ trực tiếp lên bảng **`▸ A* STEP-BY-STEP`** (xuất hiện ở góc trái màn hình khi chạy chế độ Tuần tự hoặc bấm nút ⏭ A* STEP):
*   **`step_count`**: Ánh xạ lên trường **BƯỚC** (Hiển thị A* đang lặp vòng lặp thứ bao nhiêu).
*   **`current`**: Ánh xạ lên trường **NODE XÉT** (Tọa độ hoặc ID của node đang được duyệt).
*   **`g_score`, `h_func`, `f_score`**: Ánh xạ lần lượt lên **g(n) THỰC TẾ**, **h(n) ƯỚC TÍNH**, **f(n) = g + h**.
*   **`open_set` và `closed_set`**: Ánh xạ lên danh sách **OPEN LIST** (các node tiềm năng) và **CLOSED LIST** (các node đã duyệt xong).
*   **`path`**: Ánh xạ thành các đoạn đường line màu xanh lá cây đứt đoạn vẽ trên bản đồ (`<canvas id="mc">`).

---

## 2. Giải thuật Di truyền GA (`genetic.py`)

### Tham số tinh chỉnh (Hyperparameters)
Tất cả các tham số truyền vào hàm `run_ga(...)` đều nằm trong mục **Tham số GA** của ngăn kéo `⚙ CẤU HÌNH`:
*   **`pop_size`**: Ánh xạ từ thanh kéo **Quần thể** (Mặc định 80).
*   **`generations`**: Ánh xạ từ thanh kéo **Thế hệ** (Mặc định 300).
*   **`mut_rate`**: Ánh xạ từ thanh kéo **Tỷ lệ đột biến** (Mặc định 3%).
*   **Các ràng buộc mở rộng (VRP Constraints)**:
    *   `vehicles`: Ánh xạ từ thanh kéo **Số xe giao hàng**.
    *   `capacity`: Ánh xạ từ thanh kéo **Tải trọng xe**.
    *   `time_windows`: Được kích hoạt từ nút bấm **⏰ BẬT KHUNG GIỜ GIAO**. Khi bật, hàm `constrained_fitness` trong code Python sẽ tự động cộng điểm phạt (penalty) nếu đến trễ.

### Đầu ra trực quan hóa (Visualization / Output)
Sự tiến hóa của GA được ánh xạ trực tiếp theo thời gian thực (Real-time):
*   **Tiến trình vòng lặp `for gen in range(generations)`**:
    *   Được bắt bằng hàm `progress_callback` trong Python và đẩy qua Server-Sent Events (SSE) xuống UI.
    *   *Trên UI:* Hiển thị ở mục **Tiến trình GA** trong ngăn kéo cấu hình (Thế hệ x/300) và vẽ thanh Progress bar màu xanh lá chạy dần.
*   **`best_history` (Mảng lưu fitness tốt nhất mỗi 10 thế hệ)**:
    *   *Trên UI:* Được vẽ thành **Biểu đồ hội tụ** (Convergence Chart) trong ngăn kéo `📊 KẾT QUẢ` và ô log nhỏ ở góc trái dưới cùng (`#logbox`).
*   **`best_order` (Nhiễm sắc thể tốt nhất sau khi kết thúc)**:
    *   *Trên UI:* Được giải mã thành mảng tọa độ và vẽ thành **Tuyến đường di chuyển hoàn chỉnh** nối tất cả các điểm giao hàng trên bản đồ đồ họa.
*   **`total_dist` & `total_time`**:
    *   *Trên UI:* Bắn thẳng vào **HUD Dưới cùng** (TỔNG KM / THỜI GIAN) và hiển thị lúc chiếc xe chạy dọc theo lộ trình.
