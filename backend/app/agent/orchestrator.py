import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.agent.system_prompt import GREENAIR_SYSTEM_PROMPT
from backend.app.agent.tool_registry import TOOL_SCHEMAS, execute_tool_async
from backend.app.agent.memory import ConversationMemory
from backend.app.services.llm_service import llm_service
from backend.app.database.repository import (
    get_session_messages, add_message, create_session
)
from backend.app.schemas.schemas import ChatResponse, ToolExecutionRecord

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    @classmethod
    async def process_message(
        cls,
        message: str,
        session_id: Optional[str] = None,
        active_dataset_id: Optional[str] = None,
        latest_pollutants: Optional[Dict[str, float]] = None,
    ) -> ChatResponse:
        """
        Orchestrate multi-turn agent execution:
        Prompt -> Context Load -> Tool Selection -> Tool Execution -> Grounded Response -> Persistence.
        """
        # Ensure session exists
        if not session_id:
            session_id = create_session(title=message[:40] if message else "Consultation")

        # Load history
        history_records = get_session_messages(session_id, limit=20)
        bounded_history = ConversationMemory.prepare_chat_history(history_records, max_turns=10)

        # Check provider availability
        has_key, provider_name = llm_service.is_provider_available()
        tools_executed: List[ToolExecutionRecord] = []
        final_text = ""
        finish_reason = "stop"

        if has_key and provider_name == "groq":
            try:
                # Build context messages
                sys_content = GREENAIR_SYSTEM_PROMPT
                if active_dataset_id:
                    sys_content += f"\n\n[Context Notice: The user currently has active dataset ID '{active_dataset_id}' loaded]."
                if latest_pollutants:
                    sys_content += f"\n\n[Context Notice: Latest pollutant values entered in dashboard: {json.dumps(latest_pollutants)}]."

                messages = [{"role": "system", "content": sys_content}]
                messages.extend(bounded_history)
                messages.append({"role": "user", "content": message})

                iteration = 0
                while iteration < settings.MAX_AGENT_ITERATIONS:
                    iteration += 1
                    logger.info(f"Agent iteration {iteration} calling Groq...")
                    
                    llm_resp = await llm_service.call_groq(messages, tools=TOOL_SCHEMAS)
                    choice = llm_resp.get("choices", [{}])[0]
                    assistant_msg = choice.get("message", {})
                    finish_reason = choice.get("finish_reason", "stop")

                    # Check for tool calls
                    tool_calls = assistant_msg.get("tool_calls")
                    if not tool_calls:
                        final_text = assistant_msg.get("content", "")
                        break

                    # Append assistant message with tool calls to conversation
                    messages.append(assistant_msg)

                    # Execute each tool call
                    for tc in tool_calls:
                        func_info = tc.get("function", {})
                        t_name = func_info.get("name", "")
                        raw_args = func_info.get("arguments", "{}")
                        try:
                            t_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except Exception:
                            t_args = {}

                        # Inject active_dataset_id if needed and omitted
                        if "dataset_id" in t_args and not t_args["dataset_id"] and active_dataset_id:
                            t_args["dataset_id"] = active_dataset_id

                        logger.info(f"Agent executing tool: {t_name} with args: {t_args}")
                        out, ms, ok, err = await execute_tool_async(t_name, t_args)

                        record = ToolExecutionRecord(
                            tool_name=t_name,
                            tool_arguments=t_args,
                            output=out,
                            execution_time_ms=ms,
                            success=ok,
                            error=err,
                        )
                        tools_executed.append(record)

                        # Provide tool response to LLM
                        tool_resp_content = json.dumps(out) if ok else json.dumps({"error": err})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", f"call_{t_name}"),
                            "content": tool_resp_content,
                        })

                if not final_text and tools_executed:
                    # If stopped without text, synthesize from last tool
                    final_text = "I have executed the requested environmental tools. Please review the detailed outputs above."

            except Exception as e:
                logger.warning(f"Groq provider call failed: {e}. Gracefully falling back to deterministic agent.")
                final_text, fallback_tools = llm_service.run_deterministic_agent(
                    message, active_dataset_id=active_dataset_id, latest_pollutants=latest_pollutants
                )
                tools_executed = [ToolExecutionRecord(**t) for t in fallback_tools]
                provider_used = "Deterministic Engine [Groq Fallback]"

        else:
            # Deterministic agent execution
            final_text, raw_tools = llm_service.run_deterministic_agent(
                message, active_dataset_id=active_dataset_id, latest_pollutants=latest_pollutants
            )
            tools_executed = [ToolExecutionRecord(**t) for t in raw_tools]
            provider_used = "Autonomous Deterministic Engine (Zero External Key Required)"

        # Save to database
        serialized_tools = [t.model_dump() for t in tools_executed]
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", final_text, tool_calls=serialized_tools)

        now_iso = datetime.now(timezone.utc).isoformat()

        return ChatResponse(
            session_id=session_id,
            response=final_text,
            tools_executed=tools_executed,
            data_references={"active_dataset_id": active_dataset_id},
            provider_used=provider_name if has_key else "Deterministic Engine",
            finish_reason=finish_reason,
            created_at=now_iso,
        )

orchestrator = AgentOrchestrator()
