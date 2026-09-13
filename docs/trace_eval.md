# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Phạm Thị Thùy Linh
> **Mã Sinh Viên / Mã Học viên:** 2A202602909  
> **Chủ đề Lựa chọn:** Trợ lý Kiểm định Chất lượng

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá           | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm                                                                                                                                                                                                                                                                                                    |
| :-------------------------- | :------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Multi-step Reasoning** |     4 / 5      | Hệ thống cần thực hiện nhiều bước liên tiếp: xác định mã sản phẩm/ca kiểm định → tra cứu lịch sử lỗi gán nhãn 2D/3D → phân tích loại lỗi và mức độ lỗi → đối chiếu tiêu chuẩn kiểm định → quyết định hướng xử lý → tạo phiếu Rework nếu cần.                                                                                           |
| **2. Tool Interaction**     |     5 / 5      | Bài toán cần tương tác với nhiều nguồn dữ liệu bên ngoài như cơ sở dữ liệu QC, lịch sử kiểm định, danh sách lỗi 2D/3D và hệ thống tạo phiếu Rework. Việc tra cứu và tạo phiếu đều cần Tool/API thay vì chỉ trả lời từ System Prompt.                                                                                                   |
| **3. Dynamic Decision**     |     5 / 5      | Bước tiếp theo phụ thuộc trực tiếp vào kết quả của bước trước. Ví dụ: nếu tra cứu cho thấy sản phẩm có lỗi nghiêm trọng thì Agent có thể tạo phiếu Rework; nếu lỗi đã được xử lý hoặc không đủ điều kiện Rework thì Agent không tạo phiếu và thông báo lý do. Nếu thiếu thông tin, Agent có thể tiếp tục tra cứu trước khi quyết định. |
| **4. Long Horizon Goal**    |     4 / 5      | Một yêu cầu hoàn chỉnh có thể kéo dài qua nhiều bước: tiếp nhận yêu cầu → xác định đối tượng kiểm định → tra cứu lỗi → đánh giá → lựa chọn phương án xử lý → tạo phiếu Rework → xác nhận kết quả. Tuy nhiên, các yêu cầu đơn giản như chỉ tra cứu một ca lỗi có thể hoàn thành trong ít bước.                                          |
| **TỔNG ĐIỂM AGENTIC FIT**   |  **18 / 20**   | _Nếu tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System._                                                                                                                                                                                                                                                               |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

>

```
[{

    "step": 1,
    "query": "Hãy kiểm tra ca QC2026001. Nếu ca này không đạt kiểm định thì tạo phiếu Rework với mức ưu tiên phù hợp dựa trên mức độ lỗi.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "qc_query",
    "arguments": {
      "case_id": "QC2026001"
    },
    "observation": {
      "status": "SUCCESS",
      "case_id": "QC2026001",
      "data": {
        "error_type": "Sai vị trí gán nhãn",
        "severity": "HIGH",
        "qc_result": "FAIL"
      }
    },
    "latency_ms": 980.81

  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "create_rework_ticket",
    "arguments": {
    "case_id": "QC2026001",
    "reason": "Sai vị trí gán nhãn",
    "priority": "HIGH"
    },
    "observation": {
    "status": "SUCCESS",
    "ticket_id": "RW-QC2026001-01"
    },
    "latency_ms": 1012.06
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 6 lượt.
- **Kết quả đẩy Repo nộp bài:** [X] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
