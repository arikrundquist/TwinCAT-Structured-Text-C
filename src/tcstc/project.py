
from pathlib import Path
from typing import Final, Iterator
from xml.etree import ElementTree as XML


class Project:
  def __init__(self, project: Path) -> None:
    self._project: Final = project
    self._xml = XML.parse(self._project).getroot()

  def _get_nodes(self, node: XML.Element, tag: str) -> Iterator[XML.Element]:
    if node.tag == tag or node.tag.endswith(f"}}{tag}"):
      yield node

    for child in node:
      yield from self._get_nodes(child, tag)

  def get_project_files(self) -> Iterator[Path]:
    for compile_node in self._get_nodes(self._xml, "Compile"):
      subpath = Path(compile_node.attrib["Include"].replace("\\", "/"))
      path = self._project.parent.joinpath(subpath)
      if path.exists() and path.is_file():
        yield path
        