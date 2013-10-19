import os
import shutil
import subprocess
from .lib import yaml

import sublime
import sublime_plugin


def _get_file_name():
    return(sublime.active_window().active_view().file_name())


def _parse_yaml(f):
    y = yaml.load(open(f, 'r'))
    path_entries = ['csl', 'bibliography', 'template']
    for e in path_entries:
        if (e in y) and (y[e] is not None):
            y[e] = os.path.expanduser(y[e])
    return y


def _find_blocks(source, start_markers=['---'], end_markers=['---', '...']):
    start_markers = tuple(start_markers)
    end_markers = tuple(end_markers)
    lines = open(source).readlines()
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


class ProcessPandocCommand(sublime_plugin.ApplicationCommand):
    def run(self, **args):
        f = _get_file_name()
        PROCESSOR.process_input(f)


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

    def process_input(self, source):
        """Process `inputfile` with pandoc.

        Returns:
            p : status code returned by pandoc

        """
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
            # Try to pass the block as YAML
            try:
                y = yaml.load('\n'.join(block))
            except:  # TODO WHICHERROR
                continue
            # Try to access the panwrap_entry
            try:
                panwrap_loaded = y[panwrap_entry]
                break
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
                tempfiles[key] = os.path.join(basepath,
                                              '{}-{}{}'.format(basefile,
                                                               key, extension))
                with open(tempfiles[key], 'w') as f:
                    [f.write(v + '\n') for v in val]
                pandoc_exec.append('--include-{}={}'.format(
                                   key.replace('-lines', ''), tempfiles[key]))
            # 3. pandoc-options
            elif key == 'pandoc-options':
                for item in val:
                    # Make sure that all spaces are removed
                    pandoc_exec.extend(item.split())
            # 4. template variables
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

        #
        # Write variables YAML block at end of temporary document
        #
        source_temp = os.path.join(basepath, basefile + '-temp' + extension)
        shutil.copyfile(source, source_temp)
        tempfiles['source_temp'] = source_temp
        with open(source_temp, 'a') as f:
            f.write('\n---\n')
            yaml.dump(variables, f)
            f.write('---\n')

        #
        # Do the rest in a separate thread so that Sublime Text doesn't hang
        #
        sublime.set_timeout_async(lambda: self.async_run(tempfiles, outputs,
                                  basefile, basepath, source_temp, pandoc_exec),
                                  0)

    def async_run(self, tempfiles, outputs, basefile, basepath, source_temp,
                  pandoc_exec):
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
                   'HOME': os.environ['HOME']}
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
        keep_tempfiles = False
        if tempfiles and not keep_tempfiles:
            for k in tempfiles:
                os.remove(tempfiles[k])

        # Remove the working marker from status bar
        view.erase_status('panwrap_working')

        #
        # Display outcome
        #
        if sublime.platform() == 'osx':
            icons = {'error': '❌', 'success': '✅'}
        else:
            icons = {'error': '[ERROR]', 'success': '[SUCCESS]'}
        if len(errors) > 0:
            error = '{i} Panwrap: {e} error(s)'.format(i=icons['error'],
                                                       e=len(errors))
            sublime.status_message(error)
        else:
            if len(outputs) > 1:
                multi = 's'
            else:
                multi = ''
            success = ('{i} Panwrap: wrote '
                       'file{m}: {f}'.format(i=icons['success'], m=multi,
                                             f=files))
            sublime.status_message(success)


PROCESSOR = PandocProcessor()


def plugin_loaded():
    PROCESSOR.plugin_loaded_setup()
