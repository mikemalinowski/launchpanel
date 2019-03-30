

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    import launchpanel

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

    # -- Launch the panel window with the given arguments
    launchpanel.launch(
        *args,
        **kwargs
    )
