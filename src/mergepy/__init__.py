#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import importlib.metadata
#__version__ = importlib.metadata.version("mergepy")
__version__='1.0'


import os
import sys
import copy
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
from textual.widgets import Label, Footer, Header, Static, Button, ListItem, ListView
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

diff_lines = []

class DiffSlice(ListItem,  can_focus=True):
    """Highlights Diff Slice."""

    # BINDINGS = [("space", "_on_click", "Select focused splice of text")]


    def __init__(self, string, id, linerange, diff, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.string = string
        self.linerange = linerange
        self.id = id
        self.diff = diff
        self.lang = lang
        self.theme = theme
        self.height = (linerange[1] - linerange[0]) + 3
        self.styles.height = (linerange[1] - linerange[0]) + 3
        self.width = max(len(line) for line in self.string.splitlines())
        self.virtual_size = Size(self.width, self.height)
        
    def action_focus_item(self) -> None:
        pattern = re.compile(r"^seq1_*")
        if pattern.match(self.id):
            type, type1 = 'seq2', 'scrollview2'
            result = re.sub(r"^seq1_", "seq2_", self.id)
        else:
            type, type1 = 'seq1', 'scrollview1'
            result = re.sub(r"^seq2_", "seq1_", self.id)
        # self.log(result)
        # self.log(self.linerange[0])    
        
        self.parent.parent.parent.scroll_to_widget(self, center=True)
        target = self.parent.parent.parent.parent.get_widget_by_id(result, DiffSlice)
        target1 = self.parent.parent.parent.parent.get_widget_by_id(type1)
        listView = self.parent.parent.parent.parent.get_widget_by_id(type, SideView)
        target1.scroll_to_widget(target, center=True, force=True)
        index = listView.children.index(target)
        listView.index = index

    def _on_click(self) -> None:
        self.action_focus_item()

    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        
        syntax = Syntax(self.string, self.lang, theme=self.theme, line_range=self.linerange, line_numbers=True, indent_guides=True)
        return syntax



class SetDiff(ListItem):
    """Set Diff."""

    def __init__(self, seq, linerange, diff, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.linerange = linerange
        self.diff = diff
        self.lang = lang
        self.theme = theme
        self.expand = True
        self.height = (linerange[1] - linerange[0]) + 1
        self.styles.height = (linerange[1] - linerange[0]) + 1
        self.width = max(len(line) for line in self.seq.splitlines())
        self.virtual_size = Size(self.width, self.height)

    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        
        syntax = Syntax(self.seq, self.lang, line_range=self.linerange, theme=self.theme, line_numbers=True, indent_guides=True)
        return syntax

class SideView(ListView):

    def __init__(self, seq, id, seq2, diff, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.id = id
        self.seq2 = seq2
        self.diff = diff
        self.lang = lang
        self.theme = theme
        h = 0
        x = re.compile(r'^seq[12]_(equal|replace)\d+$', re.IGNORECASE)
        for i in self.seq2:
            if x.match(i[2]):
                h += 2
        self.height = self.seq.count("\n") + 1 + h if self.seq else 0
        self.styles.height = self.seq.count("\n") + 1 + h if self.seq else 0
        self.width = max(len(line) for line in self.seq.splitlines())
        self.virtual_size = Size(self.width, self.height)
        
    def scroll_item(self) -> None:
        target = self.children[self.index]
        if target.id:
            pattern = re.compile(r"^seq1_*")
            pattern2 = re.compile(r"^seq2_*")
            if pattern.match(target.id):
                type, type1 = 'seq2', 'scrollview2'
                result = re.sub(r"^seq1_", "seq2_", target.id)
            elif pattern2.match(target.id):
                type, type1 = 'seq1', 'scrollview1'
                result = re.sub(r"^seq2_", "seq1_", target.id) 
            if type and result:
                self.parent.parent.scroll_to_widget(target, center=True)
                target1 = self.parent.parent.parent.get_widget_by_id(result, DiffSlice)
                target2 = self.parent.parent.parent.get_widget_by_id(type1)
                listView = self.parent.parent.parent.get_widget_by_id(type, SideView)
                target2.scroll_to_widget(target1, center=True)
                listView.index = listView.children.index(target1)

    def on_key(self, event: events.Key) -> None:
        if event.key == 'up' or event.key == 'down':
            self.parent.parent.scroll_to_widget(self.children[self.index])
        elif event.key == 'left' or event.key == 'right':
            if self.id == 'seq1':
                self.parent.parent.get_widget_by_id('seq2').focus()
            else:
                self.parent.parent.get_widget_by_id('seq1').focus()
        elif event.key == 'ctrl+up':
            for i in reversed(self.children):
                if i.id and self.children.index(i) < self.index:
                    self.index = self.children.index(i)
                    self.scroll_item()
                    break
        elif event.key == 'ctrl+down':
            for i in self.children:
                if i.id and self.children.index(i) > self.index:
                    self.index = self.children.index(i)
                    self.scroll_item()
                    break
        elif event.key == 'space':
            self.scroll_item()
        elif event.key == 'k':
            target = self.parent.parent.parent.get_widget_by_id('diffview', CodeView)
            seq = ''
            range = self.children[self.index].linerange
            for num, line in enumerate(self.children[self.index].seq.splitlines(), 1):
                if num >= range[0] and num <= range[1]:
                    seq += line[2:] + '\n'
            diff_lines.append([seq, self.index, copy.copy(self.children[self.index])])
            target.add_diff(seq)
            self.pop(self.index)
        elif event.key == 'ctrl+z':
            if diff_lines:
                target = self.parent.parent.parent.get_widget_by_id('diffview', CodeView)
                seq, idx, item = diff_lines.pop()
                range = len(seq.splitlines())
                target.remove_diff(range)
                self.insert(idx, iter([item]))

    def on_mount(self) -> None:
        if self.id == 'seq1':
            self.focus()
            for i in self.children:
                if i.id:
                    self.index = self.children.index(i)
                    self.scroll_item()
                    break 

    def compose(self) -> ComposeResult:
        # yield SetDiff(self.seq, self.seq2, self.lang, self.theme)
        x = re.compile(r'^seq[12]_(equal|replace)\d+$', re.IGNORECASE)
        for i in self.seq2:
            j = i.copy()
            if x.match(i[2]):
                yield DiffSlice(self.seq, j[2], j[3], self.diff, self.lang, self.theme)
            else:
                yield SetDiff(self.seq, i[3], self.diff, self.lang, self.theme)



class CodeView(ScrollView):   

    code = reactive('')

    def __init__(self, filepath, lang, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lang = lang
        self.id = 'diffview'
        self.filepath=str(filepath)
        self.code=str(filepath)
        self.height = self.code.count("\n") + 1 if self.code else 0
        self.styles.min_height = self.code.count("\n") + 1 if self.code else 0
        self.width = max(len(line) for line in self.code.splitlines()) if self.code else 0
        self.virtual_size = Size(self.width, self.height)
    
    def add_diff(self, code) -> None:
        self.code += code

    def remove_diff(self, range) -> None:
        self.code = "\n".join(self.code.splitlines()[:-range])

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse over the widget."""
        pass
    
    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        syntax = Syntax(self.code, self.lang, line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax         

class MergePy(App):
    
    CSS_PATH = "merge.tcss"


    # ("ctrl+q,q", "quit", "Quit", show=True, priority=True),
    # ("space", "nothing('2')", "Select Conflict")
    BINDINGS = [
        ("Up/Down", " ", "Next/Prev Block"),
        ("^Up/^Down", "  ", "Next/Prev Conflict"),
    ]

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
            yield Label(str(self.file_path1))
            with HorizontalScroll(id='scrollview1'):
                yield SideView(self.seq1, 'seq1', self.seq12, self.diff, self.lang, 'ansi_dark')
            yield Label(str(self.file_path2))
            with HorizontalScroll(id='scrollview2'):
                yield SideView(self.seq2, 'seq2', self.seq22, self.diff, self.lang, 'ansi_dark')
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
