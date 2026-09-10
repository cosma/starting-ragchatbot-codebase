import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


class TestAIGeneratorToolCalling:
    """Test AIGenerator's tool-calling behavior and one-round constraint."""

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
    def test_generate_response_with_tool_use(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that when API returns tool_use, the tool is executed and a
        second API call is made with the tool result.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # First response: tool use request
        tool_use_response = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "photosynthesis"}
        )

        # Second response: final answer
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

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_use_second_call_excludes_tools(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Test that the second API call after tool use does NOT include
        tools parameter, enforcing the one-round-trip constraint.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # First response: tool use
        tool_use_response = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "mitochondria"}
        )

        # Second response: final answer
        final_response = mock_anthropic_response_builders["text"]("Mitochondria answer")

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Mitochondria search results"

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")
        tool_def = {
            "name": "search_course_content",
            "description": "Search",
            "input_schema": {}
        }

        generator.generate_response(
            query="Tell me about mitochondria",
            tools=[tool_def],
            tool_manager=mock_tool_manager
        )

        # Check the second call's parameters
        second_call = mock_client.messages.create.call_args_list[1]
        call_kwargs = second_call[1]

        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_one_round_trip_only_no_looping(self, mock_anthropic_class, mock_anthropic_response_builders):
        """
        Regression test: even if the second response is tool_use,
        no third call should be made. Tool calling stops after one round.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # First response: tool use
        tool_use_response_1 = mock_anthropic_response_builders["tool_use"](
            tool_name="search_course_content",
            tool_input={"query": "test"}
        )

        # Second response: another tool_use (shouldn't happen, but if it does...)
        tool_use_response_2 = mock_anthropic_response_builders["tool_use"](
            tool_name="get_course_outline",
            tool_input={"course_name": "test"}
        )

        mock_client.messages.create.side_effect = [tool_use_response_1, tool_use_response_2]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        generator = AIGenerator(api_key="test-key", model="claude-3-5-sonnet-20241022")

        # This should not crash, and should extract the tool_use content from the second response
        # since there's no tool result handler for it
        try:
            result = generator.generate_response(
                query="test",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager
            )
            # If it gets content[0].text from a tool_use block, it will raise AttributeError
            # because tool_use doesn't have .text
        except (AttributeError, IndexError):
            pass

        # The key test: only 2 API calls, not 3+
        assert mock_client.messages.create.call_count == 2
