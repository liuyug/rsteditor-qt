import os.path
import logging
import json
from collections import OrderedDict

try:
    from docutils.core import publish_string
    from docutils.core import publish_cmdline
    from docutils.core import publish_cmdline_to_binary
    from docutils.writers.odf_odt import Writer, Reader
    from docutils.writers import html5_polyglot
except:
    raise Exception('Please install docutils firstly')

from rsteditor import __data_path__, __home_data_path__

logger = logging.getLogger(__name__)

default_overrides = {
    'input_encoding': 'utf-8',
    'output_encoding': 'utf-8',
}


def get_themes():
    """
    result: { 'theme': theme_dict, ... }
    """
    themes_dirs = [
        os.path.join(__home_data_path__, 'themes'),
        os.path.join(__data_path__, 'themes'),
    ]
    themes = OrderedDict()
    for themes_dir in themes_dirs:
        if os.path.exists(themes_dir):
            for theme in os.listdir(themes_dir):
                theme_json = os.path.join(themes_dir, theme, 'theme.json')
                if os.path.exists(theme_json):
                    try:
                        styles = json.load(open(theme_json))
                        for name, style in styles.items():
                            style['stylesheet_dirs'] = [os.path.dirname(theme_json)]
                            themes[name] = style
                    except Exception as err:
                        logger.error(err)
                        continue
    return themes


def get_theme_settings(theme, pygments):
    """
    1. pygments.css has been created in app.py so parameter pygments is unused.
    2. docutils writer will load css file.
    """
    stylesheet = {}
    search_paths = [
        '/usr/share/docutils/writers',
        os.path.abspath(os.path.dirname(os.path.dirname(html5_polyglot.__file__))),
        os.path.abspath(os.path.join(__data_path__, 'docutils', 'writers')),
    ]
    docutils_theme_path = ''
    for path in search_paths:
        if os.path.exists(os.path.join(path, 'html5_polyglot', 'template.txt')):
            docutils_theme_path = path
            break
    stylesheet['stylesheet_dirs'] = [
        os.path.join(docutils_theme_path, 'html4css1'),
        os.path.join(docutils_theme_path, 'html5_polyglot'),
    ]

    pygments_path = os.path.join(__home_data_path__, 'themes', 'pygments.css')
    if os.path.exists(pygments_path):
        stylesheet['stylesheet_path'] = pygments_path
        stylesheet['syntax_highlight'] = 'short'

    # docutils default theme
    if theme == 'docutils':
        return stylesheet

    # third part theme
    themes = get_themes()
    styles = themes.get(theme)

    # stylesheet_path : css file path
    # syntax_highlight: short
    # template: template file path
    stylesheet['stylesheet_dirs'].extend(styles['stylesheet_dirs'])
    if 'syntax_highlight' in styles:
        stylesheet['syntax_highlight'] = styles['syntax_highlight']
    if 'stylesheet_path' in styles:
        css_paths = styles['stylesheet_path'].split(',')
        if 'stylesheet_path' in stylesheet:
            css_paths += stylesheet['stylesheet_path'].split(',')
        stylesheet['stylesheet_path'] = ','.join(css_paths)
    if 'template' in styles:
        old_path = styles['template']
        new_path = os.path.abspath(
            os.path.join(__home_data_path__,
                         'themes',
                         theme,
                         old_path))
        stylesheet['template'] = new_path
    return stylesheet


def rst2htmlcode(rst_text, theme='docutils', pygments='docutils', settings={}):
    output = None
    try:
        overrides = {}
        overrides.update(default_overrides)
        overrides.update(settings)
        overrides.update(get_theme_settings(theme, pygments))
        logger.debug(overrides)
        output = publish_string(
            rst_text,
            writer_name='html5',
            settings_overrides=overrides,
        )
    except Exception as err:
        logger.error(err)
        output = str(err)
    return output


def rst2html(rst_file, filename, theme='docutils', pygments='docutils', settings={}):
    output = None
    try:
        overrides = {}
        overrides.update(default_overrides)
        overrides.update(settings)
        overrides.update(get_theme_settings(theme, pygments))
        logger.debug(overrides)
        output = publish_cmdline(
            writer_name='html5',
            settings_overrides=overrides,
            argv=[
                rst_file,
                filename,
            ]
        )
    except Exception as err:
        logger.error(err)
        output = err
    return output


def rst2odt(rst_file, filename, theme='docutils', pygments='docutils', settings={}):
    output = None
    try:
        overrides = {}
        overrides.update(default_overrides)
        overrides.update(settings)
        overrides.update(get_theme_settings(theme, pygments))
        logger.debug(overrides)
        writer = Writer()
        reader = Reader()
        output = publish_cmdline_to_binary(
            reader=reader,
            writer=writer,
            settings_overrides=overrides,
            argv=[
                rst_file,
                filename,
            ]
        )
    except Exception as err:
        logger.error(err)
        output = err
    return output
