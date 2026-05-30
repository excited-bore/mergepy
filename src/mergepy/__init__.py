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
from textual.widgets import Label, Footer, Header, Static, Button, ListItem, ListView
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.syntax import Syntax
from rich.style import Style
from PySide6.QtWidgets import QApplication, QFileDialog

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

# diff_lines = [ text, id, index, widget, action_name ]

diff_lines = []

# undones = [ [ [ text1, id1, index1, widget1, action_name1 ], [ text2, id2, index2, widget2, action_name2 ] ], ... ] 

undones = []

class Slice(ListItem):
    """Base class for diff slices."""

    def __init__(self, seq, id, linerange, diff, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.id = id
        self.linerange = linerange
        self.diff = diff
        self.lang = lang
        self.theme = theme
        self.width = max(len(line) for line in self.seq.splitlines())

    def action_focus_item(self) -> None:
        pattern = re.compile(r"^seq1_*")
        if pattern.match(self.id):
            type, type1 = 'seq2', 'scrollview2'
            result = re.sub(r"^seq1_", "seq2_", self.id)
        else:
            type, type1 = 'seq1', 'scrollview1'
            result = re.sub(r"^seq2_", "seq1_", self.id)

        self.parent.parent.parent.scroll_to_widget(self, center=True)

        try:
            target = self.parent.parent.parent.parent.get_widget_by_id(result, Slice)
            target1 = self.parent.parent.parent.parent.get_widget_by_id(type1)
            listView = self.parent.parent.parent.parent.get_widget_by_id(type, SideView)
            target1.scroll_to_widget(target, center=True, force=True)
            index = listView.children.index(target)
            listView.index = index
        except:
            pass

    def on_click(self) -> None:
        self.action_focus_item()


class DiffSlice(Slice):
    """Highlights Diff Slice."""

    def __init__(self, seq, id, linerange, diff, lang, theme, **kwargs) -> None:
        super().__init__(seq, id, linerange, diff, lang, theme, **kwargs)
        self.classes = re.sub(r'.*_(replace)\d+', r'\1', id)
        self.height = (linerange[1] - linerange[0]) + 3
        self.styles.height = (linerange[1] - linerange[0]) + 3
        self.virtual_size = Size(self.width, self.height)

    def render(self) -> RenderResult:
        syntax = Syntax(self.seq, self.lang, theme=self.theme, line_range=self.linerange, line_numbers=True, indent_guides=True)
        return syntax


class CommonSlice(Slice):
    """Common Slice."""

    def __init__(self, seq, id, linerange, diff, lang, theme, **kwargs) -> None:
        super().__init__(seq, id, linerange, diff, lang, theme, **kwargs)
        self.height = (linerange[1] - linerange[0]) + 1
        self.styles.height = (linerange[1] - linerange[0]) + 1
        self.virtual_size = Size(self.width, self.height)

    def render(self) -> RenderResult:
        syntax = Syntax(self.seq, self.lang, line_range=self.linerange, theme=self.theme, line_numbers=True, indent_guides=True)
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
        for i in self.seq2:
            if x.match(i[2]):
                h += 2
        self.height = self.seq.count("\n") + 1 + h if self.seq else 0
        self.styles.height = "auto"
        self.width = max(len(line) for line in self.seq.splitlines())
        self.styles.width = self.width
        self.virtual_size = Size(self.width, self.height)
        self.get_index()

    def __init__(self, seq, id, seq2, diff, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seq = seq
        self.id = id
        self.index = 0
        self.seq2 = seq2
        self.diff = diff
        self.lang = lang
        self.theme = theme
        self.calibrate_dimensions()
    
    def scroll_item(self) -> None:
        self.children[self.index].action_focus_item()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == 'space': 
            self.scroll_item()
        elif event.key == 'up' and self.index-1 >= 0:
            self.parent.scroll_to_widget(self.children[self.index-1], center=True)
        elif event.key == 'down' and self.index+1 <= len(self.children) - 1:
            self.parent.scroll_to_widget(self.children[self.index+1], center=True)
        elif event.key == 'left' or event.key == 'ctrl+left' or event.key == 'right' or event.key == 'ctrl+right':
            self.parent.parent.parent.get_widget_by_id('mergeview').focus()
        elif event.key == 'shift+up':
            self.parent.scroll_up()
        elif event.key == 'shift+down':
            self.parent.scroll_down()
        elif event.key == 'shift+left':
            self.parent.scroll_page_left()
        elif event.key == 'shift+right':
            self.parent.scroll_page_right()
        elif event.key == 'ctrl+up' or event.key == 'ctrl+down':
            seq1 = self.parent.parent.get_widget_by_id('seq1')
            seq2 = self.parent.parent.get_widget_by_id('seq2')
            if self.id == 'seq1' and len(seq2.children) >= 1:
                self.parent.parent.get_widget_by_id('seq2').focus()
            elif self.id == 'seq2' and len(seq1.children) >= 1:
                self.parent.parent.get_widget_by_id('seq1').focus()
                
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
        for i in self.seq2:
            j = i.copy()
            if x.match(i[2]):
                yield DiffSlice(self.seq, j[2], j[3], self.diff, self.lang, self.theme)
            else:
                yield CommonSlice(self.seq, i[2], i[3], self.diff, self.lang, self.theme)



class MergeView(ScrollView):   

    text = reactive('')

    def calibrate_dimensions(self) -> None:
        self.height = self.text.count("\n") + 2 if not self.text == '' else 0
        self.styles.height = self.height
        self.width = max(len(line) for line in self.text.splitlines()) if self.text else 0
        self.styles.width = self.width
        self.virtual_size = Size(self.width, self.height)

    def __init__(self, text, lang, theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lang = lang
        self.id = 'mergeview'
        self.text = text
        self.theme = theme
        self.calibrate_dimensions()
    
    def on_key(self, event: events.Key) -> None:
        if event.key == 'ctrl+left' or event.key == 'ctrl+right':
            seq1 = self.parent.parent.get_widget_by_id('seq1') 
            seq2 = self.parent.parent.get_widget_by_id('seq2') 
            if len(seq1.children) >= 1: 
                self.parent.parent.get_widget_by_id('seq1').focus()
            elif len(seq2.children) >= 1:
                self.parent.parent.get_widget_by_id('seq2').focus()
        elif event.key == 'up': 
            self.parent.scroll_up()
        elif event.key == 'shift+up':
            self.parent.scroll_up()
        elif event.key == 'down':
            self.parent.scroll_down()
        elif event.key == 'shift+down':
            self.parent.scroll_down()
        elif event.key == 'shift+left':
            self.parent.scroll_left()
        elif event.key == 'shift+right':
            self.parent.scroll_right()
           
    def add_diff(self, text) -> None:
        self.text += text
        self.calibrate_dimensions()
        self.parent.scroll_end()

    def remove_diff(self, range) -> None:
        self.text = "\n".join(self.text.splitlines()[:-range]) + '\n'
        self.calibrate_dimensions() 

    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        # syntax = Syntax.from_path(self.filepath, line_numbers=True, indent_guides=True, word_wrap=True, highlight_lines=[7,8])
        #syntax = Syntax(self.seq, self.lang, theme=self.theme, line_range=self.linerange, line_numbers=True, indent_guides=True)
         
        syntax = Syntax(self.text, self.lang, theme=self.theme, line_numbers=True, indent_guides=True, word_wrap=True)
        return syntax         

class MergePy(App):
    
    CSS_PATH = "merge.tcss"

    # ("space", "nothing('2')", "Select Conflict")
    BINDINGS = [
        ("Ctrl-↑/↓/←/→", "   ", "Next window"),
        ("Shift-↑/↓/←/→", "    ", "Scroll"),
        ("Alt-↑/↓", "next_conflict", "Next Conflict"),
        ("Spacebar", "sync", "Sync"),
        ("Enter", "replace_keep", "Replace/Keep"),
        ("r", "replace", "Replace Block"),
        ("k", "keep", "Keep Block"),
        ("d", "delete", "Delete Block"),
        ("q", "quit", "Quit"),
        ("ctrl+z", "undo", "Undo"),
        ("ctrl+y", "redo", "Redo"),
        ("ctrl+s", "save", "Save"),
     ]

    def on_mount(self) -> None:
        self.title = 'diff ' + str(self.file_path1) + ' ' + str(self.file_path2)
    
    def on_key(self, event: events.Key) -> None:
        # Try and except otherwise command palette freaks out 
        try: 
            if not self.get_widget_by_id('mergeview').has_focus_within: 
                 
                if not (event.key == 'shift+up' or event.key == 'shift+down' or event.key == 'shift+left' or event.key == 'shift+right'): 
                    self.refresh_bindings()
                if event.key == 'enter':
                    self.action_replace_keep()
        except:
            pass

    def on_click(self) -> None:
        try: 
            if self.get_widget_by_id('scrollview3').has_focus:
                self.get_widget_by_id('mergeview').focus()
            self.refresh_bindings()
        except:
            # Command palette open 
            pass

    def check_empty(self) -> None:
        seq1 = self.get_widget_by_id('seq1') 
        seq2 = self.get_widget_by_id('seq2') 
        mergeview = self.get_widget_by_id('mergeview') 
   
        if len(seq1.children) < 2 and len(seq2.children) > 2:
            seq2.focus() 
        elif len(seq1.children) > 2 and len(seq2.children) < 2:
            seq1.focus() 
        elif len(seq1.children) < 2 and len(seq2.children) < 2 and not mergeview.text == '':
            mergeview.focus()

    def action_next_conflict(self) -> None: 
        list = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2') 
        for i in list.children:
            pttrn = re.compile(r'.*replace.*')
            if pttrn.match(i.id) and list.children.index(i) > list.index:
                list.index = list.children.index(i)
                list.scroll_item()
                break
     
    def action_sync(self) -> None:
        list = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        list.scroll_item()

    def action_replace(self) -> None:
        target = self.get_widget_by_id('mergeview', MergeView)
        list = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        
        list2 = self.get_widget_by_id('seq2') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq1')
        id = 'seq2' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq1'
        id = id + '_' + str(re.sub(r'.*_', '', list.children[list.index].id)) 
        diffv = self.get_widget_by_id(id)
        seq, seq2 = '', ''

        range = list.children[list.index].linerange
        for num, line in enumerate(list.children[list.index].seq.splitlines(), 1):
            if num >= range[0] and num <= range[1]:
                seq += line[2:] + '\n'
        diff_lines.append([seq, list.id, list.index, copy.copy(list.children[list.index]), 'replace'])
        list.pop(list.index)
        
        range = diffv.linerange
        for num, line in enumerate(diffv.seq.splitlines(), 1):
            if num >= range[0] and num <= range[1]:
                seq2 += line[2:] + '\n'
        diff_lines.append([seq2, list2.id, list2.children.index(diffv), copy.copy(diffv), 'replace'])
        list2.pop(list2.children.index(diffv))
        target.add_diff(seq)
        
        list.calibrate_dimensions()
        list2.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear() 

    def action_keep(self) -> None:
        target = self.get_widget_by_id('mergeview', MergeView)
        seq = ''
        id = 'seq1' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq2'
        list = self.get_widget_by_id('seq1') if id == 'seq1' else self.get_widget_by_id('seq2')
        
        range = list.children[list.index].linerange
        for num, line in enumerate(list.children[list.index].seq.splitlines(), 1):
            if num >= range[0] and num <= range[1]:
                seq += line[2:] + '\n'
        
        item = list.children[list.index]

        diff_lines.append([seq, list.id, list.index, copy.copy(item), 'keep'])
        target.add_diff(seq)
        
        comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 
        if comm.match(list.children[list.index].id):
            idlist2 = re.sub(r"seq1", 'seq2', list.id) if id == 'seq1' else re.sub(r"seq2", 'seq1', list.id)
            list2 = self.get_widget_by_id(idlist2)
            
            id2 = list.children[list.index].id 
            id2 = re.sub(r"seq1", 'seq2', id2) if id == 'seq1' else re.sub(r"seq2", 'seq1', id2)
            item2 = self.get_widget_by_id(id2)
            idx2 = list2.children.index(item2) 

            diff_lines.append([seq, list2.id, idx2, copy.copy(item2), 'keep'])
            list2.pop(idx2)
            list2.calibrate_dimensions()

        list.pop(list.index)
        list.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear() 

    def action_delete(self) -> None:
        seq = ''
        list = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        
        id = 'seq1' if self.get_widget_by_id('scrollview1').has_focus_within else 'seq2'
        range = list.children[list.index].linerange
        for num, line in enumerate(list.children[list.index].seq.splitlines(), 1):
            if num >= range[0] and num <= range[1]:
                seq += line[2:] + '\n'
        diff_lines.append([seq, list.id, list.index, copy.copy(list.children[list.index]), 'delete'])
        list.pop(list.index)
        list.calibrate_dimensions()
        comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 
        if comm.match(list.children[list.index].id):
            idlist2 = re.sub(r"seq1", 'seq2', list.id) if id == 'seq1' else re.sub(r"seq2", 'seq1', list.id)
            id2 = re.sub(r"seq1", 'seq2', list.children[list.index].id) if id == 'seq1' else re.sub(r"seq2", 'seq1', list.children[list.index].id)
            list2 = self.get_widget_by_id(idlist2)
            item2 = self.get_widget_by_id(id2)
            diff_lines.append([seq, list2.id, list2.children.index(item2), copy.copy(item2), 'delete'])
            list2.pop(list2.children.index(item2))
            list2.calibrate_dimensions()
        
        self.refresh_bindings()
        self.check_empty() 
        undones.clear()

    def action_replace_keep(self) -> None:
        list = self.get_widget_by_id('seq1') if self.get_widget_by_id('scrollview1').has_focus_within else self.get_widget_by_id('seq2')
        # if list still has entries
        if type(list.index) == int and len(list.children) >= list.index:
            repl = re.compile(r'seq\d_replace\d+', re.IGNORECASE) 
            if repl.match(list.children[list.index].id):
                self.action_replace()
            else:
                self.action_keep() 

    def action_undo(self) -> None:
        eq_rep = re.compile(r'^seq\d_replace\d+$', re.IGNORECASE) 
        comm = re.compile(r'^seq\d_common\d+$', re.IGNORECASE)
        if len(diff_lines) > 0: 
            seq1 = self.get_widget_by_id('seq1') 
            if seq1.index:
                seq1.children[seq1.index].highlighted = False
            seq2 = self.get_widget_by_id('seq2')
            if seq2.index:
                seq2.children[seq2.index].highlighted = False  
            target = self.get_widget_by_id('mergeview', MergeView)
            
            text, id, idx, item, type = diff_lines.pop()
            undones.append([[text, id, idx, item, type]]) 
            range = len(text.splitlines())
            if not type == 'delete':
                target.remove_diff(range)
            item.highlighted = False
            list = self.get_widget_by_id(id)
            list.insert(idx, iter([item]))
            list.calibrate_dimensions()        
           
            # If diff_lines is still not empty 
            if len(diff_lines) > 0 and ((not type == 'keep' and eq_rep.match(item.id) and eq_rep.match(diff_lines[-1][3].id)) or (comm.match(item.id) and comm.match(diff_lines[-1][3].id))):
                text1, id1, idx1, item1, type1 = diff_lines.pop()
                undones[-1].append([text1, id1, idx1, item1, type1]) 
                item1.highlighted = False
                list1 = self.get_widget_by_id(id1)
                list1.insert(idx1, iter([item1]))
                list1.calibrate_dimensions()
            
            self.refresh_bindings()
            self.check_empty() 
   

    def action_redo(self) -> None: 
      
        target = self.get_widget_by_id('mergeview', MergeView)
         
        if len(undones) > 0:
            
            full_undo = undones.pop()
           
            def redo(first):
                text, id, idx, item, type = full_undo.pop(-1)
                list = self.get_widget_by_id(id) 
                list.pop(list.children.index(item)) 
                diff_lines.append([text, id, idx, item, type]) 
                comm = re.compile(r'seq\d_common\d+', re.IGNORECASE) 
                if not type == 'delete' and ((first and (comm.match(item.id) or type == 'keep' or type == 'replace'))):
                    target.add_diff(text) 

            redo(True) 
            
            if len(full_undo) > 0:
     
                redo(False)
             
            self.refresh_bindings()
            self.check_empty() 
   
    def action_save(self) -> None: 
        target = self.get_widget_by_id('mergeview', MergeView) 
        
        # If were on linux, use zenity
        if platform.system() == 'Linux':
            result = subprocess.run(["zenity", "--file-selection", "--save","--filename=" + str(self.file_path1)], capture_output=True, text=True)
            filepath = result.stdout.strip()
            if filepath:
                with open(filepath, 'w') as f:
                    f.write(target.text)
        
        # Otherwise default to PySide6
        else:
            app = QApplication.instance() or QApplication(sys.argv) 
            ext = str(Path(self.file_path1).suffix.lower()) 
            lang = str(guess_language(self.file_path1)) 
            if lang == 'unknown':
                ext, lang = '' ''
            if not lang == '' and not ext == '':
                lang = lang.capitalize() + ' Files'     
                lang = lang + " (*." + ext + ");;" 
            filepath, _ = QFileDialog.getSaveFileName(None, "Save file", str(self.file_path1), lang + "All files (*.*)")
            if filepath:
                with open(filepath, 'w') as f:
                    f.write(target.text)


    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  
        # Check if an action may run.
        seq = False 
        x = re.compile(r'^seq[12]_replace\d+$', re.IGNORECASE) 
       
        # Try except clause because self.get_widget_by_id raises exception when not found
        # Which happens when opening command palette
        # Same with using queries. 
        # Afaik there doesn't seem to be a way to just 'check' whether self has a widget with a certain id without raising an exception if not found  
        try:
            mergeview = self.get_widget_by_id('scrollview3')
    
            if self.get_widget_by_id('scrollview1').has_focus_within:
                list = self.get_widget_by_id('seq1') 
                h = list.highlighted_child
                seq = True 
            elif self.get_widget_by_id('scrollview2').has_focus_within:
                list = self.get_widget_by_id('seq2')
                h = list.highlighted_child
                seq = True
            
            if (action == "next_conflict" or action == 'sync' or action == 'replace_keep') and mergeview.has_focus_within:
                return False
            if action == 'replace' and (not seq or h == None or not x.match(h.id)):
                return False
            if action == 'keep' and (not seq or len(list.children) == 0):
                return False
            if action == 'delete' and (not seq or len(list.children) == 0):
                return False 
            if action == "undo" and len(diff_lines) == 0:
                return False
            if action == "redo" and len(undones) == 0:
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
   
    diff = reactive('') 

    def __init__(self, file_path1: Path, file_path2: Path, **kwargs):
        super().__init__(**kwargs)

        self.file_path1 = file_path1
        self.file_path2 = file_path2
        
        with open(self.file_path1) as self_file:
            text1 = self_file.read()
        
        with open(self.file_path2) as self_file:
            text2 = self_file.read()
        
        self.seq=self.show_diff(text1, text2)
        
        if Path(self.file_path1).suffix:
            self.lang = guess_language(self.file_path1)
        elif Path(self.file_path2).suffix:
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
                i[2] = 'seq1_' + i[2]
                j[2] = 'seq2_' + j[2]
                self.seq12.append(i)
                self.seq22.append(j)

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
         

    def compose(self) -> ComposeResult:
        # A scrollable container for the file contents
        # yield Header()
       
        with VerticalGroup():
            yield Label(str(self.file_path1))
            with HorizontalScroll(id='scrollview1'):
                yield SideView(self.seq1, 'seq1', self.seq12, self.diff, self.lang, 'ansi_dark')
            yield Label(str(self.file_path2))
            with HorizontalScroll(id='scrollview2'):
                yield SideView(self.seq2, 'seq2', self.seq22, self.diff, self.lang, 'ansi_dark')
        with ScrollableContainer(id='scrollview3'):
            yield MergeView(self.diff, self.lang, 'ansi_dark')
       
        yield Footer()

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
        MergePy(file1, file2).run()

if __name__ == "__main__":
    main()
