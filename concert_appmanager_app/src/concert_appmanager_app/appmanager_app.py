#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_qt_gui/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

from __future__ import division
import os

from python_qt_binding import loadUi
from PyQt4.QtCore import Qt, QAbstractListModel, Signal
from PyQt4.QtGui import QIcon, QWidget, QLabel, QComboBox
from PyQt4.QtGui import QSizePolicy, QTextEdit, QPushButton
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout, QPlainTextEdit
from PyQt4.QtGui import QGridLayout, QTextCursor, QDialog, QTreeWidgetItem

import rospkg
import rospy
from rocon_std_msgs.msg import Remapping
from rocon_std_msgs.srv import GetPlatformInfo
from rocon_app_manager_msgs.srv import Status, Invite, StartApp, StopApp
from qt_gui.plugin import Plugin

from appmanager_app_info import AppManagerApphInfo
##############################################################################
# Dynamic Argument Layer Classes
##############################################################################


class DynamicArgumentLayer():
    def __init__(self, dialog_layout, name='', add=False, params=[]):
        self.dlg_layout = dialog_layout
        self.name = name
        self.add = add
        self.params = params
        self.params_list = []

        params_item = []
        for k in self.params:
            param_name = k[0]
            param_type = k[1]
            param_widget = None
            params_item.append([param_name, param_widget, param_type])
        self.params_list.append(params_item)

        print "DAL: %s" % (self.params_list)

        self.arg_ver_sub_widget = QWidget()
        self.arg_ver_layout = QVBoxLayout(self.arg_ver_sub_widget)
        self.arg_ver_layout.setContentsMargins(0, 0, 0, 0)
        self._create_layout()

    def _create_layout(self):
        name_hor_sub_widget = QWidget()
        name_hor_layout = QHBoxLayout(name_hor_sub_widget)

        name_widget = QLabel(self.name + ": ")
        name_hor_layout.addWidget(name_widget)
        if self.add == True:
            btn_add = QPushButton("+", name_hor_sub_widget)

            btn_add.clicked.connect(self._push_param)
            btn_add.clicked.connect(self._update_item)
            name_hor_layout.addWidget(btn_add)

            btn_subtract = QPushButton("-", name_hor_sub_widget)
            btn_subtract.clicked.connect(self._pop_param)
            btn_subtract.clicked.connect(self._update_item)
            name_hor_layout.addWidget(btn_subtract)
            pass

        self.arg_ver_layout.addWidget(name_hor_sub_widget)
        self.dlg_layout.addWidget(self.arg_ver_sub_widget)
        self._update_item()

    def _update_item(self):
        widget_layout = self.arg_ver_layout
        item_list = self.params_list

        widget_list = widget_layout.parentWidget().children()
        while len(widget_list) > 2:
            added_arg_widget = widget_list.pop()
            widget_layout.removeWidget(added_arg_widget)
            added_arg_widget.setParent(None)
            added_arg_widget.deleteLater()

        #resize
        dialog_widget = widget_layout.parentWidget().parentWidget()
        dialog_widget.resize(dialog_widget.minimumSize())
        for l in item_list:
            params_hor_sub_widget = QWidget()
            params_hor_layout = QHBoxLayout(params_hor_sub_widget)
            for k in l:
                param_name = k[0]
                param_type = k[2]
                name_widget = QLabel(param_name + ": ")
                if param_type == 'string' or param_type == 'int':
                    k[1] = QTextEdit()
                    k[1].setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
                    k[1].setMinimumSize(0, 30)
                    k[1].append("")
                elif param_type == 'bool':
                    k[1] = QTextEdit()
                    k[1] = QComboBox()
                    k[1].setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
                    k[1].setMinimumSize(0, 30)

                    k[1].addItem("True", True)
                    k[1].addItem("False", False)

                params_hor_layout.addWidget(name_widget)
                params_hor_layout.addWidget(k[1])
            widget_layout.addWidget(params_hor_sub_widget)

    def _push_param(self):
        params_item = []
        for k in self.params:
            param_name = k[0]
            param_type = k[1]
            param_widget = None
            params_item.append([param_name, param_widget, param_type])
        self.params_list.append(params_item)

    def _pop_param(self):
        if len(self.params_list) > 1:
            self.params_list.pop()
        else:
            pass

    def _get_param_list(self):
        return self.params_list
        pass

##############################################################################
# ConductorGraph Classes
##############################################################################


class AppManagerApp(Plugin):

    _deferred_fit_in_view = Signal()
    _client_list_update_signal = Signal()

    def __init__(self, context):
        self._context = context
        super(AppManagerApp, self).__init__(context)
        self.initialised = False
        self.setObjectName('App Manager App')

        self._client_info_list = {}
        self._widget = QWidget()
        self.cur_selected_client_name = ""
        self.pre_selected_client_name = ""

        self.app_manager_app_info = AppManagerApphInfo()
        self.app_manager_app_info._reg_event_callback(self._update_client_list)

        rospack = rospkg.RosPack()
        ui_file = os.path.join(rospack.get_path('concert_appmanager_app'), 'ui', 'appmanager_app.ui')
        self._widget.setObjectName('AppManagerAppUi')
        loadUi(ui_file, self._widget, {})
        if context.serial_number() > 1:
            self._widget.setWindowTitle(self._widget.windowTitle() + (' (%d)' % context.serial_number()))

        #self._widget.refresh_graph_push_button.setIcon(QIcon.fromTheme('view-refresh'))
        self._widget.refresh_graph_push_button.setIcon(QIcon.fromTheme('window-new'))
        self._widget.refresh_graph_push_button.pressed.connect(self._update_client_info)
        self._widget.fit_in_view_push_button.setIcon(QIcon.fromTheme('zoom-original'))

        #client tab
        self._widget.tabWidget.currentChanged.connect(self._change_client_tab)

        #client tree update
        self._widget.client_tree_widget.itemClicked.connect(self._select_clinet_tree_item)
        #update signal
        self._client_list_update_signal.connect(self._update_client_info)

        context.add_widget(self._widget)

    def shutdown_plugin(self):
        pass

    def _update_client_info(self):
        # re-enable controls customizing fetched ROS graph
        self._update_client_tab()
        self._update_client_tree()

    def _update_client_tree(self):
        print '[update_client_tree]'
        self._widget.client_tree_widget.clear()
        clients = self.app_manager_app_info._client_info_list
        for client in clients.values():
            #Top service
            client_item = QTreeWidgetItem(self._widget.client_tree_widget)
            client_item.setText(0, client['name'])
            #set Top Level Font
            font = client_item.font(0)
            font.setPointSize(20)
            font.setBold(True)
            client_item.setFont(0, font)
        pass

    def _select_clinet_tree_item(self, item):
        for k in range(self._widget.tabWidget.count()):
            if self._widget.tabWidget.tabText(k) == item.text(0):
                self._widget.tabWidget.setCurrentIndex(k)
                break

    def _update_client_list(self):
        self._client_list_update_signal.emit()
        pass

    def _start_service(self, node_name, service_name):
        service = self.app_manager_app_info._client_info_list[node_name]['gateway_name'] + "/" + service_name
        info_text = ''

        if service_name == 'status':
            service_handle = rospy.ServiceProxy(service, Status)
            call_result = service_handle()

            info_text = "<html>"
            info_text += "<p>-------------------------------------------</p>"
            info_text += "<p><b>application_namespace: </b>" + call_result.application_namespace + "</p>"
            info_text += "<p><b>remote_controller: </b>" + call_result.remote_controller + "</p>"
            info_text += "<p><b>application_status: </b>" + call_result.application_status + "</p>"
            info_text += "</html>"
            self._client_list_update_signal.emit()

        elif service_name == 'platform_info':
            service_handle = rospy.ServiceProxy(service, GetPlatformInfo)
            call_result = service_handle()

            info_text = "<html>"
            info_text += "<p>-------------------------------------------</p>"
            info_text += "<p><b>rocon_uri: </b>" + call_result.platform_info.uri + "</p>"
            info_text += "<p><b>concert_version: </b>" + call_result.platform_info.version + "</p>"
            info_text += "</html>"
            self._client_list_update_signal.emit()

        elif service_name == 'invite':
            #sesrvice
            service_handle = rospy.ServiceProxy(service, Invite)
            #dialog
            dlg = QDialog(self._widget)
            dlg.setMinimumSize(400, 0)
            dlg.setMaximumSize(400, 0)
            dlg.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            #dialog layout
            ver_layout = QVBoxLayout(dlg)
            ver_layout.setContentsMargins(0, 0, 0, 0)

            dynamic_arg = []
            dynamic_arg.append(DynamicArgumentLayer(ver_layout, 'Remote Target Name', False, [('remote_target_name', 'string')]))
            dynamic_arg.append(DynamicArgumentLayer(ver_layout, 'Application Namespace', False, [('application_namespace', 'string')]))
            dynamic_arg.append(DynamicArgumentLayer(ver_layout, 'Cancel', False, [('cancel', 'bool')]))
            #button
            button_hor_sub_widget = QWidget()
            button_hor_layout = QHBoxLayout(button_hor_sub_widget)

            btn_call = QPushButton("Call")
            btn_cancel = QPushButton("cancel")

            btn_call.clicked.connect(lambda: dlg.done(0))
            btn_call.clicked.connect(lambda: self._call_invite_service(service, service_handle, dynamic_arg))

            btn_cancel.clicked.connect(lambda: dlg.done(0))
            #add button
            button_hor_layout.addWidget(btn_call)
            button_hor_layout.addWidget(btn_cancel)
            #add button layout
            ver_layout.addWidget(button_hor_sub_widget)

            dlg.setVisible(True)

        elif service_name == 'start_app':
            #service
            service_handle = rospy.ServiceProxy(service, StartApp)

            #dialog
            dlg = QDialog(self._widget)
            dlg.setMinimumSize(400, 0)
            dlg.setMaximumSize(400, 0)
            dlg.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            #dialog layout
            ver_layout = QVBoxLayout(dlg)
            ver_layout.setContentsMargins(0, 0, 0, 0)

            dynamic_arg = []
            dynamic_arg.append(DynamicArgumentLayer(ver_layout, 'Name', False, [('name', 'string')]))
            dynamic_arg.append(DynamicArgumentLayer(ver_layout, 'Remappings', True, [('remap to', 'string'), ('remap from', 'string')]))
            #button
            button_hor_sub_widget = QWidget()
            button_hor_layout = QHBoxLayout(button_hor_sub_widget)

            btn_call = QPushButton("Call")
            btn_cancel = QPushButton("cancel")

            btn_call.clicked.connect(lambda: dlg.done(0))
            btn_call.clicked.connect(lambda: self._call_start_app_service(service, service_handle, dynamic_arg))

            btn_cancel.clicked.connect(lambda: dlg.done(0))
            #add button
            button_hor_layout.addWidget(btn_call)
            button_hor_layout.addWidget(btn_cancel)
            #add button layout
            ver_layout.addWidget(button_hor_sub_widget)

            dlg.setVisible(True)

        elif service_name == 'stop_app':
            service_handle = rospy.ServiceProxy(service, StopApp)
            call_result = service_handle()

            info_text = "<html>"
            info_text += "<p>-------------------------------------------</p>"
            info_text += "<p><b>stopped: </b>" + str(call_result.stopped) + "</p>"
            info_text += "<p><b>error_code: </b>" + str(call_result.error_code) + "</p>"
            info_text += "<p><b>message: </b>" + call_result.message + "</p>"
            info_text += "</html>"

            self._update_client_tab()
        else:
            print 'has no service'
            return

        # display the result of calling service
        # get tab widget handle
        service_text_widget = None
        cur_tab_widget = self._widget.tabWidget.currentWidget()

        if cur_tab_widget == None:
            return

        object_name = 'services_text_widget'
        for k in cur_tab_widget.children():
            if k.objectName().count(object_name) >= 1:
                service_text_widget = k
                break
        if service_text_widget == None:
            return

        service_text_widget.clear()
        service_text_widget.appendHtml(info_text)

    def _call_invite_service(self, service, service_handle, dynamic_arg):
        remote_target_name = ""
        application_namespace = ""
        cancel = False

        for k in dynamic_arg:
            if k.name == 'Remote Target Name':
                item_widget = k._get_param_list()[0][0][1]
                remote_target_name = item_widget.toPlainText()

            elif k.name == 'Application Namespace':
                item_widget = k._get_param_list()[0][0][1]
                application_namespace = item_widget.toPlainText()

            elif k.name == 'Cancel':
                item_widget = k._get_param_list()[0][0][1]
                cancel = item_widget.itemData(item_widget.currentIndex())
        #calling service
        call_result = service_handle(remote_target_name, application_namespace, cancel)
        #status update
        self._client_list_update_signal.emit()
        # display the result of calling service

        info_text = "<html>"
        info_text += "<p>-------------------------------------------</p>"
        info_text += "<p><b>result: </b>" + str(call_result.result) + "</p>"
        info_text += "<p><b>error_code: </b>" + str(call_result.error_code) + "</p>"
        info_text += "<p><b>message: </b>" + call_result.message + "</p>"
        info_text += "</html>"

        # get tab widget handle
        service_text_widget = None
        cur_tab_widget = self._widget.tabWidget.currentWidget()
        if cur_tab_widget == None:
            return

        object_name = 'services_text_widget'
        for k in cur_tab_widget.children():
            if k.objectName().count(object_name) >= 1:
                service_text_widget = k
                break
        if service_text_widget == None:
            return

        service_text_widget.clear()
        service_text_widget.appendHtml(info_text)

        pass

    def _call_start_app_service(self, service, service_handle, dynamic_arg):
        name = ""
        remappings = []
        for k in dynamic_arg:
            if k.name == 'Name':
                name = k._get_param_list()[0][0][1].toPlainText()
            elif k.name == 'Remappings':
                for l in k._get_param_list():
                    remap_to = l[0][1].toPlainText()
                    remap_from = l[1][1].toPlainText()
                    remappings.append(Remapping(remap_to, remap_from))
        #calling service
        call_result = service_handle(name, remappings)
        #status update
        self._client_list_update_signal.emit()

        # display the result of calling service
        info_text = "<html>"
        info_text += "<p>-------------------------------------------</p>"
        info_text += "<p><b>started: </b>" + str(call_result.started) + "</p>"
        info_text += "<p><b>error_code: </b>" + str(call_result.error_code) + "</p>"
        info_text += "<p><b>message: </b>" + call_result.message + "</p>"
        info_text += "<p><b>app_namespace: </b>" + call_result.app_namespace + "</p>"
        info_text += "</html>"
        # get tab widget handle
        service_text_widget = None
        cur_tab_widget = self._widget.tabWidget.currentWidget()
        if cur_tab_widget == None:
            return
        object_name = 'services_text_widget'
        for k in cur_tab_widget.children():
            if k.objectName().count(object_name) >= 1:
                service_text_widget = k
                break
        if service_text_widget == None:
            return

        service_text_widget.clear()
        service_text_widget.appendHtml(info_text)

        pass

    def _update_client_tab(self):
        print '[_update_client_tab]'
        self.pre_selected_client_name = self.cur_selected_client_name
        self._widget.tabWidget.clear()

        for k in self.app_manager_app_info._client_info_list.values():
            main_widget = QWidget()

            ver_layout = QVBoxLayout(main_widget)

            ver_layout.setContentsMargins(9, 9, 9, 9)
            ver_layout.setSizeConstraint(ver_layout.SetDefaultConstraint)

            #button layout
            sub_widget = QWidget()
            sub_widget.setAccessibleName('sub_widget')
            btn_grid_layout = QGridLayout(sub_widget)

            btn_grid_layout.setContentsMargins(9, 9, 9, 9)

            btn_grid_layout.setColumnStretch(1, 0)
            btn_grid_layout.setRowStretch(2, 0)

            invite_btn = QPushButton("Invite")
            platform_info_btn = QPushButton("Get Platform Info")
            status_btn = QPushButton("Get Status")
            start_app_btn = QPushButton("Start App")
            stop_app_btn = QPushButton("Stop App")

            invite_btn.clicked.connect(lambda: self._start_service(self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex()), "invite"))
            platform_info_btn.clicked.connect(lambda: self._start_service(self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex()), "platform_info"))
            status_btn.clicked.connect(lambda: self._start_service(self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex()), "status"))
            start_app_btn.clicked.connect(lambda: self._start_service(self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex()), "start_app"))
            stop_app_btn.clicked.connect(lambda: self._start_service(self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex()), "stop_app"))

            btn_grid_layout.addWidget(invite_btn)
            btn_grid_layout.addWidget(platform_info_btn)
            btn_grid_layout.addWidget(status_btn)
            btn_grid_layout.addWidget(start_app_btn)
            btn_grid_layout.addWidget(stop_app_btn)
            ver_layout.addWidget(sub_widget)

            #client information layout
            context_label = QLabel()
            context_label.setText("Client information")
            ver_layout.addWidget(context_label)

            app_context_widget = QPlainTextEdit()
            app_context_widget.setObjectName(k["name"] + '_' + 'app_context_widget')
            app_context_widget.setAccessibleName('app_context_widget')
            app_context_widget.appendHtml(k["app_context"])
            app_context_widget.setReadOnly(True)

            cursor = app_context_widget.textCursor()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor, 0)
            app_context_widget.setTextCursor(cursor)
            ver_layout.addWidget(app_context_widget)

            #service information layout
            context_label = QLabel()
            context_label.setText("Service result")
            ver_layout.addWidget(context_label)

            services_text_widget = QPlainTextEdit()
            services_text_widget.setObjectName(k["name"] + '_' + 'services_text_widget')
            services_text_widget.setReadOnly(True)
            cursor = services_text_widget.textCursor()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor, 0)
            services_text_widget.setTextCursor(cursor)
            ver_layout.addWidget(services_text_widget)

            # new icon
            path = ""
            if k["is_new"] == True:
                path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../resources/images/new.gif")

            #add tab
            self._widget.tabWidget.addTab(main_widget, QIcon(path), k["name"])

        #set previous selected tab
        for k in range(self._widget.tabWidget.count()):
            tab_text = self._widget.tabWidget.tabText(k)
            if tab_text == self.pre_selected_client_name:
                self._widget.tabWidget.setCurrentIndex(k)

    def _change_client_tab(self, index):
        self.cur_selected_client_name = self._widget.tabWidget.tabText(self._widget.tabWidget.currentIndex())
        if self._widget.tabWidget.widget(index) != None:
            for k in  self._widget.tabWidget.widget(index).children():
                if k.objectName().count("services_text_widget"):
                    k.clear()
