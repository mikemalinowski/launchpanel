import sys


def format_sys_argv():
    """
    From the system arguments, get the specific positional and keyword arguments supported for launchpanel.

    These are (with default values):

    plugin_locations = None
    environment_id = 'launchpanel'
    style = 'space'
    title = 'Launch Panel'
    style_overrides = None
    parent = None

    Arguments can be provided as positional (in order, when not provided with an "=" sign), or keyword, when
    an "=" sign is included.

    :return: tuple of args, kwargs
    :rtype: (list, dict)
    """
    # -- The first argument is always the filepath being executed
    # -- by python, so ignore that.
    all_args = sys.argv[1:]

    # -- Define our args and keyword arguments. We need to seperate these
    args = list()
    kwargs = dict()

    for arg in all_args:

        # -- If it has an =, its a kwarg
        if '=' in arg:
            kwargs[arg.split('=')[0]] = arg.split('=')[1]

        else:
            # -- We're dealing with an arg, so just
            # -- add it
            args.append(arg)

    return args, kwargs
