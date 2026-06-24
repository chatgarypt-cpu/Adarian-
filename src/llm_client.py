"""
LLM 统一调用封装
---
所有 LLM 调用必须通过此模块，禁止在业务代码中直接 import openai。
Why: 统一接口便于切换 provider，统一错误处理和重试机制。
"""

import json
import inspect
import re
import os
import sys
import time
import httpx
from typing import Type, TypeVar, Generic, Optional
from pydantic import BaseModel
from openai import OpenAI
import config
from src.utils.runtime_logger import get_runtime_logger


def _check_endpoint(base_url: str, timeout: int = 3) -> bool:
    """检查 API 端点是否可达。
    
    启动前快速检查内网代理是否响应，避免 LLM 调用时才发现不通。
    只做连接检查，不发真实请求。
    """
    if not base_url:
        return False
    # 去掉 /v1 后缀或空路径，只检测根地址
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    try:
        httpx.get(root, timeout=timeout)
        return True
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError):
        return False

# 类型变量，用于泛型返回
T = TypeVar('T', bound=BaseModel)


class LLMResponse(BaseModel):
    """LLM 调用结果"""
    content: str
    raw_response: dict
    model: str
    usage: Optional[dict] = None


# 全局 observer 列表（TokenTracker 等通过 register_observer 注册）
_llm_observers: list = []


def register_observer(callback) -> None:
    """注册 LLM 调用完成后的观察者回调。

    callback 签名: fn(*, usage: dict, caller: str, elapsed: float, model: str)
    """
    _llm_observers.append(callback)


class LLMClient:
    """LLM 统一客户端

    支持多种 provider 的统一接口。
    """

    def __init__(
        self,
        provider: str = config.LLM_PROVIDER,
        api_key: str = config.LLM_API_KEY,
        base_url: str = config.LLM_BASE_URL,
        model: str = None,
        temperature: float = config.DEFAULT_TEMPERATURE,
        max_tokens: int = config.DEFAULT_MAX_TOKENS,
        request_timeout: float | None = None,
        task_type: str = "default",
    ):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.task_type = task_type

        # 初始化 OpenAI 客户端
        #兼容 DeepSeek/Zhipu/Qwen 等 provider
        _default_timeout = httpx.Timeout(
            connect=10.0,
            read=180.0,
            write=10.0,
            pool=10.0,
        )
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            timeout=_default_timeout,
        )

        # 确定模型名称
        self.model = model or config.get_model_name(task_type=self.task_type)

    def _diag_log(self, stage: str, caller: str | None = None, extra: str | None = None) -> None:
        parts = [
            "[llm_diag]",
            f"stage={stage}",
            f"model={self.model}",
            f"provider={self.provider}",
            f"timeout={self.request_timeout}",
            f"max_tokens={self.max_tokens}",
        ]
        if caller:
            parts.append(f"caller={caller}")
        if extra:
            parts.append(extra)
        print(" ".join(parts), file=sys.stderr)

    def _estimate_message_chars(self, messages: list) -> int:
        total = 0
        for item in messages:
            content = item.get("content", "")
            if isinstance(content, str):
                total += len(content)
            else:
                total += len(str(content))
        return total

    def _build_messages(self, system: str, user: str) -> list:
        """构建消息格式

        统一转换为 OpenAI 格式。
        """
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

    def _call_with_retry(self, messages: list, retry_times: int = None) -> LLMResponse:
        """带重试的 LLM 调用

        Args:
            messages: 消息列表
            retry_times: 重试次数，默认从 config 读取

        Returns:
            LLMResponse 对象
        """
        retry_times = retry_times or config.LLM_RETRY_TIMES
        last_error = None
        caller = inspect.stack()[2].function if len(inspect.stack()) > 2 else "unknown"
        logger = get_runtime_logger()

        for attempt in range(retry_times):
            try:
                start = time.perf_counter()
                self._diag_log("before_call_with_retry", caller=caller, extra=f"attempt={attempt}")
                logger.log_llm_start(caller, self.model)
                self._diag_log("before_chat_completions_create", caller=caller, extra=f"attempt={attempt}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.request_timeout,
                )
                elapsed = time.perf_counter() - start
                logger.log_llm_end(caller, self.model, elapsed)

                content = response.choices[0].message.content
                if not content:
                    content = getattr(response.choices[0].message, 'reasoning_content', '') or ''
                llm_response = LLMResponse(
                    content=content,
                    raw_response=response.model_dump(),
                    model=self.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    }
                )

                # 通知外部观察者（TokenTracker 等）
                for _obs in _llm_observers:
                    try:
                        _obs(
                            usage=llm_response.usage,
                            caller=caller,
                            elapsed=elapsed,
                            model=self.model,
                        )
                    except Exception:
                        pass  # 观察者失败不影响主流程

                return llm_response

            except Exception as e:
                self._diag_log(
                    "on_exception",
                    caller=caller,
                    extra=f"attempt={attempt} exception_type={type(e).__name__}",
                )
                logger.log_error(f"llm:{caller}", str(e))
                last_error = e
                if attempt < retry_times - 1:
                    time.sleep(config.LLM_RETRY_DELAY * (attempt + 1))
                continue

        raise RuntimeError(f"LLM 调用失败，已重试 {retry_times} 次: {last_error}")

    def _strip_think_block(self, content: str) -> str:
        """过滤思维链内容（qwen3 等模型的 :react 标签）

        移除内容中的 :react\n\n... 思维链块，只保留最终回答。

        Args:
            content: 原始响应内容

        Returns:
            过滤后的内容
        """
        # 移除 :react 标签开头的思维链
        # 模式: :react\n\n<思考内容>\n\n<实际回答>
        if content.startswith(":react") or content.startswith(":React"):
            # 找到第一个换行后的实际内容
            lines = content.split("\n", 2)
            if len(lines) >= 3:
                # lines[0] = ":react", lines[1] = "", lines[2] = 剩余内容
                content = lines[2] if len(lines) == 3 else "\n".join(lines[2:])

        # 通用模式：移除 <think>...</think> 思维链块
        content = re.sub(r'<think>[\s\S]*?</think>', '', content)

        # 通用模式：移除 <!-- ... --> 注释块
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

        return content.strip()

    def generate(
        self,
        system: str,
        user: str,
        response_model: Type[T] = None,
    ) -> T | str:
        """生成内容

        Args:
            system: System prompt
            user: User prompt
            response_model: Pydantic 模型类，用于结构化输出。如果为 None，则返回原始字符串。

        Returns:
            如果指定了 response_model，返回 Pydantic 模型实例；
            否则返回原始字符串。
        """
        self._diag_log("before_generate")
        messages = self._build_messages(system, user)
        self._diag_log(
            "input_size",
            extra=(
                f"system_chars={len(system)} "
                f"user_chars={len(user)} "
                f"message_count={len(messages)} "
                f"total_chars={self._estimate_message_chars(messages)} "
                f"estimated_tokens={self._estimate_message_chars(messages) // 4}"
            ),
        )
        response = self._call_with_retry(messages)

        if response_model is None:
          
            return self._strip_think_block(response.content)

        # 结构化输出：尝试解析 JSON
        content = response.content.strip()

       
        content = self._strip_think_block(content)

        # 尝试提取 JSON（处理可能的 markdown 代码块）
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
            # Pydantic 校验 + 自动重试
            return self._validate_with_retry(response_model, data, messages)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 返回内容无法解析为 JSON: {e}\n原始内容: {content}")

    def _validate_with_retry(
        self,
        response_model: Type[T],
        data: dict,
        original_messages: list,
        retry_times: int = 3,
    ) -> T:
        """使用 Pydantic 校验输出，失败则重试

        Args:
            response_model: Pydantic 模型类
            data: 原始数据 dict
            original_messages: 原始消息，用于重试时重新调用
            retry_times: 最大重试次数

        Returns:
            校验通过的 Pydantic 模型实例
        """
        for attempt in range(retry_times):
            try:
                return response_model(**data)
            except Exception as e:
                if attempt < retry_times - 1:
                    # 添加校验失败的上下文，重新调用
                    correction_prompt = f"""
之前的输出无法通过校验，错误信息: {e}
请严格按照 Pydantic schema 重新输出有效的 JSON。
"""
                    new_messages = original_messages + [
                        {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                        {"role": "user", "content": correction_prompt}
                    ]
                    response = self._call_with_retry(new_messages)

                    content = response.content.strip()
                    # v1.1.13: 过滤思维链内容
                    content = self._strip_think_block(content)
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                else:
                    raise ValueError(f"Pydantic 校验失败，已重试 {retry_times} 次: {e}")

        raise RuntimeError("不应到达此处")


# =============================================================================
# 全局单例
# =============================================================================

# 全局 LLM 客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def init_llm_client(
    provider: str = None,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    task_type: Optional[str] = None,
) -> LLMClient:
    """初始化全局 LLM 客户端

    应在应用启动时调用一次。

    自动检测内网端点是否可达，不可达时切换到外网 fallback 模型。
    
    Parameters
    ----------
    task_type : str, optional
        任务类型，用于模型路由器选择内网模型（如 'phase4_report', 'code_review'）。
        不传则用 router 的默认模型。
    """
    global _llm_client

    # ── Proxy 绕过：内网地址不走系统代理 ──────────────────────
    _gateway = (base_url or config.LLM_BASE_URL)
    if _gateway and ("100.89.3.59" in _gateway.lower() or "localhost" in _gateway.lower()):
        existing = os.environ.get("NO_PROXY", "")
        if "100.89.3.59" not in existing:
            os.environ["NO_PROXY"] = f"100.89.3.59,localhost,127.0.0.1,{existing}"
            os.environ["no_proxy"] = os.environ["NO_PROXY"]

    # ── Fallback 检查：内网不通时切外网 ──────────────────────
    if config.FALLBACK_ENABLED:
        target_url = base_url or config.LLM_BASE_URL
        if target_url and not _check_endpoint(target_url):
            print(f"[⚠] 内网端点 {target_url} 不可达，切换到外网 fallback")
            provider = config.FALLBACK_PROVIDER
            api_key = config.FALLBACK_API_KEY
            base_url = config.FALLBACK_BASE_URL
            model = config.FALLBACK_MODEL

    # ── 内网模式下用 router 选模型 ──────────────────────────
    if model is None and provider is None:
        from src.model_router import select as _select_model
        model = _select_model(task_type or "default")

    _llm_client = LLMClient(
        provider=provider or config.LLM_PROVIDER,
        api_key=api_key or config.LLM_API_KEY,
        base_url=base_url or config.LLM_BASE_URL,
        model=model,
    )
    return _llm_client
