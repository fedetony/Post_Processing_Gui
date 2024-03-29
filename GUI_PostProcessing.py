# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GUI_PostProcessing.ui'
#
# Created by: PyQt5 UI code generator 5.15.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1201, 826)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.widget_2 = QtWidgets.QWidget(self.centralwidget)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.splitter = QtWidgets.QSplitter(self.widget_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.groupBox_Plots = QtWidgets.QGroupBox(self.splitter)
        self.groupBox_Plots.setMaximumSize(QtCore.QSize(500, 16777215))
        self.groupBox_Plots.setObjectName("groupBox_Plots")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.groupBox_Plots)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.treeView = QtWidgets.QTreeView(self.groupBox_Plots)
        self.treeView.setObjectName("treeView")
        self.horizontalLayout_4.addWidget(self.treeView)
        self.widget = QtWidgets.QWidget(self.splitter)
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_2 = QtWidgets.QGroupBox(self.widget)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.frame_5 = QtWidgets.QFrame(self.groupBox_2)
        self.frame_5.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_5.setObjectName("frame_5")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.frame_5)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_csv_File = QtWidgets.QLabel(self.frame_5)
        self.label_csv_File.setObjectName("label_csv_File")
        self.verticalLayout_2.addWidget(self.label_csv_File)
        self.label_results_folder_path = QtWidgets.QLabel(self.frame_5)
        self.label_results_folder_path.setObjectName("label_results_folder_path")
        self.verticalLayout_2.addWidget(self.label_results_folder_path)
        self.verticalLayout_4.addWidget(self.frame_5)
        self.frame_4 = QtWidgets.QFrame(self.groupBox_2)
        self.frame_4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.formLayout_3 = QtWidgets.QFormLayout(self.frame_4)
        self.formLayout_3.setObjectName("formLayout_3")
        self.label_Prefix = QtWidgets.QLabel(self.frame_4)
        self.label_Prefix.setObjectName("label_Prefix")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_Prefix)
        self.lineEdit_Prefix = QtWidgets.QLineEdit(self.frame_4)
        self.lineEdit_Prefix.setMaxLength(20)
        self.lineEdit_Prefix.setObjectName("lineEdit_Prefix")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.lineEdit_Prefix)
        self.verticalLayout_4.addWidget(self.frame_4)
        self.groupBox_Info = QtWidgets.QGroupBox(self.groupBox_2)
        self.groupBox_Info.setMinimumSize(QtCore.QSize(0, 200))
        self.groupBox_Info.setObjectName("groupBox_Info")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox_Info)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.textEdit = QtWidgets.QTextEdit(self.groupBox_Info)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout_3.addWidget(self.textEdit)
        self.verticalLayout_4.addWidget(self.groupBox_Info)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.horizontalLayout_3.addWidget(self.splitter)
        self.horizontalLayout.addWidget(self.widget_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1201, 25))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        self.menuaction = QtWidgets.QMenu(self.menubar)
        self.menuaction.setObjectName("menuaction")
        self.menuAbout = QtWidgets.QMenu(self.menubar)
        self.menuAbout.setObjectName("menuAbout")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen_CSV = QtWidgets.QAction(MainWindow)
        self.actionOpen_CSV.setObjectName("actionOpen_CSV")
        self.actionConfiguration = QtWidgets.QAction(MainWindow)
        self.actionConfiguration.setObjectName("actionConfiguration")
        self.actionSet_Results_Path = QtWidgets.QAction(MainWindow)
        self.actionSet_Results_Path.setObjectName("actionSet_Results_Path")
        self.actionSet_Results_Path_2 = QtWidgets.QAction(MainWindow)
        self.actionSet_Results_Path_2.setObjectName("actionSet_Results_Path_2")
        self.actionMake_Plots = QtWidgets.QAction(MainWindow)
        self.actionMake_Plots.setObjectName("actionMake_Plots")
        self.actionSet_Orientation = QtWidgets.QAction(MainWindow)
        self.actionSet_Orientation.setObjectName("actionSet_Orientation")
        self.actionSave_Plots_Structure = QtWidgets.QAction(MainWindow)
        self.actionSave_Plots_Structure.setObjectName("actionSave_Plots_Structure")
        self.actionLoad_Plots_Structure = QtWidgets.QAction(MainWindow)
        self.actionLoad_Plots_Structure.setObjectName("actionLoad_Plots_Structure")
        self.actionPlot_Preview_Structure = QtWidgets.QAction(MainWindow)
        self.actionPlot_Preview_Structure.setObjectName("actionPlot_Preview_Structure")
        self.actionPlot_Preview_Selected = QtWidgets.QAction(MainWindow)
        self.actionPlot_Preview_Selected.setObjectName("actionPlot_Preview_Selected")
        self.actionPlot_Structure_to_pdf = QtWidgets.QAction(MainWindow)
        self.actionPlot_Structure_to_pdf.setObjectName("actionPlot_Structure_to_pdf")
        self.actionAbout = QtWidgets.QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.actionAdditionals = QtWidgets.QAction(MainWindow)
        self.actionAdditionals.setObjectName("actionAdditionals")
        self.actionPlot_Structure_to_files = QtWidgets.QAction(MainWindow)
        self.actionPlot_Structure_to_files.setObjectName("actionPlot_Structure_to_files")
        self.menuFile.addAction(self.actionOpen_CSV)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_Plots_Structure)
        self.menuFile.addAction(self.actionLoad_Plots_Structure)
        self.menuFile.addSeparator()
        self.menuSettings.addAction(self.actionConfiguration)
        self.menuSettings.addSeparator()
        self.menuSettings.addAction(self.actionSet_Results_Path_2)
        self.menuSettings.addSeparator()
        self.menuSettings.addAction(self.actionAdditionals)
        self.menuaction.addAction(self.actionPlot_Preview_Selected)
        self.menuaction.addAction(self.actionPlot_Preview_Structure)
        self.menuaction.addSeparator()
        self.menuaction.addAction(self.actionPlot_Structure_to_pdf)
        self.menuaction.addSeparator()
        self.menuaction.addAction(self.actionPlot_Structure_to_files)
        self.menuAbout.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuaction.menuAction())
        self.menubar.addAction(self.menuAbout.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.groupBox_Plots.setTitle(_translate("MainWindow", "Plots Structure"))
        self.label_csv_File.setText(_translate("MainWindow", "TextLabel"))
        self.label_results_folder_path.setText(_translate("MainWindow", "TextLabel"))
        self.label_Prefix.setText(_translate("MainWindow", "Prefix"))
        self.groupBox_Info.setTitle(_translate("MainWindow", "Terminal view"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings"))
        self.menuaction.setTitle(_translate("MainWindow", "Action"))
        self.menuAbout.setTitle(_translate("MainWindow", "About"))
        self.actionOpen_CSV.setText(_translate("MainWindow", "Open CSV"))
        self.actionConfiguration.setText(_translate("MainWindow", "Configuration"))
        self.actionSet_Results_Path.setText(_translate("MainWindow", "Set Results Path"))
        self.actionSet_Results_Path_2.setText(_translate("MainWindow", "Set_Results_Path"))
        self.actionSet_Results_Path_2.setToolTip(_translate("MainWindow", "Set_Results_Path (Default: same csv file path)"))
        self.actionMake_Plots.setText(_translate("MainWindow", "Make Plots"))
        self.actionSet_Orientation.setText(_translate("MainWindow", "Set_Orientation"))
        self.actionSave_Plots_Structure.setText(_translate("MainWindow", "Save Plots Structure"))
        self.actionLoad_Plots_Structure.setText(_translate("MainWindow", "Load Plots Structure"))
        self.actionPlot_Preview_Structure.setText(_translate("MainWindow", "Plot Preview Structure"))
        self.actionPlot_Preview_Selected.setText(_translate("MainWindow", "Plot Preview Selected"))
        self.actionPlot_Structure_to_pdf.setText(_translate("MainWindow", "Plot Structure to pdf"))
        self.actionAbout.setText(_translate("MainWindow", "About"))
        self.actionAdditionals.setText(_translate("MainWindow", "Additionals"))
        self.actionPlot_Structure_to_files.setText(_translate("MainWindow", "Plot Structure to files"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
