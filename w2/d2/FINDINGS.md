# RCA FINDINGS

## Cluster chinh

Cluster lon nhat `c-000-000` co root cause duoc xep hang la **`payment-svc`**, voi graph score `1.0` va confidence tong hop **0.86**. Dich vu nay phat alert som nhat trong cum, nam o cuoi chuoi goi dang loi va co nhieu dich vu upstream phu thuoc. Retrieval tim thay incident gan nhat la **`INC-2025-11-08`**, dung voi ghi chu ground truth trong dataset. Classifier kNN top-1 gan class **`connection_pool_exhaustion`** va de xuat rollback payment-svc, tang connection pool, cung them pool monitoring.

## Confidence va auto-remediation

Toi chua dam auto-rollback chi dua tren confidence 0.86. Payment path anh huong truc tiep den doanh thu, nen nguong hop ly la **0.90**. Ngoai threshold, top-1 can on dinh qua nhieu time window va historical match can cung root-cause service. Output hien tai nen duoc dung de uu tien dieu tra hoac tao remediation proposal cho SRE duyet.

## Case chua chac chan va bonus

Case `recommender-svc` co confidence **0.61** va duoc gan class `batch_overlap` tu `INC-2026-03-07`. Ket qua hop ly voi note concurrent batch retrain, nhung chi co mot alert nen van chua du de auto-remediate. Toi **khong chon bonus path**. Retrieval-only da du cho bai vi GeekShop co service map tuong doi on dinh, lich su su co lap lai va pipeline khong can API key. Trade-off la he thong kho khai quat khi gap failure class hoan toan moi; khi do graph-only fallback phai yeu cau dieu tra thu cong.
