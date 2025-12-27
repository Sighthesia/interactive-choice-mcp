"""Terminal client for hand-off mode.

This module provides the CLI entrypoint that the agent runs after receiving
a `pending_terminal_launch` response. It fetches the session from the server,
renders the questionary UI, and posts the result back.
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

import httpx
import questionary


def main() -> int:
    """Main entrypoint for the terminal client."""
    parser = argparse.ArgumentParser(description="Interactive Choice Terminal Client")
    parser.add_argument("--session", required=True, help="Session ID to attach to")
    parser.add_argument("--url", required=True, help="Server base URL")
    args = parser.parse_args()

    session_id: str = args.session
    base_url: str = args.url.rstrip("/")

    # Fetch session info
    try:
        resp = httpx.get(f"{base_url}/terminal/{session_id}", timeout=10)
        if resp.status_code == 404:
            print("Error: Session not found or expired.", file=sys.stderr)
            return 1
        try:
            resp.raise_for_status()
        except Exception as e:  # Catch HTTPStatusError and similar
            print(f"Error: Server returned an error: {e}", file=sys.stderr)
            return 1
        try:
            data = resp.json()
        except Exception as e:
            print(f"Error: Invalid JSON response: {e}", file=sys.stderr)
            return 1
    except httpx.RequestError as e:
        print(f"Error: Could not connect to server: {e}", file=sys.stderr)
        return 1

    if data.get("status") == "completed":
        print("Session already completed.")
        result = data.get("result", {})
        print(f"Result: {result.get('action_status')} - {result.get('summary', '')}")
        return 0

    # Extract request info
    request = data.get("request", {})
    title = request.get("title", "Choice")
    prompt = request.get("prompt", "Select an option")
    selection_mode = request.get("selection_mode", "single")
    options = request.get("options", [])
    config = data.get("config", {})

    if not options:
        print("Error: No options available.", file=sys.stderr)
        return 1

    # Build choices
    choices = []
    for opt in options:
        opt_id = opt.get("id", "")
        desc = opt.get("description", "")
        recommended = opt.get("recommended", False)
        label = f"{opt_id} (推荐)" if recommended else opt_id
        choices.append(questionary.Choice(title=label, value=opt_id))

    # Show prompt
    print(f"\n{title}")
    print("-" * len(title))

    try:
        if selection_mode == "single":
            # Find default if use_default_option is enabled
            default_val = None
            if config.get("use_default_option"):
                for opt in options:
                    if opt.get("recommended"):
                        default_val = opt.get("id")
                        break
            answer = questionary.select(prompt, choices=choices, default=default_val).unsafe_ask()
            if answer is None:
                _submit_cancelled(base_url, session_id)
                return 0
            selected = [answer]
        else:
            # Multi-select mode
            default_checked = []
            if config.get("use_default_option"):
                default_checked = [opt.get("id") for opt in options if opt.get("recommended")]
            multi_choices = [
                questionary.Choice(
                    title=f"{opt.get('id')} (推荐)" if opt.get("recommended") else opt.get("id"),
                    value=opt.get("id"),
                    checked=opt.get("id") in default_checked
                )
                for opt in options
            ]
            answer = questionary.checkbox(prompt, choices=multi_choices).unsafe_ask()
            if answer is None:
                _submit_cancelled(base_url, session_id)
                return 0
            selected = answer

        # Collect optional annotations
        option_annotations = {}
        for opt_id in selected:
            try:
                note = questionary.text(f"Note for '{opt_id}' (optional)", default="").unsafe_ask()
                if note:
                    option_annotations[opt_id] = note
            except (KeyboardInterrupt, EOFError):
                _submit_cancelled(base_url, session_id)
                return 0

        global_annotation = None
        try:
            global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask()
        except (KeyboardInterrupt, EOFError):
            _submit_cancelled(base_url, session_id)
            return 0

        # Submit result
        _submit_result(base_url, session_id, selected, option_annotations, global_annotation)
        print(f"\n✓ Selection submitted: {selected}")
        return 0

    except (KeyboardInterrupt, EOFError):
        _submit_cancelled(base_url, session_id)
        print("\nCancelled.")
        return 0


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
