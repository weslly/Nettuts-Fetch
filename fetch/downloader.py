import sublime
import threading
import sys
import zipfile
import os
import re

try:
    from .cli_downloader import CliDownloader
    from ..Fetch import sublime_version
except (ValueError):
    from cli_downloader import CliDownloader
    from Fetch import sublime_version

try:
    # Python 3
    import urllib.request as urllib_compat
    from urllib.error import HTTPError, URLError

except (ImportError):
    # Python 2
    import urllib2 as urllib_compat
    from urllib2 import HTTPError, URLError


try:
    import ssl
except (ImportError):
    pass


class Downloader(threading.Thread):
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
                request = urllib_compat.Request(self.url)
                http_file = urllib_compat.urlopen(request, timeout=self.timeout)
                if sublime_version == 2:
                    self.txt = unicode(http_file.read(), 'utf-8')
                else:
                    self.txt = str(http_file.read(), 'utf-8')

                downloaded = True

            else:
                clidownload = CliDownloader()
                if clidownload.find_binary('wget'):
                    command = [clidownload.find_binary('wget'),
                                '--connect-timeout=' + str(int(self.timeout)),
                                self.url, '-qO-']
                    if sublime_version == 2:
                        self.txt = unicode(clidownload.execute(command), 'utf-8')
                    else:
                        self.txt = str(clidownload.execute(command), 'utf-8')

                    downloaded = True

                elif clidownload.find_binary('curl'):
                    command = [clidownload.find_binary('curl'),
                                '--connect-timeout', str(int(self.timeout)),
                                '-L', '-sS', self.url]
                    if sublime_version == 2:
                        self.txt = unicode(clidownload.execute(command), 'utf-8')
                    else:
                        self.txt = str(clidownload.execute(command), 'utf-8')

                    downloaded = True

            if not downloaded:
                sublime.error_message('Unable to download ' + self.url +
                            ' due to no ssl module available and no capable' +
                            ' program found. Please install curl or wget.')
                return False
            else:
                self.result = True

        except (URLError) as e:
            err = '%s: URL error %s contacting API' % (__name__, str(e.code))
            sublime.error_message(err)

    def download_package(self):
        downloaded = False
        try:
            finalLocation = os.path.join(self.location, '__tmp_package.zip')
            has_ssl = 'ssl' in sys.modules

            if has_ssl:
                urllib_compat.install_opener(
                    urllib_compat.build_opener(urllib_compat.ProxyHandler()))
                request = urllib_compat.Request(self.url)
                response = urllib_compat.urlopen(request, timeout=self.timeout)
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
                            try:
                                print ('%s: Skipping file from package named %s' +
                                    ' due to an invalid filename') % (__name__,
                                                                      path)
                            except(SyntaxError):
                                print(('%s: Skipping file from package named %s' +
                                    ' due to an invalid filename') % (__name__,
                                                                      path))
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
                            try:
                                print ('%s: Skipping file from package named %s' +
                                    ' due to an invalid filename') % (__name__,
                                                                      path)
                            except(SyntaxError):
                                print(('%s: Skipping file from package named %s' +
                                    ' due to an invalid filename') % (__name__,
                                                                      path))

                pkg.close()
                os.remove(finalLocation)
                self.result = True

            return

        except (HTTPError) as e:
            err = '%s: HTTP error %s contacting server' % (__name__,
                                                           str(e.code))
        except (URLError) as e:
            err = '%s: URL error %s contacting server' % (__name__,
                                                          str(e.code))

        sublime.error_message(err)
        self.result = False
