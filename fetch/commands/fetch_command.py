# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
import os


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

        for name, url in packages.items():
            try:
                # Python 2
                self.packageList.append([name.decode('utf-8'),
                                         url.decode('utf-8')])
            except AttributeError:
                # Python 3
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

        if not self.window.views():
            self.window.new_file()

        self.window.run_command("fetch_get", {"option":
                    "package", "url": self.packageUrl, "location": location})

    def list_files(self):
        files = self.s.get('files')

        if not files:
            self.s.set('files', self.filesPlaceholder)
            sublime.save_settings('Fetch.sublime-settings')
            files = self.s.get('files')

        for name, url in files.items():
            try:
                # Python 2
                self.fileList.append([name.decode('utf-8'),
                                      url.decode('utf-8')])
            except AttributeError:
                # Python 3
                self.fileList.append([name, url])

        self.window.show_quick_panel(self.fileList, self.get_file)

    def get_file(self, index):
        if (index > -1):
            if not self.window.views():
                self.window.new_file()

            url = self.fileList[index][1]
            self.window.run_command("fetch_get", {"option": "txt", "url": url})

