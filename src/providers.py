import os
import sys
import json
from typing import Dict, Any, List
from dotenv import load_dotenv


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


load_dotenv()


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling."""

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """
    Offline Mock Provider.

    Dùng để:
    - chạy test khi API hết quota
    - kiểm thử Tool Calling
    - kiểm thử ReAct multi-step
    - không phụ thuộc Internet/API key
    """

    def __init__(self):
        self.model_name = "Offline-Mock-QC-Assistant-2026"

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:
        return (
            "[Mock Chatbot Response]: "
            "Tôi là QC Assistant, hỗ trợ tra cứu ca kiểm định "
            "và tạo phiếu Rework cho các ca lỗi."
        )

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        prompt_lower = prompt.lower()

        # ==========================================================
        # 1. ĐÃ TẠO TICKET THÀNH CÔNG
        # ==========================================================
        # Nếu observation đã chứa ticket_id thì workflow đã hoàn thành.
        # Không được gọi create_rework_ticket lần nữa.
        if '"ticket_id"' in prompt_lower:

            return {
                "type": "text",
                "content": (
                    "Ca kiểm định đã được xác định là không đạt. "
                    "Phiếu Rework đã được tạo thành công."
                ),
                "thought": (
                    "Observation đã chứa ticket_id, "
                    "nghĩa là phiếu Rework đã được tạo. "
                    "Không cần gọi thêm Tool."
                )
            }

        # ==========================================================
        # 2. REACT MULTI-STEP:
        #    KIỂM TRA TRƯỚC, SAU ĐÓ MỚI REWORK
        # ==========================================================

        # Nếu prompt hiện tại có observation QC FAIL,
        # Agent được phép chuyển sang create_rework_ticket.
        has_qc_fail = (
            '"qc_result": "fail"' in prompt_lower
        )

        if has_qc_fail:

            case_id = self._extract_case_id(prompt)

            # Lấy reason dựa trên observation
            reason = self._extract_reason(prompt)

            # Nếu observation có severity HIGH
            if '"severity": "high"' in prompt_lower:
                priority = "HIGH"

            elif '"severity": "medium"' in prompt_lower:
                priority = "MEDIUM"

            else:
                priority = "LOW"

            return {
                "type": "tool_call",
                "tool_name": "create_rework_ticket",
                "arguments": {
                    "case_id": case_id,
                    "reason": reason,
                    "priority": priority
                },
                "thought": (
                    f"Ca kiểm định {case_id} có kết quả FAIL. "
                    f"Mức độ lỗi phù hợp với ưu tiên {priority}. "
                    "Tôi sẽ tạo phiếu Rework."
                )
            }

        # ==========================================================
        # 3. MULTI-STEP REQUEST
        #    "kiểm tra ... nếu FAIL thì tạo Rework"
        # ==========================================================

        is_conditional_rework = (
            "nếu" in prompt_lower
            and "rework" in prompt_lower
            and (
                "không đạt" in prompt_lower
                or "fail" in prompt_lower
            )
        )

        if is_conditional_rework:

            case_id = self._extract_case_id(prompt)

            return {
                "type": "tool_call",
                "tool_name": "qc_query",
                "arguments": {
                    "case_id": case_id
                },
                "thought": (
                    f"Cần kiểm tra kết quả QC của ca {case_id} "
                    "trước khi quyết định có tạo phiếu Rework hay không."
                )
            }

        # ==========================================================
        # 4. TẠO REWORK TRỰC TIẾP
        # ==========================================================

        if (
            "rework" in prompt_lower
            and (
                "tạo" in prompt_lower
                or "create" in prompt_lower
            )
        ):

            case_id = self._extract_case_id(prompt)

            priority = self._extract_priority(prompt)
            reason = self._extract_reason(prompt)

            return {
                "type": "tool_call",
                "tool_name": "create_rework_ticket",
                "arguments": {
                    "case_id": case_id,
                    "reason": reason,
                    "priority": priority
                },
                "thought": (
                    f"Người dùng yêu cầu tạo phiếu Rework "
                    f"cho ca {case_id} với mức ưu tiên {priority}."
                )
            }

        # ==========================================================
        # 5. TRA CỨU CA KIỂM ĐỊNH
        # ==========================================================

        if (
            "qc" in prompt_lower
            and (
                "tra cứu" in prompt_lower
                or "kiểm tra" in prompt_lower
                or "thông tin" in prompt_lower
                or "ca kiểm định" in prompt_lower
            )
        ):

            case_id = self._extract_case_id(prompt)

            return {
                "type": "tool_call",
                "tool_name": "qc_query",
                "arguments": {
                    "case_id": case_id
                },
                "thought": (
                    f"Người dùng yêu cầu tra cứu ca kiểm định "
                    f"{case_id}. Tôi sẽ gọi tool qc_query."
                )
            }

        # ==========================================================
        # 6. DIRECT ANSWER
        # ==========================================================

        return {
            "type": "text",
            "content": (
                "Quy trình kiểm định chất lượng (QC) là quá trình "
                "kiểm tra dữ liệu gán nhãn nhằm phát hiện và đánh giá "
                "các lỗi trước khi dữ liệu được sử dụng cho hệ thống AI. "
                "Với dữ liệu 2D, các lỗi phổ biến gồm sai vị trí, sai lớp, "
                "bỏ sót đối tượng hoặc gán nhãn thừa. "
                "Với dữ liệu 3D, có thể gặp lỗi về hình học, kích thước, "
                "vị trí hoặc góc xoay của đối tượng. "
                "Các ca FAIL có thể cần tạo phiếu Rework để xử lý."
            ),
            "thought": (
                "Câu hỏi mang tính kiến thức chung về QC, "
                "không cần gọi Tool."
            )
        }

    # ==============================================================
    # HELPER METHODS
    # ==============================================================

    @staticmethod
    def _extract_case_id(prompt: str) -> str:
        """
        Trích xuất Case ID từ prompt.

        Hỗ trợ:
        - QC2026001
        - QC-2026001
        - qc2026001
        - qc-2026001

        Chuẩn hóa về:
        QC2026001
        """

        import re

        match = re.search(
            r"\bQC[- ]?\d{7}\b",
            prompt,
            re.IGNORECASE
        )

        if match:
            return (
                match.group(0)
                .upper()
                .replace("-", "")
                .replace(" ", "")
            )

        # Fallback mặc định cho mock test
        return "QC2026001"

    @staticmethod
    def _extract_priority(prompt: str) -> str:
        """Trích xuất mức ưu tiên LOW/MEDIUM/HIGH."""

        prompt_upper = prompt.upper()

        if "HIGH" in prompt_upper:
            return "HIGH"

        if "MEDIUM" in prompt_upper:
            return "MEDIUM"

        if "LOW" in prompt_upper:
            return "LOW"

        # Nếu không nói rõ, mặc định MEDIUM
        return "MEDIUM"

    @staticmethod
    def _extract_reason(prompt: str) -> str:
        """Trích xuất lý do Rework đơn giản cho Mock."""

        prompt_lower = prompt.lower()

        if "sai vị trí gán nhãn 2d" in prompt_lower:
            return "Sai vị trí gán nhãn 2D"

        if "sai vị trí" in prompt_lower:
            return "Sai vị trí gán nhãn"

        if "sai hình học" in prompt_lower:
            return "Sai hình học"

        if "gán nhãn 2d" in prompt_lower:
            return "Lỗi gán nhãn 2D"

        if "gán nhãn 3d" in prompt_lower:
            return "Lỗi gán nhãn 3D"

        return "Lỗi kiểm định chất lượng cần Rework"


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider với Native Tool Calling."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "gemini-2.5-flash"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:

        if (
            not self.api_key
            or self.api_key == "your_gemini_api_key_here"
        ):
            return (
                "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY. "
                "Đang sử dụng chế độ Mock."
            )

        try:
            from google import genai

            client = genai.Client(
                api_key=self.api_key
            )

            contents = (
                f"{system_prompt}\n\n{prompt}"
                if system_prompt
                else prompt
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            return response.text or ""

        except Exception as e:
            return (
                f"[Gemini Exception]: {str(e)}"
            )

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        if (
            not self.api_key
            or self.api_key == "your_gemini_api_key_here"
        ):
            print(
                "ℹ️ [Gemini Provider]: "
                "Chưa tìm thấy GEMINI_API_KEY hợp lệ. "
                "Tự động chuyển sang Mock Offline."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=self.api_key
            )

            # ======================================================
            # Chuẩn hóa Tool Schema cho Gemini
            # ======================================================

            function_declarations = []

            for tool in tools_schema:

                if (
                    not tool.get("name")
                    or not tool.get("parameters")
                ):
                    continue

                function_declarations.append(
                    {
                        "name": tool["name"],
                        "description": tool.get(
                            "description",
                            ""
                        ),
                        "parameters": tool.get(
                            "parameters",
                            {}
                        )
                    }
                )

            config = types.GenerateContentConfig(
                system_instruction=(
                    system_prompt
                    if system_prompt
                    else None
                ),
                tools=(
                    [
                        {
                            "function_declarations":
                                function_declarations
                        }
                    ]
                    if function_declarations
                    else None
                ),
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # ======================================================
            # Gemini Tool Call
            # ======================================================

            if response.function_calls:

                call = response.function_calls[0]

                args = (
                    dict(call.args)
                    if hasattr(call, "args")
                    and call.args
                    else {}
                )

                # Chuẩn hóa case_id nếu Gemini trả
                # QC-2026001
                if "case_id" in args:
                    args["case_id"] = (
                        str(args["case_id"])
                        .strip()
                        .upper()
                        .replace("-", "")
                        .replace(" ", "")
                    )

                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": (
                        f"Gemini quyết định gọi công cụ "
                        f"'{call.name}' với tham số: "
                        f"{json.dumps(args, ensure_ascii=False)}"
                    )
                }

            # ======================================================
            # Gemini trả lời text
            # ======================================================

            return {
                "type": "text",
                "content": response.text or "",
                "thought": (
                    "Gemini phản hồi trực tiếp bằng văn bản "
                    "(không cần gọi công cụ)."
                )
            }

        except Exception as e:

            print(
                "⚠️ [Gemini API Warning]: "
                f"Không thể kết nối live API ({str(e)}). "
                "Tự động fallback về Mock."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider với Native Tool Calling."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )

        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "gpt-4o-mini"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:

        if (
            not self.api_key
            or self.api_key == "your_openai_api_key_here"
        ):
            return (
                "[OpenAI Error]: Chưa cấu hình "
                "OPENAI_API_KEY. Đang sử dụng chế độ Mock."
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key
            )

            messages = []

            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                )

            messages.append(
                {
                    "role": "user",
                    "content": prompt
                }
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )

            return (
                response.choices[0]
                .message
                .content
                or ""
            )

        except Exception as e:

            return (
                f"[OpenAI Exception]: {str(e)}"
            )

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        if (
            not self.api_key
            or self.api_key == "your_openai_api_key_here"
        ):
            print(
                "ℹ️ [OpenAI Provider]: "
                "Chưa tìm thấy OPENAI_API_KEY hợp lệ. "
                "Tự động chuyển sang Mock Offline."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key
            )

            # ======================================================
            # Chuẩn hóa Tool Schema cho OpenAI
            # ======================================================

            tools = []

            for tool in tools_schema:

                if not tool.get("name"):
                    continue

                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get(
                                "description",
                                ""
                            ),
                            "parameters": tool.get(
                                "parameters",
                                {}
                            )
                        }
                    }
                )

            messages = []

            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                )

            messages.append(
                {
                    "role": "user",
                    "content": prompt
                }
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice=(
                    "auto"
                    if tools
                    else None
                )
            )

            msg = response.choices[0].message

            # ======================================================
            # OpenAI Tool Call
            # ======================================================

            if msg.tool_calls:

                call = msg.tool_calls[0]

                args = (
                    json.loads(
                        call.function.arguments
                    )
                    if call.function.arguments
                    else {}
                )

                if "case_id" in args:
                    args["case_id"] = (
                        str(args["case_id"])
                        .strip()
                        .upper()
                        .replace("-", "")
                        .replace(" ", "")
                    )

                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": (
                        f"OpenAI quyết định gọi công cụ "
                        f"'{call.function.name}' với tham số: "
                        f"{json.dumps(args, ensure_ascii=False)}"
                    )
                }

            # ======================================================
            # OpenAI Text Response
            # ======================================================

            return {
                "type": "text",
                "content": msg.content or "",
                "thought": (
                    "OpenAI phản hồi trực tiếp bằng văn bản "
                    "(không cần gọi công cụ)."
                )
            }

        except Exception as e:

            print(
                "⚠️ [OpenAI API Warning]: "
                f"Không thể kết nối live API ({str(e)}). "
                "Tự động fallback về Mock."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function khởi tạo Provider
    theo biến môi trường LLM_PROVIDER.
    """

    provider_type = (
        os.getenv(
            "LLM_PROVIDER",
            "gemini"
        )
        .lower()
    )

    if provider_type == "gemini":

        key = os.getenv(
            "GEMINI_API_KEY"
        )

        if (
            key
            and key != "your_gemini_api_key_here"
        ):
            return GeminiProvider()

        return MockOfflineProvider()

    elif provider_type == "openai":

        key = os.getenv(
            "OPENAI_API_KEY"
        )

        if (
            key
            and key != "your_openai_api_key_here"
        ):
            return OpenAIProvider()

        return MockOfflineProvider()

    elif provider_type == "mock":

        return MockOfflineProvider()

    else:

        return MockOfflineProvider()