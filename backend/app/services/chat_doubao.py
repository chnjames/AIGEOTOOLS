"""豆包（字节跳动）聊天模型封装模块 - 支持 async 流式调用"""
import asyncio
from typing import Any, Optional, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)


class ChatDoubao(BaseChatModel):
    """豆包聊天模型封装（LangChain 兼容，支持 async streaming）"""

    volc_ak: str
    volc_sk: str
    endpoint_id: str
    temperature: float = 0.7
    client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, volc_ak: str, volc_sk: str, endpoint_id: str, temperature: float = 0.7, **kwargs: Any):
        super().__init__(
            volc_ak=volc_ak,
            volc_sk=volc_sk,
            endpoint_id=endpoint_id,
            temperature=temperature,
            **kwargs,
        )
        self._init_client()

    def _init_client(self) -> None:
        try:
            from volcengine.ark import Ark
            self.client = Ark(ak=self.volc_ak, sk=self.volc_sk)
        except ImportError:
            try:
                from volcenginesdkarkruntime import Ark
                self.client = Ark(ak=self.volc_ak, sk=self.volc_sk)
            except ImportError as e:
                raise ImportError(
                    f"豆包初始化失败：缺少依赖库。请运行：pip install 'volcengine-python-sdk[ark]'。错误：{e}"
                )

    def _convert_messages(self, messages: List[BaseMessage]) -> list[dict]:
        volc_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                volc_messages.append({"role": "system", "content": str(msg.content)})
            elif isinstance(msg, HumanMessage):
                volc_messages.append({"role": "user", "content": str(msg.content)})
            elif isinstance(msg, AIMessage):
                volc_messages.append({"role": "assistant", "content": str(msg.content)})
            else:
                volc_messages.append({"role": "user", "content": str(msg.content)})
        return volc_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        volc_messages = self._convert_messages(messages)
        response = self.client.chat.completions.create(
            model=self.endpoint_id,
            messages=volc_messages,
            temperature=self.temperature,
        )
        ai_message = AIMessage(content=response.choices[0].message.content or "")
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        volc_messages = self._convert_messages(messages)

        def _sync_call() -> Any:
            return self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=volc_messages,
                temperature=self.temperature,
            )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, _sync_call)
        ai_message = AIMessage(content=response.choices[0].message.content or "")
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @property
    def _llm_type(self) -> str:
        return "doubao"


def create_chat_doubao(api_key: str, temperature: float = 0.7) -> ChatDoubao:
    parts = api_key.split(":")
    if len(parts) < 3:
        raise ValueError("豆包 API Key 格式错误，应为：access_key:secret_key:endpoint_id（用冒号分隔）")
    return ChatDoubao(
        volc_ak=parts[0],
        volc_sk=parts[1],
        endpoint_id=parts[2],
        temperature=temperature,
    )
