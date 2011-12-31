import sublime, sublime_plugin
import urllib, urllib2
import os
import threading
import zipfile

class FetchCommand(sublime_plugin.WindowCommand):
    fileList = []
    packageList = []
    s = None
    packageUrl = None

    def __init__(self, *args, **kwargs):
        super(FetchCommand, self).__init__(*args, **kwargs)


    def run(self):
        self.s = sublime.load_settings('Fetch.sublime-settings')
        self.fileList = []
        self.packageList = []

        options = ['Single file', 'Package file']

        self.window.show_quick_panel(options, self.callback)

    def callback(self, index):
        if (index == 0):
            self.list_files()
        elif (index == 1):
            self.list_packages()
    
    def list_packages(self):
        packages = self.s.get('packages')
        if not packages:
            self.s.set('packages', {"html5-boilerplate" : "http://github.com/h5bp/html5-boilerplate/zipball/v2.0stripped"})
            sublime.save_settings('Fetch.sublime-settings')
            packages = self.s.get('packages')

        for name, url in packages.iteritems():
            self.packageList.append([name, url])

        self.window.show_quick_panel(self.packageList , self.set_package_location)

    def set_package_location(self, index):
        if (index > -1):
            self.packageUrl = self.packageList[index][1]

            self.window.show_input_panel(
                "Select a location to extract the files: ", 
                self.window.folders()[0], 
                self.get_package,
                None,
                None
            )

    def get_package(self, location):
        os.makedirs(location) if not os.path.exists(location) else None;
        if not os.path.exists(location):
            return False
        else:
            self.window.active_view().run_command("fetch_extract_package", {"url": self.packageUrl, "location": location})

    def list_files(self):
        files = self.s.get('files')

        if not files:
            self.s.set('files', {"jquery" : "http://code.jquery.com/jquery.min.js"})
            sublime.save_settings('Fetch.sublime-settings')
            files = self.s.get('files')

        for name, url in files.iteritems():
            self.fileList.append([name, url])

        self.window.show_quick_panel(self.fileList , self.get_file)
    
    def get_file(self, index):
        if (index > -1):
            url = self.fileList[index][1]
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
            sublime.status_message("The file was successfully fetched from " + url)


class FetchExtractPackageCommand(sublime_plugin.TextCommand):
    result = None
    url = None
    location = None

    def run(self, edit, url, location):
        self.url = url
        self.location = location

        threads = []
        thread = FetchDownload(url, location, 5)
        threads.append(thread)
        thread.start()
        self.handle_threads(edit, threads)

    def handle_threads(self, edit, threads, offset=0, i=0, dir=1):
        next_threads = []
        for thread in threads:
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
            self.view.set_status('fetch', 'Downloading package from %s [%s=%s] ' % \
                (self.url ,' ' * before, ' ' * after))

            sublime.set_timeout(lambda: self.handle_threads(edit, threads,
                 offset, i, dir), 100)
            return

        self.view.erase_status('fetch')
        sublime.status_message('The package from %s was successfully downloaded and extracted' %
            (self.url))


class FetchDownload(threading.Thread):
    def __init__(self, url, location, timeout):
        self.url = url
        self.location = location
        self.timeout = timeout
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        try:
            urllib2.install_opener(urllib2.build_opener(urllib2.ProxyHandler()));
            finalLocation = os.path.join(self.location, '_fetch_package.zip')
            request = urllib2.Request(self.url)
            response = urllib2.urlopen(request, timeout=self.timeout)
            output = open(finalLocation,'wb')
            output.write(response.read())
            output.close()

            zip_file = zipfile.ZipFile(finalLocation, 'r')
            zip_file.extractall(self.location)
            zip_file.close()
            os.remove(finalLocation)
            
            self.result = True
            return

        except (urllib2.HTTPError) as (e):
            err = '%s: HTTP error %s contacting server' % (__name__, str(e.code))
        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting server' % (__name__, str(e.reason))

        sublime.error_message(err)
        self.result = False
