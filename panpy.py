#!/usr/bin/env python

# * * *
# panpy -- pandoc wrapper and template engine
# Author: Stefan Pfenninger <http://pfenninger.org/>
# * * *

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import subprocess
import argparse


def parse_settings(source_file, force_parsing=False):
    """Barebones parser for lists of "key:val\n" type settings.

    Returns:
        settings : a dict with the parsed settings

    Args:
        source_file : path to a file
        force_parsing : if False (default), will search for
            '<!--' before begining to parse, and stop at '-->'

    """
    pathsettings = ('pandoc', 'template', 'bibliography', 'csl')
    dictsettings = ('geometry')
    listsettings = ('header', 'footer')
    lines = open(source_file).readlines()
    parsing = False
    settings = {}
    for line in lines:
        if force_parsing:
            parsing = True
        else:
            if line.startswith("<!--"):
                parsing = True
                continue
            elif line.startswith("-->"):
                parsing = False
                # End the loop here, i.e. we won't even look at
                # possible html comments further down in the file
                break
        if parsing:
            if not line.strip() or line.startswith('#'):
                continue
            key, val = line.strip().split(':')
            if key in pathsettings:
                settings[key] = os.path.expanduser(val)
            elif key in dictsettings:
                    k, v = val.split('=')
                    if key in settings:
                        settings[key][k] = v
                    else:
                        settings[key] = {k: v}
            elif key in listsettings:
                    if key in settings:
                        settings[key].append(val)
                    else:
                        settings[key] = [val]
            else:
                settings[key] = val
    return settings


def process_input(inputfile, output_format, template=None, csl=None,
                  pandoc_options=None, bib=True, verbose=False,
                  globalsettings=None, panpy_dir='.'):
    """Process `inputfile` with pandoc, using the given template and
    CSL file, producing a PDF file with the same name.

    Returns:
        p : status code returned by pandoc

    Args:
        inputfile : Path to input file.
        output_format : Pandoc-compatible output format, e.g. 'pdf',
                        will be used as file suffix.
        template : Path to template (if None, uses default read from
                   globalsettings, and if none given there, uses
                   pandoc default).
        csl : Path to CSL file (if None, uses default read from
              globalsettings).
        pandoc_options : Additional options to pass to pandoc (must give
                         as ++foo=bar or +f=bar), + will be replaced with -.
        bib : Whether to process the bibliography (default: True).
        verbose : Show more details (default: False).
        globalsettings : Path to global settings file.
        panpy_dir: Path to panpy directory.

    """
    if not globalsettings:
        globalsettings = '{}/global.conf'.format(panpy_dir)
    tempfile = {}  # Dict to hold paths to temporary files
    settings_global = parse_settings(os.path.expanduser(globalsettings),
                                     force_parsing=True)
    pandoc = settings_global['pandoc']
    if template:
        settings_global['template'] = '{}/{}'.format(panpy_dir, template)
    if csl:
        settings_global['csl'] = csl
    if 'template' in settings_global:
        settings_global['template'] = '{}/{}'.format(panpy_dir,
                                                     settings_global['template'])
        templatesettings = settings_global['template'].replace('.tex', '.conf')
    else:
        templatesettings = '{}/defaults.conf'.format(panpy_dir)
    settings_template = parse_settings(os.path.expanduser(templatesettings),
                                       force_parsing=True)
    sourcefile_path = os.path.expanduser(inputfile)
    # Get the filename without the extension
    basefile = '.'.join(sourcefile_path.split('.')[0:-1])
    extension = inputfile.split('.')[-1]
    # Override template defaults with settings given in the source file
    settings_template_source = parse_settings(sourcefile_path)
    for key, val in settings_template_source.iteritems():
        if isinstance(val, dict):
            for k, v in val.iteritems():
                    settings_template[key][k] = v
        else:
            if key in settings_template:
                settings_template[key] = val
            else:
                raise ValueError('Unknown key: {}'.format(key))
    pandoc_exec = [pandoc]
    pandoc_exec.append('--latex-engine=xelatex')
    pandoc_exec.append('--smart')  # Produce typographically correct output
    pandoc_exec.append('--columns=98')  # Correct table width for editor colwidth
    # Global settings
    for key, val in settings_global.iteritems():
        # 'pandoc' is the only option we don't actually pass on,
        # as it's simply the pandoc binary's path!
        if key != 'pandoc':
            if (not bib) and (key == 'bibliography'):
                continue
            pandoc_exec.append('--{0}={1}'.format(key, val))
    # Template settings
    for key, val in settings_template.iteritems():
        if val == '':
            # If an option has no value it is skipped
            continue
        elif isinstance(val, dict):
            for k, v in val.iteritems():
                pandoc_exec.append('--variable={0}:{1}={2}'.format(key, k, v))
        elif isinstance(val, list):
            # Special case for header and body
            assert key == 'header' or key == 'body'
            tempfile[key] = '{}.{}.{}'.format(basefile, key, extension)
            with open(tempfile[key], 'w') as f:
                [f.write(v + '\n') for v in val]
            onames = {'body': 'before-body', 'header': 'in-header'}
            pandoc_exec.append('--include-{}={}'.format(
                               onames[key], tempfile[key]))
        elif key == 'header':
            pandoc_exec.append('--include-in-header={}'.format(
                               os.path.expanduser(val)))
        elif key == 'body':
            pandoc_exec.append('--include-before-body={}'.format(
                               os.path.expanduser(val)))
        elif key == 'pandoc-options':
            for o in val.split(','):
                pandoc_exec.append('--{}'.format(o))
        else:
            pandoc_exec.append('--variable={0}:{1}'.format(key, val))
    # Output filename
    pandoc_exec.append('--output={0}.{1}'.format(basefile, output_format))
    if pandoc_options:
        for option in pandoc_options.split(' '):
            pandoc_exec.append(option.replace('+', '-'))
    pandoc_exec.append(sourcefile_path)
    if verbose:
        print('>>> Executing: ' + ' '.join(pandoc_exec))
    p = subprocess.call(pandoc_exec, stderr=subprocess.STDOUT)
    # Clean up temporary files
    if tempfile:
        for v in tempfile.values():
            os.remove(v)
    return p


# If script is called directly, read command-line arguments
# and call process_input accordingly.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process `file.md` with '
                                     'pandoc, and write output to `file.pdf`.')
    parser.add_argument('file', metavar='file', type=str, help='Input file.')
    parser.add_argument('-o', '--output', metavar='..', type=str, default='pdf',
                        help='Pandoc output format (default: pdf).')
    parser.add_argument('-t', '--template', metavar='..', dest='template',
                        type=str, help='Path to custom template (default: use '
                        'setting from {panpy_dir}/global.conf '
                        'or pandoc default).')
    parser.add_argument('-c', '--csl', metavar='..', dest='csl', type=str,
                        help='Path to custom CSL file (default: use setting '
                        'from {panpy_dir}/global.conf)')
    parser.add_argument('--pandoc-options', metavar='..', dest='pandoc_options',
                        type=str, help='Additional options to pass to pandoc '
                        '(like so: --pandoc-options="++foo=bar ++option").')
    parser.add_argument('--no-bib', dest='bib', action='store_const',
                        const=False, default=True,
                        help='Do not process bibliography.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_const',
                        const=True, default=False, help='Show more details.')
    parser.add_argument('--panpy-dir', dest='panpydir', type=str,
                        help='Set panpy_dir, the directory where the script and'
                        ' configuration files reside (default: ".")')
    args = parser.parse_args()
    p = process_input(args.file, output_format=args.output,
                      template=args.template,
                      csl=args.csl, pandoc_options=args.pandoc_options,
                      bib=args.bib, verbose=args.verbose,
                      panpy_dir=args.panpydir)
