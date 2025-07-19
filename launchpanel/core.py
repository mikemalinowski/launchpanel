"""
LaunchPanel is a simple interface designed to expose LaunchPad Actions
to the user in an intuitive way.

LaunchActions are displayed in icon-centric list widgets, and they are
organised into tabs based on their groups. The user has the ability to
define tab orientation, icon size and plugin locations.

This module has the following dependencies:

    * launchpad
    * qtility
    * scribble (pip install scribble)

"""
import os
import sys
import time
import ctypes
import qtility
import scribble
import launchpad
import functools
import collections

from Qt import QtCore, QtGui, QtWidgets

from . import create
from . import styling
from . import resources
from . import constants as c


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class LaunchPanel(QtWidgets.QWidget):
    """
    This is the main Ui widget which makes up the LaunchPanel Ui.
    """
    # -- This is the enum for defining the state of the tab
    TAB_AUTO = 0
    TAB_SIDE = 1
    TAB_TOP = 2

    tabStateUpdated = QtCore.Signal(object)

    # --------------------------------------------------------------------------
    def __init__(self,
                 plugin_locations=None,
                 environment_id='launchpanel',
                 # style='space',
                 title='Launch Panel',
                 style_overrides=None,
                 parent=None):
        super(LaunchPanel, self).__init__(parent=parent)

        # -- Store our scribble id
        self.environment_id = environment_id

        # -- Store the base launch panel title
        self.base_title = title

        # -- Define our alert icon
        self._alert_icon = QtGui.QIcon(QtGui.QPixmap(resources.get('alert.png')))

        # -- Set the window properties
        self.setWindowTitle('Launch Panel')
        self.setWindowIcon(QtGui.QIcon(resources.get('launch.png')))

        # -- If we're on windows we need to tell windows that python is actually just
        # -- hosting an application and is not the application itself.
        if sys.platform == 'win32':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(c.APP_ID)

        # -- Create a default layout
        self.setLayout(qtility.layouts.slimify(QtWidgets.QVBoxLayout()))
        
        # -- Load in the ui
        self.ui = qtility.designer.load(resources.get('launchpad.ui'))
        self.layout().addWidget(self.ui)

        # -- Assign icons
        self.ui.tabPanel.setTabIcon(
            0,
            QtGui.QIcon(QtGui.QPixmap(resources.get('options.png'))),
        )

        qtility.styling.apply(
            [
                styling.get_style(),
            ],
            self,
        )

        # -- Set the window geometry if we have the settings
        settings = scribble.get(self.environment_id)
        self.window().setGeometry(
            *settings.get(
                'geometry',
                [
                    300,
                    300,
                    400,
                    400,
                ]
            )
        )

        # -- Update the icon size variable to reflect what it actually
        # -- is
        self.ui.iconSize.setValue(settings.get('icon_size', 50))
        self.ui.statusInterval.setValue(settings.get('status_inverval', 1800))
        self.ui.showBeta.setChecked(settings.get('show_beta', False))

        # -- Combine any paths we're given with any stored paths
        # -- and then ensure we remove any duplicates
        stored_plugin_paths = settings.get('plugin_locations', [])
        stored_plugin_paths.extend(plugin_locations or list())
        stored_plugin_paths = list(set(stored_plugin_paths))

        # -- Define the default settings
        self.tabMode = None
        self.setTabMode(scribble.get(environment_id).get('tabMode', self.TAB_AUTO))

        # -- We'll store all of our list widgets here so we can interact
        # -- with them as we need to
        self._action_lists = list()

        # -- Now we need to instance our action factory
        self.factory = launchpad.LaunchPad(plugin_locations=stored_plugin_paths)

        # -- Populate the ui with all our actions
        self.populate()

        # -- Each user has their own favourites tab which they
        # -- can pin things to
        self.user_tab = None
        self.populateUserActions()

        # -- Now we restore our tab based on the scribble settings
        self.restoreActiveTab()

        # -- Define the timer we will use to perform status
        # -- check updates. Default to 30 minutes if no settings
        # -- are present
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.setInterval(settings.get('status_inverval', 1800) * 1000)
        self._timer.timeout.connect(self.performStatusCheck)
        self._timer.start()

        # -- Hook up signals and slots
        self.ui.iconSize.valueChanged.connect(self.resizeIcons)
        self.ui.addPluginPath.clicked.connect(self.addPluginPath)
        self.ui.actionWizard.clicked.connect(self.initiateWizard)
        self.ui.tabPanel.currentChanged.connect(self.storeActiveTab)
        self.ui.removePluginPath.clicked.connect(self.removePluginPath)
        self.ui.tabModeCombo.currentIndexChanged.connect(self.setTabMode)
        self.ui.statusInterval.valueChanged.connect(self.updateStatusInterval)
        self.ui.showBeta.stateChanged.connect(self.toggleBetaPlugins)

        # -- Begin with a status check
        self.performStatusCheck()

    # --------------------------------------------------------------------------
    def setTabMode(self, tab_mode=None):
        """
        This updates the tab mode and the stylesheets.
        :param tab_mode:
        :return:
        """
        # -- If no tab mode is given we should look at the ui for
        # -- that information
        if tab_mode is None:
            tab_mode = self.ui.tabModeCombo.currentIndex()

        if tab_mode == self.tabMode and not self.tabMode == self.TAB_AUTO:
            return

        # -- Store the tab mode so we can query on the next
        # -- request
        self.tabMode = tab_mode

        # -- Ensure the combo box is also updated
        self.ui.tabModeCombo.setCurrentIndex(tab_mode)

        # -- Store the tab mode into the scribble data
        settings = scribble.get(self.environment_id)
        settings['tabMode'] = tab_mode
        settings.save()

        # -- Test whether the window is wide
        is_wide = self.size().width() > self.size().height()
        should_be_top = self.tabMode == self.TAB_AUTO and is_wide

        # -- If we're expected to have the tab at the top, or
        # -- if we're in auto mode and the window is wide, we
        # -- set the orientation of the tab bar to the top
        if self.tabMode == self.TAB_TOP or should_be_top:
            self.ui.tabPanel.setTabPosition(QtWidgets.QTabWidget.North)
            qtility.styling.apply(
                [
                    styling.get_style(),
                    resources.get('north.qss'),
                ],
                self.ui.tabPanel,
            )

        # -- To be here we're expected to have the tab on the side, or we're
        # -- in auto mode and the window is long, so we switch to a side
        # -- tab
        else:
            self.ui.tabPanel.setTabPosition(QtWidgets.QTabWidget.West)
            qtility.styling.apply(
                [
                    styling.get_style(),
                    resources.get('west.qss'),
                ],
                self.ui.tabPanel,
            )

    # --------------------------------------------------------------------------
    def populate(self):
        """
        This will populate the ui with all the plugins in the launchpad,
        clearing all current plugins
        """
        # -- Clear the plugin combo and refresh it
        self.ui.pluginPaths.clear()
        for path in self.factory.paths():
            self.ui.pluginPaths.addItem(path)

        # -- Clear all our list widget references
        self._action_lists = list()

        # -- This is a list of tabs we never want to remove
        protected_tabs = ['']

        # -- Start by clearing all tabs and entries in the 'all' panel
        while self.ui.tabPanel.count() > len(protected_tabs):
            for tab_index in range(self.ui.tabPanel.count()):
                if self.ui.tabPanel.tabText(tab_index) not in protected_tabs:
                    self.ui.tabPanel.removeTab(tab_index)
                    break

        # -- Get the scribble settings
        settings = scribble.get(self.environment_id)

        # -- Now we can begin populating all the tabs. We start by adding
        # -- the persistent 'All' tab which shows all actions
        widget = ActionListWidget(
            factory=self.factory,
            action_list=None,
            show_beta=self.ui.showBeta.isChecked(),
            size=settings.get('icon_size', 75),
            parent=self,
        )
        self._action_lists.append(widget)

        # -- Add the tab into the ui
        self.ui.tabPanel.insertTab(
            0,
            widget,
            'All',
        )

        # -- We now need to cycle over all the grouped identifiers
        # -- and create a ListWidget containing them.
        groups = self.factory.grouped_identifiers(
            show_beta=self.ui.showBeta.isChecked(),
        )

        group_names = reversed(sorted(list(groups.keys())))

        for group_name in group_names:

            # -- We do not show uncategorised items. They will
            # -- show in the 'All' tab
            if group_name == 'Uncategorised':
                continue

            widget = ActionListWidget(
                factory=self.factory,
                action_list=groups[group_name],
                show_beta=self.ui.showBeta.isChecked(),
                size=settings.get('icon_size', 75),
                parent=self,
            )

            # -- Hook up event signals specific to this widget type
            widget.alertPropogation.connect(self.updateTabState)

            # -- Hook up the event to update the ui whenever the
            # -- user scrolls over
            self.ui.tabPanel.insertTab(
                0,
                widget,
                group_name,
            )
            self._action_lists.append(widget)

    # --------------------------------------------------------------------------
    def populateUserActions(self):
        """
        Builds the users customisable tab
        """
        # -- Get the current tab name
        current_tab = self.ui.tabPanel.tabText(self.ui.tabPanel.currentIndex())

        # -- Read the user settings
        settings = scribble.get(self.environment_id)
        user_picked_actions = settings.get('user_actions', list())
        user_tab_index = self._getIndexFromTabName('[+]')

        if user_tab_index >= 0:
            self.user_tab = None
            self.ui.tabPanel.removeTab(user_tab_index)

        if not user_picked_actions:
            return

        # -- Build the tab
        widget = ActionListWidget(
            factory=self.factory,
            action_list=user_picked_actions,
            show_beta=self.ui.showBeta.isChecked(),
            size=settings.get('icon_size', 75),
            parent=self,
        )

        # -- Hook up event signals specific to this widget type
        widget.alertPropogation.connect(self.updateTabState)

        # -- Hook up the event to update the ui whenever the
        # -- user scrolls over
        self.ui.tabPanel.insertTab(
            0,
            widget,
            '[+]',
        )
        self._action_lists.append(widget)

        # -- Restore the tab selection
        self._setTabByName(current_tab)

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def resizeEvent(self, event):
        """
        Switch between North and west as the user resizes the panel.
        """

        # -- Call the function which handles the tab mode switching
        self.setTabMode(self.tabMode)

        # -- Store the current window size in our scribble settings
        self.storeWidgetGeometry()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def hideEvent(self, event):
        """
        Initiate a settings save when the ui is hidden / closed.
        """

        # -- Store the current window size in our scribble settings
        self.storeWidgetGeometry()

    # --------------------------------------------------------------------------
    def storeWidgetGeometry(self):
        """
        Save the current window position and size to settings.
        """

        # -- Store the current window size in our scribble settings
        window = self.window()
        settings = scribble.get(self.environment_id)
        settings['geometry'] = [
            window.pos().x() + 7,
            window.pos().y() + 32,
            window.width(),
            window.height(),
        ]

        settings.save()

    # --------------------------------------------------------------------------
    def addPluginPath(self, path=None):
        """
        Adds a plugin path to the launchpad factory, and refreshes
        the ui to show any additional plugins.

        :param path: Path to add. If no path is provided the user is prompted
            for one
        """
        # -- If we dont have a path, prompt the user for one
        if not path:
            path = QtWidgets.QFileDialog.getExistingDirectory(self)

            if not path:
                return

            # -- Conventionalise the paths
            path = path.replace('\\', '/')

        # -- Add the path and refresh the ui
        self.factory.add_path(path)

        # -- Update the paths in the scribble data
        settings = scribble.get(self.environment_id)
        settings['plugin_locations'] = self.factory.paths()
        settings.save()

        # -- Re-populate the ui
        self.populate()
        self.populateUserActions()

    # --------------------------------------------------------------------------
    def removePluginPath(self, path=None):
        """
        Removes the given (or prompted) path from the launchpad factory
        and refreshes the ui

        :param path: Path to remove. If no path is provided the current
            path in the combo is removed.

        :return:
        """
        # -- Take the given path, or use the combo box text
        path = path or self.ui.pluginPaths.currentText()

        # -- Remove the path and re-populate the ui only if the
        # -- path exists in the factory
        if path in self.factory.paths():
            self.factory.remove_path(path)
            self.populate()

            # -- Update the paths in the scribble data
            settings = scribble.get(self.environment_id)
            settings['plugin_locations'] = self.factory.paths()
            settings.save()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def storeActiveTab(self, *args, **kwargs):
        """
        This stores the currently active tab into the scribble data
        """
        settings = scribble.get(self.environment_id)
        settings['active_tab'] = self.ui.tabPanel.tabText(
            self.ui.tabPanel.currentIndex(),
        )
        settings.save()

    # --------------------------------------------------------------------------
    def restoreActiveTab(self):
        """
        Looks into the scribble data for the last active tab and applies
        that if it exists.
        """
        # -- Get the stored tab name from the settings
        settings = scribble.get(self.environment_id)
        tab_name = settings.get('active_tab', None)

        # -- If no tab information is stored we do not do anything
        if not tab_name:
            return

        # -- Cycle our tabs, and attempt to match it via name
        self._setTabByName(tab_name)

    # ----------------------------------------------------------------------------------
    def toggleBetaPlugins(self):

        settings = scribble.get(self.environment_id)
        settings['show_beta'] = self.ui.showBeta.isChecked()
        settings.save()

        self.populate()
        self.populateUserActions()

    # --------------------------------------------------------------------------
    def resizeIcons(self, icon_size=None):
        """
        Resizes the icons to the given size (or to the ui settings if no
        size is given). All changes through this method will be stored
        ready for the next run.

        :param icon_size:
        :return:
        """
        # -- Take the icon size, but if its not given read
        # -- the value in the ui
        icon_size = icon_size or self.ui.iconSize.value()
        
        # -- Cycle over all our action lists and propogate the icon
        # -- size change
        for action_list in self._action_lists:
            action_list.setIconSize(QtCore.QSize(icon_size, icon_size))

        # -- Store the value in the scribble settings
        settings = scribble.get(self.environment_id)
        settings['icon_size'] = self.ui.iconSize.value()
        settings.save()

    # --------------------------------------------------------------------------
    def updateStatusInterval(self, inverval=None):
        """
        Updates the time between status check intervals

        :return:
        """
        # -- Take the icon size, but if its not given read
        # -- the value in the ui
        interval = inverval or self.ui.statusInterval.value()

        self._timer.setInterval(interval * 1000)

        # -- Store the value in the scribble settings
        settings = scribble.get(self.environment_id)
        settings['status_inverval'] = interval
        settings.save()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def _getIndexFromTabName(self, name):
        """
        This will update the text panel based on the currently hovered item
        """
        for tab_idx in range(self.ui.tabPanel.count()):
            if self.ui.tabPanel.tabText(tab_idx) == name:
                return tab_idx

        return -1

    # --------------------------------------------------------------------------
    def _setTabByName(self, tab_name):
        # -- Cycle our tabs, and attempt to match it via name
        for tab_idx in range(self.ui.tabPanel.count()):
            if self.ui.tabPanel.tabText(tab_idx) == tab_name:
                self.ui.tabPanel.setCurrentIndex(tab_idx)

    # --------------------------------------------------------------------------
    def initiateWizard(self):
        wizard = create.ClassWizard()
        wizard.exec_()

        if wizard.save_directory:
            self.addPluginPath(wizard.save_directory)

    # --------------------------------------------------------------------------
    def performStatusCheck(self):
        """
        This will cycle through all the action list widgets and ask each
        of them to perform a status check. These will be run in a thread, and
        if there are any changes in state the updateTabState will be called

        :return:
        """
        for list_widget in self._action_lists:
            list_widget.performStatusCheck()

    # --------------------------------------------------------------------------
    def performStatusCheckOfActionType(self, action_type):
        """
        This will cycle through all the action list widgets and ask each
        of them to perform a status check. These will be run in a thread, and
        if there are any changes in state the updateTabState will be called

        :return:
        """

        for list_widget in self._action_lists:
            for idx in range(list_widget.count()):
                item = list_widget.item(idx)

                if item.identifier == action_type:
                    list_widget.performSingleStatusCheck(item)

    # --------------------------------------------------------------------------
    def updateTabState(self, action_list):
        """
        Updates the tab state for the action list based on whether there
        are any active alerts

        :param action_list: ActionListWidget to check
        :type action_list: ActionListWidget

        :return:
        """
        # -- Assume no alerts by default, so use a null icon
        icon_to_use = QtGui.QIcon()

        # -- Cycle over our list widgets items
        for idx in range(action_list.count()):

            # -- Get the item, anad check if there is a status
            if action_list.item(idx).status:
                icon_to_use = self._alert_icon

        # -- Now cycle over our tab panels so we can find the tab which
        # -- this list widget resides under
        for idx in range(self.ui.tabPanel.count()):

            # -- Get the widget
            widget = self.ui.tabPanel.widget(idx)

            # -- We're only interested in the matching list widget
            if widget != action_list:
                continue

            # -- Assign the icon
            self.ui.tabPanel.setTabIcon(idx, icon_to_use)

        self.tabStateUpdated.emit(action_list)


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class ActionListWidget(QtWidgets.QListWidget):
    """
    This is a QListWidget which is specifically designed to take in the
    launchpad factory and list of actions to be shown.
    """
    # -- This signal is used to alert that changes in
    # -- state have occured
    alertPropogation = QtCore.Signal(object)

    # --------------------------------------------------------------------------
    def __init__(self, factory, action_list, show_beta=False, size=75, parent=None):
        super(ActionListWidget, self).__init__(parent=parent)

        # -- store the launch panel
        self._launch_panel = parent
        self._parent = parent
        self._show_beta = show_beta

        # -- This variable can be used to query whether this widget has any items
        # -- within it which have alerts
        self.status_threads = list()
        self.status_tracker = dict()

        # -- Define some optimisation variables
        self._size = QtCore.QSize(size, size)

        # -- Define our visual parameters on the widget
        self.setSpacing(10)
        self.setIconSize(self._size)
        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setSortingEnabled(False)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QListWidget.NoSelection)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        # -- Store our factory and list of actions
        self.factory = factory
        self.action_list = action_list or factory.identifiers(show_beta=show_beta)

        # -- Populate the panel
        self.populate()

        self.setStyleSheet(
            """
                background-image: url(%s);
                background-position: top right;
                background-origin: content;
                background-repeat: repeat-xy;
            """ % resources.get('bg.png')
        )

        # -- Hook up the event to allow the window title to show the
        # -- text of the active item
        self.itemEntered.connect(self.updateWindowTitle)

    # --------------------------------------------------------------------------
    def populate(self):
        """
        This will populate the list widget with all the elements defined
        in the action list during initialisation.
        """
        self.clear()
        valid_actions = self.factory.identifiers(
            show_beta=self._show_beta
        )

        # -- Start by adding all the required items
        for idx, action_name in enumerate(self.action_list):

            if action_name not in valid_actions:
                continue

            # -- Create the item
            item = QtWidgets.QListWidgetItem(action_name)
            item.identifier = action_name
            item.setToolTip(action_name)

            # -- We will store status information on the item
            # -- which will change periodically. So assign these
            # -- as blank values to begin with
            item.status = None

            # -- Add the item
            self.addItem(item)

        # -- Now assign the delegates to the items
        for idx in range(self.count()):
            item = self.item(idx)

            delegate = ActionDelegate(
                action=self.factory.request(item.identifier),
                size=self._size,
                parent=self,
            )

            delegate.needsRedraw.connect(self.viewport().update)

            # -- Assign the delegate
            self.setItemDelegateForRow(
                idx,
                delegate
            )

    # --------------------------------------------------------------------------
    def setIconSize(self, size):
        """
        Overrides the usual setIconSize and passes the size information
        to all the registered draw delegates.
        """
        super(ActionListWidget, self).setIconSize(size)

        for row_idx in range(self.count()):
            self.itemDelegateForRow(row_idx).buildPixmaps(size)

    # --------------------------------------------------------------------------
    def run(self, item):
        """
        Invokes the run method of the clicked action

        :param item: action item to run
        """

        # -- pass a NoneType item
        if not item:
            return

        action = self.factory.request(item.identifier)

        # -- check we have not disabled the action
        if launchpad.PluginStates.DISABLED in action.state():
            return

        action.run()

        # -- Trigger a status check for this item
        self._parent.performStatusCheckOfActionType(item.identifier)

    # --------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.run(self.itemAt(event.pos()))

    # --------------------------------------------------------------------------
    def contextMenuEvent(self, event):
        """
        Generate a context menu based on the action plugin the user
        has right clicked.

        :param event: QContextMenuEvent
        """
        item = self.itemAt(event.pos())

        if not item:
            return

        # -- Get the settings
        settings = scribble.get(self._launch_panel.environment_id)
        is_user_item = item.identifier in settings.get(
            'user_actions',
            list(),
        )

        # -- Add all the plugin menu items first
        menu_dict = collections.OrderedDict()
        menu_dict.update(self.factory.request(item.identifier).actions())
        menu_dict['-'] = None

        # -- Now add the launchpad options
        if is_user_item:
            menu_dict['Remove From User Panel'] = functools.partial(
                self.removeUserItem,
                item.identifier,
            )
        else:
            menu_dict['Add To User Panel'] = functools.partial(
                self.addUserItem,
                item.identifier,
            )

        # -- Pop up the menu
        menu = qtility.menus.create(menu_dict, parent=self)
        menu.popup(event.globalPos())

    # --------------------------------------------------------------------------
    def removeUserItem(self, name):
        settings = scribble.get(self._launch_panel.environment_id)

        if 'user_actions' not in settings:
            return

        settings['user_actions'].remove(name)
        settings.save()

        self._launch_panel.populateUserActions()

    # --------------------------------------------------------------------------
    def addUserItem(self, name):
        settings = scribble.get(self._launch_panel.environment_id)
        user_actions = settings.get('user_actions', list())
        user_actions.append(name)
        settings['user_actions'] = user_actions
        settings.save()

        self._launch_panel.populateUserActions()

    # --------------------------------------------------------------------------
    def updateWindowTitle(self, item):
        """
        Used to update the title bar of the window based on what item
        is being hovered over

        :param item: Item to display text from

        :return: None
        """
        if not item:
            return

        self.window().setWindowTitle(
            '%s : %s' % (self._parent.base_title, item.text())
        )

    # --------------------------------------------------------------------------
    def performStatusCheck(self):
        """
        This cycles over all the items in the list and will ask for the status
        of that item. All status checks are performed in threads to ensure they
        do not block the interface.

        :return:
        """

        # -- Cycle each item, if there is a change in the status of an item
        # -- then trigger a redraw of it
        for idx in range(self.count()):

            # -- Get the item
            item = self.item(idx)
            self.performSingleStatusCheck(item)

    # --------------------------------------------------------------------------
    def performSingleStatusCheck(self, item):
        """
        This cycles over all the items in the list and will ask for the status
        of that item. All status checks are performed in threads to ensure they
        do not block the interface.

        :return:
        """
        # -- Get the plugin this item represents
        plugin = self.factory.request(item.identifier)

        # -- The status is different to what it was before so
        # -- we need to update the view accordingly
        index = self.indexFromItem(item)
        delegate = self.itemDelegate(index)

        # -- Create the thread which we will perform the check
        thread = StatusCheckThread(
            plugin=plugin,
            item=item,
            delegate=delegate,
        )

        # -- Once the thread is finished, we need to parse the
        # -- result, so connect the finished signal
        thread.finished.connect(self.updateStatusChecks)

        # -- To ensure we can iterate as optimally as possible, track
        # -- all the threads which we are generating
        self.status_threads.append(thread)

        # -- Kick the thread off
        thread.start()

    # --------------------------------------------------------------------------
    def updateStatusChecks(self, *args, **kwargs):
        """
        This function will cycle through any status threads and update the
        item and delegate according to the status information of that thread.

        :return:
        """
        threads_to_remove = list()

        # -- Cycle over our active threads
        for thread in self.status_threads:

            # -- If the thread is not finished we leave it
            # -- to continue
            if not thread.isFinished():
                continue

            # -- Ensure we remove this thread once we're done with it
            threads_to_remove.append(thread)

            thread.delegate.requires_attention = thread.status

            # -- Update the tooltip. If there is no alert state it can
            # -- simply by blank
            thread.item.setToolTip(str(thread.status or thread.plugin.Description))
            thread.item.status = thread.status

            # -- Finally we trigger a redraw of this item
            self.update(self.indexFromItem(thread.item))

            # -- If the status is different we need to emit a status
            # -- change
            if thread.item.identifier in self.status_tracker:
                if thread.status != self.status_tracker[thread.item.identifier]:
                    self.alertPropogation.emit(self)
                    self.status_tracker[thread.item.identifier] = thread.status
            
            else:
                # -- In this situation its the first time we have run for this
                # -- item, so we only want to trigger an alert propogation if there
                # -- is an actual message
                self.status_tracker[thread.item.identifier] = thread.status
                
                if thread.status:
                    self.alertPropogation.emit(self)

        # -- Now we can clean up any complete threads. We do not do this
        # -- during the update iteration as the lists are mutable
        for thread in threads_to_remove:
            if thread in self.status_threads:
                self.status_threads.remove(thread)


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class ActionDelegate(QtWidgets.QItemDelegate):
    """
    This is responsible for painting the delegate. We use a delegate to
    allow us to do color/grayscale switching etc.
    """
    # -- These are class attributes as they will only ever need
    # -- to be defined once regardless of how many instances we
    # -- create.
    BACKGROUND_COLOUR = [255, 255, 255]
    LABEL_BACKGROUND = QtGui.QColor(*[0, 0, 0], a=200)
    BLACK_PEN = QtGui.QPen(QtCore.Qt.black)
    WHITE_PEN = QtGui.QPen(QtCore.Qt.white)
    DESC_PEN = QtGui.QPen(QtGui.QColor(255, 255, 255, a=60))
    DESC_ACTIVE_PEN = QtGui.QPen(QtGui.QColor(255, 255, 255, a=100))
    TRANSPARENT_BRUSH = QtGui.QBrush(QtCore.Qt.transparent)

    _DEFAULT_ICON = resources.get('launch.png')

    needsRedraw = QtCore.Signal()

    # -- This pixmap will always be the same, so we only need to build it
    # -- once and can then share it
    _ALERT_SIZE = 25
    _ALERT_PIXMAP = None

    # --------------------------------------------------------------------------
    def __init__(self, action, size, parent=None):
        super(ActionDelegate, self).__init__(parent=parent)

        # -- Store the action, as this is used during painting
        self.action = action
        self.state = action.state()
        self.requires_attention = False

        # -- Extract the icon, and create the pixmaps for the
        # -- icons
        self.icon_colour = None
        self.icon_bw = None
        self.size = size
        self.polygon = None
        self.highlight = None
        self.buildPixmaps(size)

    # --------------------------------------------------------------------------
    def buildPixmaps(self, size):
        """
        Rebuilds the colour and black-and-white pixmaps to the specified
        sizes and updates the size hint
        """

        # -- If we have an icon, and we can access the
        if not self.action:
            return

        icon_path = self._DEFAULT_ICON

        # -- If we have an icon path, generate a colour
        # -- and a black and white variation
        if self.action.Icon and os.path.exists(self.action.Icon):
            icon_path = self.action.Icon

        # -- Create a scaled version of our icon
        self.icon_colour = QtGui.QPixmap(icon_path).scaled(
            size.height(),
            size.height(),
            mode=QtCore.Qt.SmoothTransformation,
        )

        # -- Build the pixmap we use to show alerts, but only build it
        # -- if it does not already exist
        if not ActionDelegate._ALERT_PIXMAP:
            ActionDelegate._ALERT_PIXMAP = QtGui.QPixmap(resources.get('alert.png')).scaled(
                self._ALERT_SIZE,
                self._ALERT_SIZE,
                mode=QtCore.Qt.SmoothTransformation,
            )

        # -- Now create a grayscale version of our icon
        self.icon_bw = qtility.pixmaps.grayscaled(self.icon_colour)

        # -- Generate the painter polygon
        self.polygon = QtGui.QPolygonF()
        self.polygon.append(QtCore.QPoint(0, size.height() * 0.25))
        self.polygon.append(QtCore.QPoint(size.width() * 0.25, 0))
        self.polygon.append(QtCore.QPoint(size.width(), 0))
        self.polygon.append(QtCore.QPoint(size.width(), size.height()))
        self.polygon.append(QtCore.QPoint(0, size.height()))

        # -- Store this size value so it can be returned as part
        # -- of the size hint
        self.size = size

        # -- We want to load the image as a q-image to allow us to
        # -- inspect the general colour of the icon for use as a highlighting
        # -- mechanism.
        image = QtGui.QImage(icon_path)
        counter = 0
        r, g, b = [], [], []

        # -- Cycle the pixels and pull out the colour
        for x in range(0, int(image.width() * 0.1)):
            for y in range(0, int(image.height() * 0.1)):
                counter += 1
                colors = QtGui.QColor(image.pixel(x * 10, y * 10)).getRgbF()

                r.append(colors[0])
                g.append(colors[1])
                b.append(colors[2])

        # -- Providing we have a valid image, we set the highlight
        # -- colour
        if len(r):
            self.highlight = QtGui.QColor(
                (sum(r) / len(r)) * 255,
                (sum(g) / len(g)) * 255,
                (sum(b) / len(b)) * 255,
                a=100,
            )

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def sizeHint(self, *args, **kwargs):
        return self.size

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def paint(self, painter, option, index):
        """
        This is responsible for painting the delegate. We use a delegate to
        allow us to do color/grayscale switching etc.
        """
        # -- Define our default draw variables. These will remain
        # -- the same unless the option state is different to the
        # -- defaults
        hovering = False
        icon_opacity = 0.5
        icon_px = self.icon_bw

        # -- If we're hovering lets increase the opacity and use
        # -- the colour icon
        disabled = launchpad.PluginStates.DISABLED in self.state

        if option.state & QtWidgets.QStyle.State_MouseOver:
            hovering = True
            icon_opacity = 1
            icon_px = self.icon_colour

        if disabled:
            icon_opacity = 0.25
            icon_px = self.icon_bw

        if hovering:
            gradient = QtGui.QLinearGradient(
                0,
                option.rect.y(),
                0,
                option.rect.y() + option.rect.height(),
            )

            if self.highlight and not disabled:
                gradient.setColorAt(0, self.highlight)
                gradient.setColorAt(1, QtGui.QColor(0, 0, 0, a=0))
                painter.setBrush(gradient)
                painter.setPen(QtGui.QColor(0, 0, 0, a=0))
                painter.drawRect(
                    option.rect,
                )

        if self.requires_attention:
            painter.setBrush(QtGui.QBrush(QtCore.Qt.red))
            painter.drawPixmap(
                option.rect.width() - self._ALERT_SIZE,
                option.rect.y() + 10,
                self._ALERT_SIZE,
                self._ALERT_SIZE,
                self._ALERT_PIXMAP,
            )

        # -- Define the opacity of the painter based on the values
        # -- we have been given and draw the pixmap
        painter.setOpacity(icon_opacity)
        painter.drawPixmap(
            option.rect.x(),
            option.rect.y(),
            self.size.height(),
            self.size.height(),
            icon_px,
        )

        # -- Now we restore the opacity back to full
        painter.setOpacity(1)
        font_size = max(8, (int(self.size.height() * 0.15)))
        painter.setFont(QtGui.QFont("ariel", font_size))
        text_rect = QtCore.QRect(
            option.rect.x() + self.size.width() + (self.size.width() * 0.2),
            option.rect.y() + (self.size.height() * 0.1),
            option.rect.width(),
            option.rect.height() * 0.5,
        )
        # -- Draw the actual text
        painter.setPen(QtGui.QPen(QtCore.Qt.white))
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            self.action.Name,
        )

        painter.setPen(self.DESC_PEN)

        if hovering:
            painter.setPen(self.DESC_ACTIVE_PEN)

        y_offset = 50
        desc_rect = QtCore.QRect(
            option.rect.x() + self.size.width() + (self.size.width() * 0.4),
            option.rect.y() + (option.rect.height() * 0.5),
            option.rect.width(),
            option.rect.height() - (option.rect.height() * 0.5),
        )
        # -- Draw the actual text
        painter.drawText(
            desc_rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            self.action.Description,
        )

        painter.drawLine(
            option.rect.x(),
            option.rect.y(),
            option.rect.width(),
            option.rect.y(),
        )


# ------------------------------------------------------------------------------
class StatusCheckThread(QtCore.QThread):
    """
    This is the thread which calls the status of a plugin. This is to ensure
    the status check is never blocking to the UI
    """

    # --------------------------------------------------------------------------
    def __init__(self, plugin, item, delegate):
        super(StatusCheckThread, self).__init__()
        self.plugin = plugin
        self.item = item
        self.delegate = delegate
        self.status = None

    # --------------------------------------------------------------------------
    def runAfterDelay(self):
        # -- We're running code from within a plugin, so we wrap it as we
        # -- cannot guarantee its quality
        try:
            # -- skip any INVALID plugins
            if self.plugin.state() == launchpad.PluginStates.INVALID:
                return

            # -- only update the tooltip if we have a Status to report
            self.status = self.plugin.status_message() or None

        except:
            print('Failed to get status for {}'.format(self.item.identifier))
            print(sys.exc_info())

    # --------------------------------------------------------------------------
    def run(self):
        time.sleep(self.plugin.STATUS_DELAY)
        self.runAfterDelay()


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def launch(blocking=True, show_splash=True, *args, **kwargs):
    """
    Creates (or uses) the QApplication and instances the widget.
    :param blocking:
    :param args:
    :param kwargs:
    :return:
    """
    q_app = qtility.app.get()

    splash_screen = None

    if show_splash:
        try:
            if show_splash and os.path.exists(show_splash):
                splash_path = show_splash

                splash_screen = QtWidgets.QSplashScreen(splash_path)
                splash_screen.show()

        except:
            pass

    # -- get any passed args that we can use
    title = kwargs.pop('title', '')
    icon = kwargs.pop('icon', '')

    # -- Create a window and embed our widget into it
    launch_widget = LaunchPanel(*args, **kwargs)
    launch_window = QtWidgets.QMainWindow(parent=qtility.windows.application())

    # -- Update the geometry of the window to the last stored
    # -- geometry
    launch_window.setGeometry(launch_widget.geometry())
    launch_window.setCentralWidget(launch_widget)

    # -- Set the window properties
    launch_window.setWindowTitle(
        title or 'Launch Panel'
    )
    launch_window.setWindowIcon(
        QtGui.QIcon(icon or resources.get('launch.png'))
    )

    # -- Show the ui, and if we're blocking call the exec_
    launch_window.show()

    if show_splash and splash_screen is not None:
        splash_screen.finish(launch_window)

    if blocking:
        q_app.exec_()

    return launch_window
