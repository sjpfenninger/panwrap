# panpy -- pandoc wrapper and template engine #

## Installation ##

Copy all files into `~/.panpy` and either add that folder to your `$PATH` or symlink `panpy.py` into your `$PATH`, e.g. into `/usr/local/bin`.

## Use ##

Simply call panpy on your markdown file to produce a PDF file:
    
    $ panpy.py your_file.md

This will produce a PDF file, `your_file.pdf`, in the same directory as `your_file.md`.

Call panpy with `-h` to get help:

    $ panpy.py -h

### Defining variables inside a markdown file ###

To set variables such as fontsize or margins in a markdown file, add a HTML comment block at the top of the file (the first HTML comment block in the file is parsed as settings):

    <!--
    fontsize:11pt
    -->

Check `defaults.conf` for often-used variables. Custom templates may define any amount of variables that can be used either by setting them in the comment block inside the markdown file, or by setting defaults in the template's configuration file.

Parsing is not robust at all: the begin and end comment tags must be on a line on their own. Variable definitions must be on individual lines between the begin/end comment tags.

### Using custom templates ###

See `default-enhanced.tex` for an example of a custom template. Use it by calling panpy with `--template=~\.panpy\default-enhanced.tex`. Default settings for variables are automatically read from a `.conf` file in the same location as the template file itself.

## Configuration ##

### `global.conf` ###

* `pandoc`: Path to pandoc binary
* `template:` Path to default template
* `bibliography:` Path to default BibTex file
* `csl:` Path to default citation style file

### `defaults.conf` ###

Defines default settings to use if no `template` is set in `global.conf`. These default settings will be passed to Pandoc's default template, so refer to the Pandoc source to see what variables can be set by the user.

### `replacements.conf` ###

Allows to give a list of replacements, one per line, in the format `string:replacement_string`, e.g. `--->:$\rightarrow$` Replacements are applied to the source file before processing it with Pandoc.

## License ##

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <[http://www.gnu.org/licenses/](http://www.gnu.org/licenses/)>.

## Credits ##

Author: [Stefan Pfenninger](http://pfenninger.org/)

Source code available from [https://github.com/sjpfenninger/panpy](https://github.com/sjpfenninger/panpy)
