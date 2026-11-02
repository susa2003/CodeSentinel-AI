from typing import List, Dict, Any

class ConversationMemory:
    @staticmethod
    def prepare_chat_history(
        messages: List[Dict[str, Any]],
        max_turns: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Produce a bounded sliding-window conversation history for LLM invocation.
        Retains the most recent exchanges to prevent unbounded context growth.
        """
        # Take the most recent max_turns messages
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        formatted = []
        for m in recent:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant", "system"):
                formatted.append({"role": role, "content": content})

        return formatted
