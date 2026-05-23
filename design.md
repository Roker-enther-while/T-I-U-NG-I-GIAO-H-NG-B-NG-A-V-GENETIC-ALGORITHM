# Tài Liệu Thiết Kế: Tối Ưu Đường Đi Giao Hàng Bằng A* và Genetic Algorithm

## 1. Tổng Quan Hệ Thống (System Overview)
Hệ thống được thiết kế để giải quyết bài toán giao hàng có giới hạn tải trọng và khung thời gian (CVRPTW - Capacitated Vehicle Routing Problem with Time Windows) bằng cách kết hợp hai thuật toán cốt lõi:
- **A-Star (A*)**: Tìm đường đi thực tế ngắn nhất giữa hai điểm bất kỳ trên bản đồ đường phố mô phỏng.
- **Genetic Algorithm (GA)**: Tối ưu hóa thứ tự các điểm giao hàng và phân bổ cho nhiều xe (Multiple Vehicles) tuân thủ giới hạn tải trọng (Capacity) và khung giờ giao hàng (Time Windows) để đạt được tổng chi phí (quãng đường và thời gian) nhỏ nhất.

Phiên bản hiện tại tách rõ các mode xử lý: tuyến tuần tự ban đầu, A* tuần tự, GA tối ưu và chế độ so sánh A* vs GA. Cơ chế A* + GA không còn là một mode chạy riêng. A* được dùng để tìm đường hợp lệ trên mạng đường và tạo dữ liệu path phục vụ hiển thị/đối chiếu; GA tối ưu thứ tự giao hàng theo metric Euclid, sau đó backend tính lại quãng đường thực tế và path chi tiết để vẽ lên giao diện.

## 2. Kiến Trúc Cụ Thể (Architecture Design)
Hệ thống chia làm 4 module chính (Phases):

### 2.1. Module Dữ Liệu & Đồ Thị (Data & Graph)
- **generator.py**: Chịu trách nhiệm sinh các điểm giao hàng (x, y) ngẫu nhiên và tạo bản đồ lưới.
- **graph.py**: Biểu diễn bản đồ dưới dạng đồ thị (Adjacency List) hỗ trợ di chuyển 4 hướng (lên, xuống, trái, phải).
- **distance.py**: Định nghĩa các hàm heuristic (Manhattan, Euclidean) dùng cho thuật toán A*.

### 2.2. Module Tìm Đường (Pathfinding - A*)
- **astar.py**: Cài đặt thuật toán A*. 
  - `g_score`: Chi phí thực tế từ điểm xuất phát.
  - `f_score`: `g_score + h_score` (h_score ước lượng từ Heuristic).
  - Sử dụng cấu trúc dữ liệu PriorityQueue để lưu trữ các node đang xét (Open list).
- **Distance Matrix**: Từ danh sách điểm giao hàng, chạy A* cho mọi cặp điểm để xây dựng ma trận khoảng cách NxN (D). Chi phí này là chi phí thực tế (đã tránh vật cản) chứ không phải khoảng cách đường chim bay.

### 2.3. Module Tối Ưu Lộ Trình (Optimization - Genetic Algorithm)
- **genetic.py**: Nhận đầu vào là ma trận metric dùng cho GA. Bản hiện tại dùng metric Euclid khi tối ưu GA, sau đó tính lại `actual_dist` và `route_paths` theo backend để hiển thị tuyến thực tế.
  - **Mã hóa (Encoding)**: Permutation (Hoán vị). Mỗi NST (Chromosome) là một dãy thứ tự các điểm giao hàng. Ví dụ: `[3, 1, 4, 2]`.
  - **Hàm thích nghi (Fitness Function)**: Tổng chi phí đường đi dựa trên ma trận metric được chọn. Fitness càng nhỏ càng tốt.
  - **Toán tử chọn lọc (Selection)**: Tournament Selection (chọn nhóm ngẫu nhiên và lấy phần tử tốt nhất).
  - **Toán tử lai ghép (Crossover)**: Order Crossover (OX) - Lai ghép bảo toàn thứ tự để tránh trùng lặp điểm giao.
  - **Toán tử đột biến (Mutation)**: Swap Mutation - Hoán đổi ngẫu nhiên vị trí của 2 điểm.
  - **Chia tuyến nhiều xe**: `split_routes()` phân phối nghiệm GA thành nhiều route theo số xe người dùng chọn, đồng thời vẫn xét tải trọng nếu cấu hình capacity được bật.

### 2.4. Module Giao Diện (Visualization & Web UI)
- **HTML5 / JS / Flask**: Giao diện người dùng sử dụng công nghệ Web thay vì Tkinter, được thiết kế theo phong cách Nature Friendly & Modern (Slate/Emerald):
  - Hiển thị bản đồ tương tác với HTML5 Canvas mượt mà.
  - Giao tiếp trực tiếp với lõi Python (Backend) qua REST API (Flask) và Server-Sent Events (SSE) để truyền tham số và nhận kết quả realtime.
  - Hiển thị animation hành trình xe chạy song song (nhiều xe cùng lúc).
  - Cung cấp các công cụ so sánh trực quan và biểu đồ hội tụ (Convergence Graph) của GA.
  - Chỉ giữ một control **Số xe giao hàng**. Control này áp dụng cho GA và chế độ so sánh; tuyến tuần tự ban đầu và A* tuần tự chỉ dùng một tuyến đối chiếu.

### 2.5. Module Nhật Ký Chạy Thuật Toán (Algorithm Run Logs)
- **logging_utils.py**: Ghi log có cấu trúc dạng JSONL cho từng lần chạy thuật toán.
- Các file mới nhất được đặt tại `logs/algorithm_runs/latest_astar.jsonl` và `latest_ga.jsonl` khi bật ghi log thuật toán.
- Thư mục `logs/algorithm_runs/history/` lưu bản lịch sử theo `run_id`, giúp demo lại quá trình chạy và đối chiếu kết quả.
- Các event chính gồm `start`, `matrix_done`, `metric_matrix_ready`, `baseline_ready`, `generation_progress`, `done`, `error`.

## 3. Luồng Dữ Luệu (Data Workflow)
1. Sinh N điểm giao hàng ngẫu nhiên trên bản đồ (Generator).
2. Xây dựng đồ thị lưới cho bản đồ (Graph).
3. Duyệt mọi cặp điểm giao hàng (i, j), chạy A* để tìm chi phí đường đi thực tế. Lưu vào ma trận chi phí D.
4. Ghi log A* để lưu cấu hình, kích thước ma trận và số cặp path đã tạo.
5. Khởi tạo quần thể GA (danh sách các hoán vị điểm giao hàng).
6. Vòng lặp GA (Evaluations -> Selection -> Crossover -> Mutation) dùng metric Euclid để tính fitness và tìm thứ tự giao hàng tốt.
7. Chia nghiệm tốt nhất thành nhiều tuyến theo số xe đã cấu hình.
8. Ghi log GA gồm tiến trình thế hệ, route cuối, `best_dist`, `actual_dist` và `route_count`.
9. Truy xuất lại đường đi chi tiết (từ A*) dựa vào thứ tự tối ưu để vẽ lên giao diện.

## 4. Các Ràng Buộc & Giả Định (Constraints & Assumptions)
- Hệ thống hỗ trợ định tuyến cho một hạm đội gồm nhiều xe (Multiple Vehicles).
- Các đơn hàng có thể có yêu cầu về khung giờ giao (Time Windows).
- Các xe có giới hạn về tải trọng (Capacity).
- Xe giao hàng bắt đầu từ một kho hàng cố định.
- Vận tốc di chuyển của xe là hằng số được tùy chỉnh trên giao diện.
- Trọng tâm hiện tại là trình bày rõ hai vai trò: A* tìm đường hợp lệ trên đường phố cho tuyến tuần tự/hiển thị path, còn GA phân bổ và sắp xếp thứ tự giao hàng tối ưu gần đúng cho toàn bộ hạm đội xe.
