import sublime
import sublime_plugin
import urllib
import urllib2
import os
import sys
import threading
import zipfile
import re
import subprocess

try:
    import ssl
except (ImportError):
    pass


class FetchCommand(sublime_plugin.WindowCommand):
    fileList = []
    packageList = []
    s = None
    packageUrl = None

    filesPlaceholder = {"jquery": "http://code.jquery.com/jquery.min.js"}
    packagesPlaceholder = {"html5_boilerplate":
                    "https://github.com/h5bp/html5-boilerplate/zipball/master"}

    def __init__(self, *args, **kwargs):
        super(FetchCommand, self).__init__(*args, **kwargs)

        s = sublime.load_settings('Fetch.sublime-settings')
        if not s.has('packages'):
            s.set('packages', self.packagesPlaceholder)
        if not s.has('files'):
            s.set('files', self.filesPlaceholder)
        sublime.save_settings('Fetch.sublime-settings')

    def run(self, *args, **kwargs):
        _type = kwargs.get('type', None)
        self.s = sublime.load_settings('Fetch.sublime-settings')
        self.fileList = []
        self.packageList = []

        if _type == 'single':
            self.list_files()
        elif _type == 'package':
            self.list_packages()
        else:
            options = ['Single file', 'Package file']
            self.window.show_quick_panel(options, self.callback)

    def callback(self, index):
        if not self.window.views():
            self.window.new_file()

        if (index == 0):
            self.list_files()
        elif (index == 1):
            self.list_packages()

    def list_packages(self):
        packages = self.s.get('packages')
        if not packages:
            self.s.set('packages', self.packagesPlaceholder)
            sublime.save_settings('Fetch.sublime-settings')
            packages = self.s.get('packages')

        for name, url in packages.iteritems():
            self.packageList.append([name, url])

        self.window.show_quick_panel(self.packageList,
                                     self.set_package_location)

    def set_package_location(self, index):
        if (index > -1):
            self.packageUrl = self.packageList[index][1]

            if not self.window.folders():
                initialFolder = os.path.expanduser('~')
                try:
                    from win32com.shell import shellcon, shell
                    initialFolder = shell.SHGetFolderPath(0,
                                    shellcon.CSIDL_APPDATA, 0, 0)

                except ImportError:
                    initialFolder = os.path.expanduser("~")

            else:
                initialFolder = self.window.folders()[0]

            self.window.show_input_panel(
                "Select a location to extract the files: ",
                initialFolder,
                self.get_package,
                None,
                None
            )

    def get_package(self, location):
        if not os.path.exists(location):
            try:
                os.makedirs(location)
            except:
                sublime.error_message('ERROR: Could not create directory.')
                return False

        self.window.active_view().run_command("fetch_get", {"option":
                    "package", "url": self.packageUrl, "location": location})

    def list_files(self):
        files = self.s.get('files')

        if not files:
            self.s.set('files', self.filesPlaceholder)
            sublime.save_settings('Fetch.sublime-settings')
            files = self.s.get('files')

        for name, url in files.iteritems():
            self.fileList.append([name, url])

        self.window.show_quick_panel(self.fileList, self.get_file)

    def get_file(self, index):
        if (index > -1):
            url = self.fileList[index][1]
            self.window.active_view().run_command("fetch_get",
                                                 {"option": "txt", "url": url})


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
        thread = FetchDownload(url, option, location, 5)
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
            for region in self.view.sel():
                self.view.replace(edit, region, txt)

            sublime.status_message(('The file was successfully downloaded' +
                                   ' from %s') % self.url)


class FetchDownload(threading.Thread):
    def __init__(self, url, option, location, timeout):
        self.url = url
        self.location = location
        self.timeout = timeout
        self.option = option
        self.result = None
        self.txt = None
        threading.Thread.__init__(self)

    def run(self):
        if self.option == 'txt':
            self.download_text()
        elif self.option == 'package':
            self.download_package()

    def download_text(self):
        try:
            downloaded = False
            has_ssl = 'ssl' in sys.modules
            if has_ssl:
                request = urllib2.Request(self.url)
                http_file = urllib2.urlopen(request, timeout=self.timeout)
                self.txt = unicode(http_file.read(), 'utf-8')
                downloaded = True

            else:
                clidownload = CliDownloader()
                if clidownload.find_binary('wget'):
                    command = [clidownload.find_binary('wget'),
                                '--connect-timeout=' + str(int(self.timeout)),
                                self.url, '-qO-']
                    self.txt = unicode(clidownload.execute(command), 'utf-8')
                    downloaded = True

                elif clidownload.find_binary('curl'):
                    command = [clidownload.find_binary('curl'),
                                '--connect-timeout', str(int(self.timeout)),
                                '-L', '-sS', self.url]
                    self.txt = unicode(clidownload.execute(command), 'utf-8')
                    downloaded = True

            if not downloaded:
                sublime.error_message('Unable to download ' + self.url +
                            ' due to no ssl module available and no capable' +
                            ' program found. Please install curl or wget.')
                return False
            else:
                self.result = True

        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting API' % (__name__, str(e.reason))
            sublime.error_message(err)

    def download_package(self):
        downloaded = False
        try:
            finalLocation = os.path.join(self.location, '__tmp_package.zip')
            has_ssl = 'ssl' in sys.modules

            if has_ssl:
                urllib2.install_opener(
                    urllib2.build_opener(urllib2.ProxyHandler()))
                request = urllib2.Request(self.url)
                response = urllib2.urlopen(request, timeout=self.timeout)
                output = open(finalLocation, 'wb')
                output.write(response.read())
                output.close()
                downloaded = True

            else:
                clidownload = CliDownloader()
                if clidownload.find_binary('wget'):
                    command = [clidownload.find_binary('wget'),
                                '--connect-timeout=' + str(int(self.timeout)),
                                '-O', finalLocation, self.url]
                    clidownload.execute(command)
                    downloaded = True
                elif clidownload.find_binary('curl'):
                    command = [clidownload.find_binary('curl'),
                                '--connect-timeout', str(int(self.timeout)),
                                '-L', self.url, '-o', finalLocation]
                    clidownload.execute(command)
                    downloaded = True

            if not downloaded:
                sublime.error_message('Unable to download ' + self.url +
                            ' due to no ssl module available and no capable' +
                            ' program found. Please install curl or wget.')
                return False

            else:
                pkg = zipfile.ZipFile(finalLocation, 'r')

                root_level_paths = []
                last_path = None
                for path in pkg.namelist():
                    last_path = path
                    if path.find('/') in [len(path) - 1, -1]:
                        root_level_paths.append(path)
                    if path[0] == '/' or path.find('..') != -1:
                        sublime.error_message(__name__ +
                            ': Unable to extract package due to unsafe' +
                            ' filename on one or more files.')
                        return False

                if last_path and len(root_level_paths) == 0:
                    root_level_paths.append(
                        last_path[0:last_path.find('/') + 1])

                os.chdir(self.location)

                skip_root_dir = len(root_level_paths) == 1 and \
                    root_level_paths[0].endswith('/')
                for path in pkg.namelist():
                    dest = path
                    if os.name == 'nt':
                        regex = ':|\*|\?|"|<|>|\|'
                        if re.search(regex, dest) != None:
                            print ('%s: Skipping file from package named %s' +
                                ' due to an invalid filename') % (__name__,
                                                                  path)
                            continue
                    regex = '[\x00-\x1F\x7F-\xFF]'
                    if re.search(regex, dest) != None:
                        dest = dest.decode('utf-8')

                    if skip_root_dir:
                        dest = dest[len(root_level_paths[0]):]
                    dest = os.path.join(self.location, dest)
                    if path.endswith('/'):
                        if not os.path.exists(dest):
                            os.makedirs(dest)
                    else:
                        dest_dir = os.path.dirname(dest)
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                        try:
                            open(dest, 'wb').write(pkg.read(path))
                        except (IOError, UnicodeDecodeError):
                            print ('%s: Skipping file from package named %s' +
                                ' due to an invalid filename') % (__name__,
                                                                  path)

                pkg.close()
                os.remove(finalLocation)
                self.result = True

            return

        except (urllib2.HTTPError) as (e):
            err = '%s: HTTP error %s contacting server' % (__name__,
                                                           str(e.code))
        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting server' % (__name__,
                                                          str(e.reason))

        sublime.error_message(err)
        self.result = False


class BinaryNotFoundError(Exception):
    pass


class NonCleanExitError(Exception):
    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)


class CliDownloader():
    def find_binary(self, name):
        for dir in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir, name)
            if os.path.exists(path):
                return path

        raise BinaryNotFoundError('The binary ' + name + ' could not be ' +
            'located')

    def execute(self, args):
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        output = proc.stdout.read()
        returncode = proc.wait()
        if returncode != 0:
            error = NonCleanExitError(returncode)
            error.output = output
            raise error
        return output
