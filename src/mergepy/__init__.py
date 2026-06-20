#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import importlib.metadata
#__version__ = importlib.metadata.version("mergepy")
__version__='1.0'


import os
import platform
import sys
import subprocess
import copy
import re
from pathlib import Path
import difflib
import argparse 
import argcomplete
import codecs
from textual import events, on, work, getters
from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll, VerticalGroup, ScrollableContainer
from textual.geometry import Size
from textual.binding import Binding
from textual.widgets import Label, Footer, Header, Static, Button, ListItem, ListView, TextArea
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.syntax import Syntax
from rich.style import Style
from PySide6.QtWidgets import QApplication, QFileDialog
from dataclasses import dataclass, field


def editor_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".html": "html",
        ".css": "css",
        ".rb": "ruby",
        ".php": "php",
        ".rs": "rust",
        ".go": "go",
        ".swift": "swift",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
        ".env": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".csh": "",
        ".fish": "",
    }.get(ext, "")


def rich_language(file_path: str) -> str:
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
        ".rb": "ruby",
        ".php": "php",
        ".rs": "rust",
        ".go": "go",
        ".swift": "swift",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "shell",
        ".env": "shell",
        ".bash": "bash",
        ".zsh": "zsh",
        ".csh": "csh",
        ".fish": "fish",
    }.get(ext, "unknown")

# diff_lines = [ text, id, index, widget, action_name, undostack_item ]

diff_lines = []

# undones = [ [ [ text1, id1, index1, widget1, action_name1, undostack_item1 ], [ text2, id2, index2, widget2, action_name2, undostack_item2 ] ], ... ] 

undones = []

class Slice(ListItem):
    """Base class for diff and common slices."""

    def __init__(self, text, id1, linerange, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.text = text
        self.id = id1
        self.linerange = linerange
        self.lang = lang
        self.theme = theme
        self.width = max(len(line) for line in self.text.splitlines())

    def action_focus_item(self) -> None:
        pattern = re.compile(r"^seq1_*")
        if pattern.match(self.id):
            type1, type2 = 'seq2', 'scrollview2'
            result = re.sub(r"^seq1_", "seq2_", self.id)
        else:
            type1, type2 = 'seq1', 'scrollview1'
            result = re.sub(r"^seq2_", "seq1_", self.id)

        self.parent.parent.parent.scroll_to_widget(self, center=True)

        try:
            target = self.parent.parent.parent.parent.get_widget_by_id(result, Slice)
            target1 = self.parent.parent.parent.parent.get_widget_by_id(type2)
            listView = self.parent.parent.parent.parent.get_widget_by_id(type1, SideView)
            target1.scroll_to_widget(target, center=True, force=True)
            index = listView.children.index(target)
            listView.index = index
        except:
            pass

    def on_click(self) -> None:
        self.action_focus_item()


class DiffSlice(Slice):
    """Highlights Diff Slice."""

    def __init__(self, text, id1, linerange, lang, theme, **kwargs) -> None:
        super().__init__(text, id1, linerange, lang, theme, **kwargs)
        self.classes = re.sub(r'.*_(replace)\d+', r'\1', id1)
        self.height = (linerange[1] - linerange[0]) + 3
        self.styles.height = (linerange[1] - linerange[0]) + 3
        self.virtual_size = Size(self.width, self.height)

    def render(self) -> RenderResult:
        syntax = Syntax(self.text, self.lang, theme=self.theme, line_range=self.linerange, line_numbers=True, indent_guides=True)
        return syntax



class CommonSlice(Slice):
    """Common Slice."""

    def __init__(self, text, id1, linerange, lang, theme, **kwargs) -> None:
        super().__init__(text, id1, linerange, lang, theme, **kwargs)
        self.height = (linerange[1] - linerange[0]) + 1
        self.styles.height = (linerange[1] - linerange[0]) + 1
        self.virtual_size = Size(self.width, self.height)

    def render(self) -> RenderResult:
        syntax = Syntax(self.text, self.lang, line_range=self.linerange, theme=self.theme, line_numbers=True, indent_guides=True)
        return syntax


class SideView(ListView):
     
    def get_index(self) -> None:
        for i in self.children:
            if i.id:
                self.index = self.children.index(i)
                break 

    def calibrate_dimensions(self) -> None:
        h = 0
        x = re.compile(r'^seq[12]_replace\d+$', re.IGNORECASE)
        for i in self.slices:
            if x.match(i[2]):
                h += 2
        self.height = self.text.count("\n") + 1 + h if self.text else 0
        self.styles.height = "auto"
        self.width = max(len(line) for line in self.text.splitlines())
        self.styles.width = self.width
        self.virtual_size = Size(self.width, self.height)
        self.get_index()

    def __init__(self, text, id1, slices, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.text = text
        self.id = id1
        self.index = 0
        self.slices = slices
        self.lang = lang
        self.theme = theme
        self.calibrate_dimensions()
    
    def scroll_item(self) -> None:
        self.children[self.index].action_focus_item()
    
    def on_key(self, event: events.Key) -> None:
        seq1 = self.parent.parent.get_widget_by_id('seq1')
        seq2 = self.parent.parent.get_widget_by_id('seq2')
        if event.key == 'space': 
            self.scroll_item()
        elif event.key == 'up' and self.index-1 >= 0:
            self.parent.scroll_to_widget(self.children[self.index-1], center=True)
        elif event.key == 'down' and self.index+1 <= len(self.children) - 1:
            self.parent.scroll_to_widget(self.children[self.index+1], center=True)
        elif event.key == 'ctrl+right': 
            seq1.highlighted_child.highlighted = False 
            seq2.highlighted_child.highlighted = False 
            self.parent.parent.parent.parent.textarea.focus()
        elif event.key == 'shift+up':
            self.parent.scroll_up()
        elif event.key == 'shift+down':
            self.parent.scroll_down()
        elif event.key == 'shift+left':
            self.parent.scroll_page_left()
        elif event.key == 'shift+right':
            self.parent.scroll_page_right()
        elif event.key == 'ctrl+up' and self.id == 'seq2' and len(seq1.children) >= 1:
            self.parent.parent.get_widget_by_id('seq1').focus()
        elif event.key == 'ctrl+down' and self.id == 'seq1' and len(seq2.children) >= 1:
            self.parent.parent.get_widget_by_id('seq2').focus()
                
        elif event.key == 'alt+up':
            for i in reversed(self.children):
                pttrn = re.compile(r'.*replace.*')
                if pttrn.match(i.id) and self.children.index(i) < self.index:
                    self.index = self.children.index(i)
                    self.scroll_item()
                    break
        elif event.key == 'alt+down':
            for i in self.children:
                pttrn = re.compile(r'.*replace.*')
                if pttrn.match(i.id) and self.children.index(i) > self.index:
                    self.index = self.children.index(i)
                    self.scroll_item()
                    break
        
        elif event.key == 'space':
            self.scroll_item()                

    def on_mount(self) -> None:
        if self.id == 'seq1':
            self.focus()

    def compose(self) -> ComposeResult:
        x = re.compile(r'^seq[12]_replace\d+$', re.IGNORECASE)
        for i in self.slices:
            j = i.copy()
            if x.match(i[2]):
                yield DiffSlice(self.text, j[2], j[3], self.lang, self.theme)
            else:
                yield CommonSlice(self.text, i[2], i[3], self.lang, self.theme)

# Textarea bindings

    """
    | Key(s)                 | Description                                  |
    | :-                     | :-                                           |
    | up                     | Move the cursor up.                          |
    | down                   | Move the cursor down.                        |
    | left                   | Move the cursor left.                        |
    | ctrl+left              | Move the cursor to the start of the word.    |
    | ctrl+shift+left        | Move the cursor to the start of the word and select.    |
    | right                  | Move the cursor right.                       |
    | ctrl+right             | Move the cursor to the end of the word.      |
    | ctrl+shift+right       | Move the cursor to the end of the word and select.      |
    | home,ctrl+a            | Move the cursor to the start of the line.    |
    | end,ctrl+e             | Move the cursor to the end of the line.      |
    | shift+home             | Move the cursor to the start of the line and select.      |
    | shift+end              | Move the cursor to the end of the line and select.      |
    | pageup                 | Move the cursor one page up.                 |
    | pagedown               | Move the cursor one page down.               |
    | shift+up               | Select while moving the cursor up.           |
    | shift+down             | Select while moving the cursor down.         |
    | shift+left             | Select while moving the cursor left.         |
    | shift+right            | Select while moving the cursor right.        |
    | backspace              | Delete character to the left of cursor.      |
    | ctrl+w                 | Delete from cursor to start of the word.     |
    | delete,ctrl+d          | Delete character to the right of cursor.     |
    | ctrl+f                 | Delete from cursor to end of the word.       |
    | ctrl+shift+k           | Delete the current line.                     |
    | ctrl+u                 | Delete from cursor to the start of the line. |
    | ctrl+k                 | Delete from cursor to the end of the line.   |
    | f6                     | Select the current line.                     |
    | f7                     | Select all text in the document.             |
    | ctrl+z                 | Undo.                                        |
    | ctrl+y                 | Redo.                                        |
    | ctrl+x                 | Cut selection or line if no selection.       |
    | ctrl+c                 | Copy selection to clipboard.                 |
    | ctrl+v                 | Paste from clipboard.                        |
    """ 
    

class MergeView(TextArea):   

    def calibrate_dimensions(self) -> None:
        self.height = self.text.count("\n") + 2 if not self.text == '' else 0
        self.styles.height = self.height
        self.width = max(len(line) for line in self.text.splitlines()) if self.text else 0
        self.styles.width = self.width
        self.styles.min_width = 100
        self._rewrap_and_refresh_virtual_size()  
        self.virtual_size = Size(self.width, self.height)

    def action_undo(self) -> None:
        self.parent.parent.action_undo()
    
    def action_redo(self) -> None:
        self.parent.parent.action_redo() 

    def on_key(self, event: events.Key) -> None:
        if event.key == 'ctrl+left' or event.key == 'ctrl+right':
            seq1 = self.parent.parent.get_widget_by_id('seq1') 
            seq2 = self.parent.parent.get_widget_by_id('seq2') 
            if len(seq1.children) >= 1: 
                seq1.focus()
                seq1.highlighted_child.highlighted = True
            elif len(seq2.children) >= 1:
                seq2.focus()
                seq2.highlighted_child.highlighted = True
        elif event.key == 'up' or event.key == 'down':
            self.scroll_cursor_visible()
        elif event.key == 'alt+up':
            self.scroll_up()
        elif event.key == 'alt+down':
            self.scroll_down() 
        elif event.key == 'pagedown' or event.key == 'alt+pagedown':
            self.scroll_page_down()
        elif event.key == 'pageup' or event.key == 'alt+pageup':
            self.scroll_page_up()
        elif event.key == 'alt+left':
            self.scroll_page_left()
        elif event.key == 'alt+right':
            self.scroll_page_right()

    def add_diff(self, text) -> None:
        if len(self.text) > 0 and not self.text[-1] == '\n': 
            self.insert('\n', (self.document.line_count - 1, len(self.text.splitlines()[0])), maintain_selection_offset=False) 
        self.insert(text, (self.document.line_count - 1, 0), maintain_selection_offset=False) 
        diff_lines[-1][-1] = self.history.undo_stack[-1] 
        self.calibrate_dimensions()

    def remove_diff(self) -> None:
        # Otherwise gives error 
        self.move_cursor(self.history.undo_stack[-1][0].from_location) 
        self.undo()
        self.calibrate_dimensions() 

class MergePy(App):
    
    CSS_PATH = "merge.tcss"

    BINDINGS = [
        ("ctrl-↑/↓/←/→", "   ", "Next window"),
        ("shift-↑/↓/←/→", "scroll1", "Scroll"),
        ("shift-↑/↓/←/→", "select", "Select"),
        ("alt-↑/↓", "next_conflict", "Next Conflict"),
        ("alt-↑/↓/←/→", "scroll2", "Scroll"),
        ("space", "sync", "Sync"),
        ("enter", "replace_keep", "Replace/Keep"),
        ("r", "replace", "Replace Block"),
        ("k", "keep", "Keep Block"),
        ("d", "delete", "Delete Block"),
        ("q", "quit", "Quit"),
        ("ctrl+z", "undo", "Undo"),
        ("ctrl+y", "redo", "Redo"),
        ("ctrl+s", "save", "Save"),
        # I put these here sinds textual's textarea uses ctrl+z and ctrl+y internally with show=False 
        ("^z", "undo", "Undo"),
        ("^y", "redo", "Redo"),
     ]

    merge = reactive('') 

    def __init__(self, file_path1: Path, file_path2: Path, output=None, automerge=True, richtheme='ansi_dark',language='', mergetheme='css', **kwargs):
        super().__init__(**kwargs)
        self.id = 'app' 
        self.file_path1 = file_path1
        self.file_path2 = file_path2
        self.output = output
        self.automerge = automerge
        self.richtheme = richtheme 
        self.mergetheme = mergetheme 
        with open(self.file_path1) as self_file:
            text1 = self_file.read()
        
        with open(self.file_path2) as self_file:
            text2 = self_file.read()
        
        self.seq=self.show_diff(text1, text2)
        
        if language: 
            self.richlang = language 
            self.editlang = language 
        elif Path(self.file_path1).suffix:
            self.richlang = rich_language(self.file_path1)
            self.editlang = editor_language(self.file_path1)
        elif Path(self.file_path2).suffix:
            self.richlang = rich_language(self.file_path2)
            self.editlang = editor_language(self.file_path2)
        
        self.textarea = MergeView.code_editor(id='mergeview', text="", language=self.editlang, theme=self.mergetheme) 
        
        self.slices1, self.slices2 = [], []
        for i in self.seq:
            if i[0] == 'seq1':
                self.slices1.append(i)
            elif i[0] == 'seq2':
                self.slices2.append(i)
            if i[0] == 'common':
                j = i.copy()
                i[2] = 'seq1_' + i[2]
                j[2] = 'seq2_' + j[2]
                self.slices1.append(i)
                self.slices2.append(j)

        self.text1, self.text2, linenr1, linenr2 = '', '', 0, 0
        for lines in self.slices1:
            linenr12 = 0
            for line in lines[1]:
                self.text1 += line
                linenr12 += 1
            lines[1] = ''.join(lines[1])
            lines.append((linenr1 + 1, linenr1 + linenr12))
            linenr1 += linenr12
        for lines in self.slices2:
            linenr22 = 0
            for line in lines[1]:
                self.text2 += line
                linenr22 += 1
            lines[1] = ''.join(lines[1])
            lines.append((linenr2 + 1, linenr2 + linenr22))
            linenr2 += linenr22 

    def on_mount(self) -> None:
        self.title = ' diff ' + str(self.file_path1) + ' ' + str(self.file_path2)
    
    def on_key(self, event: events.Key) -> None:
        # Try and except otherwise command palette freaks out 
        try: 
            if not self.textarea.has_focus_within: 
                 
                if not (event.key == 'shift+up' or event.key == 'shift+down' or event.key == 'shift+left' or event.key == 'shift+right'): 
                    self.refresh_bindings()
                if event.key == 'enter':
                    self.action_replace_keep()
        except:
            pass

    def check_automerge(self): 
        pass 

    def check_empty(self) -> None:
        seq1 = self.get_widget_by_id('seq1') 
        seq2 = self.get_widget_by_id('seq2') 
   
        if len(seq1.children) < 2 and len(seq2.children) > 2:
            seq2.focus() 
        elif len(seq1.children) > 2 and len(seq2.children) < 2:
            seq1.focus() 
        elif len(seq1.children) < 2 and len(seq2.children) < 2 and not self.textarea.text == '':
            self.textarea.focus()

    def action_next_conflict(self) -> None: 
        list1 = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2') 
        for i in list1.children:
            pttrn = re.compile(r'.*replace.*')
            if pttrn.match(i.id) and list1.children.index(i) > list1.index:
                list1.index = list1.children.index(i)
                list1.scroll_item()
                break
     
    def sync(self) -> None:
        list1 = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        list1.scroll_item()

    def action_sync(self) -> None:
        self.sync()

    def replace(self):
        target = self.textarea 
        list1 = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        
        list2 = self.get_widget_by_id('seq2') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq1')
        id1 = 'seq2' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq1'
        id1 = id1 + '_' + str(re.sub(r'.*_', '', list1.children[list1.index].id)) 
        diffv = self.get_widget_by_id(id1)
        seq, seq2 = '', ''

        range1 = list1.children[list1.index].linerange
        for num, line in enumerate(list1.children[list1.index].text.splitlines(), 1):
            if num >= range1[0] and num <= range1[1]:
                seq += line[2:] + '\n'
        diff_lines.append([seq, list1.id, list1.index, copy.copy(list1.children[list1.index]), 'replace', ''])
        complete1 = list1.pop(list1.index)
        
        range1 = diffv.linerange
        for num, line in enumerate(diffv.text.splitlines(), 1):
            if num >= range1[0] and num <= range1[1]:
                seq2 += line[2:] + '\n'
        diff_lines.append([seq2, list2.id, list2.children.index(diffv), copy.copy(diffv), 'replace', ''])
        complete2 = list2.pop(list2.children.index(diffv))
        target.add_diff(seq)
        
        list1.calibrate_dimensions()
        list2.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear()
        
        return complete1, complete2

    def action_replace(self) -> None:
        self.replace() 

    def keep(self):
        target = self.textarea
        seq = ''
        id1 = 'seq1' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq2'
        list1 = self.get_widget_by_id('seq1') if id1 == 'seq1' else self.get_widget_by_id('seq2')
        
        range1 = list1.children[list1.index].linerange
        for num, line in enumerate(list1.children[list1.index].text.splitlines(), 1):
            if num >= range1[0] and num <= range1[1]:
                seq += line[2:] + '\n'
        
        item = list1.children[list1.index]

        diff_lines.append([seq, list1.id, list1.index, copy.copy(item), 'keep', ''])
        
        comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 
        if comm.match(list1.children[list1.index].id):
            idlist2 = re.sub(r"seq1", 'seq2', list1.id) if id1 == 'seq1' else re.sub(r"seq2", 'seq1', list1.id)
            list2 = self.get_widget_by_id(idlist2)
            
            id2 = list1.children[list1.index].id 
            id2 = re.sub(r"seq1", 'seq2', id2) if id1 == 'seq1' else re.sub(r"seq2", 'seq1', id2)
            item2 = self.get_widget_by_id(id2)
            idx2 = list2.children.index(item2) 

            diff_lines.append([seq, list2.id, idx2, copy.copy(item2), 'keep', ''])
            list2.pop(idx2)
            list2.calibrate_dimensions()

        target.add_diff(seq)
       
        list1.pop(list1.index)
        list1.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear() 

    def action_keep(self) -> None:
        self.keep()

    def delete(self):
        seq = ''
        list1 = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        
        id1 = 'seq1' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq2'
        range1 = list1.children[list1.index].linerange
        for num, line in enumerate(list1.children[list1.index].text.splitlines(), 1):
            if num >= range1[0] and num <= range1[1]:
                seq += line[2:] + '\n'
        diff_lines.append([seq, list1.id, list1.index, copy.copy(list1.children[list1.index]), 'delete', ''])
        list1.pop(list1.index)
        list1.calibrate_dimensions()
        comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 
        if comm.match(list1.children[list1.index].id):
            idlist2 = re.sub(r"seq1", 'seq2', list1.id) if id1 == 'seq1' else re.sub(r"seq2", 'seq1', list1.id)
            id2 = re.sub(r"seq1", 'seq2', list1.children[list1.index].id) if id1 == 'seq1' else re.sub(r"seq2", 'seq1', list1.children[list1.index].id)
            list2 = self.get_widget_by_id(idlist2)
            item2 = self.get_widget_by_id(id2)
            diff_lines.append([seq, list2.id, list2.children.index(item2), copy.copy(item2), 'delete', ''])
            list2.pop(list2.children.index(item2))
            list2.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear()

    def action_delete(self) -> None:
        self.delete() 

    def replace_keep(self) -> None:
        list1 = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        # if list still has entries
        if type(list1.index) == int and len(list1.children) >= list1.index:
            repl = re.compile(r'seq\d_replace\d+', re.IGNORECASE) 
            if repl.match(list1.children[list1.index].id):
                self.replace()
            else:
                self.keep() 

    def action_replace_keep(self) -> None:
        self.replace_keep()

    def undo(self):
        target = self.textarea
        # If texteditor portion should undo before the selected parts of text should 
        if len(target.history.undo_stack) > 0 and (len(diff_lines) == 0 or not target.history.undo_stack[-1] == diff_lines[-1][-1]):
            target.move_cursor(target.history.undo_stack[-1][-1]._edit_result.end_location)
            target.undo()
            target.scroll_cursor_visible()
        elif len(diff_lines) > 0: 
            
            seq1 = self.get_widget_by_id('seq1') 
            if seq1.index:
                seq1.children[seq1.index].highlighted = False
            seq2 = self.get_widget_by_id('seq2')
            if seq2.index:
                seq2.children[seq2.index].highlighted = False  
            
            text1, id1, idx1, item1, type1, undostack_item1 = diff_lines.pop()
            undones.append([[text1, id1, idx1, item1, type1, undostack_item1]]) 
            if not type1 == 'delete':
                target.remove_diff()
            list1 = self.get_widget_by_id(id1)
            list1.insert(idx1, iter([item1]))
            for i in list1.children:
                i.highlighted = False
            list1.children[idx1].highlighted = True 
            list1.scroll_to_widget(list1.children[idx1]) 
            list1.calibrate_dimensions()        
          
            eq_rep = re.compile(r'^seq\d_replace\d+$', re.IGNORECASE) 
            comm = re.compile(r'^seq\d_common\d+$', re.IGNORECASE)
            # If diff_lines is still not empty 
            if len(diff_lines) > 0 and ((not type1 == 'keep' and eq_rep.match(item1.id) and eq_rep.match(diff_lines[-1][3].id)) or (comm.match(item1.id) and comm.match(diff_lines[-1][3].id))):
                text2, id2, idx2, item2, type2, undostack_item2 = diff_lines.pop()
                # undostack_item2 should be '' 
                undones[-1].append([text2, id2, idx2, item2, type2, undostack_item1]) 
                list2 = self.get_widget_by_id(id2)
                list2.insert(idx2, iter([item2]))
                for i in list2.children:
                    i.highlighted = False
                list2.children[idx2].highlighted = True 
                list2.scroll_to_widget(list2.children[idx2]) 
                list2.calibrate_dimensions()
           
            target.move_cursor((target.document.line_count - 1, 0)) 
            list1.scroll_item() 
            self.refresh_bindings()
            self.check_empty() 
        target.calibrate_dimensions()    
   
    def action_undo(self) -> None:
        self.undo() 

    def redo(self): 
      
        target = self.textarea
        # If texteditor portion should redo before the selected parts of text should 
        if len(target.history.redo_stack) > 0 and (len(undones) == 0 or not target.history.redo_stack[-1][0] == undones[-1][-1][5][0]): 
            target.move_cursor(target.history.redo_stack[-1][-1]._edit_result.end_location)
            target.redo()
            target.scroll_cursor_visible() 
        elif len(undones) > 0:
            
            target.scroll_end(animate=False) 
            
            full_undo = undones.pop()
            
            text1, id1, idx1, item1, type1, undostack_item1 = full_undo.pop(-1)
            if len(full_undo) > 0:
                text2, id2, idx2, item2, type2, undostack_item2 = full_undo.pop(-1)
            
            if undostack_item2 and isinstance(undostack_item2, list):
                undostack_item1 = undostack_item2 
            list1 = self.get_widget_by_id(id1) 
            list1.pop(list1.children.index(item1)) 
            list2 = self.get_widget_by_id(id2) 
            list2.pop(list2.children.index(item2)) 
            
            diff_lines.append([text1, id1, idx1, item1, type1, undostack_item1])
            if text2: 
                diff_lines.append([text2, id2, idx2, item2, type2, undostack_item1])
             
            comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 

            if not type1 == 'delete' and ((comm.match(item1.id) or type1 == 'keep' or type1 == 'replace')):
                target.redo()

            self.refresh_bindings()
            self.check_empty() 
        target.calibrate_dimensions()    
   
    def action_redo(self) -> None: 
        self.redo()

    def save(self): 
        
        target = self.textarea

        # If we're on linux, use zenity
        if self.output: 
            with open(self.output, 'w') as f:
                f.write(target.text)
                self.notify("File saved!", title="Saved") 
        else: 
            if platform.system() == 'Linux':
                result = subprocess.run(["zenity", "--file-selection", "--save","--filename=" + str(self.file_path1)], capture_output=True, text=True)
                filepath = result.stdout.strip()
                if filepath:
                    with open(filepath, 'w') as f:
                        f.write(target.text)
                        self.notify("File saved!", title="Saved") 
            
            # Otherwise default to PySide6
            else:
                app = QApplication.instance() or QApplication(sys.argv) 
                ext = str(Path(self.file_path1).suffix.lower()) 
                lang = str(guess_language(self.file_path1)) 
                if lang == 'unknown':
                    ext, lang = '',''
                if not lang == '' and not ext == '':
                    lang = lang.capitalize() + ' Files'     
                    lang = lang + " (*." + ext + ");;" 
                filepath, _ = QFileDialog.getSaveFileName(None, "Save file", str(self.file_path1), lang + "All files (*.*)")
                if filepath:
                    with open(filepath, 'w') as f:
                        f.write(target.text)
                        self.notify("File saved!", title="Saved") 

    def action_save(self) -> None: 
        self.save()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  
        # Check if an action may run.
        seq = False 
        x = re.compile(r'^seq[12]_replace\d+$', re.IGNORECASE) 
       
        # Try except clause because self.get_widget_by_id raises exception when not found
        # Which happens when opening command palette
        # Same with using queries. 
        # Afaik there doesn't seem to be a way to just 'check' whether self has a widget with a certain id without raising an exception if not found  
        try:
            mergeview = self.get_widget_by_id('mergeview')
    
            if self.get_widget_by_id('scrollview1').has_focus_within:
                list1 = self.get_widget_by_id('seq1') 
                h = list1.highlighted_child
                seq = True 
            elif self.get_widget_by_id('scrollview2').has_focus_within:
                list1 = self.get_widget_by_id('seq2')
                h = list1.highlighted_child
                seq = True
            
            if (action == "next_conflict" or action == 'scroll1' or action == 'sync' or action == 'replace_keep') and mergeview.has_focus_within:
                return False
            elif (action == 'scroll2' or action == 'select') and not mergeview.has_focus_within:
                return False
            if action == 'replace' and (not seq or h == None or not x.match(h.id)):
                return False
            if action == 'keep' and (not seq or len(list1.children) == 0):
                return False
            if action == 'delete' and (not seq or len(list1.children) == 0):
                return False 
            if action == "undo" and not diff_lines and not self.textarea.history.undo_stack:
                return False
            if action == "redo" and not self.textarea.history.redo_stack:
                return False
            if action == "save" and len(self.textarea.text) == 0:
                return False
        except:
            pass
       
        return True

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
        i, replace, rep, plus, min, com = 0, 0, 0, 0, 0, 0
        for line in sequence:

            if replace > 0:
                replace -= 1
            # Replace with ? based comments for both lines
            # - export VARIABLE='foo'
            # ?                  ^^^ 
            # + #export VARIABLE='bar'
            # ? +                 ^^^
            elif i+3 < len(sequence) and (line.startswith('- ') and str(sequence[i+1]).startswith('? ') and str(sequence[i+2]).startswith('+ ') and str(sequence[i+3]).startswith('? ')):
                seq.append(['seq1', [line], "seq1_replace" + str(rep)])
                seq.append(['seq2', [sequence[i+2]], "seq2_replace" + str(rep)])
                replace = 3 
                rep += 1
                seq1before, seq2before, commonbefore = False, False, False
            
            # Replace with ? based comment for one line
            # - export VARIABLE='foo'
            # + #export VARIABLE='foo'
            # ? + 
            elif i+2 < len(sequence) and (line.startswith('- ') and str(sequence[i+1]).startswith('+ ') and str(sequence[i+2]).startswith('? ')): 
                seq.append(['seq1', [line], "seq1_replace" + str(rep)])
                seq.append(['seq2', [sequence[i+1]], "seq2_replace" + str(rep)])
                replace = 2 
                rep += 1
                seq1before, seq2before, commonbefore = False, False, False
            
            # Replace without comments
            # - export GEM_HOME=$HOME/.gem/ruby/3.4.0
            # + #export GEM_HOME="$(ruby -e 'puts Gem.user_dir')"
            elif i+1 < len(sequence) and (line.startswith('- ') and str(sequence[i+1]).startswith('+ ')): 
                seq.append(['seq1', [line], "seq1_replace" + str(rep)])
                seq.append(['seq2', [sequence[i+1]], "seq2_replace" + str(rep)])
                replace = 1 
                rep += 1
                seq1before, seq2before, commonbefore = False, False, False
            
            elif line.startswith('- '):
                diffstr += line
                if not seq1before:
                    seq.append(['seq1', [line], 'min' + str(min)])
                    seq1before, seq2before, commonbefore = True, False, False
                    min += 1
                else: 
                    seq[len(seq)-1][1].append(line)
            elif line.startswith('+ '):
                diffstr += line
                if not seq2before:
                    seq.append(['seq2', [line], 'plus' + str(plus)])
                    seq1before, seq2before, commonbefore = False, True, False
                    plus += 1
                else: 
                    seq[len(seq)-1][1].append(line)
            elif line.startswith('  '):
                diffstr += line
                if not commonbefore:
                    seq.append(['common', [line], 'common' + str(com)])
                    seq1before, seq2before, commonbefore = False, False, True
                    com += 1
                else: 
                    seq[len(seq)-1][1].append(line)
            i += 1
        return seq
   
    
         

    def compose(self) -> ComposeResult:
        # A scrollable container for the file contents
        # yield Header()
       
        with VerticalGroup():
            yield Label(str(self.file_path1))
            with HorizontalScroll(id='scrollview1'):
                yield SideView(self.text1, 'seq1', self.slices1, self.richlang, self.richtheme)
            yield Label(str(self.file_path2))
            with HorizontalScroll(id='scrollview2'):
                yield SideView(self.text2, 'seq2', self.slices2, self.richlang, self.richtheme)
        yield self.textarea
       
        yield Footer()

def main():
    choices = argcomplete.completers.ChoicesCompleter
    parser = argparse.ArgumentParser(description="Merge files 2-way",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v','--version', action='version', version='Mergepy: {version}'.format(version=__version__))
    parser.add_argument("-o","--output", required=False, help="Output file of the merge", metavar="output file")
    parser.add_argument("-a","--automerge-common", type=bool, default=True, required=False, help="Automatically merge common blocks", metavar="automerge")
    parser.add_argument("-f","--file-theme", required=False, choices=['ansi_dark', 'ansi_light', 'bw', 'sas', 'staroffice', 'xcode', 'default', 'monokai', 'lightbulb', 'github-dark', 'rrt', 'abap', 'algol', 'algol_nu', 'arduino', 'autumn', 'borland', 'colorful', 'igor', 'lovelace', 'murphy', 'pastie', 'rainbow_dash', 'sata-light', 'stata-dark', 'trac', 'vs', 'emacs', 'tango', 'solarized-light', 'solarized-dark', 'manni', 'gruvbox', 'gruvbox-light', 'gruvbox-dark', 'friendly', 'friendly_grayscale', 'perldoc', 'paraiso-light', 'paraiso-dark', 'zenburn', 'nord', 'nord-darker', 'material', 'one-dark', 'dracula', 'coffee', 'native', 'inkpot', 'fruity', 'vim'],  default='ansi_dark', help="""Syntax theme of the two files. 
    Should be the name of a Pygments theme, or a special case name like 'ansi_dark/ansi_light'. 
    Refer to: https://pygments.org/styles/ for reference.""", metavar="filetheme")
    parser.add_argument("-l","--language", required=False, choices=["python","javascript","typescript","json","java","cpp","c","html","css","ruby","php","rust","go","swift","yaml","bash","zsh"], help="""Language to parse for the editor portion (merge).""", metavar="mergelanguage") 
    parser.add_argument("-e","--editor-theme", required=False, choices=TextArea().available_themes, default='css', help="""Syntax theme of the editor portion (merge). Available options are: 'css', 'dracula', 'vscode_dark', 'github_light', 'monokai'""", metavar="mergetheme") 
    parser.add_argument("file1", type=Path, help="First file to be merged", metavar="file1")
    parser.add_argument("file2", type=Path, help="Second file to be merged", metavar="file2")
    output_stream = None
    if "_ARGCOMPLETE_POWERSHELL" in os.environ:
        output_stream = codecs.getwriter("utf-8")(sys.stdout.buffer)
    argcomplete.autocomplete(parser, output_stream=output_stream)
    args = parser.parse_args() 
    
    if hasattr(args, ' version'):
        print('Mergepy: {version}'.format(version=__version__))
    
    if not args.file1.is_file():
        raise FileNotFoundError("%s doesn't exists or is not a file" % sys.argv[1])
    elif os.path.getsize(args.file1) == 0: 
        raise FileNotFoundError("%s is empty" % sys.argv[1])
    elif not args.file2.is_file():
        raise FileNotFoundError("%s doesn't exists or is not a file" % sys.argv[2])
    elif os.path.getsize(args.file2) == 0: 
        raise FileNotFoundError("%s is empty" % sys.argv[2])
    else:
        file1=os.path.abspath(args.file1)
        file2=os.path.abspath(args.file2)
        argumnts = {"file_path1" : file1, "file_path2" : file2} 
        output = os.path.abspath(args.output) if args.output else None 
        argumnts["output"] = output
        if args.automerge_common:
            argumnts["automerge"] = args.automerge_common
        if args.file_theme:
            argumnts["richtheme"] = args.file_theme
        if args.language:
            argumnts["language"] = args.language
        if args.editor_theme:
            argumnts["mergetheme"] = args.editor_theme
        MergePy(**argumnts).run()

if __name__ == "__main__":
    main()

