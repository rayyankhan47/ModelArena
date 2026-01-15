"""Backboard-powered orchestrator for AI Arena matches."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Set

from ai_arena.config import settings
from ai_arena.engine.generate import generate_initial_state
from ai_arena.engine.reducer import resolve_round
from ai_arena.engine.types import (
    Action,
    ActionType,
    CollectAction,
    MoveAction,
    NoopAction,
    OpenVaultAction,
    ScanAction,
    SetTrapAction,
    StealAction,
    GameState,
)
from ai_arena.storage.logger import MatchLogger

from .backboard_client import BackboardClient, BackboardConfig
from .prompts import (
    action_prompt,
    negotiation_prompt,
    planning_prompt,
    system_prompt,
    RULES_SUMMARY,
)
from .routing import ModelRouter
from .tools import ToolContext, ToolExecutor, tool_definitions, parse_tool_calls
from ai_arena.rag.index import upload_corpus_to_assistant


PLAYER_IDS = ["P1", "P2", "P3", "P4"]


class OrchestratorRunner:
    """Runs a Backboard-driven match with planner/actor routing and tools."""

    def __init__(self, db_path: str = "ai_arena.db"):
        if not settings.backboard_api_key:
            raise ValueError("BACKBOARD_API_KEY is required to run the orchestrator.")

        self.router = ModelRouter()
        self.client = BackboardClient(
            BackboardConfig(
                api_key=settings.backboard_api_key,
                base_url=settings.backboard_base_url,
                timeout=settings.backboard_timeout,
            )
        )
        self.logger = MatchLogger(db_path=db_path)
        self.tool_executor = ToolExecutor()

        self.assistants: Dict[str, str] = {}
        self.threads: Dict[str, str] = {}
        self.shared_assistant_id: Optional[str] = None
        self.shared_thread_id: Optional[str] = None
        self._search_budget: Dict[str, int] = {}
        self._last_search_round: Dict[str, int] = {}

    def run_match(self, seed: Optional[str] = None, rounds: Optional[int] = None) -> str:
        """Run a full match using Backboard and return match_id."""
        match_seed = seed or settings.default_match_seed
        max_rounds = rounds or settings.default_match_rounds

        match_id = self.logger.start_match(
            seed=match_seed,
            max_rounds=max_rounds,
            config={"planner_model": settings.planner_model, "actor_model": settings.actor_model},
        )

        self._setup_assistants_and_threads()

        state = generate_initial_state(seed=match_seed, max_rounds=max_rounds)
        deals: List[Any] = []
        self._init_search_budget()

        for round_num in range(max_rounds):
            shared_summary = self._get_shared_summary(round_num)

            # Planning phase
            for player_id in PLAYER_IDS:
                web_search = self._web_search_mode(player_id, state.round)
                response = self._send_phase_message(
                    state=state,
                    deals=deals,
                    player_id=player_id,
                    phase="plan",
                    content=planning_prompt(self._state_summary(state), shared_summary),
                    model_route=self.router.planner_route(),
                    memory="Auto",
                    web_search=web_search,
                )
                citations = self._extract_citations(response.get("content") or "")
                if citations:
                    self.logger.log_tool_calls(
                        round_num=state.round,
                        player_id=player_id,
                        tool_calls=[{
                            "name": "rag_citations",
                            "args": {"citations": sorted(citations)},
                            "result": {}
                        }],
                    )
                search_query = self._extract_search_query(response.get("content") or "")
                if web_search == "Auto":
                    self._mark_search_used(player_id, state.round)
                    self.logger.log_tool_calls(
                        round_num=state.round,
                        player_id=player_id,
                        tool_calls=[{
                            "name": "web_search_used",
                            "args": {"query": search_query or "unspecified"},
                            "result": {}
                        }],
                    )

            # Negotiation phase
            negotiation_messages = []
            for player_id in PLAYER_IDS:
                response = self._send_phase_message(
                    state=state,
                    deals=deals,
                    player_id=player_id,
                    phase="negotiate",
                    content=negotiation_prompt(self._state_summary(state), shared_summary),
                    model_route=self.router.planner_route(),
                    memory="Auto",
                )
                message = (response.get("content") or "").strip()
                if message:
                    negotiation_messages.append(f"{player_id}: {message}")
                    self._append_shared_message(f"{player_id} says: {message}")

            if negotiation_messages or deals:
                transcript = " | ".join(negotiation_messages) if negotiation_messages else "No messages"
                self._append_shared_message(
                    f"Round {round_num} negotiation transcript: {transcript}. Deals: {self._deals_snapshot(deals)}"
                )

            # Keep active deals on the state for UI/replay visibility
            state.active_deals = deals

            # Commit phase
            actions: Dict[str, Action] = {}
            for player_id in PLAYER_IDS:
                response = self._send_phase_message(
                    state=state,
                    deals=deals,
                    player_id=player_id,
                    phase="commit",
                    content=action_prompt(self._state_summary(state), shared_summary),
                    model_route=self.router.actor_route(),
                    memory="Readonly",
                )
                action = self._parse_action(response)
                if isinstance(action, NoopAction):
                    # Retry once with planner model if invalid
                    response = self._send_phase_message(
                        state=state,
                        deals=deals,
                        player_id=player_id,
                        phase="commit_retry",
                        content=action_prompt(self._state_summary(state), shared_summary),
                        model_route=self.router.planner_route(),
                        memory="Readonly",
                    )
                    action = self._parse_action(response)
                actions[player_id] = action

            # Resolve round
            result = resolve_round(state, actions)
            state = result.next_state

            # Log round
            self.logger.log_round_complete(round_num, state, actions, result.rewards)
            self.logger.log_events(round_num, result.events)

            # Memory writeback (private + shared)
            round_summary = self._build_round_summary(round_num, actions, result.rewards, result.events)
            for player_id in PLAYER_IDS:
                self._append_agent_memory(player_id, round_summary)
            self._append_shared_message(round_summary)

        return match_id

    def _setup_assistants_and_threads(self) -> None:
        tools = tool_definitions()

        # Shared assistant for match memory
        shared = self.client.create_assistant(
            name="AI Arena Shared",
            system_prompt="You summarize shared match context and negotiations succinctly.",
            tools=tools,
        )
        self.shared_assistant_id = shared["assistant_id"]
        self.shared_thread_id = self.client.create_thread(self.shared_assistant_id)["thread_id"]

        # Upload RAG corpus to shared assistant
        upload_corpus_to_assistant(self.client, self.shared_assistant_id)

        # Per-player assistants and threads
        for player_id in PLAYER_IDS:
            assistant = self.client.create_assistant(
                name=f"AI Arena {player_id}",
                system_prompt=system_prompt(player_id) + "\n\n" + RULES_SUMMARY,
                tools=tools,
            )
            assistant_id = assistant["assistant_id"]
            thread_id = self.client.create_thread(assistant_id)["thread_id"]
            upload_corpus_to_assistant(self.client, assistant_id)
            self.assistants[player_id] = assistant_id
            self.threads[player_id] = thread_id

    def _send_phase_message(
        self,
        *,
        state: GameState,
        deals: List[Dict[str, Any]],
        player_id: str,
        phase: str,
        content: str,
        model_route,
        memory: str,
        web_search: str = "off",
    ) -> Dict[str, Any]:
        thread_id = self.threads[player_id]
        request_payload = {
            "content": content,
            "llm_provider": model_route.provider or "",
            "model_name": model_route.model,
            "memory": memory,
            "web_search": web_search,
            "send_to_llm": True,
            "metadata": {
                "phase": phase,
                "round": state.round,
                "player_id": player_id,
            },
        }

        start = time.time()
        response = self.client.post_message(thread_id, **request_payload)
        latency_ms = int((time.time() - start) * 1000)
        self.logger.log_agent_call(
            round_num=state.round,
            player_id=player_id,
            phase=phase,
            model=model_route.model,
            latency_ms=latency_ms,
            request=request_payload,
            response=response,
        )

        # Tool handling loop (limit to avoid infinite cycles)
        tool_cycles = 0
        while response.get("tool_calls") and response.get("run_id") and tool_cycles < 3:
            tool_calls = parse_tool_calls(response)
            tool_outputs = []
            tool_logs = []
            for tool_call in tool_calls:
                if not tool_call["tool_call_id"]:
                    continue
                ctx = ToolContext(state=state, player_id=player_id, deals=deals)
                result = self.tool_executor.execute(tool_call["name"], tool_call["args"], ctx)
                tool_outputs.append({
                    "tool_call_id": tool_call["tool_call_id"],
                    "output": json.dumps(result),
                })
                tool_logs.append({
                    "name": tool_call["name"],
                    "args": tool_call["args"],
                    "result": result,
                })

            if tool_logs:
                self.logger.log_tool_calls(state.round, player_id, tool_logs)

            response = self.client.submit_tool_outputs(
                thread_id=thread_id,
                run_id=response["run_id"],
                tool_outputs=tool_outputs,
                stream=False,
            )
            tool_cycles += 1

        return response

    def _append_shared_message(self, content: str) -> None:
        if not self.shared_thread_id:
            return
        self.client.post_message(
            self.shared_thread_id,
            content=content,
            llm_provider=self.router.planner_route().provider or "",
            model_name=self.router.planner_route().model,
            memory="Auto",
            web_search="off",
            send_to_llm=False,
            stream=False,
        )

    def _append_agent_memory(self, player_id: str, summary: str) -> None:
        thread_id = self.threads[player_id]
        self.client.post_message(
            thread_id,
            content=summary,
            llm_provider=self.router.planner_route().provider or "",
            model_name=self.router.planner_route().model,
            memory="Auto",
            web_search="off",
            send_to_llm=False,
            stream=False,
        )

    def _get_shared_summary(self, round_num: int) -> str:
        if not self.shared_thread_id:
            return ""
        prompt = (
            f"Provide a short shared summary for round {round_num}. "
            "Include key negotiations, deals, and notable behaviors in 3 bullets."
        )
        response = self.client.post_message(
            self.shared_thread_id,
            content=prompt,
            llm_provider=self.router.planner_route().provider or "",
            model_name=self.router.planner_route().model,
            memory="Auto",
            web_search="off",
            send_to_llm=True,
            stream=False,
        )
        return (response.get("content") or "").strip()

    def _state_summary(self, state: GameState) -> str:
        players = []
        for pid, p in state.players.items():
            players.append(
                f"{pid}: pos=({p.pos.x},{p.pos.y}) score={p.score} keys={p.keys} trapped={p.trapped_for}"
            )
        return " | ".join(players)

    def _build_round_summary(self, round_num: int, actions: Dict[str, Action], rewards: Dict[str, int], events) -> str:
        action_str = ", ".join([f"{pid}:{action.type}" for pid, action in actions.items()])
        reward_str = ", ".join([f"{pid}:{rewards.get(pid, 0)}" for pid in PLAYER_IDS])
        event_str = "; ".join([e.kind for e in events[:6]])
        return f"Round {round_num} summary. Actions: {action_str}. Rewards: {reward_str}. Events: {event_str}."

    def _extract_citations(self, text: str) -> Set[str]:
        """Extract citation tags like [R1] or [S3] from text."""
        citations: Set[str] = set()
        for part in text.split("["):
            if "]" in part:
                tag = part.split("]")[0].strip()
                if tag and (tag.startswith("R") or tag.startswith("S")) and tag[1:].isdigit():
                    citations.add(f"[{tag}]")
        return citations

    def _extract_search_query(self, text: str) -> str:
        for line in text.splitlines():
            if line.lower().startswith("searchquery:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _init_search_budget(self) -> None:
        for pid in PLAYER_IDS:
            self._search_budget[pid] = settings.search_budget_per_agent
            self._last_search_round[pid] = -9999

    def _web_search_mode(self, player_id: str, round_num: int) -> str:
        if self._search_budget.get(player_id, 0) <= 0:
            return "off"
        last_round = self._last_search_round.get(player_id, -9999)
        if round_num - last_round < settings.search_cooldown_rounds:
            return "off"
        return "Auto"

    def _mark_search_used(self, player_id: str, round_num: int) -> None:
        if self._search_budget.get(player_id, 0) <= 0:
            return
        self._search_budget[player_id] -= 1
        self._last_search_round[player_id] = round_num

    def _deals_snapshot(self, deals: List[Any]) -> str:
        if not deals:
            return "none"
        parts = []
        for deal in deals[:6]:
            from_player = getattr(deal, "from_player", "?")
            to_player = getattr(deal, "to_player", "?")
            status = getattr(deal, "status", "?")
            parts.append(f"{from_player}->{to_player}({status})")
        return ", ".join(parts)

    def _parse_action(self, response: Dict[str, Any]) -> Action:
        content = response.get("content") or ""
        content = content.strip()
        if not content:
            return NoopAction(reason="empty_response")

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from code block
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                try:
                    data = json.loads(content[start:end])
                except json.JSONDecodeError:
                    return NoopAction(reason="invalid_json")
            else:
                return NoopAction(reason="invalid_json")

        action_type = data.get("type")
        try:
            if action_type == ActionType.MOVE.value:
                return MoveAction.model_validate(data)
            if action_type == ActionType.COLLECT.value:
                return CollectAction.model_validate(data)
            if action_type == ActionType.OPEN_VAULT.value:
                return OpenVaultAction.model_validate(data)
            if action_type == ActionType.SCAN.value:
                return ScanAction.model_validate(data)
            if action_type == ActionType.SET_TRAP.value:
                return SetTrapAction.model_validate(data)
            if action_type == ActionType.STEAL.value:
                return StealAction.model_validate(data)
            if action_type == ActionType.NOOP.value:
                return NoopAction.model_validate(data)
        except Exception:  # noqa: BLE001
            return NoopAction(reason="invalid_schema")

        return NoopAction(reason="unknown_action_type")
