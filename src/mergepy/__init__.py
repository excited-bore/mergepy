#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import importlib.metadata
#__version__ = importlib.metadata.version("mergepy")
__version__='1.0'


import os
import sys
import shutil
from pathlib import Path
import argparse 
import argcomplete
import codecs
from textual import events
from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll, VerticalScroll
from textual.geometry import Size
from textual.widgets import Footer, Header, Static
from textual.widget import Widget
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.syntax import Syntax
if shutil.which("git"):
   import git
   from git import Repo

def is_git_repo(path):
    if not shutil.which("git"):
        return False
    try:
        repo = git.Repo(path, search_parent_directories=True).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


class CodeView(ScrollView):

    code = reactive("")   

    def __init__(self, filepath, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filepath = filepath
        with open(self.filepath) as self_file:
            self.code = self_file.read()
        self.height = self.code.count("\n") + 1 if self.code else 0
        self.width = max(len(line) for line in self.code.splitlines())
        self.virtual_size = Size(self.width, self.height)
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse over the widget."""
        pass
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        syntax = Syntax.from_path(self.filepath, line_numbers=True)
        return syntax         

class MergeApp(App):
    
    CSS_PATH = "merge.tcss"
    
    def toggle_dark(self):
        self.dark = not self.dark

    def __init__(self, file_path1: Path, file_path2: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path1 = file_path1
        self.file_path2 = file_path2

    def compose(self) -> ComposeResult:
         # A scrollable container for the file contents
        yield Header()
        yield Footer()
        with HorizontalScroll(id='scrollview1'):
            yield CodeView(self.file_path1)
        with HorizontalScroll(id='scrollview2'):
            yield CodeView(self.file_path2)


def main():
    choices = argcomplete.completers.ChoicesCompleter
    parser = argparse.ArgumentParser(description="Merge files 2-way",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-o","--output", type=argparse.FileType('r'), required=False, help="output file", metavar="output file")
    parser.add_argument("file1", type=Path, help="First file to be merged", metavar="first file")
    parser.add_argument("file2", type=Path, help="Second file to be merged", metavar="second file")
    output_stream = None
    if "_ARGCOMPLETE_POWERSHELL" in os.environ:
        output_stream = codecs.getwriter("utf-8")(sys.stdout.buffer)
    argcomplete.autocomplete(parser, output_stream=output_stream)
    args = parser.parse_args()
    if not args.file1.is_file():
        raise FileNotFoundError("File %s doesn't exists" % sys.argv[1])
    elif not args.file2.is_file():
        raise FileNotFoundError("File %s doesn't exists" % sys.argv[2])
    else:
        print("Files found!")
        MergeApp(args.file1, args.file2).run()

if __name__ == "__main__":
    main()