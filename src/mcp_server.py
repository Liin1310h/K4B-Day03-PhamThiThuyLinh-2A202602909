"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPQCServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "qc-assistant-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        # --------------------------------------------------------------------------
        # 1. Gọi hàm dispatch_tool_call(tool_name, arguments) để lấy chuỗi JSON kết quả từ Tool Router.
        # 2. Chuyển đổi chuỗi JSON kết quả thành Python Dictionary (dùng json.loads).
        # 3. Đóng gói phản hồi và trả về Dict theo đúng chuẩn giao thức MCP JSON-RPC 2.0:
        #    - Các trường bắt buộc: "jsonrpc": "2.0", "server": self.server_name, "tool": tool_name, "result": content
        # --------------------------------------------------------------------------
        raw_result = dispatch_tool_call(tool_name, arguments)
        try:
            content = json.loads(raw_result)

        except json.JSONDecodeError as e:
            content = {
                "status": "INVALID_TOOL_RESPONSE",
                "error": str(e),
                "raw_result": raw_result
            }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }

if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (qc-assistant-mcp-server)")
    print("==========================================================")
    
    server = MCPQCServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # --------------------------------------------------------------------------
    # Kiểm tra Tool 1: qc_query
    # --------------------------------------------------------------------------

    qc_tool = next(
        (t for t in tools if t.get("name") == "qc_query"),
        None
    )

    if qc_tool and qc_tool.get("parameters", {}).get("properties"):
        print(
            "[TOOL 1]: Tool 'qc_query' đã có schema đầy đủ."
        )
    else:
        print(
            "[TOOL 1]: Tool 'qc_query' chưa được định nghĩa đầy đủ."
        )

    # --------------------------------------------------------------------------
    # Kiểm tra Tool 2: create_rework_ticket
    # --------------------------------------------------------------------------

    rework_tool = next(
        (
            t for t in tools
            if t.get("name") == "create_rework_ticket"
        ),
        None
    )

    if rework_tool and rework_tool.get("parameters", {}).get("properties"):
        print(
            "[TOOL 2]: Tool 'create_rework_ticket' đã có schema đầy đủ."
        )
    else:
        print(
            "[TOOL 2]: Tool 'create_rework_ticket' "
            "chưa được định nghĩa đầy đủ."
        )

    # --------------------------------------------------------------------------
    # Kiểm tra TODO 2.1: call_tool()
    # --------------------------------------------------------------------------

    test_result = server.call_tool(
        "qc_query",
        {
            "case_id": "QC2026001"
        }
    )

    if not test_result:

        print(
            "[TODO 2.1]: Hàm call_tool() đang trả về rỗng. "
            "Hãy kiểm tra lại implementation."
        )

    else:

        print(
            "[TODO 2.1]: Test dispatch Tool 'qc_query' thành công:"
        )

        print(
            "Phản hồi JSON-RPC:"
        )

        print(
            json.dumps(
                test_result,
                ensure_ascii=False,
                indent=2
            )
        )

    # --------------------------------------------------------------------------
    # Kiểm tra Tool 2: create_rework_ticket
    # --------------------------------------------------------------------------

    rework_result = server.call_tool(
        "create_rework_ticket",
        {
            "case_id": "QC2026001",
            "reason": "Sai vị trí gán nhãn 2D",
            "priority": "HIGH"
        }
    )

    print()
    print(
        "Test Tool 'create_rework_ticket':"
    )

    print(
        json.dumps(
            rework_result,
            ensure_ascii=False,
            indent=2
        )
    )