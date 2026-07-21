"""API test runner for E2E testing framework."""

import base64
import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx
from langchain_core.load import loads

from gnw_evals.runners.base import BaseTestRunner
from gnw_evals.utils.eval_types import ExpectedData, TestResult


class APITestRunner(BaseTestRunner):
    """Test runner for API endpoint execution."""

    def __init__(
        self,
        api_base_url: str,
        api_token: str | None = None,
        ff: str | None = None,
        verbose: bool = False,
    ):
        """Initialize with API configuration."""
        self.api_base_url = api_base_url
        self.api_token = api_token
        self.ff = ff
        self.verbose = verbose

    @staticmethod
    def _build_app_thread_url(api_base_url: str, thread_id: str) -> str:
        """Build GNW app thread URL from API base URL and session/thread ID."""
        parsed = urlparse(api_base_url)
        if not parsed.scheme or not parsed.netloc:
            return f"{api_base_url.rstrip('/')}/app/threads/{thread_id}"

        host = parsed.hostname or ""
        if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return f"http://localhost:3000/app/threads/{thread_id}"

        app_host = host.removeprefix("api.") if host.startswith("api.") else host
        netloc = app_host
        if parsed.port:
            netloc = f"{app_host}:{parsed.port}"

        return urlunparse(
            (parsed.scheme, netloc, f"/app/threads/{thread_id}", "", "", ""),
        )

    async def run_test(self, query: str, expected_data: ExpectedData) -> TestResult:
        """Run a single agent test using API endpoint.

        Args:
            query: User query to test
            expected_data: Expected test results for evaluation

        Returns:
            TestResult with evaluation scores and metadata

        """
        thread_id = str(uuid4())
        trace_url = None
        app_thread_url = self._build_app_thread_url(self.api_base_url, thread_id)

        try:
            # Collect all streaming responses to ensure conversation completes
            responses = []
            trace_id = None

            # Prepare request payload
            payload = {
                "query": query,
                "user_persona": "Researcher",
                "thread_id": thread_id,
                "metadata": {"langfuse_tags": ["simple_e2e_test"]},
                "user_id": "test_user",
            }
            if self.ff:
                payload["ff"] = self.ff

            headers = {}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            # Use httpx async client for streaming
            async with httpx.AsyncClient(timeout=240.0) as client:
                if not expected_data.thread_id:
                    async with client.stream(
                        "POST",
                        f"{self.api_base_url}/api/chat",
                        json=payload,
                        headers=headers,
                    ) as response:
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if line.strip():
                                stream_data = json.loads(line)
                                responses.append(stream_data)

                                # Capture trace ID from stream
                                if stream_data.get("node") == "trace_info":
                                    update_data = json.loads(
                                        stream_data.get("update", "{}"),
                                    )
                                    trace_id = update_data.get("trace_id")
                                    trace_url = update_data.get("trace_url")

                # Get final agent state using the state endpoint
                state_response = await client.get(
                    f"{self.api_base_url}/api/threads/{thread_id}/state",
                    headers=headers,
                )
                state_response.raise_for_status()
                response_data = state_response.json()
                agent_state = response_data.get("state", {})
                agent_state = loads(agent_state)

                # Fetch dashboard details when a dashboard was created this turn.
                # agent_state only carries the dashboard_id; AOI/widget details
                # live on the dashboard resource itself. A failed fetch degrades
                # to dashboard=None (soft failure) rather than erroring the row -
                # the primary chat result already succeeded.
                dashboard: dict[str, Any] | None = None
                dashboard_id = (
                    agent_state.get("dashboard_id")
                    if isinstance(agent_state, dict)
                    else None
                )
                if dashboard_id:
                    try:
                        dashboard_response = await client.get(
                            f"{self.api_base_url}/api/dashboards/{dashboard_id}",
                            headers=headers,
                        )
                        dashboard_response.raise_for_status()
                        dashboard = dashboard_response.json()
                    except Exception as dashboard_error:
                        print(
                            f"Warning: failed to fetch dashboard {dashboard_id}: "
                            f"{dashboard_error}",
                        )
                        dashboard = None

            # Run evaluations
            evaluations = self._run_evaluations(
                agent_state,
                expected_data,
                query,
                dashboard,
            )
            overall_score = self._calculate_overall_score(evaluations, expected_data)

            # Print tool trace in verbose mode
            if self.verbose:
                print(
                    self._format_tool_trace(
                        query,
                        thread_id,
                        trace_id,
                        trace_url,
                        agent_state,
                        overall_score,
                    ),
                )

            kwargs = expected_data.to_dict()
            kwargs.update(evaluations)
            kwargs.pop("thread_id", None)
            kwargs.pop("trace_id", None)
            kwargs.pop("trace_url", None)
            kwargs.pop("query", None)
            kwargs.pop("overall_score", None)
            kwargs.pop("execution_time", None)

            return TestResult(
                thread_id=thread_id,
                app_thread_url=app_thread_url,
                trace_id=trace_id,
                trace_url=trace_url,
                query=query,
                overall_score=overall_score,
                execution_time=datetime.now().isoformat(),
                **kwargs,
            )

        except Exception as e:
            print(f"Error: {e}")
            return self._create_empty_evaluation_result(
                thread_id,
                trace_url or "",
                app_thread_url,
                query,
                expected_data,
                str(e),
            )

    @staticmethod
    def _indent(text: str, prefix: str) -> str:
        """Add prefix to each line of text."""
        return "\n".join(f"{prefix}{line}" for line in text.split("\n"))

    def _truncate(self, text: str, limit: int = 2000) -> str:
        """Truncate long text with an ellipsis indicator."""
        if len(text) <= limit:
            return text
        return text[:limit] + "\n... (truncated)"

    def _format_tool_trace(
        self,
        query: str,
        thread_id: str,
        trace_id: str | None,
        trace_url: str | None,
        agent_state: dict[str, Any],
        overall_score: float,
    ) -> str:
        """Format a human-readable tool trace for verbose output.

        Extracts tool calls from messages (tool_call/tool_message pairs)
        and decoded codeact_parts (code blocks and execution output),
        presenting them in a step-by-step chronological format.
        """
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("TOOL TRACE")
        lines.append("=" * 70)
        lines.append(f"Query:     {query}")
        lines.append(f"Thread ID: {thread_id}")
        if trace_id:
            lines.append(f"Trace ID:  {trace_id}")
        if trace_url:
            lines.append(f"Trace URL: {trace_url}")
        lines.append(f"Score:     {overall_score}")

        messages = agent_state.get("messages", [])
        raw_parts = agent_state.get("codeact_parts", [])

        # Extract tool call / tool message pairs from messages
        tool_calls: list[dict[str, Any]] = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if isinstance(tc, dict):
                        tool_calls.append(
                            {
                                "name": tc.get("name", "unknown"),
                                "args": tc.get("args", {}),
                                "id": tc.get("id", ""),
                            },
                        )

        # Match tool messages back to their calls
        for msg in messages:
            if hasattr(msg, "tool_call_id") and hasattr(msg, "content"):
                tid = msg.tool_call_id
                for tc in reversed(tool_calls):
                    if tc["id"] == tid and "output" not in tc:
                        tc["output"] = msg.content
                        break

        # Print tool calls from messages
        if tool_calls:
            lines.append("")
            lines.append("--- Tool Calls ---")
            for i, tc in enumerate(tool_calls, 1):
                lines.append("")
                lines.append(f"Tool {i}: {tc['name']}")
                if tc["args"]:
                    args_str = json.dumps(tc["args"], indent=2, default=str)
                    lines.append(f"  Input:\n{self._indent(args_str, '    ')}")
                if "output" in tc:
                    output = str(tc["output"])
                    output = self._truncate(output, 3000)
                    lines.append(f"  Output:\n{self._indent(output, '    ')}")

        # Decode and print codeact_parts
        if raw_parts:
            lines.append("")
            lines.append("--- Execution Trace ---")
            type_labels = {
                "code_block": "CODE",
                "text_output": "LLM",
                "execution_output": "OUTPUT",
            }
            step = 0
            for part in raw_parts:
                part_type = part.get("type", "unknown")
                try:
                    content = base64.b64decode(
                        part.get("content", ""),
                    ).decode("utf-8")
                except Exception:
                    content = part.get("content", "")
                label = type_labels.get(part_type, part_type.upper())
                step += 1
                content = self._truncate(content, 4000)
                lines.append("")
                lines.append(f"Step {step} [{label}]")
                lines.append(self._indent(content, "    "))

        if not tool_calls and not raw_parts:
            lines.append("")
            lines.append("(no tool trace available)")

        lines.append("=" * 70)
        return "\n".join(lines)
