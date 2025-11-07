#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import importlib.metadata
#__version__ = importlib.metadata.version("mergepy")
__version__='1.0'


import os
import sys
import re
import asyncio
import logging
from pathlib import Path
import shutil
import subprocess
from contextlib import chdir
import difflib
import tempfile
import argparse 
import argcomplete
import codecs
from textual import events, on, work
from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll, VerticalScroll, VerticalGroup
from textual.geometry import Size
from textual.widgets import Footer, Header, Static, Button, ListItem, ListView
from textual.widget import Widget
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.syntax import Syntax
from rich.style import Style

def guess_language(file_path: str) -> str:
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


class DiffSlice(ListItem):
    """Highlights Diff Slice."""

    def __init__(self, string, id, linerange, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.string = string
        self.linerange = linerange
        self.id = id
        self.lang = lang
        self.theme = theme
        self.height = (linerange[1] - linerange[0]) + 3
        self.styles.height = (linerange[1] - linerange[0]) + 3
        self.width = max(len(line) for line in self.string.splitlines())
        self.virtual_size = Size(self.width, self.height)
    

    def _on_click(self) -> None:
        pattern = re.compile(r"^seq1_*")
        if pattern.match(self.id):
            type, type1 = 'seq2', 'scrollview2'
            result = re.sub(r"^seq1_", "seq2_", self.id)
        else:
            type, type1 = 'seq1', 'scrollview1'
            result = re.sub(r"^seq2_", "seq1_", self.id)
        # self.log(result)
        # self.log(self.linerange[0])    
        
        self.parent.parent.parent.scroll_to_widget(self)
        logging.debug(self.parent.parent.parent.styles.height)
        target = self.parent.parent.parent.parent.get_widget_by_id(result, DiffSlice)
        target1 = self.parent.parent.parent.parent.get_widget_by_id(type1)
        target1.scroll_to_widget(target, force=True)
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        
        syntax = Syntax(self.string, self.lang, theme=self.theme, line_range=self.linerange, line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax



class SetDiff(ListItem):
    """Set Diff."""

    def __init__(self, seq, linerange, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lang = lang
        self.seq = seq
        self.linerange = linerange
        self.theme = theme
        self.expand = True
        self.height = (linerange[1] - linerange[0]) + 1
        self.styles.height = (linerange[1] - linerange[0]) + 1
        self.width = max(len(line) for line in self.seq.splitlines())
        self.virtual_size = Size(self.width, self.height)

    diff = reactive('')
    
    def on_mount(self) -> None:
        self.diff = self.seq
        # self.update(self.diff)
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        
        syntax = Syntax(self.diff, self.lang, line_range=self.linerange, theme=self.theme, line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax

class SideView(ScrollView):

    def __init__(self, seq, type, seq2, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.id = type
        self.seq2 = seq2
        self.lang = lang
        self.theme = theme
        self.height = self.seq.count("\n") + 1 if self.seq else 0
        self.styles.height = self.seq.count("\n") + 1 if self.seq else 0
        self.width = max(len(line) for line in self.seq.splitlines())
        self.virtual_size = Size(self.width, self.height)
        
    def compose(self) -> ComposeResult:
        # yield SetDiff(self.seq, self.seq2, self.lang, self.theme)
        x = re.compile(r'^seq[12]_(equal|replace)\d+$', re.IGNORECASE)
        with ListView():
            for i in self.seq2:
                j = i.copy()
                if x.match(i[2]):
                    yield DiffSlice(self.seq, j[2], j[3], self.lang, self.theme)
                else:
                    yield SetDiff(self.seq, i[3], self.lang, self.theme)



class CodeView(ScrollView):

    code = reactive("")   

    def __init__(self, filepath, lang, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lang = lang
        if isinstance(filepath, Path):
            self.filepath = filepath
            with open(self.filepath) as self_file:
                self.code = self_file.read()
        else:
            self.filepath=str(filepath)
            self.code=str(filepath)
        self.height = self.code.count("\n") + 1 if self.code else 0
        self.styles.min_height = self.code.count("\n") + 1 if self.code else 0
        self.width = max(len(line) for line in self.code.splitlines())
        self.virtual_size = Size(self.width, self.height)
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse over the widget."""
        pass
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        if isinstance(self.filepath, Path):
            syntax = Syntax.from_path(self.filepath, theme='ansi_dark', line_numbers=True, indent_guides=True, word_wrap=True)
        else:
            syntax = Syntax(self.code, self.lang, line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax         

class MergePy(App):
    
    CSS_PATH = "merge.tcss"
    
    def toggle_dark(self):
        self.dark = not self.dark

    def show_diff(self, string1, string2):
        lines1 = string1.splitlines(keepends=True)
        lines2 = string2.splitlines(keepends=True)

        differ = difflib.Differ()
        diff = differ.compare(lines1, lines2)
        sequence = []
        # Diff object does not have indices which we need to put it in a list first
        for line in diff:
            sequence.append(line)
        diffstr = ''
        seq = []
        seq1before, seq2before, commonbefore = False,False,False
        i, eq, equal, rep, replace = 0, 0, 0, 0, 0
        for line in sequence:
            if equal == 4:
               equal = 0 
            if replace == 3:
               replace = 0
            if equal > 0:
                equal += 1
            elif replace > 0:
                replace += 1
            elif line.startswith('- ') and str(sequence[i+1]).startswith('? ') and str(sequence[i+2]).startswith('+ ') and str(sequence[i+3]).startswith('? '):
                # Equal
                seq.append(['seq1', [line], "seq1_equal" + str(eq)])
                seq.append(['seq2', [sequence[i+2]], "seq2_equal" + str(eq)])
                eq += 1
                equal = 1
                seq1before, seq2before, commonbefore = False, False, False
            elif line.startswith('- ') and str(sequence[i+1]).startswith('+ ') and str(sequence[i+2]).startswith('? '): 
                # Replace
                seq.append(['seq1', [line], "seq1_replace" + str(rep)])
                seq.append(['seq2', [sequence[i+1]], "seq2_replace" + str(rep)])
                rep += 1
                replace = 1
                seq1before, seq2before, commonbefore = False, False, False
            elif line.startswith('- '):
                diffstr += line
                if not seq1before:
                    seq.append(['seq1', [line], 'none'])
                    seq1before, seq2before, commonbefore = True, False, False
                else: 
                    seq[len(seq)-1][1].append(line)
            elif line.startswith('+ '):
                diffstr += line
                if not seq2before:
                    seq.append(['seq2', [line], 'none'])
                    seq1before, seq2before, commonbefore = False, True, False
                else: 
                    seq[len(seq)-1][1].append(line)
            elif line.startswith('  '):
                diffstr += line
                if not commonbefore:
                    seq.append(['common', [line], 'none'])
                    seq1before, seq2before, commonbefore = False, False, True
                else: 
                    seq[len(seq)-1][1].append(line)
            i += 1
        return seq
    
    def __init__(self, file_path1: Path, file_path2: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path1 = file_path1
        self.file_path2 = file_path2
        
        with open(self.file_path1) as self_file:
            code1 = self_file.read()
        
        with open(self.file_path2) as self_file:
            code2 = self_file.read()
        
        self.seq=self.show_diff(code1, code2)
        
        if self.file_path1.suffix:
            self.lang = guess_language(self.file_path1)
        elif self.file_path2.suffix:
            self.lang = guess_language(self.file_path2)
        # Else we just pretend its a shell language
        else:
            self.lang = 'shell'

        self.seq12, self.seq22 = [], []
        for i in self.seq:
            if i[0] == 'seq1':
                self.seq12.append(i)
            elif i[0] == 'seq2':
                self.seq22.append(i)
            if i[0] == 'common':
                j = i.copy()
                self.seq12.append(i)
                self.seq22.append(j)

        # print(self.seq12)

        self.seq1, self.seq2, linenr1, linenr2 = '', '', 0, 0
        for lines in self.seq12:
            linenr12 = 0
            for line in lines[1]:
                self.seq1 += line
                linenr12 += 1
            lines[1] = ''.join(lines[1])
            lines.append((linenr1 + 1, linenr1 + linenr12))
            linenr1 += linenr12
        for lines in self.seq22:
            linenr22 = 0
            for line in lines[1]:
                self.seq2 += line
                linenr22 += 1
            lines[1] = ''.join(lines[1])
            lines.append((linenr2 + 1, linenr2 + linenr22))
            linenr2 += linenr22
        #for i, line in enumerate(self.seq2.splitlines(), start=1):
        #    print(f"{i:>3}: {line}")
        #x = re.compile(r'^(equal|replace)\d+$', re.IGNORECASE)
        #for i in self.seq22:
        #    if x.match(i[2]):
        #        print(i[1]) 
        #        print(i[3])
        #for i in self.seq12:
        #    print(i) 
    diff = reactive('')


    def compose(self) -> ComposeResult:
        # A scrollable container for the file contents
        yield Header()
        yield Footer()
        
        with VerticalGroup():
            with HorizontalScroll(id='scrollview1'):
                yield SideView(self.seq1, 'seq1', self.seq12, self.lang, 'ansi_dark')
            with HorizontalScroll(id='scrollview2'):
                yield SideView(self.seq2, 'seq2', self.seq22, self.lang, 'lightbulb')
        #if self.diff:
        #    with VerticalScroll(id='scrollview3'):
        #        yield CodeView(self.diff, self.lang)
        seq1, seq2, common = 0,0,0
        #for lines in self.seq:
        #    if lines == 'common':
        #        self.diff += self.common[common] 
        #        common += 1
        #    else:
        #        pass
                #input("Press Enter to continue...")                    
        if self.diff:
            with VerticalScroll(id='scrollview3'):
                yield CodeView(self.diff, self.lang)

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
        MergePy(args.file1, args.file2).run()

if __name__ == "__main__":
    main()
