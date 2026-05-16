# Tài Liệu Thiết Kế: Tối Ưu Đường Đi Giao Hàng Bằng A* và Genetic Algorithm

## 1. Tổng Quan Hệ Thống (System Overview)
Hệ thống được thiết kế để giải quyết bài toán giao hàng (Vehicle Routing Problem - VRP) cho một xe bằng cách kết hợp hai thuật toán cốt lõi:
- **A-Star (A*)**: Tìm đường đi ngắn nhất giữa hai điểm bất kỳ trên bản đồ lưới (grid) tránh các vật cản (nếu có).
- **Genetic Algorithm (GA)**: Tối ưu hóa thứ tự các điểm giao hàng để đạt được tổng chi phí (quãng đường và thời gian) nhỏ nhất.

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
- **genetic.py**: Nhận đầu vào là ma trận khoảng cách D từ module A*.
  - **Mã hóa (Encoding)**: Permutation (Hoán vị). Mỗi NST (Chromosome) là một dãy thứ tự các điểm giao hàng. Ví dụ: `[3, 1, 4, 2]`.
  - **Hàm thích nghi (Fitness Function)**: Tổng chi phí đường đi dựa trên ma trận khoảng cách. Fitness càng nhỏ càng tốt.
  - **Toán tử chọn lọc (Selection)**: Tournament Selection (chọn nhóm ngẫu nhiên và lấy phần tử tốt nhất).
  - **Toán tử lai ghép (Crossover)**: Order Crossover (OX) - Lai ghép bảo toàn thứ tự để tránh trùng lặp điểm giao.
  - **Toán tử đột biến (Mutation)**: Swap Mutation - Hoán đổi ngẫu nhiên vị trí của 2 điểm.

### 2.4. Module Giao Diện (Visualization & GUI)
- **display.py / gui.py**: Giao diện người dùng sử dụng `Tkinter` (hoặc `Pygame` / `Matplotlib` tùy chọn) để:
  - Hiển thị bản đồ và các điểm giao hàng.
  - Hiển thị animation đường đi A* và lộ trình tổng thể từ GA.
  - Biểu đồ hội tụ (Convergence Graph) của GA.

## 3. Luồng Dữ Luệu (Data Workflow)
1. Sinh N điểm giao hàng ngẫu nhiên trên bản đồ (Generator).
2. Xây dựng đồ thị lưới cho bản đồ (Graph).
3. Duyệt mọi cặp điểm giao hàng (i, j), chạy A* để tìm chi phí đường đi thực tế. Lưu vào ma trận chi phí D.
4. Khởi tạo quần thể GA (danh sách các hoán vị điểm giao hàng).
5. Vòng lặp GA (Evaluations -> Selection -> Crossover -> Mutation) sử dụng ma trận D để tính fitness.
6. Lấy cá thể tốt nhất sau M thế hệ -> Thứ tự điểm giao tối ưu.
7. Truy xuất lại đường đi chi tiết (từ A*) dựa vào thứ tự tối ưu để vẽ lên giao diện.

## 4. Các Ràng Buộc & Giả Định (Constraints & Assumptions)
- Xe giao hàng bắt đầu từ một kho hàng cố định.
- Vận tốc di chuyển của xe là hằng số để tính toán thời gian.
- Trọng tâm nằm ở việc kết hợp A* để vượt chướng ngại vật trên đường và GA để sắp xếp lịch trình.
