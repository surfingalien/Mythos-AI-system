"""Entry point: python -m mythos [--gui | --headless | --web | --text]."""

from __future__ import annotations

import argparse
import asyncio

from mythos import __version__
from mythos.config import config


def _run_text_repl() -> None:
    """Type-only REPL — test the brain with no audio hardware at all."""
    from mythos.llm import Brain

    brain = Brain(config)
    print(f"{config.assistant_name} text console (v{__version__}). "
          "Ctrl-D or 'quit' to exit.")

    async def repl() -> None:
        while True:
            try:
                text = await asyncio.to_thread(input, "You: ")
            except (EOFError, KeyboardInterrupt):
                break
            text = text.strip()
            if not text:
                continue
            if text.lower() in ("quit", "exit"):
                break
            print(f"{config.assistant_name}: ", end="", flush=True)
            async for sentence in brain.respond_stream(text):
                print(sentence, end=" ", flush=True)
            print()

    asyncio.run(repl())


def _run_headless() -> None:
    """Voice pipeline without any GUI (e.g. on a Raspberry Pi)."""
    from mythos.core.pipeline import Pipeline

    pipeline = Pipeline(config)
    try:
        asyncio.run(pipeline.run())
    except KeyboardInterrupt:
        pipeline.request_stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mythos", description="Mythos AI voice assistant")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true",
                      help="desktop GUI (default)")
    mode.add_argument("--headless", action="store_true",
                      help="voice pipeline without a GUI")
    mode.add_argument("--web", action="store_true",
                      help="web chat UI (needs fastapi + uvicorn)")
    mode.add_argument("--text", action="store_true",
                      help="text-only REPL, no audio needed")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.text:
        _run_text_repl()
    elif args.headless:
        _run_headless()
    elif args.web:
        from mythos.ui.web import main as web_main

        web_main()
    else:
        from mythos.ui.gui import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
