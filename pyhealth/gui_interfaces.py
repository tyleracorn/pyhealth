#! /usr/bin/env python
"""
A Python 3 module for entering user settings through different gui interfaces
Rely's primarely on pyqt
"""
import warnings
import sys
import PyQt5.QtWidgets as pqtw

# from PyQt5.QtWidgets import *
# from PyQt5.QtGui import *
# from PyQt5.QtCore import pyqtSlot

class GUI_Login(pqtw.QWidget):
    """
    setup up a GUI interface using pyqt for entering the basic username, password information
    for a connection
    """

    def __init__(self, parent=None, site=' '):
        super(GUI_Login, self).__init__()
        self.site = site
        self.setUI()
        formlayout = True
        label_login = pqtw.QLabel("Login Name:")
        self.login = pqtw.QLineEdit()

        label_pw = pqtw.QLabel("Password:")
        self.password = pqtw.QLineEdit()
        self.password.setEchoMode(pqtw.QLineEdit.Password)
        fbox = pqtw.QFormLayout(self)

        BttnSubmit = pqtw.QPushButton("Submit")
        BttnCancel = pqtw.QPushButton("Cancel")

        BttnSubmit.clicked.connect(self.accept)
        BttnCancel.clicked.connect(self.exit)

        if formlayout:
            fbox.addRow(label_login, self.login)
            fbox.addRow(label_pw, self.password)
            fbox.addRow(BttnSubmit, BttnCancel)
            self.setLayout(fbox)
        else:
            # This is an alternative way to organize the layout
            # Saving this incase I need to expand this window to
            # a more complex setup
            self.grid = pqtw.QGridLayout()
            self.setLayout(self.grid)
            # (widget, fromRow, fromColumn, rowSpan, columnSpan)
            self.grid.addWidget(self.label_un, 1, 1, 1, 1)
            self.grid.addWidget(self.username, 2, 1, 1, 10)

            self.grid.addWidget(self.label_pw, 3, 1, 1, 1)
            self.grid.addWidget(self.password, 4, 1, 1, 10)

            self.grid.addWidget(BttnConnect, 10, 1, 1, 5)
            self.grid.addWidget(BttnCancel, 10, 6, 1, 5)
        self.setFocus()
        self.show()

    def setUI(self):
        # setGeometry(int x, int y, int w, int h)
        self.setGeometry(100, 100, 300, 100)
        self.setWindowTitle("Login GarminConnect")

    def accept(self):
        print(f"Login entered: {self.login.text()}")
        pqtw.QApplication.quit()

    def exit(self):
        # Exit the program, for now, no confirmation
        pqtw.QApplication.quit()


class GUI_Login_Ext(pqtw.QWidget):
    """
    setup up a GUI interface using pyqt for entering the basic username, password information
    for a connection. Extended to include username and login email (for the cases when they are different)
    """

    def __init__(self, parent=None, site=' '):
        super(GUI_Login_Ext, self).__init__()
        self.site = site
        self.setUI()

        label_login = pqtw.QLabel("Login Name:")
        self.login = pqtw.QLineEdit()

        label_un = pqtw.QLabel("User Name:")
        self.username = pqtw.QLineEdit()

        label_pw = pqtw.QLabel("Password:")
        self.password = pqtw.QLineEdit()
        self.password.setEchoMode(pqtw.QLineEdit.Password)
        fbox = pqtw.QFormLayout(self)

        BttnSubmit = pqtw.QPushButton("Submit")
        BttnCancel = pqtw.QPushButton("Cancel")

        BttnSubmit.clicked.connect(self.accept)
        BttnCancel.clicked.connect(self.exit)

        fbox.addRow(label_login, self.login)
        fbox.addRow(label_un, self.username)
        fbox.addRow(label_pw, self.password)
        fbox.addRow(BttnSubmit, BttnCancel)
        self.setLayout(fbox)

        self.show()

    def setUI(self):
        # setGeometry(int x, int y, int w, int h)
        self.setGeometry(100, 100, 300, 100)
        self.setWindowTitle("Login GarminConnect")

    def accept(self):
        print(f"login entered: {self.login.text()}")
        pqtw.QApplication.quit()

    def exit(self):
        # Exit the program, for now, no confirmation
        pqtw.QApplication.quit()


def get_login_credentials(site='Unknown', extended_info=False):
    """
    function used to call the GUI_Login class and return the username and password entered.
    This is a way to allow the login window to by called multiple times without crashing the kernel
    see:
    https://stackoverflow.com/questions/24041259/python-kernel-crashes-after-closing-an-pyqt4-gui-application
    https://stackoverflow.com/questions/29451285/loading-a-pyqt-application-multiple-times-cause-segmentation-fault

    Parameters:
        site (str): Name of site collecting login info for
        extended info (bool): Some sites require `username` that's different from the login credentials in order
            to access certain data. extended window collects the original username

    Returns:
        login (str), password (str), username (str)

        username = None if extended_info is False
    """
    # Use (`global app` or `app = None`) and instance() to ensure closing gui window doesn't
    # crash the kernal if running from jupyter notebook.

    APP = None
    username = None
    APP = pqtw.QApplication.instance()
    if APP is None:
        APP = pqtw.QApplication(sys.argv)

    if extended_info:
        logwindow = GUI_Login_Ext(sys.argv, site=site)
    else:
        logwindow = GUI_Login(sys.argv, site=site)
    APP.exit(APP.exec_())
    login = logwindow.login.text()
    password = logwindow.password.text()

    if login is None or login == '':
        warnings.warn('No login entered')
    if password is None or password == '':
        warnings.warn('No password entered')

    if extended_info:
        username = logwindow.username.text()
        if username is None or username == '':
            warnings.warn('No username entered')

    return login, password, username
