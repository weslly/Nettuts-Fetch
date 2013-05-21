import sublime
import sublime_plugin


sublime_version = 2

if not sublime.version() or int(sublime.version()) > 3000:
    sublime_version = 3

try:
    # Python 3
    from .fetch.commands.fetch_command import FetchCommand
    from .fetch.commands.fetch_get_command import FetchNewFileCommand
    from .fetch.commands.fetch_get_command import FetchGetCommand

except (ValueError):
    # Python 2
    from fetch.commands.fetch_command import FetchCommand
    from fetch.commands.fetch_get_command import FetchNewFileCommand
    from fetch.commands.fetch_get_command import FetchGetCommand

