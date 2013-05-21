import sublime
import sublime_plugin
import threading
from ..downloader import Downloader


class FetchNewFileCommand(sublime_plugin.TextCommand):
    def run(self, edit, txt):
        for sel in self.view.sel():
            self.view.replace(edit, sel, txt)


class FetchGetCommand(sublime_plugin.TextCommand):
    result = None
    url = None
    location = None
    option = None

    def run(self, edit, option, url, location=None):
        self.url = url
        self.location = location
        self.option = option

        threads = []
        thread = Downloader(url, option, location, 5)
        threads.append(thread)
        thread.start()
        self.handle_threads(edit, threads)

    def handle_threads(self, edit, threads, offset=0, i=0, dir=1):
        status = None
        next_threads = []
        for thread in threads:
            status = thread.result
            txt = thread.txt
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result == False:
                continue

        threads = next_threads

        if len(threads):
            # This animates a little activity indicator in the status area
            before = i % 8
            after = (7) - before

            if not after:
                dir = -1
            if not before:
                dir = 1

            i += dir
            sublime.status_message('Downloading file from %s [%s=%s] ' % \
                (self.url, ' ' * before, ' ' * after))

            sublime.set_timeout(lambda: self.handle_threads(edit, threads,
                 offset, i, dir), 100)
            return

        self.view.erase_status('fetch')
        if status and self.option == 'package':
            sublime.status_message(('The package from %s was successfully' +
                                   ' downloaded and extracted') % self.url)

        elif status and self.option == 'txt':
            new_file = sublime.active_window().active_view()
            new_file.run_command('fetch_new_file', {'txt': txt})

            sublime.status_message(('The file was successfully downloaded' +
                                   ' from %s') % self.url)

