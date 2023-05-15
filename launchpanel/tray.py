import os
import qute
import traceback
from . import core


class LaunchPanelTray(qute.MemorableTimedProcessorTray):

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(LaunchPanelTray, self).__init__(
            identifier='Launch Panel Tray',
            icon=os.path.join(os.path.dirname(__file__), '_resources/launch.ico'),
            auto_process=False,
            interval=5,
        )

        self.widget = core.LaunchPanel(*args, **kwargs)
        self.widget.tabStateUpdated.connect(self.updateTabState)
        self.widget.show()

        self.message = None

        self.messageClicked.connect(self.message_clicked)

    # --------------------------------------------------------------------------
    def message_clicked(self):
        qute.utilities.request.message(
            title='LaunchPanel',
            label=self.message
        )

    # --------------------------------------------------------------------------
    def show_message(self, message):
        self.message = message
        self.showMessage('LaunchPanel', message)

    # --------------------------------------------------------------------------
    def updateTabState(self, action_list):
        for idx in range(action_list.count()):
            # -- Get the item, and check if there is a status
            item = action_list.item(idx)
            try:
                if item.status:
                    self.show_message(str(item.status))
            except:
                self.show_message(traceback.format_exc())

    # --------------------------------------------------------------------------
    def onActivate(self, reason):
        if reason == self.DoubleClick:
            self.widget.setVisible(not self.widget.isVisible())
        else:
            super(LaunchPanelTray, self).onActivate(reason)


# ------------------------------------------------------------------------------
def launch_tray(*args, **kwargs):
    """
    Launches a system tray application for the process of running reflection
    scans on a timer

    :return:
    """
    # -- Get a q-application instance
    q_app = qute.qApp()

    # -- Ensure the qapplication closes when the tray closes
    q_app.setQuitOnLastWindowClosed(False)

    # -- Create a memorable system tray
    tray = LaunchPanelTray(*args, **kwargs)

    # -- Show the tray
    tray.show()

    # -- Block the thread so we dont quit
    q_app.exec_()
