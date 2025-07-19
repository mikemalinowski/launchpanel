"""
This is a plugin creator wizard to make it easy for users to generate
their own plugins without coding.
"""
import os
import sys
import qtility
import launchpad

from Qt import QtCore, QtWidgets, QtGui


# ------------------------------------------------------------------------------
# -- This is the template code for all action plugins
PLUGIN_TEMPLATE = """
import os
import launchpad
import subprocess

class _ACTION_NAME_Plugin(launchpad.LaunchAction):
    Name = '_ACTION_NAME_'
    Description = \"\"\"_ACTION_DESCRIPTION_\"\"\"
    Icon = __file__[:-3] + '.png'
    Groups = [_GROUPS_]

    Version = 0

    @classmethod
    def run(cls):
_ACTION_COMMAND_

    @classmethod
    def actions(cls):
        return dict()

    @classmethod
    def properties(cls):
        return dict()
"""


# ------------------------------------------------------------------------------
def _get_resource(name):
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
    ).replace('//', '/')


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ClassWizard(QtWidgets.QWizard):
    """
    This is the main wizard class which guides the user through the 
    plugin creation. 
    """

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(ClassWizard, self).__init__(parent)

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        self.setWindowTitle('Action Wizard')

        self.setPixmap(
            QtWidgets.QWizard.WatermarkPixmap,
            QtGui.QPixmap(_get_resource('wizard.png')),
        )

        qtility.styling.apply(
            [
                _get_resource('space.qss'),
                _get_resource('wizard.qss'),
            ],
            self,
        )

        self.save_directory = None

        # -- Add pages to the wizard
        self.addPage(IntroductionPage())
        self.addPage(DetailsPage())
        self.addPage(GroupsPage())
        self.addPage(CommandPage())
        self.addPage(SummaryPage())

    # --------------------------------------------------------------------------
    def accept(self):
        """
        Upon acceptence, we can generate a plugin from the template.
        """
        # -- Start by pulling out all the action data the user
        # -- has inputted
        action_name = self.field('actionName')
        action_type = self.field('actionCommandType')
        action_groups = self.field('actionGroups')
        action_command = self.field('actionCommand')
        action_description = self.field('actionDescription').strip()
        save_location = self.field('actionSaveLocation')

        # # -- Conform the groups
        action_groups = [line.strip() for line in action_groups.splitlines()]

        # -- We need to ensure the action command is indented
        # -- correct
        if action_type == 0:
            # -- We're dealing with pure python code to execute
            formatted_action = []
            for line in action_command.splitlines():
                formatted_action.append((' ' * 8) + line)
            action_command = '\r\n'.join(formatted_action)

        elif action_type == 1:
            # -- We're dealing with a python file which needs executing
            action_command.replace('\\', '/')
            action_command = (' ' * 8) + 'execFile(\'%s\')' % action_command

        elif action_type == 2:
            # -- We're dealing with a subprocess
            action_command = action_command.replace('//', '/')
            action_command = 'subprocess.Popen(\'%s\')' % action_command
            action_command = (' ' * 8) + action_command

        # -- Start updating the template
        template = PLUGIN_TEMPLATE[:]
        template = template.replace('_ACTION_NAME_', action_name.replace(' ', ''))
        template = template.replace('_ACTION_COMMAND_', action_command)
        template = template.replace('_ACTION_DESCRIPTION_', action_description)
        template = template.replace('_GROUPS_', "'" + "', '".join(action_groups) + "'")

        # -- Ensure our save directory exists
        save_dir = os.path.dirname(save_location)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # -- Write out the file
        with open(save_location, 'w') as f:
            f.write(template)

        # -- Store the save directory
        self.save_directory = save_dir

        # -- Super to finalise
        super(ClassWizard, self).accept()

# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class BasePage(QtWidgets.QWizardPage):

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(BasePage, self).__init__(parent=parent)

        self.setLayout(qtility.layouts.slimify(QtWidgets.QVBoxLayout()))


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class IntroductionPage(BasePage):

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(IntroductionPage, self).__init__(parent)

        # -- Load in our ui element
        self.ui = qtility.designer.load(_get_resource('wizard_page_one.ui'))
        self.layout().addWidget(self.ui)

        # -- Register the field
        self.registerField('actionName', self.ui.actionName)


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class DetailsPage(BasePage):

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(DetailsPage, self).__init__(parent)

        # -- Load in our ui element
        self.ui = qtility.designer.load(_get_resource('wizard_page_two.ui'))
        self.layout().addWidget(self.ui)

        # -- Register the field
        self.registerField(
            'actionDescription',
            self.ui.actionDescription,
            'plainText',
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class GroupsPage(BasePage):

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(GroupsPage, self).__init__(parent)

        # -- Load in our ui element
        self.ui = qtility.designer.load(_get_resource('wizard_page_three.ui'))
        self.layout().addWidget(self.ui)

        # -- Register the field
        self.registerField(
            'actionGroups',
            self.ui.actionGroups,
            'plainText',
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class CommandPage(BasePage):

    DESCRIPTIONS = {
        'Execute Python Code': 'This will execute the python code you write in this box whenever the action is run. It will be run "as-is."',
        'Execute Python Script File': 'This will execute a python script on the run of the action. You should copy/paste (write) the filepath to the script in the box below.',
        'Execute Command Line': 'This will run the given file as if its on the command line.'
    }

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(CommandPage, self).__init__(parent)

        # -- Load in our ui element
        self.ui = qtility.designer.load(_get_resource('wizard_page_four.ui'))
        self.layout().addWidget(self.ui)

        # -- Register the field
        self.registerField('actionCommand', self.ui.actionCommand, "plainText")
        self.registerField('actionCommandType', self.ui.actionCommandType)

        # -- Hook up signals and slots
        self.ui.actionCommandType.currentIndexChanged.connect(
            self.updateActionTypeDescription
        )

        self.updateActionTypeDescription()

    # --------------------------------------------------------------------------
    def updateActionTypeDescription(self):
        self.ui.commandTypeDescription.setText(
            self.DESCRIPTIONS[self.ui.actionCommandType.currentText()],
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class SummaryPage(BasePage):
    COMMANDS = [
        'Execute Python Code',
        'Execute Python Script File',
        'Execute Command Line',
    ]

    SUMMARY = """
    <html><head/><body><p>Your action (<span style=" color:#2fc1ff;">actionName</span>) will <span style=" color:#2fc1ff;">actionType</span> using the data shown below. It will be shown in the groups <span style=" color:#2fc1ff;">actionGroups</span>.</p></body></html>
    """

    # --------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(SummaryPage, self).__init__(parent)

        # -- Load in our ui element
        self.ui = qtility.designer.load(_get_resource('wizard_page_five.ui'))
        self.layout().addWidget(self.ui)

        self.registerField('actionSaveLocation', self.ui.actionSaveLocation)

        self.ui.changeSaveLocation.clicked.connect(
            self.changeSavePath,
        )

    # --------------------------------------------------------------------------
    def initializePage(self):
        # -- We need to collage all the information we have so far to
        # -- allow the user to confirm.
        action_name = self.field('actionName')
        action_type = self.field('actionCommandType')
        action_groups = self.field('actionGroups')
        action_command = self.field('actionCommand')

        # # -- Conform the groups
        action_groups = [
            line.strip()
            for line in action_groups.splitlines()
        ]

        # -- Build up the summary text
        summary = self.SUMMARY.strip()
        summary = summary.replace('actionName', action_name)
        summary = summary.replace('actionType', self.COMMANDS[action_type])
        summary = summary.replace('actionGroups', ', '.join(action_groups))
        self.ui.actionOverview.setText(summary)

        # -- Show the command
        self.ui.actionCommandSummary.setText(action_command)

        # -- Define the default save location
        self.ui.actionSaveLocation.setText(
            os.path.join(
                launchpad.LAUNCHPAD_USER_PLUGIN_DIR,
                '%s.py' % action_name,
            ).replace('//', '/')
        )

    # --------------------------------------------------------------------------
    def changeSavePath(self):
        """
        Allows the user to specify a different filepath

        :return:
        """
        # -- Browse for a file
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            dir=launchpad.LAUNCHPAD_USER_PLUGIN_DIR,
            filter='(*.py)*.py',
        )

        # -- If none, we dont change any values
        if not path:
            return None

        # -- Formalise the path
        path = path.replace('//', '//')
        if not path.lower().endswith('.py'):
            path += '.py'

        # -- Apply the change
        self.ui.actionSaveLocation.setText(
            path.replace('//', '//')
        )


# ------------------------------------------------------------------------------
def show():
    _wizard = ClassWizard()
    _wizard.exec_()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app = qtility.app.get()
    _wizard = ClassWizard()
    _wizard.show()
    sys.exit(app.exec_())
