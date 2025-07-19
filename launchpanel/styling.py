import re
import os
from . import resources

# -- This is a set of default variables used when
# -- applying style sheets
STYLE_DEFAULTS = {
    '_BACKGROUND_': '40, 40, 40',
    '_ALTBACKGROUND_': '70, 70, 70',
    '_FOREGROUND_': '66, 194, 244',
    '_HIGHLIGHT_': '109, 214, 255',
    '_TEXT_': '255, 255, 255',
}

# -- We expose all of our resources as special variables
for resource in resources.all():
    key = '_%s_' % os.path.basename(resource).replace('.', '_').upper()
    STYLE_DEFAULTS[key] = resource


def get_style():

    with open(resources.get("space.qss"), 'r') as f:
        stylesheet = f.read()

    # -- We need to combine the kwargs with the defaults
    styling_parameters = STYLE_DEFAULTS.copy()

    # -- Now that we have compounded all our style information we can cycle
    # -- over it and carry out any replacements
    for regex, replacement in styling_parameters.items():
        regex = re.compile(regex)
        stylesheet = regex.sub(replacement, stylesheet)

    return stylesheet
