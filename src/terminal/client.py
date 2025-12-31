"""Terminal client for hand-off mode.

Improved UI semantics for structured terminal hand-off:
- Structured header with invocation time + timeout countdown
- Always-on annotations (empty = no note)
- j/k navigation aliases; Tab accepts selection (jumps toward annotations)
- Settings entry to update config or switch this session to web
- Cancel path prompts for a global annotation
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

import httpx
import questionary
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from questionary import Choice, Style

# Section: Visual Styling
CUSTOM_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "fg:white bold"),
    ("answer", "fg:green bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:green"),
    ("separator", "fg:gray"),
    ("instruction", "fg:gray italic"),
    ("text", "fg:white"),
])


def _enhance_navigation(question: questionary.Question) -> questionary.Question:
    """Add j/k navigation and Tab-to-accept bindings to a questionary prompt."""
    kb = question.application.key_bindings

    @kb.add("j")
    def _(event) -> None:  # noqa: ANN001
        event.app.key_processor.feed(KeyPress(Keys.Down))

    @kb.add("k")
    def _(event) -> None:  # noqa: ANN001
        event.app.key_processor.feed(KeyPress(Keys.Up))

    @kb.add("tab")
    def _(event) -> None:  # noqa: ANN001
        event.app.key_processor.feed(KeyPress(Keys.Enter))

    return question


def _print_header(title: str, prompt: str, timeout_seconds: int, remaining_seconds: float, started_at: Optional[float]) -> None:
    """Print a styled header with title, prompt, invocation time, and timeout info."""
    width = max(len(title), len(prompt), 60)
    border = "─" * width
    started_label = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at)) if started_at else "unknown"
    remaining_display = f"{int(remaining_seconds)}s" if remaining_seconds >= 0 else "n/a"

    print()
    print(f"┌{border}┐")
    print(f"│ \033[1;36m{title.center(width - 2)}\033[0m │")
    print(f"├{border}┤")
    print(f"│ {prompt.ljust(width - 2)} │")
    print(f"├{border}┤")
    print(f"│ Started: {started_label.ljust(width - 11)}│")
    print(f"│ Timeout: {str(timeout_seconds).ljust(8)} Remaining: {remaining_display.ljust(width - 29)}│")
    print(f"└{border}┘")
    print()


def _print_options_preview(options: list[dict]) -> None:
    """Print a preview of options with their descriptions."""
    print("\033[90m选项说明:\033[0m")
    for opt in options:
        opt_id = opt.get("id", "")
        desc = opt.get("description", "")
        recommended = opt.get("recommended", False)
        marker = " \033[32m★\033[0m" if recommended else ""
        print(f"  • \033[1m{opt_id}\033[0m{marker}")
        if desc:
            print(f"    \033[90m{desc}\033[0m")
    print()


def _build_choice_label(opt: dict) -> str:
    opt_id = opt.get("id", "")
    recommended = opt.get("recommended", False)
    if recommended:
        return f"★ {opt_id} (推荐)"
    return opt_id


def _prompt_additional_annotation() -> Optional[str]:
    try:
        note = questionary.text(
            "全局备注 (可选):",
            default="",
            style=CUSTOM_STYLE,
        ).unsafe_ask()
        return note.strip() or None if note else None
    except Exception:
        return None


def _update_settings(base_url: str, session_id: str, current_timeout: int) -> None:
    """Open a settings menu to update timeout/interface and persist via server."""
    try:
        new_timeout = questionary.text(
            "设置超时时间 (秒)",
            default=str(current_timeout),
            style=CUSTOM_STYLE,
        ).unsafe_ask()
        timeout_val = int(new_timeout) if new_timeout else current_timeout
    except Exception:
        timeout_val = current_timeout

    try:
        transport_choice = _enhance_navigation(
            questionary.select(
                "选择交互方式",
                choices=[Choice("terminal", "terminal"), Choice("web", "web")],
                default="terminal",
                style=CUSTOM_STYLE,
                instruction="",
            )
        ).unsafe_ask()
    except Exception:
        transport_choice = "terminal"

    payload = {
        "action_status": "update_settings",
        "config": {
            "timeout_seconds": timeout_val,
            "interface": transport_choice,
        },
    }
    try:
        resp = httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
        if resp.status_code == 200:
            print("\033[32m✓ 设置已更新并已持久化\033[0m")
        else:
            print(f"\033[33m⚠ 设置更新返回 {resp.status_code}\033[0m")
    except Exception as exc:  # noqa: BLE001
        print(f"\033[33m⚠ 设置更新失败: {exc}\033[0m")


def _switch_to_web(base_url: str, session_id: str, timeout_seconds: int) -> None:
    payload = {
        "action_status": "switch_to_web",
        "config": {
            "timeout_seconds": timeout_seconds,
        },
    }
    try:
        resp = httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        web_url = data.get("web_url")
        if web_url:
            # Output a special marker that the agent can parse
            # This tells the agent to use poll_selection to get the result
            print("\n\033[36m↗ Switched to Web interface\033[0m")
            print(f"URL: {web_url}")
            print(f"[SWITCH_TO_WEB] session_id={session_id}")
        else:
            print("\033[33m⚠ Web URL not available, please retry\033[0m")
    except Exception as exc:  # noqa: BLE001
        print(f"\033[31m✗ Failed to switch to Web: {exc}\033[0m")


def _submit_result(
    base_url: str,
    session_id: str,
    selected: list[str],
    option_annotations: dict[str, str],
    additional_annotation: Optional[str],
) -> None:
    payload = {
        "action_status": "selected",
        "selected_indices": selected,
        "option_annotations": option_annotations,
        "additional_annotation": additional_annotation,
    }
    try:
        httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
    except httpx.RequestError:
        pass


def _submit_cancelled(
    base_url: str,
    session_id: str,
    additional_annotation: Optional[str] = None,
) -> None:
    payload = {
        "action_status": "cancelled",
        "additional_annotation": additional_annotation,
    }
    try:
        httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
    except httpx.RequestError:
        pass


def _handle_cancel(base_url: str, session_id: str) -> int:
    additional_annotation = _prompt_additional_annotation()
    _submit_cancelled(base_url, session_id, additional_annotation)
    print("\n\033[33m⚠ Cancelled\033[0m")
    # Output a structured marker - only include additional_annotation if non-empty
    if additional_annotation:
        print(f"[CANCELLED] additional_annotation={additional_annotation}")
    else:
        print("[CANCELLED]")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive Choice Terminal Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Keyboard shortcuts:
  ↑/↓ or j/k  Navigate options
  Enter        Select/Confirm
  Space        Toggle (multi-select)
  Tab          快速进入注释
  Ctrl+C       Cancel (会请求全局备注)
        """
    )
    parser.add_argument("--session", "-s", required=True, help="Session ID to attach to")
    parser.add_argument("--url", "-u", required=True, help="Server base URL")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output (no descriptions preview)")
    args = parser.parse_args()

    session_id: str = args.session
    base_url: str = args.url.rstrip("/")
    quiet_mode: bool = args.quiet

    try:
        resp = httpx.get(f"{base_url}/terminal/{session_id}", timeout=10)
        if resp.status_code == 404:
            print("\033[31m✗ Error:\033[0m Session not found or expired.", file=sys.stderr)
            print("  The session may have timed out. Please request a new one.", file=sys.stderr)
            return 1
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        print(f"\033[31m✗ Error:\033[0m Server returned {e.response.status_code}", file=sys.stderr)
        return 1
    except httpx.RequestError as e:
        print(f"\033[31m✗ Error:\033[0m Could not connect to server", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"\033[31m✗ Error:\033[0m {e}", file=sys.stderr)
        return 1

    if data.get("status") == "completed":
        result = data.get("result", {})
        action = result.get("action_status", "unknown")
        selected = result.get("selected_indices", [])
        print(f"\033[33m⚠ Session already completed:\033[0m {action}")
        if selected:
            print(f"  Selected: {selected}")
        return 0

    request = data.get("request", {})
    title = request.get("title", "Choice")
    prompt = request.get("prompt", "Select an option")
    selection_mode = request.get("selection_mode", "single")
    options = request.get("options", [])
    config = data.get("config", {})
    timeout_seconds = config.get("timeout_seconds", 300)
    remaining_seconds = data.get("remaining_seconds", timeout_seconds)
    started_at = data.get("started_at")

    if not options:
        print("\033[31m✗ Error:\033[0m No options available.", file=sys.stderr)
        return 1

    _print_header(title, prompt, timeout_seconds, remaining_seconds, started_at)
    if not quiet_mode:
        _print_options_preview(options)

    choices = [
        Choice(title=_build_choice_label(opt), value=opt.get("id", ""))
        for opt in options
    ]

    def select_flow() -> Optional[int]:
        try:
            if selection_mode == "single":
                default_val = None
                if config.get("use_default_option"):
                    for opt in options:
                        if opt.get("recommended"):
                            default_val = opt.get("id")
                            break

                prompt_obj = _enhance_navigation(
                    questionary.select(
                        "请选择:",
                        choices=choices,
                        default=default_val,
                        style=CUSTOM_STYLE,
                        instruction="",
                    )
                )
                answer = prompt_obj.unsafe_ask()
                if answer is None:
                    return _handle_cancel(base_url, session_id)
                selected = [answer]
            else:
                default_checked = []
                if config.get("use_default_option"):
                    default_checked = [opt.get("id") for opt in options if opt.get("recommended")]
                prompt_obj = _enhance_navigation(
                    questionary.checkbox(
                        "请选择 (可多选):",
                        choices=[
                            Choice(
                                title=_build_choice_label(opt),
                                value=opt.get("id", ""),
                                checked=opt.get("id", "") in default_checked,
                            )
                            for opt in options
                        ],
                        style=CUSTOM_STYLE,
                        instruction="",
                    )
                )
                answer = prompt_obj.unsafe_ask()
                if answer is None:
                    return _handle_cancel(base_url, session_id)
                selected = answer

            option_annotations: dict[str, str] = {}
            print("\n\033[90m--- 选项备注 (空输入视为无备注) ---\033[0m")
            for opt_id in selected:
                note = questionary.text(
                    f"备注 [{opt_id}]:",
                    default="",
                    style=CUSTOM_STYLE,
                ).unsafe_ask()
                if note and note.strip():
                    option_annotations[opt_id] = note.strip()

            additional_annotation = questionary.text(
                "全局备注 (可选):",
                default="",
                style=CUSTOM_STYLE,
            ).unsafe_ask()
            if additional_annotation:
                additional_annotation = additional_annotation.strip() or None

            _submit_result(base_url, session_id, selected, option_annotations, additional_annotation)
            print()
            print(f"\033[32m✓ Selection submitted:\033[0m {selected}")
            if option_annotations:
                print(f"  Annotations: {option_annotations}")
            if additional_annotation:
                print(f"  Global note: {additional_annotation}")
            # Output a structured marker that the agent can parse
            # Only include non-empty fields
            marker_parts = [f"selected={','.join(selected)}"]
            if option_annotations:
                marker_parts.append(f"annotations={json.dumps(option_annotations)}")
            if additional_annotation:
                marker_parts.append(f"additional_annotation={additional_annotation}")
            print(f"[SELECTION_COMPLETE] {' '.join(marker_parts)}")
            print()
            return 0

        except (KeyboardInterrupt, EOFError):
            return _handle_cancel(base_url, session_id)
        except Exception as exc:  # noqa: BLE001
            print(f"\n\033[31m✗ Error:\033[0m {exc}", file=sys.stderr)
            return _handle_cancel(base_url, session_id)

    while True:
        try:
            action = _enhance_navigation(
                questionary.select(
                    "选择操作:",
                    choices=[
                        Choice("开始选择", "select"),
                        Choice("⚙ 设置", "settings"),
                        Choice("↗ 切换到 Web", "switch_web"),
                        Choice("取消", "cancel"),
                    ],
                    style=CUSTOM_STYLE,
                    instruction="",
                )
            ).unsafe_ask()
        except (KeyboardInterrupt, EOFError):
            return _handle_cancel(base_url, session_id)

        if action == "select":
            result = select_flow()
            if result is not None:
                return result
        elif action == "settings":
            _update_settings(base_url, session_id, timeout_seconds)
        elif action == "switch_web":
            _switch_to_web(base_url, session_id, timeout_seconds)
            return 0
        elif action == "cancel":
            return _handle_cancel(base_url, session_id)


if __name__ == "__main__":
    sys.exit(main())
