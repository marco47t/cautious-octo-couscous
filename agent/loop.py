import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator
from google.genai import types
from utils.logger import logger

MAX_STEPS = 10          # hard ceiling on iterations
MAX_RETRIES = 3         # retries per failed step


@dataclass
class StepResult:
    step: int
    tool_calls: list[str] = field(default_factory=list)
    tool_errors: list[str] = field(default_factory=list)
    text: str = ""
    done: bool = False


async def run_agentic_loop(
    session,
    message: str,
    user_id: int,
    on_step: callable = None,           # optional callback for live step updates
) -> AsyncGenerator[str, None]:
    """
    Run a multi-step agentic loop.
    Yields status updates as the agent works through a problem.
    """
    current_input = message
    steps_taken = 0
    all_errors = []
    plan_shown = False

    while steps_taken < MAX_STEPS:
        steps_taken += 1
        logger.info(f"[loop:{user_id}] ── STEP {steps_taken} ──────────────────────")

        # ── Execute one round ───────────────────────────────────────────
        result = await _execute_step(session, current_input, user_id, steps_taken)

        # ── Notify caller of progress ───────────────────────────────────
        if on_step and result.tool_calls:
            for call in result.tool_calls:
                yield f"🔧 <i>{call}</i>"

        # ── Collect errors for self-correction ─────────────────────────
        if result.tool_errors:
            all_errors.extend(result.tool_errors)
            logger.warning(f"[loop:{user_id}] Step {steps_taken} errors: {result.tool_errors}")

        # ── Agent decided it's done ─────────────────────────────────────
        if result.done:
            logger.info(f"[loop:{user_id}] Agent finished in {steps_taken} steps")
            yield result.text
            return

        # ── No tool calls — agent gave a text response ──────────────────
        if not result.tool_calls:
            # Check if it's a plan (contains numbered steps)
            if _looks_like_plan(result.text) and not plan_shown:
                plan_shown = True
                yield f"📋 <b>Plan:</b>\n{result.text}\n\n<i>Executing...</i>"
                current_input = "Proceed with the plan above step by step."
                continue

            # Final answer
            yield result.text
            return

        # ── Self-correction: if errors, inject feedback ─────────────────
        if result.tool_errors:
            error_summary = "\n".join(result.tool_errors[-3:])   # last 3 errors
            current_input = (
                f"The previous step had errors:\n{error_summary}\n\n"
                f"Diagnose the issue and try a different approach."
            )
        else:
            current_input = ""   # Gemini handles tool results internally

    # Hit MAX_STEPS
    logger.warning(f"[loop:{user_id}] Hit MAX_STEPS ({MAX_STEPS})")
    yield (
        f"⚠️ Reached maximum steps ({MAX_STEPS}). "
        f"Here's what was accomplished:\n\n{result.text or 'No final output.'}"
    )


async def _execute_step(session, message: str, user_id: int, step: int) -> StepResult:
    """Execute one step — send message, collect tool calls and response."""
    result = StepResult(step=step)
    retries = 0

    while retries < MAX_RETRIES:
        try:
            response = await asyncio.to_thread(
                session.send_message, message
            ) if message else await asyncio.to_thread(
                session.send_message, " "   # nudge for continuation
            )

            # Parse tool calls and errors
            for candidate in (response.candidates or []):
                for part in (candidate.content.parts or []):
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        call_str = f"{fc.name}({_fmt_args(dict(fc.args))})"
                        result.tool_calls.append(call_str)
                        logger.info(f"[loop:{user_id}] TOOL → {call_str}")

                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        resp_str = str(fr.response)
                        logger.debug(f"[loop:{user_id}] RESULT ← {fr.name}: {resp_str[:200]}")

                        # Detect errors in tool responses
                        if _is_error(resp_str):
                            result.tool_errors.append(f"{fr.name}: {resp_str[:300]}")

            try:
                result.text = response.text or ""
            except Exception:
                result.text = ""

            # Decide if done
            result.done = (
                not result.tool_calls and
                bool(result.text) and
                not _needs_continuation(result.text)
            )

            return result

        except Exception as e:
            retries += 1
            logger.error(f"[loop:{user_id}] Step {step} error (retry {retries}): {e}")
            if retries >= MAX_RETRIES:
                result.text = f"❌ Step failed after {MAX_RETRIES} retries: {e}"
                result.done = True
                return result
            await asyncio.sleep(1)

    return result


def _looks_like_plan(text: str) -> bool:
    import re
    return bool(re.search(r"^\s*\d+[\.\)]\s+\w", text, re.MULTILINE))


def _needs_continuation(text: str) -> bool:
    continuation_phrases = [
        "let me", "i will", "i'll", "next i", "now i",
        "proceeding", "continuing", "working on"
    ]
    return any(p in text.lower() for p in continuation_phrases)


def _is_error(response_str: str) -> bool:
    error_indicators = ["error:", "❌", "exception", "traceback", "failed", "not found"]
    return any(e in response_str.lower() for e in error_indicators)


def _fmt_args(args: dict) -> str:
    if not args:
        return ""
    items = []
    for k, v in list(args.items())[:3]:
        v_str = str(v)[:50]
        items.append(f"{k}={v_str!r}" if len(v_str) < 50 else f"{k}=...")
    return ", ".join(items)
