import launchpad
import webbrowser


# ------------------------------------------------------------------------------
class GenericMax(launchpad.LaunchAction):
    """
    This example shows a straight forward action which opens a url
    to a specific address.
    """
    Name = 'Github'
    Description = 'Launches the github repository for launchpad'
    Groups = ['Help']

    # --------------------------------------------------------------------------
    @classmethod
    def run(cls):
        """
        This is used to initiate the default action for this plugin.
        """
        webbrowser.open('http://github.com/mikemalinowski')

    # --------------------------------------------------------------------------
    @classmethod
    def viability(cls):
        return cls.VALID
