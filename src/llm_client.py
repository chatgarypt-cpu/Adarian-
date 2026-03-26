"""
LLM 统一调用封装
---
所有 LLM 调用必须通过此模块，禁止在业务代码中直接 import openai。
Why: 统一接口便于切换 provider，统一错误处理和重试机制。
"""

import json
import time
from typing import Type, TypeVar, Generic, Optional
from pydantic import BaseModel
from openai import OpenAI
import config

# 类型变量，用于泛型返回
T = TypeVar('T', bound=BaseModel)


class LLMResponse(BaseModel):
    """LLM 调用结果"""
    content: str
    raw_response: dict
    model: str
    usage: Optional[dict] = None


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
    ):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 初始化 OpenAI 客户端
        #兼容 DeepSeek/Zhipu/Qwen 等 provider
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
        )

        # 确定模型名称
        self.model = model or config.get_model_name()

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

        for attempt in range(retry_times):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                content = response.choices[0].message.content
                return LLMResponse(
                    content=content,
                    raw_response=response.model_dump(),
                    model=self.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    }
                )

            except Exception as e:
                last_error = e
                if attempt < retry_times - 1:
                    time.sleep(config.LLM_RETRY_DELAY * (attempt + 1))
                continue

        raise RuntimeError(f"LLM 调用失败，已重试 {retry_times} 次: {last_error}")

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
        messages = self._build_messages(system, user)
        response = self._call_with_retry(messages)

        if response_model is None:
            return response.content

        # 结构化输出：尝试解析 JSON
        content = response.content.strip()

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
) -> LLMClient:
    """初始化全局 LLM 客户端

    应在应用启动时调用一次。
    """
    global _llm_client
    _llm_client = LLMClient(
        provider=provider or config.LLM_PROVIDER,
        api_key=api_key or config.LLM_API_KEY,
        base_url=base_url or config.LLM_BASE_URL,
        model=model,
    )
    return _llm_client
