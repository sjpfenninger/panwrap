import subprocess

import sublime
import sublime_plugin


def get_md_name():
    return(sublime.active_window().active_view().file_name())


class OpenPdfCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        pdf_name = '.'.join(get_md_name().split('.')[0:-1]) + '.pdf'
        subprocess.call(['open', pdf_name])


class PreviewMarkedCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        subprocess.call(['open', '-a', 'Marked', get_md_name()])
