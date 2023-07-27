import os
import sys
import launchpad
import subprocess


# ------------------------------------------------------------------------------
class GenericMax(launchpad.LaunchAction):
    """
    This example shows how we can dynamically generate plug-ins based
    on applications the user has installed. This means you do not have
    to create new plugins for every version of an application
    """
    Name = 'Max __VERSION__'
    Description = 'Launches Max __VERSION__'
    Groups = ['Applications']

    # -- Private property which can be altered if you have Max
    # -- on a completely different path
    Path = r'C:/Program Files/Autodesk/3ds Max __VERSION__/3dsmax.exe'

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
# -- Dynamically generate plugins for all the installed Max versions
this_module = sys.modules[__name__]

# -- Cycle an arbitrary range of Max versions, both historic and
# -- future
for version_number in range(16, 30):
    cls_name = GenericMax.__name__ + '20' + str(version_number)

    new_cls = type(
        cls_name,
        (GenericMax,),
        {
            'Name': GenericMax.Name.replace(
                '__VERSION__',
                '20%s' % version_number,
            ),
            'Description': GenericMax.Description.replace(
                '__VERSION__',
                '20%s' % version_number,
            ),
            'Path': GenericMax.Path.replace(
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
