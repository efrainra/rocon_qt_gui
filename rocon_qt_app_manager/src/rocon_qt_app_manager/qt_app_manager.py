#!/usr/bin/env python
#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_qt_gui/license/LICENSE
#
##############################################################################
# Imports
##############################################################################
#system
from __future__ import division
import os
import math
#pyqt
from python_qt_binding import loadUi
from python_qt_binding.QtCore import QFile, QIODevice, Qt, Signal, QAbstractListModel, pyqtSignal
from python_qt_binding.QtCore import pyqtSlot, SIGNAL,SLOT, QRectF , QTimer, QEvent, QUrl
from python_qt_binding.QtGui import QFileDialog, QGraphicsScene, QIcon, QImage, QPainter, QWidget, QLabel, QComboBox
from python_qt_binding.QtGui import QSizePolicy,QTextEdit, QCompleter, QBrush, QDialog, QColor, QPen, QPushButton
from python_qt_binding.QtGui import QTabWidget, QPlainTextEdit,QGridLayout, QVBoxLayout, QHBoxLayout, QMessageBox
from python_qt_binding.QtGui import QTreeWidgetItem, QPixmap, QGraphicsScene
from python_qt_binding.QtDeclarative import QDeclarativeView
from python_qt_binding.QtSvg import QSvgGenerator
#ros
import rospkg
from qt_app_manager_info import TeleopAppInfo
#rqt
from qt_gui.plugin import Plugin

##############################################################################
# Teleop App
##############################################################################


class QtAppManager(Plugin):
    _update_app_list_signal = Signal()

    def __init__(self, context):
        self._context = context
        super(QtAppManager, self).__init__(context)
        self.initialised = False
        self.setObjectName('Qt App Manager')

        self._widget = QWidget()
        rospack = rospkg.RosPack()
        ui_file = os.path.join(rospack.get_path('concert_teleop_app'), 'ui', 'teleop_app.ui')
        self._widget.setObjectName('TeleopAppUi')
        loadUi(ui_file, self._widget, {})
        if context.serial_number() > 1:
            self._widget.setWindowTitle(self._widget.windowTitle() + (' (%d)' % context.serial_number()))

        #list item click event
        self._widget.robot_list_tree_widget.itemClicked.connect(self._select_robot_list_tree_item)
        self._widget.robot_list_tree_widget.itemDoubleClicked.connect(self._dbclick_robot_list_item)

        #button event connection

        self._widget.capture_teleop_btn.pressed.connect(self._capture_teleop)
        self._widget.release_teleop_btn.pressed.connect(self._release_teleop)
        #signal event connection

        self._widget.destroyed.connect(self._exit)

        self._update_app_list_signal.connect(self._app_robot_list)
        self.connect(self, SIGNAL("capture"), self._show_capture_teleop_message)
        self.connect(self, SIGNAL("release"), self._show_release_teleop_message)
        self.connect(self, SIGNAL("error"), self._show_error_teleop_message)

        context.add_widget(self._widget)

        #init
        self.scene = QGraphicsScene(self._widget)
        self._widget.camera_view.setScene(self.scene)
        self.timer_image = QTimer(self._widget)
        self.timer_image.timeout.connect(self._display_image)
        self.timer_image.start(self.CAMERA_FPS)

        self.timer_contorl = QTimer(self._widget)
        self.timer_contorl.timeout.connect(self._on_move)

        self._widget.release_teleop_btn.setEnabled(False)
        self.teleop_app_info = TeleopAppInfo()
        self.teleop_app_info._reg_event_callback(self._refresh_robot_list)
        self.teleop_app_info._reg_capture_event_callback(self._capture_event_callback)
        self.teleop_app_info._reg_release_event_callback(self._release_event_callback)
        self.teleop_app_info._reg_error_event_callback(self._error_event_callback)

        self.robot_item_list = {}
        self.current_robot = None
        self.current_captured_robot = None

        #virtual joystick controll
        self.last_linear_command = 0.0
        self.last_angular_command = 0.0
        vj_path = os.path.join(rospack.get_path('concert_teleop_app'), 'ui', 'virtual_joystick.qml')
        self._widget.vj_view.setSource(QUrl(vj_path))
        self._widget.vj_view.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        rootObject = self._widget.vj_view.rootObject()
        rootObject.feedback.connect(self.joystick_feedback_event)
        rootObject.pressedHoverChanged.connect(self.pressed_hover_changed_event)

    def _exit(self):
        if self.current_captured_robot:
            self.teleop_app_info._release_teleop(self.current_captured_robot["rocon_uri"])

    def _update_app_list(self):
        self._widget.robot_list_tree_widget.clear()
        robot_list = self.teleop_app_info.robot_list

        for k in robot_list.values():
            robot_item = QTreeWidgetItem(self._widget.robot_list_tree_widget)
            robot_item.setText(0, k["name"].string)
            self.robot_item_list[robot_item] = k

    def _select_app_list_tree_item(self, Item):
        if not Item in self.robot_item_list.keys():
            print "HAS NO KEY"
        else:
            self.current_robot = self.robot_item_list[Item]
            if self.current_robot == self.current_captured_robot:
                self._widget.release_teleop_btn.setEnabled(True)
            else:
                self._widget.release_teleop_btn.setEnabled(False)

    def _refresh_app_list(self):
        self._update_app_list_signal.emit()
        pass
