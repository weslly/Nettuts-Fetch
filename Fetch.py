import sublime
import sublime_plugin
import urllib
import urllib2


class FetchCommand(sublime_plugin.WindowCommand):
    fetchList = []
    def __init__(self, *args, **kwargs):
        super(FetchCommand, self).__init__(*args, **kwargs)


    def run(self):
        s = sublime.load_settings('Fetch.sublime-settings')
        files = s.get('files')
        self.fetchList = []
        for name, url in files.iteritems():
            self.fetchList.append([name, url])
            
        self.window.show_quick_panel(self.fetchList , self.callback, sublime.MONOSPACE_FONT)

    def callback(self, index):
        if (index > -1):
            url = self.fetchList[index][1]
            self.window.active_view().run_command("fetch_insert_file", {"url": url})

class FetchInsertFileCommand(sublime_plugin.TextCommand):
    result = None
    def run(self, edit, url):
        try:
            request = urllib2.Request(url)
            http_file = urllib2.urlopen(request, timeout=5)
            self.result = unicode(http_file.read(), 'utf-8')

        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting API' % (__name__, str(e.reason))
            sublime.error_message(err)

        for region in self.view.sel():
            self.view.replace(edit, region, self.result)