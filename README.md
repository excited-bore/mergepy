# `mergepy`

>[!important]
> TODO: Implement compatibility with git so it can be used as a mergetool 

## ℹ️ About

Mergepy is a cli-based python tool designed to merge 2 files together interactively by segmenting the 2 files into parts that are different and common. You easily select, then choose to keep or replace the conflicts by jumping between 2 panes and pressing enter (which will always replace a different part of the file and keep a common part) which will insert the selected text into a third pane which can be also used to edit the result. Mergepy uses python's standard 'difflib' to segment the files and uses textual, uses a rich renderable to highlight the syntax for the 2 file panes and uses treesitter to highlight the syntax in the editor pane.

