import os


def location():

    return os.path.join(
        os.path.dirname(__file__),
        '_resources',
    )


def get(name):
    """
    This is a convinience function to get files from the resources directory
    and correct handle the slashing.

    :param name: Name of file to pull from the resource directory

    :return: Absolute path to the resource requested.
    """
    return os.path.join(
        os.path.dirname(__file__),
        '_resources',
        name,
    ).replace('\\', '/')


def all():
    files = list()
    for filename in os.listdir(location()):
        files.append(os.path.join(location(), filename).replace('\\', '/'))
    return files