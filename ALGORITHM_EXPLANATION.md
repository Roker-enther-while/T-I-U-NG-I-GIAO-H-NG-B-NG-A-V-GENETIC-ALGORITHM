# Giải Phẫu Thuật Toán A* và Genetic Algorithm (Góc Nhìn Kỹ Sư Áp Dụng)

Tài liệu này giải thích cách hoạt động của hai thuật toán cốt lõi trong dự án (`astar.py` và `genetic.py`) từ góc độ của một người viết code ứng dụng/vận hành hệ thống. Thay vì đi sâu vào chứng minh toán học, tài liệu tập trung vào ý nghĩa thực tiễn của các tham số và cách hệ thống phản ứng khi chúng bị thay đổi.

---

## 1. Thuật Toán A* (`delivery_optimizer/algorithms/astar.py`)

**Nhiệm vụ chính:** Tìm một đường đi khả thi và ngắn nhất giữa **hai điểm cụ thể** trên bản đồ (có xét đến vật cản/đường cấm). A* trong dự án này đóng vai trò là "mắt thần", giúp hệ thống biết được khoảng cách thực tế thay vì chỉ đo đường chim bay.

### Các tham số và biến số cốt lõi:

*   **`graph`**: Đại diện cho "bản đồ mạng lưới đường đi" (Adjacency List). Nó chứa thông tin từ node A có thể đi đến node B, C với chi phí là bao nhiêu. 
    *   *Thực hành:* Nếu bạn can thiệp vào `graph` (ví dụ xóa một cạnh kết nối), thuật toán sẽ hiểu khu vực đó là ngõ cụt hoặc bức tường và tự động đi vòng hướng khác.
*   **`start` & `goal`**: ID của điểm xuất phát và điểm đích.
*   **`h_func` (Hàm Heuristic)**: Là "kim chỉ nam" của thuật toán. Nó ước lượng khoảng cách đường thẳng từ vị trí hiện tại đến đích.
    *   *Nếu thay đổi luôn trả về `0`*: Thuật toán biến thành Dijkstra (tìm kiếm mù quáng tản ra mọi hướng). Chạy rất chậm nhưng luôn ra kết quả đúng.
    *   *Nếu nhân lên nhiều lần (vd: `h_func * 10`)*: Thuật toán trở nên "tham lam" (Greedy Best-First Search), cắm đầu chạy thẳng về hướng đích. Chạy cực kỳ nhanh nhưng có thể đâm vào vật cản rồi kẹt, hoặc tạo ra đường đi vòng vèo không tối ưu.
*   **`g_score`**: Chi phí **thực tế** đã đi từ điểm `start` đến node hiện tại.
*   **`f_score`**: Tổng chi phí dự kiến (`f = g + h`). Đây là giá trị quan trọng nhất để quyết định "bước tiếp theo nên đi vào ô nào". Hàng đợi ưu tiên (`SimplePriorityQueue`) luôn nhả ra node có `f_score` thấp nhất.

### Các hàm chính:
*   `astar(...)`: Phiên bản chạy ngầm (backend) không lưu vết, xử lý với tốc độ tối đa để nhanh chóng tạo ra ma trận khoảng cách.
*   `astar_with_steps(...)`: Sinh ra mảng dữ liệu từng bước duyệt. Nếu bạn sửa thuật toán ở đây, nó sẽ ảnh hưởng trực tiếp đến hiệu ứng hoạt họa (animation) đang hiển thị trên giao diện web.

---

## 2. Genetic Algorithm - Giải thuật Di truyền (`delivery_optimizer/algorithms/genetic.py`)

**Nhiệm vụ chính:** Giải bài toán tối ưu tổ hợp định tuyến. Trả lời câu hỏi: "Nên phục vụ các điểm giao hàng theo thứ tự nào để tổng quãng đường là ngắn nhất?".

### Cấu trúc Dữ liệu:

*   **`chromosome` (Cá thể/Nhiễm sắc thể)**: Là một mảng (list) chứa thứ tự các điểm giao. Ví dụ: `[3, 1, 4, 2]`. Giá trị này đại diện cho 1 lộ trình cụ thể: *Từ Kho -> điểm 3 -> điểm 1 -> điểm 4 -> điểm 2 -> về Kho*. Điểm `0` (Kho) được ngầm hiểu ở hai đầu.
*   **`distance_matrix`**: Ma trận tra cứu nhanh chi phí từ `u` đến `v`. *Lưu ý:* GA hoàn toàn "mù" về bản đồ, nó chỉ biết khoảng cách thông qua ma trận này. Nếu ma trận bị cung cấp sai (khoảng cách đường chim bay), GA sẽ vô tình chỉ đạo xe đâm xuyên vật cản.

### Các tham số tinh chỉnh chiến lược trong `run_ga(...)`:

Đây là nơi bạn (kỹ sư vận hành) trực tiếp can thiệp để cân bằng giữa Tốc độ và Độ chính xác:

*   **`pop_size` (Kích thước quần thể - mặc định 100)**: Số lượng các lộ trình ngẫu nhiên được sinh ra trong một thế hệ.
    *   *Nếu tăng (vd: 500)*: Thuật toán quét được không gian rất rộng, dễ tìm ra đường tối ưu tuyệt đối nhưng CPU phải xử lý nặng nề hơn.
    *   *Nếu giảm (vd: 10)*: Thuật toán chạy tức thời, nhưng kết quả thường dở tệ vì "hồ gen" ban đầu quá nghèo nàn, thiếu các mảnh ghép lộ trình tốt.
*   **`generations` (Số thế hệ/Vòng lặp - mặc định 500)**: Số lần thuật toán tiến hóa.
    *   *Nếu tăng (vd: 2000)*: Cho phép thuật toán có thời gian "gọt giũa" kĩ lưỡng các điểm giao hàng cuối cùng. Đồ thị hội tụ sẽ kéo dài và dần đi ngang.
    *   *Nếu giảm (vd: 50)*: GA dừng lại khi chưa kịp tối ưu xong, lộ trình trả về có thể bị đan chéo và dư thừa quãng đường.
*   **`elite_size` (Số tinh anh giữ lại - mặc định 10)**: Chuyển thẳng N lộ trình tốt nhất sang thế hệ sau mà không qua lai ghép/đột biến.
    *   *Nếu đặt = 0*: Rủi ro cao. Một lộ trình hoàn hảo có thể bị phá nát ở thế hệ sau do phép lai ghép, đồ thị hội tụ sẽ giật cục thất thường.
    *   *Nếu đặt quá cao (vd: 80)*: Quần thể bị "tự kỷ". Các gen tốt lấn át ngay lập tức khiến quần thể mất đi sự đa dạng, thuật toán mắc kẹt ở một cấu hình chưa tối ưu (Tối ưu cục bộ - Local Optima).
*   **`cross_rate` (Tỷ lệ lai ghép - mặc định 0.8)**: Xác suất 2 lộ trình bố mẹ tráo đổi một đoạn điểm giao để tạo ra lộ trình con. Giữ ở mức 80%-90% là tiêu chuẩn công nghiệp.
*   **`mut_rate` (Tỷ lệ đột biến - mặc định 0.05)**: Xác suất để 2 điểm giao hàng tự nhiên tráo đổi vị trí cho nhau (`swap_mutation`). 
    *   *Vai trò:* Là "phao cứu sinh" giúp thoát khỏi ngõ cụt. Nếu đồ thị hội tụ đi ngang mãi không giảm, đột biến sẽ tạo ra một cú hích ngẫu nhiên để phá vỡ bế tắc.
    *   *Nếu đổi thành 0.5 (50%)*: Cấu trúc di truyền bị phá vỡ hoàn toàn, GA thoái hóa thành tìm kiếm ngẫu nhiên (Random Search). Quãng đường sẽ tăng vọt và không ổn định.

### Xử lý nâng cao (Đa phương tiện & Ràng buộc):

*   **`split_routes(...)`**: Nhận một chuỗi dài (vd: `[3, 1, 4, 2]`) và cắt thành nhiều lộ trình nhỏ dựa trên `vehicles` (số xe) hoặc `capacity` (sức chứa).
*   **`constrained_fitness(...)`**: Tính điểm "phạt". Nếu một lộ trình vi phạm ràng buộc tải trọng hoặc giao trễ giờ, hàm này sẽ cộng thêm một hình phạt khổng lồ (`overload_penalty = 10000`). Điều này khiến GA đánh giá lộ trình này rất thấp (chi phí cao = xấu) và lập tức đào thải nó ở bước chọn lọc tiếp theo.

---

### Tổng Kết Chiến Lược Vận Hành

Trong thực tế ứng dụng:
1.  **Dữ liệu là vua**: Bạn không cần tùy chỉnh file `astar.py` nhiều, chỉ cần đảm bảo thuật toán này chạy ra ma trận `distance_matrix` chính xác, có tính vật cản.
2.  **Đánh đổi (Trade-off)**: Thao tác chủ yếu nằm ở việc truyền tham số cho `run_ga`. Nếu cần đáp ứng API thời gian thực (nhanh), hãy giảm `generations` và `pop_size`. Nếu chạy batch qua đêm (cần kết quả hoàn hảo), hãy tăng tối đa hai thông số này và đẩy nhẹ `mut_rate` để tránh mắc kẹt.
