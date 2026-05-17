# KẾ HOẠCH KIỂM TRA TÍNH KHẢ THI VÀ NÂNG CẤP ĐỀ TÀI

## 1. Mục tiêu của kế hoạch

Tài liệu này trình bày kế hoạch kiểm tra tính khả thi và kế hoạch nâng cấp chi tiết cho đề tài **Tối ưu đường đi giao hàng bằng A* và Genetic Algorithm**. Các hướng nâng cấp được xét gồm:

- Thêm vật cản hoặc đường cấm trên bản đồ.
- Dùng dữ liệu bản đồ thực tế thay vì tọa độ ngẫu nhiên.
- Bổ sung nhiều xe giao hàng.
- Thêm ràng buộc thời gian giao hàng.
- Thêm trọng tải xe và số lượng hàng hóa.

Mục tiêu không chỉ là liệt kê chức năng mới, mà còn đánh giá chức năng nào có thể triển khai được trong phạm vi đồ án, chức năng nào cần thêm dữ liệu hoặc thay đổi lớn về thuật toán.

## 2. Tiêu chí kiểm tra tính khả thi

Mỗi hướng nâng cấp sẽ được đánh giá theo các tiêu chí sau:

| Tiêu chí | Nội dung đánh giá |
|---|---|
| Dữ liệu đầu vào | Cần thêm loại dữ liệu gì, có dễ tạo hoặc thu thập không |
| Thay đổi thuật toán | Có cần sửa A*, GA hoặc cấu trúc bài toán không |
| Thay đổi giao diện | Có cần thêm điều khiển, bảng nhập liệu hoặc bản đồ mới không |
| Độ phức tạp triển khai | Mức độ sửa code và rủi ro phát sinh |
| Khả năng kiểm thử | Có thể tạo kịch bản kiểm thử rõ ràng không |
| Giá trị học thuật | Có làm rõ hơn vai trò của thuật toán AI không |
| Mức ưu tiên | Nên làm trước hay sau |

Thang đánh giá khả thi:

- **Cao**: Có thể triển khai trực tiếp trên nền tảng hiện tại.
- **Trung bình**: Làm được nhưng cần sửa cấu trúc dữ liệu hoặc thuật toán.
- **Thấp**: Cần dữ liệu thực tế, thư viện ngoài hoặc thay đổi lớn.

## 3. Kiểm tra tính khả thi từng hướng nâng cấp

### 3.1. Thêm vật cản hoặc đường cấm trên bản đồ

#### Mục tiêu

Bổ sung các vùng hoặc đoạn đường không thể đi qua, để thuật toán A* thể hiện rõ vai trò tìm đường thay vì chỉ tính khoảng cách giữa hai điểm.

#### Tính khả thi

**Mức khả thi: Cao.**

Chức năng này phù hợp nhất với cấu trúc hiện tại vì dự án đã có A*, đồ thị và bản đồ 2D. Khi thêm vật cản, chỉ cần thay đổi cách xây dựng đồ thị:

- Không tạo cạnh đi qua vùng cấm.
- Không cho node nằm trong vùng vật cản.
- Nếu dùng dạng lưới, loại bỏ các ô bị chặn.

#### Dữ liệu cần bổ sung

- Danh sách vật cản, ví dụ hình chữ nhật: `x_min`, `y_min`, `x_max`, `y_max`.
- Danh sách đường cấm, ví dụ cặp điểm hoặc cạnh không được đi.
- Trạng thái bật/tắt vật cản trên giao diện.

#### Cách kiểm tra khả thi

1. Tạo một bản đồ nhỏ có 5-8 điểm giao.
2. Đặt vật cản nằm giữa kho và một điểm giao.
3. Chạy A* để kiểm tra đường đi có tránh vật cản không.
4. So sánh khoảng cách trước và sau khi thêm vật cản.
5. Quan sát bản đồ để xác nhận tuyến đường không cắt qua vùng cấm.

#### Điều kiện đạt

- A* không trả về đường đi xuyên qua vật cản.
- Nếu không có đường hợp lệ, hệ thống báo không tìm thấy đường.
- Ma trận khoảng cách cập nhật đúng sau khi thêm vật cản.
- GA không chọn tuyến có cạnh không hợp lệ.

#### Rủi ro

- Nếu vẫn dùng đồ thị đầy đủ, cạnh có thể đi xuyên vật cản.
- Nếu chuyển sang đồ thị lưới, số node tăng làm A* chạy lâu hơn.
- Giao diện cần hiển thị vật cản rõ ràng để người dùng hiểu kết quả.

#### Mức ưu tiên

**Ưu tiên 1.** Đây là nâng cấp nên làm đầu tiên vì giúp A* có vai trò rõ hơn và tăng chất lượng báo cáo.

## 3.2. Dùng dữ liệu bản đồ thực tế

#### Mục tiêu

Thay tọa độ ngẫu nhiên bằng dữ liệu bản đồ thực tế như vị trí đường, nút giao, khoảng cách hoặc tọa độ GPS.

#### Tính khả thi

**Mức khả thi: Trung bình đến thấp.**

Nếu chỉ nhập danh sách tọa độ GPS thủ công thì khả thi ở mức trung bình. Nếu muốn dùng bản đồ thật với đường phố thật, cần thêm nguồn dữ liệu như OpenStreetMap và thư viện xử lý đồ thị đường đi.

#### Dữ liệu cần bổ sung

- Tọa độ kho hàng và điểm giao hàng theo kinh độ, vĩ độ.
- Dữ liệu đường đi thực tế giữa các điểm.
- Nếu dùng OpenStreetMap: cần tải dữ liệu đường và chuyển thành đồ thị.

#### Cách kiểm tra khả thi

1. Chọn một khu vực nhỏ, ví dụ một phường hoặc một khu phố.
2. Lấy 5-10 điểm tọa độ thật.
3. Chuyển tọa độ GPS sang hệ tọa độ hiển thị trên giao diện.
4. Tính khoảng cách giữa các điểm bằng dữ liệu đường hoặc khoảng cách địa lý.
5. Chạy lại A* + GA và kiểm tra kết quả.

#### Điều kiện đạt

- Điểm giao hiển thị đúng vị trí tương đối.
- Khoảng cách tính ra hợp lý so với thực tế.
- Giao diện vẫn vẽ được tuyến đường.
- Thuật toán không bị phụ thuộc vào dữ liệu ngẫu nhiên.

#### Rủi ro

- Dữ liệu bản đồ thực tế có thể phức tạp và cần xử lý nhiều lỗi.
- Cần kết nối mạng nếu dùng API bên ngoài.
- Nếu dùng dữ liệu lớn, hiệu năng có thể giảm.
- Tọa độ GPS cần chuyển đổi để hiển thị đúng trên canvas hoặc matplotlib.

#### Mức ưu tiên

**Ưu tiên 4.** Nên làm sau khi hệ thống ổn định với vật cản và nhiều ràng buộc cơ bản.

## 3.3. Bổ sung nhiều xe giao hàng - [ĐÃ TRIỂN KHAI]

#### Mục tiêu

Mở rộng bài toán từ một xe thành nhiều xe cùng xuất phát từ kho, chia nhau giao hàng để giảm tổng thời gian hoặc tổng quãng đường.

#### Tính khả thi

**Mức khả thi: Trung bình.**

Chức năng này làm thay đổi bản chất bài toán từ TSP sang VRP. GA hiện tại biểu diễn một chromosome là một thứ tự điểm giao cho một xe. Khi có nhiều xe, chromosome cần biểu diễn thêm cách chia điểm cho từng xe.

#### Dữ liệu cần bổ sung

- Số lượng xe.
- Danh sách điểm giao được gán cho từng xe.
- Chi phí từng xe.
- Tiêu chí tối ưu: giảm tổng quãng đường, giảm thời gian xe lâu nhất, hoặc cân bằng tải giữa các xe.

#### Gợi ý mã hóa chromosome

Có thể dùng một trong hai cách:

**Cách 1: Hoán vị kèm điểm cắt**

```text
Chromosome = [3, 1, 5, 2, 4]
Split = [2]
Xe 1: 0 -> 3 -> 1 -> 0
Xe 2: 0 -> 5 -> 2 -> 4 -> 0
```

**Cách 2: Gán xe cho từng điểm**

```text
Điểm:  1 2 3 4 5
Xe:    1 2 1 2 1
```

Cách 1 dễ kết hợp với GA hiện tại hơn vì vẫn giữ dạng hoán vị.

#### Cách kiểm tra khả thi

1. Thêm biến số lượng xe, ví dụ 2 xe.
2. Chạy với 6-10 điểm giao.
3. Kiểm tra mỗi điểm được giao đúng một lần.
4. Kiểm tra mỗi xe bắt đầu và kết thúc tại kho.
5. So sánh tổng quãng đường hoặc thời gian hoàn thành với phiên bản một xe.

#### Điều kiện đạt

- Không có điểm bị giao thiếu hoặc giao trùng.
- Mỗi xe có lộ trình riêng.
- Giao diện phân biệt được lộ trình của từng xe bằng màu khác nhau.
- Kết quả thống kê hiển thị tổng quãng đường và thời gian từng xe.

#### Rủi ro

- GA phức tạp hơn vì phải tối ưu cả thứ tự và cách chia điểm.
- Nếu chia điểm không hợp lý, một xe có thể nhận quá nhiều điểm.
- Cần thiết kế lại giao diện hiển thị nhiều tuyến cùng lúc.

#### Mức ưu tiên

**Ưu tiên 3.** Nên làm sau khi đã ổn định phần vật cản và chuẩn hóa dữ liệu chi phí.

## 3.4. Thêm ràng buộc thời gian giao hàng - [ĐÃ TRIỂN KHAI]

#### Mục tiêu

Mỗi điểm giao có một khoảng thời gian mong muốn, ví dụ giao trong khoảng 8:00-10:00. Thuật toán cần ưu tiên hoặc bắt buộc chọn lộ trình sao cho hạn chế giao trễ.

#### Tính khả thi

**Mức khả thi: Trung bình.**

Chức năng này có thể thêm vào GA bằng cách sửa hàm fitness. Thay vì chỉ tối ưu quãng đường, fitness cần tính thêm chi phí phạt nếu giao sớm hoặc trễ.

#### Dữ liệu cần bổ sung

- Thời gian bắt đầu giao hàng.
- Thời gian phục vụ tại mỗi điểm.
- Khung thời gian cho từng điểm: `earliest_time`, `latest_time`.
- Hệ số phạt khi giao trễ.

#### Gợi ý hàm fitness mới

```text
fitness = total_distance + penalty_late + penalty_waiting
```

Trong đó:

- `total_distance`: tổng quãng đường.
- `penalty_late`: chi phí phạt nếu đến sau thời gian cho phép.
- `penalty_waiting`: chi phí chờ nếu đến quá sớm, có thể tính hoặc bỏ qua tùy yêu cầu.

#### Cách kiểm tra khả thi

1. Tạo 5 điểm giao với khung thời gian giả lập.
2. Chạy GA chỉ theo quãng đường.
3. Chạy GA có ràng buộc thời gian.
4. So sánh số điểm giao trễ giữa hai kết quả.
5. Kiểm tra giao diện có hiển thị thời gian đến từng điểm không.

#### Điều kiện đạt

- Hệ thống tính được thời gian đến dự kiến của từng điểm.
- Fitness tăng khi có điểm giao trễ.
- Lộ trình sau tối ưu giảm số điểm trễ hoặc giảm tổng thời gian trễ.
- Bảng kết quả hiển thị điểm nào đúng hạn, điểm nào trễ.

#### Rủi ro

- Nếu hệ số phạt quá nhỏ, GA vẫn ưu tiên đường ngắn và bỏ qua trễ giờ.
- Nếu hệ số phạt quá lớn, GA có thể hy sinh quá nhiều quãng đường.
- Cần cân bằng giữa mục tiêu quãng đường và mục tiêu đúng giờ.

#### Mức ưu tiên

**Ưu tiên 2.** Đây là nâng cấp có giá trị thực tế cao và có thể triển khai bằng cách sửa fitness.

## 3.5. Thêm trọng tải xe và số lượng hàng hóa - [ĐÃ TRIỂN KHAI]

#### Mục tiêu

Mỗi điểm giao có một lượng hàng cần giao. Xe có tải trọng tối đa. Lộ trình cần đảm bảo tổng hàng trên mỗi chuyến không vượt quá tải trọng xe.

#### Tính khả thi

**Mức khả thi: Trung bình.**

Nếu vẫn chỉ có một xe và tổng hàng không vượt tải, chức năng này đơn giản. Nếu có nhiều xe hoặc phải quay về kho để lấy thêm hàng, bài toán sẽ phức tạp hơn và gần với Capacitated Vehicle Routing Problem (CVRP).

#### Dữ liệu cần bổ sung

- Nhu cầu hàng hóa tại mỗi điểm: `demand`.
- Tải trọng tối đa của xe: `capacity`.
- Số lượng xe nếu kết hợp với nâng cấp nhiều xe.

#### Gợi ý xử lý trong GA

Có hai hướng:

**Hướng 1: Dùng penalty**

```text
fitness = total_distance + overload_penalty
```

Nếu tổng hàng của tuyến vượt tải, cộng thêm chi phí phạt lớn.

**Hướng 2: Ràng buộc cứng**

Chỉ cho phép tạo chromosome hợp lệ, tức là mọi tuyến đều không vượt tải. Hướng này sạch hơn nhưng khó cài đặt hơn.

#### Cách kiểm tra khả thi

1. Tạo danh sách điểm giao có nhu cầu hàng hóa.
2. Đặt tải trọng xe nhỏ để tạo trường hợp vượt tải.
3. Chạy GA và kiểm tra fitness có phạt tuyến vượt tải không.
4. Nếu có nhiều xe, kiểm tra tổng hàng mỗi xe không vượt tải.
5. Hiển thị tải đã dùng của từng xe hoặc từng tuyến.

#### Điều kiện đạt

- Mỗi điểm có nhu cầu hàng hóa rõ ràng.
- Hệ thống phát hiện tuyến vượt tải.
- Thuật toán ưu tiên tuyến không vượt tải.
- Giao diện hiển thị tổng tải và trạng thái hợp lệ/không hợp lệ.

#### Rủi ro

- Nếu chỉ dùng một xe nhưng tổng nhu cầu vượt tải, bài toán không có nghiệm hợp lệ.
- Khi kết hợp với nhiều xe, chromosome và fitness phức tạp hơn.
- Cần kiểm soát để GA không sinh quá nhiều nghiệm không hợp lệ.

#### Mức ưu tiên

**Ưu tiên 5 nếu làm độc lập**, nhưng **ưu tiên 4 nếu đã triển khai nhiều xe**, vì trọng tải phát huy ý nghĩa rõ nhất trong bài toán nhiều xe.

## 4. Kế hoạch nâng cấp chi tiết

### Giai đoạn 1: Chuẩn hóa nền tảng dữ liệu

#### Mục tiêu

Chuẩn hóa dữ liệu đầu vào để các ràng buộc mới có thể thêm vào mà không phá vỡ cấu trúc hiện tại.

#### Công việc

- Bổ sung cấu trúc điểm giao hàng gồm: `id`, `name`, `x`, `y`, `demand`, `time_window`.
- Tách dữ liệu cấu hình thuật toán khỏi giao diện.
- Chuẩn hóa kết quả trả về gồm: lộ trình, tổng km, tổng thời gian, danh sách điểm trễ, tải trọng.
- Đảm bảo A* và GA vẫn chạy đúng với dữ liệu cũ.

#### Kết quả mong đợi

- Code dễ mở rộng hơn.
- Có thể thêm ràng buộc mà không sửa nhiều nơi.
- Giao diện đọc dữ liệu thống nhất.

### Giai đoạn 2: Thêm vật cản và đường cấm

#### Mục tiêu

Làm rõ vai trò của A* bằng bản đồ có vùng không thể đi qua.

#### Công việc

- Thiết kế cấu trúc dữ liệu vật cản.
- Sửa `build_graph()` để loại bỏ cạnh không hợp lệ.
- Cập nhật A* để báo khi không có đường đi.
- Vẽ vật cản trên bản đồ.
- Thêm một vài preset bản đồ có vật cản.

#### Kiểm thử

- Trường hợp không có vật cản: kết quả không thay đổi nhiều so với hiện tại.
- Trường hợp vật cản nằm giữa hai điểm: A* phải đi vòng.
- Trường hợp vật cản chặn hoàn toàn: hệ thống báo không có đường.

#### Kết quả mong đợi

- A* thể hiện rõ vai trò tìm đường.
- Báo cáo có minh chứng trực quan hơn.

### Giai đoạn 3: Thêm ràng buộc thời gian

#### Mục tiêu

Đưa bài toán gần với thực tế hơn bằng cách xét thời hạn giao hàng.

#### Công việc

- Thêm thời gian bắt đầu và tốc độ xe vào cấu hình.
- Thêm khung giờ giao cho từng điểm.
- Sửa fitness GA để cộng phạt giao trễ.
- Tính thời gian đến từng điểm theo lộ trình.
- Hiển thị trạng thái đúng hạn/trễ trên danh sách lộ trình.

#### Kiểm thử

- Lộ trình không có ràng buộc thời gian.
- Lộ trình có một điểm dễ bị trễ.
- Lộ trình có nhiều điểm xung đột khung giờ.

#### Kết quả mong đợi

- GA không chỉ tối ưu đường ngắn mà còn cân nhắc đúng giờ.
- Bảng so sánh có thêm số điểm trễ và tổng phút trễ.

### Giai đoạn 4: Bổ sung nhiều xe

#### Mục tiêu

Mở rộng từ bài toán một xe sang nhiều xe giao hàng.

#### Công việc

- Thêm tham số số lượng xe.
- Thiết kế chromosome có điểm cắt tuyến.
- Sửa fitness để tính tổng quãng đường hoặc thời gian xe lâu nhất.
- Hiển thị nhiều tuyến bằng nhiều màu.
- Thêm bảng thống kê từng xe.

#### Kiểm thử

- 2 xe, 6 điểm giao.
- 3 xe, 12 điểm giao.
- Trường hợp một xe không có điểm giao.
- Kiểm tra không có điểm bị trùng hoặc bị bỏ sót.

#### Kết quả mong đợi

- Hệ thống chia được điểm giao cho nhiều xe.
- Người dùng xem được lộ trình riêng của từng xe.

### Giai đoạn 5: Thêm trọng tải và số lượng hàng hóa

#### Mục tiêu

Ràng buộc tuyến giao theo tải trọng xe.

#### Công việc

- Thêm `demand` cho mỗi điểm giao.
- Thêm `capacity` cho từng xe.
- Sửa fitness để phạt tuyến vượt tải.
- Nếu dùng nhiều xe, tính tải từng xe.
- Hiển thị tổng tải và trạng thái vượt tải.

#### Kiểm thử

- Tổng hàng nhỏ hơn tải xe.
- Tổng hàng bằng tải xe.
- Tổng hàng vượt tải xe.
- Nhiều xe với nhu cầu hàng phân bố không đều.

#### Kết quả mong đợi

- Tuyến giao hàng hợp lệ về tải trọng.
- Hệ thống cảnh báo nếu bài toán không có nghiệm hợp lệ.

### Giai đoạn 6: Tích hợp dữ liệu bản đồ thực tế

#### Mục tiêu

Nâng cấp từ mô phỏng tọa độ sang dữ liệu thực tế.

#### Công việc

- Chọn nguồn dữ liệu: nhập tay tọa độ, CSV, hoặc OpenStreetMap.
- Thiết kế bộ chuyển đổi tọa độ GPS sang tọa độ hiển thị.
- Xây dựng đồ thị đường từ dữ liệu bản đồ.
- Kiểm tra A* trên đồ thị thực.
- Cập nhật giao diện để hiển thị bản đồ nền nếu cần.

#### Kiểm thử

- Dữ liệu nhỏ 5 điểm trong cùng khu vực.
- Dữ liệu 10-20 điểm.
- Điểm nằm ngoài vùng bản đồ.
- Đường một chiều hoặc đường cấm nếu dữ liệu hỗ trợ.

#### Kết quả mong đợi

- Hệ thống có thể chạy với dữ liệu gần thực tế.
- Kết quả có tính ứng dụng cao hơn.

## 5. Lộ trình thời gian đề xuất

| Giai đoạn | Nội dung | Thời gian dự kiến | Ưu tiên |
|---|---|---:|---|
| 1 | Chuẩn hóa dữ liệu | 1-2 ngày | Rất cao |
| 2 | Thêm vật cản/đường cấm | 2-3 ngày | Rất cao |
| 3 | Ràng buộc thời gian | 2-4 ngày | Cao |
| 4 | Nhiều xe giao hàng | 4-6 ngày | Trung bình |
| 5 | Trọng tải và hàng hóa | 3-5 ngày | Trung bình |
| 6 | Bản đồ thực tế | 5-10 ngày | Sau cùng |

## 6. Thứ tự ưu tiên đề xuất

Nếu thời gian làm đồ án còn hạn chế, nên triển khai theo thứ tự:

1. **Vật cản/đường cấm**: tăng giá trị minh họa cho A* rõ nhất.
2. **Ràng buộc thời gian**: tăng tính thực tế và chỉ cần sửa fitness GA.
3. **Nhiều xe giao hàng**: mở rộng bài toán từ TSP sang VRP.
4. **Trọng tải hàng hóa**: nên làm sau hoặc cùng với nhiều xe.
5. **Bản đồ thực tế**: giá trị cao nhưng phụ thuộc dữ liệu và xử lý phức tạp.

## 7. Kết luận khả thi

Các hướng nâng cấp đều có thể thực hiện, nhưng mức độ khó khác nhau. Trong phạm vi đồ án môn học, hướng khả thi và có giá trị nhất là **thêm vật cản/đường cấm** và **thêm ràng buộc thời gian giao hàng**. Hai nâng cấp này làm rõ vai trò của A* và GA mà không cần thay đổi toàn bộ kiến trúc.

Các hướng **nhiều xe**, **trọng tải** và **bản đồ thực tế** có giá trị thực tiễn cao hơn nhưng cần thay đổi lớn hơn về dữ liệu, fitness và giao diện. Vì vậy, nên đưa vào kế hoạch phát triển tiếp theo hoặc thực hiện nếu còn đủ thời gian.

## 8. Trạng thái thực hiện đến 14/05/2026

- Đã bổ sung cấu trúc dữ liệu mở rộng cho điểm giao hàng: `demand` và `time_window`.
- Đã thêm preset vật cản/đường cấm và node phụ quanh vật cản để A* có thể tìm đường đi vòng.
- Đã sửa ma trận khoảng cách để không dùng khoảng cách giả khi A* không tìm được đường hợp lệ; API sẽ báo lỗi rõ nếu còn cặp điểm không thể kết nối.
- Đã thêm GA có ràng buộc nhiều xe, tải trọng và khung giờ giao hàng thông qua hàm fitness mở rộng.
- Đã cập nhật giao diện web để cấu hình số xe, tải trọng, vật cản và bật/tắt khung giờ giao.
- Đã cập nhật hiển thị nhiều tuyến xe bằng nhiều màu và vẽ vùng vật cản trên bản đồ.
- Đã kiểm tra nhanh bằng `python -m compileall`, Flask test client cho `/api/generate`, `/api/astar`, `/api/optimize`, và một ca A* đi vòng qua vật cản.

Hạng mục còn lại nên làm sau:

- Bổ sung bảng chi tiết tải trọng và trạng thái đúng hạn/trễ cho từng điểm giao.
- Bổ sung bộ test tự động cố định thay vì chỉ kiểm tra nhanh bằng test client.
- Tích hợp dữ liệu bản đồ thực tế hoặc CSV nếu còn thời gian.
