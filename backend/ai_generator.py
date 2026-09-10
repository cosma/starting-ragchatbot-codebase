import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Tool Usage:
- **Course outline queries**: Use the course outline tool to retrieve course structure, lesson list, and links
- **Content queries**: Use the content search tool for questions about specific course materials and detailed educational content
- You may use tools across up to two sequential rounds per question. Use a second round only when the first round's results are needed to decide what to search for next (e.g., looking up a lesson title or course structure before searching content on that topic), or when comparing/cross-referencing information from two different tools or courses
- Do not repeat an identical tool call with the same arguments, and do not call a tool again just to double-check a result that already answered the question
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course structure/outline questions**: Use the outline tool to get the complete lesson structure
- **Course-specific content questions**: Search first, then answer
- **Multi-step questions**: If answering requires information from one tool call to inform another (e.g., a lesson title needed to search related content), use the first round to gather that information, then use it in the second round
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        # (newer Claude models reject the `temperature` param, so it's omitted)
        self.base_params = {
            "model": self.model,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential rounds of tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        # Loop for up to 2 rounds of tool use, then one final text-only round
        for round_num in range(1, self.MAX_TOOL_ROUNDS + 2):
            offer_tools = bool(tools) and tool_manager is not None and round_num <= self.MAX_TOOL_ROUNDS
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content
            }
            if offer_tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            response = self.client.messages.create(**api_params)

            if response.stop_reason != "tool_use":
                return response.content[0].text

            messages.append({"role": "assistant", "content": response.content})
            tool_results, error_occurred = self._execute_tools(response.content, tool_manager)
            messages.append({"role": "user", "content": tool_results})

            if error_occurred:
                break

        # Final call without tools (reached only via error break, or when budget exhausted)
        final_response = self.client.messages.create(
            **{**self.base_params, "messages": messages, "system": system_content}
        )
        return final_response.content[0].text
    
    def _execute_tools(self, content_blocks: List, tool_manager) -> tuple:
        """
        Execute all tool calls from a response and collect results.

        Args:
            content_blocks: The content blocks from Claude's response
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (tool_results list, error_occurred boolean)
        """
        tool_results = []
        error_occurred = False

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            try:
                result = tool_manager.execute_tool(block.name, **block.input)
            except Exception as e:
                result = f"Tool execution failed: {e}"
                error_occurred = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })

        return tool_results, error_occurred