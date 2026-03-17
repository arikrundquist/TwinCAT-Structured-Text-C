import logging
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

import click

from tcstc.formatters.structured_text import format
from tcstc.models.twincat import TwinCatObject
from tcstc.parsers.structured_text.structured_text import structured_text_parser
from tcstc.project import Project
from tcstc.util.utils import (
    clean_structured_text,
    convert_path,
    expect_one,
    find_by_extension,
    write_file,
)


def _project_option(name: str) -> Any:
    type = click.Path(exists=True, dir_okay=False)
    default_project = expect_one(find_by_extension(".plcproj", Path()))

    if default_project is None:
        return click.option(
            name,
            type=type,
            help="The path to the plc project.",
            required=True,
        )

    default_project = default_project.resolve()
    return click.option(
        name,
        type=type,
        help=f"The path to the plc project. (default: {default_project})",
    )


def _directory_option(name: str) -> Any:
    default_directory = Path().resolve()
    return click.option(
        name,
        default=str(default_directory),
        type=click.Path(dir_okay=True, file_okay=False, writable=True),
        help=f"The path to the workspace. (default: {default_directory})",
    )


def _get_project_path(path: str) -> Path:
    p = Path(path)
    assert p.is_file()
    return p


def _get_folder_path(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    assert p.is_dir()
    return p


@click.command(help="Extract PLC code from the specified project.")
@_project_option("--src")
@_directory_option("--dest")
@click.option(
    "--no-fmt",
    "fmt",
    flag_value=False,
    default=True,
    help="Disable reformatting after extraction. (default)",
)
@click.option(
    "--fmt", "fmt", flag_value=True, help="Enable reformatting after extraction."
)
def tc2st(src: str, dest: str, fmt: bool) -> None:
    project_path = _get_project_path(src)
    project_root = project_path.parent
    project = Project(project_path)
    folder = _get_folder_path(dest)
    assert isinstance(fmt, bool)

    shutil.rmtree(folder, ignore_errors=True)

    for project_file in project.get_project_files():
        for ObjectType in TwinCatObject.object_types():
            if not project_file.name.endswith(ObjectType.extension()):
                continue

            object = ObjectType.get_from_path(project_file)
            assert object.path

            converted = convert_path(
                src_folder=project_root,
                path=project_file,
                dest_folder=folder,
            )

            structured_text = clean_structured_text(object.get_structured_text())
            write_file(converted, structured_text)

    if fmt:
        stfmt(["--dir", dest])


@click.command(help="Format structured text.")
@_directory_option("--dir")
def stfmt(dir: str) -> None:
    folder = _get_folder_path(dir)
    for file in find_by_extension("", folder):
        with suppress(Exception):
            with open(file, "r") as f:
                structured_text = clean_structured_text(f.read())
            try:
                parsed = structured_text_parser.parse(structured_text)(file)
                structured_text = "\n\n".join(format(node) for node in parsed)

            except Exception as e:
                logging.error(f"Failed to parse {file}")
                logging.exception(e)
                raise

            with open(file, "w") as f:
                f.write(structured_text)


@click.command(help="Insert PLC code into the specified project.")
@_directory_option("--src")
@_project_option("--dest")
def st2tc(src: str, dest: str) -> None:
    folder = _get_folder_path(src)
    project = _get_project_path(dest)
    raise NotImplementedError(folder, project)
