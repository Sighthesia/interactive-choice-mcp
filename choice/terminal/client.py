"""Terminal client for hand-off mode.

This module provides the CLI entrypoint that the agent runs after receiving
a `pending_terminal_launch` response. It fetches the session from the server,
renders an improved questionary UI, and posts the result back.

Key improvements over the original:
- Clear visual structure with title, descriptions, and timeout display
- Simplified annotation workflow (skipped by default, use --annotate to enable)
- Better error messages and status feedback
- Keyboard navigation hints
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

import httpx
import questionary
from questionary import Style


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


def _print_header(title: str, prompt: str, timeout_seconds: int) -> None:
    """Print a styled header with title, prompt, and timeout info."""
    width = max(len(title), len(prompt), 50)
    border = "─" * width
    
    print()
    print(f"┌{border}┐")
    print(f"│ \033[1;36m{title.center(width - 2)}\033[0m │")
    print(f"├{border}┤")
    print(f"│ {prompt.ljust(width - 2)} │")
    print(f"├{border}┤")
    print(f"│ \033[33m⏱ Timeout: {timeout_seconds}s\033[0m".ljust(width + 9) + " │")
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
    """Build a display label for an option."""
    opt_id = opt.get("id", "")
    recommended = opt.get("recommended", False)
    if recommended:
        return f"★ {opt_id} (推荐)"
    return opt_id


def main() -> int:
    """Main entrypoint for the terminal client."""
    parser = argparse.ArgumentParser(
        description="Interactive Choice Terminal Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --session abc123 --url http://127.0.0.1:17863
  %(prog)s --session abc123 --url http://127.0.0.1:17863 --annotate

Keyboard shortcuts:
  ↑/↓   Navigate options
  Enter Select/Confirm
  Space Toggle (multi-select)
  Ctrl+C Cancel
        """
    )
    parser.add_argument("--session", "-s", required=True, help="Session ID to attach to")
    parser.add_argument("--url", "-u", required=True, help="Server base URL")
    parser.add_argument("--annotate", "-a", action="store_true", 
                        help="Enable annotation prompts for selections")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Minimal output (no descriptions preview)")
    args = parser.parse_args()

    session_id: str = args.session
    base_url: str = args.url.rstrip("/")
    enable_annotations: bool = args.annotate
    quiet_mode: bool = args.quiet

    # Section: Fetch Session
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
    except Exception as e:
        print(f"\033[31m✗ Error:\033[0m {e}", file=sys.stderr)
        return 1

    # Section: Handle Completed Session
    if data.get("status") == "completed":
        result = data.get("result", {})
        action = result.get("action_status", "unknown")
        selected = result.get("selected_indices", [])
        print(f"\033[33m⚠ Session already completed:\033[0m {action}")
        if selected:
            print(f"  Selected: {selected}")
        return 0

    # Section: Parse Session Data
    request = data.get("request", {})
    title = request.get("title", "Choice")
    prompt = request.get("prompt", "Select an option")
    selection_mode = request.get("selection_mode", "single")
    options = request.get("options", [])
    config = data.get("config", {})
    timeout_seconds = config.get("timeout_seconds", 300)

    if not options:
        print("\033[31m✗ Error:\033[0m No options available.", file=sys.stderr)
        return 1

    # Section: Display Header
    _print_header(title, prompt, timeout_seconds)
    
    if not quiet_mode:
        _print_options_preview(options)

    # Section: Build Choices
    choices = [
        questionary.Choice(title=_build_choice_label(opt), value=opt.get("id", ""))
        for opt in options
    ]

    # Section: Interactive Selection
    try:
        if selection_mode == "single":
            # Find default selection
            default_val = None
            if config.get("use_default_option"):
                for opt in options:
                    if opt.get("recommended"):
                        default_val = opt.get("id")
                        break

            print("\033[90m使用 ↑/↓ 导航, Enter 确认, Ctrl+C 取消\033[0m\n")
            answer = questionary.select(
                "请选择:",
                choices=choices,
                default=default_val,
                style=CUSTOM_STYLE,
                instruction="",
            ).unsafe_ask()

            if answer is None:
                _submit_cancelled(base_url, session_id)
                print("\n\033[33m⚠ Cancelled\033[0m")
                return 0
            selected = [answer]

        else:
            # Multi-select mode
            default_checked = []
            if config.get("use_default_option"):
                default_checked = [opt.get("id") for opt in options if opt.get("recommended")]

            multi_choices = [
                questionary.Choice(
                    title=_build_choice_label(opt),
                    value=opt.get("id", ""),
                    checked=opt.get("id", "") in default_checked
                )
                for opt in options
            ]

            print("\033[90m使用 ↑/↓ 导航, Space 切换选中, Enter 确认, Ctrl+C 取消\033[0m\n")
            answer = questionary.checkbox(
                "请选择 (可多选):",
                choices=multi_choices,
                style=CUSTOM_STYLE,
                instruction="",
            ).unsafe_ask()

            if answer is None:
                _submit_cancelled(base_url, session_id)
                print("\n\033[33m⚠ Cancelled\033[0m")
                return 0
            selected = answer

        # Section: Optional Annotations
        option_annotations: dict[str, str] = {}
        global_annotation: Optional[str] = None

        if enable_annotations and selected:
            print("\n\033[90m--- 添加备注 (可选, 直接 Enter 跳过) ---\033[0m")
            
            for opt_id in selected:
                try:
                    note = questionary.text(
                        f"备注 [{opt_id}]:",
                        default="",
                        style=CUSTOM_STYLE,
                    ).unsafe_ask()
                    if note and note.strip():
                        option_annotations[opt_id] = note.strip()
                except (KeyboardInterrupt, EOFError):
                    _submit_cancelled(base_url, session_id)
                    print("\n\033[33m⚠ Cancelled\033[0m")
                    return 0

            try:
                global_annotation = questionary.text(
                    "全局备注:",
                    default="",
                    style=CUSTOM_STYLE,
                ).unsafe_ask()
                if global_annotation:
                    global_annotation = global_annotation.strip() or None
            except (KeyboardInterrupt, EOFError):
                _submit_cancelled(base_url, session_id)
                print("\n\033[33m⚠ Cancelled\033[0m")
                return 0

        # Section: Submit Result
        _submit_result(base_url, session_id, selected, option_annotations, global_annotation)
        
        print()
        print(f"\033[32m✓ 选择已提交:\033[0m {selected}")
        if option_annotations:
            print(f"  备注: {option_annotations}")
        if global_annotation:
            print(f"  全局备注: {global_annotation}")
        print()
        return 0

    except (KeyboardInterrupt, EOFError):
        _submit_cancelled(base_url, session_id)
        print("\n\033[33m⚠ Cancelled\033[0m")
        return 0
    except Exception as e:
        print(f"\n\033[31m✗ Error:\033[0m {e}", file=sys.stderr)
        _submit_cancelled(base_url, session_id)
        return 1


def _submit_result(
    base_url: str,
    session_id: str,
    selected: list[str],
    option_annotations: dict[str, str],
    global_annotation: Optional[str],
) -> None:
    """Submit the selection result to the server."""
    payload = {
        "action_status": "selected",
        "selected_indices": selected,
        "option_annotations": option_annotations,
        "global_annotation": global_annotation,
    }
    try:
        httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
    except httpx.RequestError:
        pass


def _submit_cancelled(base_url: str, session_id: str) -> None:
    """Submit a cancellation to the server."""
    payload = {"action_status": "cancelled"}
    try:
        httpx.post(f"{base_url}/terminal/{session_id}/submit", json=payload, timeout=10)
    except httpx.RequestError:
        pass


if __name__ == "__main__":
    sys.exit(main())
