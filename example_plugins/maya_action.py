import os
import sys
import launchpad
import subprocess


# ------------------------------------------------------------------------------
class GenericMaya(launchpad.LaunchAction):
    """
    This example shows how we can dynamically generate plug-ins based
    on applications the user has installed. This means you do not have
    to create new plugins for every version of an application
    """
    Name = 'Maya __VERSION__'
    Description = 'Launches Maya __VERSION__'
    Groups = ['Applications']

    # -- Private property which can be altered if you have maya
    # -- on a completely different path
    Path = r'C:/Program Files/Autodesk/Maya__VERSION__/bin/maya.exe'

    # --------------------------------------------------------------------------
    @classmethod
    def run(cls):
        """
        This is used to initiate the default action for this plugin.
        """
        subprocess.Popen(
            [
                cls.Path,
            ],
        )

    @classmethod
    def state(cls):
        if os.path.exists(cls.Path):
            return launchpad.PluginStates.VALID
        return launchpad.PluginStates.INVALID


# ------------------------------------------------------------------------------
# -- Dynamically generate plugins for all the installed maya versions
this_module = sys.modules[__name__]

# -- Cycle an arbitrary range of maya versions, both historic and
# -- future
for version_number in range(16, 30):
    cls_name = GenericMaya.__name__ + '20' + str(version_number)

    new_cls = type(
        cls_name,
        (GenericMaya,),
        {
            'Name': GenericMaya.Name.replace(
                '__VERSION__',
                '20%s' % version_number,
            ),
            'Description': GenericMaya.Description.replace(
                '__VERSION__',
                '20%s' % version_number,
            ),
            'Path': GenericMaya.Path.replace(
                '__VERSION__',
                '20%s' % version_number,
            )
        }
    )

    # noinspection PyUnresolvedReferences
    if new_cls.state():
        setattr(
            this_module,
            cls_name,
            new_cls,
        )
