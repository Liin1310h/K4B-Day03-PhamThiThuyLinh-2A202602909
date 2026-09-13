import json
import os
import sys
import time

from dotenv import load_dotenv


# ==========================================================
# PATH & ENCODING
# ==========================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    CURRENT_DIR
)

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8"
        )
    except Exception:
        pass


# ==========================================================
# IMPORT MODULES
# ==========================================================

from mcp_server import MCPQCServer

from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)

from providers import get_llm_provider


# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

load_dotenv()


# ==========================================================
# LOAD TEST CASES
# ==========================================================

def load_test_cases():
    """
    Tải Test Cases từ:

        config/test_cases.json

    Nếu file test_cases.json chưa tồn tại,
    sử dụng:

        config/test_cases.example.json
    """

    config_dir = os.path.join(
        PROJECT_ROOT,
        "config"
    )

    config_path = os.path.join(
        config_dir,
        "test_cases.json"
    )

    example_path = os.path.join(
        config_dir,
        "test_cases.example.json"
    )

    if not os.path.exists(config_path):

        if os.path.exists(example_path):

            print(
                "⚠️ [CONFIG NOTICE]: "
                "Chưa tìm thấy 'config/test_cases.json'."
            )

            print(
                "👉 Đang sử dụng "
                "'config/test_cases.example.json'."
            )

            print(
                "👉 Hãy tạo test_cases.json "
                "và viết Test Cases theo đề tài QC Assistant.\n"
            )

            config_path = example_path

        else:

            raise FileNotFoundError(
                "Không tìm thấy "
                "'config/test_cases.json' "
                "hoặc "
                "'config/test_cases.example.json'."
            )

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ==========================================================
# SAVE WATERFALL TRACE
# ==========================================================

def save_waterfall_trace(
    trace_data: list
):
    """
    Lưu Waterfall Trace vào:

        docs/trace_waterfall.json
    """

    docs_dir = os.path.join(
        PROJECT_ROOT,
        "docs"
    )

    os.makedirs(
        docs_dir,
        exist_ok=True
    )

    trace_path = os.path.join(
        docs_dir,
        "trace_waterfall.json"
    )

    with open(
        trace_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            trace_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"📊 [OBSERVABILITY]: "
        f"Đã lưu {len(trace_data)} sự kiện "
        f"Waterfall Trace tại:"
    )

    print(
        f"   {trace_path}"
    )


# ==========================================================
# CHATBOT BASELINE
# ==========================================================

def run_baseline_chatbot(
    user_query: str,
    provider
):
    """
    Chạy Chatbot Baseline - Cấp 2.

    Chatbot chỉ sử dụng LLM,
    không có Tool và không kết nối MCP Server.
    """

    print(
        "\n💬 [CHATBOT BASELINE]"
    )

    print(
        f"👤 Câu hỏi: {user_query}"
    )

    response = provider.generate(
        user_query,
        system_prompt=CHATBOT_BASELINE_PROMPT
    )

    print(
        "🤖 Chatbot phản hồi:"
    )

    print(
        response
    )

    return response


# ==========================================================
# BUILD REACT CONTEXT
# ==========================================================

def build_agent_input(
    user_query: str,
    observations: list
):
    """
    Xây dựng input gửi cho Agent.

    Nếu Agent chưa gọi Tool:
        Chỉ gửi câu hỏi của User.

    Nếu Agent đã gọi Tool:
        Gửi lại câu hỏi + các Observation
        để Agent suy luận bước tiếp theo.
    """

    if not observations:

        return user_query

    observation_blocks = []

    for item in observations:

        tool_name = item.get(
            "tool_name",
            ""
        )

        observation = item.get(
            "observation",
            {}
        )

        observation_blocks.append(
            (
                f"Tool: {tool_name}\n"
                f"Observation:\n"
                f"{json.dumps(observation, ensure_ascii=False, indent=2)}"
            )
        )

    observations_text = "\n\n".join(
        observation_blocks
    )

    return (
        "Yêu cầu ban đầu của người dùng:\n"
        f"{user_query}\n\n"
        "Các kết quả Tool đã nhận được:\n"
        f"{observations_text}\n\n"
        "Hãy tiếp tục suy luận dựa trên các Observation "
        "trên.\n"
        "Nếu cần thực hiện thêm hành động, hãy gọi Tool "
        "phù hợp.\n"
        "Nếu đã đủ thông tin để trả lời người dùng, "
        "hãy trả về Final Answer."
    )


# ==========================================================
# FORMAT QC QUERY RESULT
# ==========================================================

def format_qc_query_result(
    obs_data: dict
):
    """
    Chuyển kết quả qc_query thành câu trả lời
    dễ hiểu cho người dùng.
    """

    status = obs_data.get(
        "status"
    )

    if status == "SUCCESS":

        data = obs_data.get(
            "data",
            {}
        )

        return (
            f"Ca kiểm định {obs_data.get('case_id', '')} "
            f"của {data.get('product_name', '')} "
            f"({data.get('product_id', '')}) có thông tin: "
            f"loại nhãn {data.get('label_type', '')}, "
            f"lỗi '{data.get('error_type', '')}', "
            f"mức độ {data.get('severity', '')}, "
            f"trạng thái {data.get('status', '')}, "
            f"kết luận QC {data.get('qc_result', '')}. "
            f"Mô tả: {data.get('description', '')}"
        )

    if status == "NOT_FOUND":

        return obs_data.get(
            "message",
            "Không tìm thấy ca kiểm định."
        )

    return (
        "Không thể xử lý kết quả tra cứu QC: "
        + json.dumps(
            obs_data,
            ensure_ascii=False
        )
    )


# ==========================================================
# FORMAT REWORK RESULT
# ==========================================================

def format_rework_result(
    obs_data: dict
):
    """
    Chuyển kết quả create_rework_ticket
    thành câu trả lời dễ hiểu.
    """

    status = obs_data.get(
        "status"
    )

    if status == "SUCCESS":

        return (
            f"Tạo phiếu Rework "
            f"{obs_data.get('ticket_id', '')} "
            f"thành công cho ca "
            f"{obs_data.get('case_id', '')}. "
            f"Sản phẩm: "
            f"{obs_data.get('product_id', '')}. "
            f"Mức ưu tiên: "
            f"{obs_data.get('priority', '')}. "
            f"Lý do: "
            f"{obs_data.get('reason', '')}."
        )

    if status == "REWORK_NOT_REQUIRED":

        return obs_data.get(
            "message",
            "Ca kiểm định đạt yêu cầu, không cần tạo phiếu Rework."
        )

    if status == "NOT_FOUND":

        return obs_data.get(
            "message",
            "Không tìm thấy ca kiểm định."
        )

    if status == "INVALID_PRIORITY":

        return obs_data.get(
            "message",
            "Mức độ ưu tiên không hợp lệ."
        )

    return (
        "Không thể tạo phiếu Rework: "
        + json.dumps(
            obs_data,
            ensure_ascii=False
        )
    )


# ==========================================================
# FORMAT TOOL RESULT
# ==========================================================

def format_tool_result(
    tool_name: str,
    obs_data: dict
):
    """
    Format kết quả theo từng loại Tool.
    """

    if tool_name == "qc_query":

        return format_qc_query_result(
            obs_data
        )

    if tool_name == "create_rework_ticket":

        return format_rework_result(
            obs_data
        )

    return (
        "Phản hồi từ Tool "
        f"'{tool_name}': "
        + json.dumps(
            obs_data,
            ensure_ascii=False
        )
    )


# ==========================================================
# REACT AGENT
# ==========================================================

def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPQCServer
):
    """
    Thực thi ReAct Agent.

    Flow:

        User Query
             ↓
        Thought
             ↓
        Tool Call
             ↓
        MCP Server
             ↓
        Observation
             ↓
        Thought
             ↓
        Tool Call tiếp theo
             ↓
        ...
             ↓
        Final Answer
    """

    print(
        "\n🤖 [REACT AGENT]"
    )

    print(
        f"👤 Câu hỏi: {user_query}"
    )

    step = 0

    trace_logs = []

    observations = []

    tools_list = mcp_server.list_tools()

    # ------------------------------------------------------
    # REACT LOOP
    # ------------------------------------------------------

    while step < MAX_ITERATIONS:

        step += 1

        step_start_time = time.time()

        print(
            "\n--------------------------------------------------"
        )

        print(
            f"🔄 ReAct Loop - Step "
            f"{step}/{MAX_ITERATIONS}"
        )

        print(
            "--------------------------------------------------"
        )

        # --------------------------------------------------
        # BUILD AGENT INPUT
        # --------------------------------------------------

        agent_input = build_agent_input(
            user_query,
            observations
        )

        # --------------------------------------------------
        # CALL LLM
        # --------------------------------------------------

        try:

            llm_response = provider.generate_with_tools(
                agent_input,
                tools_list,
                system_prompt=REACT_AGENT_SYSTEM_PROMPT
            )

        except Exception as error:

            latency_ms = round(
                (time.time() - step_start_time) * 1000,
                2
            )

            print(
                f"❌ [LLM ERROR]: {error}"
            )

            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "ERROR",
                    "error": str(error),
                    "latency_ms": latency_ms
                }
            )

            break

        latency_ms = round(
            (time.time() - step_start_time) * 1000,
            2
        )

        # --------------------------------------------------
        # READ THOUGHT
        # --------------------------------------------------

        thought = llm_response.get(
            "thought",
            "Agent đang suy luận..."
        )

        print(
            f"🧠 [Thought]: {thought}"
        )

        # ==================================================
        # CASE 1: FINAL TEXT
        # ==================================================

        if llm_response.get("type") == "text":

            final_content = llm_response.get(
                "content",
                ""
            )

            print(
                f"🏁 [Final Answer]: "
                f"{final_content}"
            )

            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": thought,
                    "output": final_content,
                    "latency_ms": latency_ms
                }
            )

            break

        # ==================================================
        # CASE 2: TOOL CALL
        # ==================================================

        if llm_response.get("type") == "tool_call":

            tool_name = llm_response.get(
                "tool_name"
            )

            arguments = llm_response.get(
                "arguments",
                {}
            )

            print(
                f"🛠️ [Action Proposed]: "
                f"{tool_name}"
            )

            print(
                f"   Arguments: {arguments}"
            )

            # --------------------------------------------------
            # VALIDATE TOOL NAME
            # --------------------------------------------------

            available_tools = {
                tool.get("name")
                for tool in tools_list
            }

            if tool_name not in available_tools:

                error_message = (
                    f"Agent yêu cầu Tool "
                    f"'{tool_name}' nhưng Tool này "
                    f"không tồn tại trên MCP Server."
                )

                print(
                    f"❌ {error_message}"
                )

                trace_logs.append(
                    {
                        "step": step,
                        "query": user_query,
                        "action_type": "TOOL_ERROR",
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "error": error_message,
                        "latency_ms": latency_ms
                    }
                )

                break

            # --------------------------------------------------
            # CALL MCP TOOL
            # --------------------------------------------------

            try:

                mcp_result = mcp_server.call_tool(
                    tool_name,
                    arguments
                )

            except Exception as error:

                print(
                    f"❌ [MCP ERROR]: {error}"
                )

                trace_logs.append(
                    {
                        "step": step,
                        "query": user_query,
                        "action_type": "MCP_ERROR",
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "error": str(error),
                        "latency_ms": latency_ms
                    }
                )

                break

            # --------------------------------------------------
            # GET OBSERVATION
            # --------------------------------------------------

            obs_data = mcp_result.get(
                "result",
                {}
            )

            print(
                "👁️ [Observation từ MCP Server]:"
            )

            print(
                json.dumps(
                    obs_data,
                    ensure_ascii=False,
                    indent=2
                )
            )

            # --------------------------------------------------
            # EMPTY OBSERVATION
            # --------------------------------------------------

            if not obs_data:

                final_answer = (
                    "MCP Server không trả về dữ liệu "
                    "cho yêu cầu này."
                )

                print(
                    f"🏁 [Final Answer]: "
                    f"{final_answer}"
                )

                trace_logs.append(
                    {
                        "step": step,
                        "query": user_query,
                        "action_type": "TOOL_EXECUTION",
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "observation": {},
                        "latency_ms": latency_ms
                    }
                )

                trace_logs.append(
                    {
                        "step": step + 1,
                        "query": user_query,
                        "action_type": "FINAL_ANSWER",
                        "thought": (
                            "MCP Server không trả về dữ liệu."
                        ),
                        "output": final_answer,
                        "latency_ms": 10.0
                    }
                )

                break

            # --------------------------------------------------
            # SAVE OBSERVATION
            # --------------------------------------------------

            observation_record = {
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data
            }

            observations.append(
                observation_record
            )

            # --------------------------------------------------
            # TRACE TOOL EXECUTION
            # --------------------------------------------------

            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": obs_data,
                    "latency_ms": latency_ms
                }
            )

            # --------------------------------------------------
            # CHECK RESULT
            # --------------------------------------------------

            status = obs_data.get(
                "status"
            )

            # Tool thất bại -> kết thúc
            if status in [
                "NOT_FOUND",
                "UNKNOWN_TOOL",
                "EXECUTION_ERROR",
                "INVALID_PRIORITY"
            ]:

                final_answer = format_tool_result(
                    tool_name,
                    obs_data
                )

                print(
                    f"🏁 [Final Answer]: "
                    f"{final_answer}"
                )

                trace_logs.append(
                    {
                        "step": step + 1,
                        "query": user_query,
                        "action_type": "FINAL_ANSWER",
                        "thought": (
                            "Tool trả về lỗi hoặc "
                            "không tìm thấy dữ liệu."
                        ),
                        "output": final_answer,
                        "latency_ms": 10.0
                    }
                )

                break

            # --------------------------------------------------
            # PASS -> không cần Rework
            # --------------------------------------------------

            if (
                tool_name == "qc_query"
                and status == "SUCCESS"
            ):

                data = obs_data.get(
                    "data",
                    {}
                )

                qc_result = data.get(
                    "qc_result"
                )

                if qc_result == "PASS":

                    final_answer = format_tool_result(
                        tool_name,
                        obs_data
                    )

                    print(
                        "🧠 [Decision]: "
                        "Ca QC đạt yêu cầu, không cần Rework."
                    )

                    print(
                        f"🏁 [Final Answer]: "
                        f"{final_answer}"
                    )

                    trace_logs.append(
                        {
                            "step": step + 1,
                            "query": user_query,
                            "action_type": "FINAL_ANSWER",
                            "thought": (
                                "Kết quả QC là PASS nên "
                                "không cần tạo phiếu Rework."
                            ),
                            "output": final_answer,
                            "latency_ms": 10.0
                        }
                    )

                    break

            # --------------------------------------------------
            # REWORK NOT REQUIRED
            # --------------------------------------------------

            if (
                status == "REWORK_NOT_REQUIRED"
            ):

                final_answer = format_tool_result(
                    tool_name,
                    obs_data
                )

                print(
                    f"🏁 [Final Answer]: "
                    f"{final_answer}"
                )

                trace_logs.append(
                    {
                        "step": step + 1,
                        "query": user_query,
                        "action_type": "FINAL_ANSWER",
                        "thought": (
                            "Ca kiểm định đạt yêu cầu "
                            "nên không cần Rework."
                        ),
                        "output": final_answer,
                        "latency_ms": 10.0
                    }
                )

                break

            # --------------------------------------------------
            # TOOL SUCCESS
            #
            # Không kết thúc ngay.
            #
            # Agent sẽ nhận Observation ở vòng tiếp theo
            # và tự quyết định có gọi Tool tiếp hay không.
            # --------------------------------------------------

            print(
                "🧠 [Agent]: "
                "Đã nhận Observation. "
                "Tiếp tục suy luận bước tiếp theo..."
            )

            continue

        # ==================================================
        # UNKNOWN RESPONSE TYPE
        # ==================================================

        else:

            error_message = (
                "LLM trả về response không hợp lệ: "
                + json.dumps(
                    llm_response,
                    ensure_ascii=False
                )
            )

            print(
                f"❌ {error_message}"
            )

            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "INVALID_LLM_RESPONSE",
                    "response": llm_response,
                    "latency_ms": latency_ms
                }
            )

            break

    # ======================================================
    # MAX ITERATIONS
    # ======================================================

    if step >= MAX_ITERATIONS:

        print(
            "\n⚠️ [MAX ITERATIONS]: "
            "Agent đã đạt giới hạn số vòng lặp."
        )

        trace_logs.append(
            {
                "step": step + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": (
                    "Agent đã đạt giới hạn số bước "
                    "suy luận."
                ),
                "output": (
                    "Agent đã đạt giới hạn số bước "
                    "suy luận cho yêu cầu này."
                ),
                "latency_ms": 10.0
            }
        )

    return trace_logs


# ==========================================================
# INTERACTIVE MODE
# ==========================================================

def run_interactive_mode(
    provider,
    mcp_server
):
    """
    Chạy QC Assistant ở chế độ chat trực tiếp.
    """

    print(
        "🎮 [INTERACTIVE MODE]"
    )

    print(
        "Trò chuyện trực tiếp với QC Assistant."
    )

    print(
        "\n💡 Ví dụ câu hỏi:"
    )

    print(
        "1. Hãy tra cứu ca kiểm định QC2026001"
    )

    print(
        "2. Hãy tra cứu ca QC2026002"
    )

    print(
        "3. Kiểm tra ca QC2026001 và nếu ca này "
        "không đạt thì tạo phiếu Rework với "
        "mức ưu tiên phù hợp."
    )

    print(
        "4. Tra cứu ca QC9999999"
    )

    print(
        "\nGõ 'exit' hoặc 'quit' để kết thúc.\n"
    )

    while True:

        try:

            user_input = input(
                "👤 Người dùng: "
            ).strip()

            if not user_input:

                continue

            if user_input.lower() in [
                "exit",
                "quit"
            ]:

                print(
                    "👋 Tạm biệt!"
                )

                break

            logs = run_react_agent(
                user_input,
                provider,
                mcp_server
            )

            save_waterfall_trace(
                logs
            )

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                "\n👋 Đã thoát phiên tương tác."
            )

            break


# ==========================================================
# TEST SUITE MODE
# ==========================================================

def run_test_suite(
    tests,
    provider,
    mcp_server
):
    """
    Chạy toàn bộ Test Cases.
    """

    print(
        "🚀 [TEST SUITE MODE]"
    )

    print(
        f"Kiểm tra {len(tests)} Test Cases."
    )

    completed_count = 0

    todo_count = 0

    all_traces = []

    for tc in tests:

        print(
            "\n=================================================="
        )

        print(
            f"🧪 [{tc.get('id', 'UNKNOWN')}] "
            f"Loại test: {tc.get('type', '')}"
        )

        print(
            f"📊 Độ phức tạp: "
            f"{tc.get('complexity', '')}"
        )

        print(
            f"📌 Kỳ vọng: "
            f"{tc.get('expected_behavior', '')}"
        )

        question = tc.get(
            "question",
            ""
        )

        if (
            not question
            or question.strip().startswith("TODO")
        ):

            print(
                "⏸️ [TODO]: "
                "Test Case chưa có câu hỏi thực tế."
            )

            print(
                f"   {question}"
            )

            todo_count += 1

            continue

        logs = run_react_agent(
            question,
            provider,
            mcp_server
        )

        all_traces.extend(
            logs
        )

        completed_count += 1

    print(
        "\n=================================================="
    )

    print(
        f"📊 [KẾT QUẢ TEST SUITE]"
    )

    print(
        f"Đã thực thi: "
        f"{completed_count}/{len(tests)}"
    )

    print(
        f"Đang TODO: "
        f"{todo_count}"
    )

    if all_traces:

        save_waterfall_trace(
            all_traces
        )


# ==========================================================
# DEFAULT DEMO MODE
# ==========================================================

def run_default_demo(
    tests,
    provider,
    mcp_server
):
    """
    Chạy một Test Case mẫu khi không truyền argument.
    """

    print(
        "ℹ️ HƯỚNG DẪN SỬ DỤNG:"
    )

    print(
        "  1. Chat trực tiếp:"
    )

    print(
        "     python src/app.py --interactive"
    )

    print(
        "  2. Chạy toàn bộ Test Cases:"
    )

    print(
        "     python src/app.py --all"
    )

    print(
        "\n--------------------------------------------------"
    )

    if len(tests) > 1:

        sample_query = tests[1].get(
            "question",
            ""
        )

    elif tests:

        sample_query = tests[0].get(
            "question",
            ""
        )

    else:

        sample_query = (
            "Hãy tra cứu ca kiểm định QC2026001."
        )

    if (
        not sample_query
        or sample_query.strip().startswith("TODO")
    ):

        sample_query = (
            "Hãy tra cứu ca kiểm định QC2026001."
        )

    print(
        "🏁 DEMO REACT AGENT"
    )

    print(
        f"👤 Câu hỏi: {sample_query}"
    )

    logs = run_react_agent(
        sample_query,
        provider,
        mcp_server
    )

    save_waterfall_trace(
        logs
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    print(
        "=========================================================="
    )

    print(
        "🚀 QC ASSISTANT - DAY 03 LAB"
    )

    print(
        "   CHATBOT BASELINE VS REACT AGENT"
    )

    print(
        "=========================================================="
    )

    # ------------------------------------------------------
    # INIT PROVIDER
    # ------------------------------------------------------

    try:

        provider = get_llm_provider()

    except Exception as error:

        print(
            f"❌ Không thể khởi tạo LLM Provider: "
            f"{error}"
        )

        return

    # ------------------------------------------------------
    # INIT MCP SERVER
    # ------------------------------------------------------

    try:

        mcp_server = MCPQCServer()

    except Exception as error:

        print(
            f"❌ Không thể khởi tạo MCP QC Server: "
            f"{error}"
        )

        return

    print(
        f"🔌 LLM Provider: "
        f"{provider.__class__.__name__}"
    )

    print(
        f"🌐 MCP Server: "
        f"{mcp_server.server_name}"
    )

    print(
        f"🧰 Tools: "
        f"{len(mcp_server.list_tools())}"
    )

    for tool in mcp_server.list_tools():

        print(
            f"   - {tool.get('name')}"
        )

    print()

    # ------------------------------------------------------
    # LOAD TEST CASES
    # ------------------------------------------------------

    try:

        tests = load_test_cases()

    except Exception as error:

        print(
            f"❌ Không thể load Test Cases: "
            f"{error}"
        )

        return

    print(
        f"✅ Đã tải thành công "
        f"{len(tests)} Test Cases."
    )

    print()

    # ------------------------------------------------------
    # MODE: INTERACTIVE
    # ------------------------------------------------------

    if "--interactive" in sys.argv:

        run_interactive_mode(
            provider,
            mcp_server
        )

        return

    # ------------------------------------------------------
    # MODE: ALL
    # ------------------------------------------------------

    if "--all" in sys.argv:

        run_test_suite(
            tests,
            provider,
            mcp_server
        )

        return

    # ------------------------------------------------------
    # DEFAULT
    # ------------------------------------------------------

    run_default_demo(
        tests,
        provider,
        mcp_server
    )


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()
