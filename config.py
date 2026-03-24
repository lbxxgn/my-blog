"""
Compatibility config module.

Always reload and re-export `backend.config` so test fixtures that mutate
environment variables and then `reload(config)` pick up the new values.
"""

from importlib import import_module, reload

_backend_config = import_module('backend.config')
_backend_config = reload(_backend_config)

for _name in dir(_backend_config):
    if _name.startswith('_'):
        continue
    globals()[_name] = getattr(_backend_config, _name)

__all__ = [name for name in globals() if not name.startswith('_')]
