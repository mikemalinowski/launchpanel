"""

# Overview


LaunchPanel is a simple interface designed to expose LaunchPad Actions
to the user in an intuitive way.

LaunchActions are displayed in icon-centric list widgets, and they are
organised into tabs based on their groups. The user has the ability to
define tab orientation, icon size and plugin locations.

You can run launchpanel by calling:

```python
import launchpanel
launchpanel.launch()
```

This code will work in both standalone python as well as supported applications
such as Max, Maya and Motion Builder (see details of qtility for full list of
application support https://github.com/mikemalinowski/qtility)


# Environments

If you're using launchpanel in multiple contexts it can be useful to
differentiate one from the other. This can be done by setting the
environment_id.

This is simply a string identifier which defines where it will store its
settings/preferences.

```python
import launchpanel
launchpanel.launch(environment_id='foo')
```

The above instance will not cross over with the instance created below, meaning
each can have their own paths to look for actions.

```python
import launchpanel
launchpanel.launch(environment_id='bar')
```

This is particulary useful if you are running multiple projects and want a
bespoke set of plugins displayed for each one.


## Dependencies


This module has the following dependencies:

    * launchpad
    * qtility
    * scribble (pip install scribble)


# Compatibility

Launchpad has been tested under Python 2.7 and Python 3.7 on Windows and Ubuntu.
"""
__version__ = "3.0.1"

from .core import launch
from . import utils
