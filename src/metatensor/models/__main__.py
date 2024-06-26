"""The main entry point for the metatensor-models command line interface."""

import argparse
import importlib
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import metatensor.torch
from omegaconf import OmegaConf

from . import __version__
from .cli.eval import _add_eval_model_parser, eval_model
from .cli.export import _add_export_model_parser, export_model
from .cli.train import _add_train_model_parser, train_model
from .utils.architectures import check_architecture_name
from .utils.logging import setup_logging


logger = logging.getLogger(__name__)


def _datetime_output_path(now: datetime) -> Path:
    """Get a date and time based output path."""
    return Path(
        "outputs",
        now.strftime("%Y-%m-%d"),
        now.strftime("%H-%M-%S"),
    )


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    if len(sys.argv) < 2:
        ap.error("You must specify a sub-command")

    # If you change the synopsis of these commands or add new ones adjust the completion
    # script at `src/metatensor/models/share/metatensor-models-completion.bash`.
    ap.add_argument(
        "--version",
        action="version",
        version=f"metatensor-models {__version__}",
    )

    ap.add_argument(
        "--debug",
        action="store_true",
        help="Run with debug options.",
    )

    ap.add_argument(
        "--shell-completion",
        action="version",
        help="Path to the shell completion script",
        version=str(Path(__file__).parent / "share/metatensor-models-completion.bash"),
    )

    # Add sub-parsers
    subparser = ap.add_subparsers(help="sub-command help")
    _add_eval_model_parser(subparser)
    _add_export_model_parser(subparser)
    _add_train_model_parser(subparser)

    args = ap.parse_args()
    callable = args.__dict__.pop("callable")
    debug = args.__dict__.pop("debug")
    logfile = None

    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    if callable == "eval_model":
        args.__dict__["model"] = metatensor.torch.atomistic.load_atomistic_model(
            path=args.__dict__.pop("path"),
            extensions_directory=args.__dict__.pop("extensions_directory"),
        )
    elif callable == "export_model":
        architecture_name = args.__dict__.pop("architecture_name")
        check_architecture_name(architecture_name)
        architecture = importlib.import_module(f"metatensor.models.{architecture_name}")

        args.__dict__["model"] = architecture.__model__.load_checkpoint(
            args.__dict__.pop("path")
        )
    elif callable == "train_model":
        # define and create `checkpoint_dir` based on current directory and date/time
        checkpoint_dir = _datetime_output_path(now=datetime.now())
        os.makedirs(checkpoint_dir)
        args.__dict__["checkpoint_dir"] = checkpoint_dir

        # save log to file
        logfile = checkpoint_dir / "train.log"

        # merge/override file options with command line options
        override_options = args.__dict__.pop("override_options")
        if override_options is None:
            override_options = {}

        args.options = OmegaConf.merge(args.options, override_options)
    else:
        raise ValueError("internal error when selecting a sub-command.")

    with setup_logging(logger, logfile=logfile, level=level):
        try:
            if callable == "eval_model":
                eval_model(**args.__dict__)
            elif callable == "export_model":
                export_model(**args.__dict__)
            elif callable == "train_model":
                train_model(**args.__dict__)
            else:
                raise ValueError("internal error when selecting a sub-command.")
        except Exception as err:
            if debug:
                traceback.print_exc()
            else:
                sys.exit(str(err))


if __name__ == "__main__":
    main()
