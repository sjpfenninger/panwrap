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

PANPY_DIR = '~/.panpy'

def parse_settings(source_file, force_parsing=False):
    """Barebones parser for lists of "key:val\n" type settings.

    Returns:
        settings : a dict with the parsed settings

    Args:
        source_file : path to a file
        force_parsing : if False (default), will search for '<!--' before begining to parse, and stop at '-->'

    """
    pathsettings = ('csl', 'bibliography', 'template')
    listsettings = ('geometry')
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
                break  # End the loop here, i.e. we won't even look at possible html comments further down in the file
        if parsing:
            if not line.strip() or line.startswith('#'):
                continue
            key, val = line.strip().split(':')
            if key in pathsettings:
                settings[key] = os.path.expanduser(val)
            elif key in listsettings:
                    k, v = val.split('=')
                    if key in settings:
                        settings[key][k] = v
                    else:
                        settings[key] = {k: v}
            else:
                settings[key] = val
    return settings


def process_replacements(inputfile, replacement_settings):
    """Process replacements

    Args:
        inputfile : path to the input file
        replacement_settings : a dict containing replacement mappings (key replaced with val)

    Returns:
        lines : the lines of inputfile with applied replacements

    """
    import codecs
    input_file = codecs.open(inputfile, 'r')
    lines = []
    for line in input_file.readlines():
        for key, val in replacement_settings.iteritems():
            line = line.replace(key, val)
        lines.append(line)
    return lines


def process_input(inputfile, output_format, template=None, csl=None, pandoc_options=None, replacements=True, globalsettings='{}/global.conf'.format(PANPY_DIR)):
    """Process `inputfile` with pandoc, using the given template and CSL file, producing a PDF file with the same name.

    Returns:
        p : status code returned by pandoc

    Args:
        inputfile : Path to input file.
        output_format : Pandoc-compatible output format, e.g. 'pdf', will be used as file suffix.
        template : Path to template (if None, uses default read from globalsettings, and if none given there, uses pandoc default).
        csl : Path to CSL file (if None, uses default read from globalsettings).
        pandoc_options : Additional options to pass to pandoc (must give as ++foo=bar or +f=bar), + will be replaced with -.
        replacements : Whether to apply text replacements from replacements.conf before processing with pandoc (default: True).
        globalsettings : Path to global settings file.

    """
    settings_global = parse_settings(os.path.expanduser(globalsettings), force_parsing=True)
    pandoc = settings_global['pandoc']
    if template:
        settings_global['template'] = template
    if csl:
        settings_global['csl'] = csl
    if 'template' in settings_global:
        templatesettings = settings_global['template'].replace('.template', '.conf')
    else:
        templatesettings = '{}/defaults.conf'.format(PANPY_DIR)
    settings_template = parse_settings(os.path.expanduser(templatesettings), force_parsing=True)
    sourcefile_path = os.path.expanduser(inputfile)
    basefile = ''.join(sourcefile_path.split('.')[0:-1])  # Get the filename without the extension
    extension = inputfile.split('.')[-1]
    if replacements:
        replacement_settings = parse_settings(os.path.expanduser('{}/replacements.conf'.format(PANPY_DIR)), force_parsing=True)
        lines = process_replacements(sourcefile_path, replacement_settings)
        newfile_path = '{0}.replaced.{1}'.format(basefile, extension)
        with open(newfile_path, 'w') as f:
            f.writelines(lines)
        sourcefile_path = newfile_path
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
    # Global settings
    for key, val in settings_global.iteritems():
        if key != 'pandoc':  # 'pandoc' is the only option we don't actually pass on, as it's simply the pandoc binary's path!
            pandoc_exec.append('--{0}={1}'.format(key, val))
    # Template settings
    for key, val in settings_template.iteritems():
        if isinstance(val, dict):
            for k, v in val.iteritems():
                pandoc_exec.append('--variable={0}:{1}={2}'.format(key, k, v))
        else:
            pandoc_exec.append('--variable={0}:{1}'.format(key, val))
    # Output filename
    pandoc_exec.append('--output={0}.{1}'.format(basefile, output_format))
    if pandoc_options:
        for option in pandoc_options.split(' '):
            pandoc_exec.append(option.replace('+', '-'))
    pandoc_exec.append(sourcefile_path)
    print '>>> Executing: ' + ' '.join(pandoc_exec)
    p = subprocess.call(pandoc_exec)
    if replacements:
        os.remove(sourcefile_path)
    return p


# If script is called directly, read command-line arguments and call process_input accordingly.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process `file.md` with pandoc, and write output to `file.pdf`.')
    parser.add_argument('file', metavar='file', type=str, help='Input file.')
    parser.add_argument('-o', '--output', metavar='..', type=str, default='pdf', help='Pandoc output format (default: pdf).')
    parser.add_argument('-t', '--template', metavar='..', dest='template', type=str, help='Path to custom template (default: use setting from {}/global.conf or pandoc default).'.format(PANPY_DIR))
    parser.add_argument('-c', '--csl', metavar='..', dest='csl', type=str, help='Path to custom CSL file (default: use setting from {}/global.conf)'.format(PANPY_DIR))
    parser.add_argument('--pandoc-options', metavar='..', dest='pandoc_options', type=str, help='Additional options to pass to pandoc (like so: ++foo=bar or +f=bar.)')
    parser.add_argument('--no-replacements', dest='replacements', action='store_const', const=False, default=True, help='Do not apply replacements from replacements.conf.')
    args = parser.parse_args()
    process_input(args.file, output_format=args.output, template=args.template, csl=args.csl, pandoc_options=args.pandoc_options, replacements=args.replacements)
