# Hướng dẫn demo code A* và Genetic Algorithm

## Cách chạy

Chạy demo đầy đủ:

```bash
python main.py --demo
```

Chạy demo kèm giải thích biến trong code:

```bash
python main.py --demo --verbose
```

Chạy chế độ hỏi nhanh:

```bash
python main.py --explain
```

## A* trong đề tài

A* được import từ `delivery_optimizer/algorithms/astar.py`. Thuật toán dùng công thức:

```text
f(n) = g(n) + h(n)
```

- `g(n)`: chi phí thực tế từ điểm bắt đầu đến node hiện tại.
- `h(n)`: heuristic ước lượng từ node hiện tại đến đích.
- `f(n)`: điểm ưu tiên để chọn node tiếp theo.

Code dùng `SimplePriorityQueue` dựa trên `heapq`, giúp luôn lấy node có `f_score` nhỏ nhất. Biến `came_from` lưu node cha để dựng lại đường đi sau khi tìm được goal.

## Genetic Algorithm trong đề tài

GA được import từ `delivery_optimizer/algorithms/genetic.py`. Một nghiệm được mã hóa bằng `chromosome`, là một hoán vị các điểm giao hàng, không chứa depot `0`.

Các thành phần chính:

- `population`: tập nhiều chromosome.
- `fitness`: tổng quãng đường, càng thấp càng tốt.
- `selection`: chọn cha mẹ bằng tournament selection.
- `crossover`: dùng order crossover để giữ thứ tự tương đối của route.
- `mutation`: dùng swap mutation để đổi chỗ hai điểm giao.
- `elitism`: giữ lại các cá thể tốt nhất sang thế hệ sau.

## Quy trình hiện tại

Bản hiện tại không còn chạy một mode riêng tên **A* + GA**. Hệ thống tách vai trò thành các chế độ rõ ràng:

1. **Tuyến tuần tự ban đầu**: đi theo thứ tự `0 -> 1 -> 2 -> ... -> n -> 0`, dùng làm mốc đối chiếu.
2. **A* tuần tự**: vẫn đi theo thứ tự tuần tự, nhưng dùng A* để tìm đường hợp lệ trên mạng đường/hẻm và tránh vật cản.
3. **GA tối ưu**: GA tối ưu thứ tự giao hàng theo metric Euclid, hỗ trợ nhiều xe, tải trọng và khung giờ. Sau khi GA chọn thứ tự, backend tính lại quãng đường thực tế và `route_paths` để vẽ tuyến đúng trên bản đồ.
4. **So sánh A* vs GA**: chạy A* tuần tự và GA để đối chiếu tổng km, thời gian, runtime, số xe và mức cải thiện.

## Artifact sau khi chạy

Khi chạy `python main.py --demo`, hệ thống tạo:

- `outputs/demo_terminal/terminal_demo_summary.json`
- `outputs/demo_terminal/astar_demo_steps.json`
- `outputs/demo_terminal/ga_demo_history.json`
- `outputs/demo_terminal/astar_ga_result.json` nếu chạy demo terminal cũ; UI web hiện tại không dùng mode A*+GA riêng.
- `outputs/demo_terminal/terminal_demo_log.txt`

## Câu hỏi giảng viên có thể hỏi

### Vì sao dùng priority queue trong A*?

Vì A* cần lấy node có `f_score` nhỏ nhất ở mỗi vòng lặp. Priority queue giúp thao tác này nhanh hơn so với quét tuyến tính toàn bộ danh sách.

### `came_from` dùng để làm gì?

`came_from` lưu node cha tốt nhất của mỗi node. Khi A* gặp đích, hàm `reconstruct_path` đi ngược từ goal về start để tạo đường đi cuối cùng.

### `g_score` và `f_score` khác nhau thế nào?

`g_score` là chi phí đã đi thật. `f_score` là chi phí dự kiến tổng, bằng `g_score + heuristic`.

### GA tối ưu cái gì?

GA tối ưu thứ tự giao hàng và chia tuyến. Nó không tự tìm đường tránh vật cản trong bước fitness; sau khi GA chọn thứ tự, backend lấy lại quãng đường và path thực tế để hiển thị tuyến hợp lệ trên bản đồ.

### Vì sao không chỉ dùng A*?

A* tìm đường tốt giữa hai điểm, nhưng không quyết định thứ tự giao nhiều điểm. Nếu đi theo thứ tự ban đầu, tổng quãng đường có thể dài.

### Vì sao không chỉ dùng GA?

GA hiện dùng metric Euclid để chạy nhanh và dễ quan sát hội tụ. A* vẫn cần thiết để minh họa đường đi hợp lệ, chạy tuyến A* tuần tự và cung cấp path chi tiết cho giao diện.

### Vì sao hiện tại không trình bày mode A* + GA riêng?

Để phần demo dễ hiểu và không trộn lẫn kết quả, UI hiện tại tách riêng A* tuần tự và GA. A* thể hiện năng lực tìm đường hợp lệ, còn GA thể hiện năng lực tối ưu thứ tự/chia xe. Khi cần so sánh, hệ thống đặt hai kết quả cạnh nhau thay vì gọi đó là một thuật toán lai độc lập.
