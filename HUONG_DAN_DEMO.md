# Kịch Bản Demo & Bảo Vệ Đề Tài: Tối Ưu Giao Hàng Bằng A* và GA

Tài liệu này cung cấp kịch bản trình bày (Demo) từng bước cho giảng viên môn Trí tuệ nhân tạo, kèm theo các "điểm nóng" mà giảng viên chắc chắn sẽ hỏi để bạn chuẩn bị sẵn câu trả lời.

---

## PHẦN 1: KỊCH BẢN DEMO TỪNG BƯỚC (STEP-BY-STEP)

### Bước 1: Mở đầu và Giới thiệu Bài toán (1 phút)
*   **Thao tác:** Mở trang web `delivery_optimizer_demo.html` (đã bật backend). Để màn hình ở chế độ chờ (Chưa bấm chạy).
*   **Trình bày:** "Chào thầy/cô, đề tài của nhóm em giải quyết bài toán giao hàng trong đô thị có rào cản (đường cấm, khu vực thi công). Điểm khác biệt của hệ thống này là không chỉ tìm đường chim bay, mà còn dùng **A*** để né vật cản, và dùng **Genetic Algorithm (GA)** để sắp xếp thứ tự giao hàng sao cho tổng quãng đường ngắn nhất. Ngoài ra, hệ thống hỗ trợ ràng buộc thực tế như số lượng xe, tải trọng và khung giờ."

### Bước 2: Bật chế độ "CHỈ A* (TUẦN TỰ)" - Thể hiện sức mạnh dò đường cục bộ
*   **Thao tác:** Bấm chọn mode **`CHỈ A* (TUẦN TỰ)`**. Chọn cấu hình **`🏙 NỘI THÀNH`**. Bấm **`▶ CHẠY`**.
*   **Trình bày:** "Đầu tiên, đây là chế độ Baseline (Tuần tự). Thuật toán chỉ sử dụng A* để đi từ Kho -> Điểm 1 -> Điểm 2 theo đúng thứ tự mảng dữ liệu sinh ra. Thầy cô có thể thấy xe **biết né các mảng màu đỏ (vật cản)** rất thông minh. Tuy nhiên, vì không tối ưu thứ tự, xe chạy vòng vèo, đường đi cắt chéo nhau rất nhiều, dẫn đến tổng quãng đường rất dài."

### Bước 3: Bật chế độ "GA (DI TRUYỀN)" - Tối ưu thứ tự và chia xe
*   **Thao tác:** Chuyển sang mode **`CHỈ GA (DI TRUYỀN)`**. Bấm **`▶ CHẠY`**.
*   **Trình bày:** "Bây giờ em đổi sang GA. GA sẽ tối ưu thứ tự giao hàng và chia tuyến theo số xe, tải trọng, khung giờ. Fitness của GA dùng metric Euclid để chạy nhanh; sau khi có thứ tự tốt, backend lấy lại đường đi chi tiết để vẽ tuyến trên bản đồ. Vì vậy kết quả thể hiện vai trò chính của GA: tối ưu tổ hợp và phân bổ xe."

### Bước 4: Chế độ "TUYẾN TUẦN TỰ BAN ĐẦU" - Mốc đối chiếu
*   **Thao tác:** Chuyển sang mode **`TUYẾN TUẦN TỰ BAN ĐẦU`** nếu cần trình bày mốc ban đầu. Bấm **`▶ CHẠY`**.
*   **Trình bày:** "Đây không phải thuật toán tối ưu, mà là tuyến tham chiếu đi theo đúng thứ tự điểm được sinh ra. Em dùng tuyến này để giải thích vì sao cần tối ưu: khi đi tuần tự, tổng quãng đường và thời gian thường cao hơn GA."

### Bước 5: Tính năng nâng cao - Khung giờ và Đa phương tiện (VRP)
*   **Thao tác:** Bấm **`⚙ CẤU HÌNH`**. Kéo số xe lên `2` hoặc `3`. Đảm bảo nút "⏰ BẬT KHUNG GIỜ GIAO" được bật. Bấm **`▶ CHẠY`**. Mở tab **`📊 KẾT QUẢ`**.
*   **Trình bày:** "Để đáp ứng thực tế, nhóm đã nâng cấp bài toán TSP thành VRP (Vehicle Routing Problem). Hệ thống tự động chia tuyến cho 2 xe, đảm bảo không xe nào bị quá tải, và phải đến điểm giao đúng khung giờ quy định. Tab Kết quả hiển thị chi tiết lộ trình từng xe."

### Bước 6: Chốt lại bằng "SO SÁNH A* VS GA"
*   **Thao tác:** Chọn mode **`⚡ SO SÁNH A* VS GA`**. Bấm **`⚡ SO SÁNH`**.
*   **Trình bày:** "Cuối cùng, phần mềm chạy A* tuần tự và GA rồi đặt kết quả cạnh nhau. Bảng so sánh cho thấy tổng km, thời gian, runtime, số xe và phần trăm cải thiện. Tuyến tuần tự ban đầu vẫn là mốc tham khảo riêng, còn bảng này tập trung vào hai thuật toán chính."

---

## PHẦN 2: "BẮT BÀI" - CÁC CÂU HỎI PHẢN BIỆN CỦA GIẢNG VIÊN

Đây là những vị trí trên UI hoặc thuật toán mà giảng viên AI thường sẽ xoáy vào.

### Câu 1: "Tại sao dùng cả A* và GA? Tại sao không dùng mỗi A* để giải luôn toàn bộ?"
*   **Mục đích hỏi:** Kiểm tra sinh viên có phân biệt được **Bài toán Tìm đường (Pathfinding)** và **Bài toán Định tuyến (Routing/TSP)** hay không.
*   **Trả lời:** "Dạ, A* là thuật toán tìm đường cục bộ, nó chỉ giỏi giải quyết bài toán: 'Làm sao đi từ điểm A đến điểm B nhanh nhất'. Nó không thể trả lời câu hỏi: 'Trong 10 điểm, nên đi điểm nào trước, điểm nào sau'. Nếu dùng A* duyệt hết mọi hoán vị thì chi phí tính toán tăng theo giai thừa. Vì vậy bản hiện tại tách rõ: A* dùng để trình bày tìm đường hợp lệ và làm tuyến tuần tự đối chiếu; GA dùng để tối ưu thứ tự giao hàng và chia xe."

### Câu 2: "Trong GA, hàm Fitness của em tính như thế nào khi có thêm điều kiện Khung giờ và Tải trọng?"
*   **Mục đích hỏi:** Xem cách bạn chuyển đổi các ràng buộc (Constraints) thành hàm mục tiêu (Objective Function).
*   **Trả lời:** "Dạ em dùng kỹ thuật **Hàm Phạt (Penalty)** ạ. Hàm Fitness ban đầu chỉ là tổng quãng đường. Nhưng nếu lộ trình đó chở lố tải trọng, em sẽ cộng thêm `(phần quá tải * 10000)` vào tổng quãng đường. Tương tự với đi trễ giờ. Vì GA luôn tìm cách thu nhỏ (minimize) Fitness, nên những cá thể bị phạt điểm cao chót vót sẽ tự động bị đào thải ở vòng chọn lọc tiếp theo."

### Câu 3: (GV chỉ vào thông số trên UI) "Nếu thầy đổi Tỷ lệ Đột biến (Mutation Rate) lên 80% thì chuyện gì xảy ra?"
*   **Mục đích hỏi:** Kiểm tra mức độ hiểu sâu về các tham số của Giải thuật Di truyền.
*   **Trả lời:** "Dạ nếu để Mutation Rate lên 80%, thuật toán sẽ bị phá vỡ cấu trúc và biến thành **Tìm kiếm ngẫu nhiên (Random Search)**. Đột biến có vai trò như 'cú hích' nhẹ để thoát khỏi tối ưu cục bộ, bình thường chỉ nên để 5-10%. Nếu đột biến quá cao, các gen tốt mà lai ghép vừa vất vả giữ lại được sẽ bị hoán đổi nát bét, đồ thị hội tụ sẽ răng cưa và không thể tìm ra đường đi tối ưu."

### Câu 4: "Vì sao bản hiện tại không còn mode A* + GA riêng?"
*   **Mục đích hỏi:** Kiểm tra sinh viên có nắm đúng bản demo đang chạy hay không.
*   **Trả lời:** "Dạ nhóm đã tách mode để giảng viên dễ nhìn vai trò từng thuật toán. Nếu gộp thành A*+GA, người xem dễ nhầm không biết phần nào là tìm đường, phần nào là tối ưu thứ tự. Bản hiện tại có A* tuần tự để minh họa tìm đường hợp lệ, GA để minh họa tối ưu tổ hợp, và mode so sánh A* vs GA để đối chiếu kết quả."

### Câu 5: "Làm sao em chứng minh thuật toán của em hội tụ?"
*   **Mục đích hỏi:** Bắt bạn chỉ ra bằng chứng trực quan của GA.
*   **Trả lời:** *(Lúc này bạn bấm chạy GA hoặc So sánh A* vs GA)* "Dạ mời thầy cô nhìn vào **đồ thị hội tụ GA** trong Tab Kết quả. Đường này biểu diễn fitness tốt nhất qua các thế hệ. Ban đầu đồ thị giảm nhanh, sau đó đi ngang dần. Khi đường đi ngang, nghĩa là GA đã hội tụ hoặc không còn cải thiện đáng kể."

---
*Chúc bạn có một buổi báo cáo đồ án AI thật trơn tru và nhận điểm tối đa!*
