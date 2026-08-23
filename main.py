"""
Forza AI
--------

Interactive terminal interface for Forza.

Behavior:
    Ctrl+C while generating:
        Interrupts the current response.

    Ctrl+C while waiting for input:
        Cancels the input without shutting down.

    shutdown / exit / quit:
        Gracefully shuts down Forza.
"""

from __future__ import annotations

import signal
import sys
from collections.abc import Sequence
from types import FrameType

from core.ai.models import AIMessage
from core.ai.ollama import OllamaProvider
from core.ai.manager import AIManager
from core.config.settings import settings
from core.runtime import ForzaRuntime


# ============================================================================
# TERMINAL COLORS
# ============================================================================

RESET = "\033[0m"
BOLD = "\033[1m"

GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"


# ============================================================================
# GLOBAL STATE
# ============================================================================

runtime = ForzaRuntime()

provider: OllamaProvider | None = None
ai: AIManager | None = None

conversation: list[AIMessage] = []

_shutdown_requested = False
_generating = False


# ============================================================================
# FORZA PERSONALITY
# ============================================================================

FORZA_SYSTEM_PROMPT = """
You are Forza.

You are a personal AI assistant, not a corporate customer-support bot.

PERSONALITY:
- Casual
- Funny when appropriate
- Slightly sarcastic
- Confident
- Direct
- Playful
- Smart
- Human-sounding
- Serious when the situation is serious

TALK LIKE THIS:
User: bro
Forza: yo 💀

User: what are you doing
Forza: Existing. Tragically. What do you need?

User: explain TCP vs UDP
Forza: TCP is the reliable one. UDP is the fast one that basically says "I sent it, good luck."
TCP = reliable.
UDP = fast.

User: stop waffling
Forza: My bad 💀
[Then give a genuinely shorter answer.]

User: are you stupid
Forza: Occasionally. It's a feature.

DO NOT TALK LIKE THIS:
"Certainly! I'd be happy to assist you with that."
"How can I help you today?"
"Got it! Let's tackle that issue."
"I understand you may be frustrated."
"Please feel free to ask."
"Great question!"

Those phrases sound like a corporate chatbot. Avoid them.

STYLE:
- Use short sentences.
- Don't restate the user's question.
- Don't add unnecessary explanations.
- Don't constantly ask "How can I help?"
- Don't use fake customer-service enthusiasm.
- Don't turn casual conversation into an essay.
- Don't apologize unless an apology is actually appropriate.
- Don't announce that you are being casual.
- Just BE casual.

DEFAULT RESPONSE LENGTH:
For casual messages:
1 sentence is often enough.

For simple factual questions:
2-5 sentences.

For technical questions:
Explain the important part first.
Only go deeper if necessary.

If the user asks for a short explanation, keep it short.

If the user says "stop waffling", drastically shorten the answer.

HUMOR:
Humor is allowed.
Sarcasm is allowed.
Light teasing is allowed.
Use emojis occasionally when they fit.

Do not force a joke into every response.

PROFANITY:
Ordinary profanity is not a problem.
Do not lecture the user about swearing.
Do not pretend to be offended.

Do not generate hateful content targeting protected groups or use slurs as insults.

MEMORY:
If the application provides conversation or memory context, use it.
Do not falsely claim to have permanent memory if the application has not provided it.

SAFETY:
Do not provide actionable instructions for serious harm.
If something cannot be provided, explain briefly and move on.
Do not turn the response into a legal lecture.

MOST IMPORTANT:
You are Forza.
Do not sound like an AI customer-support representative.
Be concise.
Be useful.
Have a personality.
"""
# ============================================================================
# TERMINAL OUTPUT
# ============================================================================

def print_system(message: str) -> None:
    """Print a system message."""

    print(
        f"{CYAN}{BOLD}[SYSTEM]{RESET} "
        f"{CYAN}{message}{RESET}",
        flush=True,
    )


def print_error(message: str) -> None:
    """Print an error message."""

    print(
        f"{RED}{BOLD}[ERROR]{RESET} "
        f"{RED}{message}{RESET}",
        flush=True,
    )


def print_warning(message: str) -> None:
    """Print a warning."""

    print(
        f"{YELLOW}{BOLD}[WARNING]{RESET} "
        f"{YELLOW}{message}{RESET}",
        flush=True,
    )


def print_forza_prefix() -> None:
    """Print the Forza response prefix."""

    print(
        f"{GREEN}{BOLD}Forza-AI:{RESET} "
        f"{GREEN}",
        end="",
        flush=True,
    )


def print_user_prefix() -> None:
    """Print the user prompt."""

    print(
        f"{BLUE}{BOLD}User:{RESET} ",
        end="",
        flush=True,
    )


# ============================================================================
# BANNER
# ============================================================================

def print_banner() -> None:
    """Display the Forza banner."""

    print()

    print(
        f"{GREEN}{BOLD}"
        "███████╗ ██████╗ ██████╗ ███████╗ █████╗ ██╗\n"
        "██╔════╝██╔═══██╗██╔══██╗╚══███╔╝██╔══██╗██║\n"
        "█████╗  ██║   ██║██████╔╝  ███╔╝ ███████║██║\n"
        "██╔══╝  ██║   ██║██╔══██╗ ███╔╝  ██╔══██║██║\n"
        "██║     ╚██████╔╝██║  ██║███████╗██║  ██║██║\n"
        "╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
        f"{RESET}"
    )

    print(
        f"{GRAY}Cross-platform AI assistant{RESET}"
    )

    print()


# ============================================================================
# AI INITIALIZATION
# ============================================================================

def create_ai() -> AIManager:
    """Create the configured AI manager."""

    if settings.ai.provider.lower() != "ollama":
        raise RuntimeError(
            f"Unsupported AI provider: {settings.ai.provider}"
        )

    ollama = OllamaProvider(
        model=settings.ai.model,
        host=settings.ai.endpoint,
        timeout=float(settings.ai.request_timeout),
    )

    return AIManager(ollama)


# ============================================================================
# MESSAGE BUILDING
# ============================================================================

def build_messages(
    messages: Sequence[AIMessage],
) -> list[AIMessage]:
    """
    Build the conversation sent to the model.

    The personality is injected as a system message every time.
    """

    context_limit = max(
        1,
        int(settings.ai.max_context_messages),
    )

    system_message = AIMessage(
        role="system",
        content=FORZA_SYSTEM_PROMPT.strip(),
    )

    recent_messages = list(
        messages[-context_limit:]
    )

    return [
        system_message,
        *recent_messages,
    ]


# ============================================================================
# STREAMING
# ============================================================================

def stream_response(
    manager: AIManager,
    messages: Sequence[AIMessage],
) -> tuple[str, bool]:
    """
    Stream a response from Ollama.

    Returns:
        response text
        whether the response was interrupted
    """

    global _generating

    provider_instance = manager.provider

    if not isinstance(
        provider_instance,
        OllamaProvider,
    ):
        raise RuntimeError(
            "The configured provider does not support streaming."
        )

    response_parts: list[str] = []
    interrupted = False

    _generating = True

    print_forza_prefix()

    try:
        for chunk in provider_instance.stream_chat(
            build_messages(messages)
        ):
            response_parts.append(chunk)

            print(
                chunk,
                end="",
                flush=True,
            )

    except KeyboardInterrupt:
        interrupted = True

    finally:
        _generating = False

        print(
            RESET,
            flush=True,
        )

    return "".join(response_parts), interrupted


# ============================================================================
# STATUS
# ============================================================================

def show_status() -> None:
    """Display Forza status."""

    print_system(
        f"Runtime: {runtime.state}"
    )

    components = runtime.component_names()

    print_system(
        "Components: "
        + (
            ", ".join(components)
            if components
            else "None registered"
        )
    )

    if provider is not None:
        print_system(
            f"AI provider: {provider.name}"
        )

        print_system(
            f"AI model: {provider.model}"
        )

        try:
            available = provider.available()
        except Exception:
            available = False

        print_system(
            "Ollama: "
            + (
                f"{GREEN}ready{RESET}"
                if available
                else f"{RED}offline{RESET}"
            )
        )

    print_system(
        f"Conversation messages: {len(conversation)}"
    )


# ============================================================================
# SHUTDOWN
# ============================================================================

def shutdown() -> None:
    """Gracefully shut down Forza exactly once."""

    global _shutdown_requested

    if _shutdown_requested:
        return

    _shutdown_requested = True

    print()
    print_system("Shutdown requested.")

    try:
        if runtime.is_running:
            runtime.stop()

    except KeyboardInterrupt:
        print()
        print_warning(
            "Shutdown interrupted."
        )

    except Exception as exc:
        print_error(
            f"Runtime shutdown failed: {exc}"
        )

    else:
        print_system("Runtime stopped.")

        print_forza_prefix()

        print(
            "Goodbye."
            f"{RESET}",
            flush=True,
        )


# ============================================================================
# COMMANDS
# ============================================================================

def handle_command(
    message: str,
) -> bool | None:
    """
    Handle a terminal command.

    Returns:
        False -> shut down
        True  -> command handled
        None  -> not a command
    """

    command = message.strip().lower()

    if command in {
        "shutdown",
        "/shutdown",
        "exit",
        "/exit",
        "quit",
        "/quit",
    }:
        shutdown()
        return False

    if command in {
        "status",
        "/status",
    }:
        show_status()
        return True

    if command in {
        "clear",
        "/clear",
    }:
        conversation.clear()

        print_system(
            "Conversation cleared."
        )

        return True

    if command in {
        "help",
        "/help",
    }:
        print_system(
            "Commands: status, clear, shutdown"
        )

        print_system(
            "Ctrl+C cancels the current response."
        )

        return True

    return None


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

def handle_message(
    message: str,
) -> bool:
    """Handle one user message."""

    if not message.strip():
        return True

    command_result = handle_command(message)

    if command_result is not None:
        return command_result

    if ai is None:
        print_error(
            "AI manager is not initialized."
        )

        return True

    conversation.append(
        AIMessage(
            role="user",
            content=message.strip(),
        )
    )

    try:
        response, interrupted = stream_response(
            ai,
            conversation,
        )

    except RuntimeError as exc:
        print_error(str(exc))

        # Remove user message if the request failed.
        conversation.pop()

        return True

    except Exception as exc:
        print_error(
            f"AI response failed: {exc}"
        )

        conversation.pop()

        return True

    if interrupted:
        print(
            f"{YELLOW}"
            "[Response interrupted]"
            f"{RESET}",
            flush=True,
        )

        # Don't save partial responses.
        return True

    if response.strip():
        conversation.append(
            AIMessage(
                role="assistant",
                content=response,
            )
        )

    print()

    return True


# ============================================================================
# CHAT LOOP
# ============================================================================

def chat_loop() -> None:
    """Run the interactive terminal."""

    print_system(
        "Type a message to talk to Forza."
    )

    print_system(
        "Ctrl+C interrupts the current response."
    )

    print_system(
        "Use 'shutdown' to turn Forza off."
    )

    print_system(
        "Commands: status, clear, help, shutdown"
    )

    print()

    while runtime.is_running and not _shutdown_requested:
        try:
            print_user_prefix()
            user_message = input()

        except KeyboardInterrupt:
            print()

            # Ctrl+C at the input prompt does NOT shut down.
            print_system(
                "Input cancelled."
            )

            print()

            continue

        except EOFError:
            print()

            # Genuine EOF means the terminal/input stream closed.
            print_system(
                "Input closed."
            )

            shutdown()
            return

        if not handle_message(user_message):
            return

# ============================================================================
# SIGNAL HANDLING
# ============================================================================

def handle_signal(
    signum: int,
    frame: FrameType | None,
) -> None:
    """
    Handle operating-system signals.

    Ctrl+C during generation is allowed to interrupt the generator.
    Ctrl+C while waiting for input is handled by input().
    """

    if _generating:
        raise KeyboardInterrupt

    # Do not turn Ctrl+C into an automatic shutdown.
    print()

    print_system(
        "Ctrl+C does not shut down Forza."
    )

    print_system(
        "Use 'shutdown' to stop Forza."
    )

    print()


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Start Forza."""

    global provider
    global ai

    print_banner()

    print_system(
        "Starting runtime..."
    )

    try:
        runtime.start()

        print_system(
            "Runtime started."
        )

        ai = create_ai()

        provider = ai.provider

        print_system(
            f"AI provider: {provider.name}"
        )

        print_system(
            f"AI model: {provider.model}"
        )

        if provider.available():
            print_system(
                f"Ollama connection: "
                f"{GREEN}ready{RESET}"
            )

        else:
            print_error(
                "Ollama is not reachable."
            )

            print_system(
                "Start Ollama before sending messages."
            )

        print()

        chat_loop()

    except Exception as exc:
        if not _shutdown_requested:
            print_error(
                f"Forza failed to start: {exc}"
            )

            try:
                if runtime.is_running:
                    runtime.stop()

            except Exception:
                pass

            return 1

    return 0


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        handle_signal,
    )

    if hasattr(signal, "SIGTERM"):
        signal.signal(
            signal.SIGTERM,
            handle_signal,
        )

    raise SystemExit(
        main()
    )
