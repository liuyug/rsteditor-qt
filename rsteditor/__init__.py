import sys
import os.path

__app_name__ = 'RSTEditor'
__app_version__ = '0.1.6.3'
__default_filename__ = 'unknown.rst'


__data_path__ = os.path.join(sys.prefix, 'share', __app_name__.lower())
if not os.path.exists(__data_path__):
    __data_path__ = os.path.join(os.path.expanduser('~'), '.local', 'share', __app_name__.lower())
__home_data_path__ = os.path.join(os.path.expanduser('~'), '.config', __app_name__.lower())
