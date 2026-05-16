# BÁO CÁO ĐỀ TÀI: TỐI ƯU ĐƯỜNG ĐI GIAO HÀNG BẰNG A* VÀ GENETIC ALGORITHM

## 1. Mục tiêu bài toán

### 1.1. Tên đề tài

**Tối ưu đường đi giao hàng bằng thuật toán A* và Genetic Algorithm (GA).**

### 1.2. Mô tả bài toán

Trong hoạt động giao hàng, xe giao hàng thường phải xuất phát từ một kho, đi qua nhiều điểm giao khác nhau và quay trở lại kho sau khi hoàn thành. Nếu số điểm giao tăng lên, việc chọn thứ tự giao hàng không còn đơn giản vì mỗi cách sắp xếp thứ tự sẽ tạo ra một tổng quãng đường khác nhau. Mục tiêu của bài toán là tìm ra một lộ trình có tổng quãng đường và thời gian di chuyển nhỏ nhất hoặc gần nhỏ nhất trong thời gian tính toán hợp lý.

Bài toán trong đề tài được mô phỏng như sau:

- Có một điểm kho hàng cố định, ký hiệu là điểm `0`.
- Có `n - 1` điểm giao hàng được sinh ngẫu nhiên trên bản đồ tọa độ 2D.
- Xe bắt đầu từ kho, đi qua toàn bộ điểm giao hàng đúng một lần, sau đó quay về kho.
- Người dùng có thể chọn số điểm giao hàng, tốc độ xe và loại heuristic cho thuật toán A* thông qua giao diện.
- Hệ thống cần hiển thị bản đồ, tuyến đường, tổng quãng đường, thời gian ước tính, số điểm giao đã hoàn thành và phần trăm cải thiện so với lộ trình tuần tự.

Về bản chất, bài toán có liên quan đến bài toán người giao hàng (Travelling Salesman Problem - TSP) hoặc bài toán định tuyến phương tiện đơn giản (Vehicle Routing Problem - VRP với một xe). Đây là nhóm bài toán tối ưu tổ hợp, trong đó số khả năng sắp xếp tăng rất nhanh theo số điểm giao. Với `m` điểm giao hàng, số thứ tự có thể là `m!`. Vì vậy, nếu duyệt toàn bộ các khả năng thì thời gian tính toán sẽ tăng rất mạnh khi số điểm lớn.

### 1.3. Mục tiêu cần đạt

Đề tài hướng tới các mục tiêu chính:

- Xây dựng được bản đồ mô phỏng gồm kho hàng và các điểm giao hàng.
- Biểu diễn bản đồ dưới dạng đồ thị để có thể tính đường đi giữa các điểm.
- Áp dụng thuật toán A* để tìm đường đi ngắn nhất giữa từng cặp điểm.
- Xây dựng ma trận khoảng cách giữa các điểm để làm đầu vào cho bước tối ưu.
- Áp dụng Genetic Algorithm để tìm thứ tự giao hàng tối ưu hơn so với lộ trình tuần tự.
- Hiển thị kết quả dự đoán lộ trình trên giao diện.
- So sánh kết quả giữa lộ trình tuần tự và lộ trình A* + GA.
- Đánh giá lý do lựa chọn thuật toán dựa trên độ phù hợp, hiệu quả và khả năng minh họa.

### 1.4. Phạm vi và giả định

Đề tài tập trung vào mô phỏng thuật toán và trực quan hóa kết quả, không xử lý đầy đủ tất cả yếu tố ngoài thực tế như kẹt xe, đơn hàng có khung giờ giao, nhiều xe giao hàng hoặc trọng tải xe. Các giả định chính:

- Chỉ có một xe giao hàng.
- Xe luôn xuất phát từ kho và quay lại kho.
- Mỗi điểm giao hàng chỉ cần đi qua một lần.
- Tốc độ xe được xem là hằng số theo giá trị người dùng nhập.
- Trọng số cạnh trên đồ thị được tính theo khoảng cách giữa các điểm.
- Kết quả GA là nghiệm tối ưu gần đúng, không khẳng định là nghiệm tối ưu tuyệt đối trong mọi trường hợp.

## 2. Cơ sở lý thuyết về các giải thuật áp dụng

### 2.1. TT1 - Thuật toán A*

#### Khái niệm

A* là thuật toán tìm kiếm đường đi ngắn nhất trên đồ thị có trọng số không âm. Thuật toán kết hợp giữa chi phí thực tế đã đi và chi phí ước lượng còn lại để ưu tiên mở rộng các đỉnh có khả năng nằm trên đường đi tốt nhất.

Trong đề tài, A* được dùng để tìm khoảng cách ngắn nhất giữa hai điểm bất kỳ trên bản đồ. Sau khi chạy A* cho mọi cặp điểm, hệ thống tạo ra ma trận khoảng cách. Ma trận này là dữ liệu đầu vào cho Genetic Algorithm.

#### Công thức đánh giá

A* sử dụng hàm:

```text
f(n) = g(n) + h(n)
```

Trong đó:

- `g(n)` là chi phí thực tế từ điểm bắt đầu đến node hiện tại `n`.
- `h(n)` là chi phí ước lượng từ node hiện tại `n` đến đích.
- `f(n)` là tổng chi phí dự đoán nếu đi qua node `n`.

Node có `f(n)` nhỏ nhất sẽ được ưu tiên xét trước.

#### Heuristic sử dụng

Trong chương trình có hai loại heuristic:

- **Euclidean distance**: phù hợp khi khoảng cách được đo theo đường thẳng trên mặt phẳng.

```text
h(n) = sqrt((x2 - x1)^2 + (y2 - y1)^2)
```

- **Manhattan distance**: phù hợp với mô hình di chuyển theo lưới đường vuông góc.

```text
h(n) = |x2 - x1| + |y2 - y1|
```

#### Các thành phần chính của A*

- **Open list**: tập các node đang chờ xét.
- **Closed list**: tập các node đã xét.
- **Priority Queue**: hàng đợi ưu tiên, dùng để lấy node có `f(n)` nhỏ nhất.
- **came_from**: lưu node cha để truy vết lại đường đi.
- **g_score**: lưu chi phí thực tế tốt nhất từ điểm bắt đầu đến từng node.
- **f_score**: lưu tổng chi phí dự đoán `g_score + heuristic`.

#### Vai trò trong đề tài

A* không trực tiếp quyết định thứ tự giao hàng tổng thể. Vai trò của A* là tính chi phí đường đi giữa từng cặp điểm. Ví dụ, cần biết chi phí từ kho đến điểm 1, từ điểm 1 đến điểm 3, từ điểm 3 đến điểm 2, v.v. Sau khi có các chi phí này, thuật toán GA mới có thể đánh giá lộ trình nào ngắn hơn.

#### Ưu điểm

- Tìm đường đi ngắn nhất hiệu quả nếu heuristic phù hợp.
- Dễ trực quan hóa qua từng bước: node đang xét, open list, closed list.
- Có thể mở rộng cho bản đồ phức tạp hơn nếu thêm vật cản hoặc mạng đường.
- Phù hợp làm nền tảng tính ma trận khoảng cách cho bài toán giao hàng.

#### Hạn chế

- Nếu chạy cho nhiều cặp điểm, số lần chạy A* tăng theo `n^2`.
- Hiệu quả phụ thuộc vào heuristic.
- Nếu bản đồ là đồ thị đầy đủ và không có vật cản, A* gần giống tính khoảng cách trực tiếp; tuy nhiên vẫn có ý nghĩa minh họa và mở rộng.

### 2.2. TT2 - Genetic Algorithm (GA)

#### Khái niệm

Genetic Algorithm là thuật toán tối ưu dựa trên cơ chế tiến hóa tự nhiên. Thuật toán mô phỏng quá trình chọn lọc, lai ghép và đột biến để cải thiện dần chất lượng nghiệm qua nhiều thế hệ.

Trong đề tài, GA được dùng để tối ưu thứ tự giao hàng. Mỗi cá thể trong quần thể là một thứ tự đi qua các điểm giao hàng. Qua nhiều thế hệ, thuật toán giữ lại các cá thể tốt và tạo ra cá thể mới có khả năng tốt hơn.

#### Mã hóa nghiệm

Một nghiệm được biểu diễn bằng một hoán vị các điểm giao hàng, không bao gồm kho.

Ví dụ:

```text
[3, 1, 4, 2]
```

Lộ trình đầy đủ tương ứng là:

```text
0 -> 3 -> 1 -> 4 -> 2 -> 0
```

Trong đó `0` là kho hàng.

#### Hàm thích nghi

Hàm thích nghi dùng để đánh giá chất lượng một lộ trình. Trong đề tài, fitness là tổng quãng đường:

```text
fitness = d(0, p1) + d(p1, p2) + ... + d(pk, 0)
```

Trong đó:

- `d(a, b)` là khoảng cách ngắn nhất từ điểm `a` đến điểm `b`, lấy từ ma trận khoảng cách do A* tạo ra.
- Fitness càng nhỏ thì lộ trình càng tốt.

#### Các toán tử chính

**Khởi tạo quần thể**: tạo nhiều hoán vị ngẫu nhiên của các điểm giao hàng. Mỗi hoán vị là một cá thể.

**Selection - Tournament Selection**: chọn ngẫu nhiên một nhóm cá thể, sau đó lấy cá thể có fitness tốt nhất trong nhóm. Cách này giúp giữ lại cá thể tốt nhưng vẫn duy trì sự đa dạng.

**Crossover - Order Crossover (OX)**: lai ghép hai cha mẹ để tạo cá thể con, đồng thời bảo toàn tính hợp lệ của hoán vị. OX phù hợp với bài toán sắp xếp thứ tự vì không làm trùng điểm giao hàng.

**Mutation - Swap Mutation**: chọn hai vị trí trong chromosome và hoán đổi chúng. Đột biến giúp thuật toán tránh bị kẹt ở nghiệm cục bộ.

**Elitism**: giữ lại một số cá thể tốt nhất sang thế hệ sau. Điều này đảm bảo nghiệm tốt không bị mất trong quá trình lai ghép và đột biến.

#### Vai trò trong đề tài

GA là phần tối ưu hóa chính. Sau khi A* cung cấp ma trận chi phí giữa các điểm, GA thử nhiều thứ tự giao hàng khác nhau và cải thiện dần qua các thế hệ. Kết quả cuối cùng là một lộ trình có tổng quãng đường nhỏ hơn lộ trình tuần tự trong đa số trường hợp.

#### Ưu điểm

- Phù hợp với bài toán tối ưu tổ hợp như TSP/VRP.
- Không cần duyệt toàn bộ `m!` khả năng.
- Có thể tìm nghiệm tốt trong thời gian chấp nhận được.
- Dễ mở rộng thêm nhiều ràng buộc như thời gian giao hàng, trọng tải, chi phí ưu tiên.
- Có thể minh họa quá trình hội tụ bằng biểu đồ fitness qua các thế hệ.

#### Hạn chế

- Không đảm bảo luôn tìm được nghiệm tối ưu tuyệt đối.
- Kết quả phụ thuộc vào tham số như kích thước quần thể, số thế hệ, tỷ lệ đột biến.
- Có yếu tố ngẫu nhiên nên mỗi lần chạy có thể cho kết quả hơi khác nhau.
- Nếu tham số không phù hợp, thuật toán có thể hội tụ chậm hoặc mắc kẹt ở nghiệm cục bộ.

### 2.3. TT3 - Mô hình kết hợp A* + GA

#### Khái niệm

Trong đề tài này, chỉ có hai thuật toán chính được sử dụng độc lập là **A*** và **Genetic Algorithm**. Tuy nhiên, giải pháp hoàn chỉnh không dùng riêng từng thuật toán, mà kết hợp cả hai theo mô hình:

```text
A* -> Ma trận khoảng cách -> GA -> Lộ trình giao hàng tối ưu
```

A* chịu trách nhiệm tính chi phí đường đi ngắn nhất giữa từng cặp điểm. GA sử dụng các chi phí đó để đánh giá và tối ưu thứ tự giao hàng. Vì vậy, TT3 trong báo cáo được hiểu là **phương án kết hợp hai thuật toán**, không phải một thuật toán thứ ba độc lập.

#### Vai trò trong đề tài

Mô hình kết hợp A* + GA giải quyết bài toán theo hai tầng:

- Tầng 1: A* tìm khoảng cách ngắn nhất giữa các điểm.
- Tầng 2: GA chọn thứ tự đi qua các điểm sao cho tổng quãng đường nhỏ.

Nếu chỉ dùng A*, hệ thống chỉ biết cách đi ngắn nhất từ một điểm đến một điểm khác, nhưng chưa biết nên giao hàng theo thứ tự nào. Nếu chỉ dùng GA mà không có ma trận khoảng cách, việc đánh giá từng lộ trình sẽ thiếu dữ liệu chi phí giữa các điểm. Vì vậy, mô hình kết hợp giúp hai thuật toán bổ sung cho nhau.

#### Ưu điểm

- Phân chia bài toán rõ ràng thành tìm đường và tối ưu thứ tự.
- Kết hợp được ưu điểm của A* trong tìm đường ngắn nhất và GA trong tối ưu tổ hợp.
- Dễ minh họa trên giao diện qua bản đồ, bảng kết quả và biểu đồ hội tụ.
- Có khả năng mở rộng cho các bài toán giao hàng phức tạp hơn.

#### Hạn chế

- Thời gian tính toán tăng khi số điểm giao hàng lớn vì cần xây dựng ma trận khoảng cách và chạy GA nhiều thế hệ.
- Chất lượng nghiệm cuối phụ thuộc vào tham số GA.
- GA là thuật toán gần đúng nên không đảm bảo tối ưu tuyệt đối trong mọi lần chạy.

## 3. Phương pháp đánh giá lựa chọn thuật toán

### 3.1. Các hướng xử lý được đánh giá

Đề tài xét hai thuật toán chính và một mô hình kết hợp:

- **TT1 - A***: dùng để tìm đường đi ngắn nhất giữa hai điểm.
- **TT2 - Genetic Algorithm**: dùng để tối ưu thứ tự giao hàng.
- **TT3 - A* + GA**: mô hình kết hợp hai thuật toán để giải bài toán hoàn chỉnh.

### 3.2. Tiêu chí đánh giá

Các tiêu chí được dùng để lựa chọn thuật toán:

| Tiêu chí | Ý nghĩa |
|---|---|
| Độ phù hợp bài toán | Thuật toán có giải quyết đúng vấn đề cần xử lý không |
| Chất lượng kết quả | Tổng quãng đường và thời gian có được cải thiện không |
| Khả năng mở rộng | Có thể áp dụng khi số điểm tăng hoặc bài toán phức tạp hơn không |
| Tính trực quan | Có dễ minh họa trên giao diện và giải thích cho giáo viên không |
| Chi phí tính toán | Thời gian chạy có chấp nhận được không |
| Khả năng kết hợp | Có thể phối hợp với thuật toán khác trong hệ thống không |

### 3.3. Đánh giá từng hướng xử lý

#### A*

A* phù hợp cho bài toán tìm đường đi giữa hai điểm vì thuật toán vừa xét chi phí đã đi vừa dùng heuristic để định hướng tìm kiếm. So với tìm kiếm mù như BFS hoặc Dijkstra trong một số trường hợp, A* có thể giảm số node cần xét nếu heuristic tốt.

Trong đề tài, A* được chọn vì:

- Có cơ sở lý thuyết rõ ràng trong môn Trí tuệ nhân tạo.
- Dễ giải thích qua công thức `f(n) = g(n) + h(n)`.
- Có thể hiển thị từng bước chạy trên giao diện.
- Có thể mở rộng cho bản đồ có vật cản hoặc mạng đường thực tế.
- Tạo được ma trận chi phí đáng tin cậy cho GA.

#### Genetic Algorithm

GA phù hợp cho bài toán sắp xếp thứ tự giao hàng vì đây là bài toán tối ưu tổ hợp. Nếu dùng vét cạn, số trường hợp tăng theo giai thừa và nhanh chóng không khả thi. GA cho phép tìm nghiệm tốt mà không cần duyệt toàn bộ không gian nghiệm.

GA được chọn vì:

- Phù hợp với bài toán TSP/VRP dạng hoán vị.
- Có khả năng tìm nghiệm tốt trong thời gian hợp lý.
- Có các toán tử rõ ràng: selection, crossover, mutation, elitism.
- Dễ biểu diễn nghiệm bằng chromosome.
- Có thể hiển thị biểu đồ hội tụ để đánh giá quá trình tối ưu.

#### Mô hình kết hợp A* + GA

Mô hình kết hợp A* + GA được chọn vì bài toán giao hàng không chỉ là bài toán tìm đường giữa hai điểm, cũng không chỉ là bài toán sắp xếp thứ tự. Nó gồm cả hai phần:

- Tìm chi phí di chuyển giữa các điểm.
- Chọn thứ tự đi qua các điểm để giảm tổng chi phí.

A* phù hợp với phần thứ nhất, GA phù hợp với phần thứ hai. Do đó, phương án kết hợp là lựa chọn hợp lý hơn so với việc chỉ dùng riêng một thuật toán.

Trong phần đánh giá kết quả, chương trình vẫn dùng **lộ trình tuần tự** làm tuyến đối chiếu. Tuyến tuần tự không được xem là thuật toán chính của đề tài, mà chỉ là mốc đối chiếu để đo mức cải thiện của mô hình A* + GA.

### 3.4. Lý do chọn mô hình kết hợp A* + GA

Bài toán giao hàng có hai lớp quyết định:

1. Đi từ điểm A đến điểm B như thế nào là ngắn nhất.
2. Nên đi qua các điểm giao hàng theo thứ tự nào để tổng đường đi là nhỏ nhất.

A* giải quyết lớp thứ nhất, còn GA giải quyết lớp thứ hai. Nếu chỉ dùng A*, chương trình chỉ biết đường đi ngắn nhất giữa hai điểm nhưng không biết thứ tự giao hàng tối ưu. Nếu chỉ dùng GA mà không có ma trận chi phí từ A*, việc đánh giá route sẽ thiếu nền tảng đường đi giữa các điểm. Vì vậy, kết hợp A* + GA là lựa chọn hợp lý:

- A* tạo dữ liệu khoảng cách chính xác giữa từng cặp điểm.
- GA dùng dữ liệu đó để tối ưu thứ tự giao hàng.
- Lộ trình tuần tự làm mốc so sánh để đánh giá hiệu quả.

## 4. Xây dựng giải pháp bài toán và kết quả

### 4.1. Quy trình xây dựng giải pháp

Giải pháp được xây dựng theo luồng sau:

1. Người dùng chọn kịch bản hoặc nhập số điểm giao hàng.
2. Chương trình sinh danh sách điểm gồm kho hàng và các điểm giao.
3. Chương trình xây dựng đồ thị từ danh sách điểm.
4. Người dùng chọn heuristic cho A*.
5. Chạy A* cho mọi cặp điểm để xây dựng ma trận khoảng cách.
6. Người dùng chạy GA để tối ưu thứ tự giao hàng.
7. GA trả về lộ trình tốt nhất, tổng quãng đường và lịch sử fitness.
8. Giao diện hiển thị lộ trình dự đoán, thời gian ước tính và biểu đồ hội tụ.
9. Hệ thống so sánh lộ trình A* + GA với lộ trình tuần tự.

### 4.2. Dữ liệu đầu vào

Dữ liệu đầu vào từ giao diện gồm:

- **Số điểm giao hàng**: số lượng điểm cần tạo trên bản đồ.
- **Tốc độ xe**: dùng để quy đổi quãng đường sang thời gian di chuyển.
- **Heuristic A***: người dùng chọn `euclidean` hoặc `manhattan`.
- **Kịch bản nhanh**: nội thành, ngoại ô, hỗn hợp hoặc tùy chỉnh.

### 4.3. Dữ liệu đầu ra

Hệ thống hiển thị các kết quả:

- Bản đồ các điểm giao hàng.
- Lộ trình A* + GA sau khi tối ưu.
- Tổng quãng đường của lộ trình tối ưu.
- Tổng thời gian ước tính.
- Số điểm giao đã hoàn thành.
- Biểu đồ hội tụ GA.
- Bảng so sánh tuyến tuần tự và tuyến A* + GA.
- Danh sách lộ trình của từng phương pháp trong cửa sổ so sánh.

### 4.4. Hiển thị kết quả dự đoán

Khi thuật toán chạy xong, hệ thống dự đoán lộ trình giao hàng tốt nhất theo dạng:

```text
Kho hàng -> Điểm giao A -> Điểm giao B -> ... -> Kho hàng
```

Trên giao diện, tuyến đường được vẽ trực tiếp trên bản đồ bằng đường nối và mũi tên chỉ hướng. Danh sách lộ trình cũng được hiển thị để người dùng biết thứ tự giao hàng cụ thể.

Kết quả dự đoán không chỉ gồm thứ tự điểm mà còn có:

- Tổng km cần đi.
- Thời gian di chuyển dự kiến.
- Quá trình giao hàng mô phỏng bằng animation.
- Biểu đồ cho thấy fitness của GA giảm dần qua các thế hệ.

### 4.5. Đánh giá và so sánh kết quả

Phần so sánh được thực hiện giữa:

- **Lộ trình tuần tự**: `0 -> 1 -> 2 -> ... -> n -> 0`.
- **Lộ trình A* + GA**: thứ tự điểm do GA tối ưu dựa trên ma trận khoảng cách từ A*.

Các chỉ số so sánh:

| Chỉ số | Ý nghĩa |
|---|---|
| Tổng quãng đường | Tổng km xe cần đi |
| Thời gian ước tính | Thời gian dự kiến dựa trên tốc độ xe |
| Số km tiết kiệm | Chênh lệch giữa tuyến tuần tự và tuyến A* + GA |
| Phần trăm cải thiện | Tỷ lệ giảm quãng đường so với tuyến tuần tự |
| Lộ trình cụ thể | Danh sách điểm đi qua của từng phương pháp |

Công thức phần trăm cải thiện:

```text
improvement = ((distance_baseline - distance_ga) / distance_baseline) * 100
```

Nếu `improvement` lớn hơn `0`, tuyến A* + GA tốt hơn tuyến tuần tự. Nếu bằng `0` hoặc nhỏ hơn, điều đó cho thấy tuyến tuần tự trong trường hợp đó đã tương đương hoặc tốt hơn, thường chỉ xảy ra ở một số cấu hình điểm đặc biệt hoặc do đặc tính ngẫu nhiên của GA.

### 4.6. Kết quả đạt được

Sau khi xây dựng chương trình, hệ thống đạt được các kết quả:

- Sinh được bản đồ giao hàng theo số điểm người dùng chọn.
- Tính được ma trận khoảng cách giữa các điểm bằng A*.
- Tối ưu được thứ tự giao hàng bằng Genetic Algorithm.
- Hiển thị được lộ trình tối ưu trên bản đồ.
- Hiển thị được quá trình hội tụ của GA.
- So sánh được tuyến tuần tự và tuyến A* + GA.
- Chỉ rõ tuyến nào tối ưu hơn trong cửa sổ so sánh.
- Người dùng có thể thay đổi số điểm, tốc độ và heuristic để quan sát kết quả khác nhau.

### 4.7. Nhận xét

Việc kết hợp A* và GA là phù hợp với mục tiêu đề tài. A* đảm nhiệm phần tìm đường đi ngắn nhất giữa các điểm, còn GA đảm nhiệm phần tối ưu thứ tự giao hàng. Cách chia này làm cho bài toán rõ ràng, dễ giải thích và dễ mở rộng.

So với lộ trình tuần tự, lộ trình A* + GA thường có tổng quãng đường ngắn hơn do GA thử nhiều hoán vị khác nhau và giữ lại nghiệm tốt qua từng thế hệ. Tuy nhiên, vì GA là thuật toán gần đúng và có yếu tố ngẫu nhiên, kết quả có thể thay đổi giữa các lần chạy. Điều này phù hợp với đặc điểm của các thuật toán tối ưu tiến hóa.

### 4.8. Hướng phát triển

Trong tương lai, đề tài có thể mở rộng theo các hướng:

- Thêm vật cản hoặc đường cấm trên bản đồ để A* thể hiện rõ vai trò tìm đường.
- Dùng dữ liệu bản đồ thực tế thay vì tọa độ ngẫu nhiên.
- Bổ sung nhiều xe giao hàng.
- Thêm ràng buộc thời gian giao hàng.
- Thêm trọng tải xe và số lượng hàng hóa.
- So sánh GA với các thuật toán khác như Greedy, Simulated Annealing hoặc Ant Colony Optimization.
- Lưu lịch sử kết quả để thống kê nhiều lần chạy.

## 5. Kết luận

Đề tài đã xây dựng được một hệ thống mô phỏng tối ưu đường đi giao hàng bằng cách kết hợp thuật toán A* và Genetic Algorithm. A* được dùng để tính đường đi ngắn nhất giữa các điểm, còn GA được dùng để tìm thứ tự giao hàng tối ưu hơn. Lộ trình tuần tự được sử dụng làm phương án cơ sở để đánh giá mức cải thiện.

Kết quả cho thấy mô hình A* + GA phù hợp với bài toán tối ưu lộ trình giao hàng, có khả năng minh họa trực quan và đáp ứng yêu cầu của môn học Trí tuệ nhân tạo. Hệ thống không chỉ đưa ra kết quả dự đoán mà còn trình bày được quá trình tối ưu, giúp người xem hiểu rõ cách thuật toán hoạt động và lý do chọn thuật toán.
