import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


pytestmark = pytest.mark.unit


class TestAIGeneratorToolCalling:
    """Test AIGenerator's tool-calling behavior with support for up to 2 sequential rounds."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_direct_text_no_tools(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that when API returns end_turn with text, no tools are used
        and the text is returned directly.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = mock_anthropic_response_builders["text"]("Direct answer without tools")
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        result = generator.generate_response(
            query="What is photosynthesis?",
            tools=[]
        )

        assert result == "Direct answer without tools"
        mock_client.messages.create.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_single_round_tool_use_then_stop(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that a single round of tool use works: round 1 tool_use,
        round 2 returns text.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: tool use request
        tool_use_response = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "photosynthesis"}
        )

        # Round 2: final answer
        final_response = mock_anthropic_response_builders["text"]("Here is the answer about photosynthesis.")

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search result about photosynthesis"

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tool_def = {
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {}
        }

        result = generator.generate_response(
            query="What is photosynthesis?",
            tools=[tool_def],
            tool_manager=mock_tool_manager
        )

        assert result == "Here is the answer about photosynthesis."
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="photosynthesis"
        )

        # Check that tools were included in round 2 (since 2 <= MAX_TOOL_ROUNDS)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_rounds_tool_use_then_stop(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that two rounds of tool use work: round 1 tool_use (outline),
        round 2 tool_use (search), round 3 returns text without tools.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: get course outline
        outline_response = mock_anthropic_response_builders["tool_use"](
            tool_name="get_course_outline",
            tool_input={"course_name": "Biology 101"}
        )

        # Round 2: search course content
        search_response = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "photosynthesis"}
        )

        # Round 3: final answer
        final_response = mock_anthropic_response_builders["text"]("Here is the comprehensive answer.")

        mock_client.messages.create.side_effect = [outline_response, search_response, final_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = [
            "Lesson 4: Cellular Respiration",
            "Found photosynthesis content"
        ]

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tools = [
            {"name": "get_course_outline", "description": "Get course outline", "input_schema": {}},
            {"name": "search_course_content", "description": "Search content", "input_schema": {}}
        ]

        result = generator.generate_response(
            query="What is photosynthesis?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        assert result == "Here is the comprehensive answer."
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Round 3 should not have tools/tool_choice
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_cap_forces_final_answer(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that even if rounds 1 and 2 both want to call tools,
        round 3 is forced to be text-only (tools omitted), proving the cap
        is enforced structurally.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: tool use
        tool_response_1 = mock_anthropic_response_builders["tool_use"](
            tool_name="get_course_outline",
            tool_input={"course_name": "test"}
        )

        # Round 2: also tool use
        tool_response_2 = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "test"}
        )

        # Round 3: text response (forced, since no tools offered)
        text_response = mock_anthropic_response_builders["text"]("Final answer")

        mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tool_def = {"name": "test_tool", "description": "Test", "input_schema": {}}

        result = generator.generate_response(
            query="test",
            tools=[tool_def],
            tool_manager=mock_tool_manager
        )

        # Exactly 3 calls (no 4th call even though round 2 wanted tools)
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Final answer"

        # Round 3 should not have tools
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_error_returns_graceful_final_answer(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that a tool execution error is caught, surfaced to Claude as
        a tool_result, and a final text-only call is made.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: tool use
        tool_use_response = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "test"}
        )

        # Round 2 (post-error): final answer
        final_response = mock_anthropic_response_builders["text"]("I encountered an error, but here's what I know.")

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = Exception("boom")

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tool_def = {"name": "search_course_content", "description": "Search", "input_schema": {}}

        result = generator.generate_response(
            query="test",
            tools=[tool_def],
            tool_manager=mock_tool_manager
        )

        # No exception escapes
        assert result == "I encountered an error, but here's what I know."
        assert mock_client.messages.create.call_count == 2

        # Round 2 should not have tools (error abort)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" not in second_call_kwargs

        # Check that the tool_result block contains the error message
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]
        assert tool_result_msg["role"] == "user"
        assert "Tool execution failed:" in tool_result_msg["content"][0]["content"]

    @patch("ai_generator.anthropic.Anthropic")
    def test_message_history_accumulates_across_rounds(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that message history (including tool_use and tool_result blocks)
        accumulates correctly across rounds.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: tool use
        tool_response_1 = mock_anthropic_response_builders["tool_use"](
            tool_name="get_course_outline",
            tool_input={"course_name": "Biology"}
        )

        # Round 2: tool use
        tool_response_2 = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "photosynthesis"}
        )

        # Round 3: text
        text_response = mock_anthropic_response_builders["text"]("Final answer")

        mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Outline result", "Search result"]

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tools = [
            {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
            {"name": "search_course_content", "description": "Search", "input_schema": {}}
        ]

        result = generator.generate_response(
            query="Find photosynthesis info",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Check round 2's messages contain round 1's tool_use and tool_result
        round2_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        assert len(round2_messages) >= 3  # user, assistant with tool_use, user with tool_result
        assert round2_messages[1]["role"] == "assistant"
        assert round2_messages[2]["role"] == "user"

        # Check round 3's messages contain both rounds' interactions
        round3_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        assert len(round3_messages) >= 5  # user, asst tool1, user result1, asst tool2, user result2
        assert round3_messages[-2]["role"] == "assistant"
        assert round3_messages[-1]["role"] == "user"
