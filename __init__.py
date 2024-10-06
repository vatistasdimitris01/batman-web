# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring, cyclic-import

import sys
import os
from os.path import dirname, abspath
import logging

import searx.unixthreadname
import searx.settings_loader
from searx.settings_defaults import settings_set_defaults


# Debug
LOG_FORMAT_DEBUG = '%(levelname)-7s %(name)-30.30s: %(message)s'

# Production
LOG_FORMAT_PROD = '%(asctime)-15s %(levelname)s:%(name)s: %(message)s'
LOG_LEVEL_PROD = logging.WARNING

# Initialize paths
searx_dir = abspath(dirname(__file__))
searx_parent_dir = abspath(dirname(dirname(__file__)))

# Load settings
settings, settings_load_message = searx.settings_loader.load_settings()

# Ensure settings are set to defaults if loaded
if settings is not None:
    settings = settings_set_defaults(settings)

_unset = object()

def get_setting(name, default=_unset):
    """Returns the value to which ``name`` points. If there is no such name in the
    settings and the ``default`` is unset, a :py:obj:`KeyError` is raised.
    """
    value = settings
    for a in name.split('.'):
        if isinstance(value, dict):
            value = value.get(a, _unset)
        else:
            value = _unset

        if value is _unset:
            if default is _unset:
                raise KeyError(name)
            value = default
            break

    return value

def is_color_terminal():
    return os.getenv('TERM') not in ('dumb', 'unknown') and sys.stdout.isatty()

def logging_config_debug():
    try:
        import coloredlogs  # pylint: disable=import-outside-toplevel
    except ImportError:
        logging.warning("coloredlogs module not found. Using basic logging.")
        coloredlogs = None

    log_level = os.environ.get('SEARXNG_DEBUG_LOG_LEVEL', 'DEBUG')
    if coloredlogs and is_color_terminal():
        level_styles = {
            'spam': {'color': 'green', 'faint': True},
            'debug': {},
            'notice': {'color': 'magenta'},
            'success': {'bold': True, 'color': 'green'},
            'info': {'bold': True, 'color': 'cyan'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'},
            'critical': {'bold': True, 'color': 'red'},
        }
        field_styles = {
            'asctime': {'color': 'green'},
            'hostname': {'color': 'magenta'},
            'levelname': {'color': 8},
            'name': {'color': 8},
            'programname': {'color': 'cyan'},
            'username': {'color': 'yellow'},
        }
        coloredlogs.install(level=log_level, level_styles=level_styles, field_styles=field_styles, fmt=LOG_FORMAT_DEBUG)
    else:
        logging.basicConfig(level=logging.getLevelName(log_level), format=LOG_FORMAT_DEBUG)

# Configure logging based on settings
try:
    searx_debug = settings['general']['debug']
    if searx_debug:
        logging_config_debug()
    else:
        logging.basicConfig(level=LOG_LEVEL_PROD, format=LOG_FORMAT_PROD)
        logging.root.setLevel(level=LOG_LEVEL_PROD)
        logging.getLogger('werkzeug').setLevel(level=LOG_LEVEL_PROD)
except KeyError as e:
    logging.error("Missing setting in configuration: %s", e)
    sys.exit(1)  # Exit if essential settings are missing

logger = logging.getLogger('searx')
logger.info(settings_load_message)

# Log max_request_timeout
try:
    max_request_timeout = settings['outgoing']['max_request_timeout']
    logger.info('max_request_timeout=%s', repr(max_request_timeout))
except KeyError:
    logger.warning('max_request_timeout setting is missing.')

# Check for public instance feature
try:
    if settings['server']['public_instance']:
        logger.warning(
            "Be aware you have activated features intended only for public instances. "
            "This forces the usage of the limiter and link_token / "
            "see https://docs.searxng.org/admin/searx.limiter.html"
        )
except KeyError:
    logger.warning('public_instance setting is missing.')
