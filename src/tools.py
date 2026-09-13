"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu ca kiểm định / lỗi QC
    {
        "name": "qc_query",
        "description": "Tra cứu thông tin ca kiểm định chất lượng, bao gồm mã sản phẩm, loại lỗi gán nhãu 2D/3D, mức độ lỗi, trạng thái xử lý và kết luận QC.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "Mã ca kiểm định cần tra cứu (ví dụ: 'QC-2026001')"
                }
            },
            "required": ["case_id"]
        }
    },
    
    # --------------------------------------------------------------------------
    # Tool 2: Tạo phiếu Rework
    # --------------------------------------------------------------------------
    {
        "name": "create_rework_ticket",
        "description": "Tạo phiếu Rework kiểm định cho một ca lỗi dựa trên thông tin kiểm định và mức độ lỗi.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "Mã ca kiểm định cần tạo phiếu Rework (ví dụ: 'QC-2026001')"
                },
                "reason": {
                    "type": "string",
                    "description": "Lý do tạo phiếu Rework (ví dụ: 'Lỗi 2D nghiêm trọng, cần kiểm tra lại')"
                },
                "priority": {
                    "type": "string",
                    "description": "Mức độ ưu tiên (ví dụ: 'Cao', 'Trung bình', 'Thấp')"
                }
            },
            "required": ["case_id", "reason", "priority"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {

    "QC2026001": {
        "product_id": "PROD-1001",
        "product_name": "Sản phẩm A",
        "label_type": "2D",
        "error_type": "Sai vị trí gán nhãn",
        "severity": "HIGH",
        "status": "OPEN",
        "qc_result": "FAIL",
        "description": (
            "Nhãn 2D bị lệch khỏi vị trí tiêu chuẩn, "
            "cần kiểm tra và gán nhãn lại."
        )
    },

    "QC2026002": {
        "product_id": "PROD-1002",
        "product_name": "Sản phẩm B",
        "label_type": "3D",
        "error_type": "Sai hình học",
        "severity": "MEDIUM",
        "status": "OPEN",
        "qc_result": "FAIL",
        "description": (
            "Dữ liệu gán nhãn 3D có sai lệch hình học "
            "so với tiêu chuẩn kiểm định."
        )
    },

    "QC2026003": {
        "product_id": "PROD-1003",
        "product_name": "Sản phẩm C",
        "label_type": "2D",
        "error_type": "Không có lỗi",
        "severity": "LOW",
        "status": "RESOLVED",
        "qc_result": "PASS",
        "description": (
            "Ca kiểm định đạt yêu cầu, không phát hiện lỗi "
            "cần Rework."
        )
    }
}


def execute_qc_query(case_id: str) -> str:
    """Thực thi tra cứu kiểm định theo mã ca kiểm định"""
    normalized_case_id = case_id.strip().upper()
    case = MOCK_DATABASE.get(normalized_case_id)
    if case:
        return json.dumps({
            "status": "SUCCESS",
            "case_id": normalized_case_id,
            "data": case
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu ca kiểm định có mã '{normalized_case_id}'"
        }, ensure_ascii=False)


def execute_create_rework_ticket(case_id: str, reason: str, priority: str) -> str:
    """Thực thi tạo phiếu Rework kiểm định"""
    normalized_case_id = case_id.strip().upper()
    normalized_priority = priority.strip().upper()
    # Kiểm tra ca kiểm định có tồn tại không
    case = MOCK_DATABASE.get(normalized_case_id)
    if not case:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu ca kiểm định có mã '{normalized_case_id}'"
        }, ensure_ascii=False)

    # Không tạo Rework cho ca đã đạt QC
    if case["qc_result"] == "PASS":
        return json.dumps(
            {
                "status": "REWORK_NOT_REQUIRED",
                "case_id": normalized_case_id,
                "message": (
                    "Ca kiểm định đạt yêu cầu, không cần tạo "
                    "phiếu Rework."
                )
            },
            ensure_ascii=False
        )

    # Kiểm tra priority
    valid_priorities = {"LOW", "MEDIUM", "HIGH"}

    if normalized_priority not in valid_priorities:
        return json.dumps(
            {
                "status": "INVALID_PRIORITY",
                "message": (
                    "Mức độ ưu tiên không hợp lệ. "
                    "Giá trị hợp lệ: LOW, MEDIUM, HIGH."
                )
            },
            ensure_ascii=False
        )

    # Mô phỏng tạo phiếu
    ticket_id = f"RW-{normalized_case_id}-01"

    return json.dumps(
        {
            "status": "SUCCESS",
            "ticket_id": ticket_id,
            "case_id": normalized_case_id,
            "product_id": case["product_id"],
            "priority": normalized_priority,
            "reason": reason,
            "message": (
                f"Tạo phiếu Rework {ticket_id} thành công "
                f"cho ca kiểm định {normalized_case_id}."
            )
        },
        ensure_ascii=False
    )


# Router gọi tool thực tế
TOOL_ROUTER = {
    "qc_query": execute_qc_query,
    "create_rework_ticket": execute_create_rework_ticket
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
