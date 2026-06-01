"""
ForensIQ – Core Agent Logic
=============================
Encapsulates all LLM interactions through the ``ForensIQAgent`` class.

The agent:
    1. Initialises the Groq SDK (Llama 3.3 via Groq inference).
    2. Maintains an in-memory *case memory* (list of labelled documents).
    3. Exposes four analytical methods that pair a module prompt with the
       case context and parse the structured JSON response.
    4. Provides a conversational chat method for free-form investigator
       questions.

Error Handling Strategy
-----------------------
* Every LLM call is wrapped in ``try / except`` blocks that catch:
  - ``json.JSONDecodeError`` – when the model returns malformed JSON.
  - API-level failures (quota, network, auth).
  - Generic ``Exception`` – any unexpected issue.
* On failure the method returns a dict/list with an ``"error"`` key so the
  UI can display a user-friendly message instead of crashing.

Usage:
    from agent import ForensIQAgent
    agent = ForensIQAgent()
    agent.add_document("Suspect A – Statement 1", text)
    result = agent.detect_contradictions()
"""

from __future__ import annotations

import json
import re
import time
import logging
from typing import Any

from groq import Groq

from config import get_settings
from prompts import (
    SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    CONTRADICTION_PROMPT,
    TIMELINE_PROMPT,
    PROFILER_PROMPT,
    NEXT_QUESTION_PROMPT,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("forensiq.agent")


# ---------------------------------------------------------------------------
# Helper – strip markdown fences the model sometimes adds despite prompting
# ---------------------------------------------------------------------------
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)


def _clean_json_response(raw: str) -> str:
    """
    Strip markdown code fences (```json ... ```) if the LLM wraps them
    around the JSON despite our instructions.  Returns the inner content.
    """
    match = _JSON_FENCE_RE.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _safe_parse_json(raw: str) -> list | dict:
    """
    Attempt to parse *raw* as JSON.  Tries cleaning markdown fences first.

    Returns
    -------
    list | dict
        Parsed JSON structure.

    Raises
    ------
    json.JSONDecodeError
        If the string cannot be parsed even after cleaning.
    """
    cleaned = _clean_json_response(raw)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# ForensIQ Agent
# ---------------------------------------------------------------------------
class ForensIQAgent:
    """
    Central agent class that wraps the Groq LLM and provides the four
    forensic analysis modules plus a conversational chat interface.

    Parameters
    ----------
    api_key : str | None
        Override the API key from config.  Primarily useful for testing.
    model_name : str | None
        Override the model name from config.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        # Force-load .env before anything else to guarantee env vars exist
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        _env_file = Path(__file__).resolve().parent / ".env"
        load_dotenv(_env_file, override=True)

        cfg = get_settings()

        # Strict fallback chain: explicit arg → GROQ_API_KEY → config
        self._api_key = (
            api_key
            or os.getenv("GROQ_API_KEY", "").strip()
            or cfg.api_key
        )
        self._model_name = model_name or cfg.model_name
        self._temperature = cfg.temperature
        self._max_tokens = cfg.max_output_tokens

        # Instantiate the Groq client
        self._client = Groq(api_key=self._api_key)

        # Chat history for multi-turn conversations
        self._chat_history: list[dict[str, str]] = []

        # ── Case Memory ──────────────────────────────────────────────────
        # Each entry: {"label": str, "text": str, "added_at": float}
        self._memory: list[dict[str, Any]] = []

        logger.info(
            "ForensIQAgent initialised  model=%s  provider=groq",
            self._model_name,
        )

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------
    @property
    def memory(self) -> list[dict[str, Any]]:
        """Return a shallow copy of the case memory."""
        return list(self._memory)

    @property
    def memory_text(self) -> str:
        """
        Compile all documents in memory into a single labelled text block
        suitable for insertion into a prompt template.
        """
        if not self._memory:
            return "(No case documents loaded.)"

        sections = []
        for idx, doc in enumerate(self._memory, 1):
            sections.append(
                f"--- Document {idx}: {doc['label']} ---\n{doc['text']}"
            )
        return "\n\n".join(sections)

    def add_document(self, label: str, text: str) -> None:
        """
        Add a new document to the case memory.

        Parameters
        ----------
        label : str
            A human-readable label, e.g. "Suspect A – Statement 1".
        text : str
            The full text content of the document.
        """
        if not text or not text.strip():
            logger.warning("Attempted to add empty document '%s' – skipped.", label)
            return

        self._memory.append(
            {
                "label": label.strip(),
                "text": text.strip(),
                "added_at": time.time(),
            }
        )
        logger.info("Document added to memory: '%s' (%d chars)", label, len(text))

    def clear_memory(self) -> None:
        """Remove all documents from the case memory."""
        self._memory.clear()
        self._chat_history.clear()
        logger.info("Case memory cleared.")

    def remove_document(self, index: int) -> None:
        """
        Remove a document from memory by its 0-based index.

        Parameters
        ----------
        index : int
            The index of the document to remove.
        """
        if 0 <= index < len(self._memory):
            removed = self._memory.pop(index)
            logger.info("Document removed: '%s'", removed["label"])
        else:
            logger.warning("Invalid document index: %d", index)

    # ------------------------------------------------------------------
    # Private – call the LLM and parse JSON
    # ------------------------------------------------------------------
    def _call_llm(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        """
        Send *prompt* to Groq and return the raw text response.

        Parameters
        ----------
        prompt : str
            The user message / full prompt to send.
        system_prompt : str
            The system instruction for this call.

        Raises
        ------
        RuntimeError
            If the API call fails for any reason.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            choice = response.choices[0]
            if choice.finish_reason == "content_filter":
                raise RuntimeError(
                    "The model's response was blocked by content filters."
                )

            return choice.message.content

        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            raise RuntimeError(f"LLM API error: {exc}") from exc

    def _analyse(self, prompt_template: str) -> list | dict:
        """
        Core analysis pipeline:
            1. Build the full prompt by injecting case memory.
            2. Call the LLM.
            3. Parse the JSON response.
            4. Return structured data or an error dict.

        Parameters
        ----------
        prompt_template : str
            One of the module prompt templates from ``prompts.py``.

        Returns
        -------
        list | dict
            Parsed JSON on success, or ``{"error": "<message>"}`` on
            failure.
        """
        if not self._memory:
            return {"error": "No case documents in memory.  Please add at least one document before running analysis."}

        full_prompt = prompt_template.format(case_documents=self.memory_text)

        try:
            raw_response = self._call_llm(full_prompt)
        except RuntimeError as exc:
            return {"error": str(exc)}

        try:
            parsed = _safe_parse_json(raw_response)
            return parsed
        except json.JSONDecodeError as exc:
            logger.error(
                "JSON parse error: %s\nRaw response (first 500 chars): %s",
                exc,
                raw_response[:500],
            )
            return {
                "error": (
                    "The AI returned a response that could not be parsed as "
                    "valid JSON.  Please try again.  If the problem persists, "
                    "try rephrasing or simplifying the case documents."
                ),
                "raw_response": raw_response[:2000],
            }

    # ------------------------------------------------------------------
    # Public – the four analytical modules
    # ------------------------------------------------------------------
    def detect_contradictions(self) -> list | dict:
        """
        **Module 1 – Contradiction Detector**

        Cross-references all statements in case memory and flags logical
        inconsistencies.

        Returns
        -------
        list[dict]
            Each dict contains ``statement_1``, ``statement_2``, and
            ``explanation_of_conflict``.  Returns ``{"error": ...}`` on
            failure.
        """
        return self._analyse(CONTRADICTION_PROMPT)

    def build_timeline(self) -> list | dict:
        """
        **Module 2 – Timeline Constructor**

        Extracts temporal data from case memory and assembles a
        chronologically sorted sequence of events.

        Returns
        -------
        list[dict]
            Each dict contains ``timestamp``, ``event_description``,
            ``source``, and ``confidence_level``.  Returns
            ``{"error": ...}`` on failure.
        """
        return self._analyse(TIMELINE_PROMPT)

    def profile_suspects(self) -> list | dict:
        """
        **Module 3 – Suspect Profiler**

        Builds a comprehensive profile card for every named individual
        mentioned in the case documents.

        Returns
        -------
        list[dict]
            Each dict contains ``name``, ``role_in_case``,
            ``known_associations``, ``key_statements``,
            ``potential_motives``, ``behavioral_flags``, and
            ``timeline_presence``.  Returns ``{"error": ...}`` on failure.
        """
        return self._analyse(PROFILER_PROMPT)

    def generate_next_questions(self) -> list | dict:
        """
        **Module 4 – Next-Question Generator**

        Analyses current case context and suggests the most critical
        follow-up questions for the investigator.

        Returns
        -------
        list[dict]
            Each dict contains ``target_person``, ``suggested_question``,
            ``reasoning``, ``investigative_value``, and ``priority_rank``.
            Returns ``{"error": ...}`` on failure.
        """
        return self._analyse(NEXT_QUESTION_PROMPT)

    # ------------------------------------------------------------------
    # Conversational chat
    # ------------------------------------------------------------------
    def chat(self, user_message: str) -> str:
        """
        Send a free-form message to the agent in the context of the
        current case.  Maintains a multi-turn chat session.

        Parameters
        ----------
        user_message : str
            The investigator's message / question.

        Returns
        -------
        str
            The agent's natural-language response.
        """
        if not user_message or not user_message.strip():
            return "Please enter a message."

        try:
            chat_system = CHAT_SYSTEM_PROMPT.format(
                case_context=self.memory_text
            )

            # Build messages list: system + history + new user message
            messages = [{"role": "system", "content": chat_system}]
            messages.extend(self._chat_history)
            messages.append({"role": "user", "content": user_message})

            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=0.4,
                max_tokens=self._max_tokens,
            )

            reply = response.choices[0].message.content

            # Append to history for multi-turn
            self._chat_history.append({"role": "user", "content": user_message})
            self._chat_history.append({"role": "assistant", "content": reply})

            return reply

        except Exception as exc:
            logger.error("Chat call failed: %s", exc)
            return f"⚠️ An error occurred: {exc}"

    def reset_chat(self) -> None:
        """Clear the conversational chat history (keeps case memory)."""
        self._chat_history.clear()
        logger.info("Chat session reset.")

    # ------------------------------------------------------------------
    # Run all modules at once
    # ------------------------------------------------------------------
    def run_full_analysis(self) -> dict[str, Any]:
        """
        Execute all four analytical modules sequentially and return a
        consolidated report.

        Returns
        -------
        dict
            Keys: ``contradictions``, ``timeline``, ``profiles``,
            ``next_questions``.  Each value is the parsed JSON output
            (or an error dict) from the respective module.
        """
        return {
            "contradictions": self.detect_contradictions(),
            "timeline": self.build_timeline(),
            "profiles": self.profile_suspects(),
            "next_questions": self.generate_next_questions(),
        }
