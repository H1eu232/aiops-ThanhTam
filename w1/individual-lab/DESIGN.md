# Detection Approach - DESIGN.md

## Approach tôi dùng

Rule-based detection kết hợp cửa sổ trượt ngắn.

## Tại sao chọn approach này

Data đến liên tục theo stream và fault trong generator có dấu hiệu rất rõ trên metric. Rule-based detection dễ chạy realtime, không cần training data, giải thích được vì sao alert được bắn, và phù hợp với bài lab 3 giờ. Pipeline dùng HTTP server chuẩn của Python nên không cần cài thêm thư viện.

## Cách hoạt động

Pipeline nhận từng payload ở endpoint `/ingest`, đọc metrics và logs, sau đó tính tín hiệu cho 3 loại fault: `memory_leak`, `traffic_spike`, và `dependency_timeout`. Mỗi loại fault phải có nhiều metric cùng bất thường, ví dụ memory leak cần memory utilization cao kèm GC pause cao, traffic spike cần RPS cao kèm queue/latency tăng, dependency timeout cần upstream timeout rate và 5xx cùng tăng. Pipeline giữ 5 sample gần nhất và chỉ alert khi cùng một fault xuất hiện ít nhất 2 lần trong cửa sổ, giúp giảm false alert do noise. Sau khi alert, pipeline có cooldown để không ghi quá nhiều dòng trùng lặp.

## Parameters tôi chọn

- Window size: 5 sample gần nhất.
- Minimum hits: 2 sample trong window và sample hiện tại vẫn đang bất thường.
- Cooldown: 20 tick cho mỗi loại fault.
- Memory leak: memory utilization >= 75%, GC pause >= 60ms, kèm latency/5xx/log evidence.
- Traffic spike: RPS >= 350, queue depth >= 50, upstream timeout rate < 5%, kèm latency/5xx/log evidence.
- Dependency timeout: upstream timeout rate >= 8%, 5xx >= 3%, kèm latency/log evidence.

Các ngưỡng này cao hơn khoảng normal trong đề bài nên tránh báo giả trước fault, nhưng vẫn đủ thấp để phát hiện sớm khi generator bắt đầu inject sự cố.

## Cải thiện nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ thêm baseline động theo rolling mean/standard deviation để threshold tự thích nghi theo traffic theo giờ, thêm unit test cho từng fault type, và expose endpoint `/alerts` để xem alert gần nhất khi demo.
