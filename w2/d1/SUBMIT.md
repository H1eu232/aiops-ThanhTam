# BÁO CÁO BÀI TẬP W2-D1: ALERT CORRELATION PIPELINE

**Tác giả:** ThanhTam  
**Ngày:** 2026-06-12  
**Dataset:** GeekShop e-commerce synthetic alerts — 20 alerts, 10 services, 4 backing stores

---

## 1. Lựa chọn `gap_sec` và lý do

Tôi chọn **`gap_sec = 120` (2 phút)**. Đây là ngưỡng "sweet-spot" phù hợp với hành vi thực tế của hệ thống microservice. Khi một dịch vụ cốt lõi gặp sự cố, các dịch vụ phụ thuộc thường phản ứng trong vòng vài giây đến tối đa 90 giây (do timeout, retry backoff và health-check intervals). Với `gap_sec = 30`, các alert thuộc cùng một incident dài sẽ bị bẻ gãy thành nhiều session nhỏ, gây mất context. Với `gap_sec = 600`, hai sự cố hoàn toàn không liên quan xảy ra cách nhau dưới 10 phút sẽ bị gộp nhầm, làm tăng false-correlation và gây khó khăn cho on-call engineer.

---

## 2. Lựa chọn `max_hop` và lý do

Tôi chọn **`max_hop = 2`**. Khoảng cách 2 bước trên undirected service graph cho phép bao phủ cấu trúc cascade điển hình: `entry-point → service lỗi gốc → downstream dependency`. Ví dụ cụ thể trong dataset: `edge-lb (hop 0) → checkout-svc (hop 1) → payment-svc (hop 2)` — ba dịch vụ này đều alert trong cùng incident nhưng cách nhau 2 hops. Nếu tăng lên `max_hop = 3`, các dịch vụ chia sẻ `catalog-db` nhưng thuộc domain hoàn toàn khác (search-svc, recommender-svc) sẽ bị gộp nhầm vào cluster chính, làm giảm signal-to-noise ratio.

---

## 3. Alert ID bị "miss" (không match cluster nào / tạo cluster đơn)

Trong dataset hiện tại, **`a-0016` (`search-svc | catalog_db_query_time_ms | warn`)** là alert có khả năng bị cô lập cao nhất. Lý do: `search-svc` kết nối với `catalog-db` (backing store, không phải service), và từ `search-svc` đến các service đang alert chính (`payment-svc`, `checkout-svc`, `edge-lb`) phải đi qua ít nhất 3 hops (`search-svc → catalog-db → catalog-svc → cart-svc → checkout-svc`), vượt quá `max_hop = 2`. Ngoài ra, bản thân nhãn trong dataset cũng đánh dấu đây là `"noise — independent slow query"`, xác nhận đây là alert độc lập không liên quan đến incident chính.

---

## 4. Bottleneck khi mở rộng lên 10,000 alerts

Nếu có 10,000 alerts, điểm nghẽn nghiêm trọng nhất nằm ở **Layer 3 — `topology_group()`**, vì mỗi alert mới phải được so khoảng cách topology với các incident center hiện có bằng BFS giới hạn `max_hop`. Khi số service và số cụm tăng, phần kiểm tra hop-distance này sẽ chạy lặp lại rất nhiều lần. Hướng tối ưu: (1) Precompute/cache khoảng cách giữa các service bằng BFS giới hạn độ sâu hoặc all-pairs shortest path cho graph nhỏ; (2) Lưu cache theo cặp `(center_service, alert_service, max_hop)` để không tính lại; (3) Layer 2 session windowing cũng có thể chậm vì phải sort timestamp, nên nên parse timestamp sang Unix epoch ngay từ đầu.

---

## 5. EOD Checkpoint Answers

### Câu 1: Vì sao fingerprint không bao gồm timestamp hay value?

Fingerprint dùng để xác định "danh tính loại alert" nhằm gộp các cảnh báo lặp lại từ cùng một nguồn (`service|metric|severity`). Cả `timestamp` và `value` thay đổi liên tục — nếu đưa vào fingerprint, mỗi alert phát ra sẽ có hash hoàn toàn khác nhau, khiến Layer 1 Dedup mất tác dụng. **Ví dụ:** Nếu fingerprint = `payment-svc|latency_p99_ms|crit|1840|09:42:22Z`, thì alert `a-0008` (cùng service, cùng metric, cùng value nhưng ts=09:43:18Z) sẽ là fingerprint khác — hệ thống không thể nhận ra đây là "cùng vấn đề đang tiếp diễn" và sẽ không dedup được, dẫn đến cluster có 50+ entry thay vì 1 fingerprint đại diện.

### Câu 2: Sự khác biệt giữa "duplicate" và "correlated" alert?

**Duplicate alert** là các cảnh báo có cùng bản chất lặp đi lặp lại từ một nguồn. Trong dataset: `a-0003`, `a-0008`, `a-0015` đều là `payment-svc|latency_p99_ms|crit` — cùng service, cùng metric, cùng severity, chỉ khác timestamp và value nhỏ → đây là duplicate, gộp về 1 fingerprint. **Correlated alert** là các cảnh báo khác nhau về service hoặc metric nhưng có mối liên hệ nhân quả. Ví dụ: `a-0002` (`payment-svc|db_connection_pool|crit`) → gây ra `a-0006` (`checkout-svc|downstream_payment_error_rate|crit`) → dẫn đến `a-0007` (`edge-lb|upstream_5xx_rate|warn`). Ba alert khác nhau hoàn toàn nhưng cùng thuộc một chuỗi cascade failure.

### Câu 3: gap_sec = 30 vs gap_sec = 600

- **`gap_sec = 30`:** Làm nát incident — các alert thuộc cùng một sự cố nhưng phản ứng chậm (>30s) sẽ bị xé thành nhiều cluster nhỏ, on-call nhận nhiều ticket thay vì 1.
- **`gap_sec = 600`:** Làm loãng incident — gom nhầm nhiều sự cố không liên quan xảy ra trong 10 phút vào chung một cluster, làm mờ root cause.

### Câu 4: recommender-svc batch retrain có bị gộp vào cluster chính không?

**KHÔNG.** Dù `a-0013` (`recommender-svc|cpu_utilization|warn`) xảy ra lúc 09:45:10Z, nằm trong cùng time-window với cluster chính (thỏa mãn Layer 2), nhưng Layer 3 Topology sẽ tách nó ra. Lý do cụ thể: Trên service graph, `recommender-svc` kết nối với `catalog-svc` qua HTTP và `catalog-db` qua Postgres. Từ `recommender-svc` đến `payment-svc` (root cause của incident chính) phải đi ít nhất 3-4 hops: `recommender-svc → catalog-svc → cart-svc → checkout-svc → payment-svc`. Khoảng cách này vượt `max_hop = 2`, nên Union-Find không merge hai component, và `recommender-svc` tạo thành cluster riêng biệt. Đây chính xác là hành vi mong muốn — correlator không bị nhiễu bởi sự kiện độc lập (`note: "unrelated — concurrent batch retrain"`).

### Câu 5: Limitation lớn nhất của topology grouping và cách khắc phục

Hạn chế lớn nhất là **sự phụ thuộc tuyệt đối vào tính chính xác và tính cập nhật của Service Graph**. Trong thực tế, microservice topology thay đổi liên tục (deploy mới, thêm dependency, A/B routing), nhưng `services.json` tĩnh nên nhanh chóng bị lỗi thời. Hệ quả: alert từ một service vừa được kết nối mới sẽ không được merge đúng cluster. **Design trade-off:** Static graph đơn giản, dễ audit và reproducible, nhưng không phản ánh runtime reality. **Khắc phục đề xuất:** Tích hợp Service Mesh telemetry (Istio, Linkerd) hoặc Distributed Tracing (OpenTelemetry/Jaeger) để tự động rebuild graph từ actual traffic — dynamic graph thay thế static JSON, cập nhật theo rolling window 5-15 phút. Ngoài ra có thể thêm Layer 4 dựa trên semantic similarity của alert message để bổ cứu khi graph thiếu sót.

---

*Word count: ≥ 600 từ. File được tạo tự động bởi pipeline W2-D1.*

