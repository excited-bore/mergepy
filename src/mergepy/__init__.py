#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import importlib.metadata
#__version__ = importlib.metadata.version("mergepy")
__version__='1.0'


import os
import sys
from pathlib import Path
import shutil
import subprocess
from contextlib import chdir
from difflib import Differ
import tempfile
import argparse 
import argcomplete
import codecs
from textual import events
from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll, VerticalScroll, VerticalGroup
from textual.geometry import Size
from textual.widgets import Footer, Header, Static
from textual.widget import Widget
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.syntax import Syntax



def guess_language_by_extension(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c-header",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".rb": "ruby",
        ".php": "php",
        ".rs": "rust",
        ".go": "go",
        ".swift": "swift",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "shell",
        ".csh": "csh",
        ".bash": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
    }.get(ext, "unknown")

class CodeView(ScrollView):

    code = reactive("")   

    def __init__(self, filepath, **kwargs) -> None:
        super().__init__(**kwargs)
        if isinstance(filepath, Path):
            self.filepath = filepath
            with open(self.filepath) as self_file:
                self.code = self_file.read()
        else:
            self.filepath=str(filepath)
            self.code=str(filepath)
        self.height = self.code.count("\n") + 1 if self.code else 0
        self.width = max(len(line) for line in self.code.splitlines())
        self.virtual_size = Size(self.width, self.height)
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse over the widget."""
        pass
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        if isinstance(self.filepath, Path):
            syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True)
        else:
            syntax = Syntax(str(list(self.code)), 'Csh', line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax         

class MergeApp(App):
    
    CSS_PATH = "merge.tcss"
    
    def toggle_dark(self):
        self.dark = not self.dark

    def show_diff(self, string1, string2):
        lines1 = string1.splitlines(keepends=True)
        lines2 = string2.splitlines(keepends=True)

        differ = Differ()
        diff = differ.compare(lines1, lines2)
        print(diff)
        #raise SystemExit
        return str(diff)

    def __init__(self, file_path1: Path, file_path2: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path1 = file_path1
        self.file_path2 = file_path2

    def compose(self) -> ComposeResult:
         # A scrollable container for the file contents
        yield Header()
        yield Footer()
        with VerticalGroup():
            with HorizontalScroll(id='scrollview1'):
                yield CodeView(self.file_path1)
            with HorizontalScroll(id='scrollview2'):
                yield CodeView(self.file_path2)
        with open(self.file_path1) as self_file:
            code1 = self_file.read()
        with open(self.file_path2) as self_file:
            code2 = self_file.read()
        diff=self.show_diff(code1, code2)
        with VerticalScroll(id='scrollview3'):
            yield CodeView(diff)


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
        file1=os.path.abspath(args.file1)
        file2=os.path.abspath(args.file2)
        #if shutil.which("git"):
            #tempd=tempfile.TemporaryDirectory()
            #with chdir(tempd.name):
            #    subprocess.run(["git", "init", "temprepo"])
            #    with chdir('temprepo'):
            #        shutil.copyfile(file1, 'file')
            #        subprocess.run(["git", "add", "file"])
            #        subprocess.run(["git", "commit", "-m", '"First file"'])
            #        
            #        subprocess.run(["git", "checkout", "-b", 'branch2'])
            #        shutil.copyfile(file2, 'file')
            #        subprocess.run(["git", "commit", "-am", '"Second file"'])
            #        
            #        subprocess.run(['git', 'merge', 'main'])
            #        subprocess.run(['nvim', 'file'])
                    # shutil.copyfile(file2, 'file2')
        MergeApp(args.file1, args.file2).run()

if __name__ == "__main__":
    main()