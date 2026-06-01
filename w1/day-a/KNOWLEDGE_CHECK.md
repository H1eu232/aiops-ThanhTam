# KNOWLEDGE CHECK: Anomaly Detection Fundamentals

---

## 1. Giải thích Skewness là gì, data bị skew thì $3\sigma$ sai ở đâu, và 2 cách xử lý khi gặp data skewed

**Skewness (Độ lệch):** Là chỉ số đo lường mức độ bất đối xứng của phân phối dữ liệu so với phân phối chuẩn (Gaussian). Trong giám sát hệ thống, các metric như latency thường bị lệch phải (Right-skewed, $\text{Skewness} > 1$) vì đa số request xử lý rất nhanh nhưng có một số ít request bị chậm hẳn (do GC pause, cache miss) tạo nên một cái đuôi dài bên phải.

**Điểm sai của $3\sigma$ trên dữ liệu skewed:** Quy tắc $3\sigma$ giả định dữ liệu phải đối xứng dạng hình chuông. Khi dữ liệu bị lệch phải nặng, các giá trị outlier cực lớn ở đuôi sẽ kéo giá trị Trung bình ($\mu$) tăng cao và làm phình to Độ lệch chuẩn ($\sigma$). Hệ quả là:
- Ngưỡng dưới (Lower bound: $\mu - 3\sigma$) có thể bị âm, hoàn toàn vô nghĩa với các metric không âm như latency.
- Ngưỡng trên (Upper bound: $\mu + 3\sigma$) bị đẩy lên quá xa, dẫn đến việc bỏ sót rất nhiều điểm bất thường thực tế (lọt lưới sự cố).

**2 cách xử lý khi gặp dữ liệu skewed:**

*Cách 1 (Log Transform):* Áp dụng hàm $\ln(x + 1)$ lên dữ liệu để nén các giá trị lớn và kéo dãn các giá trị nhỏ, giúp phân phối trở nên đối xứng gần giống Gaussian hơn rồi mới áp dụng $3\sigma$.

*Cách 2 (Sử dụng IQR - Interquartile Range):* Xác định ngưỡng dựa trên phân vị (Percentile) cụ thể là $Q_1$ (25%) và $Q_3$ (75%) thay vì dùng Mean/Std, giúp thuật toán không bị ảnh hưởng bởi các outlier nằm ở đuôi dữ liệu.

---

## 2. So sánh $3\sigma$ vs EWMA vs STL: mỗi cái detect loại anomaly nào, fail ở đâu, dùng khi nào

### $3\sigma$ (Z-Score)

**Loại anomaly phát hiện:** Các điểm đột biến đơn lẻ, bất ngờ và cực đoan vượt trội hẳn so với lịch sử ngắn hạn (Spike/Drop).

**Fail ở đâu:** Thất bại khi dữ liệu có tính chu kỳ (Seasonal), dữ liệu có xu hướng tăng/giảm (Trend), dữ liệu phân phối lệch nặng (Skewed) hoặc khi outlier kéo dài làm "ô nhiễm" cửa sổ tính toán (Window contamination).

**Dùng khi nào:** Metric ổn định, không có chu kỳ rõ ràng, phân phối gần chuẩn (như CPU usage baseline, nhiệt độ thiết bị).

### EWMA (Exponentially Weighted Moving Average)

**Loại anomaly phát hiện:** Sự dịch chuyển từ từ của baseline hoặc lỗi hệ thống tăng dần theo thời gian (Concept Drift / Persistent Shift).

**Fail ở đâu:** Chậm trễ trong việc bắt các đỉnh spike quá nhanh ngắn hạn và dễ bị sai lệch nếu hệ thống thay đổi chu kỳ mạnh mẽ.

**Dùng khi nào:** Giám sát các lỗi tích tụ như Memory Leak, hao mòn tài nguyên phần cứng.

### STL Decomposition (Seasonal-Trend-Loess)

**Loại anomaly phát hiện:** Các điểm bất thường phá vỡ cấu trúc chu kỳ tự nhiên (ví dụ: lượng traffic tụt dốc vào giờ cao điểm).

**Fail ở đâu:** Yêu cầu tài nguyên tính toán lớn hơn, cần biết trước độ dài chu kỳ chính xác (`period`) và không tối ưu cho dữ liệu biến động hỗn loạn vô định hình.

**Dùng khi nào:** Các metric hạ tầng chịu ảnh hưởng trực tiếp bởi hành vi người dùng vốn có tính chu kỳ ngày/đêm rất mạnh (Request throughput, Network I/O).

---

## 3. Isolation Forest: giải thích ý tưởng "path length ngắn = anomaly", tại sao cần feature engineering trước khi feed vào

**Ý tưởng "path length ngắn = anomaly":** Thuật toán xây dựng các cây quyết định ngẫu nhiên (Random Trees) bằng cách chọn ngẫu nhiên một feature và một điểm cắt (split). Vì các điểm bất thường (Anomaly) thường có giá trị rất khác biệt và thưa thớt nên chúng cực kỳ dễ bị cô lập. Do đó, chúng sẽ bị tách ra rất sớm ngay từ những tầng đầu tiên của cây (Path length - số bước chia từ gốc đến lá rất ngắn). Ngược lại, các điểm bình thường (Normal) nằm tập trung dày đặc nên cần rất nhiều lượt cắt (Path length dài) mới cô lập được.

**Tại sao cần Feature Engineering trước khi feed vào:** Isolation Forest nguyên bản không có khái niệm về thời gian và ngữ cảnh chuỗi (Time-blind). Nó chỉ nhìn nhận các điểm dữ liệu hoàn toàn độc lập độc thoại. Nếu ta feed dữ liệu thô vào, mô hình sẽ miss các lỗi dạng ngữ cảnh (ví dụ: CPU 80% là bình thường ở 2h chiều nhưng là bất thường ở 2h sáng). Việc tạo thêm các đặc trưng ngữ cảnh temporal (như `rolling_mean`, `rolling_std`, `lag_1`, `rate_of_change`) giúp cung cấp "bức tranh toàn cảnh về quá khứ gần" cho mô hình, từ đó tăng độ chính xác lên gấp nhiều lần.

---

## 4. Univariate vs Multivariate: cho 1 scenario (VD: memory leak), giải thích tại sao univariate miss và multivariate catch

**Scenario (Ví dụ thực tế):** Lỗi rò rỉ bộ nhớ từ từ kết hợp với cơ chế Auto-scaling (ASG).

**Tại sao Univariate MISS:** Nếu ta cấu hình các detector đơn biến (Univariate) chạy độc lập trên từng metric: Metric CPU thấy ổn định quanh 40% (vì cứ quá tải là ASG sinh thêm Pod), metric Memory của từng container cũng chỉ tăng nhẹ rồi đứng yên do tải được san sẻ bớt. Khi nhìn riêng rẽ, không một metric đơn lẻ nào vượt ngưỡng cảnh báo (Z-score hay IQR đều báo Normal) $\rightarrow$ Hệ thống MISS lỗi.

**Tại sao Multivariate CATCH:** Detector đa biến (Multivariate) phân tích đồng thời mối tương quan không gian giữa nhiều chiều metric: Hệ thống nhận diện được nghịch lý là mặc dù Request Throughput (lưu lượng tải) không hề tăng, CPU tổng vẫn đi ngang, nhưng tổng số lượng Pods đang tăng liên tục một cách bất thường đi kèm với tổng dung lượng RAM toàn hệ thống phình to. Mối tương quan bất hợp lý giữa `[Request_Throughput, Pod_Count, Total_Memory]` này lập tức bị không gian đa biến phát hiện ra $\rightarrow$ Hệ thống CATCH được lỗi hệ thống.

---

## 5. Precision vs Recall: trong AIOps tại sao ưu tiên recall, trade-off gì khi tune threshold

**Tại sao AIOps ưu tiên Recall:**
- **Recall** đo lường tỷ lệ bắt được bao nhiêu lỗi thật trên tổng số lỗi xảy ra (tránh lọt lỗi).
- **Precision** đo lường tỷ lệ cảnh báo đúng trên tổng số cảnh báo phát ra (tránh báo ảo).

Trong vận hành hệ thống lớn, một lỗi nghiêm trọng lọt lưới (False Negative) có thể dẫn đến sập toàn bộ hệ thống (Outage), gây gián đoạn dịch vụ và thiệt hại hàng triệu USD cho doanh nghiệp. Trong khi đó, một cảnh báo sai (False Positive) chỉ khiến kỹ sư vận hành mất khoảng 5-10 phút truy cập hệ thống để kiểm tra nhanh. Do đó, mục tiêu tối thượng là **thà bắt nhầm còn hơn bỏ sót**, tức là tối ưu Recall lên hàng đầu.

**Trade-off khi tune threshold:**
Precision và Recall luôn có mối quan hệ tỷ lệ nghịch (đánh đổi).
- Nếu ta hạ thấp Threshold (hoặc tăng tỷ lệ `contamination`) $\rightarrow$ Mô hình trở nên cực kỳ nhạy bén, **Recall tăng cao** nhưng đi kèm với việc **Precision giảm mạnh**, hệ thống bắn ra quá nhiều báo động giả dẫn đến hội chứng "Alert Fatigue" (kỹ sư bị quá tải và chai sạn với cảnh báo, dễ phớt lờ cảnh báo thật).
- Nếu ta nâng cao Threshold $\rightarrow$ Hệ thống chỉ cảnh báo khi chắc chắn 100%, **Precision tăng cao** nhưng **Recall sẽ giảm sâu**, hệ thống trở nên "vô cảm" và dễ dàng bỏ lọt các sự cố ngầm phức tạp. Người kỹ sư cần lựa chọn một điểm cân bằng (thường tối ưu qua F1-Score) sao cho đạt Recall tối đa trong ngưỡng False Alarm mà đội ngũ Ops có thể xử lý được.

---

✅ **Knowledge Check hoàn tất!** Sẵn sàng để ghi vào vở.
