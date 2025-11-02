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
from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalGroup, VerticalScroll
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


class CodeView(Widget):

    lang = ''
    code = reactive("")

    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        syntax = Syntax(self.code, self.lang, line_numbers=True, indent_guides=True)
        return syntax         

class MergeApp(App):
    
    CSS_PATH = "merge.tcss"
    
    def toggle_dark(self):
        self.dark = not self.dark

    def __init__(self, file_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path

    def compose(self) -> ComposeResult:
         # A scrollable container for the file contents
        yield Header()
        yield Footer()
        with open(self.file_path) as self_file:
            code = self_file.read()
        code_view = CodeView()
        code_view.lang = 'fish'
        code_view.code = code
        yield code_view


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
        MergeApp(args.file1).run()

if __name__ == "__main__":
#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
    main()