import os
import shutil
import subprocess
import tempfile

from .lib import md2bib
from .lib import yaml

import sublime
import sublime_plugin


def _get_file_name():
    return(sublime.active_window().active_view().file_name())


def _parse_yaml(src, src_is_file=True):
    """src is treated as path to a file, except if src_is_file=False"""
    if src_is_file:
        with open(src, 'r', encoding='utf-8') as f:
            y = yaml.safe_load(f)
    else:
        y = yaml.safe_load(src)
    path_entries = ['csl', 'bibliography', 'template']
    for e in path_entries:
        if (e in y) and (y[e] is not None):
            y[e] = os.path.expanduser(y[e])
    return y


def _find_blocks(source, start_markers=['---'], end_markers=['---', '...']):
    start_markers = tuple(start_markers)
    end_markers = tuple(end_markers)
    with open(source, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    block_id = 0
    blocks = {}
    parsing = False
    for line in lines:
        if not parsing and line.startswith(start_markers):
            parsing = True
            blocks[block_id] = []
            continue
        elif line.startswith(end_markers):
            parsing = False
            block_id += 1
        if parsing:
            blocks[block_id].append(line)
    return blocks


def _display_status(message, msg_type='notification', title='Panwrap:'):
    """type can be 'notification', 'success' or 'error'"""
    if sublime.platform() == 'osx':
        icons = {'notification': '[❕]', 'error': '[❌]', 'success': '[✅]'}
    else:
        icons = {'notification': '[i]', 'error': '[err]', 'success': '[ok]'}
    sublime.status_message(icons[msg_type] + ' ' + title + ' ' + message)


class ProcessPandocCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        f = _get_file_name()
        if not PROCESSOR.running:
            PROCESSOR.process_input(f)
        else:
            msg = 'Already running! Wait for it to finish.'
            _display_status(msg)


class OpenPdfCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        pdf_name = '.'.join(_get_file_name().split('.')[0:-1]) + '.pdf'
        cmd = PROCESSOR.plugin_settings.get('pdf_viewer')
        subprocess.call(cmd.split() + [pdf_name])


class PreviewCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        cmd = PROCESSOR.plugin_settings.get('preview')
        subprocess.call(cmd.split() + [_get_file_name()])


class PandocProcessor(object):
    def plugin_loaded_setup(self):
        self.plugin_settings_file = 'panwrap.sublime-settings'
        self.plugin_settings = sublime.load_settings(self.plugin_settings_file)
        self.running = False

    def process_input(self, source):
        """Process `inputfile` with pandoc.

        Returns:
            p : status code returned by pandoc

        """
        self.running = True
        tempdir = tempfile.mkdtemp()
        tempfiles = {}  # Keeps track of temporary files
        source = os.path.expanduser(source)
        basefile, extension = os.path.splitext(source)  # split off extension
        basepath, basefile = os.path.split(basefile)  # and split off the path
        # Initialize pandoc_exec as a list with one item
        pandoc_exec = ['pandoc']
        panwrap = _parse_yaml(sublime.packages_path()
                              + '/panwrap/default_panwrap.yaml')
        variables = _parse_yaml(sublime.packages_path()
                                + '/panwrap/default_variables.yaml')

        #
        # Find and load panwrap settings
        #
        panwrap_entry = 'panwrap_'
        blocks = _find_blocks(source)
        for _, block in blocks.items():
            # Try to parse the block as YAML
            y = _parse_yaml('\n'.join(block), src_is_file=False)
            # Try to access the panwrap_entry
            try:
                panwrap_loaded = y[panwrap_entry]
                break  # As soon as first panwrap_entry found, abort
            except KeyError:
                continue
        else:
            panwrap_loaded = {}

        #
        # Combine loaded panwrap settings with defaults_panwrap
        #
        p = panwrap
        for k, v in panwrap_loaded.items():
            p[k] = v
        if 'pandoc-options' in panwrap_loaded.keys():
            p['pandoc-options'] = p['pandoc-options-default'] + panwrap_loaded['pandoc-options']
        if 'in-header-lines' in panwrap_loaded.keys():
            p['in-header-lines'] = p['in-header-lines-default'] + panwrap_loaded['in-header-lines']
        if 'before-body-lines' in panwrap_loaded.keys():
            p['before-body-lines'] = p['before-body-lines-default'] + panwrap_loaded['before-body-lines']

        #
        # Process panwrap settings
        #
        for key, val in panwrap.items():
            # Skip values that are 'none'
            if val is None:
                pass
            # 1. output
            elif key == 'output':
                if isinstance(val, list):
                    outputs = val
                else:
                    outputs = [val]
            # 2. header-lines/body-lines
            elif (key == 'in-header-lines') or (key == 'before-body-lines'):
                # Special case for header and body
                tempfiles[key] = os.path.join(tempdir,
                                              '{}-{}{}'.format(basefile,
                                                               key, extension))
                with open(tempfiles[key], 'w', encoding='utf-8') as f:
                    [f.write(v + '\n') for v in val]
                pandoc_exec.append('--include-{}={}'.format(
                                   key.replace('-lines', ''), tempfiles[key]))
            # 3. pandoc-options
            elif key == 'pandoc-options':
                for item in val:
                    # Make sure that all spaces are removed
                    pandoc_exec.extend(item.split())
            # 4. template settings/variables default override
            elif key == 'template':
                pth = os.path.splitext(val)[0] + '.yaml'
                # Expand panwrap plugin path if '{PANWRAP}'' is in pth
                panwrap_path = os.path.dirname(os.path.abspath(__file__))
                pth = pth.format(PANWRAP=panwrap_path)
                # If pth is still relative, we make it absolute with the
                # source file directory as base directory
                if not os.path.isabs(pth):
                    pth = os.path.join(basepath, pth)
                variables_loaded = _parse_yaml(pth)
                for k, v in variables_loaded.items():
                    variables[k] = v
            # 5. bibliography extraction
            elif key == 'extract_bibliography':
                if val['extract']:
                    # Extract citation keys from source file
                    keys = md2bib.getKeysFromMD(source)
                    # Read source bibliography and generate subset
                    with open(variables['bibliography'], 'r',
                              encoding='utf-8') as f:
                        entries = md2bib.parseBibTex(f.readlines())
                    subset = md2bib.subsetBibliography(entries, keys)
                    # Write extracted subset to new bibliography file
                    bibsubset_file = os.path.join(tempdir, basefile + '.bib')
                    with open(bibsubset_file, 'w', encoding='utf-8') as f:
                        md2bib.emitBibliography(subset, f)
                    # If set to keep, we copy the bib file into basepath
                    if val['keep']:
                        shutil.copy(bibsubset_file, basepath)
                    variables['bibliography'] = bibsubset_file

        #
        # Write variables YAML block at end of temporary document
        #
        source_temp = os.path.join(tempdir, basefile + '-temp' + extension)
        shutil.copyfile(source, source_temp)
        with open(source_temp, 'a', encoding='utf-8') as f:
            f.write('\n---\n')
            yaml.dump(variables, f)
            f.write('---\n')

        #
        # Read debug settings
        #
        if (('debug' in panwrap and 'keep_tempfiles' in panwrap['debug']
             and panwrap['debug']['keep_tempfiles'] is True)):
            keep_tempfiles = True
        else:
            keep_tempfiles = False

        #
        # Do the rest in a separate thread so that Sublime Text doesn't hang
        #
        sublime.set_timeout_async(lambda: self.async_run(tempdir, outputs,
                                  basefile, basepath, source_temp, pandoc_exec,
                                  keep_tempfiles), 0)

    def async_run(self, tempdir, outputs, basefile, basepath, source_temp,
                  pandoc_exec, keep_tempfiles=False):
        # Add a working marker to status bar
        view = sublime.active_window().active_view()
        view.set_status('panwrap_working', '[Panwrap is working...]')

        #
        # Set output filenames and call pandoc
        #
        errors = []
        files = []
        for output in outputs:
            f = '{}.{}'.format(basefile, output)
            files.append(f)
            o = '--output=' + os.path.join(basepath, f)
            execute = pandoc_exec + [o] + [source_temp]
            print('>>> Executing: ' + ' '.join(execute))
            pandoc_path = self.plugin_settings.get('pandoc_path')
            tex_path = self.plugin_settings.get('tex_path')
            env = {'PATH': tex_path + ':' + pandoc_path + ':' + os.environ['PATH'],
                   'HOME': os.environ['HOME'],
                   'LANG': 'en_US.UTF-8'}  # Force UTF-8
            try:
                subprocess.check_output(execute, stderr=subprocess.STDOUT,
                                        env=env, cwd=basepath)
            except subprocess.CalledProcessError as err:
                print('Pandoc error.')
                errors.append(err.returncode)
                print('Output: {}'.format(err.output))

        #
        # Clean up temporary files
        #
        if keep_tempfiles:
            print('Temporary folder not deleted: {}'.format(tempdir))
        else:
            shutil.rmtree(tempdir)

        # Remove the working marker from status bar
        view.erase_status('panwrap_working')

        #
        # Display outcome
        #
        if len(errors) > 0:
            _display_status('{e} error(s)'.format(e=len(errors)),
                            msg_type='error')
        else:
            if len(outputs) > 1:
                multi = 's'
            else:
                multi = ''
            _display_status('wrote file{m}: {f}'.format(m=multi, f=files),
                            msg_type='success')
        self.running = False


PROCESSOR = PandocProcessor()


def plugin_loaded():
    PROCESSOR.plugin_loaded_setup()
