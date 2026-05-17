# Kế Hoạch Chi Tiết: Tối Ưu Đường Đi Giao Hàng bằng A* và Genetic Algorithm

## Thông tin đề tài

| Mục | Nội dung |
|-----|----------|
| **Tên đề tài** | Tối ưu đường đi giao hàng bằng A* và Genetic Algorithm (GA) cho CVRPTW |
| **Môn học** | Trí Tuệ Nhân Tạo |
| **Trạng thái** | ✅ **HOÀN THÀNH** |
| **Giao diện** | **Web UI (Nature Friendly)** (Slate/Emerald aesthetic) |
| **Mô tả** | Ứng dụng A* tìm đường đi ngắn nhất. Sau đó áp dụng GA phân bổ hạm đội (Nhiều xe, Giới hạn tải trọng, Khung giờ) và sắp xếp thứ tự giao hàng tối ưu. |

---

## Mục tiêu (Đã đạt được)

- [x] Tạo dữ liệu các điểm giao hàng ngẫu nhiên (Module 1)
- [x] Tìm đường đi ngắn nhất bằng A* (Module 4-6)
- [x] Xác định thứ tự giao hàng tối ưu bằng GA (Module 8-11)
- [x] Hiển thị lộ trình giao hàng trực quan (Nature UI)
- [x] Thống kê: tổng quãng đường, tổng thời gian, số điểm giao hoàn thành.

---

## Cấu trúc thư mục Hiện tại

```
delivery_optimizer/
│
├── data/
│   └── generator.py          # Module 1: Sinh điểm ngẫu nhiên/lưới
│
├── graph/
│   ├── graph.py              # Module 2: Xây dựng Adjacency List
│   └── distance.py           # Module 3, 7: Tính khoảng cách & Matrix
│
├── algorithms/
│   ├── astar.py              # Lõi A* Step-by-step
│   └── genetic.py            # Lõi GA xử lý Multi-vehicle, Capacity, Time Windows
│
├── delivery_optimizer_demo.html # Giao diện Web UI (Nature Friendly)
├── server.py                 # Backend Flask cung cấp REST API & SSE
└── delivery_optimizer/gui.py # Desktop Launcher mở Web UI
```

---

## Cập nhật Công nghệ & Giao diện

| Thành phần | Công nghệ sử dụng | Ghi chú |
|------------|-------------------|---------|
| **Backend** | Python 3.x (Flask) | Thuật toán xây dựng thủ công (Manual implementation). Xử lý qua REST API & SSE. |
| **Giao diện** | HTML5 / CSS3 / JS | Phong cách Nature Friendly (Slate/Emerald), mượt mà, render trên Browser |
| **Đồ thị** | HTML5 Canvas | Vẽ lộ trình, xe chạy (animation), và đồ thị hội tụ (Convergence Graph) |
| **Cấu trúc** | Client-Server | Tách biệt hoàn toàn xử lý đồ họa (JS) và tính toán nặng (Python) |

---

## Phase 1 — Chuẩn bị dữ liệu (Hoàn thành)
- `generate_points()`: Hỗ trợ sinh điểm theo tọa độ thực tế.
- `build_graph()`: Hỗ trợ chế độ "Full" và "Grid".

## Phase 2 — Thuật toán A* (Hoàn thành)
- `astar()`: Tìm đường tối ưu với Heuristic Euclidean/Manhattan.
- `astar_with_steps()`: Hỗ trợ xem từng bước chạy của A* ngay trên bản đồ.

## Phase 3 — Genetic Algorithm (Hoàn thành)
- `run_ga()`: Tích hợp Elitism và OX Crossover.
- Tham số chuẩn hóa: `Pop: 120`, `Gen: 500`, `Mut: 4%`.

## Phase 4 — Giao diện & Thống kê (Hoàn thành)
- Hệ thống màu sắc Nature: Teal `#4db8a0`, Amber `#f5a623`, Lime `#6bcf7f`.
- Chế độ Step-by-step trực quan.
- Bảng so sánh hiệu quả giữa GA và lộ trình ngẫu nhiên.

---

## Checklist tiến độ (Cập nhật cuối cùng)

### Phase 1 — Dữ liệu
- [x] Viết `generate_points()`
- [x] Viết `generate_grid()`
- [x] Viết `build_graph()`
- [x] Viết `add_edge()`
- [x] Viết `euclidean()`, `manhattan()`, `heuristic()`

### Phase 2 — A*
- [x] Viết `PriorityQueue` thủ công
- [x] Viết `astar()`
- [x] Viết `reconstruct_path()`
- [x] Viết `calc_travel_time()`, `calc_path_time()`
- [x] Viết `build_distance_matrix()`

### Phase 3 — GA
- [x] Viết `random_chromosome()`, `init_population()`
- [x] Viết `fitness()`, `evaluate_population()`
- [x] Viết `tournament_selection()`
- [x] Viết `order_crossover()`
- [x] Viết `swap_mutation()`
- [x] Viết `run_ga()`

### Phase 4 — Giao diện
- [x] Thiết kế UI Nature Friendly với CustomTkinter
- [x] Tích hợp bản đồ Matplotlib vào GUI
- [x] Viết hàm `animate_delivery()` (mô phỏng xe chạy)
- [x] Vẽ đồ thị hội tụ GA
- [x] Bảng so sánh hiệu quả (Comparison Dialog)

---

*Dự án đã hoàn thành tất cả các mục tiêu đề ra với tiêu chuẩn giao diện hiện đại và cấu trúc code chặt chẽ.*
