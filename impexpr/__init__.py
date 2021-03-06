import argparse
import builtins
import importlib
import importlib.abc
import importlib.util
import sys
import typing as T
from pathlib import Path as P
from subprocess import run

from ideas import import_hook, main_hack

from .token_transformers import transform_source

__version__ = "0.0.5"
__all__ = ["main", "add_hook"]


def add_hook():
    """Creates and automatically adds the import hook in sys.meta_path"""
    builtins.importlib = importlib  # type: ignore
    hook = import_hook.create_hook(hook_name=__name__, transform_source=transform_source, first=True)
    return hook


def parse_argv(argv: T.List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pysh")
    parser.add_argument("script", help="The script to run", nargs="?", default=None)
    parser.add_argument("-v", "--version", help="Print the version and exit", action="store_true")
    parser.add_argument("-c", "--compile", help="Compile the script without running", action="store_true")
    parser.add_argument(
        "-b",
        "--black",
        help="Run black on the script after compiling it",
        action="store_true",
        default=True,
    )
    parser.add_argument("-o", "--output", help="The compilation output file/directory", default=None)
    return parser.parse_args(argv)


def main(argv: T.Optional[T.List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_argv(argv)

    if args.version:
        print(__version__)
        sys.exit(0)
    elif args.script is None:
        from ideas import console

        console.configure(transform_source=transform_source)
        console.start(
            prompt=">>> ",
            banner=f"Pysh Console [Python version: {sys.version}]",
            locals={"importlib": importlib},
        )
        exit(0)
    elif not P(args.script).is_file():
        print("Expecting a path to the script", file=sys.stderr)
        exit(1)
    elif args.compile:
        new_source = transform_source(P(args.script).read_text())
        new_source = "import importlib\n" + new_source
        if args.output is None:
            file = P(args.script)
        else:
            output = P(args.output)
            if output.is_dir():
                file = output / args.script
            else:
                file = output
        file.write_text(new_source)
        run([sys.executable, "-m", "black", "--target-version", "py37", "--line-length", "120", file])
    else:
        add_hook()
        if argv is sys.argv:
            argv[0] = argv.pop(1)

        module_name = args.script[: -len(".py")]
        main_hack.main_name = module_name
        module_path = P(args.script).resolve()
        sys.path.insert(0, str(module_path.parent))
        try:
            importlib.import_module(module_name)
        except Exception:
            import traceback

            exc = traceback.format_exc()
            seeked_str = f'  File "{module_path}"'
            if seeked_str in exc:
                exc = "Traceback (most recent call last):\n" + exc[exc.index(f'  File "{module_path}"') :]
                sys.stderr.write(exc)
                sys.exit(1)
            else:
                raise


if __name__ == "__main__":
    main()
