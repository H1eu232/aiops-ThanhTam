# W2-D2 SUBMIT - EOD CHECKPOINT

## Cau 1: Confidence va nguong auto-rollback

Trong cluster lon nhat `c-000-000`, top-1 la `payment-svc` voi confidence **0.86**. Neu phai set threshold cho auto-rollback khong can SRE xac nhan, toi chon **0.90**. Confidence hien tai chua vuot nguong nen pipeline chi tao de xuat remediation. Payment la critical path anh huong doanh thu; false rollback co blast radius lon. Vi vay, ngoai threshold, top-1 can on dinh qua nhieu time window va historical match phai cung root-cause service. Top historical match thuc te la `INC-2025-11-08`.

## Cau 2: Classifier variant va trade-off

Toi chon **Variant A: rule-based graph scorer + keyword kNN retrieval**. Pipeline thuc te chay offline, lay class va actions tu top-1 incident tuong tu, dong thoi co graph-only fallback khi retrieval rong. Uu diem la deterministic, de audit, khong can API key va chi phi thap. So voi Variant B/C dung LLM, giai phap nay it linh hoat voi loi moi hoac mo ta khac tu vung, nhung tranh hallucination va output JSON luon on dinh.

## Cau 3: Industry landscape

Pipeline gan **Dynatrace Davis** nhat vi service topology la tin hieu chinh de xep hang root cause, sau do lich su incident bo sung class va remediation. Cach nay hop ly voi GeekShop do alert volume cao va service map tuong doi on dinh. Tuy nhien, static graph khong nen duoc xem la source of truth tuyet doi. Khi he thong thay doi nhanh, nen bo sung distributed tracing hoac runtime dependency map de tranh graph loi thoi va cai thien RCA cho cac luong bat dong bo.
