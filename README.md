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

To set variables such as fontsize or margins in a markdown file, add a HTML comment block at the top of the file:

    <!--
    fontsize:11pt
    -->

Check `defaults.conf` for often-used variables. Custom templates may define any amount of variables that can be used either by setting them in the comment block inside the markdown file, or by setting defaults in the template's configuration file.

Parsing is not robust at all: the begin and end comment tags must be on a line on their own. Variable definitions must be on individual lines between the begin/end comment tags.

### Using custom templates ###

See `xetex-custom.tex` for an example of a custom template. Use it by calling panpy with `--template=~\.panpy\xetex-custom.tex`. Default settings for variables are automatically read from a `.conf` file in the same location as the template file itself.

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

## Credits ##

xetex-custom template is based on:

[https://github.com/claes/pandoc-templates](https://github.com/claes/pandoc-templates)