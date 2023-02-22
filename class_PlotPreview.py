from locale import normalize
from ssl import HAS_TLSv1_2
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
import logging
import GUI_PlotPreview
import class_File_Dialogs
import class_TreeViewFunctions
from types import *
import numpy
import matplotlib
import mpl_toolkits.axes_grid1 as mpl_tk
import os
import pandas as pd
import re
from scipy.interpolate import interp1d
from scipy.special import comb
from scipy import signal
import math
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import sys
import linecache
from io import StringIO

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
formatter=logging.Formatter('[%(levelname)s] (%(threadName)-10s) %(message)s')
ahandler=logging.StreamHandler()
ahandler.setLevel(logging.INFO)
ahandler.setFormatter(formatter)
log.addHandler(ahandler)

class PlotPreviewDialog(QWidget,GUI_PlotPreview.Ui_Dialog_PlotPreview):
    plot_structure_changed= QtCore.pyqtSignal(list,str,str,str)
    plot_dialog_closing= QtCore.pyqtSignal(str)

    def Signal_Plot_Structure_Changed(self,track,val,valtype,subtype):
        #log.info('PP Emmiting: {} {} {} {}'.format(track,val,valtype,subtype))
        self.plot_structure_changed.emit(track,val,valtype,subtype)
    
    def __init__(self,Plot_ID,Plot_struct,csv_data,Plot_struct_mask, *args, **kwargs):                
        super(PlotPreviewDialog, self).__init__(*args, **kwargs)  
        self.__name__="Plot_Preview"
        self.aDialog=class_File_Dialogs.Dialogs()             
        self.Plot_struct=Plot_struct
        self.Plot_struct_mask=Plot_struct_mask
        self.csv_data_original=self.recursive_copy_dict(csv_data) 
        self.initial_csv_fields=self.get_fields_in_csv_data(csv_data)       
        self.csv_data=self.recursive_copy_dict(csv_data)
        self.csv_data_filtered=self.recursive_copy_dict(csv_data)             
        self.Plot_ID=Plot_ID #    
        self.update_Plot_dict()  #defines self.Plot_dict  
        self.data_dict=self.make_available_csv_data_dict()
        #self.Plot_dict.update({'Data':self.data_dict})
        self.Setup_Plot_Preview()                
        self.openPlot_PreviewDialog()   #comment this line to be called only when you want the dialog to pop up from main  
        self.Setup_info_in_objects()
        self.FigPreview=None
        self.sel_data={}
        self.use_graphicsView=True #False 
        self.set_FigureCanvas()
        matplotlib.pyplot.set_loglevel('info')
        self.debugmode=False
         
    
    def set_FigureCanvas(self):
        if self.use_graphicsView==False:
            layout = self.DPPui.verticalLayout_5
            #layout = QtWidgets.QVBoxLayout(self._main)
            asize=self.DPPui.graphicsView.size()
            thewidth=asize.width()
            theheight=asize.height()
            tsize=(int(thewidth/10),int(theheight/10))
            tsize=(2,2)
            log.info('Actual Size {}'.format(tsize))
            self.static_canvas = FigureCanvas(Figure(figsize=tsize))
            # Ideally one would use self.addToolBar here, but it is slightly
            # incompatible between PyQt6 and other bindings, so we just add the
            # toolbar as a plain widget instead.        
            self.static_canvas.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
            self.static_canvas.updateGeometry()
            layout.addWidget(self.static_canvas)        
            self.navi_toolbar = NavigationToolbar(self.static_canvas, self.DPPui.groupBox_Plot_Preview)
            layout.addWidget(self.navi_toolbar)
            self.DPPui.graphicsView.hide()                

    def ok_callback(self):
        print(self.Plot_ID," OK")
        self.quit()

    def cancel_callback(self):
        print(self.Plot_ID," Cancel")
        self.quit()

    def mycloseEvent(self, evnt):
        #super(PlotPreviewDialog, self).closeEvent(evnt)        
        print('entered close event ',self.Plot_ID)
    
    def get_local_dict_track(self,track_struct):
            triii=track_struct.copy()
            track=[]
            if track_struct[0]==self.Plot_ID:
                triii.pop(0)
                if triii[0]=='Plots':
                    triii.pop(0)
                    track=triii            
            return track
    
    def get_generaltrack_from_localtrack(self,localtrack):
            gentrack=[self.Plot_ID,'Plots']
            for iii in localtrack:
                gentrack.append(iii)  
            return gentrack


    def refresh_Treeview(self):
        self.tvf.Plot_struct=self.Plot_struct
        #self.tvf.Plot_struct=self.Plot_dict
        self.tvf.set_show_dict()
        #print('passed set_show_dict')
        self.tvf.refresh_Treeview(self.tvf.Show_dict,self.tvf.modelobj,self.tvf.treeviewobj)  
        self.modelobj=self.tvf.modelobj  
        self.treeviewobj=self.tvf.treeviewobj
    

    def get_my_dictionary_from_struct(self,Plot_ID,plot_struct):
        if self.is_list(plot_struct)==True:
            for adict in plot_struct:
                if adict['ID']==Plot_ID:
                    #print('get my dict Found ID',Plot_ID)
                    return adict
        elif self.is_dict(plot_struct)==True:
            #print('get my dict nochange is dict',Plot_ID)
            return plot_struct
        else:
            return {}

    def Setup_info_in_objects(self):
        #Fill item treeview
        #treeview handled by external class
        self.Reftrack=self.get_generaltrack_from_localtrack([])
        self.tvf=class_TreeViewFunctions.treeview_functions(self.DPPui.treeView,self.Plot_struct,self.Plot_struct_mask,self.Plot_ID,self.Reftrack)
        self.treeviewobj=self.tvf.treeviewobj        
        self.modelobj=self.tvf.modelobj
        self.tvf.data_change[list,str,str,str].connect(self.Signal_Plot_Structure_Changed)
        self.tvf.Expand_to_Depth(0) 
        self.icons_dict=self.get_icon_dict()
        self.bgcolor_dict=self.get_bg_color_dict()
        self.tvf.set_Icons(self.icons_dict)
        #self.tvf.set_BackgroundColors(self.bgcolor_dict)
        #Fill data Treeview
        self.Fill_Data_Treeview()
        

        #Groupboxes
        self.DPPui.groupBox_Plot_Data.setTitle('Data for '+ self.Plot_ID)
        self.DPPui.groupBox_Plot_Preview.setTitle('Preview for '+ self.Plot_ID)
    
    def Fill_Data_Treeview(self):
        self.data_dict=self.make_available_csv_data_dict()
        self.tvdataf=class_TreeViewFunctions.treeview_functions(self.DPPui.treeView_Data,self.data_dict,[],'',[])
        self.treeviewdataobj=self.tvdataf.treeviewobj        
        self.modeldataobj=self.tvdataf.treeviewobj.model() #self.tvdataf.modelobj
        self.tvdataf.treeviewobj.setAlternatingRowColors(True)
        
        #self.tvdataf.data_change[list,str,str].connect(self.Data_Changed)        
        self.tvdataf.Expand_to_Depth(-1)
        self.tvf.set_Icons(self.icons_dict)
        self.tvf.set_BackgroundColors(self.bgcolor_dict)
        self.add_data_style_to_treeview(self.treeviewdataobj.model())

        #self.treeviewdataobj.collapseAll()
    def add_data_style_to_treeview(self,modelobj):
        # Add style to tree rows
        item = modelobj.item(0)
        for i in range(item.rowCount()):
            for j in range(7):
                childitem = item.child(i, j)
                if childitem != None:
                    #childitem.setBackground(QColor(225, 225, 225))
                    #childitem.setSizeHint(QSize(30, 25))
                    childitem.setTextAlignment(QtCore.Qt.AlignTop)
                    #childitem.setFont(QFont("Times New Roman", weight=QFont.Bold))

    def Fill_Selected_Data_Treeview(self,selected_data_dict):
        #Fill Selected data Treeview
        self.tvselecteddataf=class_TreeViewFunctions.treeview_functions(self.DPPui.treeView_Data_2,selected_data_dict,[],'',[])
        self.treeviewselecteddataobj=self.tvselecteddataf.treeviewobj        
        self.modelselecteddataobj=self.tvselecteddataf.treeviewobj.model()#self.tvselecteddataf.modelobj                
        self.tvselecteddataf.Expand_to_Depth(-1)
        #refresh data Treeview   
        self.tvselecteddataf.treeviewobj.setAlternatingRowColors(True)
        self.Fill_Data_Treeview()   
        self.tvf.set_Icons(self.icons_dict)
        self.tvf.set_BackgroundColors(self.bgcolor_dict)
        #self.tvdataf.refresh_Treeview(self.tvdataf.Show_dict,self.tvdataf.modelobj,self.tvdataf.treeviewobj)  
        #self.tvdataf.Expand_to_Depth(-1)
        self.add_data_style_to_treeview(self.tvselecteddataf.treeviewobj.model())
        
    def Setup_Plot_Preview(self):
        #initial values here        
        self.Activate_test_button=False
        self.Is_Dialog_Open=False
        self.line_numberlistW=[]
        self.line_numberlistlW=[]
        self.line_numberlistE=[]
        self.globlsparam = {'__builtins__' : {'acos': math.acos, 'acosh': math.acosh, 'asin': math.asin, 
            'asinh': math.asinh, 'atan': math.atan, 'atan2': math.atan2, 'atanh': math.atanh,             
            'ceil': math.ceil, 'copysign': math.copysign, 'cos': math.cos, 'cosh': math.cosh, 
            'degrees': math.degrees, 'dist': math.dist, 'erf': math.erf, 'erfc': math.erfc, 
            'exp': math.exp, 'expm1': math.expm1, 'fabs': math.fabs, 'factorial': math.factorial, 
            'floor': math.floor, 'fmod': math.fmod, 'frexp': math.frexp, 'fsum': math.fsum, 
            'gamma': math.gamma, 'gcd': math.gcd, 'hypot': math.hypot, 'isclose': math.isclose, 
            'isfinite': math.isfinite, 'isinf': math.isinf, 'isnan': math.isnan, 'isqrt': math.isqrt, 
            #'lcm': math.lcm, 
            'ldexp': math.ldexp, 'lgamma': math.lgamma, 'log': math.log, 
            'log1p': math.log1p, 'log10': math.log10, 'log2': math.log2, 'modf': math.modf, 
            'pow': math.pow, 'radians': math.radians, 'remainder': math.remainder, 'sin': math.sin, 
            'sinh': math.sinh, 'sqrt': math.sqrt, 'tan': math.tan, 'tanh': math.tanh, 
            'trunc': math.trunc, 'prod': math.prod, 'perm': math.perm, 'comb': math.comb, 
            #'nextafter': math.nextafter,'ulp': math.ulp, 
            'pi': math.pi, 'e': math.e, 'tau': math.tau, 
            'inf': math.inf, 'nan': math.nan, 'NaN':numpy.nan, 'max':numpy.max,'min':numpy.min,
            'average':numpy.average,'phi':self.get_phi(),'range':self.listrange,'np':numpy,'abs':numpy.abs,
            #'dflist':self.make_df_var_list
            }} 
    
    def quit(self):                
        self.Is_Dialog_Open=False                
        self.plot_dialog_closing.emit(self.Plot_ID)
        self.Dialog_PrintPreview.close()
        self.close()
        #self.Dialog_PrintPreview.closeEvent()
    
    
        
            
           
    def openPlot_PreviewDialog(self):
        self.Dialog_PrintPreview = QtWidgets.QDialog()
        self.DPPui = GUI_PlotPreview.Ui_Dialog_PlotPreview()
        self.DPPui.setupUi(self.Dialog_PrintPreview)        
        #self.Dialog_PrintPreview.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint|QtCore.Qt.WindowCloseButtonHint)
        self.Dialog_PrintPreview.showMaximized()
        #Show dialog function in main
        #self.Dialog_PrintPreview.show()    
        self.Is_Dialog_Open=True    
        self.Setup_interface_objects()
        self.Connect_actions()        
        #add max option
        #self.Dialog_PrintPreview.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, True)
        #self.Dialog_PrintPreview.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, True)
        
        #self.closeEvent=self.Dialog_PrintPreview.closeEvent
        
        #self.setFixedSize(self.width(), self.height())
        # set the icon 
        self.app_path=self.aDialog.get_appPath()          
        path_to_file=self.app_path+os.sep+"img"+os.sep+"Data-Scatter-Plot-icon.png"
        file_exists = os.path.exists(path_to_file)
        #print(path_to_file+' '+str(file_exists))
        if file_exists==True:
            self.iconDialog = QtGui.QIcon(QtGui.QPixmap(path_to_file))
            self.Dialog_PrintPreview.setWindowIcon(self.iconDialog)
        
    
    def get_bg_color_dict(self):        
        #self.Reftrack
        mydict=self.tvf.get_tracked_value_in_struct([self.Plot_ID,'Plots'],self.Plot_struct)
        plotlist=self.get_dict_key_list(mydict)               
        bgdict={}
        for iii,plots in enumerate(plotlist):
            #use matplotlib color iterator
            colorstr=self.get_line_color(iii,{'linecolor':['']},'linecolor') 
            colortuple=matplotlib.colors.to_rgba(colorstr,alpha=0.5)
            color=QtGui.QColor(*colortuple)            
            '''
            #with random color generation
            mRGB=255*numpy.random.rand(3,1)
            mRGB=mRGB.tolist()              
            color=QtGui.QColor(int(mRGB[0][0]),int(mRGB[1][0]),int(mRGB[2][0]),0.5)
            '''
            bgdict.update({plots:color})
        #log.info('bgdict {}'.format(bgdict))    
        return bgdict
    
    def get_icon_dict(self):        
        #self.Reftrack
        colordict=self.get_bg_color_dict()        
        plotlist=self.get_dict_key_list(colordict)               
        icdict={}
        size=16
        for iii,plots in enumerate(plotlist):      
            try:   
                filename=self.app_path+os.sep+'img'+os.sep+plots+'.png'
                pixmap = QtGui.QPixmap(filename)
            except:
                pixmap = QtGui.QPixmap(self.app_path+os.sep+'img'+os.sep+'Data-Scatter-Plot-icon')                        
            #pixmap.fill(QtCore.Qt.transparent)
            #thesize=pixmap.size()
            #size=thesize.height()
            #pixmap.fill(colordict[plots])
            #size=float(size)            
            mask = pixmap.createMaskFromColor(QtGui.QColor(255, 255, 255), QtCore.Qt.MaskOutColor)
            #mask = pixmap.createMaskFromColor(QtCore.Qt.transparent, QtCore.Qt.MaskOutColor)

            p = QtGui.QPainter(pixmap)
            p.setPen(colordict[plots])
            p.drawPixmap(pixmap.rect(), mask, mask.rect())
            p.end()
            '''
            ficon=matplotlib.pyplot.plot(range(10),range(10))
            colorstr=self.get_line_color(iii,{'linecolor':['']},'linecolor') 
            rect=matplotlib.pyplot.Rectangle((0,0),size,size,color=colorstr,antialiased=False)
            matplotlib.pyplot.axis('off')
            matplotlib.pyplot.savefig(filename, transparent = True, bbox_inches = 'tight')
            '''
            
            #matplotlib.pyplot.savefig(filename, transparent = True, bbox_inches = 'tight')            
            '''
            qp = QtGui.QPainter(pixmap)
            qp.setRenderHints(qp.Antialiasing)
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, size, size)
            qp.setClipPath(path)      
            qp.fillPath(path,colordict[plots])      
            sourceRect = QtCore.QRect(0, 0, size, size)
            sourceRect.moveCenter(pixmap.rect().center())            
            qp.drawPixmap(pixmap.rect(), pixmap, sourceRect)
            qp.end()
            '''            
            icon=QtGui.QIcon(pixmap)            
            icdict.update({plots:icon})            
            #pixmap = QtGui.QPixmap(filename)            
            
            #pixmap.save(filename)
            
        #log.info('bgdict {}'.format(icdict))    
        return icdict

    def Send_Figure_icon(self,plotname):
        filename=self.app_path+os.sep+'img'+os.sep+plotname+'.png'
        matplotlib.pyplot.savefig(filename, transparent = False, dpi=10,bbox_inches='tight', pad_inches=0)    #no margins
        self.icons_dict=self.get_icon_dict()

    def Save_figure_to_file(self,fig,filepath=None,plotname=None,fileext='.png',figDPI='figure',aspect=None,margin=0.1,transparent_=False,facecolor_='auto', edgecolor_='auto',backend_=None):  
        if filepath==None:
            the_path=self.app_path+os.sep+'img'+os.sep
        else:
            the_path=filepath
        fne=plotname+fileext             
        filename=the_path+fne
        try: 
            if fileext:
                format_=fileext.strip('.')            
            else:
                format_=None
            #metadata=None
            fig.savefig(filename,format=format_, transparent = transparent_, dpi=figDPI,bbox_inches=aspect, pad_inches=margin,facecolor=facecolor_, edgecolor=edgecolor_,backend=backend_)    #no margins=0
            return filename
        except Exception as e:
            log.error("Can't save file {} : {}".format(filename,e))
            return None
        

    
    def Setup_interface_objects(self):
        self.Dialog_PrintPreview.setWindowTitle(self.Plot_ID)
        self.DPPui.groupBox_Plot_Data.setTitle('Plots')
        self.DPPui.checkBox_Show_Figure.setChecked(True)

        
    def Connect_actions(self):    
        #Connect buttons
        #log.info('Nothing to connect yet :)')
        self.DPPui.pushButton_Make_Preview.clicked.connect(self.generate_plot_preview)
        self.DPPui.buttonBox.accepted.connect(self.ok_callback)
        self.DPPui.buttonBox.rejected.connect(self.cancel_callback)                        
        '''
        if self.Activate_test_button==False:
            self.DPPui.pushButton_CCD_Refresh_Commands_File.clicked.connect(self.PB_CCD_Refresh_Commands_File)
        else:
            self.DPPui.pushButton_CCD_Refresh_Commands_File.clicked.connect(self.PB_debugtests)

        self.DPPui.tabWidget_CCD_configs.currentChanged.connect(self.TW_Tab_Change)
        # activated-When user changes it
        # currentIndexChanged -> when user or program changes it
        self.DPPui.comboBox_CCD_interface.activated.connect(self.ComboBox_Select_interface)
        
        #textEdited->only when user changes, not by the program
        #textChanged-> when user changes or the program changes text
        self.DPPui.lineEdit_CCD_testRead_text.textEdited.connect(self.Test_text_Changed) 
    
        '''
    def Groupbox_Data_Checked(self,value):
        print('Groupbox Changed---->',value)

    def get_fields_in_csv_data(self,df):
        field_list=[]
        try:
            #field_list=list(df.columns.values)[-1]
            field_list=list(df.columns.values) 
        except:
            pass
        return field_list

    def is_field_in_csv_data(self,df,field):
        field_list=self.get_fields_in_csv_data(df)
        if field in field_list:
            return True
        else:
            return False
    
    def make_available_csv_data_dict(self):
        csv_data_dict={}
        df=self.csv_data
        fields=self.get_fields_in_csv_data(df)
        for fff in fields:
            datainfo={}
            datainfo.update({'Data_Length':len(df[fff])})
            datainfo.update({'Data':df[fff].values})
            csv_data_dict.update({fff:datainfo})
        return csv_data_dict
    
    def recursive_copy_dict(self,indict):
        outdict={}
        if self.is_dict(indict):
            keylist=self.get_dict_key_list(indict)
            for iii in keylist:
                if self.is_dict(indict[iii])==True:
                    outdict.update({iii:self.recursive_copy_dict(indict[iii])})                
                else:
                    outdict.update({iii:indict[iii]})
        else:    
            outdict=indict
        return outdict

    def get_dict_key_list(self,dict):
        alist=[]
        for key in dict:
            alist.append(key)
        return alist
    
    def is_dict(self,var):
        if type(var)==dict:
            return True
        else:
            return False

    def is_list(self,var):
        if type(var)==list:
            return True
        else:
            return False
    
    def update_Plot_dict(self):
        try:
            self.Plot_dict=self.get_my_dictionary_from_struct(self.Plot_ID,self.Plot_struct)['Plots']
        except:
            logging.info("No key 'Plots' in structure")
            self.Plot_dict=self.get_my_dictionary_from_struct(self.Plot_ID,self.Plot_struct)

    def generate_plot_preview(self):
        self.DPPui.pushButton_Make_Preview.setEnabled(False)
        self.sel_data={}  
        self.update_Plot_dict()
        allplotinfo={}
        log.info('+++++++++++++++++++++++++++ Start Plot Generation +++++++++++++++++++++++++++')
        for aplot in self.Plot_dict:
            plotinfo={}
            self.eval_math_to_df(aplot)
            plotinfo=self.Mask_data(aplot,plotinfo)
            plotinfo=self.Mask_Additional_data(aplot,plotinfo)
            if plotinfo['isok']==True:                
                plotinfo=self.data_filter_preprocessing(aplot,plotinfo)
                plotinfo=self.Additonal_data_filter_preprocessing(aplot,plotinfo)
                plotinfo=self.Colormap_info(aplot,plotinfo)
                plotinfo=self.get_other_plot_info(aplot,plotinfo)
            #print('In Generate preview: zv=',plotinfo['zv'])
            allplotinfo.update({aplot:plotinfo})
            try:
                Adduvwinfo={'Add_axis_info':plotinfo['Add_axis_info'],'dfuvw':plotinfo['dfuvw'],'Meshgrids':{'uv':plotinfo['uv'],'vv':plotinfo['vv'],'wv':plotinfo['wv']},'Add_plot_Dim':plotinfo['Add_plot_Dim'],'uu':plotinfo['uu'],'uv':plotinfo['uv'],'uw':plotinfo['uw']}
                plinfo=self.get_plotted_info(plotinfo)                
                xyzinfo={'axis_info':plotinfo['axis_info'],'dfxyz':plotinfo['dfxyz'],'Meshgrids':{'xv':plotinfo['xv'],'yv':plotinfo['yv'],'zv':plotinfo['zv']},'plot_Dim':plotinfo['plot_Dim'],'ux':plotinfo['ux'],'uy':plotinfo['uy'],'uz':plotinfo['uz'],'Additional':Adduvwinfo,'Plotted_info':plinfo}                
            except Exception as e:
                log.error('Setting selected data to tree!')
                log.error(e)
                Adduvwinfo={}
                xyzinfo={}
            self.sel_data.update({plotinfo['me_plot']:xyzinfo})       
        try:    
            rplinfo=self.Make_Fig_Plots(allplotinfo)                                   
        except Exception as e:
            log.error('Making Figure Plots!')
            log.error(e)
            self.log_Exception()
        try:                
            for pli in rplinfo: 
                xyzinfo=self.sel_data[pli]
                plinfo=rplinfo[pli]            
                xyzinfo.update({'Plotted_info':plinfo})
                self.sel_data.update({pli:xyzinfo}) 
            self.Fill_Selected_Data_Treeview(self.sel_data)
        except Exception as e:
            log.error('Filling Selected data Used in Plot!')
            log.error(e)
            self.log_Exception()
        log.info('+++++++++++++++++++++++++++ End Plot Generation +++++++++++++++++++++++++++')
        self.DPPui.pushButton_Make_Preview.setEnabled(True)

    def Make_Fig_Plots(self,allplotinfo):                        
        fig_sizelist=self.tvf.get_tracked_value_in_struct([self.Plot_ID,'Fig_Size'],self.Plot_struct)
        fig_size=(fig_sizelist[0],fig_sizelist[1])              
        numplots=len(allplotinfo)
        plotlaylist,plotlayinfo,plotlaysizelist=self.get_layout_plot_lists(allplotinfo)
        RCsize=self.get_spec_size(plotlaysizelist,plotlaylist)
        Hlayall=RCsize[0]
        Vlayall=RCsize[1]
        #Hlayall, Vlayall=self.get_all_plots_layout(plotlaylist)
        #print('Layouts:',plotlaylist,'All:',Hlayall, Vlayall)
        layoutamountmat,layoutmat,layoutdict,layoutamountlist=self.get_layout_matrices(plotlaylist,plotlayinfo)        
        #print('öööööööööööööööööööööö\n',layoutamountmat,len(layoutmat),len(layoutdict),layoutamountlist,plotlaylist,len(plotlayinfo))
        self.sel_data.update({'Layouts':{'Lay_Amounts':layoutamountlist,'Lay_list':plotlaylist}})
        
        fig, axmat = matplotlib.pyplot.subplots(Hlayall, Vlayall, figsize = fig_size ,layout="tight")#,layout="constrained")                  
        #fig= matplotlib.pyplot.figure(figsize = fig_size ,layout="tight")#,layout="constrained")                  
        self.spec = fig.add_gridspec(ncols=Vlayall, nrows=Hlayall)     
        
        #print('axmat->',axmat)
        rplinfo={}
        iii=0        
        for amountlist,layinfolist in zip(layoutamountmat,layoutmat):            
            jjj=0
            for amount,layinfo in zip(amountlist,layinfolist):                
                if amount>0:
                    rplinfo=self.plot_in_Fig_ax(axmat,iii,jjj,layinfo,rplinfo,len(plotlayinfo))
                jjj=jjj+1
            iii=iii+1
        self.FigPreview=fig
        #log.info('######### Here rplinfo {}'.format(rplinfo))
        return rplinfo

    def plot_in_Fig_ax(self,ax,iii,jjj,layinfo,rplinfo,numax):        
        try:
            for pnum,Plotinfo in enumerate(layinfo):   #pnum from 0  
                Hlay=int(Plotinfo['layoutH'])
                Vlay=int(Plotinfo['layoutV'])
                RSlay=int(Plotinfo['layoutSizeR'])
                CSlay=int(Plotinfo['layoutSizeC'])
                sss=self.get_spec([RSlay,CSlay],[Hlay-1,Vlay-1],self.spec) 
                Plotinfo.update({'me_layout':sss}) 
                Plotinfo.update({'me_layout_pos':iii+jjj})                 
                log.info('Evaluating layout: {}'.format(sss))      
                if type(ax)==numpy.ndarray:                           
                    #print('inside plot_in_fig_ax:',ax.shape,iii,jjj)                                                    
                    if len(ax.shape)==2:
                        try:
                            if pnum>=1:
                                ax2 = ax[iii,jjj].twinx() #puts plot in same axis
                            else:
                                ax2 = ax[iii,jjj]
                        except:
                            ax2 = ax[iii,jjj]
                        plotok,nPlotinfo=self.do_plot_fig(ax2,Plotinfo)  
                        rplinfo.update({nPlotinfo['me_plot']:self.get_plotted_info(nPlotinfo)})                              
                    elif len(ax.shape)==1:
                        try:
                            if pnum>=1:
                                ax2 = ax[max(iii,jjj)].twinx()
                            else:
                                ax2 = ax[max(iii,jjj)]
                        except:
                            ax2 = ax[max(iii,jjj)]
                        plotok,nPlotinfo=self.do_plot_fig(ax2,Plotinfo) 
                        rplinfo.update({nPlotinfo['me_plot']:self.get_plotted_info(nPlotinfo)})                      
                    else:
                        plotok=False
                        rplinfo.update({Plotinfo['me_plot']:self.get_plotted_info(Plotinfo)})                     
                else:   
                    if type(ax)!=type(None): 
                        #log.info('Entered else evaluation')           
                        try:
                            if pnum>=1:                            
                                ax2 = ax.twinx() #puts plot in same axis
                            else:
                                ax2 = ax
                        except:
                            ax2 = ax
                        plotok,nPlotinfo=self.do_plot_fig(ax2,Plotinfo)  
                        rplinfo.update({nPlotinfo['me_plot']:self.get_plotted_info(nPlotinfo)})   
                    
                #show plots    
                if plotok==True:   
                    self.FigPreview=matplotlib.pyplot.gcf()                     
                    self.Show_in_Graphics_View(self.FigPreview)                
                    if self.DPPui.checkBox_Show_Figure.isChecked()==True:
                        matplotlib.pyplot.show()                           
                else:
                    self.Show_in_Graphics_View(None)
                    log.warning('Not showing {} type {}! Something not ok!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                
                #log.info('------------------- {} got plotinfo {}!'.format(Plotinfo['me_plot'],rplinfo[Plotinfo['me_plot']]))
                #log.info('------------------- {} got plotinfo {}!'.format(Plotinfo['me_plot'],rplinfo))
        except Exception as e:
            log.error('Plot in Figure axis: {}'.format(e))
        return rplinfo          

            
                    
    def Show_in_Graphics_View(self,afig):
        if self.use_graphicsView==True:
            if afig==None:
                scene = QGraphicsScene()
                scene.clear()
                log.info('Graphics View cleared')
            else:                
                scene = QGraphicsScene()
                scene.clear()
                #bbox_inches='tight', pad_inches=0
                #afig.tight_layout(pad=0)
                canvas=matplotlib.backends.backend_agg.FigureCanvasAgg(afig)                                
                canvas.draw()
                width, height = afig.figbbox.width, afig.figbbox.height                
                img = QtGui.QImage(canvas.buffer_rgba(), width, height, QtGui.QImage.Format_ARGB32)            
                
                pixmapfig=QtGui.QPixmap(img)
                Scenerect=self.DPPui.graphicsView.sceneRect()
                #pixmapfig = pixmapfig.scaled(Scenerect.width,Scenerect.height,  QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                asize=self.DPPui.graphicsView.size()
                thewidth=asize.width()
                #thewidth=Scenerect.width()
                #thewidth=int(thewidth)
                pixmapfig = pixmapfig.scaledToWidth(thewidth,QtCore.Qt.TransformationMode.SmoothTransformation)#  QtCore.Qt.TransformationMode.SmoothTransformation) #QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                scene.addPixmap(pixmapfig)
                self.DPPui.graphicsView.fitInView(Scenerect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            #view = QGraphicsView(scene)            
            self.DPPui.graphicsView.setScene(scene)                        
            self.DPPui.graphicsView.show()
        else:            
            if afig==None:
                self.static_canvas.clear() 
            else:
                #FigureCanvas.__init__(self.static_canvas, afig)
                self.static_canvas.figure=afig
                #afig.set_canvas(self.static_canvas)
                #afig.canvas.draw()
                #self.static_canvas=matplotlib.backends.backend_qtagg.FigureCanvasAgg(afig)                                
                self.static_canvas.draw()
                
                #self.static_canvas.figure.setF(afig) 
                #refresh size of figure
                #self.static_canvas.updateGeometry()
                #if self.DPPui.checkBox_Show_Figure.isChecked()==True:
                #    matplotlib.pyplot.show() 

    def is_same_list(self,list1,list2):
        if len(list1)!=len(list2):
            return False        
        for iii,jjj in zip(list1,list2):
            if iii!=jjj:
                return False
        return True

    def get_layout_plot_lists(self,allplotinfo):        
        plotlaylist=[]
        plotlayinfo=[]
        plotkeylist=self.tvf.get_dict_key_list(allplotinfo)
        is_11=False
        plotlaysizelist=[]
        for plot in plotkeylist:
            Hlay=allplotinfo[plot]['layoutH']
            Vlay=allplotinfo[plot]['layoutV']
            RSlay=allplotinfo[plot]['layoutSizeR']
            CSlay=allplotinfo[plot]['layoutSizeC']
            
            lay=[Hlay,Vlay]    
            if Hlay==1 and Vlay==1:
                is_11=True        
            plotlaylist.append(lay)
            plotlayinfo.append(allplotinfo[plot])
            plotlaysizelist.append([RSlay,CSlay])
        
        return plotlaylist,plotlayinfo,plotlaysizelist

    def limit_var(self,var,min,max):
        if var<min:
            return min
        if var>max:
            return max
        return var
    
    def get_spec_size(self,lsizelist,lpos1list):
        rmax=0
        cmax=0
        for lsize,lpos0 in zip(lsizelist,lpos1list):
            rrr=lsize[0]+lpos0[0]-1 #position list is 1 based
            if rrr>rmax:
                rmax=rrr
            ccc=lsize[1]+lpos0[1]-1
            if ccc>cmax:
                cmax=ccc
        log.info('Layout size {},{}'.format(rmax,cmax))
        return [rmax,cmax]

    def get_spec(self,lsize,lpos0,specobj):
        totr=specobj.nrows
        totc=specobj.ncols
        if totr>0 and totc>0:
            #limit sizes to matrix size
            lsize[0]=self.limit_var(lsize[0],1,totr)
            lsize[1]=self.limit_var(lsize[1],1,totc)
            lpos0[0]=self.limit_var(lpos0[0],0,totr-1)
            lpos0[1]=self.limit_var(lpos0[1],0,totc-1)
            return specobj[lpos0[0]:lpos0[0]+lsize[0],lpos0[1]:lpos0[1]+lsize[1]]        
        else: 
            return specobj[lpos0[0]+1,lpos0[1]+1] #returns 1 based

    def get_layout_matrices(self,plotlaylist,plotlayinfo):
        Hlayall, Vlayall=self.get_all_plots_layout(plotlaylist)
        #numplots=len(plotlaylist)        
        layoutamountmat=[]            
        layoutmat=[]    
        layoutdict={}   
        zerolist=[]
        nonelist=[]
        for jjj in range(0,Vlayall):  
            zerolist.append(0)
            nonelist.append(None)
        for iii in range(0,Hlayall):
            layoutamountmat.append(zerolist.copy())            
            layoutmat.append(nonelist.copy())

        kkk=0           
        for lay,info in zip(plotlaylist,plotlayinfo):
            [Hlay,Vlay]=lay
            for iii in range(0,Hlayall):
                for jjj in range(0,Vlayall):                
                    #layoutamountmat[iii][jjj]=0
                    if layoutmat[iii][jjj]==None:
                        layoutmat[iii][jjj]=[]                     
                    if Hlay==iii+1 and Vlay==jjj+1:
                        layoutamountmat[iii][jjj]=layoutamountmat[iii][jjj]+1
                        layoutmat[iii][jjj].append(info)
                        layoutdict.update({'iii':iii,'jjj':jjj,'Amount':layoutamountmat[iii][jjj],'Plotinfo':layoutmat[iii][jjj]})
            kkk=kkk+1
            
        layoutamountlist=[]            
        for iii,lay in enumerate(plotlaylist):
            layoutamountlist.append(0)
        for layold in plotlaylist:
            [Hlayold,Vlayold]=layold                
            for jjj,lay in enumerate(plotlaylist):
                [Hlay,Vlay]=lay
                if Hlay==Hlayold and Vlay==Vlayold:
                    layoutamountlist[jjj]=layoutamountlist[jjj]+1        
                
        return layoutamountmat,layoutmat,layoutdict,layoutamountlist

    def get_colormap_range(self,vect,Plotinfo):
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        if ppp['Colormap']['Colormap_Auto_Range']==True:
            cmrange=[min(vect),max(vect)] #set new range if auto range             
        else:
            cmrange=Plotinfo['Colormap_Range']
        cmvmin=cmrange[0]
        cmvmax=cmrange[1] 
        return cmvmin,cmvmax


    def do_a_spectrum_plot(self,ax,Plotinfo):        
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True    
        dfxyz=Plotinfo['dfxyz']    
            
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        colormap_dict=Plotinfo['colormap_dict']
        cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']
        
        spectrum_NFFT=Plotinfo['spectrum_NFFT']
        spectrum_Fs=Plotinfo['spectrum_Fs']
        spectrum_Fc=Plotinfo['spectrum_Fc']
        spectrum_detrend=Plotinfo['spectrum_detrend']
        spectrum_window=Plotinfo['spectrum_window']
        spectrum_noverlap=Plotinfo['spectrum_noverlap']
        spectrum_pad_to=Plotinfo['spectrum_pad_to']
        spectrum_sides=Plotinfo['spectrum_sides']
        spectrum_scale_by_freq=Plotinfo['spectrum_scale_by_freq']
        spectrum_mode=Plotinfo['spectrum_mode']
        spectrum_scale=Plotinfo['spectrum_scale']
        spectrum_scipy_parameters=Plotinfo['spectrum_scipy_parameters']
        spectrum_scipy_windowtype=Plotinfo['spectrum_scipy_windowtype']
        
        
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            xxx,yyy,zzz,_,_=self.get_vectors_separated(dfxyz)
            xy=self.get_var_axis_info_(1,axis_info,[xxx,yyy,zzz])
            ccc=self.get_var_axis_info_(2,axis_info,[xxx,yyy,zzz])             
            value=yaxis
            if self.is_list(xy)==False:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'])) 
            else:
                if len(xy)==0:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))   
                else:
                    doplot=True                                            
            #Set colormap 2D   
            if self.is_list(ccc)==False:   
                ccc=xy 
            cmvmin,cmvmax=self.get_colormap_range(ccc,Plotinfo)
            # warn
            if Plotinfo['Plot_Type']=='specgram' and spectrum_mode=='psd' and spectrum_scale_by_freq==True:
                log.warning('Scale by frequency is not taken in count when psd mode')   
            #set window  
            def spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,spectrum_NFFT):  
                try:            
                    NP=len(xy)
                    #log.info('NP from xy ={} valx ={}'.format(NP,valx))
                except:
                    if self.is_list(valx)==True:
                        NP=len(valx)
                    else:
                        NP=valx
                if NP<spectrum_NFFT:
                    NP=spectrum_NFFT
                #log.info('NP value {}'.format(NP))
                if spectrum_window=='none': 
                    thewindow=matplotlib.mlab.window_none(NP)
                elif spectrum_window=='hanning':      
                    thewindow=matplotlib.mlab.window_hanning(NP)
                elif spectrum_window=='blackman':      
                    thewindow=numpy.blackman(NP)
                elif spectrum_window=='hamming':      
                    thewindow=numpy.hamming(NP)
                elif spectrum_window=='scipy_signal': 
                    try:
                        if spectrum_scipy_windowtype in ['boxcar', 'triang', 'blackman', 'hamming', 'hann', 'bartlett', 'flattop', 'parzen', 'bohman', 'blackmanharris', 'nuttall', 'barthann', 'cosine', 'exponential,tukey', 'taylor', 'lanczos']:     
                            thewindow=signal.get_window(spectrum_scipy_windowtype,NP)
                        elif spectrum_scipy_windowtype in ['kaiser(beta)', 'kaiser_bessel_derived(beta)', 'gaussian(standarddeviation)', 'general_hamming(windowcoefficient)', 'dpss(normalizedhalf-bandwidth)', 'chebwin(attenuation)']:
                            splitted=spectrum_scipy_windowtype.split('(')
                            params=self.get_list_of_float_or_None(spectrum_scipy_parameters)
                            windowtuple=(splitted[0],params[0])
                            thewindow=signal.get_window(windowtuple,NP)
                        elif spectrum_scipy_windowtype in ['general_gaussian(powerandwidth)']:
                            splitted=spectrum_scipy_windowtype.split('(')
                            params=self.get_list_of_float_or_None(spectrum_scipy_parameters)
                            windowtuple=(splitted[0],params[0],params[1])
                            thewindow=signal.get_window(windowtuple,NP)
                        elif spectrum_scipy_windowtype in ['general_cosine(weightingcoefficients)']:
                            splitted=spectrum_scipy_windowtype.split('(')
                            params=self.get_list_of_float_or_None(spectrum_scipy_parameters)
                            windowtuple=(splitted[0],params.asarray())
                            thewindow=signal.get_window(windowtuple,NP)
                    except Exception as e:
                        thewindow=matplotlib.mlab.window_none(NP)
                        log.warning('Scipy {} Window Error: {}'.format(spectrum_scipy_windowtype,e))
                else:
                    thewindow=matplotlib.mlab.window_none(NP)
                if not numpy.iterable(thewindow): #none gives an int
                    thewindow = numpy.ones(NP)
                return thewindow
            
            if spectrum_pad_to<0:
                spectrum_pad_to=None
            #log.info('window : {}'.format(thewindow))        
            if doplot==True:      
                #log.info('xy({}) {} \n ccc({}) {}'.format(len(xy),xy,len(ccc),ccc))  
                #log.info('test {}'.format(spectrum_window_call(100))) 

                #   
                if Plotinfo['Plot_Type']=='specgram':     
                    spectrum_window_call=lambda valx: spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,spectrum_NFFT)      
                    if colormap_dict[value][1]==1: #colormap active                    
                        thecmap=colormap_dict[value][0]
                        log.info('{} {} with colormap'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'])) 
                        spectrum,freqs,ttt,im = ax.specgram(xy, NFFT=spectrum_NFFT, Fs=spectrum_Fs, Fc=spectrum_Fc, detrend=spectrum_detrend, window=spectrum_window_call, noverlap=spectrum_noverlap, cmap=thecmap, vmin=cmvmin, vmax=cmvmax, xextent=None, pad_to=spectrum_pad_to, sides=spectrum_sides, scale_by_freq=spectrum_scale_by_freq, mode=spectrum_mode, scale=spectrum_scale)
                        try:
                            #imlist=ax.get_images()
                            self.set_color_map_label(im,ax,thecmap,Plotinfo)  
                        except Exception as e:
                            log.error('Making colormap label: {}'.format(e))
                            pass
                    else:
                        log.info('{} {} without colormap'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'])) 
                        spectrum,freqs,ttt,im = ax.specgram(xy, NFFT=spectrum_NFFT, Fs=spectrum_Fs, Fc=spectrum_Fc, detrend=spectrum_detrend, window=spectrum_window_call, noverlap=spectrum_noverlap, pad_to=spectrum_pad_to, sides=spectrum_sides, scale_by_freq=spectrum_scale_by_freq, mode=spectrum_mode, scale=spectrum_scale)   #xextent=None 
                    plinfo.update({'x':xy})
                    plinfo.update({'y':ccc})  
                    plinfo.update({'z':None}) 
                    plinfo.update({'spectrum':spectrum})
                    plinfo.update({'freqs':freqs})
                    plinfo.update({'t':ttt})
                
                if Plotinfo['Plot_Type']=='psd':  
                    spectrum_window_call=lambda valx: spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,spectrum_NFFT)
                    Pxx,freqs,line = ax.psd(xy, NFFT=spectrum_NFFT, Fs=spectrum_Fs, Fc=spectrum_Fc, detrend=spectrum_detrend, window=spectrum_window_call, noverlap=spectrum_noverlap, pad_to=spectrum_pad_to, sides=spectrum_sides, scale_by_freq=spectrum_scale_by_freq, return_line=True)   #xextent=None 
                    plinfo.update({'x':xy})
                    plinfo.update({'y':None})  
                    plinfo.update({'z':None}) 
                    plinfo.update({'Pxx':Pxx})
                    plinfo.update({'freqs':freqs})
                
                if Plotinfo['Plot_Type']=='magnitude_spectrum':  
                    spectrum_window_call=lambda valx: spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,len(xy))
                    spectrum,freqs,line = ax.magnitude_spectrum(xy, Fs=spectrum_Fs, Fc=spectrum_Fc, window=spectrum_window_call, pad_to=spectrum_pad_to, sides=spectrum_sides, scale=spectrum_scale)  
                    plinfo.update({'x':xy})
                    plinfo.update({'y':None})  
                    plinfo.update({'z':None}) 
                    plinfo.update({'spectrum':spectrum})
                    plinfo.update({'freqs':freqs})
                
                if Plotinfo['Plot_Type']=='angle_spectrum':  
                    spectrum_window_call=lambda valx: spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,len(xy))
                    spectrum,freqs,line = ax.angle_spectrum(xy, Fs=spectrum_Fs, Fc=spectrum_Fc, window=spectrum_window_call, pad_to=spectrum_pad_to, sides=spectrum_sides)  
                    plinfo.update({'x':xy})
                    plinfo.update({'y':None})  
                    plinfo.update({'z':None}) 
                    plinfo.update({'spectrum':spectrum})
                    plinfo.update({'freqs':freqs})
                
                if Plotinfo['Plot_Type']=='phase_spectrum':  
                    spectrum_window_call=lambda valx: spectrum_window_func(xy,spectrum_window,spectrum_scipy_windowtype,spectrum_scipy_parameters,valx,len(xy))
                    spectrum,freqs,line = ax.phase_spectrum(xy, Fs=spectrum_Fs, Fc=spectrum_Fc, window=spectrum_window_call, pad_to=spectrum_pad_to, sides=spectrum_sides)  
                    plinfo.update({'x':xy})
                    plinfo.update({'y':None})  
                    plinfo.update({'z':None}) 
                    plinfo.update({'spectrum':spectrum})
                    plinfo.update({'freqs':freqs})
                    
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False
        return plotok,plinfo,ax,Plotinfo

    def do_a_scatter_plot(self,ax,Plotinfo):        
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True        
        xv=Plotinfo['xv']
        yv=Plotinfo['yv']
        zv=Plotinfo['zv']        
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        axis_value=Plotinfo['axis_value']
        colormap_dict=Plotinfo['colormap_dict']
        cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']
        markertype=Plotinfo['Plot_Marker_Type']            
        markersize=Plotinfo['Plot_Marker_Size']
        
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            ccc=[]
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True
                xy=xv
                z=yv
                ccc=zv #self.df_x[value]
                value=zaxis
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]  
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True
                    xy=xv
                    z=yv
                    ccc=z
                    value=yaxis #2D->yaxis                            
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True
                    xy=yv
                    z=zv
                    ccc=z
                    value=yaxis
                    
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True
                    xy=xv
                    z=zv
                    ccc=z
                    value=yaxis
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                
                #Set colormap 2D      
                if axis_value!=None and doplot==True:
                    ccc=self.set_ctevalue_into_MNlist(xy,axis_value)                        
                if len(ccc)==0:
                    ccc=self.set_ctevalue_into_MNlist(xy,cmrange[0])                                                
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]
            if doplot==True:                   
                #plotnonfinite differentiates NaN values in plot
                if colormap_dict[value][1]==1: #colormap active
                    #ax,axb,imb=self.get_ax_for_color_map_label(ax,Plotinfo) 
                    im = ax.scatter(xy, z, c=ccc, marker=markertype, s=markersize, cmap=colormap_dict[value][0],vmin=cmvmin,vmax=cmvmax,plotnonfinite=True)                                                                         
                    cmap=colormap_dict[value][0]
                    self.set_color_map_label(im,ax,cmap,Plotinfo)  
                else:
                    im = ax.scatter(xy, z, c=ccc, marker=markertype, s=markersize, plotnonfinite=True)     
                plinfo.update({'x':xy})
                plinfo.update({'y':z})  
                plinfo.update({'z':ccc}) 
                #log.info('&&&&&&&&& Here in scatter {} \n xy {}'.format(plinfo,xy))
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False
        return plotok,plinfo,ax,Plotinfo

    def log_Exception(self):  
        if self.debugmode==True:      
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)        
            line = linecache.getline(filename, lineno, f.f_globals)
            filename=self.aDialog.extract_filename(filename,True)
            log.error('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

    def do_a_bar_plot(self,ax,Plotinfo):        
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        colormap_dict=Plotinfo['colormap_dict']
        #cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']        
        Use_bar_colors=Plotinfo['bar_Use_colors']        
        bar_width=Plotinfo['bar_width']
        bar_Use_Lines_style=Plotinfo['bar_Use_Lines_style']
        bar_logy=Plotinfo['bar_logy']
        bar_align=Plotinfo['bar_align']
        Use_Err_bars=Plotinfo['Use_Err_bars']
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            doplot=False 
            ccc=[]             
            
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True
                xy=xxx
                z=yyy
                ccc=zzz 
                value=zaxis                             
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True
                    xy=xxx
                    z=yyy
                    ccc=zeros
                    value=yaxis                            
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True
                    xy=yyy
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis                      
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True
                    xy=xxx
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis
                elif self.is_same_list(axis_info,[1,0,0])==True:
                    doplot=True
                    xy=bbb
                    z=xxx
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,1,0])==True:
                    doplot=True
                    xy=bbb
                    z=yyy
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,0,1])==True:
                    doplot=True
                    xy=bbb
                    z=zzz
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        

            if doplot==True:        
                
                #log.info('cm dict {}'.format(colormap_dict))
                if colormap_dict[value][1]==1: #colormap active
                    log.info('Bar plot with Colormap')
                    acmap=colormap_dict[value][0]
                    colors=[]
                    for val in z:
                        colors.append(acmap(val))                         
                    line_width,line_colors=self.get_line_colors_RGBAlist(Plotinfo,xy)                                                                         
                    thecolors=colors                                                                      
                else:      
                    log.info('Bar plot with selected Colors')                  
                    # Selected colors when no colormap
                    thecolors=self.get_selected_list_moded(Use_bar_colors)
                    
                    line_width,line_colors=self.get_line_colors_RGBAlist(Plotinfo,xy)                                                        
                #Set bar line colors
                if bar_Use_Lines_style==True:                            
                    if len(line_width)>1: 
                        lwidth=numpy.array(line_width)                                          
                    else:
                        lwidth=float(line_width[0])
                if Plotinfo['Plot_Type'] in ['bar']:        
                    if bar_Use_Lines_style==True:   
                        im = ax.bar(xy,z,width=bar_width,bottom=ccc,align=bar_align,color=thecolors,log=bar_logy,edgecolor=line_colors,linewidth=lwidth)    
                    else:
                        im = ax.bar(xy,z,width=bar_width,bottom=ccc,align=bar_align,color=thecolors,log=bar_logy)    
                    plinfo.update({'x':xy})
                    plinfo.update({'y':z})  
                    if Use_Err_bars==True:
                        error_kw_dict=self.get_error_bar_dict(xy,z,Plotinfo=Plotinfo)
                        im = self.do_plot_Errorbar(xy,z,ax,error_kw_dict,Use_Err_bars)     
                        plinfo.update({'xerr':error_kw_dict['xerr']})
                        plinfo.update({'yerr':error_kw_dict['yerr']})                  
                if Plotinfo['Plot_Type'] in ['barh']:
                    Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                    if bar_Use_Lines_style==True:   
                        im = ax.barh(xy,z,height=bar_width,left=ccc,align=bar_align,color=thecolors,log=bar_logy,edgecolor=line_colors,linewidth=lwidth)    
                    else:
                        im = ax.barh(xy,z,height=bar_width,left=ccc,align=bar_align,color=thecolors,log=bar_logy) 
                    plinfo.update({'x':xy})
                    plinfo.update({'y':z})                     
                    if Use_Err_bars==True:
                        error_kw_dict=self.get_error_bar_dict(z,xy,Plotinfo=Plotinfo)
                        im = self.do_plot_Errorbar(z,xy,ax,error_kw_dict,Use_Err_bars)
                        plinfo.update({'xerr':error_kw_dict['xerr']})
                        plinfo.update({'yerr':error_kw_dict['yerr']})                      
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo    
    
    def get_annotations_of_Axis(self,plotinfo,axisname,xTicks):
        try: 
            namesdict={'x':1,'y':2,'z':3,'u':4,'v':5,'w':6}
            xannolabels=None                    
            x_annotate=False         
            xannotate_ticks=plotinfo['ticks_'+axisname+'annotate']  
            if xannotate_ticks not in ['','None']:              
                xannotations=self.get_datafield_of_variable(xannotate_ticks,'__empty__',True)     
                           
                if len(xannotations)>0: #and len(xTicks)==len(xannotations):         
                    xannotations,_,_ =self.get_error_dxyzsized(xannotations,'anno='+xannotate_ticks,plotinfo) 
                    #annodict={}
                    xannolabels=[]
                    for iii,an in enumerate(xannotations):
                        #annodict.update({iii:str(an)})
                        xannolabels.append(str(an))
                    #dfxanno=pd.DataFrame(annodict)  
                    #xannolabels=self.get_annotations_for_tick_values(namesdict[axisname],xTicks,dfxanno,xannotate_ticks,plotinfo) 
                    #log.info('{} =? {}'.format(len(xTicks),len(xannotations)))            
                    x_annotate=True
                else:
                    if len(xannotations)>0:
                        log.error('Annotation labels for axis {} have different size!'.format(axisname))
                    xannolabels=None                    
                    x_annotate=False
            return xannolabels, x_annotate
        except Exception as e:
            log.error('Getting annotation labels for axis {}:{}'.format(axisname,e))
        return xannolabels, x_annotate
    
    def get_likeeventplot_info_(self,dfxyz,dfuvw,axis_info,plinfo,Add_axis_info):
        xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
        uuu,vvv,www,bbb2,_=self.get_vectors_separated(dfuvw)             
        doplot=False 
        ccc=[] 
        vectors=[]
        vectornames=['x','y','z','u','v','w']
        usedaxis=[]
        y_sv=[] 
        x_sv=[]
        all_sv=[]
        for iii in range(0,6):
            jjj=numpy.fmod(iii, 3)+1 #count 1 to 3
            if iii<3:    
                _V1=self.get_var_axis_info_(jjj,axis_info,[xxx,yyy,zzz])                     
                if type(_V1)!=type(None) and self.is_all_NaN_values(_V1)==False:
                    vectors.append(_V1)
                    ccc.append(iii+1)                        
                    plinfo.update({vectornames[iii]:_V1})
                    usedaxis.append(vectornames[iii])   
                    if numpy.NaN in _V1:
                        log.warning('nan values found in vector {} Replacing with 0'.format(vectornames[iii]))
                        _V1=self.replace_in_moded(numpy.NaN,0,_V1)
                    if vectornames[iii]=='x':
                        x_sv=_V1 
                    else:                            
                        y_sv.append(_V1)
                    all_sv.append(_V1)
                        
            else:
                _V5=self.get_var_axis_info_(jjj,Add_axis_info,[uuu,vvv,www])         
                vn=self.get_var_axis_info_(jjj,Add_axis_info,['u','v','w'])
                if type(_V5)!=type(None) and self.is_all_NaN_values(_V5)==False:
                    vectors.append(_V5)
                    ccc.append(iii+1)
                    plinfo.update({vn:_V5})
                    usedaxis.append(vn)
                    if numpy.NaN in _V5:
                        log.warning('nan values found in vector {} Replacing with 0'.format(vn))
                        _V5=self.replace_in_moded(numpy.NaN,0,_V5)
                    y_sv.append(_V5)
                    all_sv.append(_V5)
        return doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,bbb,zeros,bbb2

    def do_a_Violin_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
             
        violin_positions_key=Plotinfo['violin_positions_key']
        violin_vert=Plotinfo['violin_vert']
        violin_widths=Plotinfo['violin_widths']
        violin_showmeans=Plotinfo['violin_showmeans']
        violin_showextrema=Plotinfo['violin_showextrema']
        violin_showmedians=Plotinfo['violin_showmedians']
        violin_quantiles=Plotinfo['violin_quantiles']
        violin_points=Plotinfo['violin_points']
        violin_bw_method=Plotinfo['violin_bw_method']
        violin_bw_method_KDE=Plotinfo['violin_bw_method_KDE']

        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            elif lenv<=1 and Plotinfo['Plot_Type']=='stackplot':
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                if Plotinfo['Plot_Type']=='violin':
                    legends=[]
                    for uaxis in usedaxis:
                        legends.append(labeldict[uaxis]['Label_Text'])
                    
                    #get quantiles                    
                    if self.is_list(violin_quantiles)==True: 
                        #log.info('Entered list')
                        violin_quantileslist=self.get_moded_property(usedaxis,violin_quantiles)
                        violin_quantileslist=self.getsized_property(usedaxis,violin_quantileslist)
                        log.info('Evaluating the following quantiles:{}'.format(violin_quantileslist))
                        v_quan=[]
                        for vq in violin_quantileslist:  
                            if vq not in [None,'','none','None']:
                                try:
                                    vq_df=self.eval_data_into_a_df(vq,logshow=True,use_filtered=True)
                                    v_quantiles=numpy.asarray(vq_df)
                                    if len(v_quantiles)!=len(x_sv):
                                        v_quantiles,_,_=self.get_error_dxyzsized(v_quantiles,vq,Plotinfo)
                                        ev_quan=numpy.asarray(v_quantiles)
                                    else:
                                        ev_quan=v_quantiles
                                    #normalize to [0,1]
                                    lv_quan=ev_quan.tolist()
                                    vnorm=self.list_map(lv_quan,0,1)
                                    ev_quan=numpy.asarray(vnorm)
                                except Exception as e:
                                    log.warning('Quantil {} was not evaluated found error: {}'.format(v_quantiles,e))
                                    ev_quan=[]
                            else:
                                ev_quan=[]
                            v_quan.append(ev_quan)
                        try:
                            v_quan=self.MNmat_toMNarray(v_quan)
                            if v_quan.size<=0:
                                v_quan=None
                            log.info('Found quantiles: {}'.format(v_quan))
                        except:
                            v_quan=None
                            log.info('No quantiles Found')
                    else:
                        v_quan=None
                        log.info('No quantiles Found')
                    #log.info('test got quantiles {}'.format(v_quan))
                    
                    #get positions
                    if violin_positions_key not in [None,'','none','None']:
                        try:
                            v_df=self.eval_data_into_a_df(violin_positions_key,logshow=True,use_filtered=True)
                            v_positions=numpy.asarray(v_df)
                            if len(v_positions)!=len(x_sv):
                                v_positions,_,_=self.get_error_dxyzsized(v_positions,violin_positions_key,Plotinfo)
                                v_pos=numpy.asarray(v_positions)
                            else:
                                v_pos=v_positions
                        except Exception as e:
                            log.warning('Variable {} was not evaluated found error: {}'.format(violin_positions_key,e))
                            v_pos=None
                    else:
                        v_pos=None
                    if violin_bw_method_KDE>0:                     
                        violin_bw_method=violin_bw_method_KDE
                    log.info('Using bw_method={}. Set bw_method_KDE>0 to use KDE.'.format(violin_bw_method))
                    plinfo.update({'quantiles':v_quan})
                    plinfo.update({'positions':v_pos})
                    dataset=self.MNmat_toMNarray(all_sv)
                    im = ax.violinplot(dataset, positions=v_pos, quantiles=v_quan, vert=violin_vert, widths=violin_widths, showmeans=violin_showmeans, showextrema=violin_showextrema, showmedians=violin_showmedians, points=violin_points, bw_method=violin_bw_method)
                    #set x label
                    #Plotinfo[usedaxis[0]+'label']['Label_Text']='Positions'
                    Plotinfo=self.update_axis_ticks_label(usedaxis[0],Plotinfo,label=Plotinfo[usedaxis[0]+'label'])
                    for lll,leg in enumerate(legends):
                        if lll==0:
                            atxt='{}'.format(leg)
                        else:
                            atxt='{}, {}'.format(atxt,leg)
                        #atxt=atxt.strip("'")
                    Plotinfo[usedaxis[1]+'label']['Label_Text']=atxt
                    Plotinfo=self.update_axis_ticks_label(usedaxis[1],Plotinfo,Plotinfo[usedaxis[1]+'label'])
                    if violin_vert==False:
                        Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                    plotok=True

                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo
    
    def do_a_Box_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']


        boxplot_positions=Plotinfo['boxplot_positions']
        boxplot_widths=Plotinfo['boxplot_widths']
        boxplot_notch=Plotinfo['boxplot_notch']
        boxplot_sym=Plotinfo['boxplot_sym']
        boxplot_orientation=Plotinfo['boxplot_orientation']
        boxplot_whis=Plotinfo['boxplot_whis']
        boxplot_bootstrap=Plotinfo['boxplot_bootstrap']
        boxplot_usermedians=Plotinfo['boxplot_usermedians']
        boxplot_patch_artist=Plotinfo['boxplot_patch_artist']
        boxplot_conf_intervals=Plotinfo['boxplot_conf_intervals']
        boxplot_meanline=Plotinfo['boxplot_meanline']
        boxplot_showmeans=Plotinfo['boxplot_showmeans']
        boxplot_showcaps=Plotinfo['boxplot_showcaps']
        boxplot_showbox=Plotinfo['boxplot_showbox']
        boxplot_showfliers=Plotinfo['boxplot_showfliers']
        boxplot_manage_ticks=Plotinfo['boxplot_manage_ticks']
        boxplot_autorange=Plotinfo['boxplot_autorange']
        boxplot_zorder=Plotinfo['boxplot_zorder']
        boxplot_boxprops_color=Plotinfo['boxplot_boxprops_color']
        boxplot_boxprops_linestyle=Plotinfo['boxplot_boxprops_linestyle']
        boxplot_boxprops_linewidth=Plotinfo['boxplot_boxprops_linewidth']
        boxplot_medianprops_color=Plotinfo['boxplot_medianprops_color']
        boxplot_medianprops_linestyle=Plotinfo['boxplot_medianprops_linestyle']
        boxplot_medianprops_linewidth=Plotinfo['boxplot_medianprops_linewidth']

        boxplot_flierprops_marker=Plotinfo['boxplot_flierprops_marker']
        boxplot_flierprops_markerfacecolor=Plotinfo['boxplot_flierprops_markerfacecolor']
        boxplot_flierprops_markersize=Plotinfo['boxplot_flierprops_markersize']
        boxplot_flierprops_linestyle=Plotinfo['boxplot_flierprops_linestyle']
        boxplot_flierprops_markeredgecolor=Plotinfo['boxplot_flierprops_markeredgecolor']
        boxplot_flierprops_linewidth=Plotinfo['boxplot_flierprops_linewidth']
        
        boxplot_meanprops_marker=Plotinfo['boxplot_meanprops_marker']
        boxplot_meanprops_markerfacecolor=Plotinfo['boxplot_meanprops_markerfacecolor']
        boxplot_meanprops_markersize=Plotinfo['boxplot_meanprops_markersize']
        boxplot_meanprops_linestyle=Plotinfo['boxplot_meanprops_linestyle']
        boxplot_meanprops_markeredgecolor=Plotinfo['boxplot_meanprops_markeredgecolor']
        boxplot_meanprops_linewidth=Plotinfo['boxplot_meanprops_linewidth']
        boxplot_meanprops_color=Plotinfo['boxplot_meanprops_color']

        boxplot_capprops_capwidths=Plotinfo['boxplot_capprops_capwidths']
        #boxplot_capprops_capsize=Plotinfo['boxplot_capprops_capsize']
        boxplot_capprops_color=Plotinfo['boxplot_capprops_color']
        boxplot_capprops_linestyle=Plotinfo['boxplot_capprops_linestyle']
        boxplot_capprops_linewidth=Plotinfo['boxplot_capprops_linewidth']
        
        
        boxplot_whiskerprops_color=Plotinfo['boxplot_whiskerprops_color']
        boxplot_whiskerprops_linestyle=Plotinfo['boxplot_whiskerprops_linestyle']
        boxplot_whiskerprops_linewidth=Plotinfo['boxplot_whiskerprops_linewidth']


        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            if boxplot_orientation=='vertical':
                boxplot_vert=True
            else:
                boxplot_vert=False

            min_whis=min(boxplot_whis)
            max_whis=max(boxplot_whis)
            if min_whis==max_whis and boxplot_autorange==False:
                b_whis=None
            else:
                b_whis=(min_whis,max_whis)

            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                                                                              
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                if Plotinfo['Plot_Type']=='boxplot':
                    legends=[]
                    for uaxis in usedaxis:
                        legends.append(labeldict[uaxis]['Label_Text'])
                    
                    vectx2=[] #double size 2 caps per box
                    for aaa in usedaxis:
                        vectx2.append(aaa) 
                        vectx2.append(aaa)
                    
                    #get positions and widths
                    b_pos=self.get_selected_list_moded(boxplot_positions)
                    if self.is_list(b_pos)==True: 
                        b_pos=self.getsized_property(usedaxis,b_pos)
                    else:
                        b_pos=None
                    b_wit=self.get_selected_list_moded(boxplot_widths)
                    if self.is_list(b_wit)==True: 
                        b_wit=self.getsized_property(usedaxis,b_wit)
                    else:
                        try:
                            if b_wit<=0:
                                b_wit=None
                        except:
                            b_wit=None
                    #get usermedians
                    u_medianslist=[]                    
                    for iii,_ in enumerate(usedaxis):
                        try:
                            val=float(boxplot_usermedians[iii])
                            u_medianslist.append(val)
                        except:
                            u_medianslist.append(None)
                    if self.is_all_None_values(u_medianslist)==True:
                        b_umedians=None
                    else:
                        b_umedians=u_medianslist
                    
                    #get conf_intervals
                    confint1=[]  
                    confint2=[]  
                    confint=[]               
                    for iii,_ in enumerate(usedaxis):
                        try:
                            jjj=2*iii
                            val1=float(boxplot_conf_intervals[jjj])
                            confint1.append(val1)
                            val2=float(boxplot_conf_intervals[jjj+1])
                            confint2.append(val2)
                            confint.append([val1,val2])
                        except:
                            confint1.append(None)
                            confint2.append(None)
                            confint.append([None,None])
                    if self.is_all_None_values(confint1)==True and self.is_all_None_values(confint2)==True:
                        b_conf_intervals=None
                    else:
                        b_conf_intervals=confint
                    '''
                    if boxplot_usermedians not in [None,'','none','None']:
                        try:
                            b_df=self.eval_data_into_a_df(boxplot_usermedians,logshow=True,use_filtered=True)
                            b_usermedians=numpy.asarray(b_df)
                            if len(b_usermedians)!=len(x_sv):
                                b_usermedians,_,_=self.get_error_dxyzsized(b_usermedians,boxplot_usermedians,Plotinfo)
                                b_umedians=numpy.asarray(b_usermedians)
                            else:
                                b_umedians=b_usermedians
                        except Exception as e:
                            log.warning('Boxplot usermedians variable {} was not evaluated found error: {}'.format(boxplot_usermedians,e))
                            b_umedians=None
                    else:
                        b_umedians=None
                    
                    
                    #get conf_intervals
                    for confinterval in boxplot_conf_intervals:
                        iii=0
                        if confinterval not in [None,'','none','None']:
                            try:
                                c_df=self.eval_data_into_a_df(confinterval,logshow=True,use_filtered=True)
                                b_confinterval=numpy.asarray(c_df)
                                if len(b_confinterval)!=len(x_sv):
                                    b_confinterval,_,_=self.get_error_dxyzsized(b_confinterval,confinterval,Plotinfo)                                    
                                if iii==0:
                                    b_c=[]
                                if self.is_list(b_c):
                                    b_c.append(numpy.asarray(b_confinterval))
                                    iii=iii+1
                            except Exception as e:
                                log.warning('Boxplot widths variable {} was not evaluated found error: {}'.format(boxplot_widths,e))
                                b_c=None
                        else:
                            b_c=None
                    if self.is_list(b_c) and boxplot_notch==True:
                        b_conf_intervals=self.MNmat_toMNarray(b_c) 
                    elif self.is_list(b_c) and boxplot_notch==False:
                        b_conf_intervals=self.MNmat_toMNarray(b_c)
                        log.warning('Boxplot notch must be True to draw conf intervals')
                    else: 
                        b_conf_intervals=None  
                    '''
                    plinfo.update({'conf_intervals':b_conf_intervals})
                    plinfo.update({'usermedians':b_umedians})
                    
                    #boxplot properties:
                    #------------------                    
                    bp_colors=[]
                    for iii,bp_c in enumerate(boxplot_boxprops_color):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_boxprops_color') 
                        bp_colors.append(thecolor)                                   
                    if len(bp_colors)>0: 
                        bp_colors=self.getsized_property(usedaxis,bp_colors)
                        boxplot_boxprops=None 
                    else:
                        boxplot_boxprops=None 
                    bp_linewidth=[]
                    for iii,bp_c in enumerate(boxplot_boxprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_boxprops_linewidth') 
                        bp_linewidth.append(thecolor)                                    
                    if len(bp_linewidth)>0: 
                        bp_linewidth=self.getsized_property(usedaxis,bp_linewidth) 
                    bp_linestyle=[]
                    for iii,bp_c in enumerate(boxplot_boxprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_boxprops_linestyle') 
                        bp_linestyle.append(thecolor)                                   
                    if len(bp_linestyle)>0: 
                        bp_linestyle=self.getsized_property(usedaxis,bp_linestyle)                        
                    #------------------    
                    mep_colors=[]
                    for iii,mep_c in enumerate(boxplot_medianprops_color):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_medianprops_color') 
                        mep_colors.append(thecolor)                                   
                    if len(mep_colors)>0: 
                        mep_colors=self.getsized_property(usedaxis,mep_colors)
                        boxplot_medianprops=None 
                    else:
                        boxplot_medianprops=None                     
                    mep_linewidth=[]
                    for iii,mep_c in enumerate(boxplot_medianprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_medianprops_linewidth') 
                        mep_linewidth.append(thecolor)                                    
                    if len(mep_linewidth)>0: 
                        mep_linewidth=self.getsized_property(usedaxis,mep_linewidth) 
                    mep_linestyle=[]
                    for iii,mep_c in enumerate(boxplot_medianprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_medianprops_linestyle') 
                        mep_linestyle.append(thecolor)                                   
                    if len(mep_linestyle)>0: 
                        mep_linestyle=self.getsized_property(usedaxis,mep_linestyle)
                    #------------------
                    whip_colors=[]
                    for iii,whip_c in enumerate(boxplot_whiskerprops_color):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_whiskerprops_color') 
                        whip_colors.append(thecolor)                                   
                    if len(whip_colors)>0: 
                        whip_colors=self.getsized_property(vectx2,whip_colors)
                        boxplot_whiskerprops=None 
                    else:
                        boxplot_whiskerprops=None
                    whip_linewidth=[]
                    for iii,whip_c in enumerate(boxplot_whiskerprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_whiskerprops_linewidth') 
                        whip_linewidth.append(thecolor)                                    
                    if len(whip_linewidth)>0: 
                        whip_linewidth=self.getsized_property(vectx2,whip_linewidth) 
                    whip_linestyle=[]
                    for iii,whip_c in enumerate(boxplot_whiskerprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_whiskerprops_linestyle') 
                        whip_linestyle.append(thecolor)                                   
                    if len(whip_linestyle)>0: 
                        whip_linestyle=self.getsized_property(vectx2,whip_linestyle)
                    #------------------
                    flip_mfcolors=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_markerfacecolor):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_flierprops_markerfacecolor') 
                        flip_mfcolors.append(thecolor)                                   
                    if len(flip_mfcolors)>0: 
                        flip_mfcolors=self.getsized_property(usedaxis,flip_mfcolors)
                        boxplot_flierprops=None 
                    else:
                        boxplot_flierprops=None
                    flip_mecolors=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_markeredgecolor):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_flierprops_markeredgecolor') 
                        flip_mecolors.append(thecolor)                                   
                    if len(flip_mecolors)>0: 
                        flip_mecolors=self.getsized_property(usedaxis,flip_mecolors)
                    flip_marker=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_marker):
                        thecolor=self.get_line_markertype(iii,Plotinfo,'boxplot_flierprops_marker') 
                        flip_marker.append(thecolor)                                    
                    if len(flip_marker)>0: 
                        flip_marker=self.getsized_property(usedaxis,flip_marker) 
                    flip_markersize=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_markersize):
                        thecolor=self.get_line_markersize(iii,Plotinfo,'boxplot_flierprops_markersize') 
                        flip_markersize.append(thecolor)                                    
                    if len(flip_markersize)>0: 
                        flip_markersize=self.getsized_property(usedaxis,flip_markersize)
                    flip_linestyle=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_flierprops_linestyle') 
                        flip_linestyle.append(thecolor)                                   
                    if len(flip_linestyle)>0: 
                        flip_linestyle=self.getsized_property(usedaxis,flip_linestyle)
                    flip_linewidth=[]
                    for iii,flip_c in enumerate(boxplot_flierprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_flierprops_linewidth') 
                        flip_linewidth.append(thecolor)                                    
                    if len(flip_linewidth)>0: 
                        flip_linewidth=self.getsized_property(usedaxis,flip_linewidth) 
                    #------------------
                    meanp_mfcolors=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_markerfacecolor):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_meanprops_markerfacecolor') 
                        meanp_mfcolors.append(thecolor)                                   
                    if len(meanp_mfcolors)>0: 
                        meanp_mfcolors=self.getsized_property(usedaxis,meanp_mfcolors)
                        boxplot_meanprops=None 
                    else:
                        boxplot_meanprops=None
                    meanp_mecolors=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_markeredgecolor):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_meanprops_markeredgecolor') 
                        meanp_mecolors.append(thecolor)                                   
                    if len(meanp_mecolors)>0: 
                        meanp_mecolors=self.getsized_property(usedaxis,meanp_mecolors)
                    meanp_colors=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_color):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_meanprops_color') 
                        meanp_colors.append(thecolor)                                   
                    if len(meanp_colors)>0: 
                        meanp_colors=self.getsized_property(usedaxis,meanp_colors)
                    meanp_marker=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_marker):
                        thecolor=self.get_line_markertype(iii,Plotinfo,'boxplot_meanprops_marker') 
                        meanp_marker.append(thecolor)                                    
                    if len(meanp_marker)>0: 
                        meanp_marker=self.getsized_property(usedaxis,meanp_marker) 
                    meanp_markersize=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_markersize):
                        thecolor=self.get_line_markersize(iii,Plotinfo,'boxplot_meanprops_markersize') 
                        meanp_markersize.append(thecolor)                                    
                    if len(meanp_markersize)>0: 
                        meanp_markersize=self.getsized_property(usedaxis,meanp_markersize)
                    meanp_linestyle=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_meanprops_linestyle') 
                        meanp_linestyle.append(thecolor)                                   
                    if len(meanp_linestyle)>0: 
                        meanp_linestyle=self.getsized_property(usedaxis,meanp_linestyle)
                    meanp_linewidth=[]
                    for iii,meanp_c in enumerate(boxplot_meanprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_meanprops_linewidth') 
                        meanp_linewidth.append(thecolor)                                    
                    if len(meanp_linewidth)>0: 
                        meanp_linewidth=self.getsized_property(usedaxis,meanp_linewidth) 
                    #------------------
                    capp_colors=[]
                    
                    
                    for iii,capp_c in enumerate(boxplot_capprops_color):
                        thecolor=self.get_a_color(iii,Plotinfo,'boxplot_capprops_color') 
                        capp_colors.append(thecolor)                                   
                    if len(capp_colors)>0: 
                        capp_colors=self.getsized_property(vectx2,capp_colors)
                        boxplot_capprops=None 
                    else:
                        boxplot_capprops=None
                    capp_linewidth=[]
                    for iii,capp_c in enumerate(boxplot_capprops_linewidth):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_capprops_linewidth') 
                        capp_linewidth.append(thecolor)                                    
                    if len(capp_linewidth)>0: 
                        capp_linewidth=self.getsized_property(vectx2,capp_linewidth) 
                    capp_linestyle=[]
                    for iii,capp_c in enumerate(boxplot_capprops_linestyle):
                        thecolor=self.get_line_style(iii,Plotinfo,'boxplot_capprops_linestyle') 
                        capp_linestyle.append(thecolor)                                   
                    if len(capp_linestyle)>0: 
                        capp_linestyle=self.getsized_property(vectx2,capp_linestyle)
                    '''
                    capp_capsize=[]
                    for iii,capp_c in enumerate(boxplot_capprops_capsize):
                        thecolor=self.get_line_width(iii,Plotinfo,'boxplot_capprops_capsize') 
                        capp_capsize.append(thecolor)                                    
                    if len(capp_capsize)>0: 
                        capp_capsize=self.getsized_property(vectx2,capp_capsize)
                    '''    
                     
                    capp_capwidths=self.get_selected_list_moded(boxplot_capprops_capwidths)
                    if self.is_list(capp_capwidths)==True:                                      
                        if len(capp_capwidths)>0: 
                            capp_capwidths=self.getsized_property(usedaxis,capp_capwidths)
                            capp_capwidths=numpy.asarray(capp_capwidths)
                    
                    if b_umedians!=None:
                        log.info('Found usermedians: {}'.format(b_umedians))
                    
                    if b_conf_intervals!=None:
                        log.info('Found conf_intervals: {}'.format(b_conf_intervals))
                        if boxplot_notch==False:
                            log.warning('Conf_intervals only show when notch is True!')
                    
                    #do the plot
                    boxplot_dict = ax.boxplot(all_sv, positions=b_pos, widths=b_wit, notch=boxplot_notch, sym=boxplot_sym, vert=boxplot_vert, patch_artist=boxplot_patch_artist, bootstrap=boxplot_bootstrap, meanline=boxplot_meanline, showmeans=boxplot_showmeans, showcaps=boxplot_showcaps, showbox=boxplot_showbox, showfliers=boxplot_showfliers, labels=legends, manage_ticks=boxplot_manage_ticks, autorange=boxplot_autorange, zorder=boxplot_zorder, whis=b_whis, usermedians=b_umedians, conf_intervals=b_conf_intervals, boxprops=boxplot_boxprops, flierprops=boxplot_flierprops, medianprops=boxplot_medianprops, meanprops=boxplot_meanprops, capprops=boxplot_capprops, whiskerprops=boxplot_whiskerprops, capwidths=capp_capwidths) # 
                    
                    for key in boxplot_dict:
                        vals=[]
                        for item in boxplot_dict[key]:
                            vals.append(item.get_ydata())
                        plinfo.update({key:vals})
                        #print(f'{key}: {[item.get_ydata() for item in boxplot_dict[key]]}\n')

                        # set indipendent property to each box
                        if len(bp_colors)>0 and key=='boxes':
                            for boxes,color in zip(boxplot_dict[key],bp_colors):
                                boxes.set(color=color) #, xdata=cap.get_xdata() + (-n,+n), linewidth=4.0)
                        if len(bp_linewidth)>0 and key=='boxes':
                            for boxes,linewidth in zip(boxplot_dict[key],bp_linewidth):
                                boxes.set(linewidth=linewidth)
                        if len(bp_linestyle)>0 and key=='boxes':                           
                            for boxes,linestyle in zip(boxplot_dict[key],bp_linestyle):
                                boxes.set(linestyle=linestyle)  
                        #----------------
                        if len(mep_colors)>0 and key=='medians':
                            for medians,color in zip(boxplot_dict[key],mep_colors):
                                medians.set(color=color) 
                        if len(mep_linewidth)>0 and key=='medians':
                            for medians,linewidth in zip(boxplot_dict[key],mep_linewidth):
                                medians.set(linewidth=linewidth)
                        if len(mep_linestyle)>0 and key=='medians':                           
                            for medians,linestyle in zip(boxplot_dict[key],mep_linestyle):
                                medians.set(linestyle=linestyle)   
                        #----------------
                        if len(whip_colors)>0 and key=='whiskers':
                            for whiskers,color in zip(boxplot_dict[key],whip_colors):
                                whiskers.set(color=color) 
                        if len(whip_linewidth)>0 and key=='whiskers':
                            for whiskers,linewidth in zip(boxplot_dict[key],whip_linewidth):
                                whiskers.set(linewidth=linewidth)
                        if len(whip_linestyle)>0 and key=='whiskers':                           
                            for whiskers,linestyle in zip(boxplot_dict[key],whip_linestyle):
                                whiskers.set(linestyle=linestyle)   
                        #----------------
                        if len(flip_mfcolors)>0 and key=='fliers':
                            for fliers,color in zip(boxplot_dict[key],flip_mfcolors):
                                fliers.set(markerfacecolor=color) 
                        if len(flip_mecolors)>0 and key=='fliers':
                            for fliers,color in zip(boxplot_dict[key],flip_mecolors):
                                fliers.set(markeredgecolor=color) 
                        if len(flip_marker)>0 and key=='fliers':
                            for fliers,marker in zip(boxplot_dict[key],flip_marker):
                                fliers.set(marker=marker)
                        if len(flip_markersize)>0 and key=='fliers':
                            for fliers,markersize in zip(boxplot_dict[key],flip_markersize):
                                fliers.set(markersize=markersize)
                        if len(flip_linestyle)>0 and key=='fliers':                           
                            for fliers,linestyle in zip(boxplot_dict[key],flip_linestyle):
                                fliers.set(linestyle=linestyle)
                        if len(flip_linewidth)>0 and key=='fliers':
                            for fliers,linewidth in zip(boxplot_dict[key],flip_linewidth):
                                fliers.set(linewidth=linewidth)
                        #----------------
                        if len(meanp_colors)>0 and key=='means':
                            for means,color in zip(boxplot_dict[key],meanp_colors):
                                means.set(color=color) 
                        if len(meanp_mfcolors)>0 and key=='means':
                            for means,color in zip(boxplot_dict[key],meanp_mfcolors):
                                means.set(markerfacecolor=color) 
                        if len(meanp_mecolors)>0 and key=='means':
                            for means,color in zip(boxplot_dict[key],meanp_mecolors):
                                means.set(markeredgecolor=color) 
                        if len(meanp_marker)>0 and key=='means':
                            for means,marker in zip(boxplot_dict[key],meanp_marker):
                                means.set(marker=marker)
                        if len(meanp_markersize)>0 and key=='means':
                            for means,markersize in zip(boxplot_dict[key],meanp_markersize):
                                means.set(markersize=markersize)
                        if len(meanp_linestyle)>0 and key=='means':                           
                            for means,linestyle in zip(boxplot_dict[key],meanp_linestyle):
                                means.set(linestyle=linestyle)
                        if len(meanp_linewidth)>0 and key=='means':
                            for means,linewidth in zip(boxplot_dict[key],meanp_linewidth):
                                means.set(linewidth=linewidth)
                        #----------------
                        if len(capp_colors)>0 and key=='caps':
                            for caps,color in zip(boxplot_dict[key],capp_colors):
                                caps.set(color=color) 
                        '''
                        if len(capp_capsize)>0 and key=='caps':
                            for caps,color in zip(boxplot_dict[key],capp_capsize):
                                caps.set(capzize=color) 
                        '''
                        if len(capp_linestyle)>0 and key=='caps':                           
                            for caps,linestyle in zip(boxplot_dict[key],capp_linestyle):
                                caps.set(linestyle=linestyle)
                        if len(capp_linewidth)>0 and key=='caps':
                            for caps,linewidth in zip(boxplot_dict[key],capp_linewidth):
                                caps.set(linewidth=linewidth)
                        
                    
                    #set x labels
                    #Plotinfo[usedaxis[0]+'label']['Label_Text']='Positions'
                    """
                    Plotinfo=self.update_axis_ticks_label(usedaxis[0],Plotinfo,label=Plotinfo[usedaxis[0]+'label'])
                    for lll,leg in enumerate(legends):
                        if lll==0:
                            atxt='{}'.format(leg)
                        else:
                            atxt='{}, {}'.format(atxt,leg)
                        #atxt=atxt.strip("'")
                    Plotinfo[usedaxis[1]+'label']['Label_Text']=atxt
                    Plotinfo=self.update_axis_ticks_label(usedaxis[1],Plotinfo,label=Plotinfo[usedaxis[1]+'label'])
                    """
                    if boxplot_vert==False:
                        Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                    plotok=True

                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo

    def get_list_of_float_or_None(self,alist):
        newlist=[]
        for iii,atxt in enumerate(alist):
            try:
                val=float(atxt)
                newlist.append(val)
            except:
                newlist.append(None)
        return newlist

    def do_a_Stack_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
             
        stack_baseline=Plotinfo['stack_baseline']
        stack_colors=Plotinfo['stack_colors']

        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            elif lenv<=1 and Plotinfo['Plot_Type']=='stackplot':
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                
                if Plotinfo['Plot_Type']=='stackplot':
                    ce=self.get_selected_list_moded(stack_colors)  
                    st_colors=[]
                    legends=[]
                    iii=0                                       
                    for jjj,uaxis in enumerate(usedaxis):
                        if uaxis != 'x':                           
                            legends.append(labeldict[uaxis]['Label_Text'])                              
                            thecolor=self.get_a_color(iii,Plotinfo,'stack_colors')   
                            #log.info('stacked plot--> {} {} {} {}'.format(uaxis,iii,st_colors,thecolor))                             
                            st_colors.append(thecolor)
                            iii=iii+1                                                      
                    x_sva=numpy.asarray(x_sv)
                    y_sva=self.MNmat_toMNarray(y_sv)                    
                    #log.info('stacked plot--> \ny_sva:{} '.format(y_sva))                    
                    #log.info('stacked plot-->\ncolors:{} \nlegends:{} '.format(st_colors,legends))
                    im = ax.stackplot(x_sva,y_sva,colors=st_colors, baseline=stack_baseline, labels=legends)
                    st_colors=self.get_selected_list_moded(st_colors) #if is only 1 color                   
                    legends=self.get_selected_list_moded(legends)    
                    #im = ax.stackplot(x_sv,y_sv,colors=st_colors, baseline=stack_baseline, labels=legends)   
                    plotok=True                                              
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo

    def do_a_Pie_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
                   
        pie_explode=Plotinfo['pie_explode']
        pie_colors=Plotinfo['pie_colors']
        pie_autopct=Plotinfo['pie_autopct']
        pie_pctdistance=Plotinfo['pie_pctdistance']
        pie_shadow=Plotinfo['pie_shadow']
        pie_labeldistance=Plotinfo['pie_labeldistance']
        pie_radius=Plotinfo['pie_radius']
        pie_startangle=Plotinfo['pie_startangle']
        pie_counterclock=Plotinfo['pie_counterclock']
        pie_textprops=Plotinfo['pie_textprops']
        pie_center=Plotinfo['pie_center']
        pie_frame=Plotinfo['pie_frame']
        pie_rotatelabels=Plotinfo['pie_rotatelabels']
        pie_normalize=Plotinfo['pie_normalize']
        pie_wedgeprops=Plotinfo['pie_wedgeprops']

        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            elif lenv<=1 and Plotinfo['Plot_Type']=='stackplot':
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                if Plotinfo['Plot_Type']=='pie':
                    p_exp=self.get_selected_list_moded(pie_explode)
                    p_explode=self.getsized_property(x_sv,p_exp)
                    pie_ccc=self.get_selected_list_moded(pie_colors)
                    p_c=self.getsized_property(x_sv,pie_ccc)
                    #to rgba
                    p_colors=[]
                    for iii,pppccc in enumerate(p_c):
                        thecolor=self.get_a_color(iii,Plotinfo,'pie_colors') 
                        p_colors.append(thecolor )#matplotlib.colors.to_rgba(thecolor)
                    p_colors=numpy.asarray(p_colors)
                    #pie_texts=self.get_selected_list_moded(pie_textprops)
                    x_sva=numpy.asarray(x_sv)
                    y_sva=self.MNmat_toMNarray(y_sv) 
                    ext_r=pie_radius
                    #int_r=ext_r-pie_wedgeprops["width"]
                    pwidth=float(pie_wedgeprops["width"])
                    p_wedgeprops=pie_wedgeprops.copy()
                    eachsize=(pwidth)/lenv
                    legends=[]
                    def pie_format_func(pct, theformat,vector=[]):
                            #theformat=str(theformat)
                        if len(vector)!=0:
                            try:
                                val=float(pct)/numpy.sum(vector)
                            except:
                                val=pct
                                pass
                        else:
                            val=pct
                        #print(val,theformat,theformat.format(val))
                        if theformat==None:
                            return val
                        return theformat.format(val)

                    for uuu,uaxis in enumerate(usedaxis):
                        legends.append(labeldict[uaxis]['Label_Text'])
                        p_wedgeprops.update({'width':eachsize})
                        p_labeldistance=pie_labeldistance
                        if uuu == 0:
                            avect=x_sva
                        else:
                            avect=y_sva[uuu-1]
                        xannolabels, x_annotate= self.get_annotations_of_Axis(Plotinfo,uaxis,avect)
                        if xannolabels!=None:
                            if len(xannolabels)==0:
                                xannolabels=None
                            
                        if pie_autopct in ['','none','None']:
                            p_autopct=''
                        else: 
                            if '%' in pie_autopct:
                                p_autopct=lambda pct: pie_format_func(pct,pie_autopct,avect)
                            else:
                                p_autopct=lambda pct: pie_format_func(pct,pie_autopct,[])
                        im = ax.pie(avect, explode=p_explode, labels=xannolabels ,colors=p_colors, autopct=p_autopct, pctdistance=pie_pctdistance, shadow=pie_shadow, labeldistance=p_labeldistance, startangle=pie_startangle, radius=ext_r, counterclock=pie_counterclock, wedgeprops=p_wedgeprops, textprops=pie_textprops, center=(pie_center[0],pie_center[1]), frame=pie_frame, rotatelabels=pie_rotatelabels, normalize=pie_normalize)
                        ext_r=ext_r-eachsize
                    plotok=True

                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo

    def do_a_Stairs_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
        
        stairs_baseline=Plotinfo['stairs_baseline']
        stairs_fill=Plotinfo['stairs_fill']
        stairs_orientation=Plotinfo['stairs_orientation']
        stairs_edges=Plotinfo['stairs_edges']
        stairs_Use_Lines_style=Plotinfo['stairs_Use_Lines_style']
        
        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            elif lenv<=1 and Plotinfo['Plot_Type']=='stackplot':
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                
                if Plotinfo['Plot_Type']=='stairs':
                    
                    #line_width,line_colors=self.get_line_colors_RGBAlist(Plotinfo,xy) 
                    lenedges=len(stairs_edges)
                    if lenedges==len(x_sv)+1:
                        log.info('Setting fixed value Edges')
                        the_edges=stairs_edges
                    elif lenedges==1:
                        log.info('Setting None Edges')                        
                        the_edges=None
                    elif lenedges==2:
                        log.info('Setting ranged Edges')
                        delta=(stairs_edges[1]-stairs_edges[0])/len(x_sv)
                        the_edges=self.numrange(stairs_edges[0],delta,len(x_sv)+1)
                    else:
                        log.info('Setting enumerated Edges')
                        the_edges=[0]
                        the_edges.extend(self.list_enumerate(x_sv,False))
                    
                    sta_baseline=self.get_selected_list_moded(stairs_baseline)
                    sta_baseline=self.getsized_property(usedaxis,sta_baseline)                    
                    s_colors=[]
                    s_linestyles=[]
                    s_linewidths=[]
                    for iii,ua in enumerate(usedaxis):
                        s_colors.append(self.get_a_color(iii,Plotinfo,'linecolor'))     
                        #print(s_colors)              
                        s_linestyles.append(self.get_line_style(iii,Plotinfo,'linestyle'))
                        s_linewidths.append(self.get_line_width(iii,Plotinfo,'linewidth'))
                    #s_linewidths=self.get_moded_property(usedaxis,event_linewidths)   
                    #s_linewidths=self.getsized_property(usedaxis,s_linewidths)                                
                    #s_linestyles=self.get_moded_property(usedaxis,event_linestyles)
                    #s_linestyles=self.getsized_property(usedaxis,s_linestyles)
                    legends=[]
                    for uaxis in usedaxis:
                        #log.info('label dict {} --> {}'.format(uaxis,labeldict[uaxis]['Label_Text']))
                        legends.append(labeldict[uaxis]['Label_Text'])

                    for iii,vect in enumerate(vectors):
                        values=numpy.asarray(vect)
                        if stairs_Use_Lines_style==True:
                            im = ax.stairs(values,edges=the_edges,orientation=stairs_orientation, baseline=sta_baseline[iii], fill=stairs_fill, label=legends[iii],linewidth=s_linewidths[iii], color=s_colors[iii], linestyle=s_linestyles[iii]) #facecolor=s_colors[iii],edgecolor=s_colors[iii]
                        else:
                            im = ax.stairs(values,edges=the_edges,orientation=stairs_orientation, baseline=sta_baseline[iii], fill=stairs_fill, label=legends[iii])
                    #set x label
                    #Plotinfo[usedaxis[0]+'label']['Label_Text']='Steps'
                    Plotinfo=self.update_axis_ticks_label(usedaxis[0],Plotinfo,label=Plotinfo[usedaxis[0]+'label'])
                    atxt='{}'.format(legends)
                    atxt=atxt.strip("[")
                    atxt=atxt.strip("]")
                    atxt=atxt.strip("'")
                    Plotinfo[usedaxis[1]+'label']['Label_Text']=atxt
                    Plotinfo=self.update_axis_ticks_label(usedaxis[1],Plotinfo,Plotinfo[usedaxis[1]+'label'])
                    if stairs_orientation=='horizontal':                            
                        Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                    plotok=True
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo

    def do_a_Event_plot(self,ax,Plotinfo):     
        # stack, stairs, event, violin, pie   
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']        
        plot_Dim=Plotinfo['plot_Dim']
        Add_plot_Dim=Plotinfo['Add_plot_Dim']
        plot_Dim=plot_Dim+Add_plot_Dim
        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
        
        event_orientation=Plotinfo['event_orientation']
        event_lineoffsets=Plotinfo['event_lineoffsets']
        event_linelengths=Plotinfo['event_linelengths']
        event_linewidths=Plotinfo['event_linewidths']
        event_colors=Plotinfo['event_colors']
        event_linestyles=Plotinfo['event_linestyles']

        log.info('{} starting {} {}D as {}{}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info,Add_axis_info))
        #reset the labels for this plot        
        ppp=self.Plot_dict[Plotinfo['me_plot']]
        xlab=ppp['Axis_X']['Axis_Label']
        ylab=ppp['Axis_Y']['Axis_Label']
        zlab=ppp['Axis_Z']['Axis_Label']
        ulab=ppp['Additional']['Axis_U']['Axis_Label']
        vlab=ppp['Additional']['Axis_V']['Axis_Label']
        wlab=ppp['Additional']['Axis_W']['Axis_Label']
        labeldict={'x':xlab,'y':ylab,'z':zlab,'u':ulab,'v':vlab,'w':wlab}

        doplot=False
        try:            
            #get all info
            doplot,xxx,yyy,zzz,uuu,vvv,www,ccc,vectors,vectornames,usedaxis,y_sv,x_sv,all_sv,plinfo,_,_,_=self.get_likeeventplot_info_(dfxyz,dfuvw,axis_info,plinfo,Add_axis_info)
                      
            lenv=len(ccc)    
            log.info('{} using the following axis to plot: {}'.format(Plotinfo['Plot_Type'],usedaxis))
            if plot_Dim==0 or lenv==0:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            elif lenv<=1 and Plotinfo['Plot_Type']=='stackplot':
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        
            else:
                doplot=True

            if doplot==True:                  
                plotok=False   
                    
                if Plotinfo['Plot_Type']=='eventplot':
                    #get all properties for plot
                    ce=self.get_selected_list_moded(event_colors)                                      
                    ce=self.replace_in_moded('none','',ce)
                    ce=self.replace_in_moded('None','',ce)
                    ce=self.replace_in_moded(None,'',ce)
                    ce=self.replace_in_moded('','black',ce) 
                    e_colors=self.getsized_property(ccc,ce)
                    for iii in ccc:
                        e_colors[iii-1]=self.get_a_color(iii-1,Plotinfo,'event_colors')                

                    e_lineoffsets=self.get_moded_property(ccc,event_lineoffsets) 
                    if self.is_list(e_lineoffsets)==True:
                        min_tlo=min(e_lineoffsets)
                        max_tlo=max(e_lineoffsets)
                    else:
                        min_tlo=min([e_lineoffsets,e_lineoffsets*lenv])
                        max_tlo=max([e_lineoffsets,e_lineoffsets*lenv])

                    e_linelengths=self.get_moded_property(ccc,event_linelengths)                          
                    e_linewidths=self.get_moded_property(ccc,event_linewidths)                                   
                    e_linestyles=self.get_moded_property(ccc,event_linestyles)  
                    
                    legends=[]
                    for uaxis in usedaxis:
                        #log.info('label dict {} --> {}'.format(uaxis,labeldict[uaxis]['Label_Text']))
                        legends.append(labeldict[uaxis]['Label_Text'])

                    im = ax.eventplot(vectors,orientation=event_orientation, lineoffsets=e_lineoffsets, linelengths=e_linelengths, linewidths=e_linewidths, colors=e_colors, linestyles=e_linestyles)
                    xannotate=e_lineoffsets
                    if '' not in legends:
                        #ax.set_label(legends)  
                        #ax.legend(legends)
                        xannotate=legends                  
                    Plotinfo=self.update_axis_ticks_label(usedaxis[0],Plotinfo,
                    showaxis=Plotinfo['ticks_'+usedaxis[0]+'show'],
                    set_t=Plotinfo['ticks_'+usedaxis[0]+'set'],
                    annotate_t=xannotate,
                    fontsize_t=Plotinfo['ticks_'+usedaxis[0]+'fontsize'],
                    rotation_t=Plotinfo['ticks_'+usedaxis[0]+'rotation'],
                    stepsize_t=Plotinfo['ticks_'+usedaxis[0]+'stepsize'],
                    min_t=min_tlo,        
                    max_t=max_tlo)

                    allmin=Plotinfo['ticks_'+usedaxis[0]+'min']
                    allmax=Plotinfo['ticks_'+usedaxis[0]+'max']
                    ylabeln=''
                    for anum,uaxis in enumerate(usedaxis):
                        if Plotinfo['ticks_'+uaxis+'min']<=allmin:
                            allmin=Plotinfo['ticks_'+uaxis+'min']
                        if Plotinfo['ticks_'+uaxis+'max']>=allmax:
                            allmax=Plotinfo['ticks_'+uaxis+'max']
                        if labeldict[uaxis]['Label_Text']!='':
                            if anum>0:
                                add=', '
                            else:
                                add=''
                            albl=str(labeldict[uaxis]['Label_Text'])
                            ylabeln=ylabeln+add+albl
                    log.info('ylabeln = {}'.format(ylabeln))
                    if lenv==1:
                        s_a=0
                    else:
                        s_a=1
                    #set label y
                    #Plotinfo[usedaxis[s_a]+'label']['Label_Text']=ylabeln

                    Plotinfo=self.update_axis_ticks_label('y',Plotinfo,
                    label=Plotinfo[usedaxis[s_a]+'label'],
                    showaxis=Plotinfo['ticks_'+usedaxis[s_a]+'show'],
                    set_t=Plotinfo['ticks_'+usedaxis[s_a]+'set'],
                    annotate_t=Plotinfo['ticks_'+usedaxis[s_a]+'annotate'],
                    fontsize_t=Plotinfo['ticks_'+usedaxis[s_a]+'fontsize'],
                    rotation_t=90+Plotinfo['ticks_'+usedaxis[s_a]+'rotation'],
                    stepsize_t=Plotinfo['ticks_'+usedaxis[s_a]+'stepsize'],
                    min_t=allmin,max_t=allmax)
                    #set x label
                    Plotinfo[usedaxis[0]+'label']['Label_Text']='Events'
                    Plotinfo=self.update_axis_ticks_label(usedaxis[0],Plotinfo,label=Plotinfo[usedaxis[0]+'label'])

                    if event_orientation=='horizontal':                            
                        Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                    
                    plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo  

    def list_enumerate(self,alist,iszerobased=True):
        theenum=[]
        for iii in enumerate(alist):  
            if iszerobased==True:
                theenum.append(iii)
            else:
                theenum.append(iii+1)
        return theenum
    
    def list_map(self,alist,rangemin,rangemax,frommin=None,frommax=None):
        normlist=[]
        if self.is_list(alist)==True:
            normarr=numpy.asfarray(alist)
            nmin=numpy.min(normarr)
            nmax=numpy.max(normarr)
            #log.info('before map -> {} {} {}'.format(normarr,nmin,nmax))
            if frommin!=None:
                nmin=frommin
            if frommax!=None:
                nmax=frommax
            if (nmax-nmin)==0:
                nmax=1
                nmin=0
            #define mapping function
            map_function = lambda x: (x-nmin)/(nmax-nmin)*(rangemax-rangemin)+rangemin
            normarr=map_function(normarr)
            #log.info('Mapped -> {}'.format(normarr))
            normlist=normarr.tolist()  
                
        return normlist


    
    def MNmat_toMNarray(self,MNmat):
        nr,nc=self.get_size_array(MNmat)
        sizes=self.get_vector_of_size_array(MNmat)   
        if nr==1 or nc==1:            
            flatlist=MNmat[0]#numpy.asarray(MNmat).flatten().tolist()
            varr=numpy.asarray(flatlist)     
        if self.is_list(sizes)==True:
            if self.is_the_same_value_in_vector(sizes)==True:
                arrlist=[]
                for iii,row in enumerate(MNmat):
                    arrlist.append(numpy.array(row))
                arrmat=numpy.array(arrlist)
                #varr=numpy.concatenate(arrmat)
                varr=arrmat
            else:
                return None
        else:
            return None                
        #log.info('{}x{} -> {}'.format(nr,nc,varr))
        return varr


    def update_axis_ticks_label(self,ua,plotinfo,label=None,showaxis=None,set_t=None,annotate_t=None,fontsize_t=None,rotation_t=None,stepsize_t=None,min_t=None,max_t=None):
        #Labels
        if label:
            plotinfo.update({ua+'label':label}) # this is a dictionary! 
        #Ticks
        if showaxis:           
            plotinfo.update({'ticks_'+ua+'show':showaxis})
        if set_t:
            plotinfo.update({'ticks_'+ua+'set':set_t})    
        if annotate_t:
            plotinfo.update({'ticks_'+ua+'annotate':annotate_t})        
        if fontsize_t:    
            plotinfo.update({'ticks_'+ua+'fontsize':fontsize_t})
        if rotation_t:
            plotinfo.update({'ticks_'+ua+'rotation':rotation_t})
        if stepsize_t:
            plotinfo.update({'ticks_'+ua+'stepsize':stepsize_t})
        if min_t:
            plotinfo.update({'ticks_'+ua+'min':min_t})        
        if max_t:
            plotinfo.update({'ticks_'+ua+'max':max_t})
        return plotinfo


    def get_moded_property(self,ccc,aprop):
        loe=self.get_selected_list_moded(aprop) 
        if self.is_list(loe)==True:         
            aprop=self.getsized_property(ccc,loe)
        else:
            aprop=loe
        return aprop

    def replace_in_moded(self,tofind,toreplace,modedlist):
        if self.is_list(modedlist)==True:
            for iii,mmm in enumerate(modedlist):
                if mmm==tofind:
                    modedlist[iii]=toreplace             
        else:
            if modedlist==tofind:
                modedlist=toreplace  
        return modedlist      

    def do_a_Stem_plot(self,ax,Plotinfo):        
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        #colormap_dict=Plotinfo['colormap_dict']
        #cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']        
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis'] 
        Stem_bottom=Plotinfo['Stem_bottom']
        Stem_orientation=Plotinfo['Stem_orientation']
        Stem_Use_Lines_style=Plotinfo['Stem_Use_Lines_style']
        Stem_linefmt=Plotinfo['Stem_linefmt']
        Stem_markerfmt=Plotinfo['Stem_markerfmt']
        Stem_basefmt=Plotinfo['Stem_basefmt']       
        
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            doplot=False 
            ccc=[]             
            
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True
                xy=xxx
                z=yyy
                ccc=zzz 
                value=zaxis                             
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True
                    xy=xxx
                    z=yyy
                    ccc=zeros
                    value=yaxis                            
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True
                    xy=yyy
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis                      
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True
                    xy=xxx
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis
                elif self.is_same_list(axis_info,[1,0,0])==True:
                    doplot=True
                    xy=bbb
                    z=xxx
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,1,0])==True:
                    doplot=True
                    xy=bbb
                    z=yyy
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,0,1])==True:
                    doplot=True
                    xy=bbb
                    z=zzz
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                        

            if doplot==True:        
                if Stem_orientation=='vertical':        
                    if Stem_Use_Lines_style==True:   
                        markerline, stemlines, baseline = ax.stem(xy, z, basefmt=Stem_basefmt, bottom=Stem_bottom, orientation=Stem_orientation, use_line_collection=True)
                        self.set_Stem_lineformat_lines(Plotinfo,xy, markerline, stemlines)
                    else:
                        im = ax.stem(xy, z, linefmt=Stem_linefmt, markerfmt=Stem_markerfmt, bottom=Stem_bottom, basefmt=Stem_basefmt, orientation=Stem_orientation, use_line_collection=True)
                        
                    plinfo.update({'x':xy})
                    plinfo.update({'y':z})                                      
                elif Stem_orientation=='horizontal':
                    Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo,only_labels=False)
                    Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo,only_labels=True) #change labels back again
                    if Stem_Use_Lines_style==True:   
                        markerline, stemlines, baseline = ax.stem(z, xy, basefmt=Stem_basefmt, bottom=Stem_bottom, orientation=Stem_orientation, use_line_collection=True)                        
                        self.set_Stem_lineformat_lines(Plotinfo,xy, markerline, stemlines)
                    else:
                        im = ax.stem(z, xy, linefmt=Stem_linefmt, markerfmt=Stem_markerfmt, bottom=Stem_bottom, basefmt=Stem_basefmt, orientation=Stem_orientation, use_line_collection=True)
                    plinfo.update({'x':z})
                    plinfo.update({'y':xy})                     
                    
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo  

    def do_a_image_plot(self,ax,Plotinfo):
        plinfo=self.get_plotted_info(Plotinfo) 
        log.info('{} starting {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
        # images
        try:
            showaxis=Plotinfo['Show_Axis']
            imaspect=Plotinfo['BG_Aspect']
            imagepathfile=Plotinfo['BG_Path_File']
            if imagepathfile!=None:
                img = matplotlib.pyplot.imread(imagepathfile)                        
                if showaxis==False:
                    ax.axis('off')
                else:
                    ax.axis('on')
                bgia=Plotinfo['BG_in_alpha'] 
                im = ax.imshow(img, aspect=imaspect,alpha=bgia)                                        
                plotok=True
        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)   
            self.log_Exception()
            plotok=False  
        return plotok,plinfo,ax,Plotinfo   

    def do_a_contour_plot(self,ax,Plotinfo):        
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']
        xv=Plotinfo['xv']
        yv=Plotinfo['yv']
        zv=Plotinfo['zv']        
        
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        axis_value=Plotinfo['axis_value']
        colormap_dict=Plotinfo['colormap_dict']
        cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']
        
        Show_value_Labels=Plotinfo['cont_Show_value_Labels']        
        value_Labels_size=Plotinfo['cont_value_Labels_size']
        Number_of_levels=Plotinfo['cont_Number_of_levels']
        Use_specific_Values=Plotinfo['cont_Use_specific_Values']
        Use_values=Plotinfo['cont_Use_values']        
        Use_colors=Plotinfo['cont_Use_colors']        
        contourtype=Plotinfo['Plot_Type']
        try:
            log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
            doplot=False            
            ccc=[]                
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True
                xy=xv
                z=yv
                ccc=zv #self.df_x[value]
                value=zaxis
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]  
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True
                    xy=xv
                    z=yv
                    ccc=z
                    value=yaxis
                        
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True
                    xy=yv
                    z=zv
                    ccc=z
                    value=yaxis
                    
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True
                    xy=xv
                    z=zv
                    ccc=z
                    value=yaxis
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
                                                
                #Set colormap 2D   
                
                if axis_value!=None and doplot==True:
                    ccc=self.set_ctevalue_into_MNlist(xy,axis_value)                        
                if len(ccc)==0:
                    ccc=self.set_ctevalue_into_MNlist(xy,cmrange[0])
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]
            
            #Set levels
            if  Use_specific_Values==True:  
                if self.tvf.is_list(Use_values)==True:
                    if len(Use_values)>0:
                        thelevels=Use_values                        
                        thelevels.sort()                        
                    else:
                        thelevels=None    
                else:
                    log.info('No list of values found {}'.format(Use_values))
                    thelevels=int(len(ccc)-1)
                log.info('Using Specific values {}'.format(thelevels))
            else:
                if Number_of_levels>0:
                    thelevels=Number_of_levels   
                else:
                    thelevels=None #int(len(ccc)-1)
                log.info('Using Number of levels {}'.format(thelevels))
            #log.info('Using levels {}'.format(thelevels))
            
            # Selected colors when no colormap
            thecolors=self.get_selected_list_moded(Use_colors)

            if doplot==True:                          
                if Plotinfo['Smooth_Data'] in [True,'cubic','bezier']:
                    smoothdata=True
                else:
                    smoothdata=False                                                                                                                
                #plotnonfinite differentiates NaN values in plot
                if colormap_dict[value][1]==1: #colormap active
                    #cmap = matplotlib.colors.ListedColormap(colors)
                    ccmap=colormap_dict[value][0]
                    #ax,axb,imb=self.get_ax_for_color_map_label(ax,Plotinfo)  
                    if contourtype=='contourf':
                        im = ax.contourf(xy, z, ccc, levels=thelevels,corner_mask=smoothdata, cmap = ccmap,vmin=cmvmin,vmax=cmvmax,plotnonfinite=True)
                    elif contourtype=='contour':                           
                        im = ax.contour(xy, z, ccc,  levels=thelevels,corner_mask=smoothdata, cmap = ccmap,vmin=cmvmin,vmax=cmvmax,plotnonfinite=True)                        
                    self.set_color_map_label(im,ax,ccmap,Plotinfo)                            
                    #figure.colorbar(im)                                   
                else:
                    if contourtype=='contourf':
                        im = ax.contourf(xy, z, ccc, levels=thelevels,corner_mask=smoothdata, colors=thecolors, plotnonfinite=True)
                    elif contourtype=='contour':    
                        im = ax.contour(xy, z, ccc, levels=thelevels,corner_mask=smoothdata, colors=thecolors, plotnonfinite=True)                        
                plinfo.update({'x':xy})
                plinfo.update({'y':z})                        
                plinfo.update({'z':ccc}) 
                if Show_value_Labels==True:
                    clabels = ax.clabel(im)
                    [txt.set_color('black') for txt in clabels]
                    #[txt.set_backgroundcolor('white') for txt in clabels]
                    [txt.set_fontsize(value_Labels_size) for txt in clabels]
                    
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                   
                
        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False

        return plotok,plinfo,ax,Plotinfo   
    
    def do_a_hist_plot(self,ax,Plotinfo): 
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']   
        dfuvw=Plotinfo['dfuvw']     
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']        
        colormap_dict=Plotinfo['colormap_dict']
        cmrange=Plotinfo['Colormap_Range']
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']        
        Use_bar_colors=Plotinfo['bar_Use_colors']                
        histbins,histbins2=self.get_histbins(Plotinfo['Plot_Type'],Plotinfo['hist_bins'],Plotinfo['hist_bins2'])
        hist_density=Plotinfo['hist_density']
        hist_cumulative=Plotinfo['hist_cumulative']
        hist_type=Plotinfo['hist_type']
        hist_align=Plotinfo['hist_align']
        hist_orientation=Plotinfo['hist_orientation']
        hist_relative_width=Plotinfo['hist_relative_width']
        hist_log=Plotinfo['hist_log']
        hist_stacked=Plotinfo['hist_stacked']
        hist_Use_U_V_weights=Plotinfo['hist_Use_U_V_weights']
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            #uuu,vvv,www,bbb2,_=self.get_vectors_separated(dfuvw)                
            doplot=False 
            ccc=[]                
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True
                xy=xxx
                z=yyy
                ccc=zzz 
                value=zaxis
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]                      
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True
                    xy=xxx
                    z=yyy
                    ccc=zeros
                    value=yaxis                            
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True
                    xy=yyy
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis                      
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True
                    xy=xxx
                    z=zzz
                    ccc=zeros
                    value=yaxis #2D->yaxis
                elif self.is_same_list(axis_info,[1,0,0])==True:
                    doplot=True
                    xy=bbb
                    z=xxx
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,1,0])==True:
                    doplot=True
                    xy=bbb
                    z=yyy
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                elif self.is_same_list(axis_info,[0,0,1])==True:
                    doplot=True
                    xy=bbb
                    z=zzz
                    ccc=zeros
                    value=zaxis #3D->zaxis 2D->yaxis else zaxis
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
                                        
                cmvmin=cmrange[0]
                cmvmax=cmrange[1]                
            if doplot==True:                   
                #plotnonfinite differentiates NaN values in plot
                #log.info('cm dict {}'.format(colormap_dict))
                if colormap_dict[value][1]==1: #colormap active
                    log.info('Hist plot with Colormap')
                    acmap=colormap_dict[value][0]
                    if hist_density==True:
                        hist_normalize=True
                        cmvmin=0
                        cmvmax=1
                    else:                  
                        hist_normalize=False          
                    colors=[]                                                
                    numerr=0
                    for val in z:
                        colors.append(acmap(val))                           
                    thecolors=colors                            
                    if Plotinfo['Plot_Type'] in ['hist']:  
                        im = ax.hist(z,histbins,density=hist_density,cumulative=hist_cumulative,histtype=hist_type,align=hist_align,orientation=hist_orientation,rwidth=hist_relative_width,log=hist_log,stacked=hist_stacked,color=thecolors[0])                                
                        plinfo.update({'x':histbins})
                        plinfo.update({'y':z}) 
                        
                    elif Plotinfo['Plot_Type'] in ['hist2d']:                                                        
                        if hist_normalize==True:
                            im = ax.hist2d(xy,z,histbins2,density=hist_density,cmap=acmap,norm=matplotlib.colors.Normalize(vmin=cmvmin,vmax=cmvmax))
                        else:
                            im = ax.hist2d(xy,z,histbins2,density=hist_density,cmap=acmap,vmin=cmvmin,vmax=cmvmax)
                        plinfo.update({'x':xy})
                        plinfo.update({'y':z})                        
                        plinfo.update({'z':histbins2})                            
                else:      
                    log.info('Hist plot with selected Colors')                  
                    # Selected colors when no colormap
                    thecolors=self.get_selected_list_moded(Use_bar_colors)                        
                    #line_width,line_colors=self.get_line_colors_RGBAlist(Plotinfo,xy)                                                 
                    if Plotinfo['Plot_Type'] in ['hist']:                                            
                        im = ax.hist(z,histbins,density=hist_density,cumulative=hist_cumulative,histtype=hist_type,align=hist_align,orientation=hist_orientation,log=hist_log,rwidth=hist_relative_width,stacked=hist_stacked,color=thecolors[0])    
                        plinfo.update({'x':histbins})
                        plinfo.update({'y':z}) 
                    elif Plotinfo['Plot_Type'] in ['hist2d']:
                        im = ax.hist2d(xy,z,histbins2,density=hist_density)  
                        plinfo.update({'x':xy})
                        plinfo.update({'y':z})                        
                        plinfo.update({'z':histbins2})                                                                        
                plotok=True   
                if hist_orientation=='horizontal' and Plotinfo['Plot_Type'] in ['hist']:
                    Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False 
        return plotok,plinfo,ax,Plotinfo 

    def do_a_plot_plot(self,ax,Plotinfo): 
        #Normal Plot 'plot' 'loglog','semilogx','semilogy','errorbar'     
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']        
        xv=Plotinfo['xv']
        yv=Plotinfo['yv']
        zv=Plotinfo['zv']                
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']        
        xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']                
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        try:
            #xxx,yyy,zzz,_,_=self.get_vectors_separated(dfxyz)                
            doplot=False            
            lines=[]
            if plot_Dim==3 and self.is_same_list(axis_info,[1,2,3])==True:
                doplot=True 
                for iii,jjj,kkk in zip(xv,yv,zv):    
                    alabel0=xaxis                    
                    alabel1=yaxis #+'['+str(len(lines))+']'
                    alabel2=zaxis #+'['+str(len(lines))+']'
                    ax,Plotinfo,l0=self.do_the_plot_type_plot(iii,jjj,dfxyz,[1,2,0],alabel0,alabel1,ax,Plotinfo)
                    ax,Plotinfo,l1=self.do_the_plot_type_plot(iii,kkk,dfxyz,[1,0,2],alabel0,alabel2,ax,Plotinfo)                        
                    lines.append(l0)
                    lines.append(l1)                
            elif plot_Dim==2 or plot_Dim==1: 
                if self.is_same_list(axis_info,[1,2,0])==True:
                    doplot=True                        
                    alabel0=xaxis
                    alabel1=yaxis
                    ax,Plotinfo,lines=self.do_the_plot_type_plot(xv,yv,dfxyz,axis_info,alabel0,alabel1,ax,Plotinfo)                        
                elif self.is_same_list(axis_info,[0,1,2])==True:
                    doplot=True                                                
                    alabel0=yaxis
                    alabel1=zaxis
                    ax,Plotinfo,lines=self.do_the_plot_type_plot(yv,zv,dfxyz,axis_info,alabel0,alabel1,ax,Plotinfo)                    
                elif self.is_same_list(axis_info,[1,0,2])==True:
                    doplot=True                                                
                    alabel0=xaxis
                    alabel1=zaxis                    
                    ax,Plotinfo,lines=self.do_the_plot_type_plot(xv,zv,dfxyz,axis_info,alabel0,alabel1,ax,Plotinfo)                    
                else:
                    doplot=False
                    log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))                                                                                                
            if doplot==True:                                       
                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)  
                self.set_lineformat_lines(ax,Plotinfo,lines)
                plinfo=self.get_plotted_info(Plotinfo) 
        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False           
        return plotok,plinfo,ax,Plotinfo 
    def get_separated_qui_vectors(self,qxya):
        try: 
            sh=qxya.shape[1] #if single array error
            if qxya.shape[0]==1:
                _X=qxya[0]
                _Y=numpy.asfarray([])
            elif qxya.shape[0]==2:
                _X=qxya[0]
                _Y=qxya[1] 
            else:
                _X=numpy.asfarray([])
                _Y=numpy.asfarray([])
        except:  
            if qxya.shape[0]==0:
               _X=numpy.asfarray([])
               _Y=numpy.asfarray([])           
            else:
                _X=qxya
                _Y=numpy.asfarray([])
        return _X,_Y
    
    def Autoscale_axis(self,vector,axinum,axis_info,plotinfo):
        #ppp=self.Plot_dict[aplot]
        ppp=self.Plot_dict[plotinfo['me_plot']]
        xAuto_Scale=ppp['Axis_X']['Axis_Auto_Scale']
        yAuto_Scale=ppp['Axis_Y']['Axis_Auto_Scale']
        zAuto_Scale=ppp['Axis_Z']['Axis_Auto_Scale']
        AS_vect=[xAuto_Scale,yAuto_Scale,zAuto_Scale]
        xyz_vect=['X','Y','Z']
        axname_vect=['Axis_X','Axis_Y','Axis_Z']
        for iii,axi in enumerate(axis_info):
                if axi==axinum:
                    index=iii
                    break 
        
        if AS_vect[index]==True:
            mmm=vector
            Axis_Scale_Range=[numpy.amin(mmm),numpy.amax(mmm)]
            log.info('{} {} axis auto scaled to {}'.format(plotinfo['me_plot'],xyz_vect[index],Axis_Scale_Range))
            plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,axis_info,axname_vect[index],Axis_Scale_Range)
        return plotinfo

    def get_var_axis_info_(self,axinum,axis_info,xyzlist): 
        try:
            for iii,axi in enumerate(axis_info):
                if axi==axinum:
                    index=iii
                    break      
            return xyzlist[index]
        except:
            return None
    
    def get_2D_arrays_from_dxyzuvw(self,xxx,yyy,zzz,uuu,vvv,www,axis_info,Add_axis_info):
        qxy=[]
        quv=[]
        qcv=[]
        xyzlist=[xxx,yyy,zzz]
        uvwlist=[uuu,vvv,www]   
        inai_is3=self.is_value_in_vector(3,axis_info)
        inadd_ai_is3=self.is_value_in_vector(3,Add_axis_info)
        for iii,(ai,add_ai) in enumerate(zip(axis_info,Add_axis_info)):
            if ai in [1,2]: 
                if ai ==1:
                    qxy.insert(0,xyzlist[iii])
                elif ai ==2:
                    qxy.insert(1,xyzlist[iii])    
            if add_ai in [1,2]: 
                if add_ai ==1:
                    quv.insert(0,uvwlist[iii])
                elif add_ai ==2:
                    quv.insert(1,uvwlist[iii])  
            if (inai_is3 and inadd_ai_is3)==True:
                if ai in [3] or add_ai in [3]: 
                    if ai ==3:
                        qcv.insert(0,xyzlist[iii])
                    if add_ai ==3:                    
                        qcv.insert(1,uvwlist[iii])
            elif (inai_is3 or inadd_ai_is3)==True and (inai_is3 and inadd_ai_is3)==True:
                if ai in [3] or add_ai in [3]: 
                    if ai ==3:
                        qcv.insert(0,xyzlist[iii])
                        qcv.insert(1,xyzlist[iii])
                    if add_ai ==3:                    
                        qcv.insert(0,uvwlist[iii])
                        qcv.insert(1,uvwlist[iii])
            
        qxya=numpy.asfarray(qxy)#.T
        quva=numpy.asfarray(quv)#.T
        qcva=numpy.asfarray(qcv)#.T
        # The size of qcva must match the size of qxya
        
        if qxya.shape != qcva.shape:
            _X,_Y=self.get_separated_qui_vectors(qxya)
            if qcva.shape[0]==0: #if no colors use UV values with format of XY
                _C1,_C2=self.get_separated_qui_vectors(quva)
            else:    
                _C1,_C2=self.get_separated_qui_vectors(qcva)
            if _X.shape[0]>0 and _Y.shape[0]==0:
                qcva=_C1
            elif _X.shape[0]>0 and _Y.shape[0]>0:
                qcv=[]
                qcv.insert(0,_C1.tolist())
                qcv.insert(1,_C2.tolist())
                qcva=numpy.asfarray(qcv)#.T
            else:
                qcva=numpy.asfarray([])
        return qxya,quva,qcva

    def is_value_in_vector(self,value,vector):
        for iii in vector:
            if value==iii:
                return True
        return False            
    
    def do_a_Stream_plot(self,ax,Plotinfo):  
        #'streamplot'
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']          
        plot_Dim=Plotinfo['plot_Dim']

        axis_info=Plotinfo['axis_info']
        Add_axis_info=Plotinfo['Add_axis_info']
        #axis_value=Plotinfo['axis_value']
        colormap_dict=Plotinfo['colormap_dict']       
        xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']
        uaxis=Plotinfo['uaxis']
        vaxis=Plotinfo['vaxis']
        waxis=Plotinfo['waxis']
        stream_density_xy=Plotinfo['stream_density_xy'] 
        stream_density=(stream_density_xy[0],stream_density_xy[1])
        stream_start_points=Plotinfo['stream_start_points'] 
        stream_linewidth=Plotinfo['stream_linewidth'] 
        stream_zorder=Plotinfo['stream_zorder'] 
        stream_minmaxlength=Plotinfo['stream_minmaxlength'] 
        stream_minlength=numpy.min(stream_minmaxlength)
        stream_maxlength=numpy.max(stream_minmaxlength)
        stream_color=Plotinfo['stream_color'] 
        stream_integration_direction=Plotinfo['stream_integration_direction'] 
        stream_broken_streamlines=Plotinfo['stream_broken_streamlines'] 
        
        stream_arrowstyle=Plotinfo['stream_arrowstyle'] 
        stream_arrowsize=Plotinfo['stream_arrowsize'] 
        
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            #avx,avy,got_v=self.get_simplify_neovectors(dfxyz,axis_info,Plotinfo['Reverse_Data_Series'],True,logshow=True)
            #avu,avv,got_v=self.get_simplify_neovectors(dfuvw,axis_info,Plotinfo['Reverse_Data_Series'],True,logshow=True)
            Xvar=self.get_var_axis_info_(1,axis_info,[xaxis,yaxis,zaxis])
            Yvar=self.get_var_axis_info_(2,axis_info,[xaxis,yaxis,zaxis])
            Uvar=self.get_var_axis_info_(1,Add_axis_info,[uaxis,vaxis,waxis])
            Vvar=self.get_var_axis_info_(2,Add_axis_info,[uaxis,vaxis,waxis])
            if Xvar!=None and Yvar!=None and Uvar!=None and Vvar!=None:
                umg,xmg,ymg=self.evaluate_equation_fxy_into_meshgrid('uuuuu_var='+Uvar,Xvar,Yvar)
                vmg,xmg,ymg=self.evaluate_equation_fxy_into_meshgrid('vvvvv_var='+Vvar,Xvar,Yvar)
                if type(umg)==type(None) or type(vmg)==type(None) or type(xmg)==type(None) or type(ymg)==type(None):
                    log.warning('No data returned from evaluation :( . x,y shall be monotonic and equidistant and All points must be in data. \n Or functions u(x,y) v(x,y) must be dependant of x,y where x:={},y:={}'.format(Xvar,Yvar))
                    doplot=False
                else: 
                    if stream_linewidth[0] not in ['','None','none',None]:
                        lwmg0,_,_=self.evaluate_equation_fxy_into_meshgrid(stream_linewidth[0],Xvar,Yvar)
                        if type(lwmg0)==type(None):
                            lwmg0=0*umg+1.0    
                    else:
                        lwmg0=0*umg+1.0
                    if stream_linewidth[1] not in ['','None','none',None]:
                        lwmg1,_,_=self.evaluate_equation_fxy_into_meshgrid(stream_linewidth[1],Xvar,Yvar)
                        if type(lwmg1)==type(None):
                            lwmg1=lwmg0    
                    else:
                        lwmg1=lwmg0
                    Zvar=self.get_var_axis_info_(3,axis_info,[xaxis,yaxis,zaxis])
                    Wvar=self.get_var_axis_info_(3,Add_axis_info,[uaxis,vaxis,waxis])
                    #evaluate colors if 3rd Dimension given
                    if Zvar!=None:
                        zmg,_,_=self.evaluate_equation_fxy_into_meshgrid('zzzzz_var='+Zvar,Xvar,Yvar) 
                        if type(zmg)==type(None):
                            log.info('Set z(x,y) for evaluating! Using u(x,y) for coloring!')
                            zmg=umg #not found set u    
                    else:
                        zmg=umg #not found set u
                    if Wvar!=None:
                        wmg,_,_=self.evaluate_equation_fxy_into_meshgrid('wwwww_var='+Wvar,Xvar,Yvar)                        
                        if type(wmg)==type(None):
                            log.info('Set w(x,y) for evaluating! Using v(x,y) for coloring!')
                            wmg=vmg #not found set v    
                    else:
                        wmg=vmg #not found set v
                    doplot=True
            else:
                missing=[]
                if Xvar!=None: 
                    missing.append('x') 
                if Yvar!=None:
                    missing.append('y') 
                if Uvar!=None:
                    missing.append('u') 
                if Vvar!=None:
                    missing.append('v') 
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'])) 
                log.warning('Missing the following axis: {}'.format(missing))               
                doplot=False
            '''
            xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            uuu,vvv,www,bbb2,_=self.get_vectors_separated(dfuvw)  
            qxya,quva,qcva=self.get_2D_arrays_from_dxyzuvw(xxx,yyy,zzz,uuu,vvv,www,axis_info,Add_axis_info) #sets uvw same size as xyz                       
            _xxx,_yyy=self.get_separated_qui_vectors(qxya)
            _uuu,_vvv=self.get_separated_qui_vectors(quva)            
            _zzz,_www=self.get_separated_qui_vectors(qcva)  
            #get linewidth ("2D array")
            linewidth_evalx=self.eval_data_into_a_df(stream_linewidth[0],True,True)
            linewidth_evaly=self.eval_data_into_a_df(stream_linewidth[1],True,True)                                    
            lw2D=self.set_ctevalue_into_MNlist(quva,1)
            for iii in range(0,quva.shape[1]):
                lw2D[0][iii]=linewidth_evalx[iii]
                lw2D[1][iii]=linewidth_evaly[iii]            
              
            _xxx,_xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D=self.remove_repeated_x_y(_xxx,_yyy,_yyy,_zzz,_uuu,_vvv,_www,lw2D[0],lw2D[1])            
            #sort y
            sorteddf=self.sort_vectors_to_df(_yyy,_xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D)
            _xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D=sorteddf['V1'].to_list(),sorteddf['V2'].to_list(),sorteddf['V3'].to_list(),sorteddf['V4'].to_list(),sorteddf['V5'].to_list(),sorteddf['V6'].to_list(),sorteddf['V7'].to_list(),sorteddf['V8'].to_list()
            #sort x
            sorteddf=self.sort_vectors_to_df(_xxx,_xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D)
            _xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D=sorteddf['V1'].to_list(),sorteddf['V2'].to_list(),sorteddf['V3'].to_list(),sorteddf['V4'].to_list(),sorteddf['V5'].to_list(),sorteddf['V6'].to_list(),sorteddf['V7'].to_list(),sorteddf['V8'].to_list()                
            #removes repeated of xxx leaves ux sorted
            _xxx,_xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D=self.remove_repeated_x_y(_xxx,_xxx,_yyy,_zzz,_uuu,_vvv,_www,n0lw2D,n1lw2D)            
            #log.info('xxx {} \nyyy {} \nuuu {} \nvvv {}'.format(_xxx,_yyy,_uuu,_vvv))  
            #form vectors again with sorted and removed data
            #linewidths
            qxya,quva,qlwva=self.get_2D_arrays_from_dxyzuvw(_xxx,_yyy,n0lw2D,_uuu,_vvv,n1lw2D,[1,2,3],[1,2,3]) 
            #colors
            qxya,quva,qcva=self.get_2D_arrays_from_dxyzuvw(_xxx,_yyy,_zzz,_uuu,_vvv,_www,[1,2,3],[1,2,3])                        
            
            if qxya.shape[0] in [1,2] and quva.shape[0] in [2]:                
                #enough data to do 
                doplot=True                          
            else:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
                if quva.shape[0] < 2:
                     log.warning('At least 2 vectors needed in U,V,W axis info for {} plot!'.format(Plotinfo['Plot_Type']))                                                
            '''
            #Set colormap or color                  
            #if qcva.shape[0]>0 and doplot==True:
            if doplot==True:
                #log.info('Entered 1')
                Use_Colormap=True
                if plot_Dim==2:
                    value=yaxis
                else:
                    value=zaxis
                if colormap_dict[value][1]!=1: #colormap active
                    #log.info('Entered 3 {}'.format(colormap_dict[value][1]))
                    Use_Colormap=False                                               
            else:
                #log.info('Entered 2 {}'.format(qcva.shape[0]))
                Use_Colormap=False  
                 
            #get colors when no colormap
            if Use_Colormap==False:
                if stream_color in ['','None',None,'none']:
                    scolor=self.get_a_color(0,Plotinfo,'stream_color')
                else:
                    scolor=stream_color
            
            #get starting points ("2D array")
            start_points,spvar,speq=self.get_value_of_math_eq(stream_start_points,True)
            #log.info('before start point {}'.format(start_points)) 
            if self.is_list(start_points)==True:
                for iii in start_points:
                    if len(iii)==2 and self.is_list(iii)==True:
                        isvalidsp=True
                    else:
                        log.warning('Wrong starting points format {}={}. Must be a list of [x,y] coordinates. sp=[[x1,y1],[x2,y2]...]'.format(spvar,speq))
                        isvalidsp=False
                        break
            else:
                isvalidsp=False
            if isvalidsp==False:
                start_points=None                
            else:
                start_points=numpy.asarray(start_points)
                log.info('Found selected start points {}'.format(start_points))

            if doplot==True:   
                #log.info('qxya {}\nquva {}\nqcva {}'.format(qxya,quva,qcva))
                # get meshgrids
                '''
                mg_U,mg_V=numpy.meshgrid(_uuu,_vvv)
                mg_C1,mg_C2=numpy.meshgrid(_zzz,_www)
                mg_LW1,mg_LW2=numpy.meshgrid(n0lw2D,n1lw2D)
                _X,_Y=self.get_separated_qui_vectors(qxya)
                stream_minlength=stream_minlength*min(min(_Y),min(_X))
                stream_maxlength=stream_maxlength*max(max(_Y),max(_X))
                '''

                mg_U,mg_V=umg,vmg
                mg_C1,mg_C2=zmg,wmg
                mg_LW1,mg_LW2=lwmg0,lwmg1
                
                
                '''
                if _X.shape[0]>0 and _Y.shape[0]==0:
                    _Y=numpy.asfarray(self.set_ctevalue_into_MNlist([_X.tolist()],0))
                    mg_X,mg_Y=numpy.meshgrid(_X,_Y)
                    speed=mg_LW1                     
                elif _X.shape[0]>0 and _Y.shape[0]>0:
                    mg_X,mg_Y=numpy.meshgrid(_xxx,_yyy)    
                    speed=(mg_LW1**2+mg_LW2**2)**0.5                    
                elif _X.shape[0]==0 and _Y.shape[0]==0:
                    log.warning('Using U V as positional X Y!')
                    mg_X,mg_Y=numpy.meshgrid(_uuu,_vvv)
                    speed=(mg_LW1**2+mg_LW2**2)**0.5                    
                ''' 
                mg_X,mg_Y=xmg,ymg
                _X=numpy.unique(mg_X)  
                _Y=numpy.unique(mg_Y)

                minx=int(numpy.min(_X))
                miny=int(numpy.min(_Y))
                maxx=int(numpy.max(_X))
                maxy=int(numpy.max(_Y))
                #log.info('min {} {} max {} {} '.format(minx,miny,maxx,maxy))
                if stream_maxlength<1:
                    stream_maxlength=stream_maxlength*numpy.max([maxx,maxy])
                else:
                    stream_maxlength=numpy.max([maxx,maxy])
                stream_maxlength=numpy.abs(stream_maxlength)
                stream_minlength=stream_minlength*stream_maxlength                                    
                
                log.info('Stream_minmaxlength mapped to [{},{}] '.format(stream_minlength,stream_maxlength))

                #log.info('xmg {} \nymg {}'.format(xmg,ymg))
                try:
                    speed=(mg_LW1**2+mg_LW2**2)**0.5
                except:
                    speed=mg_LW1
                atuple=(mg_X,mg_Y,mg_U,mg_V)
                cmapcolorgrid=mg_C1
                lw_array=speed #5*speed / speed.max()
                #print(_X,_Y,_U,_V)
                 
                #log.info('xxx {} \nyyy {} \nuuu {} \nvvv {}'.format(*atuple))                             
                if Use_Colormap==True: #colormap active 
                    #ax,axb,imb=self.get_ax_for_color_map_label(ax,Plotinfo) 
                    log.info('{} plot with colormap!'.format(Plotinfo['Plot_Type']))     
                    
                    im = ax.streamplot(*atuple,color=cmapcolorgrid,cmap=colormap_dict[value][0], density=stream_density, linewidth=lw_array , arrowsize=stream_arrowsize, arrowstyle=stream_arrowstyle, zorder=stream_zorder, start_points=start_points, integration_direction=stream_integration_direction,minlength=stream_minlength, maxlength=stream_maxlength)#, broken_streamlines=stream_broken_streamlines)                    
                    cmap=colormap_dict[value][0]
                    self.set_color_map_label(im,ax,cmap,Plotinfo)                          
                else:
                    log.info('{} plot color selection!'.format(Plotinfo['Plot_Type']))                                                
                    im = ax.streamplot(*atuple, color=scolor, density=stream_density, linewidth=lw_array , arrowsize=stream_arrowsize, arrowstyle=stream_arrowstyle, zorder=stream_zorder, start_points=start_points, integration_direction=stream_integration_direction,minlength=stream_minlength, maxlength=stream_maxlength)#, broken_streamlines=stream_broken_streamlines)                    
                
                plinfo.update({'x':mg_X})
                plinfo.update({'y':mg_Y})  
                plinfo.update({'z':mg_C1}) 
                plinfo.update({'u':mg_U})
                plinfo.update({'v':mg_V})
                plinfo.update({'w':mg_C2})

                plotok=True   
                #Rescale axis since lots of x,y points are removed
                Plotinfo=self.Autoscale_axis(_X,1,axis_info,Plotinfo)
                Plotinfo=self.Autoscale_axis(_Y,2,axis_info,Plotinfo)
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False   
        return plotok,plinfo,ax,Plotinfo 
    
    def remove_var_from_list(self,alist,var=[numpy.nan,math.nan,numpy.NaN,'nan','',None]):
        endlist=[]
        for iii in alist:
            if iii not in var:
               endlist.append(iii)
        return endlist   
    
    def is_equation_dependant(self,the_eq,the_var_name):
        xdependant=False
        if the_var_name in the_eq:
            xdependant=True
        else:
            listofmathdefs=self.get_dict_key_list(self.math_definitionseq)
            for eee in listofmathdefs:
                if eee in the_eq:
                    other_eq=self.math_definitionseq[eee]
                    if the_var_name in other_eq:
                        xdependant=True
                        break
        return xdependant

    def replace_in_equation_(self,eq,replacedfvars=False):
        eq_fn,the_eq=self.get_filter_math_var_name(eq)
        datafields=self.get_fields_in_csv_data(self.csv_data_filtered)
        listofmathdefs=self.get_dict_key_list(self.math_definitionseq)        
        #log.info('Found equations {}, {}'.format(listofmathdefs,self.math_definitionseq))
        for eee in listofmathdefs:
            if eee in the_eq:
                #log.info('Found {} in {}'.format(eee,the_eq))
                other_eq=self.math_definitionseq[eee]
                the_eq=the_eq.replace(eee,'('+other_eq+')')

        if replacedfvars==True:
            for vvv in datafields:
                if vvv in the_eq:                    
                    the_eq=the_eq.replace(vvv,'V_'+vvv+'_')
        return eq_fn+'='+the_eq

    def get_list_of_dfvars_in_equation(self,the_eq):
        vars=[]
        datafields=self.get_fields_in_csv_data(self.csv_data_filtered)
        for vvv in datafields:
            if vvv in the_eq:                    
                vars.append(vvv)
        return vars

    def is_all_NaN_values(self,listvals):
        all_nan=True
        for iii in listvals:
            if iii != numpy.NaN:
                all_nan=False
                break
        return all_nan
    
    def is_all_None_values(self,listvals):
        all_none=True
        for iii in listvals:
            if iii != None:
                all_none=False
                break
        return all_none

    def evaluate_all_combinations_xy_in_equation(self,ux_vect,uy_vect,eq,x_varname,y_varname):
        dxyval=[]        
        neweq=self.replace_in_equation_(eq,False)
        #log.info('neweq -> {}'.format(neweq))
        eq_fn,the_eq=self.get_filter_math_var_name(neweq)
        vineqlist=self.get_list_of_dfvars_in_equation(the_eq)  
        m_df=self.eval_data_into_a_df(neweq,logshow=True,use_filtered=False)
        log.info('Found {} values'.format(len(m_df.tolist())))
        if self.is_all_NaN_values(m_df.tolist())==True:
            log.error("Variables in {} => {} can't be evaluated".format(eq,neweq))
            return dxyval,False
        dependant=[]
        is_dependant=False
        for vard in vineqlist:
            if vard not in [x_varname,y_varname]:
                dependant.append(vard)
        if len(dependant)>0:
            is_dependant=True
            log.warning('Equation {} is dependant on external variables: f{}={}!'.format(eq,dependant,the_eq))
        missing=[]
        if is_dependant==False:
            log.info('Equation {} is non dependant of external variables, calculating every point in meshgrid.'.format(eq))
            try:
                singleeq=neweq.replace(x_varname,'xxxx__var')
                singleeq=singleeq.replace(y_varname,'yyyy__var')
                _,singleevaleq=self.get_filter_math_var_name(singleeq)
                vd={}
                for xxx in ux_vect:
                    for yyy in uy_vect:
                        vd.update({'xxxx__var':xxx}) 
                        vd.update({'yyyy__var':yyy})                         
                        theval=self.evaluate_equation(singleevaleq,vd,logshow=True)
                        #log.info('singleeq {} vd {}, -> {}'.format(singleeq,vd,theval)) 
                        if type(theval)==type('hi'):
                            theval=float(theval)
                        dxyval.append([xxx,yyy,theval])
            except Exception as e:
                log.error('Making f(x,y) evaluation: {}'.format(e))
        else:
            try:
                log.info('Equation {} is dependant of external variables. Searching for each point entry!'.format(eq))
                df=self.csv_data.copy()        
                xdf=df[x_varname]
                ydf=df[y_varname]   
                x_vect=numpy.unique(xdf)
                y_vect=numpy.unique(ydf)
                # sort vectors         
                sorteddf=self.sort_vectors_to_df(y_vect.tolist(),y_vect.tolist())  
                uy_vect=sorteddf['V1'].to_list()
                sorteddf=self.sort_vectors_to_df(x_vect.tolist(),x_vect.tolist())  
                ux_vect=sorteddf['V1'].to_list()                       
                df[eq_fn]=m_df                
                show_warning=False                
                for xxx in ux_vect:
                    for yyy in uy_vect: 
                        qqq=x_varname+'='+str(xxx)+' & '+y_varname+'='+str(yyy)   
                        #log.info('Query -> {}'.format(qqq))                
                        try:
                            dfq=df.query(qqq)
                        except:
                            dfq={}
                        if len(dfq)>0:
                            val_l=dfq[eq_fn].tolist()
                            theval=val_l[0]
                        else:
                            missing.append(qqq)
                            show_warning=True
                            theval=numpy.NaN
                        if type(theval)==type('hi'):
                            theval=float(theval)
                        dxyval.append([xxx,yyy,theval])
                if show_warning==True:            
                    if len(missing)>10:
                        theq=[missing[0],missing[1],missing[2],'...4 to '+str(len(missing)-1)+'...',missing[len(missing)-1]]
                    else:
                        theq=missing
                    log.warning('Not all values are present in csv file. f{} Missing several values: \n {}'.format(vineqlist,theq))
            except Exception as e:
                log.error('Making f{} evaluation: {}'.format(vineqlist,e))
        if len(missing)>10:
            return dxyval,False            
        return dxyval,True
    
    def list_can_be_int(self,vect):
        di=1e-6
        isint=False
        count=0
        dv=0        
        for vvv in vect:
            if count>0:
                if dv>=vvv-lastv:
                    dv=vvv-lastv                    
                lastv=vvv
            else:
                dv=1e8
                lastv=vvv
            if int(vvv)<vvv+di and int(vvv)>vvv-di:
                count=count+1            
            
        if count==len(vect):
            isint=True
        return isint,dv



    def get_equally_spaced_vectors(self,vect):
        minv=numpy.min(vect)
        maxv=numpy.max(vect)
        mindelta=abs(maxv-minv)
        cbi,dv=self.list_can_be_int(vect)
        if cbi==True:
            if dv==0:
                dv=1            
            vector=range(int(minv),int(maxv+dv),int(dv))
        else:
            for vvv in vect:
                ddd=abs(minv-vvv)
                if ddd==0:            
                    ddd=abs(maxv-minv)/len(vect)
                if mindelta>ddd:
                    mindelta=ddd
            #log.info('mindelta -> {}'.format(mindelta))
            
            if len(vect)>0:            
                vector=self.listrange(minv,maxv,mindelta)
            else:
                vector=vect
            #log.info('vector -> {}'.format(vector))
        return vector 

    def evaluate_equation_fxy_into_meshgrid(self,eq,Xvar,Yvar,showlog=True,needsequallyspaced=True):
        eq_fn,the_eq=self.get_filter_math_var_name(eq)
        try:                
            xdf=self.get_datafield_of_variable(Xvar)
            ydf=self.get_datafield_of_variable(Yvar)
            valdf=self.eval_data_into_a_df(eq,False,True)

            x_vect=xdf.to_list()
            y_vect=ydf.to_list()
            x_vect=self.remove_var_from_list(x_vect) #clean nan or empty values
            y_vect=self.remove_var_from_list(y_vect)
            ux=numpy.unique(x_vect)
            uy=numpy.unique(y_vect)     
            if needsequallyspaced==True:                
                x_vect=self.get_equally_spaced_vectors(ux.tolist())       
                y_vect=self.get_equally_spaced_vectors(uy.tolist())       
            #x_vect,y_vect=self.remove_repeated_x_y(x_vect,y_vect)   
            # sort vectors         
            sorteddf=self.sort_vectors_to_df(y_vect,y_vect)        
            y_vect=sorteddf['V1'].to_list()
            sorteddf=self.sort_vectors_to_df(x_vect,x_vect)        
            x_vect=sorteddf['V1'].to_list()
            if showlog==True:
                log.info('Evaluating f(x,y)={} x:={}, y:={}'.format(the_eq,Xvar,Yvar))
                log.info(' xvect {}\n yvect {}'.format(x_vect,y_vect))
            dxyval,hasvalues=self.evaluate_all_combinations_xy_in_equation(x_vect,y_vect,eq,Xvar,Yvar)
            #log.info('found -> {} , hasvalues {}'.format(len(dxyval),hasvalues))
            Xmg,Ymg=numpy.meshgrid(x_vect,y_vect)
            if hasvalues==False:
                log.warning('Evaluation of {}={} returned no values!'.format(eq_fn,the_eq))
                Valmgy=numpy.NaN*Ymg                
                return None,None,None
            
            Valmgy=numpy.NaN*Ymg                
            Valmgx=numpy.NaN*Xmg
            
            #log.info('Xmg {}'.format(Xmg))
            for iii,xxx in enumerate(x_vect):
                for jjj,yyy in enumerate(y_vect):
                    index=self.get_index_for_xy_in_dxyval(xxx,yyy,dxyval)
                    theval=dxyval[index][2]                    
                    Valmgx[jjj][iii]=theval
                    Valmgy[jjj][iii]=theval
            #log.info('Valmg {}'.format(Valmgy))
            return Valmgy,Xmg,Ymg
        except Exception as e:
            log.error('Evaluating f(x,y)={} x:={}, y:={} into meshgrid! {}'.format(the_eq,Xvar,Yvar,e))
            return None,None,None

    def get_index_for_xy_in_dxyval(self,xxx,yyy,dxyval):          
        for jjj in range(0,len(dxyval)):
            if xxx==dxyval[jjj][0] and yyy==dxyval[jjj][1]:
                return jjj


    def do_a_quiver_plot(self,ax,Plotinfo):  
        #'quiver', 'barbs'       
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        dfxyz=Plotinfo['dfxyz']
        dfuvw=Plotinfo['dfuvw']               
        Add_axis_info=Plotinfo['Add_axis_info']
        plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        #axis_value=Plotinfo['axis_value']
        colormap_dict=Plotinfo['colormap_dict']       
        #xaxis=Plotinfo['xaxis']
        yaxis=Plotinfo['yaxis']
        zaxis=Plotinfo['zaxis']
       
        qui_angles=Plotinfo['qui_angles'] 
        qui_pivot=Plotinfo['qui_pivot'] 
        qui_units=Plotinfo['qui_units'] 
        qui_scale=Plotinfo['qui_scale'] 
        qui_scale_units=Plotinfo['qui_scale_units'] 
        qui_color=Plotinfo['qui_color'] 
        qui_arr_width=Plotinfo['qui_arr_width'] 
        qui_arr_headwidth=Plotinfo['qui_arr_headwidth'] 
        qui_arr_headlength=Plotinfo['qui_arr_headlength'] 
        qui_arr_headaxislength=Plotinfo['qui_arr_headaxislength'] 
        qui_arr_minshaft=Plotinfo['qui_arr_minshaft'] 
        qui_arr_minlength=Plotinfo['qui_arr_minlength'] 

        barbs_length=Plotinfo['barbs_length'] 
        barbs_pivot=Plotinfo['barbs_pivot'] 
        barbs_barbcolor=Plotinfo['barbs_barbcolor'] 
        barbs_flagcolor=Plotinfo['barbs_flagcolor'] 
        barbs_sizes_spacing=Plotinfo['barbs_sizes_spacing'] 
        barbs_sizes_height=Plotinfo['barbs_sizes_height'] 
        barbs_sizes_width=Plotinfo['barbs_sizes_width'] 
        barbs_sizes_emptybarb=Plotinfo['barbs_sizes_emptybarb'] 
        barbs_fill_empty=Plotinfo['barbs_fill_empty'] 
        barbs_rounding=Plotinfo['barbs_rounding'] 
        barbs_barb_increments_half=Plotinfo['barbs_barb_increments_half'] 
        barbs_barb_increments_full=Plotinfo['barbs_barb_increments_full'] 
        barbs_barb_increments_flag=Plotinfo['barbs_barb_increments_flag'] 
        barb_increments={'half':barbs_barb_increments_half,'full':barbs_barb_increments_full,'flag':barbs_barb_increments_flag}
        sizes={'spacing':barbs_sizes_spacing,'height':barbs_sizes_height,'width':barbs_sizes_width,'emptybarb':barbs_sizes_emptybarb}         
        
        log.info('{} starting {} {}D as {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'], plot_Dim,axis_info))
        doplot=False
        try:
            xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            uuu,vvv,www,bbb2,_=self.get_vectors_separated(dfuvw)   
            qxya,quva,qcva=self.get_2D_arrays_from_dxyzuvw(xxx,yyy,zzz,uuu,vvv,www,axis_info,Add_axis_info)

            if qxya.shape[0] in [1,2] and quva.shape[0] in [2]:                
                #enough data to do 
                doplot=True                          
            else:
                doplot=False
                log.warning('Not enough data to make {} {} plot!'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
                if quva.shape[0] < 2:
                     log.warning('At least 2 vectors needed in U,V,W axis info for {} plot!'.format(Plotinfo['Plot_Type']))                                                
            #Set colormap or color                  
            if qcva.shape[0]>0 and doplot==True:
                #log.info('Entered 1')
                Use_Colormap=True
                if plot_Dim==2:
                    value=yaxis
                else:
                    value=zaxis
                if colormap_dict[value][1]!=1: #colormap active
                    #log.info('Entered 3 {}'.format(colormap_dict[value][1]))
                    Use_Colormap=False                                               
            else:
                #log.info('Entered 2 {}'.format(qcva.shape[0]))
                Use_Colormap=False       
            #get colors when no colormap
            if Use_Colormap==False:
                qcolor=self.get_selected_list_moded(qui_color)
                if self.is_list(qcolor)==True:                    
                    cl2D=self.set_ctevalue_into_MNlist(quva,'black')
                    for iii in range(0,quva.shape[1]):
                        cl2D[0][iii]=(self.get_line_color(iii,Plotinfo,'qui_color'))
                        cl2D[1][iii]=(self.get_line_color(iii,Plotinfo,'qui_color'))
                    qcolor=cl2D
            else:
                qcolor=None
            if Plotinfo['Plot_Type']=='barbs':
                bbcolor=self.get_selected_list_moded(barbs_barbcolor)
                bfcolor=self.get_selected_list_moded(barbs_flagcolor)
                if self.is_list(bbcolor)==True:                    
                    cl2D=self.set_ctevalue_into_MNlist(quva,'black')
                    for iii in range(0,quva.shape[1]):
                        cl2D[0][iii]=(self.get_barbcolor(iii,Plotinfo))                    
                    bbcolor=cl2D[0]
                if self.is_list(bfcolor)==True:                                        
                    for iii in range(0,quva.shape[1]):                        
                        cl2D[1][iii]=(self.get_flagcolor(iii,Plotinfo))                    
                    bfcolor=cl2D[1]
            else:
                qcolor=None
            log.info('qcolor {}'.format(qcolor))    
            if doplot==True:                                   
                #log.info('qxya {}\nquva {}\nqcva {}'.format(qxya,quva,qcva))
                _X,_Y=self.get_separated_qui_vectors(qxya)
                _U,_V=self.get_separated_qui_vectors(quva)
                _C1,_C2=self.get_separated_qui_vectors(qcva)
                #print(_X,_Y,_U,_V)
                if _X.shape[0]>0 and _Y.shape[0]==0:
                    if Use_Colormap==True:
                        #log.info('_X {}'.format(_X))
                        _Y=numpy.asfarray(self.set_ctevalue_into_MNlist([_X.tolist()],0))
                        atuple=(_X,_Y,_U,_V,_C1)
                    else:                        
                        atuple=(_X,_U,_V)                                
                elif _X.shape[0]>0 and _Y.shape[0]>0:
                    if Use_Colormap==True:
                        atuple=(_X,_Y,_U,_V,_C1)
                    else:
                        atuple=(_X,_Y,_U,_V)
                elif _X.shape[0]==0 and _Y.shape[0]==0:
                    if Use_Colormap==True:
                        _X=_U
                        _Y=_V
                        log.warning('Using U V as positional X Y!')
                        atuple=(_X,_Y,_U,_V,_C1)
                    else:                        
                        atuple=(_U,_V)                   
                if Plotinfo['Plot_Type']=='quiver':
                    if Use_Colormap==True: #colormap active 
                        #ax,axb,imb=self.get_ax_for_color_map_label(ax,Plotinfo) 
                        log.info('{} plot with colormap!'.format(Plotinfo['Plot_Type']))                                                
                        im = ax.quiver(*atuple,cmap=colormap_dict[value][0],angles=qui_angles,pivot=qui_pivot,units=qui_units ,scale=qui_scale ,scale_units=qui_scale_units,width=qui_arr_width ,headwidth=qui_arr_headwidth ,headlength=qui_arr_headlength ,headaxislength=qui_arr_headaxislength ,minshaft=qui_arr_minshaft ,minlength=qui_arr_minlength)                    
                        cmap=colormap_dict[value][0]
                        self.set_color_map_label(im,ax,cmap,Plotinfo)                          
                    else:
                        log.info('{} plot color selection!'.format(Plotinfo['Plot_Type']))                                                
                        im = ax.quiver(*atuple, color=qcolor,angles=qui_angles,pivot=qui_pivot,units=qui_units ,scale=qui_scale ,scale_units=qui_scale_units,width=qui_arr_width ,headwidth=qui_arr_headwidth ,headlength=qui_arr_headlength ,headaxislength=qui_arr_headaxislength ,minshaft=qui_arr_minshaft ,minlength=qui_arr_minlength)
                if Plotinfo['Plot_Type']=='barbs':
                    if Use_Colormap==True: #colormap active 
                        #ax,axb,imb=self.get_ax_for_color_map_label(ax,Plotinfo) 
                        log.info('{} plot with colormap!'.format(Plotinfo['Plot_Type']))                                                
                        im = ax.barbs(*atuple, cmap=colormap_dict[value][0], barbcolor=bbcolor ,length=barbs_length,pivot=barbs_pivot, fill_empty=barbs_fill_empty , rounding=barbs_rounding , barb_increments=barb_increments, sizes=sizes)                    
                        cmap=colormap_dict[value][0]
                        self.set_color_map_label(im,ax,cmap,Plotinfo)  
                    else:
                        log.info('{} plot color selection!'.format(Plotinfo['Plot_Type']))                                                
                        im = ax.barbs(*atuple, barbcolor=bbcolor, flagcolor=bfcolor,length=barbs_length,pivot=barbs_pivot, fill_empty=barbs_fill_empty , rounding=barbs_rounding , barb_increments=barb_increments, sizes=sizes)                    
                    
                plinfo.update({'x':_X})
                plinfo.update({'y':_Y})  
                plinfo.update({'z':_C1}) 
                plinfo.update({'u':_U})
                plinfo.update({'v':_V})
                plinfo.update({'w':_C2})

                plotok=True   
                self.set_legends_title(ax,Plotinfo) 
                self.set_axis_ticks(ax,Plotinfo)                      

        except Exception as e:
            log.error('Making {} plot'.format(Plotinfo['Plot_Type']))
            log.error(e)
            self.log_Exception()
            plotok=False   
        return plotok,plinfo,ax,Plotinfo 

    def do_plot_fig(self,ax,Plotinfo):
        log.info('++++++++++++ Starting Plot {} ++++++++++'.format(Plotinfo['me_plot']))
        plinfo=self.get_plotted_info(Plotinfo) 
        plotok=True
        
        sss=Plotinfo['me_layout']        

        # if exists selects the subplot, if not creates one, also sets projection
        try:
            if Plotinfo['Projection_Type'] in ['polar','3d']:
                ax=matplotlib.pyplot.subplot(sss,projection=Plotinfo['Projection_Type']) 
                log.info('Plot projection {}'.format(Plotinfo['Projection_Type']))
            else:
                ax=matplotlib.pyplot.subplot(sss)            
            #ax.twinx()
            log.info('Plot Layout {}'.format(sss))
        except Exception as e:
            #ax=matplotlib.pyplot.subplot(sss)            
            #ax.twinx()
            log.info('Plot Layout {} created'.format(sss))
            log.error('Making Subplot {}'.format(e))
            
        
        #log.info('Plot Layout {}, {}, {}'.format(melayout,[RSlay,CSlay],[Hlay-1,Vlay-1]))
        
        #ax=self.FigPreview.add_subplot(self.spec[melayout[0],melayout[1]])# melayout[0],melayout[1],melayout[2])
        
        # set predifined style
       
        prestyle=Plotinfo['Predefined_Style']
        if prestyle not in ['','None']:
            #needs to be run befor making the plots
            #all set styles will be overwritten
            matplotlib.rcdefaults()            
            #matplotlib.pyplot.style.reload_library()           
            #apply the prestyle 
            matplotlib.pyplot.style.use(prestyle) 
            self.FigPreview.canvas.draw()
            self.FigPreview.canvas.flush_events()           
            log.info('Using {} predifined style! Other style settings will override this setting!'.format(prestyle))
        else:
            matplotlib.rcdefaults()
            matplotlib.pyplot.style.use('default')

        if Plotinfo['Plot_Type'] in ['scatter']:
            plotok,plinfo,ax,Plotinfo=self.do_a_scatter_plot(ax,Plotinfo)
        
        if Plotinfo['Plot_Type'] in ['bar','barh']:
            plotok,plinfo,ax,Plotinfo=self.do_a_bar_plot(ax,Plotinfo)
        
        if Plotinfo['Plot_Type'] in ['stem']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Stem_plot(ax,Plotinfo)

        if Plotinfo['Plot_Type'] == 'image':
            plotok,plinfo,ax,Plotinfo=self.do_a_image_plot(ax,Plotinfo)
            
        if Plotinfo['Plot_Type'] in ['contour' ,'contourf']:           
            plotok,plinfo,ax,Plotinfo=self.do_a_contour_plot(ax,Plotinfo) 
            
        if Plotinfo['Plot_Type'] in ['hist','hist2d']:
            plotok,plinfo,ax,Plotinfo=self.do_a_hist_plot(ax,Plotinfo) 

        if Plotinfo['Plot_Type'] in ['quiver','barbs']:
            plotok,plinfo,ax,Plotinfo=self.do_a_quiver_plot(ax,Plotinfo) 
        
        if Plotinfo['Plot_Type'] in ['streamplot']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Stream_plot(ax,Plotinfo) 
        
        if Plotinfo['Plot_Type'] in ['eventplot']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Event_plot(ax,Plotinfo) 
        if Plotinfo['Plot_Type'] in ['stackplot']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Stack_plot(ax,Plotinfo) 
        if Plotinfo['Plot_Type'] in ['stairs']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Stairs_plot(ax,Plotinfo) 
        if Plotinfo['Plot_Type'] in ['pie']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Pie_plot(ax,Plotinfo) 
        if Plotinfo['Plot_Type'] in ['violin']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Violin_plot(ax,Plotinfo) 
        if Plotinfo['Plot_Type'] in ['boxplot']:
            plotok,plinfo,ax,Plotinfo=self.do_a_Box_plot(ax,Plotinfo) 

        if Plotinfo['Plot_Type'] in ['specgram','psd','magnitude_spectrum','angle_spectrum','phase_spectrum']:
            plotok,plinfo,ax,Plotinfo=self.do_a_spectrum_plot(ax,Plotinfo) 
            
        if Plotinfo['Plot_Type'] in ['plot','loglog','semilogx','semilogy','errorbar']:
            plotok,plinfo,ax,Plotinfo=self.do_a_plot_plot(ax,Plotinfo) 

        Plotinfo.update({'Plotted_info':plinfo})                   
        
        '''if Plotinfo['Predefined_Style'] not in ['','None']:
            prestyle=Plotinfo['Predefined_Style']
            matplotlib.pyplot.style.use(prestyle)            
            #thelib=matplotlib.pyplot.style.library            
            self.FigPreview.canvas.draw()
            self.FigPreview.canvas.flush_events()'''
        if plotok==True:
            self.Send_Figure_icon(Plotinfo['me_plot'])        
        return plotok,Plotinfo
    
    def repeat_0_position(self,vext):
        if type(vext)==type(numpy.asarray([1,2])):
            var=vext[0]
            vext.insert(0,var)             
        elif self.is_list(vext)==True:
            var=vext[0]
            vext.insert(0,var)
            
            
        return vext

    def do_plot_Errorbar(self,xy,z,ax,error_kw_dict,Use_Err_bars):
        if Use_Err_bars==True:         
            #log.info('x{} y{} :{}'.format(xy,z,error_kw_dict))
            #log.debug('xy {}'.format(xy))
            #log.debug('xerr {}'.format(error_kw_dict['xerr']))
            #log.debug('z {}'.format(z))
            #log.debug('yerr {}'.format(error_kw_dict['yerr']))
            #log.info('lolims {}'.format(error_kw_dict['lolims']))
            '''xy=self.repeat_0_position(xy)
            z=self.repeat_0_position(z)
            xerr=self.repeat_0_position(error_kw_dict['xerr'])
            yerr=self.repeat_0_position(error_kw_dict['yerr'])'''
            xy=numpy.asarray(xy)
            z=numpy.asarray(z)
            xerr=numpy.asarray(error_kw_dict['xerr'])
            yerr=numpy.asarray(error_kw_dict['xerr'])
            im = matplotlib.pyplot.errorbar(xy,z,xerr=xerr,yerr=yerr,
                                ecolor=error_kw_dict['ecolor'],
                                capsize=error_kw_dict['capsize'],            
                                lolims=error_kw_dict['lolims'],
                                xlolims=error_kw_dict['xlolims'],
                                uplims=error_kw_dict['uplims'],
                                xuplims=error_kw_dict['xuplims'],
                                errorevery=error_kw_dict['errorevery'],
                                fmt=error_kw_dict['fmt'],
                                capthick=error_kw_dict['capthick'],
                                barsabove=error_kw_dict['barsabove'],
                                elinewidth=error_kw_dict['elinewidth'])
            matplotlib.pyplot.sca(ax) #make ax active axis
            return im
        else:
            return None

    def get_selected_list_moded(self,Use_list):        
        if len(Use_list)==0:
            thecolors=None
        elif len(Use_list)==1:
            thecolors=Use_list[0]
        elif len(Use_list)>1:
            thecolors=Use_list
        return thecolors

    def get_error_bar_dict(self,xy,z,Plotinfo,numl=0):
        Use_Err_bars=Plotinfo['Use_Err_bars']
        Err_Y_Use_key=Plotinfo['Err_Y_Use_key']
        Err_X_Use_key=Plotinfo['Err_X_Use_key']
        Err_bar_ecolor=Plotinfo['Err_bar_ecolor']        
        if Err_bar_ecolor=='':        
            Err_bar_ecolor=self.get_line_color(numl,Plotinfo)
        Err_bar_capsize=Plotinfo['Err_bar_capsize']     
        Err_bar_fmt=Plotinfo['Err_bar_fmt']
        Err_bar_capthick=Plotinfo['Err_bar_capthick']
        Err_bar_barsabove=Plotinfo['Err_bar_barsabove']
        Err_bar_elinewidth=Plotinfo['Err_bar_elinewidth']
        Err_bar_errorevery_X=Plotinfo['Err_bar_errorevery_X']
        Err_bar_errorevery_Y=Plotinfo['Err_bar_errorevery_Y']
        Err_bar_lolims=Plotinfo['Err_bar_lolims']
        Err_bar_xlolims=Plotinfo['Err_bar_xlolims']
        Err_bar_uplims=Plotinfo['Err_bar_uplims']
        Err_bar_xuplims=Plotinfo['Err_bar_xuplims']   
        #Evaluate errorbars
        error_kw_dict={'xerr':None, 'yerr':None,'ecolor':'black','capsize':0.0}   
        if Use_Err_bars==True:
            #log.info('{} plot type with Error bars'.format(Plotinfo['Plot_Type']))
            xerr=None 
            yerr=None 
            if Err_Y_Use_key!='':
                try:                                                                                        
                    m_dfy=self.eval_data_into_a_df(Err_Y_Use_key,logshow=False,use_filtered=True)
                    yerr=numpy.asarray(m_dfy)
                    #log.info('Errbar->{} \n {} \n {}'.format(m_dfy,xy,z))                    
                    if len(yerr)!=len(xy):
                        #log.info('Evaluating Error bar Y Key')
                        dferry,neoerrvx,neoerrvy =self.get_error_dxyzsized(m_dfy,Err_Y_Use_key,Plotinfo)
                        #log.info('XY {} \n {} \n {}'.format(xy,neoerrvx,neoerrvy))
                        for neox,neoy in zip(neoerrvx,neoerrvy):
                            if self.is_same_list(neox,xy):
                                yerr=numpy.asarray(neoy)
                                #log.info('Found yerr len {}'.format(len(yerr)))
                                break                        
                        
                except Exception as e:                        
                    log.error('Error evaluating Error bar math equation: {}'.format(Err_Y_Use_key))                        
                    log.error(e)  
                    yerr=None                            
            if Err_X_Use_key!='':
                try:                                                                                        
                    m_dfx=self.eval_data_into_a_df(Err_X_Use_key,logshow=False,use_filtered=True)
                    xerr=numpy.asarray(m_dfx)
                    if len(xerr)!=len(xy):
                        #log.info('Evaluating Error bar X Key')
                        dferrx,neoerrvx,neoerrvy =self.get_error_dxyzsized(m_dfx,Err_X_Use_key,Plotinfo)
                        for neox,neoy in zip(neoerrvx,neoerrvy):
                            if self.is_same_list(neox,xy):
                                xerr=numpy.asarray(neoy)
                                #log.info('Found xerr len {}'.format(len(xerr)))
                                break                        
                except Exception as e:                        
                    log.error('Error evaluating Error bar math equation: {}'.format(Err_X_Use_key))                        
                    log.error(e)  
                    xerr=None            
            error_kw_dict.update({'xerr':xerr})
            error_kw_dict.update({'yerr':yerr})            
            error_kw_dict.update({'ecolor':Err_bar_ecolor})
            error_kw_dict.update({'capsize':Err_bar_capsize})
            Err_bar_lolims=self.get_selected_list_moded(Err_bar_lolims)
            Err_bar_xlolims=self.get_selected_list_moded(Err_bar_xlolims)
            Err_bar_uplims=self.get_selected_list_moded(Err_bar_uplims)
            Err_bar_xuplims=self.get_selected_list_moded(Err_bar_xuplims)            
            lolims=self.get_Errorbar_limit_list(z,Err_bar_lolims)
            xlolims=self.get_Errorbar_limit_list(xy,Err_bar_xlolims)
            uplims=self.get_Errorbar_limit_list(z,Err_bar_uplims)
            xuplims=self.get_Errorbar_limit_list(xy,Err_bar_xuplims)
            error_kw_dict.update({'lolims':lolims})
            error_kw_dict.update({'xlolims':xlolims})
            error_kw_dict.update({'uplims':uplims})
            error_kw_dict.update({'xuplims':xuplims})
            error_kw_dict.update({'errorevery':(Err_bar_errorevery_Y,Err_bar_errorevery_X)})
            error_kw_dict.update({'fmt':Err_bar_fmt})
            error_kw_dict.update({'capthick':Err_bar_capthick})
            error_kw_dict.update({'barsabove':Err_bar_barsabove})
            error_kw_dict.update({'elinewidth':Err_bar_elinewidth})
        
        return error_kw_dict
    def replace_xyerr_in_dict(self,error_kw_dict,xerr,yerr,Do_replace):        
        if Do_replace==True:
            error_kw_dict.update({'xerr':xerr})
            error_kw_dict.update({'yerr':yerr})
        return error_kw_dict
    
    def get_dferrxyz(self,Plotinfo):
        Err_Y_Use_key=Plotinfo['Err_Y_Use_key']
        Err_X_Use_key=Plotinfo['Err_X_Use_key']
        ErrY_name,ErrY_eq=self.get_filter_math_var_name(Err_Y_Use_key)
        ErrX_name,ErrX_eq=self.get_filter_math_var_name(Err_X_Use_key)
        if Err_Y_Use_key!='':
            try:                                                                                        
                m_dfy=self.eval_data_into_a_df(Err_Y_Use_key,logshow=False,use_filtered=True)               
                dferry,_,_ =self.get_error_dxyzsized(m_dfy,Err_Y_Use_key,Plotinfo)                                        
            except Exception as e:                        
                m_dfy=self.eval_data_into_a_df(ErrY_name+'=0',logshow=False,use_filtered=True)               
                log.error('Error bar Y math equation: {} set to 0'.format(Err_Y_Use_key))                        
                log.error(e)  
        else:
            m_dfy=self.eval_data_into_a_df(ErrY_name+'=0',logshow=False,use_filtered=True)                                          
        if Err_X_Use_key!='':
            try:                                                                                        
                m_dfx=self.eval_data_into_a_df(Err_X_Use_key,logshow=False,use_filtered=True)                                
                dferrx,_,_ =self.get_error_dxyzsized(m_dfx,Err_X_Use_key,Plotinfo)
            except Exception as e:    
                m_dfx=self.eval_data_into_a_df(ErrX_name+'=0',logshow=False,use_filtered=True)                                   
                log.error('Error bar X math equation: {} set to 0'.format(Err_X_Use_key))                        
                log.error(e)  
        else:
            m_dfx=self.eval_data_into_a_df(ErrY_name+'=0',logshow=False,use_filtered=True)                                   
        dxyzerr=[]        
        dfxyz=Plotinfo['dfxyz']
        #plot_Dim=Plotinfo['plot_Dim']
        axis_info=Plotinfo['axis_info']
        #log.info('len dfxyz: {},len m_dfx: {},len m_dfy: {}'.format(len(dfxyz),len(m_dfx),len(m_dfy)))
        try:
            for iii,axi in enumerate(axis_info):
                if axi==1:
                    index=iii
                    break        
            #log.info('index val {}'.format(index))  
            xerr=numpy.asarray(m_dfx)
            yerr=numpy.asarray(m_dfy)         
            for iii,dfi in enumerate(dfxyz): 
                    #log.info('index {} {}'.format(index,dfi[index]))           
                    #log.info('vals {} {}'.format(xerr[iii],yerr[iii]))           
                    dxyzerr.append([dfi[index],xerr[iii],yerr[iii]])
            #log.info('Error x errx erry: {}'.format(dxyzerr))
        except Exception as e:
            log.Error('Error getting dferrorxyz: {}'.format(e))
        return dxyzerr

    
    def get_Errorbar_limit_list(self,z,Err_bar_lolims):
        if self.is_list(Err_bar_lolims)==True:
            lolim=[]
            for iii,_ in enumerate(z):
                lolim.append(self.get_error_limit(iii,Err_bar_lolims))
            return lolim
        else:
            if type(Err_bar_lolims)==type(True):
                return Err_bar_lolims
            else:
                try:
                    return self.str_to_bool(Err_bar_lolims)
                except:
                    return False


    def get_line_colors_RGBAlist(self,Plotinfo,xy):
        line_width=[]    
        numerr=0
        line_colors=[]
        for jjj,_ in enumerate(xy):                                                       
            try:
                lccc=self.get_line_color(jjj,Plotinfo)
                line_colors.append(matplotlib.colors.to_rgba(lccc))
                line_width.append(self.get_line_width(jjj,Plotinfo))  
            except Exception as e:
                if lccc!='':                                                                 
                    log.warning('Error on line color: {}'.format(e))
                numerr=numerr+1
                pass                                                   
        return line_width,line_colors

    def get_histbins(self,plottype,hist_bins,hist_bins2):
        if plottype in ['hist']:
            if len(hist_bins)==1:
                hist_bins=hist_bins[0]
            elif len(hist_bins)==0:
                hist_bins=10
            else:
                hist_bins.sort()  
            #print('hist_bins:',hist_bins) 
            return hist_bins,hist_bins
        else:     
            if len(hist_bins)==0:
                hist_bins=[10]
            if len(hist_bins2)==0:
                hist_bins2=[10]            
            hbmax=max(len(hist_bins),len(hist_bins2))            
            if len(hist_bins)==1 and len(hist_bins2)==1:
                hbins=[hist_bins[0],hist_bins2[0]]
            elif hbmax==0:
                hbins=[10,10]
            elif hbmax>=1:
                hbins=[]      
                try:
                    hist_bins.sort()
                except:
                    pass
                try:
                    hist_bins2.sort()
                except:
                    pass
                for jjj in range(0,hbmax):
                    #print('hbins:',hbins)
                    h1err=False
                    h2err=False
                    try:
                        h1=hist_bins[jjj]
                    except:
                        h1err=True
                        h1=10
                    try:
                        h2=hist_bins2[jjj]
                    except:
                        h2err=True
                        h2=10 
                    if h1err==False and h2err==False:
                        hbins.append([h1,h2])
                    elif h1err==True and h2err==False:
                        hbins.append([h2,h2])
                    elif h1err==False and h2err==True:
                        hbins.append([h1,h1])
                    elif h1err==True and h2err==True:
                        hbins.append([h1,h2])
            #print('[hbmax],hbins:',[hbmax],hbins) 
            return [hbmax],hbins
        


    def get_vectors_separated(self,dfxyz):
        xxx=[]
        yyy=[]
        zzz=[]
        bbb=[]
        zeros=[]
        try:
            for sss,xyz in enumerate(dfxyz):
                xxx.append(xyz[0])
                yyy.append(xyz[1])
                zzz.append(xyz[2])
                bbb.append(sss+1) #counts from 0
                zeros.append(0)
            return xxx,yyy,zzz,bbb,zeros
        except:
            return xxx,yyy,zzz,bbb,zeros

        
                        
    def set_ctevalue_into_MNlist(self,xy,ctevalue):        
        ccc=[]
        for iii in xy:
            bbb=[]
            for jjj in iii:
                bbb.append(ctevalue)                            
            ccc.append(bbb)                            
        return ccc

    def get_line_color(self,line_number,Plotinfo,plotproperty='linecolor'):
        linecolor_list=Plotinfo[plotproperty]                
        numcolors=len(linecolor_list)
        ccc=numpy.fmod(line_number, numcolors)                    
        acolor=str(linecolor_list[ccc]).strip("'")
        if acolor=='':
            prop_cycle = matplotlib.pyplot.rcParams['axes.prop_cycle']
            linecolor_list = prop_cycle.by_key()['color']
            numcolors=len(linecolor_list)
            ccc=numpy.fmod(line_number, numcolors)                    
            acolor=str(linecolor_list[ccc]).strip("'")
        return acolor
    
    def get_line_markertype(self,line_number,Plotinfo,lproperty='Line_Marker_Type'):
        linemarker_list=Plotinfo[lproperty]                
        nummark=len(linemarker_list)
        ccc=numpy.fmod(line_number, nummark)                 
        if 'int_' in linemarker_list[ccc]:
            amarker=int(linemarker_list[ccc].strip('int_'))  
        else:                 
            amarker=str(linemarker_list[ccc]).strip("'")
        return amarker
    
    def get_line_markersize(self,line_number,Plotinfo,lproperty='Line_Marker_Size'):
        line_list=Plotinfo[lproperty]              
        numcolors=len(line_list)
        ccc=numpy.fmod(line_number, numcolors)                    
        ans=float(line_list[ccc])
        return ans
    
    def get_line_markeredgewidth(self,line_number,Plotinfo,lproperty='markeredgewidth'):
        line_list=Plotinfo[lproperty]              
        numcolors=len(line_list)
        ccc=numpy.fmod(line_number, numcolors)                    
        ans=float(line_list[ccc])
        return ans
    
    def get_line_markeredgecolor(self,line_number,Plotinfo,lproperty='markeredgecolor'):        
        acolor=self.get_a_color(line_number,Plotinfo,lproperty)                               
        return acolor
    
    def get_barbcolor(self,line_number,Plotinfo):        
        acolor=self.get_a_color(line_number,Plotinfo,'barbs_barbcolor')                               
        return acolor
    
    def get_flagcolor(self,line_number,Plotinfo):        
        acolor=self.get_a_color(line_number,Plotinfo,'barbs_flagcolor')                               
        return acolor
    
    def get_line_markerfacecolor(self,line_number,Plotinfo,lproperty='markerfacecolor'):        
        acolor=self.get_a_color(line_number,Plotinfo,lproperty)        
        return acolor
    
    def get_a_color(self,line_number,Plotinfo,plotproperty):
        linecolor_list=Plotinfo[plotproperty]   
        if self.is_list(linecolor_list)==False:
            try:
                linecolor_list=self.tvf.str_to_list(linecolor_list)  
                if linecolor_list==None:
                    linecolor_list=[]
            except:
                linecolor_list=[]           
        numcolors=len(linecolor_list)
        if numcolors==0:            
            acolor=self.get_line_color(line_number,Plotinfo)            
        else:            
            ccc=numpy.fmod(line_number, numcolors)             
            acolor=str(linecolor_list[ccc]).strip("'")
        if acolor=='':            
            prop_cycle = matplotlib.pyplot.rcParams['axes.prop_cycle']
            linecolor_list = prop_cycle.by_key()['color']
            numcolors=len(linecolor_list)
            ccc=numpy.fmod(line_number, numcolors)                    
            acolor=str(linecolor_list[ccc]).strip("'")
        return acolor
    
    def get_line_markerfacecoloralt(self,line_number,Plotinfo):
        linecolor_list=Plotinfo['markerfacecolor']                
        numcolors=len(linecolor_list)
        if numcolors==0:            
            acolor=self.get_line_color(line_number,Plotinfo)
            
        else:            
            ccc=numpy.fmod(line_number, numcolors)                    
            acolor=str(linecolor_list[ccc]).strip("'")
        if acolor=='':
            prop_cycle = matplotlib.pyplot.rcParams['axes.prop_cycle']
            linecolor_list = prop_cycle.by_key()['color']
            numcolors=len(linecolor_list)
            ccc=numpy.fmod(line_number, numcolors)                    
            acolor=str(linecolor_list[ccc]).strip("'")
        return acolor    

    def get_line_style(self,line_number,Plotinfo,plotproperty='linestyle'):
        line_list=Plotinfo[plotproperty]               
        numcolors=len(line_list)
        if numcolors==0:
            return str(line_list).strip("'")
        ccc=numpy.fmod(line_number, numcolors)                    
        ans=str(line_list[ccc]).strip("'")
        return ans
    
    def get_line_width(self,line_number,Plotinfo,plotproperty='linewidth'):
        line_list=Plotinfo[plotproperty]                      
        numcolors=len(line_list)
        if numcolors==0:
            return float(line_list)
        ccc=numpy.fmod(line_number, numcolors)                    
        ans=float(line_list[ccc])
        return ans
    
    def get_error_limit(self,line_number,line_list):               
        numcolors=len(line_list)
        ccc=numpy.fmod(line_number, numcolors)                    
        val=line_list[ccc]
        if type(val)==type(True):
            ans=val
        else:
            ans=self.str_to_bool(val)
        #log.info('got {}-->{} {} of {}'.format(line_number,ccc,ans,line_list))
        return ans
    
    def str_to_bool(self,val):
        if val.lower() in ['true','1','yes','t','y','yeah', 'yup', 'certainly','si','s']:   
            return True
        else:
            return False

    def set_lineformat_lines(self,ax,Plotinfo,lines):
        #get info        
        dash_capstyle=Plotinfo['dash_capstyle']
        dash_joinstyle=Plotinfo['dash_joinstyle']
        drawstyle=Plotinfo['drawstyle'] 
        lineusemarkers=Plotinfo['lineusemarkers']
        markertype=Plotinfo['Line_Marker_Type']                
        markersize=Plotinfo['Line_Marker_Size']                        

        #Dash
        for aaa,_ in enumerate(lines):
            try:                                                
                matplotlib.pyplot.setp(ax.lines[aaa],dash_capstyle=dash_capstyle)                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                                
                matplotlib.pyplot.setp(ax.lines[aaa],dash_joinstyle=dash_joinstyle)                       
            except Exception as e:
                log.warning(e)
                pass        
            try:                                                
                matplotlib.pyplot.setp(ax.lines[aaa],drawstyle=drawstyle)                       
            except Exception as e:
                log.warning(e)
                pass
            if lineusemarkers==True:                
                try:                
                    mt=self.get_line_markertype(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],marker=mt)                       
                except Exception as e:
                    log.warning(e)
                    pass
                try:                
                    ms=self.get_line_markersize(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],markersize=ms)                       
                except Exception as e:
                    log.warning(e)
                    pass
                try:                
                    mec=self.get_line_markeredgecolor(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],markeredgecolor=mec)                       
                except Exception as e:
                    log.warning(e)
                    pass
                try:                
                    mew=self.get_line_markeredgewidth(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],markeredgewidth=mew)                       
                except Exception as e:
                    log.warning(e)
                    pass
                try:                
                    mfc=self.get_line_markerfacecolor(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],markerfacecolor=mfc)                       
                except Exception as e:
                    log.warning(e)
                    pass
                try:                
                    mfca=self.get_line_markerfacecoloralt(aaa,Plotinfo)                                
                    matplotlib.pyplot.setp(ax.lines[aaa],markerfacecoloralt=mfca)                       
                except Exception as e:
                    log.warning(e)
                    pass
    
    def set_Stem_lineformat_lines(self,Plotinfo,xy, markerline, stemlines):
        #get info        
        dash_capstyle=Plotinfo['dash_capstyle']
        dash_joinstyle=Plotinfo['dash_joinstyle']
        #drawstyle=Plotinfo['drawstyle'] #not in linecollections
        lineusemarkers=Plotinfo['lineusemarkers']
                          
        try:                                                
            matplotlib.pyplot.setp(stemlines,capstyle=dash_capstyle)                       
        except Exception as e:
            log.warning(e)
            pass
        try:                                                
            matplotlib.pyplot.setp(stemlines,joinstyle=dash_joinstyle)                       
        except Exception as e:
            log.warning(e)
            pass        
        '''try:                                                
            matplotlib.pyplot.setp(stemlines,drawstyle=drawstyle)                       
        except Exception as e:
            #log.warning(e) 
            pass'''
        
        colorm=self.get_selected_list_moded(Plotinfo['linecolor'])          
        colors=self.getsized_property(xy,colorm)
        if '' in colors:
            for iii,ccc in enumerate(colors):
                if ccc=='':
                    colors[iii]=self.get_a_color(iii,Plotinfo,'linecolor')
        stylem=self.get_selected_list_moded(Plotinfo['linestyle'])         
        styles=self.getsized_property(xy,stylem)
        if '' in styles:
            for iii,sss in enumerate(styles):
                if sss=='':
                    styles[iii]='-'
        widthm=self.get_selected_list_moded(Plotinfo['linewidth'])   
        widths=self.getsized_property(xy,widthm)
        try:                                                
            matplotlib.pyplot.setp(stemlines,linestyle=styles)                       
        except Exception as e:
            log.warning(e)
            pass
        try:                                                
            matplotlib.pyplot.setp(stemlines,colors=colors)                       
        except Exception as e:
            log.warning(e)
            pass
        try:                                                
            matplotlib.pyplot.setp(stemlines,linewidth=widths)                       
        except Exception as e:
            log.warning(e)
            pass
            
        if lineusemarkers==True:   
            lmtm=self.get_selected_list_moded(Plotinfo['Line_Marker_Type'])   
            Line_Marker_Types=self.getsized_property(xy,lmtm)
            lmsm=self.get_selected_list_moded(Plotinfo['Line_Marker_Size'])   
            Line_Marker_Sizes=self.getsized_property(xy,lmsm)
            #Use lines to get all info in same place
            if Line_Marker_Types[0]=='':
                markertype=Plotinfo['Plot_Marker_Type']   
            else:
                markertype=Line_Marker_Types[0]  
            if Line_Marker_Sizes[0]==0:                
                markersize=Plotinfo['Plot_Marker_Size']
            else:
                markersize=Line_Marker_Sizes[0]

            mecm=self.get_selected_list_moded(Plotinfo['markeredgecolor'])   
            #to rgba
            for iii,lccc in enumerate(mecm):
                mecm[iii]=matplotlib.colors.to_rgba(lccc)
            markeredgecolors=self.getsized_property(xy,mecm)
            mewm=self.get_selected_list_moded(Plotinfo['markeredgewidth'])   
            markeredgewidths=self.getsized_property(xy,mewm)
            mfcm=self.get_selected_list_moded(Plotinfo['markerfacecolor'])   
            #to rgba
            for iii,lccc in enumerate(mfcm):
                mfcm[iii]=matplotlib.colors.to_rgba(lccc)
            markerfacecolors=self.getsized_property(xy,mfcm)
            mfcam=self.get_selected_list_moded(Plotinfo['markerfacecoloralt'])   
            #to rgba
            for iii,lccc in enumerate(mfcam):
                mfcam[iii]=matplotlib.colors.to_rgba(lccc)
            markerfacecoloralts=self.getsized_property(xy,mfcam)            
            try:                        
                matplotlib.pyplot.setp(markerline,marker=markertype)                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                
                matplotlib.pyplot.setp(markerline,markersize=markersize)                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                                             
                matplotlib.pyplot.setp(markerline,markeredgecolor=markeredgecolors[0])                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                
                matplotlib.pyplot.setp(markerline,markeredgewidth=markeredgewidths[0])                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                             
                matplotlib.pyplot.setp(markerline,markerfacecolor=markerfacecolors[0])                       
            except Exception as e:
                log.warning(e)
                pass
            try:                                                 
                matplotlib.pyplot.setp(markerline,markerfacecoloralt=markerfacecoloralts[0])                       
            except Exception as e:
                log.warning(e)
                pass

    def get_plotted_info(self,Plotinfo):
        try:
            plinfo=Plotinfo['Plotted_info']
            #log.info('++++++++get_plotted_info got info {}!'.format(Plotinfo['me_plot']))
        except:
            #log.info('++++++++get_plotted_info got err {}!'.format(Plotinfo['me_plot']))
            plinfo={'x':[],'y':[],'z':[],'xerr':[],'yerr':[],'u':[],'v':[],'w':[]}
            pass
        return plinfo

           

    def do_the_plot_type_plot(self,xv,zv,dfxyz,axis_info,alabel0,alabel1,ax,Plotinfo):
        #plottypes 'plot','loglog','semilogx','semilogy','errorbar'
        avx,avy,got_v=self.get_xy_vectors(xv,zv)  
        errvx=None
        errvy=None     
        replace_err_vectors=False   
        if got_v==False:
            avx,avy,got_v=self.get_simplify_neovectors(dfxyz,axis_info,Plotinfo['Reverse_Data_Series'],Plotinfo['Line_Complete_Vectors'],logshow=True)
            dferrxyz=self.get_dferrxyz(Plotinfo)
            _,errvx,_=self.get_simplify_neovectors(dferrxyz,[1,2,0],Plotinfo['Reverse_Data_Series'],Plotinfo['Line_Complete_Vectors'],logshow=False)
            _,errvy,_=self.get_simplify_neovectors(dferrxyz,[1,0,2],Plotinfo['Reverse_Data_Series'],Plotinfo['Line_Complete_Vectors'],logshow=False)
            replace_err_vectors=True
            #log.info('----------------------------\navx={}\navy={}\n----------------------------'.format(avx,avy))
            #log.info('----------------------------\errx={}\erry={}\n----------------------------'.format(errvx,errvy))
        
        if Plotinfo['Reverse_Data_Series']==True:
            Plotinfo=self.exchange_labels_ticks_X_Y(Plotinfo)

        plinfo=self.get_plotted_info(Plotinfo)    
        pt=Plotinfo['Plot_Type']
        lines=[]      
        if got_v==False:
            #alabel1=alabel1+'('+alabel0+')' 
            log.info('{} {} has multiplicity of different sized values detected on {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'],alabel1))            
            log.info("Set 'Lines'->'Complete_Vectors' to True to make them a matrix!")
            nr=len(avx)   
            log.debug('Size here is:nr={},avx={},avy={}'.format(nr,self.get_size_array(avx),self.get_size_array(avy)))            
            if nr>1:
                maxlen=1
                numl=0
                for iii,jjj in zip(avx,avy):           
                    if Plotinfo['Reverse_Data_Series']==True:                              
                        alabel11=alabel0+'['+str(len(lines))+']('+alabel1+'='+str(jjj[0])+')'
                    else:
                        alabel11=alabel1+'['+str(len(lines))+']('+alabel0+'='+str(iii[0])+')'
                    nnn=list(range(1,len(iii)+1))
                    #log.info('\n{}\n{}\n{}'.format(iii,jjj,nnn))  
                    mycolor=self.get_line_color(numl,Plotinfo) 
                    mylw=self.get_line_width(numl,Plotinfo)  
                    myls=self.get_line_style(numl,Plotinfo)  
                    if Plotinfo['Smooth_Data'] in [True,'cubic','bezier'] and pt!='errorbar':
                        nump=50
                        if Plotinfo['Smooth_Data'] in [True,'cubic']:
                            X_,Y_=self.get_x_y_cubic_interpolation(nnn,jjj,nump)
                        if Plotinfo['Smooth_Data'] in ['bezier']:                            
                            X_,Y_=self.get_x_y_bezier_interpolation(nnn,jjj,nump)  
                        if pt== 'plot':                      
                            l0, = ax.plot(X_, Y_, label=alabel11)
                        #elif pt=='polar':
                        #    l0, = ax.plot(X_, Y_, label=alabel11)
                        elif pt=='loglog':
                            l0, = ax.loglog(X_, Y_, label=alabel11)
                        elif pt=='semilogx':
                            l0, = ax.semilogx(X_, Y_, label=alabel11)
                        elif pt=='semilogy':
                            l0, = ax.semilogy(X_, Y_, label=alabel11)
                        elif pt=='hist2d':
                            l0, = ax.hist2d(X_, Y_, label=alabel11)                                              
                    else:                        
                        if pt== 'plot':                      
                            l0, = ax.plot(nnn, jjj, label=alabel11)
                        #elif pt=='polar':
                        #    l0, = ax.plot(nnn, jjj, label=alabel11)
                        elif pt=='loglog':
                            l0, = ax.loglog(nnn, jjj, label=alabel11)
                        elif pt=='semilogx':
                            l0, = ax.semilogx(nnn, jjj, label=alabel11)
                        elif pt=='semilogy':
                            l0, = ax.semilogy(nnn, jjj, label=alabel11)
                        elif pt=='hist2d':
                            l0, = ax.hist2d(nnn, jjj, label=alabel11)

                    plinfo['x'].append(nnn)
                    plinfo['y'].append(jjj)
                    #add error bars
                    if Plotinfo['Use_Err_bars']==True or pt=='errorbar':
                        error_kw_dict=self.get_error_bar_dict(iii, jjj,Plotinfo=Plotinfo,numl=numl)
                        if replace_err_vectors==True:
                            error_kw_dict=self.replace_xyerr_in_dict(error_kw_dict,errvx[numl],errvy[numl],replace_err_vectors)
                        l0eb = self.do_plot_Errorbar(nnn, jjj,ax,error_kw_dict,True)    
                        plinfo['xerr'].append(error_kw_dict['xerr'])
                        plinfo['yerr'].append(error_kw_dict['yerr'])
                    if pt=='errorbar':
                        l0=l0eb
                    else:
                        if mycolor!='':
                            l0.set_color(mycolor)                                                                            
                        if mylw>0:
                            l0.set_linewidth(mylw)
                        if myls!='':                        
                            l0.set_linestyle(myls)                                                                                                                                                                                                                                        
                    lines.append(l0)
                    maxlen=max(maxlen,len(iii)+1)
                    numl=numl+1
                   
                Plotinfo.update({'ticks_xset': True})       
                Plotinfo.update({'ticks_xstepsize': 1})        
                Plotinfo.update({'ticks_xmin': 0})
                Plotinfo.update({'ticks_xmax': maxlen}) 
                log.info('Ploting amount of repetitions in x axis!')
                
        else:                            
            nr,_=self.get_size_array(avx)  
            #log.info('2 Vectors:{},{}'.format(avx,avy))
            log.info('{} {} has vectors {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type'],alabel1))
            if nr>1:
                numl=0
                for iii,jjj in zip(avx,avy):   
                    if Plotinfo['Reverse_Data_Series']==True:
                        alabel11=alabel0+'['+str(len(lines))+']('+alabel1+')'
                    else:                     
                        alabel11=alabel1+'['+str(len(lines))+']('+alabel0+')'
                    mycolor=self.get_line_color(numl,Plotinfo)  
                    mylw=self.get_line_width(numl,Plotinfo)  
                    myls=self.get_line_style(numl,Plotinfo) 
                    if Plotinfo['Smooth_Data'] in [True,'cubic','bezier'] and pt!='errorbar':
                        nump=50
                        if Plotinfo['Smooth_Data'] in [True,'cubic']:
                            X_,Y_=self.get_x_y_cubic_interpolation(iii,jjj,nump)                        
                        if Plotinfo['Smooth_Data'] in ['bezier']:
                            X_,Y_=self.get_x_y_bezier_interpolation(iii,jjj,nump)  
                        if pt== 'plot':                      
                            l0, = ax.plot(X_, Y_, label=alabel11)
                        #elif pt=='polar':
                        #    l0, = ax.plot(X_, Y_, label=alabel11)
                        elif pt=='loglog':
                            l0, = ax.loglog(X_, Y_, label=alabel11)
                        elif pt=='semilogx':
                            l0, = ax.semilogx(X_, Y_, label=alabel11)
                        elif pt=='semilogy':
                            l0, = ax.semilogy(X_, Y_, label=alabel11)
                        elif pt=='hist2d':
                            l0, = ax.bar(X_, Y_, label=alabel11)                                                 
                    else:   
                        if pt== 'plot':                                           
                            l0, = ax.plot(iii, jjj, label=alabel11) 
                        #elif pt=='polar':
                        #    l0, = ax.plot(iii, jjj, label=alabel11)   
                        elif pt=='loglog':                             
                            l0, = ax.loglog(iii, jjj, label=alabel11)
                        elif pt=='semilogx':
                            l0, = ax.semilogx(iii, jjj, label=alabel11)
                        elif pt=='semilogy':                       
                            l0, = ax.semilogy(iii, jjj, label=alabel11)
                        elif pt=='hist2d':                       
                            l0, = ax.hist2d(iii, jjj, label=alabel11)
                    plinfo['x'].append(iii)
                    plinfo['y'].append(jjj)                    
                    #add error bars
                    if Plotinfo['Use_Err_bars']==True or pt=='errorbar':
                        error_kw_dict=self.get_error_bar_dict(iii,jjj,Plotinfo=Plotinfo,numl=numl)
                        if replace_err_vectors==True:
                            error_kw_dict=self.replace_xyerr_in_dict(error_kw_dict,errvx[numl],errvy[numl],replace_err_vectors)
                        l0eb = self.do_plot_Errorbar(iii,jjj,ax,error_kw_dict,True)
                        plinfo['xerr'].append(error_kw_dict['xerr'])
                        plinfo['yerr'].append(error_kw_dict['yerr'])
                    if pt=='errorbar':
                        l0=l0eb
                    else:
                        if mycolor!='':
                            l0.set_color(mycolor)                                                                            
                        if mylw>0:
                            l0.set_linewidth(mylw)
                        if myls!='':                        
                            l0.set_linestyle(myls)                      
                    lines.append(l0)
                    numl=numl+1
            else:    
                numl=0 
                mycolor=self.get_line_color(numl,Plotinfo)  
                mylw=self.get_line_width(numl,Plotinfo)  
                myls=self.get_line_style(numl,Plotinfo) 
                if Plotinfo['Reverse_Data_Series']==True:
                    alabel11=alabel0
                else:                     
                    alabel11=alabel1
                if Plotinfo['Smooth_Data'] in [True,'cubic','bezier'] and pt!='errorbar':
                    nump=50
                    if Plotinfo['Smooth_Data'] in [True,'cubic']:
                        X_,Y_=self.get_x_y_cubic_interpolation(avx,avy,nump)
                    if Plotinfo['Smooth_Data'] in ['bezier']:
                        X_,Y_=self.get_x_y_bezier_interpolation(avx,avy,nump)                                                                                
                    if pt== 'plot':                      
                        l0, = ax.plot(X_, Y_, label=alabel11)
                    #elif pt=='polar':
                    #    l0, = ax.plot(X_, Y_, label=alabel11)
                    elif pt=='loglog':
                        l0, = ax.loglog(X_, Y_, label=alabel11)
                    elif pt=='semilogx':
                        l0, = ax.semilogx(X_, Y_, label=alabel11)
                    elif pt=='semilogy':
                        l0, = ax.semilogy(X_, Y_, label=alabel11)
                    elif pt=='hist2d':
                        l0, = ax.hist2d(X_, Y_, label=alabel11)                                         
                else:   
                    if pt== 'plot':                                           
                        l0, = ax.plot(avx, avy, label=alabel11)
                    #elif pt=='polar':
                    #    l0, = ax.plot(avx, avy, label=alabel11)
                    elif pt=='loglog':
                        l0, = ax.loglog(avx, avy, label=alabel11)
                    elif pt=='semilogx':
                        l0, = ax.semilogx(avx, avy, label=alabel11)
                    elif pt=='semilogy':
                        l0, = ax.semilogy(avx, avy, label=alabel11)
                    elif pt=='hist2d':
                        l0, = ax.hist2d(avx, avy, label=alabel11)
                plinfo['x'].append(avx)
                plinfo['y'].append(avy) 
                #add error bars
                if Plotinfo['Use_Err_bars']==True or pt=='errorbar':
                    error_kw_dict=self.get_error_bar_dict(avx, avy,Plotinfo=Plotinfo,numl=numl)
                    if replace_err_vectors==True:
                            error_kw_dict=self.replace_xyerr_in_dict(error_kw_dict,errvx[numl],errvy[numl],replace_err_vectors)
                    l0eb = self.do_plot_Errorbar(avx, avy,ax,error_kw_dict,True)
                    plinfo['xerr'].append(error_kw_dict['xerr'])
                    plinfo['yerr'].append(error_kw_dict['yerr'])
                if pt=='errorbar':
                    l0=l0eb
                else:
                    if mycolor!='':
                        l0.set_color(mycolor)                                                                            
                    if mylw>0:
                        l0.set_linewidth(mylw)
                    if myls!='':                        
                        l0.set_linestyle(myls)                  
                lines.append(l0)
        #print('plinfo->',plinfo)
        Plotinfo.update({'Plotted_info':plinfo})
        return ax, Plotinfo, lines
    
    def get_phi(self):
        delta=1e-9
        fip1=1
        fi=0
        nnn=0
        while delta<abs(fi-fip1) or nnn>1e5:
            fi=fip1
            fip1=1/(1+fi)
            nnn=nnn+1
            #print(nnn,1/fi)

        return 1/fi

    def get_x_y_bezier_interpolation(self,xxx,yyy,numpoint=50):
        '''
        Given a set of control points, return the
        bezier curve defined by the control points.

        points should be a list of lists, or list of tuples
        such as [ [1,1], 
                    [2,3], 
                    [4,5], ..[Xn, Yn] ]
            nTimes is the number of time steps, defaults to 50

            See http://processingjs.nihongoresources.com/bezierinfo/
        '''

        nPoints = len(xxx)
        xPoints = numpy.asarray(xxx)
        yPoints = numpy.asarray(yyy)

        t = numpy.linspace(0.0, 1.0, numpoint)

        polynomial_array = numpy.asarray([ self.bernstein_poly(i, nPoints-1, t) for i in range(0, nPoints) ])

        xvals = numpy.dot(xPoints, polynomial_array)
        yvals = numpy.dot(yPoints, polynomial_array)

        return xvals, yvals
      
    def bernstein_poly(self,i, n, t):
        """
        The Bernstein polynomial of n, i as a function of t
        """
        return comb(n, i) * ( t**i ) * (1 - t)**(n-i)

    def get_x_y_cubic_interpolation(self,xxx,yyy,numpoint=500):
        arnnn=numpy.asarray(xxx)
        arjjj=numpy.asarray(yyy)
        cubic_interploation_model = interp1d(arnnn, arjjj, kind = "cubic")
        # Interpolation
        X_=numpy.linspace(arnnn.min(), arnnn.max(), int(numpoint))
        Y_=cubic_interploation_model(X_)   
        return X_,Y_

    def get_xy_neovectors_fromdfxyz(self,dfxyz,axis_info,Reverse=False):        
        if self.is_same_list(axis_info,[1,2,3])==True:
            aX,aY,_=self.get_X_Y_Z_from_dfxyz(dfxyz)
        elif self.is_same_list(axis_info,[1,2,0])==True:
            aX,aY,_=self.get_X_Y_Z_from_dfxyz(dfxyz)
        elif self.is_same_list(axis_info,[1,0,2])==True:
            aX,_,aY=self.get_X_Y_Z_from_dfxyz(dfxyz)
        elif self.is_same_list(axis_info,[0,1,2])==True:
            _,aX,aY=self.get_X_Y_Z_from_dfxyz(dfxyz)        
        else:
            return None,None
        if Reverse==True:
            invX=aX
            aX=aY
            aY=invX
        ux=numpy.unique(aX)
        mat=[]
        kkk=-1
        #print(aX,aY,ux)
        newcycle=False
        for iii,uuuxxx in enumerate(ux):
            if iii>0:   
                newcycle=True
            for jjj,xxx in enumerate(aX):
                #print(iii,jjj,kkk,uuuxxx,xxx,aX[jjj],aY[jjj])
                if uuuxxx==xxx and iii==0 and kkk==-1:                    
                    mat=[[[[aX[jjj]],[aY[jjj]]]]]
                    #print('Entered matini',mat)
                    newcycle=False
                    kkk=0
                elif uuuxxx==xxx and newcycle==True:
                    mat.append([[[aX[jjj]],[aY[jjj]]]])
                    #print('Entered matjjj0',mat)
                    newcycle=False
                    kkk=kkk+1
                elif uuuxxx==xxx and newcycle==False:
                    #print('Entered append',iii,kkk,mat[iii][0][0])
                    mat[iii][0][0].append(aX[jjj])
                    mat[iii][0][1].append(aY[jjj])
                    #print(mat)  
                    #kkk=kkk+1
        #print('Neo matrix->',mat)
        avx=[]
        avy=[]
 
        for vect in mat:
            avx.append(vect[0][0])
            avy.append(vect[0][1])
        #log.debug('Neo vectors: x:{}'.format(avx))
        #log.debug('Neo vectors: y:{}'.format(avy))

        return avx,avy
    
    def get_simplify_neovectors(self,dfxyz,axis_info,Reversed=False,Complete_Vectors=False,logshow=True):
        samesize=False
        avx,avy=self.get_xy_neovectors_fromdfxyz(dfxyz,axis_info,Reversed)        
        sv_avx=self.get_vector_of_size_array(avx)
        sv_avy=self.get_vector_of_size_array(avy)        
        if self.is_the_same_value_in_vector(sv_avx)==True: 
            if sv_avx[0]==1:                
                navx=[]            
                for aaa in avx:
                    navx.append(aaa[0])
                avx=navx    
                if self.is_the_same_value_in_vector(sv_avy)==True and sv_avy[0]==1:                
                    navy=[]
                    for aaa in avy:
                        navy.append(aaa[0])
                    avy=navy
                    samesize=True
            elif sv_avx[0]>1 and self.is_the_same_value_in_vector(sv_avy)==True and sv_avx[0]==sv_avy[0]:                   
                avx=self.transpose_matrix[avx]
                avy=self.transpose_matrix[avy]
                samesize=True 
                
        if samesize==False:
            if logshow==True:
                log.info("X vector Array's sizes: {}".format(sv_avx))
                log.info("Y vector Array's sizes: {}".format(sv_avy))
            if Complete_Vectors==True:
                max_sv_x=len(sv_avx)
                max_sv_y=max(sv_avy)
                navx=[]            
                navy=[] 
                for iii in range(0,max_sv_x):                    
                    aux=[]            
                    for jjj in range(0,max_sv_y):                                                
                        aux.append(numpy.NaN)
                    navx.append(aux.copy())
                    navy.append(aux.copy())
                #log.info('before avx {} avy {}'.format(avx,avy))
                for iii in range(0,max_sv_x):                                        
                    for jjj in range(0,max_sv_y): 
                        try:               
                            #print('---------------->',avx[iii][jjj])                                
                            navx[iii][jjj]=avx[iii][jjj]    
                            navy[iii][jjj]=avy[iii][jjj]
                        except:
                            pass                        
                #log.info('after navx {} navy {}'.format(navx,navy))
                if Reversed==False:
                    avx=self.transpose_matrix(navx)
                    avy=self.transpose_matrix(navy)
                else:
                    avx=navx
                    avy=navy
                samesize=True

        return avx,avy,samesize
        
        


    def get_X_Y_Z_from_dfxyz(self,dfxyz):
        xxx,yyy,zzz,_,_=self.get_vectors_separated(dfxyz)
        return xxx,yyy,zzz

    def get_xy_vectors(self,xv,yv):
        nr_x,nc_x=self.get_size_array(xv)  
        nr_y,nc_y=self.get_size_array(yv)  
        txv=self.transpose_matrix(xv)
        tyv=self.transpose_matrix(yv)
        #log.info('sizex {} {} sizey {} {} xv yv {} {}'.format(nr_x,nc_x,nr_y,nc_y,xv,yv))
        if nr_x!=nc_x or nr_y!=nc_y: #different size mesh is not transposable
            equal_size=False
        else:
            equal_size=True
            #return xv,yv,False        
        is_Samex=self.is_repeated_item_in_vector(xv)
        is_Samext=self.is_repeated_item_in_vector(txv)
        is_Samey=self.is_repeated_item_in_vector(yv)
        is_Sameyt=self.is_repeated_item_in_vector(tyv)
        #log.info('is_same xy xyt: {} {}'.format((is_Samex,is_Samey),(is_Samext,is_Sameyt)))        
        solx,_=self.get_differentvalue_vector(xv,txv,yv,tyv,is_Samex ,is_Samext)
        _,soly=self.get_differentvalue_vector(xv,txv,yv,tyv,is_Samey ,is_Sameyt)       
        if is_Samex==False and is_Samext==False:
            #log.info('Selected vector pos 0 {} {}'.format((is_Samex,is_Samey),(is_Samext,is_Sameyt )))
            solx=solx[0]
            soly=soly[0]        
        #log.info('xv yv {} {} solx soly {} {}'.format(xv,yv,solx,soly))
        return solx,soly,equal_size

    def get_differentvalue_vector(self,xv,txv,yv,tyv,is_Samex,is_Samext):
        if is_Samex==True and is_Samext==False:
            solx=txv
            soly=tyv            
        elif is_Samex==False and is_Samext==True:
            solx=xv
            soly=yv
        elif is_Samex==True and is_Samext==True:
            solx=xv
            soly=tyv
        elif is_Samex==False and is_Samext==False:
            solx=txv
            soly=yv
        return solx,soly


    def is_repeated_item_in_vector(self,xv):        
        for iii in xv:
            inijjj=iii[0]
            for jjj in iii:
                if inijjj!=jjj:
                    return False                    
        return True
    
    def is_the_same_value_in_vector(self,sv):        
        for iii,sss in enumerate(sv):
            if iii==0:
                inijjj=sss
            else:            
                if inijjj!=sss:
                    return False                    
        return True

    def transpose_matrix(self,mat):
        t_mat=[]
        if type(mat)==numpy.ndarray:
            return numpy.transpose(mat)
        elif type(mat)==type([]):
            iii=0
            nr,nc=self.get_size_array(mat)
            if nc>0 and nr>0:
                if nr==1:
                    for jjj,col in enumerate(mat):
                        t_mat.append([col])
                else:
                    for iii,row in enumerate(mat[0]):
                        t_mat.append([row])
                    for iii,row in enumerate(mat):                    
                        for jjj,col in enumerate(row):
                            if iii>0:
                                t_mat[jjj].append(col)
                        
        return t_mat

    def get_size_array(self,mat):
        nr=0
        nc=0
        if len(mat)>0:  
            nr=len(mat)
            try:
                nc=len(mat[0])
            except:
                nc=nr
                nr=1
        return nr,nc
    
    def get_vector_of_size_array(self,mat):
        nr,nc=self.get_size_array(mat)
        #log.info('mat: {}'.format(mat))
        size_vect=[]
        if nr>0: 
            for row in  mat:                            
                _,nc=self.get_size_array([row])     
                size_vect.append(nc)
        #log.info('size vect: {}'.format(size_vect))
        return size_vect
    
    def get_ax_for_color_map_label(self,ax,plotinfo):
        Show_Label=plotinfo['cm_Colormap_Show_Label']        
        if Show_Label==True:
            log.info('Showing Colormap')            
            position_label=plotinfo['cm_position_label'] #"top", "right", "bottom", or "left"
            #gs0 = plotinfo['me_layout'][0]
            gs0 = self.spec[plotinfo['me_layout_pos']]
            #print('gs0',gs0)
            if position_label in ["right","left"]:
                gs00 = matplotlib.gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec=gs0)
                ori='vertical'
                axsize=[0.2, 0.1, 0.05, 0.6]
            elif position_label in ["top", "bottom"]:
                gs00 = matplotlib.gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs0)
                ori='horizontal'
                axsize=[0.2, 0.1, 0.6, 0.05]
            if position_label in ["right"]:
                sssb=self.get_spec([2,1],[1,0],gs00) #row col
                sss=self.get_spec([2,1],[0,0],gs00) #row col
            if position_label in ["left"]:
                sssb=self.get_spec([2,1],[0,0],gs00) #row col
                sss=self.get_spec([2,1],[1,0],gs00) #row col
            if position_label in ["top"]:
                sssb=self.get_spec([1,2],[0,0],gs00) #row col
                sss=self.get_spec([1,2],[0,0],gs00) #row col
            if position_label in ["bottom"]:
                sssb=self.get_spec([1,2],[0,1],gs00) #row col
                sss=self.get_spec([1,2],[0,0],gs00) #row col             
            axb=matplotlib.pyplot.subplot(sssb)
            #imb=matplotlib.pyplot.add_axes(axsize)
            axp=matplotlib.pyplot.subplot(sss)
            imb=axb
            return axp,axb,imb
        return ax,None,None
        


    def set_color_map_label(self,im,ax,cmap,plotinfo):        
        Show_Label=plotinfo['cm_Colormap_Show_Label']        
        if Show_Label==True:            
            log.info('Showing Colormap')
            cm_label=plotinfo['cm_label']
            fontsize_label=plotinfo['cm_fontsize_label']
            rotation_label=plotinfo['cm_rotation_label']
            position_label=plotinfo['cm_position_label'] #"top", "right", "bottom", or "left"
            label_align=plotinfo['cm_label_align']
            if position_label in ["right","left"]:            
                ori='vertical'
            elif position_label in ["top", "bottom"]:            
                ori='horizontal'                
            
            #pyplot.colorbar, which internally use Colorbar together with make_axes_gridspec (for GridSpec-positioned axes) 
            # or make_axes (for non-GridSpec-positioned axes).
            #cbar = matplotlib.pyplot.colorbar(im, cax=cax, ax=ax, orientation=ori)   
            if plotinfo['Plot_Type']=='scatter':
                divider = mpl_tk.make_axes_locatable(ax)
                cax = divider.append_axes(position_label, size="5%", pad=0.1)
                cbar = matplotlib.pyplot.colorbar(im, cax=cax,ax=ax, use_gridspec=True, orientation=ori)        
            elif plotinfo['Plot_Type']=='streamplot':
                cbar = matplotlib.pyplot.colorbar(im.lines,use_gridspec=True, location=position_label)                
            else:   
                #cbar = matplotlib.pyplot.colorbar(im, cax=None,ax=ax, use_gridspec=True, location=position_label)   
                if ori=='vertical':    
                    cbar = matplotlib.pyplot.colorbar(im, cax=None,ax=ax, use_gridspec=True, location=position_label) 
                else:
                    #cbar = matplotlib.pyplot.colorbar(im, cax=None,ax=ax, use_gridspec=True, location=position_label) 
                    '''
                    fig, axt = matplotlib.pyplot.subplots(figsize=(6, 1))
                    
                    fig.colorbar(matplotlib.cm.ScalarMappable(norm=None, cmap=cmap),
                                    cax=axt, orientation='horizontal')
                                    
                    cbar = matplotlib.pyplot.colorbar(im, cax=axt,ax=ax, use_gridspec=True,orientation=ori)#location=position_label) 
                    '''
                    cbar = matplotlib.pyplot.colorbar(im, cax=None,ax=ax, use_gridspec=True,location=position_label)                 
                    # Not working :(
                    
                    #cbar = matplotlib.pyplot.colorbar(im, mappable=matplotlib.cm.ScalarMappable(norm=None, cmap=cmap),ax=ax, use_gridspec=True, orientation=ori, location=position_label)     
            
            #cbar = matplotlib.pyplot.colorbar(im,ax=ax, cmap=cmap,orientation=ori)
            #cbar = matplotlib.colorbar.ColorbarBase(ax=ax, cmap=cmap, orientation = ori)
            cbar.set_label(cm_label, rotation=rotation_label, va=label_align, fontsize=fontsize_label)
            # Colorbar [left, bottom, width, height
            #cax = fig.add_axes([0.2, 0.1, 0.6, 0.05])
            #cbar = fig.colorbar(scat, cax, orientation='horizontal')
            #cbar.set_label('This is a colorbar')
            try:
                matplotlib.pyplot.sca(ax) #make ax active axis
            except Exception as e:
                log.warning('In setting focus to plot Figure! {}'.format(e))                
        else:
            log.info('Not Showing Colormap')
        
    def exchange_labels_ticks_X_Y(self,plotinfo,only_labels=False):        
        return self.exchange_labels_ticks_from_to('x','y',plotinfo,only_labels)
    
    def exchange_labels_ticks_from_to(self,lettf,lettto,plotinfo,only_labels=False):        
        pixlabeldict=plotinfo[lettf+'label']
        piylabeldict=plotinfo[lettto+'label']
        plotinfo.update({lettf+'label':piylabeldict})
        plotinfo.update({lettto+'label':pixlabeldict})
        if only_labels==True:
            return plotinfo
        #Ticks
        xshowaxis=plotinfo['ticks_'+lettf+'show']
        yshowaxis=plotinfo['ticks_'+lettto+'show']
        plotinfo.update({'ticks_'+lettf+'show':yshowaxis})
        plotinfo.update({'ticks_'+lettto+'show':xshowaxis})

        xset_ticks=plotinfo['ticks_'+lettf+'set']
        yset_ticks=plotinfo['ticks_'+lettto+'set']
        plotinfo.update({'ticks_'+lettf+'set':yset_ticks})    
        plotinfo.update({'ticks_'+lettto+'set':xset_ticks})    

        xfontsize_ticks=plotinfo['ticks_'+lettf+'fontsize']
        yfontsize_ticks=plotinfo['ticks_'+lettto+'fontsize']
        xrotation_ticks=plotinfo['ticks_'+lettf+'rotation']
        yrotation_ticks=plotinfo['ticks_'+lettto+'rotation']
        ystepsize_ticks=plotinfo['ticks_'+lettto+'stepsize']
        xstepsize_ticks=plotinfo['ticks_'+lettf+'stepsize']

        xannotate_ticks=plotinfo['ticks_'+lettf+'annotate']
        yannotate_ticks=plotinfo['ticks_'+lettto+'annotate']        
        plotinfo.update({'ticks_'+lettto+'annotate':xannotate_ticks})
        plotinfo.update({'ticks_'+lettf+'annotate':yannotate_ticks})
        
        plotinfo.update({'ticks_'+lettf+'fontsize':yfontsize_ticks})
        plotinfo.update({'ticks_'+lettf+'rotation':yrotation_ticks})
        plotinfo.update({'ticks_'+lettf+'stepsize':ystepsize_ticks})
        plotinfo.update({'ticks_'+lettto+'fontsize':xfontsize_ticks})
        plotinfo.update({'ticks_'+lettto+'rotation':xrotation_ticks})
        plotinfo.update({'ticks_'+lettto+'stepsize':xstepsize_ticks})
        xmin_ticks=plotinfo['ticks_'+lettf+'min']
        ymin_ticks=plotinfo['ticks_'+lettto+'min']        
        xmax_ticks=plotinfo['ticks_'+lettf+'max']
        ymax_ticks=plotinfo['ticks_'+lettto+'max']
        plotinfo.update({'ticks_'+lettf+'min':ymin_ticks})        
        plotinfo.update({'ticks_'+lettf+'max':ymax_ticks})
        plotinfo.update({'ticks_'+lettto+'min':xmin_ticks})
        plotinfo.update({'ticks_'+lettto+'max':xmax_ticks})
                
        return plotinfo


    def set_legends_title(self,ax,plotinfo):
        #fig=matplotlib.pyplot.getp(ax,'figure')

        # Axis labels legends
        pixlabeldict=plotinfo['xlabel']
        piylabeldict=plotinfo['ylabel']
        pizlabeldict=plotinfo['zlabel']
        if len(pixlabeldict)>0:
            pixlabel=pixlabeldict['Label_Text']
        else:
            pixlabel=''
        if len(piylabeldict)>0:
            piylabel=piylabeldict['Label_Text']
        else:
            piylabel=''
        if len(pizlabeldict)>0:
            pizlabel=pizlabeldict['Label_Text']
        else:
            pizlabel=''                
        #matplotlib.pyplot.setp(ax,color='green')
        try:
            legend_Active=plotinfo['legend_Active']   
            legend_position=plotinfo['legend_position']        
            legend_Fontsize=plotinfo['legend_Fontsize'] 
            legend_Box_anchor=plotinfo['legend_Box_anchor']
            legend_title=plotinfo['legend_title']
            legend_title_fontsize=plotinfo['legend_title_fontsize']
            if legend_title=='':
                legend_title=None
            legend_markerfirst=plotinfo['legend_markerfirst']
            legend_frameon=plotinfo['legend_frameon']
            legend_fancybox=plotinfo['legend_fancybox']
            legend_shadow=plotinfo['legend_shadow']
            legend_framealpha=plotinfo['legend_framealpha']
            legend_facecolor=plotinfo['legend_facecolor']
            legend_edgecolor=plotinfo['legend_edgecolor']
            legend_alignment=plotinfo['legend_alignment']
            legend_ncols=plotinfo['legend_ncols']
            legend_mode=plotinfo['legend_mode']
            if pizlabel!='' and legend_Active==True:
                matplotlib.pyplot.setp(ax,label=pizlabel)                  
                matplotlib.pyplot.legend(bbox_to_anchor=(legend_Box_anchor[0], legend_Box_anchor[1]), loc=legend_position, fontsize=legend_Fontsize, title=legend_title,title_fontsize=legend_title_fontsize,markerfirst=legend_markerfirst,frameon=legend_frameon,fancybox=legend_fancybox,shadow=legend_shadow,framealpha=legend_framealpha,facecolor=legend_facecolor,edgecolor=legend_edgecolor,alignment=legend_alignment,ncols=legend_ncols,mode=legend_mode)  #locaion outside with bbox               
        except Exception as e:
            log.warning(e)
            pass
        if pixlabel!='':
            matplotlib.pyplot.xlabel(pixlabel)
        if piylabel!='':
            matplotlib.pyplot.ylabel(piylabel)
        # plotting graph
        
        # Set background color of the outer         
        # area of the plt
        self.set_out_background_color(plotinfo)
        
        bgincolor=plotinfo['BG_in_Color']          
        bgia=plotinfo['BG_in_alpha']  
        try:
            if bgincolor not in [None,'None','']:
                bgincolor=matplotlib.colors.to_rgba(bgincolor)            
                bgincolor=self.swap_color_alpha_RGBA(bgia,bgincolor)            
                #background inside color
                ax.set_facecolor(bgincolor)
            elif float(bgia)!=1:
                matplotlib.pyplot.setp(ax,alpha=float(bgia))            
        except Exception as e:
            log.error('Setting inner background color')
            log.error(e)
            pass                        

        #set title
        title=plotinfo['Title']
        matplotlib.pyplot.title(title)
        #set grids
        grids=plotinfo['Show_Grid']
        if grids==True:
            gwhich=plotinfo['Grid_which']
            gaxis=plotinfo['Grid_axis']   
            uselinestyle=plotinfo['Grid_Use_Line_style']
            if uselinestyle==True:
                acolor=plotinfo['Grid_color']#self.get_line_color(0,plotinfo)
                astyle=plotinfo['Grid_linestyle']#self.get_line_style(0,plotinfo)
                awidth=plotinfo['Grid_linewidth']#self.get_line_width(0,plotinfo)
                try:
                    matplotlib.pyplot.grid(color=acolor)
                except Exception as e:
                    log.warning('Error Grid color: {}'.format(e))
                    pass
                try:
                    matplotlib.pyplot.grid(linestyle=astyle)
                except Exception as e:
                    log.warning('Error Grid color: {}'.format(e))
                    pass
                try:
                    matplotlib.pyplot.grid(linewidth=awidth)
                except Exception as e:
                    log.warning('Error Grid color: {}'.format(e))
                    pass
            matplotlib.pyplot.grid(visible=grids,which=gwhich,axis=gaxis)
    
    def annotate_heatmap(self, im, data=None, valfmt="{x:.2f}",textcolors=("black", "white"),threshold=None, **textkw):
        """
        A function to annotate a plot.
        Parameters
        ----------
        im
            The AxesImage to be labeled.
        data
            Data used to annotate.  If None, the image's data is used.  Optional.
        valfmt
            The format of the annotations inside the plot.  This should either
            use the string format method, e.g. "$ {x:.2f}", or be a
            `matplotlib.ticker.Formatter`.  Optional.
        textcolors
            A pair of colors.  The first is used for values below a threshold,
            the second for those above.  Optional.
        threshold
            Value in data units according to which the colors from textcolors are
            applied.  If None (the default) uses the middle of the colormap as
            separation.  Optional.
        **kwargs
            All other arguments are forwarded to each call to `text` used to create
            the text labels.
        """

        if not isinstance(data, (list, numpy.ndarray)):
            data = im.get_array()

        # Normalize the threshold to the images color range.
        if threshold is not None:
            threshold = im.norm(threshold)
        else:
            threshold = im.norm(data.max())/2.

        # Set default alignment to center, but allow it to be
        # overwritten by textkw.
        kw = dict(horizontalalignment="center",
                verticalalignment="center")
        kw.update(textkw)

        # Get the formatter in case a string is supplied
        if isinstance(valfmt, str):
            valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

        # Loop over the data and create a `Text` for each "pixel".
        # Change the text's color depending on the data.
        # Show all ticks and label them with the respective list entries

        #ax.set_xticks(np.arange(len(farmers)), labels=farmers)
        #ax.set_yticks(np.arange(len(vegetables)), labels=vegetables)

        texts = []
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
                text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
                texts.append(text)
        return texts


    def set_out_background_color(self,plotinfo):
        # Set background color of the outer 
        # area of the plt
        bgocolor=plotinfo['BG_Out_Color']         
        bgoa=plotinfo['BG_out_alpha']        
        try:            
            if bgocolor not in [None,'None','']:
                bgocolor=matplotlib.colors.to_rgba(bgocolor)      
                bgocolor=self.swap_color_alpha_RGBA(bgoa,bgocolor)
                #background outside color
                matplotlib.pyplot.setp(self.FigPreview,facecolor=bgocolor)
                #matplotlib.pyplot.figure(facecolor=bgocolor)
            elif float(bgoa)!=1:
                matplotlib.pyplot.setp(self.FigPreview,alpha=float(bgoa))
                #self.FigPreview.patch.set_alpha(bgoa)            
        except Exception as e:
            log.error('Setting outter background color')
            log.error(e)
            pass


    def swap_color_alpha_RGBA(self,newalpha,RGBA):
        if type(RGBA)==type((1,2,3)):
            rgbal=list(RGBA)
            if len(rgbal)==3:
                rgbal.append(float(newalpha))
                return tuple(rgbal)
            elif len(rgbal)==4:
                rgbal[3]=float(newalpha)
                return tuple(rgbal)
            else:
                return RGBA
        else:
            return RGBA

    def get_other_plot_info(self,aplot,plotinfo):
        ppp=self.Plot_dict[aplot]
        #General
        plotinfo.update({'Plot_Type':ppp['Plot_Type']})
        plotinfo.update({'Smooth_Data':ppp['Smooth_Data']})
        plotinfo.update({'Predefined_Style':ppp['Predefined_Style']})   
        plotinfo.update({'Projection_Type':ppp['Projection']['Type']})      
        #Title
        title=ppp['Plot_Title']['Title']
        plotinfo.update({'Title':title})    
        #grids        
        plotinfo.update({'Show_Grid':ppp['Grid']['Show_Grid']})   
        plotinfo.update({'Grid_which':ppp['Grid']['Grid_which']})   
        plotinfo.update({'Grid_axis':ppp['Grid']['Grid_axis']})         
        plotinfo.update({'Grid_linewidth':ppp['Grid']['Line_format']['linewidth']})  
        plotinfo.update({'Grid_color':ppp['Grid']['Line_format']['color']})  
        plotinfo.update({'Grid_linestyle':ppp['Grid']['Line_format']['linestyle']})  
        plotinfo.update({'Grid_Use_Line_style':ppp['Grid']['Use_Line_style']})   
        #Labels
        axis_info=plotinfo['axis_info']        
        xlabel=ppp['Axis_X']['Axis_Label']
        ylabel=ppp['Axis_Y']['Axis_Label']
        zlabel=ppp['Axis_Z']['Axis_Label']
        plotinfo=self.set_labels_from_axis_info(plotinfo,axis_info,xlabel,ylabel,zlabel,['x','y','z'],False)

        #Labels
        #Add_axis_info=plotinfo['Add_axis_info']        
        ulabel=ppp['Additional']['Axis_U']['Axis_Label']
        vlabel=ppp['Additional']['Axis_V']['Axis_Label']
        wlabel=ppp['Additional']['Axis_W']['Axis_Label']
        plotinfo=self.set_labels_from_axis_info(plotinfo,[1,2,3],ulabel,vlabel,wlabel,['u','v','w'],True)
          
        #Legends
        plotinfo.update({'legend_position':ppp['Plot_Legend']['Position']})        
        plotinfo.update({'legend_Fontsize':ppp['Plot_Legend']['Fontsize']})   
        plotinfo.update({'legend_Box_anchor':ppp['Plot_Legend']['Box_anchor']})   
        plotinfo.update({'legend_Active':ppp['Plot_Legend']['Legend_Active']})

        plotinfo.update({'legend_title':ppp['Plot_Legend']['title']})
        plotinfo.update({'legend_title_fontsize':ppp['Plot_Legend']['title_fontsize']})
        #plotinfo.update({'legend_weight':ppp['Plot_Legend']['weight']})
        plotinfo.update({'legend_markerfirst':ppp['Plot_Legend']['markerfirst']})
        plotinfo.update({'legend_frameon':ppp['Plot_Legend']['frameon']})
        plotinfo.update({'legend_fancybox':ppp['Plot_Legend']['fancybox']})
        plotinfo.update({'legend_shadow':ppp['Plot_Legend']['shadow']})
        plotinfo.update({'legend_framealpha':ppp['Plot_Legend']['framealpha']})
        plotinfo.update({'legend_facecolor':ppp['Plot_Legend']['facecolor']})
        plotinfo.update({'legend_edgecolor':ppp['Plot_Legend']['edgecolor']})
        plotinfo.update({'legend_alignment':ppp['Plot_Legend']['alignment']})
        plotinfo.update({'legend_ncols':ppp['Plot_Legend']['ncols']})
        plotinfo.update({'legend_mode':ppp['Plot_Legend']['mode']})

        #Ticks
        xAxis_Scale_Range=ppp['Axis_X']['Axis_Scale_Range']
        yAxis_Scale_Range=ppp['Axis_Y']['Axis_Scale_Range']
        zAxis_Scale_Range=ppp['Axis_Z']['Axis_Scale_Range']
        xAuto_Scale=ppp['Axis_X']['Axis_Auto_Scale']
        yAuto_Scale=ppp['Axis_Y']['Axis_Auto_Scale']
        zAuto_Scale=ppp['Axis_Z']['Axis_Auto_Scale']
        #Autoscale to data
        if xAuto_Scale==True:
            mmm=plotinfo['dfaxis_x_fm']            
            xAxis_Scale_Range=[numpy.amin(mmm),numpy.amax(mmm)]
            log.info('{} X axis auto scaled to {}'.format(aplot,xAxis_Scale_Range))
        if yAuto_Scale==True:
            mmm=plotinfo['dfaxis_y_fm']
            yAxis_Scale_Range=[numpy.amin(mmm),numpy.amax(mmm)]
            log.info('{} Y axis auto scaled to {}'.format(aplot,yAxis_Scale_Range))
        if zAuto_Scale==True:
            mmm=plotinfo['dfaxis_z_fm']
            zAxis_Scale_Range=[numpy.amin(mmm),numpy.amax(mmm)]   
            log.info('{} Z axis auto scaled to {}'.format(aplot,zAxis_Scale_Range)) 
        
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,axis_info,'Axis_X',xAxis_Scale_Range)
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,axis_info,'Axis_Y',yAxis_Scale_Range)
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,axis_info,'Axis_Z',zAxis_Scale_Range)
        
        
        #Lines format
        linewidth=ppp['Lines']['linewidth']
        linecolor=ppp['Lines']['color']
        linestyle=ppp['Lines']['linestyle']
        dash_capstyle=ppp['Lines']['dash_capstyle']
        dash_joinstyle=ppp['Lines']['dash_joinstyle']
        drawstyle=ppp['Lines']['drawstyle']
        line_usemarkers=ppp['Lines']['Line_Marker']['Use_Markers']
        linemarkertype=ppp['Lines']['Line_Marker']['Marker_Type']        
        linemarkersize=ppp['Lines']['Line_Marker']['Marker_Size']
        linemarkeredgecolor=ppp['Lines']['Line_Marker']['markeredgecolor']
        linemarkeredgewidth=ppp['Lines']['Line_Marker']['markeredgewidth']
        linemarkerfacecolor=ppp['Lines']['Line_Marker']['markerfacecolor']
        linemarkerfacecoloralt=ppp['Lines']['Line_Marker']['markerfacecoloralt']
        lineComplete_Vectors=ppp['Lines']['Complete_Vectors']
        plotinfo.update({'Line_Complete_Vectors':lineComplete_Vectors}) 
        plotinfo.update({'Line_Marker_Type':linemarkertype})                
        plotinfo.update({'Line_Marker_Size':linemarkersize})
        plotinfo.update({'markeredgecolor':linemarkeredgecolor})
        plotinfo.update({'markeredgewidth':linemarkeredgewidth})
        plotinfo.update({'markerfacecolor':linemarkerfacecolor})
        plotinfo.update({'markerfacecoloralt':linemarkerfacecoloralt})
        plotinfo.update({'linewidth':linewidth})                    
        plotinfo.update({'linecolor':linecolor})                    
        plotinfo.update({'linestyle':linestyle})                    
        plotinfo.update({'dash_capstyle':dash_capstyle})                    
        plotinfo.update({'dash_joinstyle':dash_joinstyle})                    
        plotinfo.update({'drawstyle':drawstyle})   
        plotinfo.update({'lineusemarkers':line_usemarkers})     
        #Hist        
        plotinfo.update({'hist_bins':ppp['Hist']['bins']}) 
        plotinfo.update({'hist_bins2':ppp['Hist']['bins2']}) 
        plotinfo.update({'hist_density':ppp['Hist']['density']})
        plotinfo.update({'hist_cumulative':ppp['Hist']['cumulative']})
        plotinfo.update({'hist_type':ppp['Hist']['histtype']})
        plotinfo.update({'hist_align':ppp['Hist']['hist_align']})
        plotinfo.update({'hist_orientation':ppp['Hist']['orientation']})
        plotinfo.update({'hist_relative_width':ppp['Hist']['relative_width']})
        plotinfo.update({'hist_log':ppp['Hist']['log']}) 
        plotinfo.update({'hist_stacked':ppp['Hist']['stacked']})
        plotinfo.update({'hist_Use_U_V_weights':ppp['Hist']['Use_U_V_weights']})
        #Quiver        
        plotinfo.update({'qui_angles':ppp['Quiver']['angles']}) 
        plotinfo.update({'qui_pivot':ppp['Quiver']['pivot']}) 
        plotinfo.update({'qui_units':ppp['Quiver']['units']}) 
        plotinfo.update({'qui_scale':ppp['Quiver']['inverse_scale']}) 
        plotinfo.update({'qui_scale_units':ppp['Quiver']['scale_units']}) 
        plotinfo.update({'qui_color':ppp['Quiver']['color']}) 
        plotinfo.update({'qui_arr_width':ppp['Quiver']['arrows']['width']}) 
        plotinfo.update({'qui_arr_headwidth':ppp['Quiver']['arrows']['headwidth']}) 
        plotinfo.update({'qui_arr_headlength':ppp['Quiver']['arrows']['headlength']}) 
        plotinfo.update({'qui_arr_headaxislength':ppp['Quiver']['arrows']['headaxislength']}) 
        plotinfo.update({'qui_arr_minshaft':ppp['Quiver']['arrows']['minshaft']}) 
        plotinfo.update({'qui_arr_minlength':ppp['Quiver']['arrows']['minlength']}) 
        #barbs        
        plotinfo.update({'barbs_length':ppp['Barbs']['length']}) 
        plotinfo.update({'barbs_pivot':ppp['Barbs']['pivot']}) 
        plotinfo.update({'barbs_barbcolor':ppp['Barbs']['barbcolor']}) 
        plotinfo.update({'barbs_flagcolor':ppp['Barbs']['flagcolor']}) 
        plotinfo.update({'barbs_sizes_spacing':ppp['Barbs']['sizes']['spacing']}) 
        plotinfo.update({'barbs_sizes_height':ppp['Barbs']['sizes']['height']}) 
        plotinfo.update({'barbs_sizes_width':ppp['Barbs']['sizes']['width']}) 
        plotinfo.update({'barbs_sizes_emptybarb':ppp['Barbs']['sizes']['emptybarb']}) 
        plotinfo.update({'barbs_fill_empty':ppp['Barbs']['fill_empty']}) 
        plotinfo.update({'barbs_rounding':ppp['Barbs']['rounding']}) 
        plotinfo.update({'barbs_barb_increments_half':ppp['Barbs']['barb_increments']['half']}) 
        plotinfo.update({'barbs_barb_increments_full':ppp['Barbs']['barb_increments']['full']}) 
        plotinfo.update({'barbs_barb_increments_flag':ppp['Barbs']['barb_increments']['flag']}) 
        #Stream        
        plotinfo.update({'stream_density_xy':ppp['Stream']['density_xy']}) 
        plotinfo.update({'stream_start_points':ppp['Stream']['start_points']}) 
        plotinfo.update({'stream_linewidth':ppp['Stream']['linewidth']}) 
        plotinfo.update({'stream_zorder':ppp['Stream']['zorder']}) 
        plotinfo.update({'stream_minmaxlength':ppp['Stream']['minmaxlength']}) 
        plotinfo.update({'stream_color':ppp['Stream']['color']}) 
        plotinfo.update({'stream_integration_direction':ppp['Stream']['integration_direction']}) 
        plotinfo.update({'stream_broken_streamlines':ppp['Stream']['broken_streamlines']}) 

        plotinfo.update({'stream_arrowstyle':ppp['Stream']['arrows']['arrowstyle']}) 
        plotinfo.update({'stream_arrowsize':ppp['Stream']['arrows']['arrowsize']})
        #Eventplot        
        plotinfo.update({'event_orientation':ppp['Eventplot']['orientation']})
        plotinfo.update({'event_lineoffsets':ppp['Eventplot']['lineoffsets']})
        plotinfo.update({'event_linelengths':ppp['Eventplot']['linelengths']})
        plotinfo.update({'event_linewidths':ppp['Eventplot']['linewidths']})
        plotinfo.update({'event_colors':ppp['Eventplot']['colors']})
        plotinfo.update({'event_linestyles':ppp['Eventplot']['linestyles']})
        #Stackplot
        plotinfo.update({'stack_baseline':ppp['Stackplot']['baseline']})
        plotinfo.update({'stack_colors':ppp['Stackplot']['colors']})
        #Stairs
        #:{'edges':[None],'orientation':'vertical','baseline':[0.0],'Fill':False},
        plotinfo.update({'stairs_baseline':ppp['Stairs']['baseline']})        
        plotinfo.update({'stairs_fill':ppp['Stairs']['Fill']})
        plotinfo.update({'stairs_orientation':ppp['Stairs']['orientation']})        
        plotinfo.update({'stairs_edges':ppp['Stairs']['edges']})
        plotinfo.update({'stairs_Use_Lines_style':ppp['Stairs']['Use_Lines_style']})
        #plotinfo.update({'stairs_colors':ppp['Stairs']['colors']})
        #Pie
        plotinfo.update({'pie_explode':ppp['Pie']['explode']})
        plotinfo.update({'pie_colors':ppp['Pie']['colors']})
        plotinfo.update({'pie_autopct':ppp['Pie']['autopct']})
        plotinfo.update({'pie_pctdistance':ppp['Pie']['pctdistance']})
        plotinfo.update({'pie_shadow':ppp['Pie']['shadow']})
        plotinfo.update({'pie_labeldistance':ppp['Pie']['labeldistance']})
        plotinfo.update({'pie_radius':ppp['Pie']['radius']})
        plotinfo.update({'pie_startangle':ppp['Pie']['startangle']})
        plotinfo.update({'pie_counterclock':ppp['Pie']['counterclock']})
        plotinfo.update({'pie_textprops':ppp['Pie']['textprops']})
        plotinfo.update({'pie_center':ppp['Pie']['center']})
        plotinfo.update({'pie_frame':ppp['Pie']['frame']})
        plotinfo.update({'pie_rotatelabels':ppp['Pie']['rotatelabels']})
        plotinfo.update({'pie_normalize':ppp['Pie']['normalize']})
        plotinfo.update({'pie_wedgeprops':ppp['Pie']['wedgeprops']})
        #Violin
        plotinfo.update({'violin_positions_key':ppp['Violinplot']['positions_key']})
        plotinfo.update({'violin_vert':ppp['Violinplot']['vert']})
        plotinfo.update({'violin_widths':ppp['Violinplot']['widths']})
        plotinfo.update({'violin_showmeans':ppp['Violinplot']['showmeans']})
        plotinfo.update({'violin_showextrema':ppp['Violinplot']['showextrema']})
        plotinfo.update({'violin_showmedians':ppp['Violinplot']['showmedians']})
        plotinfo.update({'violin_quantiles':ppp['Violinplot']['quantiles']})
        plotinfo.update({'violin_points':ppp['Violinplot']['points']})
        plotinfo.update({'violin_bw_method':ppp['Violinplot']['bw_method']})
        plotinfo.update({'violin_bw_method_KDE':ppp['Violinplot']['bw_method_KDE']})
        #Boxplot
        plotinfo.update({'boxplot_positions':ppp['Boxplot']['positions']})
        plotinfo.update({'boxplot_widths':ppp['Boxplot']['widths']})
        plotinfo.update({'boxplot_notch':ppp['Boxplot']['notch']})
        plotinfo.update({'boxplot_sym':ppp['Boxplot']['sym']})
        plotinfo.update({'boxplot_orientation':ppp['Boxplot']['orientation']})
        plotinfo.update({'boxplot_whis':ppp['Boxplot']['whis']})
        plotinfo.update({'boxplot_bootstrap':ppp['Boxplot']['bootstrap']})
        plotinfo.update({'boxplot_usermedians':ppp['Boxplot']['usermedians']})
        plotinfo.update({'boxplot_patch_artist':ppp['Boxplot']['patch_artist']})
        plotinfo.update({'boxplot_conf_intervals':ppp['Boxplot']['conf_intervals']})
        plotinfo.update({'boxplot_meanline':ppp['Boxplot']['meanline']})
        plotinfo.update({'boxplot_showmeans':ppp['Boxplot']['showmeans']})
        plotinfo.update({'boxplot_showcaps':ppp['Boxplot']['showcaps']})
        plotinfo.update({'boxplot_showbox':ppp['Boxplot']['showbox']})
        plotinfo.update({'boxplot_showfliers':ppp['Boxplot']['showfliers']})
        plotinfo.update({'boxplot_manage_ticks':ppp['Boxplot']['manage_ticks']})
        plotinfo.update({'boxplot_autorange':ppp['Boxplot']['autorange']})
        plotinfo.update({'boxplot_zorder':ppp['Boxplot']['zorder']})
        plotinfo.update({'boxplot_boxprops_color':ppp['Boxplot']['boxprops']['color']})
        plotinfo.update({'boxplot_boxprops_linestyle':ppp['Boxplot']['boxprops']['linestyle']})
        plotinfo.update({'boxplot_boxprops_linewidth':ppp['Boxplot']['boxprops']['linewidth']})
        
        plotinfo.update({'boxplot_flierprops_marker':ppp['Boxplot']['flierprops']['marker']})
        plotinfo.update({'boxplot_flierprops_markerfacecolor':ppp['Boxplot']['flierprops']['markerfacecolor']})
        plotinfo.update({'boxplot_flierprops_markersize':ppp['Boxplot']['flierprops']['markersize']})
        plotinfo.update({'boxplot_flierprops_linestyle':ppp['Boxplot']['flierprops']['linestyle']})
        plotinfo.update({'boxplot_flierprops_markeredgecolor':ppp['Boxplot']['flierprops']['markeredgecolor']})
        plotinfo.update({'boxplot_flierprops_linewidth':ppp['Boxplot']['flierprops']['linewidth']})        

        plotinfo.update({'boxplot_medianprops_color':ppp['Boxplot']['medianprops']['color']})
        plotinfo.update({'boxplot_medianprops_linestyle':ppp['Boxplot']['medianprops']['linestyle']})
        plotinfo.update({'boxplot_medianprops_linewidth':ppp['Boxplot']['medianprops']['linewidth']})

        plotinfo.update({'boxplot_whiskerprops_color':ppp['Boxplot']['whiskerprops']['color']})
        plotinfo.update({'boxplot_whiskerprops_linestyle':ppp['Boxplot']['whiskerprops']['linestyle']})
        plotinfo.update({'boxplot_whiskerprops_linewidth':ppp['Boxplot']['whiskerprops']['linewidth']})

        plotinfo.update({'boxplot_meanprops_color':ppp['Boxplot']['meanprops']['color']})
        plotinfo.update({'boxplot_meanprops_marker':ppp['Boxplot']['meanprops']['marker']})
        plotinfo.update({'boxplot_meanprops_markerfacecolor':ppp['Boxplot']['meanprops']['markerfacecolor']})
        plotinfo.update({'boxplot_meanprops_markersize':ppp['Boxplot']['meanprops']['markersize']})
        plotinfo.update({'boxplot_meanprops_linestyle':ppp['Boxplot']['meanprops']['linestyle']})
        plotinfo.update({'boxplot_meanprops_markeredgecolor':ppp['Boxplot']['meanprops']['markeredgecolor']})
        plotinfo.update({'boxplot_meanprops_linewidth':ppp['Boxplot']['meanprops']['linewidth']})
       
        plotinfo.update({'boxplot_capprops_color':ppp['Boxplot']['capprops']['color']})
        plotinfo.update({'boxplot_capprops_linestyle':ppp['Boxplot']['capprops']['linestyle']})
        plotinfo.update({'boxplot_capprops_linewidth':ppp['Boxplot']['capprops']['linewidth']})
        #plotinfo.update({'boxplot_capprops_capsize':ppp['Boxplot']['capprops']['capsize']})
        plotinfo.update({'boxplot_capprops_capwidths':ppp['Boxplot']['capprops']['capwidths']})
        # Spectrum
        plotinfo.update({'spectrum_NFFT':ppp['Spectrum']['NFFT']})
        plotinfo.update({'spectrum_Fs':ppp['Spectrum']['Fs']})
        plotinfo.update({'spectrum_Fc':ppp['Spectrum']['Fc']})
        plotinfo.update({'spectrum_detrend':ppp['Spectrum']['detrend']})
        plotinfo.update({'spectrum_window':ppp['Spectrum']['window']})
        plotinfo.update({'spectrum_noverlap':ppp['Spectrum']['noverlap']})
        plotinfo.update({'spectrum_pad_to':ppp['Spectrum']['pad_to']})
        plotinfo.update({'spectrum_sides':ppp['Spectrum']['sides']})
        plotinfo.update({'spectrum_scale_by_freq':ppp['Spectrum']['scale_by_freq']})
        plotinfo.update({'spectrum_mode':ppp['Spectrum']['mode']})
        plotinfo.update({'spectrum_scale':ppp['Spectrum']['scale']})
        plotinfo.update({'spectrum_scipy_windowtype':ppp['Spectrum']['scipy']['windowtype']})
        plotinfo.update({'spectrum_scipy_parameters':ppp['Spectrum']['scipy']['parameters']})
        
        #Layout
        numplots=len(self.Plot_dict)
        layout=ppp['Layout_Position_HV']
        layoutS=ppp['Layout_Size_RowCol']
        layout=self.correct_layout(numplots,layout,layoutS)       
        plotinfo.update({'layoutH':layout[0]})
        plotinfo.update({'layoutV':layout[1]})
        
        plotinfo.update({'layoutSizeR':layoutS[1]})
        plotinfo.update({'layoutSizeC':layoutS[0]})
        #Markers
        markertype=ppp['Plot_Marker']['Marker_Type']
        if 'int_' in markertype:
            markertype=int(markertype.strip('int_'))
        markersize=ppp['Plot_Marker']['Marker_Size']
        plotinfo.update({'Plot_Marker_Type':markertype})                
        plotinfo.update({'Plot_Marker_Size':markersize}) 
        #Background image
        imagepath=ppp['Background']['BG_Path_File']
        showaxis=ppp['Background']['Show_Axis']        
        imaspect=ppp['Background']['BG_Aspect']        
        plotinfo.update({'BG_Out_Color':ppp['Background']['BG_Out_Color']})
        plotinfo.update({'BG_in_Color':ppp['Background']['BG_in_Color']})
        plotinfo.update({'BG_out_alpha':ppp['Background']['BG_out_alpha']})
        plotinfo.update({'BG_in_alpha':ppp['Background']['BG_in_alpha']})
        plotinfo.update({'Show_Axis':showaxis})      
        plotinfo.update({'BG_Aspect':imaspect})
        plotinfo.update({'BG_Path_File':None}) 
        if imagepath!='':
            file_exists = os.path.exists(imagepath)        
            if file_exists==True:
                log.info('{} Image File path found:\n{}'.format(aplot,imagepath))
                plotinfo.update({'BG_Path_File':imagepath}) 
            else:
                log.info('{} Image File path Not found:\n{}'.format(aplot,imagepath))
        #Colormap 
        if ppp['Colormap']['Colormap_Auto_Range']==True:
            cmrange=[plotinfo['ticks_zmin'],plotinfo['ticks_zmax']] #set new range if auto range
            plotinfo.update({'Colormap_Range':cmrange}) 
            log.info('{} Colormap auto scaled to {}'.format(aplot,cmrange))        
        cm_label=plotinfo['zlabel']['Label_Text']
        cm_position_label=ppp['Colormap']['Colormap_Label']['Colormap_Position']
        cm_label_align=ppp['Colormap']['Colormap_Label']['Colormap_Label_align']
        plotinfo.update({'cm_label':cm_label})
        cm_Colormap_Show_Label=ppp['Colormap']['Colormap_Label']['Colormap_Show_Label']
        cm_fontsize_label=ppp['Colormap']['Colormap_Label']['Fontsize_Label']
        cm_rotation_label=ppp['Colormap']['Colormap_Label']['Rotation_Label']        
        plotinfo.update({'cm_Colormap_Show_Label':cm_Colormap_Show_Label})
        plotinfo.update({'cm_label_align':cm_label_align})        
        plotinfo.update({'cm_fontsize_label':cm_fontsize_label})
        plotinfo.update({'cm_rotation_label':cm_rotation_label})
        plotinfo.update({'cm_position_label':cm_position_label})
        #Contour        
        plotinfo.update({'cont_Show_value_Labels':ppp['Contour']['Show_value_Labels']})
        plotinfo.update({'cont_value_Labels_size':ppp['Contour']['value_Labels_size']})
        plotinfo.update({'cont_Number_of_levels':ppp['Contour']['Number_of_levels']})
        plotinfo.update({'cont_Use_specific_Values':ppp['Contour']['Use_specific_Values']})
        cont_Use_values=ppp['Contour']['Use_values']        
        plotinfo.update({'cont_Use_values':cont_Use_values})
        plotinfo.update({'cont_Use_colors':ppp['Contour']['Use_colors']})
        #bar
        plotinfo.update({'bar_Use_colors':ppp['Bar']['Use_colors']})        
        plotinfo.update({'bar_width':ppp['Bar']['Bar_width']})
        plotinfo.update({'bar_Use_Lines_style':ppp['Bar']['Use_Lines_style']})
        plotinfo.update({'bar_logy':ppp['Bar']['logy']})
        plotinfo.update({'bar_align':ppp['Bar']['align']})
        #Error bars        
        if plotinfo['Plot_Type']=='errorbar':
            plotinfo.update({'Use_Err_bars':True})  
        else:      
            plotinfo.update({'Use_Err_bars':ppp['Error_bars']['Use_Err_bars']})
        plotinfo.update({'Err_Y_Use_key':ppp['Error_bars']['Err_Y_Use_key']})
        plotinfo.update({'Err_X_Use_key':ppp['Error_bars']['Err_X_Use_key']})
        plotinfo.update({'Err_bar_ecolor':ppp['Error_bars']['ecolor']})
        plotinfo.update({'Err_bar_capsize':ppp['Error_bars']['capsize']})
        plotinfo.update({'Err_bar_fmt':ppp['Error_bars']['fmt']})
        plotinfo.update({'Err_bar_capthick':ppp['Error_bars']['capthick']})
        plotinfo.update({'Err_bar_barsabove':ppp['Error_bars']['barsabove']})
        plotinfo.update({'Err_bar_elinewidth':ppp['Error_bars']['elinewidth']})
        plotinfo.update({'Err_bar_errorevery_X':ppp['Error_bars']['errorevery_X']})
        plotinfo.update({'Err_bar_errorevery_Y':ppp['Error_bars']['errorevery_Y']})
        plotinfo.update({'Err_bar_lolims':ppp['Error_bars']['lolims']})
        plotinfo.update({'Err_bar_xlolims':ppp['Error_bars']['xlolims']})
        plotinfo.update({'Err_bar_uplims':ppp['Error_bars']['uplims']})
        plotinfo.update({'Err_bar_xuplims':ppp['Error_bars']['xuplims']})
        # Stem        
        plotinfo.update({'Stem_bottom':ppp['Stem']['bottom']})
        plotinfo.update({'Stem_orientation':ppp['Stem']['orientation']})
        plotinfo.update({'Stem_Use_Lines_style':ppp['Stem']['Use_Lines_style']})
        plotinfo.update({'Stem_linefmt':ppp['Stem']['linefmt']})
        plotinfo.update({'Stem_markerfmt':ppp['Stem']['markerfmt']})
        plotinfo.update({'Stem_basefmt':ppp['Stem']['basefmt']})
        # Reference Lines        
        plotinfo.update({'RL_Show_Ref_Lines':ppp['Reference_Lines']['Show_Ref_Lines']})
        plotinfo.update({'RL_Horizontal_Show':ppp['Reference_Lines']['Horizontal']['Show_XLines']})
        plotinfo.update({'RL_Horizontal_points':ppp['Reference_Lines']['Horizontal']['Y_points']})
        plotinfo.update({'RL_Horizontal_UseRange':ppp['Reference_Lines']['Horizontal']['Use_X_Range']})
        plotinfo.update({'RL_Horizontal_MinMax':ppp['Reference_Lines']['Horizontal']['X_Min_Max']})
        plotinfo.update({'RL_Horizontal_linewidth':ppp['Reference_Lines']['Horizontal']['Line_format']['linewidth']})
        plotinfo.update({'RL_Horizontal_linestyle':ppp['Reference_Lines']['Horizontal']['Line_format']['linestyle']})
        plotinfo.update({'RL_Horizontal_color':ppp['Reference_Lines']['Horizontal']['Line_format']['color']})
        
        plotinfo.update({'RL_Vertical_Show':ppp['Reference_Lines']['Vertical']['Show_YLines']})
        plotinfo.update({'RL_Vertical_points':ppp['Reference_Lines']['Vertical']['X_points']})
        plotinfo.update({'RL_Vertical_UseRange':ppp['Reference_Lines']['Vertical']['Use_Y_Range']})
        plotinfo.update({'RL_Vertical_MinMax':ppp['Reference_Lines']['Vertical']['Y_Min_Max']})
        plotinfo.update({'RL_Vertical_linewidth':ppp['Reference_Lines']['Vertical']['Line_format']['linewidth']})
        plotinfo.update({'RL_Vertical_linestyle':ppp['Reference_Lines']['Vertical']['Line_format']['linestyle']})
        plotinfo.update({'RL_Vertical_color':ppp['Reference_Lines']['Vertical']['Line_format']['color']})
        
        plotinfo.update({'RL_Radial_Show':ppp['Reference_Lines']['Radial']['Show_EquiLines']})
        plotinfo.update({'RL_Radial_points':ppp['Reference_Lines']['Radial']['Equi_points']})
        plotinfo.update({'RL_Radial_UseRange':ppp['Reference_Lines']['Radial']['Use_Ang_Range']})
        plotinfo.update({'RL_Radial_MinMax':ppp['Reference_Lines']['Radial']['Ang_Min_Max']})
        plotinfo.update({'RL_Radial_Center':ppp['Reference_Lines']['Radial']['Center_coord']})
        plotinfo.update({'RL_Radial_linewidth':ppp['Reference_Lines']['Radial']['Line_format']['linewidth']})
        plotinfo.update({'RL_Radial_linestyle':ppp['Reference_Lines']['Radial']['Line_format']['linestyle']})
        plotinfo.update({'RL_Radial_color':ppp['Reference_Lines']['Radial']['Line_format']['color']})
        plotinfo.update({'RL_Radial_ini_angle':ppp['Reference_Lines']['Radial']['ini_angle']})
        

        plotinfo.update({'RL_Angular_Show':ppp['Reference_Lines']['Angular']['Show_RLines']})
        plotinfo.update({'RL_Angular_points':ppp['Reference_Lines']['Angular']['Angles']})
        plotinfo.update({'RL_Angular_UseRange':ppp['Reference_Lines']['Angular']['Use_R_Range']})
        plotinfo.update({'RL_Angular_MinMax':ppp['Reference_Lines']['Angular']['R_Min_Max']})
        plotinfo.update({'RL_Angular_linewidth':ppp['Reference_Lines']['Angular']['Line_format']['linewidth']})
        plotinfo.update({'RL_Angular_linestyle':ppp['Reference_Lines']['Angular']['Line_format']['linestyle']})
        plotinfo.update({'RL_Angular_color':ppp['Reference_Lines']['Angular']['Line_format']['color']})
        
        return plotinfo
    def set_labels_from_axis_info(self,plotinfo,axis_info,xlabel_dict,ylabel_dict,zlabel_dict,axlett=['x','y','z'],direct=False):                
        if direct==False:
            if axis_info==[1,2,3]:
                plotinfo.update({axlett[0]+'label':xlabel_dict})
                plotinfo.update({axlett[1]+'label':ylabel_dict})
                plotinfo.update({axlett[2]+'label':zlabel_dict})
            elif axis_info==[1,2,0]:
                plotinfo.update({axlett[0]+'label':xlabel_dict})
                plotinfo.update({axlett[1]+'label':ylabel_dict})
                plotinfo.update({axlett[2]+'label':ylabel_dict})   
            elif axis_info==[1,0,2]:
                plotinfo.update({axlett[0]+'label':xlabel_dict})
                plotinfo.update({axlett[1]+'label':zlabel_dict})
                plotinfo.update({axlett[2]+'label':zlabel_dict})  
            elif axis_info==[0,1,2]:
                plotinfo.update({axlett[0]+'label':ylabel_dict})
                plotinfo.update({axlett[1]+'label':zlabel_dict})
                plotinfo.update({axlett[2]+'label':zlabel_dict}) 
            elif axis_info==[1,0,0]:
                plotinfo.update({axlett[0]+'label':{}})
                plotinfo.update({axlett[1]+'label':xlabel_dict})
                plotinfo.update({axlett[2]+'label':xlabel_dict}) 
            elif axis_info==[0,1,0]:
                plotinfo.update({axlett[0]+'label':{}})
                plotinfo.update({axlett[1]+'label':ylabel_dict})
                plotinfo.update({axlett[2]+'label':ylabel_dict}) 
            elif axis_info==[0,0,1]:
                plotinfo.update({axlett[0]+'label':{}})
                plotinfo.update({axlett[1]+'label':zlabel_dict})
                plotinfo.update({axlett[2]+'label':zlabel_dict}) 
            else:
                plotinfo.update({axlett[0]+'label':{}})
                plotinfo.update({axlett[1]+'label':{}})
                plotinfo.update({axlett[2]+'label':{}}) 
        else:
            labeldict=[xlabel_dict,ylabel_dict,zlabel_dict]
            
            for iii,axi in enumerate(axis_info):
                #log.info('axis_info {} Setting labels ->{}label {}=?123 -> {}'.format(axis_info,axlett[iii],axi,labeldict[iii]))
                if axi in [1,2,3]:
                    plotinfo.update({axlett[iii]+'label':labeldict[iii]}) 
                else:
                    plotinfo.update({axlett[iii]+'label':{}}) 
        
        return plotinfo

    def get_Axis_letter_number_from_Name(self,AxisName):
        if AxisName in ['Axis_X','Axis_Y','Axis_Z']:  
            if AxisName=='Axis_X':
                selaxis=1  
                sellett='x' 
            elif AxisName=='Axis_Y':
                selaxis=2
                sellett='y'
            elif AxisName=='Axis_Z':
                selaxis=3 
                sellett='z' 
            else:
                selaxis=0 
                sellett=''  
            axinfo=['x','y','z']   
            axnameinfo=['Axis_X','Axis_Y','Axis_Z']
        elif AxisName in ['Axis_U','Axis_V','Axis_W']:  
            if AxisName=='Axis_U':
                selaxis=1 
                sellett='u'  
            elif AxisName=='Axis_V':
                selaxis=2
                sellett='v'
            elif AxisName=='Axis_W':
                selaxis=3 
                sellett='w'  
            else:
                selaxis=0 
                sellett=''
            axinfo=['u','v','w']
            axnameinfo=['Axis_U','Axis_V','Axis_W']
        else:
            return None,None,None,None    
        return selaxis,sellett,axinfo,axnameinfo

    def set_Tick_from_axis_info(self,ppp,plotinfo,axis_info,AxisName,Axis_Scale_Range): 
        selaxis,sellett,axinfo,axnameinfo=self.get_Axis_letter_number_from_Name(AxisName)         
        if selaxis==None:
            return plotinfo

        numzeros=0
        for axi in axis_info:
            if axi==0:
                numzeros=numzeros+1
        #this puts the information in the correct column
        for iii,axi in enumerate(axis_info):
                index=iii
                axlett=axinfo[index]
                axname=axnameinfo[index]
                #print(index,axlett,axname,axis_info,'-->',axi,'==',selaxis,'?')
                if 'x' in axinfo:
                    Axis_Show_Ticks=ppp[axname]['Axis_Show_Ticks']
                    set_ticks=ppp[axname]['Axis_Ticks']['Set_Tick']        
                    rotation_ticks=ppp[axname]['Axis_Ticks']['Rotation_Tick']
                    stepsize_ticks=ppp[axname]['Axis_Ticks']['Step_Size_Tick']
                    fontsize_ticks=ppp[axname]['Axis_Ticks']['Fontsize_Tick']
                    annotate_ticks=ppp[axname]['Axis_Ticks']['Annotation_Data_Key']
                if 'u' in axinfo:
                    Axis_Show_Ticks=ppp['Additional'][axname]['Axis_Show_Ticks']
                    set_ticks=ppp['Additional'][axname]['Axis_Ticks']['Set_Tick']        
                    rotation_ticks=ppp['Additional'][axname]['Axis_Ticks']['Rotation_Tick']
                    stepsize_ticks=ppp['Additional'][axname]['Axis_Ticks']['Step_Size_Tick']
                    fontsize_ticks=ppp['Additional'][axname]['Axis_Ticks']['Fontsize_Tick']
                    annotate_ticks=ppp['Additional'][axname]['Axis_Ticks']['Annotation_Data_Key']
                if axi!=0 and axi==selaxis:                                    
                    #print('came in')
                    plotinfo.update({'ticks_'+sellett+'show':Axis_Show_Ticks})
                    plotinfo.update({'ticks_'+sellett+'set':set_ticks})        
                    plotinfo.update({'ticks_'+sellett+'fontsize':fontsize_ticks})
                    plotinfo.update({'ticks_'+sellett+'rotation':rotation_ticks})
                    plotinfo.update({'ticks_'+sellett+'stepsize':stepsize_ticks})
                    plotinfo.update({'ticks_'+sellett+'annotate':annotate_ticks})
                    plotinfo.update({'ticks_'+sellett+'min':Axis_Scale_Range[0]})        
                    plotinfo.update({'ticks_'+sellett+'max':Axis_Scale_Range[1]})
                elif axi==0 and selaxis==1: #fill with x axis info when noneused
                    plotinfo.update({'ticks_'+axlett+'show':Axis_Show_Ticks})
                    plotinfo.update({'ticks_'+axlett+'set':False})        
                    plotinfo.update({'ticks_'+axlett+'fontsize':fontsize_ticks})
                    plotinfo.update({'ticks_'+axlett+'rotation':rotation_ticks})
                    plotinfo.update({'ticks_'+axlett+'stepsize':stepsize_ticks})
                    plotinfo.update({'ticks_'+axlett+'annotate':annotate_ticks})
                    plotinfo.update({'ticks_'+axlett+'min':Axis_Scale_Range[0]})        
                    plotinfo.update({'ticks_'+axlett+'max':Axis_Scale_Range[1]})

        if numzeros==2 and selaxis==1: #cases [1,0,0],[0,1,0],[0,0,1]                   
            #set x values in y
            plotinfo.update({'ticks_'+axinfo[1]+'show':plotinfo['ticks_'+sellett+'show']})
            plotinfo.update({'ticks_'+axinfo[1]+'set':plotinfo['ticks_'+sellett+'set']})
            plotinfo.update({'ticks_'+axinfo[1]+'fontsize':plotinfo['ticks_'+sellett+'fontsize']})
            plotinfo.update({'ticks_'+axinfo[1]+'rotation':plotinfo['ticks_'+sellett+'rotation']})
            plotinfo.update({'ticks_'+axinfo[1]+'stepsize':plotinfo['ticks_'+sellett+'stepsize']})
            plotinfo.update({'ticks_'+axinfo[1]+'annotate':plotinfo['ticks_'+sellett+'annotate']})
            plotinfo.update({'ticks_'+axinfo[1]+'min':plotinfo['ticks_'+sellett+'min']})
            plotinfo.update({'ticks_'+axinfo[1]+'max':plotinfo['ticks_'+sellett+'max']})
            #set x values in z
            plotinfo.update({'ticks_'+axinfo[2]+'show':plotinfo['ticks_'+sellett+'show']})
            plotinfo.update({'ticks_'+axinfo[2]+'set':plotinfo['ticks_'+sellett+'set']})
            plotinfo.update({'ticks_'+axinfo[2]+'fontsize':plotinfo['ticks_'+sellett+'fontsize']})
            plotinfo.update({'ticks_'+axinfo[2]+'rotation':plotinfo['ticks_'+sellett+'rotation']})
            plotinfo.update({'ticks_'+axinfo[2]+'stepsize':plotinfo['ticks_'+sellett+'stepsize']})
            plotinfo.update({'ticks_'+axinfo[2]+'annotate':plotinfo['ticks_'+sellett+'annotate']})
            plotinfo.update({'ticks_'+axinfo[2]+'min':plotinfo['ticks_'+sellett+'min']})
            plotinfo.update({'ticks_'+axinfo[2]+'max':plotinfo['ticks_'+sellett+'max']})
            #set x and to not show
            plotinfo.update({'ticks_'+axinfo[0]+'set':False})

        if numzeros==1 and selaxis==2: #cases [1,2,0],[0,1,2],[1,0,2]                   
            #set y values in z
            plotinfo.update({'ticks_'+axinfo[2]+'show':plotinfo['ticks_'+sellett+'show']})
            plotinfo.update({'ticks_'+axinfo[2]+'set':plotinfo['ticks_'+sellett+'set']})
            plotinfo.update({'ticks_'+axinfo[2]+'fontsize':plotinfo['ticks_'+sellett+'fontsize']})
            plotinfo.update({'ticks_'+axinfo[2]+'rotation':plotinfo['ticks_'+sellett+'rotation']})
            plotinfo.update({'ticks_'+axinfo[2]+'stepsize':plotinfo['ticks_'+sellett+'stepsize']})
            plotinfo.update({'ticks_'+axinfo[2]+'annotate':plotinfo['ticks_'+sellett+'annotate']})
            plotinfo.update({'ticks_'+axinfo[2]+'min':plotinfo['ticks_'+sellett+'min']})
            plotinfo.update({'ticks_'+axinfo[2]+'max':plotinfo['ticks_'+sellett+'max']})
                
        return plotinfo

    def get_value_of_math_eq(self,RL_txt,logshow=True,vd={}):                
        if self.has_math_equation(RL_txt)==True:
        #if self.is_variable_in_datafield(axis_fn,use_original=True)==False and hasm==True:
            RL_weq,filter=self.get_filter_var_name(RL_txt,filtereq=True) 
            var_fn,the_eq=self.get_filter_math_var_name(RL_weq)                                                            
            #evaluate eq
            try:
                #self.get_vd_from_dict(vars_dict,iii)
                RL__points=self.evaluate_equation(the_eq,vd,logshow)                  
                #RL__points=self.eval_data_into_a_df(RL_weq,logshow=True,use_filtered=True)                
            except Exception as e:
                if logshow==True:
                    log.warning('Variable {} Not Found! :('.format(var_fn))
                RL__points=None
        else:
            if logshow==True:
                log.warning('Variable {} is not a valid math equation!'.format(RL_txt))
            RL__points=None
            var_fn=RL_txt
            the_eq=None
        return RL__points,var_fn,the_eq
    
    def getsized_property(self,vecexample,modedprop):
        try:            
            if self.is_list(modedprop)==True:                
                vecp=[]                
                lenmp=len(modedprop)
                for iii,val in enumerate(vecexample):
                    jjj=numpy.fmod(iii,lenmp)  
                    vecp.append(modedprop[jjj])
            else:
                vecp=[] 
                for iii,val in enumerate(vecexample):
                    vecp.append(modedprop)
            return vecp                    
        except Exception as e:
            log.error('getsized property {}'.format(e))
            return modedprop
    def get_line_slope(self,x1,y1,x2,y2):
        if (x1-x2)!=0:
            return (y1-y2)/(x1-x2)    
        return 0
    
    def get_line_intersection(self,x1,y1,x2,y2):
        m=self.get_line_slope(x1,y1,x2,y2)
        return y1-m*x1

    def set_Reference_Lines(self,ax,Plotinfo):
        RL_Show_Ref_Lines=Plotinfo['RL_Show_Ref_Lines']
        if RL_Show_Ref_Lines==True:
            log.info('Setting reference lines in {} type {}'.format(Plotinfo['me_plot'],Plotinfo['Plot_Type']))
            RL_Horizontal_Show=Plotinfo['RL_Horizontal_Show']
            if RL_Horizontal_Show==True:
                log.info('Horizontal lines active!')                
                RL_Horizontal_points,var_fn,the_eq=self.get_value_of_math_eq(Plotinfo['RL_Horizontal_points'])                
                #RL_Horizontal_points=numpy.asfarray(RL_Horizontal_points)
                log.info('H Points {} '.format(RL_Horizontal_points))
                RL_Horizontal_UseRange=Plotinfo['RL_Horizontal_UseRange']
                RL_Horizontal_MinMax=Plotinfo['RL_Horizontal_MinMax']                
                RL_Horizontal_linewidth=self.get_selected_list_moded(Plotinfo['RL_Horizontal_linewidth'])
                RL_Horizontal_linestyle=self.get_selected_list_moded(Plotinfo['RL_Horizontal_linestyle'])
                RL_Horizontal_color=self.get_selected_list_moded(Plotinfo['RL_Horizontal_color'])
                
                xmin=numpy.min(RL_Horizontal_MinMax)
                xmax=numpy.max(RL_Horizontal_MinMax)
                RL_Horizontal_color=self.getsized_property(RL_Horizontal_points,RL_Horizontal_color)
                RL_Horizontal_linestyle=self.getsized_property(RL_Horizontal_points,RL_Horizontal_linestyle)
                RL_Horizontal_linewidth=self.getsized_property(RL_Horizontal_points,RL_Horizontal_linewidth)
                for iii,RLp in enumerate(RL_Horizontal_points):                        
                    im = ax.axhline(y=RLp,color=RL_Horizontal_color[iii], linewidth=RL_Horizontal_linewidth[iii], linestyle=RL_Horizontal_linestyle[iii], xmin=xmin, xmax=xmax)

            
            RL_Vertical_Show=Plotinfo['RL_Vertical_Show']
            if RL_Vertical_Show==True:
                log.info('Vertical lines active!')                
                RL_Vertical_points,var_fn,the_eq=self.get_value_of_math_eq(Plotinfo['RL_Vertical_points'])                
                log.info('V Points {} '.format(RL_Vertical_points))
                RL_Vertical_UseRange=Plotinfo['RL_Vertical_UseRange']
                RL_Vertical_MinMax=Plotinfo['RL_Vertical_MinMax']
                RL_Vertical_linewidth=self.get_selected_list_moded(Plotinfo['RL_Vertical_linewidth'])
                RL_Vertical_linestyle=self.get_selected_list_moded(Plotinfo['RL_Vertical_linestyle'])
                RL_Vertical_color=self.get_selected_list_moded(Plotinfo['RL_Vertical_color'])                                    
                if RL_Vertical_points!=None:                    
                    ymin=numpy.min(RL_Vertical_MinMax)
                    ymax=numpy.max(RL_Vertical_MinMax)
                    RL_Vertical_color=self.getsized_property(RL_Vertical_points,RL_Vertical_color)
                    RL_Vertical_linestyle=self.getsized_property(RL_Vertical_points,RL_Vertical_linestyle)
                    RL_Vertical_linewidth=self.getsized_property(RL_Vertical_points,RL_Vertical_linewidth)
                    for iii,RLp in enumerate(RL_Vertical_points):                        
                        im = ax.axvline(x=RLp,color=RL_Vertical_color[iii], linewidth=RL_Vertical_linewidth[iii], linestyle=RL_Vertical_linestyle[iii], ymin=ymin, ymax=ymax)                        

            RL_Radial_Center=Plotinfo['RL_Radial_Center']
            RL_Radial_Show=Plotinfo['RL_Radial_Show']
            if RL_Radial_Show==True:                
                #log.info('Equipotential not implemented yet! Sorry :P' )
                log.info('Radial lines active!')                
                RL_Radial_points,var_fn,the_eq=self.get_value_of_math_eq(Plotinfo['RL_Radial_points'])               
                RL_Radial_ini_Angle=Plotinfo['RL_Radial_ini_angle']
                log.info('Angles {} '.format(RL_Radial_points))
                RL_Radial_UseRange=Plotinfo['RL_Radial_UseRange']
                RL_Radial_MinMax=Plotinfo['RL_Radial_MinMax']
                RL_Radial_linewidth=self.get_selected_list_moded(Plotinfo['RL_Radial_linewidth'])
                RL_Radial_linestyle=self.get_selected_list_moded(Plotinfo['RL_Radial_linestyle'])
                RL_Radial_color=self.get_selected_list_moded(Plotinfo['RL_Radial_color'])                                    
                if RL_Radial_points!=None:                                        
                    Amin=RL_Radial_ini_Angle+360*RL_Radial_MinMax[0]
                    Amax=RL_Radial_ini_Angle+360*RL_Radial_MinMax[1]
                    axis_info=Plotinfo['axis_info']
                    for iii,axi in enumerate(axis_info):
                        if axi==1:
                            index1=iii                            
                        if axi==2:
                            index2=iii
                    #axisdf=[Plotinfo['dfaxis_x_fm'],Plotinfo['dfaxis_y_fm'],Plotinfo['dfaxis_z_fm']]          
                    #print(ax.get_xticks())
                    #select the df with points of y axis in plot
                    xpoints=ax.get_xticks() #axisdf[index1]
                    ypoints=ax.get_yticks() #axisdf[index2]
                    RLp=(RL_Radial_Center[index1],RL_Radial_Center[index2])
                     
                    deltax=numpy.max(xpoints)-numpy.min(xpoints)
                    xmin=numpy.min(xpoints)
                    xmax=numpy.max(xpoints)
                    deltay=numpy.max(ypoints)-numpy.min(ypoints)
                    ymin=numpy.min(ypoints)
                    ymax=numpy.max(ypoints)
                                            
                    RL_Radial_color=self.getsized_property(RL_Radial_points,RL_Radial_color)                    
                    RL_Radial_linestyle=self.getsized_property(RL_Radial_points,RL_Radial_linestyle)
                    RL_Radial_linewidth=self.getsized_property(RL_Radial_points,RL_Radial_linewidth)                                        
                    Angrl=[]
                    for ang in range(0,360,1):
                        if ang>=Amin and ang<=Amax:                            
                            Angrl.append(numpy.radians(ang))

                    for iii,Rp in enumerate(RL_Radial_points):
                        Rvl=self.getsized_property(Angrl,Rp)     
                        #log.info('Rvl {} - {}'.format(Rvl,Rp))                                               
                        pointsx=[]                            
                        pointsy=[] 
                        angle=[]                           
                        for rrr,aaar in zip(Rvl,Angrl):
                            xxx=RLp[0]+rrr*numpy.cos(aaar)
                            yyy=RLp[1]+rrr*numpy.sin(aaar)
                            if self.is_point_inside_square(xxx,yyy,xmin,ymin,xmax,ymax)==True:
                                angle.append(aaar)
                                pointsx.append(xxx)
                                pointsy.append(yyy)
                        
                        sortedxydf=self.sort_vectors_to_df(angle,pointsx,pointsy,is_ascending=False)
                        
                        dfinQ1=sortedxydf.query('V1>=0 & V2>=0')
                        dfinQ2=sortedxydf.query('V1<0 & V2>=0')
                        dfinQ3=sortedxydf.query('V1<=0 & V2<0')
                        dfinQ4=sortedxydf.query('V1>0 & V2<0')  
                        dfinQ=[dfinQ1,dfinQ2,dfinQ3,dfinQ4]                      
                        pointsx=sortedxydf['V1'].values.tolist()
                        pointsy=sortedxydf['V2'].values.tolist()
                        
                        #log.info('points x{} y{}'.format(pointsx,pointsy)) 
                        if len(pointsx)>0:
                            doplot=True                                                    
                        for dfq in dfinQ:
                            pointsx=dfq['V1'].values.tolist()
                            pointsy=dfq['V2'].values.tolist()
                            doplot=False
                            if len(pointsx)>0:
                                doplot=True   
                            if doplot==True:
                                im = ax.plot(pointsx,pointsy,color=RL_Radial_color[iii], linewidth=RL_Radial_linewidth[iii], linestyle=RL_Radial_linestyle[iii])
                            
            RL_Angular_Show=Plotinfo['RL_Angular_Show']
            if RL_Angular_Show==True:                                                
                #log.info('Angular not implemented yet! Sorry :P' )
                log.info('Angular lines active!')                
                RL_Angular_points,var_fn,the_eq=self.get_value_of_math_eq(Plotinfo['RL_Angular_points'])                
                log.info('Angles {} '.format(RL_Angular_points))
                RL_Angular_UseRange=Plotinfo['RL_Angular_UseRange']
                RL_Angular_MinMax=Plotinfo['RL_Angular_MinMax']
                RL_Angular_linewidth=self.get_selected_list_moded(Plotinfo['RL_Angular_linewidth'])
                RL_Angular_linestyle=self.get_selected_list_moded(Plotinfo['RL_Angular_linestyle'])
                RL_Angular_color=self.get_selected_list_moded(Plotinfo['RL_Angular_color'])                                    
                if RL_Angular_points!=None:                    
                    Amin=numpy.min(RL_Angular_MinMax)
                    Amax=numpy.max(RL_Angular_MinMax)
                    axis_info=Plotinfo['axis_info']
                    for iii,axi in enumerate(axis_info):
                        if axi==1:
                            index1=iii                            
                        if axi==2:
                            index2=iii
                    #axisdf=[Plotinfo['dfaxis_x_fm'],Plotinfo['dfaxis_y_fm'],Plotinfo['dfaxis_z_fm']]          
                    #print(ax.get_xticks())
                    #select the df with points of y axis in plot
                    xpoints=ax.get_xticks() #axisdf[index1]
                    ypoints=ax.get_yticks() #axisdf[index2]

                    xfmin=numpy.min(xpoints)
                    xfmax=numpy.max(xpoints)                    
                    yfmin=numpy.min(ypoints)
                    yfmax=numpy.max(ypoints)

                    RLp=(RL_Radial_Center[index1],RL_Radial_Center[index2]) 
                    deltax=numpy.max(xpoints)-numpy.min(xpoints)
                    xmin=numpy.min(xpoints)+deltax*numpy.min(RL_Angular_MinMax)
                    xmax=numpy.min(xpoints)+deltax*numpy.max(RL_Angular_MinMax)
                    deltay=numpy.max(ypoints)-numpy.min(ypoints)
                    ymin=numpy.min(ypoints)+deltay*numpy.min(RL_Angular_MinMax)
                    ymax=numpy.min(ypoints)+deltay*numpy.max(RL_Angular_MinMax)
                    rxymin=(deltax*min(RL_Angular_MinMax)/2,deltay*min(RL_Angular_MinMax)/2)
                    #rxymax=(deltax*max(RL_Angular_MinMax)/2,deltay*max(RL_Angular_MinMax)/2)
                    rxymax=(xmax,ymax)
                                               
                    RL_Angular_color=self.getsized_property(RL_Angular_points,RL_Angular_color)                    
                    RL_Angular_linestyle=self.getsized_property(RL_Angular_points,RL_Angular_linestyle)
                    RL_Angular_linewidth=self.getsized_property(RL_Angular_points,RL_Angular_linewidth)
                    if Amin==0 and  Amax==1:
                        for iii,Ang in enumerate(RL_Angular_points):
                            Angr=numpy.radians(Ang)
                            slo=self.get_line_slope(RLp[0],RLp[1],RLp[0]+numpy.cos(Angr),RLp[1]+numpy.sin(Angr))
                            
                            im = ax.axline(RLp,slope=slo,color=RL_Angular_color[iii], linewidth=RL_Angular_linewidth[iii], linestyle=RL_Angular_linestyle[iii])                        
                            #plt.axline((0, 0.5), slope=0.25, color="black", linestyle=(0, (5, 5)))
                    else:                        
                        for iii,Ang in enumerate(RL_Angular_points):
                            Angr=numpy.radians(Ang)                            
                            rmin=((rxymin[0]*numpy.cos(Angr))**2+(rxymin[1]*numpy.sin(Angr))**2)**0.5
                            rmax=((rxymax[0]*numpy.cos(Angr))**2+(rxymax[1]*numpy.sin(Angr))**2)**0.5
                            pointsx=[RLp[0]+rmin*numpy.cos(Angr),RLp[0]+rmax*numpy.cos(Angr)]                            
                            pointsy=[RLp[1]+rmin*numpy.sin(Angr),RLp[1]+rmax*numpy.sin(Angr)]                            
                            np=100
                            pointsx=self.numrange(pointsx[0],(pointsx[1]-pointsx[0])/np,np)
                            pointsy=self.numrange(pointsy[0],(pointsy[1]-pointsy[0])/np,np)
                            px=[]
                            py=[]
                            for xxx,yyy in zip(pointsx,pointsy):                            
                                if self.is_point_inside_square(xxx,yyy,xfmin,yfmin,xfmax,yfmax)==True:
                                    angle.append(aaar)
                                    px.append(xxx)
                                    py.append(yyy)
                            #log.info('points x{} y{}'.format(pointsx,pointsy))                             
                            doplot=False
                            if len(px)>1:
                                doplot=True                            
                            if doplot==True:
                                im = ax.plot(px,py,color=RL_Angular_color[iii], linewidth=RL_Angular_linewidth[iii], linestyle=RL_Angular_linestyle[iii])
    
    def remove_repeated_x_y(self,xv,yv,*args):
        #check sizes
        lenxv=len(xv)
        lenyv=len(yv)      
        vectlen=0  
        for vector in args:
            if len(vector)!=lenxv or len(vector)!=lenyv or lenyv!=lenxv:
                log.warning('Different sizes vectors to remove repated x y')
                return xv,yv,*args
            vectlen=vectlen+1
        #same size
        keep_pos=[]
        xyfound=[]
        for iii,(xval,yval) in enumerate(zip(xv,yv)):
            if (xval,yval) not in xyfound:
                xyfound.append((xval,yval))
                keep_pos.append(iii)
        xxx=[]
        yyy=[]
        aaa=[]
        for iii in keep_pos:
            xxx.append(xv[iii])
            yyy.append(yv[iii])
            bbb=[]
            for vector in args:
                bbb.append(vector[iii])
            aaa.append(bbb)
        taaa=self.transpose_matrix(aaa)
        argvects=tuple(taaa)
        return xxx,yyy,*argvects
                


            
        
            
        

    def sort_vectors_to_df(self,refvect,*args,is_ascending=True):
        tosort={}
        tosort.update({'ref':refvect})        
        nnn=1
        nt=1
        lenref=len(refvect)
        for vector in args:
            if len(vector)==lenref:                
                vn='V'+str(nnn)            
                tosort.update({vn:vector})        
                nnn=nnn+1
            else:
                log.warning('Vector {} has not same size as reference: Refsize {}, Vectsize {}'.format(nt,lenref,len(vector)))
            nt=nt+1
        adf=pd.DataFrame(tosort)
        rslt_df = adf.sort_values(by = 'ref', ascending=is_ascending)
        return rslt_df


    def is_point_inside_square(self,pointx,pointy,minsqcornerx,minsqcornery,maxsqcornerx,maxsqcornery):
        inside=False
        if pointx>=minsqcornerx and pointx<=maxsqcornerx:
            insidex=True
        else:
            insidex=False
        if pointy>=minsqcornery and pointy<=maxsqcornery:
            insidey=True
        else:
            insidey=False

        inside=insidex and insidey
        #if inside==True:
        #    log.info('({},{}) inside ({},{})-({},{})->{}'.format(pointx,pointy,minsqcornerx,minsqcornery,maxsqcornerx,maxsqcornery,inside))    
        return inside                        
    
    def get_annotations_for_tick_values(self,axis,tickvals,annodf,dfvar,plotinfo):
        try:
            #log.info('len ticks {}'.format(len(tickvals)))
            annolist=annodf.to_dict() #self.get_list_of_values(annodf,dfvar)  
            akey=self.get_dict_key_list(annolist)  
            dfxyz=plotinfo['dfxyz']
            dfuvw=plotinfo['dfuvw']
            result_anno=[]
            if len(annolist)>0 and len(annolist)==len(dfxyz):
                axis_info=plotinfo['axis_info']
                Add_axis_info=plotinfo['Add_axis_info']
                xxx,yyy,zzz,_,_=self.get_vectors_separated(dfxyz)
                uuu,vvv,www,_,_=self.get_vectors_separated(dfuvw)
                if axis<3:
                    vect=self.get_var_axis_info_(axis,axis_info,[xxx,yyy,zzz])
                else:
                    vect=self.get_var_axis_info_(axis-3,Add_axis_info,[uuu,vvv,www])
                
                for tval in tickvals:
                    if tval in vect:
                        for iii,xyzval in enumerate(vect):
                            if tval ==xyzval:
                                result_anno.append(str(annolist[akey[iii]])) #get first label on match
                                break
                    else:
                        result_anno.append('') # set empty label
            else:
                if plotinfo['Plot_Type']!='pie':
                    log.warning('{} annotations not valid, different data size!'.format(dfvar))
        except Exception as e:
            log.error('Making {} annotations: {}'.format(dfvar,e))
            return []
        return result_anno
        

    
    def set_axis_ticks(self,ax,plotinfo):
        xshowaxis=plotinfo['ticks_xshow']
        yshowaxis=plotinfo['ticks_yshow']
        xset_ticks=plotinfo['ticks_xset']
        yset_ticks=plotinfo['ticks_yset']
        xfontsize_ticks=plotinfo['ticks_xfontsize']
        xrotation_ticks=plotinfo['ticks_xrotation']
        xstepsize_ticks=plotinfo['ticks_xstepsize']
        yfontsize_ticks=plotinfo['ticks_yfontsize']
        yrotation_ticks=plotinfo['ticks_yrotation']
        ystepsize_ticks=plotinfo['ticks_ystepsize']
        xannotate_ticks=plotinfo['ticks_xannotate']
        yannotate_ticks=plotinfo['ticks_yannotate']
        xmin_ticks=plotinfo['ticks_xmin']
        ymin_ticks=plotinfo['ticks_ymin']
        #zmin_ticks=plotinfo['ticks_zmin']
        xmax_ticks=plotinfo['ticks_xmax']
        ymax_ticks=plotinfo['ticks_ymax']
        #zmax_ticks=plotinfo['ticks_zmax']
        x_annotate=False
        y_annotate=False
        if xset_ticks==True:
            xTicks = numpy.arange(xmin_ticks, xmax_ticks + xstepsize_ticks, xstepsize_ticks)
        else:
            xTicks = ax.get_xticks()
            log.info('Got ticks->{}'.format(xTicks))
        if yset_ticks==True:
            yTicks = numpy.arange(ymin_ticks, ymax_ticks + ystepsize_ticks, ystepsize_ticks)    
        else:
            yTicks = ax.get_yticks()
        # Map to projection
        '''if plotinfo['Projection_Type'] =='polar':
            theta = numpy.linspace(0.0, 2 * numpy.pi, len(xTicks), endpoint=False)
            xTicks=theta'''
        '''xTicks=numpy.asarray(xTicks)
            #define function
            minx=numpy.min(xTicks)
            maxx=numpy.max(xTicks)
            pi=numpy.pi
            my_function = lambda x: 2*pi*x
            #apply function to NumPy array
            my_function(xTicks)'''
        
        
        try:            
            if xannotate_ticks not in ['','None']:              
                xannotations=self.get_datafield_of_variable(xannotate_ticks,'__empty__',True)                
                if len(xannotations)>0:            
                    xannolabels=self.get_annotations_for_tick_values(1,xTicks,xannotations,xannotate_ticks,plotinfo)                    
                    x_annotate=True
            if yannotate_ticks not in ['','None']:            
                yannotations=self.get_datafield_of_variable(yannotate_ticks,'__empty__',True)            
                if len(yannotations)>0:           
                    yannolabels=self.get_annotations_for_tick_values(2,yTicks,yannotations,yannotate_ticks,plotinfo)                     
                    y_annotate=True
        except Exception as e:
            log.error('Getting annotation labels:{}'.format(e))

        #if yannotate_ticks not in ['','None']:

        if xset_ticks==True:
            #xTicks = numpy.arange(xmin_ticks, xmax_ticks + xstepsize_ticks, xstepsize_ticks)
            if xshowaxis==True:
                ax.set_xticks(xTicks)
                try:
                    if x_annotate==True:   
                        log.info('Setting X labels {}'.format(xannolabels))                     
                        ax.set_xticklabels(xannolabels, rotation=xrotation_ticks, fontsize=xfontsize_ticks)
                    else:
                        ax.set_xticklabels(xTicks, rotation=xrotation_ticks, fontsize=xfontsize_ticks)    
                except Exception as e:
                    log.warning("Can't use {} X annotations: {}".format(xannotate_ticks,e))                    
                    ax.set_xticklabels(xTicks, rotation=xrotation_ticks, fontsize=xfontsize_ticks)            
            else:
                ax.set_xticks([])
        if yset_ticks==True:    
            #yTicks = numpy.arange(ymin_ticks, ymax_ticks + ystepsize_ticks, ystepsize_ticks)                
            if yshowaxis==True:
                ax.set_yticks(yTicks)
                try:
                    if y_annotate==True:                        
                        log.info('Setting Y labels {}'.format(yannolabels))                     
                        ax.set_yticklabels(yannolabels, rotation=yrotation_ticks, fontsize=yfontsize_ticks) 
                    else:
                        ax.set_yticklabels(yTicks, rotation=yrotation_ticks, fontsize=yfontsize_ticks)                   
                except Exception as e:
                    log.warning("Can't use {} Y annotations: {}".format(yannotate_ticks,e))                    
                    ax.set_yticklabels(yTicks, rotation=yrotation_ticks, fontsize=yfontsize_ticks)
            else:
                ax.set_yticks([])
        try:
            self.set_Reference_Lines(ax,plotinfo)
        except Exception as e:
            log.error('Making Reference Lines {}'.format(e))

               

    def correct_layout(self,numplots,layout,sizes):        
        layout[0]=self.limit_var(int(layout[0]),1,numplots)
        layout[1]=self.limit_var(int(layout[1]),1,numplots)
        # no need to limit layout anymore
        '''if layout[1]+layout[0]>numplots+1:
            if layout[0]>=layout[1]:
                layout[0]=max(numplots-layout[1]+1,1)
            else:
                layout[1]=max(numplots-layout[0]+1,1)
            if layout[1]+layout[0]>numplots+1:
                if layout[0]>=layout[1]:
                    layout[0]=max(numplots-layout[1]+1,1)
                else:
                    layout[1]=max(numplots-layout[0]+1,1)

        if layout[1]*layout[0]>numplots or layout[1]*layout[0]==0: 
            layout[0]=1
            layout[1]=1
        '''
        return layout
    
    def get_all_plots_layout(self,plotlayoutlist):
        maxH=0
        maxV=0
        for play in plotlayoutlist:
            if maxH<=play[0]:
                maxH=play[0]
            if maxV<=play[1]:
                maxV=play[1]
        return maxH,maxV
    
    def Mask_data(self,aplot,plotinfo):        
        plotinfo.update({'isok':True})        
                
        ppp=self.Plot_dict[aplot]
        plotinfo.update({'me_plot':aplot})        
        x_adk=ppp['Axis_X']['Axis_Data_Key']
        y_adk=ppp['Axis_Y']['Axis_Data_Key']
        z_adk=ppp['Axis_Z']['Axis_Data_Key']
        dfaxis_x=self.get_array_of_variable(x_adk)
        dfaxis_y=self.get_array_of_variable(y_adk)
        dfaxis_z=self.get_array_of_variable(z_adk)
        axisdatarange_x=ppp['Axis_X']['Axis_Data_Range']
        axisdatarange_y=ppp['Axis_Y']['Axis_Data_Range']
        axisdatarange_z=ppp['Axis_Z']['Axis_Data_Range']        
        #print(type(dfaxis_x),len(dfaxis_x))
        
        if dfaxis_y.size==0 and dfaxis_z.size>0 and dfaxis_x.size>0:
            #2Dplot
            dfaxis_y=dfaxis_z
            axisdatarange_y=axisdatarange_z
            plotinfo.update({'plot_Dim':2})             
            plotinfo.update({'axis_info':[1,0,2]})
        elif dfaxis_x.size==0 and dfaxis_z.size>0 and dfaxis_y.size>0:
            #2Dplot
            dfaxis_x=dfaxis_y
            axisdatarange_x=axisdatarange_y
            dfaxis_y=dfaxis_z
            axisdatarange_y=axisdatarange_z
            plotinfo.update({'plot_Dim':2})             
            plotinfo.update({'axis_info':[0,1,2]})
        elif dfaxis_z.size==0 and dfaxis_y.size>0 and dfaxis_x.size>0:
            #2Dplot
            dfaxis_z=dfaxis_y
            axisdatarange_z=axisdatarange_y            
            plotinfo.update({'plot_Dim':2}) 
            plotinfo.update({'axis_info':[1,2,0]})
        elif dfaxis_z.size>0 and dfaxis_y.size>0 and dfaxis_x.size>0:
            #3Dplot            
            plotinfo.update({'plot_Dim':3}) 
            plotinfo.update({'axis_info':[1,2,3]})
        elif dfaxis_x.size==0 and dfaxis_y.size==0 and dfaxis_z.size>0:
            #1Dplot            
            plotinfo.update({'plot_Dim':1})             
            plotinfo.update({'axis_info':[0,0,1]})
        elif dfaxis_x.size==0 and dfaxis_y.size>0 and dfaxis_z.size==0:
            #1Dplot            
            plotinfo.update({'plot_Dim':1})             
            plotinfo.update({'axis_info':[0,1,0]})
        elif dfaxis_x.size>0 and dfaxis_y.size==0 and dfaxis_z.size==0:
            #1Dplot            
            plotinfo.update({'plot_Dim':1})             
            plotinfo.update({'axis_info':[1,0,0]})
        else:
            log.info('No data available in csv for making plot {} of {},{},{}'.format(aplot,ppp['Axis_X']['Axis_Data_Key'],ppp['Axis_Y']['Axis_Data_Key'],ppp['Axis_Z']['Axis_Data_Key']))
            plotinfo.update({'plot_Dim':0}) 
            plotinfo.update({'axis_info':[0,0,0]})
            plotinfo.update({'isok':False})        
            return plotinfo
        xAutorange=ppp['Axis_X']['Axis_Auto_Range']
        yAutorange=ppp['Axis_Y']['Axis_Auto_Range']
        zAutorange=ppp['Axis_Z']['Axis_Auto_Range']
        if xAutorange==True:
            axisdatarange_x=[min(dfaxis_x),max(dfaxis_x)]
            log.info('{} X axis auto Ranged to {}'.format(aplot,axisdatarange_x))
        if yAutorange==True:    
            axisdatarange_y=[min(dfaxis_y),max(dfaxis_y)]
            log.info('{} Y axis auto Ranged to {}'.format(aplot,axisdatarange_y))
        if zAutorange==True:
            axisdatarange_z=[min(dfaxis_z),max(dfaxis_z)]
            log.info('{} Z axis auto Ranged to {}'.format(aplot,axisdatarange_z))

        dfaxisignore_x,dfaxis_x_fm=self.get_ignored_filter_data(dfaxis_x,axisdatarange_x)
        dfaxisignore_y,dfaxis_y_fm=self.get_ignored_filter_data(dfaxis_y,axisdatarange_y)
        dfaxisignore_z,dfaxis_z_fm=self.get_ignored_filter_data(dfaxis_z,axisdatarange_z)
        
        if len(dfaxis_x_fm)==0 and len(dfaxisignore_x)>0:
            log.info('{} {} data out of range in Axis_X'.format(aplot,x_adk))
            dfaxis_x_fm=self.get_datafield_of_variable('',0,False) #get a datafield with zeros
        if len(dfaxis_y_fm)==0 and len(dfaxisignore_y)>0:
            log.info('{} {} data out of range in Axis_Y'.format(aplot,y_adk))
            dfaxis_y_fm=self.get_datafield_of_variable('',0,False)
        if len(dfaxis_z_fm)==0 and len(dfaxisignore_z)>0:
            log.info('{} {} data out of range in Axis_Z'.format(aplot,z_adk))
            dfaxis_z_fm=self.get_datafield_of_variable('',0,False)
        plotinfo.update({'dfaxis_x':dfaxis_x})
        plotinfo.update({'dfaxis_y':dfaxis_y})
        plotinfo.update({'dfaxis_z':dfaxis_z})
        plotinfo.update({'dfaxis_x_fm':dfaxis_x_fm})
        plotinfo.update({'dfaxis_y_fm':dfaxis_y_fm})
        plotinfo.update({'dfaxis_z_fm':dfaxis_z_fm})
        plotinfo.update({'dfaxisignore_x':dfaxisignore_x})
        plotinfo.update({'dfaxisignore_y':dfaxisignore_y})
        plotinfo.update({'dfaxisignore_z':dfaxisignore_z})
        log.info('Mask Done for {}'.format(aplot))
        return plotinfo
    
    def Mask_Additional_data(self,aplot,plotinfo):        
        ppp=self.Plot_dict[aplot]
        #Additional
        u_adk=ppp['Additional']['Axis_U']['Axis_Data_Key']
        v_adk=ppp['Additional']['Axis_V']['Axis_Data_Key']
        w_adk=ppp['Additional']['Axis_W']['Axis_Data_Key']
        dfaxis_u=self.get_array_of_variable(u_adk,zeroval='__empty__',logshow=False)
        dfaxis_v=self.get_array_of_variable(v_adk,zeroval='__empty__',logshow=False)
        dfaxis_w=self.get_array_of_variable(w_adk,zeroval='__empty__',logshow=False)
        #print('Mask Additional-df:\n w',dfaxis_w,'\n v',dfaxis_v,'\n u',dfaxis_u)
        #self.get_math_df_data('test')
        axisdatarange_u=ppp['Additional']['Axis_U']['Axis_Data_Range']
        axisdatarange_v=ppp['Additional']['Axis_V']['Axis_Data_Range']
        axisdatarange_w=ppp['Additional']['Axis_W']['Axis_Data_Range']
        
        if  dfaxis_w.size>0 and dfaxis_v.size==0 and dfaxis_u.size>0:
            #2D Additional            
            plotinfo.update({'Add_plot_Dim':2})             
            plotinfo.update({'Add_axis_info':[1,0,2]})
        elif dfaxis_w.size==0 and dfaxis_v.size>0 and dfaxis_u.size>0:
            #2D Additional            
            plotinfo.update({'Add_plot_Dim':2}) 
            plotinfo.update({'Add_axis_info':[1,2,0]})
        elif dfaxis_w.size>00 and dfaxis_v.size>0 and dfaxis_u.size==0:
            #2D Additional            
            plotinfo.update({'Add_plot_Dim':2}) 
            plotinfo.update({'Add_axis_info':[0,1,2]})
        elif dfaxis_w.size>0 and dfaxis_v.size>0 and dfaxis_u.size>0:
            #3D Additional
            plotinfo.update({'Add_plot_Dim':3}) 
            plotinfo.update({'Add_axis_info':[1,2,3]})
        elif dfaxis_w.size>0 and dfaxis_v.size==0 and dfaxis_u.size==0:
            #1D Additional            
            plotinfo.update({'Add_plot_Dim':1}) 
            plotinfo.update({'Add_axis_info':[0,0,1]})
        elif dfaxis_w.size==0 and dfaxis_v.size>0 and dfaxis_u.size==0:
            #1D Additional            
            plotinfo.update({'Add_plot_Dim':1}) 
            plotinfo.update({'Add_axis_info':[0,1,0]})
        elif dfaxis_w.size==0 and dfaxis_v.size==0 and dfaxis_u.size>0:
            #1D Additional            
            plotinfo.update({'Add_plot_Dim':1}) 
            plotinfo.update({'Add_axis_info':[1,0,0]})
        else:
            plotinfo.update({'Add_plot_Dim':0}) 
            plotinfo.update({'Add_axis_info':[0,0,0]})
            log.info('No Additional data for plot {} for U({}), V({}), W({})'.format(aplot,u_adk,v_adk,w_adk))  
            #return plotinfo          
        
        uAutorange=ppp['Additional']['Axis_U']['Axis_Auto_Range']
        vAutorange=ppp['Additional']['Axis_V']['Axis_Auto_Range']
        wAutorange=ppp['Additional']['Axis_W']['Axis_Auto_Range']

        if uAutorange==True and dfaxis_u.size>0:
            axisdatarange_u=[min(dfaxis_u),max(dfaxis_u)]
            log.info('{} U axis auto Ranged to {}'.format(aplot,axisdatarange_u))
        if vAutorange==True and dfaxis_v.size>0:    
            axisdatarange_v=[min(dfaxis_v),max(dfaxis_v)]
            log.info('{} V axis auto Ranged to {}'.format(aplot,axisdatarange_v))
        if wAutorange==True and dfaxis_w.size>0:
            axisdatarange_w=[min(dfaxis_w),max(dfaxis_w)]
            log.info('{} W axis auto Ranged to {}'.format(aplot,axisdatarange_w))
        
        dfaxisignore_u,dfaxis_u_fm=self.get_ignored_filter_data(dfaxis_u,axisdatarange_u)
        dfaxisignore_v,dfaxis_v_fm=self.get_ignored_filter_data(dfaxis_v,axisdatarange_v)
        dfaxisignore_w,dfaxis_w_fm=self.get_ignored_filter_data(dfaxis_w,axisdatarange_w)
                
        if len(dfaxis_u_fm)==0 and len(dfaxisignore_u)>0:
            log.info('{} {} data out of range in Axis_U'.format(aplot,u_adk))
            dfaxis_u_fm=self.get_datafield_of_variable('',0,False) #get a datafield with zeros
        if len(dfaxis_v_fm)==0 and len(dfaxisignore_v)>0:
            log.info('{} {} data out of range in Axis_V'.format(aplot,v_adk))
            dfaxis_v_fm=self.get_datafield_of_variable('',0,False)
        if len(dfaxis_w_fm)==0 and len(dfaxisignore_w)>0:
            log.info('{} {} data out of range in Axis_W'.format(aplot,w_adk))
            dfaxis_w_fm=self.get_datafield_of_variable('',0,False)
        
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,plotinfo['Add_axis_info'],'Axis_U',axisdatarange_u)
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,plotinfo['Add_axis_info'],'Axis_V',axisdatarange_v)
        plotinfo=self.set_Tick_from_axis_info(ppp,plotinfo,plotinfo['Add_axis_info'],'Axis_W',axisdatarange_w)        

        plotinfo.update({'dfaxis_u':dfaxis_u})
        plotinfo.update({'dfaxis_v':dfaxis_v})
        plotinfo.update({'dfaxis_w':dfaxis_w})
        plotinfo.update({'dfaxis_u_fm':dfaxis_u_fm})
        plotinfo.update({'dfaxis_v_fm':dfaxis_v_fm})
        plotinfo.update({'dfaxis_w_fm':dfaxis_w_fm})
        plotinfo.update({'dfaxisignore_u':dfaxisignore_u})
        plotinfo.update({'dfaxisignore_v':dfaxisignore_v})
        plotinfo.update({'dfaxisignore_w':dfaxisignore_w})
        log.info('Mask Additional Data Done for {}'.format(aplot))
        return plotinfo
    
    def get_dfuvw_sized_to_dfxyz(self,dfxyz,dfuvw,Plotinfo):
        if self.is_list(dfxyz)==False or self.is_list(dfuvw)==False:
            return []
        lenxyz=len(dfxyz)
        lenuvw=len(dfuvw)
        if lenxyz==lenuvw or lenuvw==0:
            return dfuvw
        else:            
            uaxis=Plotinfo['uaxis']
            vaxis=Plotinfo['vaxis']
            waxis=Plotinfo['waxis']
            new_dfuvw=[]
            #xxx,yyy,zzz,bbb,zeros=self.get_vectors_separated(dfxyz)
            uuu,vvv,www,_,_=self.get_vectors_separated(dfuvw)             
            dfuuu,_,_ =self.get_error_dxyzsized(uuu,'uuuuuuu='+uaxis,Plotinfo)
            dfvvv,_,_ =self.get_error_dxyzsized(vvv,'vvvvvvv='+vaxis,Plotinfo)
            dfwww,_,_ =self.get_error_dxyzsized(www,'wwwwwww='+waxis,Plotinfo)
            for u_,v_,w_ in zip(dfuuu,dfvvv,dfwww):
                new_dfuvw.append([u_,v_,w_])
            log.info('xyz has size {} uvw resized from {} to {}'.format(lenxyz,lenuvw,len(new_dfuvw)))
            return new_dfuvw


    def get_ignored_filter_data(self,dfaxis_u,axisdatarange_u):
        dfaxis_u_fm=[]
        dfaxisignore_u=[]
        if dfaxis_u.ndim>0:
            for iii in dfaxis_u:
                if (iii <= axisdatarange_u[1] and iii >= axisdatarange_u[0]):
                    dfaxisignore_u.append(False) #Do not ignore if in range
                    dfaxis_u_fm.append(dfaxis_u)
                else:
                    dfaxisignore_u.append(True)                
            dfaxisignore_u=numpy.asarray(dfaxisignore_u)
        return dfaxisignore_u,dfaxis_u_fm


    def Additonal_data_filter_preprocessing(self,aplot, plotinfo):
        ppp=self.Plot_dict[aplot]
        try:            
            uaxis=ppp['Additional']['Axis_U']['Axis_Data_Key']
            vaxis=ppp['Additional']['Axis_V']['Axis_Data_Key']
            waxis=ppp['Additional']['Axis_W']['Axis_Data_Key']
            uaxis,filteru=self.get_filter_var_name(uaxis)            
            vaxis,filterv=self.get_filter_var_name(vaxis)            
            waxis,filterw=self.get_filter_var_name(waxis)  
            uaxis,_=self.get_filter_math_var_name(uaxis)                       
            vaxis,_=self.get_filter_math_var_name(vaxis)                      
            waxis,_=self.get_filter_math_var_name(waxis)                        
            plotinfo.update({'uaxis':uaxis})            
            plotinfo.update({'vaxis':vaxis})
            plotinfo.update({'waxis':waxis})
            plotinfo.update({'udf_filter':filteru})            
            plotinfo.update({'vdf_filter':filterv})
            plotinfo.update({'wdf_filter':filterw})
            # Add additional filters
            allfilter=plotinfo['allfilter']
            if filteru!='' or filterv!='' or filterw!='':
                filterlist=[filteru,filterv,filterw]                
                for fff,fil in enumerate(filterlist):
                    if fil!='':                        
                        if fff>0 and fff<len(filterlist) and allfilter!='':
                            allfilter=allfilter+' & '+fil
                        else:
                            allfilter=allfilter+fil  
                log.info('Additional Total filter: {} {}'.format(filterlist,allfilter))                  
                df=self.get_filter_df(allfilter,True)
                self.csv_data_filtered=df
            else:
                df=self.csv_data_filtered
            plotinfo.update({'Add_allfilter':allfilter})
            #without range filter mask
            uAutorange=ppp['Additional']['Axis_U']['Axis_Auto_Range']
            vAutorange=ppp['Additional']['Axis_V']['Axis_Auto_Range']
            wAutorange=ppp['Additional']['Axis_W']['Axis_Auto_Range']
            if uAutorange==True:
                dfaxis_u=plotinfo['dfaxis_u']
            else:            
                dfaxis_u=plotinfo['dfaxis_u_fm']
            if vAutorange==True:    
                dfaxis_v=plotinfo['dfaxis_v']
            else:
                dfaxis_v=plotinfo['dfaxis_v_fm']
            if wAutorange==True:
                dfaxis_w=plotinfo['dfaxis_w']
            else:
                dfaxis_w=plotinfo['dfaxis_w_fm']
            #with range filter mask            
            dfaxisignore_u=plotinfo['dfaxisignore_u']
            dfaxisignore_v=plotinfo['dfaxisignore_v']
            dfaxisignore_w=plotinfo['dfaxisignore_w']
            uu=numpy.unique(dfaxis_u)
            uv=numpy.unique(dfaxis_v)
            uw=numpy.unique(dfaxis_w)
            plotinfo.update({'uu':uu})
            plotinfo.update({'uv':uv})
            plotinfo.update({'uw':uw})   
            #print('Additional-df:\n w',dfaxis_w,'\n v',dfaxis_v,'\n u',dfaxis_u)
            #Recheck dimension after filter
            if  dfaxis_w.size>0 and dfaxis_v.size==0 and dfaxis_u.size>0:
                #2D Additional            
                plotinfo.update({'Add_plot_Dim':2})             
                plotinfo.update({'Add_axis_info':[1,0,2]})
            elif dfaxis_w.size==0 and dfaxis_v.size>0 and dfaxis_u.size>0:
                #2D Additional            
                plotinfo.update({'Add_plot_Dim':2}) 
                plotinfo.update({'Add_axis_info':[1,2,0]})
            elif dfaxis_w.size>00 and dfaxis_v.size>0 and dfaxis_u.size==0:
                #2D Additional            
                plotinfo.update({'Add_plot_Dim':2}) 
                plotinfo.update({'Add_axis_info':[0,1,2]})
            elif dfaxis_w.size>0 and dfaxis_v.size>0 and dfaxis_u.size>0:
                #3D Additional
                plotinfo.update({'Add_plot_Dim':3}) 
                plotinfo.update({'Add_axis_info':[1,2,3]})
            elif dfaxis_w.size>0 and dfaxis_v.size==0 and dfaxis_u.size==0:
                #1D Additional            
                plotinfo.update({'Add_plot_Dim':1}) 
                plotinfo.update({'Add_axis_info':[0,0,1]})
            elif dfaxis_w.size==0 and dfaxis_v.size>0 and dfaxis_u.size==0:
                #1D Additional            
                plotinfo.update({'Add_plot_Dim':1}) 
                plotinfo.update({'Add_axis_info':[0,1,0]})
            elif dfaxis_w.size==0 and dfaxis_v.size==0 and dfaxis_u.size>0:
                #1D Additional            
                plotinfo.update({'Add_plot_Dim':1}) 
                plotinfo.update({'Add_axis_info':[1,0,0]})
            else:
                plotinfo.update({'Add_plot_Dim':0}) 
                plotinfo.update({'Add_axis_info':[0,0,0]})
                log.info('No Additional data for plot {} after filter'.format(aplot))                  

        except Exception as e:
            log.error(e)
            return plotinfo
        if plotinfo['Add_plot_Dim']==3:         
            axis_info=plotinfo['Add_axis_info']   
            (xv,yv,zv)=(None,None,None)            
            (nx,ny,nz)=(0,0,0)
            dfxyz=[]
            if axis_info==[1,2,3]:                
                xv, yv = numpy.meshgrid(numpy.asfarray(uu), numpy.asfarray(uv), indexing='ij')
                (nx,ny)=xv.shape
                #print('xv type:',type(xv))
        
                xv=numpy.asfarray(xv) #are integers only...
                yv=numpy.asfarray(yv)
                zv=numpy.asfarray(yv.copy())
                dfxyz=[]
                for dfx,dfy,dfz,ig_x,ig_y,ig_z in zip(df[uaxis],df[vaxis],df[waxis],dfaxisignore_u,dfaxisignore_v,dfaxisignore_w):
                    if ig_x==False and ig_y==False and ig_z==False:
                        dfxyz.append([dfx,dfy,dfz])
                #print('xv type:',type(xv))
                for iii in range(nx):
                    for jjj in range(ny):
                        # treat xv[i,j], yv[i,j]
                        zv[iii,jjj] =  numpy.NaN #0.0
                        for xyz in dfxyz:
                            if xyz[0]==xv[iii,jjj] and xyz[1]==yv[iii,jjj]:                                  
                                zv[iii,jjj]=float(xyz[2])   #just passing int value
                                #print('zv value',zv[iii,jjj],xyz[2])
                                
                         
            #print('3D dfxyz:',dfxyz)
            plotinfo.update({'dfuvw':dfxyz})    
            plotinfo.update({'uv':xv})
            plotinfo.update({'vv':yv})
            plotinfo.update({'wv':zv})
            plotinfo.update({'nu':nx})
            plotinfo.update({'nv':ny})
            plotinfo.update({'nw':nz})
            
        elif plotinfo['Add_plot_Dim']==2:            
            axis_info=plotinfo['Add_axis_info']
            (xv,yv,zv)=(None,None,None)            
            (nx,ny,nz)=(0,0,0)
            dfxyz=[]
            if axis_info==[1,2,0]:                
                xv, yv = numpy.meshgrid(uu, uv, indexing='ij')
                nx=len(xv)
                ny=len(yv)
                nz=0                
                for dfx,dfy,ig_x,ig_y in zip(df[uaxis],df[vaxis],dfaxisignore_u,dfaxisignore_v):
                    if ig_x==False and ig_y==False:
                        dfxyz.append([dfx,dfy,0])
            elif axis_info==[1,0,2]:                                
                xv, zv = numpy.meshgrid(uu, uw, indexing='ij')
                nx=len(xv)
                ny=0
                nz=len(zv)
                for dfx,dfz,ig_x,ig_z in zip(df[uaxis],df[waxis],dfaxisignore_u,dfaxisignore_w):
                    if ig_x==False and ig_z==False:                
                        dfxyz.append([dfx,0,dfz])
            elif axis_info==[0,1,2]:                  
                yv, zv = numpy.meshgrid(uv, uw, indexing='ij')
                nx=0
                ny=len(yv)
                nz=len(zv)
                for dfy,dfz,ig_y,ig_z in zip(df[vaxis],df[waxis],dfaxisignore_v,dfaxisignore_w):
                    if ig_y==False and ig_z==False:
                        dfxyz.append([0,dfy,dfz])

            plotinfo.update({'dfuvw':dfxyz})    
            plotinfo.update({'uv':xv})
            plotinfo.update({'vv':yv})
            plotinfo.update({'wv':zv})
            plotinfo.update({'nu':nx})
            plotinfo.update({'nv':ny})
            plotinfo.update({'nw':nz})
        
        elif plotinfo['Add_plot_Dim']==1:            
            axis_info=plotinfo['Add_axis_info']
            (xv,yv,zv)=(None,None,None)            
            (nx,ny,nz)=(0,0,0)
            dfxyz=[]
            if axis_info==[1,0,0]:                
                enum=range(1,len(uu)+1)
                xv, yv = numpy.meshgrid(enum, uu, indexing='ij')
                nx=len(xv)
                ny=len(yv)
                nz=0
                for dfx,ig_x in zip(df[uaxis],dfaxisignore_u):
                    if ig_x==False:                
                        dfxyz.append([dfx,0,0])
            elif axis_info==[0,1,0]:                
                enum=range(1,len(uv)+1)
                xv, yv = numpy.meshgrid(enum, uv, indexing='ij')
                nx=len(xv)
                ny=len(yv)
                nz=0
                for dfy,ig_y in zip(df[vaxis],dfaxisignore_v):
                    if ig_y==False:                
                        dfxyz.append([0,dfy,0])
            elif axis_info==[0,0,1]:                
                enum=range(1,len(uw)+1)
                xv, yv = numpy.meshgrid(enum, uw, indexing='ij')
                nx=len(xv)
                ny=len(yv)
                nz=0
                for dfz,ig_z in zip(df[waxis],dfaxisignore_w):
                    if ig_z==False:                
                        dfxyz.append([0,0,dfz])

            plotinfo.update({'dfuvw':dfxyz})    
            plotinfo.update({'uv':xv})
            plotinfo.update({'vv':yv})
            plotinfo.update({'wv':zv})
            plotinfo.update({'nu':nx})
            plotinfo.update({'nv':ny})
            plotinfo.update({'nw':nz})
        else:            
            log.info('No Additional Data found!')
            plotinfo.update({'dfuvw':None})    
            plotinfo.update({'uv':None})
            plotinfo.update({'vv':None})
            plotinfo.update({'wv':None})
            plotinfo.update({'nu':None})
            plotinfo.update({'nv':None})
            plotinfo.update({'nw':None})
        if plotinfo['plot_Dim']>=1: #if there is reversal do it also for u,v and w
            if ppp['Reverse_Data_Series']==True:
                try: #They can be none...
                    txv=self.transpose_matrix(xv)
                    plotinfo.update({'uv':txv})
                except:
                    plotinfo.update({'uv':None})
                try:
                    tyv=self.transpose_matrix(yv)
                    plotinfo.update({'vv':tyv})
                except:
                    plotinfo.update({'vv':None})
                try:
                    tzv=self.transpose_matrix(zv)
                    plotinfo.update({'wv':tzv})
                except:
                    plotinfo.update({'wv':None}) 
        #set uvw same size as xyz
        try:
            thedfxyz=plotinfo['dfxyz']
            dfuvw=self.get_dfuvw_sized_to_dfxyz(thedfxyz,plotinfo['dfuvw'],plotinfo)                                                       
        except Exception as e:   
            dfuvw=[]         
            #plotinfo.update({'dfxyz':[]})    
            log.error('Making dfuvw same size as dfxyz:{}'.format(e))
        plotinfo.update({'dfuvw':dfuvw})    
        return plotinfo
    
    def data_filter_preprocessing(self,aplot, plotinfo):
        ppp=self.Plot_dict[aplot]
        try:            
            xaxis=ppp['Axis_X']['Axis_Data_Key']
            yaxis=ppp['Axis_Y']['Axis_Data_Key']
            zaxis=ppp['Axis_Z']['Axis_Data_Key']
            xaxis,filterx=self.get_filter_var_name(xaxis)            
            yaxis,filtery=self.get_filter_var_name(yaxis)            
            zaxis,filterz=self.get_filter_var_name(zaxis)    
            xaxis,_=self.get_filter_math_var_name(xaxis)                    
            yaxis,_=self.get_filter_math_var_name(yaxis)                    
            zaxis,_=self.get_filter_math_var_name(zaxis)                    
            plotinfo.update({'xaxis':xaxis})            
            plotinfo.update({'yaxis':yaxis})
            plotinfo.update({'zaxis':zaxis})
            plotinfo.update({'xdf_filter':filterx})            
            plotinfo.update({'ydf_filter':filtery})
            plotinfo.update({'zdf_filter':filterz})
            allfilter=''
            if filterx!='' or filtery!='' or filterz!='':
                filterlist=[filterx,filtery,filterz]                
                for fff,fil in enumerate(filterlist):
                    if fil!='':                        
                        if fff>0 and fff<len(filterlist) and allfilter!='':
                            allfilter=allfilter+' & '+fil
                        else:
                            allfilter=allfilter+fil  
                log.info('Total filter: {} {}'.format(filterlist,allfilter))                  
                df=self.get_filter_df(allfilter,True)
                self.csv_data_filtered=df
            else:
                df=self.csv_data
            plotinfo.update({'allfilter':allfilter})
            #without range filter mask
            xAutorange=ppp['Axis_X']['Axis_Auto_Range']
            yAutorange=ppp['Axis_Y']['Axis_Auto_Range']
            zAutorange=ppp['Axis_Z']['Axis_Auto_Range']
            if xAutorange==True:
                dfaxis_x=plotinfo['dfaxis_x']
            else:            
                dfaxis_x=plotinfo['dfaxis_x_fm']
            if yAutorange==True:    
                dfaxis_y=plotinfo['dfaxis_y']
            else:
                dfaxis_y=plotinfo['dfaxis_y_fm']
            if zAutorange==True:
                dfaxis_z=plotinfo['dfaxis_z']
            else:
                dfaxis_z=plotinfo['dfaxis_z_fm']
            #with range filter mask
            
            
            
            dfaxisignore_x=plotinfo['dfaxisignore_x']
            dfaxisignore_y=plotinfo['dfaxisignore_y']
            dfaxisignore_z=plotinfo['dfaxisignore_z']
            ux=numpy.unique(dfaxis_x)
            uy=numpy.unique(dfaxis_y)
            uz=numpy.unique(dfaxis_z)
            plotinfo.update({'ux':ux})
            plotinfo.update({'uy':uy})
            plotinfo.update({'uz':uz})
            log.info('Found unique vector lengths lux={} luy={} luz={}'.format(len(ux),len(uy),len(uz)))
            #log.debug('dfaxis_x={} dfaxis_y={} dfaxis_z={}'.format(dfaxis_x,dfaxis_y,dfaxis_z))
            #log.debug('ux={} uy={} uz={}'.format(ux,uy,uz))
            if plotinfo['plot_Dim']==3:
                if len(ux)>1 and len(uy)>1 and len(uz)>1:
                    log.info('3D Plot')                    
                    plotinfo.update({'plot_Dim':3})
                    plotinfo.update({'axis_info':[1,2,3]})
                    plotinfo.update({'axis_value':None})
                    

                elif len(ux)==1 and len(uy)>1 and len(uz)>1:
                    log.info('Replicating x to 2D')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[0,1,2]})
                    plotinfo.update({'axis_value':ux[0]})
                    

                elif len(uy)==1 and len(ux)>1 and len(uz)>1:
                    log.info('Replicating y to 2D')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[0,1,2]})
                    plotinfo.update({'axis_value':uy[0]})   

                elif len(uz)==1 and len(ux)>1 and len(uy)>1:
                    log.info('Replicating y to 2D')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,2,0]})
                    plotinfo.update({'axis_value':uz[0]})    
                
                elif len(ux)==1 and len(uy)==1 and len(uz)==1:
                    log.info('Found single point 3D')     
                    plotinfo.update({'plot_Dim':3})
                    plotinfo.update({'axis_info':[1,2,3]})
                    plotinfo.update({'axis_value':None})                

                else:
                    log.info('Replicating y to 2D with no info')
                    plotinfo.update({'plot_Dim':2})
            
            if plotinfo['plot_Dim']==2:
                if len(ux)>1 and len(uy)>1 and len(uz)<=1:
                    log.info('Found x vs y 2D')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,2,0]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)>1 and len(uy)<=1 and len(uz)>1:
                    log.info('Found x vs z 2D')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,0,2]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)==1 and len(uy)==1 and len(uz)==0:
                    log.info('Found x y 2D point')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,2,0]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)==0 and len(uy)==1 and len(uz)==1:
                    log.info('Found y z 2D point')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[0,1,2]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)==1 and len(uy)==0 and len(uz)==1:
                    log.info('Found x z 2D point')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,0,2]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)==1 and len(uy)==0 and len(uz)==1:
                    log.info('Found x z 2D point')                    
                    plotinfo.update({'plot_Dim':2})
                    plotinfo.update({'axis_info':[1,0,2]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)>1 and len(uy)<=1 and len(uz)<=1:
                    log.info('Replicating x to 1D')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[1,0,0]})
                    if len(uy)==1 and len(uz)==0:
                        plotinfo.update({'axis_value':uy[0]})
                    elif len(uy)==0 and len(uz)==1:
                        plotinfo.update({'axis_value':uz[0]})
                    else:
                        plotinfo.update({'axis_value':None})

                elif len(ux)<=1 and len(uy)>1 and len(uz)<=1:
                    log.info('Replicating y to 1D')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[0,1,0]})
                    if len(ux)==1 and len(uz)==0:
                        plotinfo.update({'axis_value':ux[0]})
                    elif len(ux)==0 and len(uz)==1:
                        plotinfo.update({'axis_value':uz[0]})
                    else:
                        plotinfo.update({'axis_value':None})
                
                elif len(ux)<=1 and len(uy)<=1 and len(uz)>1:
                    log.info('Replicating z to 1D')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[0,0,1]})
                    if len(ux)==1 and len(uy)==0:
                        plotinfo.update({'axis_value':ux[0]})
                    elif len(ux)==0 and len(uy)==1:
                        plotinfo.update({'axis_value':uy[0]})
                    else:
                        plotinfo.update({'axis_value':None})
                
            if plotinfo['plot_Dim']==1:
                if len(ux)==1 and len(uy)==0 and len(uz)==0:
                    log.info('Found x 1D point')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[1,0,0]})
                    plotinfo.update({'axis_value':None})
                
                elif len(ux)==0 and len(uy)==1 and len(uz)==0:
                    log.info('Found y 1D point')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[0,1,0]})
                    plotinfo.update({'axis_value':None})

                if len(ux)==0 and len(uy)==0 and len(uz)==1:
                    log.info('Found z 1D point')                    
                    plotinfo.update({'plot_Dim':1})
                    plotinfo.update({'axis_info':[0,0,1]})
                    plotinfo.update({'axis_value':None})

        except Exception as e:
            log.error('Processing Data into dimension {}'.format(e))
            return plotinfo
        try:
            if plotinfo['plot_Dim']==3:         
                axis_info=plotinfo['axis_info']   
                (xv,yv,zv)=(None,None,None)            
                (nx,ny,nz)=(0,0,0)
                dfxyz=[]
                if axis_info==[1,2,3]:                
                    xv, yv = numpy.meshgrid(numpy.asfarray(ux), numpy.asfarray(uy), indexing='ij')
                    (nx,ny)=xv.shape
                    #print('xv type:',type(xv))
            
                    xv=numpy.asfarray(xv) #are integers only...
                    yv=numpy.asfarray(yv)
                    zv=numpy.asfarray(yv.copy())
                    dfxyz=[]
                    for dfx,dfy,dfz,ig_x,ig_y,ig_z in zip(df[xaxis],df[yaxis],df[zaxis],dfaxisignore_x,dfaxisignore_y,dfaxisignore_z):
                        if ig_x==False and ig_y==False and ig_z==False:
                            dfxyz.append([dfx,dfy,dfz])
                    #print('xv type:',type(xv))
                    for iii in range(nx):
                        for jjj in range(ny):
                            # treat xv[i,j], yv[i,j]
                            zv[iii,jjj] =  numpy.NaN #0.0
                            for xyz in dfxyz:
                                if xyz[0]==xv[iii,jjj] and xyz[1]==yv[iii,jjj]:                                  
                                    zv[iii,jjj]=float(xyz[2])   #just passing int value
                                    #print('zv value',zv[iii,jjj],xyz[2])
                                    
                            
                #print('3D dfxyz:',dfxyz)
                plotinfo.update({'dfxyz':dfxyz})    
                plotinfo.update({'xv':xv})
                plotinfo.update({'yv':yv})
                plotinfo.update({'zv':zv})
                plotinfo.update({'nx':nx})
                plotinfo.update({'ny':ny})
                plotinfo.update({'nz':nz})
                
            elif plotinfo['plot_Dim']==2:            
                axis_info=plotinfo['axis_info']
                (xv,yv,zv)=(None,None,None)            
                (nx,ny,nz)=(0,0,0)
                dfxyz=[]
                if axis_info==[1,2,0]:                
                    xv, yv = numpy.meshgrid(ux, uy, indexing='ij')
                    nx=len(xv)
                    ny=len(yv)
                    nz=0                
                    for dfx,dfy,ig_x,ig_y in zip(df[xaxis],df[yaxis],dfaxisignore_x,dfaxisignore_y):
                        if ig_x==False and ig_y==False:
                            dfxyz.append([dfx,dfy,0])
                elif axis_info==[1,0,2]:                                
                    xv, zv = numpy.meshgrid(ux, uz, indexing='ij')
                    nx=len(xv)
                    ny=0
                    nz=len(zv)
                    for dfx,dfz,ig_x,ig_z in zip(df[xaxis],df[zaxis],dfaxisignore_x,dfaxisignore_z):
                        if ig_x==False and ig_z==False:                
                            dfxyz.append([dfx,0,dfz])
                elif axis_info==[0,1,2]:                  
                    yv, zv = numpy.meshgrid(uy, uz, indexing='ij')
                    nx=0
                    ny=len(yv)
                    nz=len(zv)
                    for dfy,dfz,ig_y,ig_z in zip(df[yaxis],df[zaxis],dfaxisignore_y,dfaxisignore_z):
                        if ig_y==False and ig_z==False:
                            dfxyz.append([0,dfy,dfz])

                plotinfo.update({'dfxyz':dfxyz})
                plotinfo.update({'xv':xv})
                plotinfo.update({'yv':yv})
                plotinfo.update({'zv':zv})
                plotinfo.update({'nx':nx})
                plotinfo.update({'ny':ny})
                plotinfo.update({'nz':nz})
            
            elif plotinfo['plot_Dim']==1:            
                axis_info=plotinfo['axis_info']
                (xv,yv,zv)=(None,None,None)            
                (nx,ny,nz)=(0,0,0)
                dfxyz=[]
                if axis_info==[1,0,0]:                
                    enum=range(1,len(ux)+1)
                    xv, yv = numpy.meshgrid(enum, ux, indexing='ij')
                    nx=len(xv)
                    ny=len(yv)
                    nz=0
                    for dfx,ig_x in zip(df[xaxis],dfaxisignore_x):
                        if ig_x==False:                
                            dfxyz.append([dfx,0,0])
                elif axis_info==[0,1,0]:                
                    enum=range(1,len(uy)+1)
                    xv, yv = numpy.meshgrid(enum, uy, indexing='ij')
                    nx=len(xv)
                    ny=len(yv)
                    nz=0
                    for dfy,ig_y in zip(df[yaxis],dfaxisignore_y):
                        if ig_y==False:                
                            dfxyz.append([0,dfy,0])
                elif axis_info==[0,0,1]:                
                    enum=range(1,len(uz)+1)
                    xv, yv = numpy.meshgrid(enum, uz, indexing='ij')
                    nx=len(xv)
                    ny=len(yv)
                    nz=0
                    for dfz,ig_z in zip(df[zaxis],dfaxisignore_z):
                        if ig_z==False:                
                            dfxyz.append([0,0,dfz])

                plotinfo.update({'dfxyz':dfxyz})
                plotinfo.update({'xv':xv})
                plotinfo.update({'yv':yv})
                plotinfo.update({'zv':zv})
                plotinfo.update({'nx':nx})
                plotinfo.update({'ny':ny})
                plotinfo.update({'nz':nz})
            else:
                plotinfo.update({'dfxyz':[None,None,None]})
                plotinfo.update({'xv':None})
                plotinfo.update({'yv':None})
                plotinfo.update({'zv':None})
                plotinfo.update({'nx':None})
                plotinfo.update({'ny':None})
                plotinfo.update({'nz':None})
            if plotinfo['plot_Dim']>=1:
                if ppp['Reverse_Data_Series']==True:
                    txv=self.transpose_matrix(xv)
                    tyv=self.transpose_matrix(yv)
                    tzv=self.transpose_matrix(zv)
                    plotinfo.update({'xv':txv})
                    plotinfo.update({'yv':tyv})
                    plotinfo.update({'zv':tzv})

        except Exception as e:
            log.error('axisinfo: {} Dim:{}'.format(axis_info,plotinfo['plot_Dim']))
            log.error('Processing Data into vectors: {}'.format(e))
            return plotinfo

        plotinfo.update({'Reverse_Data_Series':ppp['Reverse_Data_Series']})
        return plotinfo
                       
           
        
    def get_list_of_values(self,df,variable):  
        valuesList=[]  
        vals=df[variable].values
        for aval in vals:
            if aval not in valuesList:
                valuesList.append(aval)
        return valuesList

    def plot_colorMaps(self,cmap):
        fig, ax = matplotlib.pyplot.subplots(figsize=(4,0.4))
        col_map = matplotlib.pyplot.get_cmap(cmap)
        matplotlib.colorbar.ColorbarBase(ax, cmap=col_map, orientation = 'horizontal')
        matplotlib.pyplot.show()    

    def Colormap_info(self,aplot,plotinfo): 
        colormap_dict={}
        ppp=self.Plot_dict[aplot]                
        #'Colormap':{'Colormap_Type':'turbo','Colormap_Reverse':False,'Colormap_Active':True}                
        cmtype=ppp['Colormap']['Colormap_Type']                
        if ppp['Colormap']['Colormap_Reverse']==True:
            cmlist=matplotlib.pyplot.colormaps()
            if cmtype+'_r' in cmlist: # if normal replace reversed if there is reversed
                cmtype=cmtype+'_r'   
            elif '_r' in cmtype: #if reversed replace with normal
                if cmtype.strip('_r') in cmlist:
                    cmtype=cmtype.strip('_r')
        #get active colormap mask
        if ppp['Colormap']['Colormap_Active']==True:
            val=1
        else:
            val=0
        #Selection done after
        
        if plotinfo['plot_Dim']==3:    
            colormap_dict.update({ppp['Axis_Z']['Axis_Data_Key']:[matplotlib.pyplot.cm.get_cmap(cmtype).copy(),val]}) 
        elif plotinfo['plot_Dim']==2:        
            colormap_dict.update({ppp['Axis_Y']['Axis_Data_Key']:[matplotlib.pyplot.cm.get_cmap(cmtype).copy(),val]}) 
        else:
            colormap_dict.update({ppp['Axis_Z']['Axis_Data_Key']:[matplotlib.pyplot.cm.get_cmap(cmtype).copy(),val]}) 
        plotinfo.update({'colormap_dict':colormap_dict})
            
        cmrange=ppp['Colormap']['Colormap_Range']
        plotinfo.update({'Colormap_Range':cmrange})
        
        #self.plot_colorMaps(cmtype)
        return plotinfo

    def get_array_of_variable(self,variable,zeroval=0,logshow=True):
        try:
            df=self.get_datafield_of_variable(variable,zeroval,logshow)        
            return numpy.asarray(df)
        except:
            return numpy.empty(shape=(0))
    
    def get_filter_df(self,afilter,logshow=False):
        df=self.csv_data.copy()
        try:                                    
            aquery = df.query(afilter)  
            if logshow==True:          
                log.info('Dataframe Got filtered df for {}'.format(afilter)) 
                log.info('Filtered Dataframe size is {}'.format(len(aquery)))            
            return aquery 
        except:
            if logshow==True:          
                log.info('Dataframe Query made error for'.format(afilter))
            return df
    def filter_data_query(self,adf,afilter):
        try:
            aquery = adf.query(afilter)
        except:
            aquery = adf
        return aquery

    def get_datafield_of_variable(self,variable,zeroval=0,logshow=True):
        df=self.csv_data_filtered        
        fields=self.get_fields_in_csv_data(df)
        variable,_=self.get_filter_math_var_name(variable)
        if variable in fields:
            return df[variable]
        else:            
            filtered=self.get_filtered_data_indf_for_var(variable)
            try:
                if filtered.empty==False:
                    return filtered
            except:
                pass
            if logshow==True:
                log.info('No data field available on csv for field {}'.format(variable))  
            # must return same size 
            if zeroval=='__empty__':
                return numpy.empty(shape=(0)) #return empty array
            return self.get_df_filled(df,variable,zeroval,logshow)            

    def get_df_filled(self,df,variable,zeroval=0,logshow=False):
        aaa={}       
        fields=self.get_fields_in_csv_data(df)   
        #log.info('{} aaa-> {}'.format(variable,aaa))  
        lendf=len(df[fields[0]])
        info=[]
        for iii in range(0,lendf):
            info.append(zeroval)#numpy.NaN)
        aaa.update({variable:info})
        ppp=pd.DataFrame(aaa)
        if logshow==True:
            log.info('Setting field {} to {}'.format(variable,zeroval))  
        return ppp[variable]
    
    def get_filtered_data_indf_for_var(self,variable):
        df=self.csv_data
        try:            
            avar,afilter=self.get_filter_var_name(variable)
            avar,_=self.get_filter_math_var_name(avar)    
            #if it is a query input
            aquery = df.query(afilter)            
            log.info('Variable ({}) found query data with Filter: {}'.format(avar,afilter))
            thedf=aquery[avar]
            return thedf 
        except:
            if variable!='':
                log.warning('Query data not found for variable: ({})'.format(variable))
            return {}
    
    def get_math_df_data(self,Text):
        mathdir=math.__dict__
        mathdict={}
        for iii in mathdir:
            if '_' not in iii:
                mathdict.update({str(iii):iii})
        print(mathdict)

    def get_filter_math_var_name(self,variable):
        try:
            variable,_=self.get_filter_var_name(variable,filtereq=False) #removes filter
            rematch=re.search('(.+)=(.+?)$',variable) # variable {filter}            
            #print(rematch.groups())
            #print(rematch.groups()[0],'\n',rematch.groups()[1])
            if rematch.group():
                thevarname=rematch.groups()[0]
                the_equation=rematch.groups()[1]  
                thevarname=thevarname.strip()          
            return thevarname,the_equation
        except:            
            return variable,''
    
    def has_math_equation(self,variable):
        try:
            variable,_=self.get_filter_var_name(variable,filtereq=False) #removes filter
            rematch=re.search('(.+)=(.+?)$',variable) # variable {filter}            
            #print(rematch.groups())
            #print(rematch.groups()[0],'\n',rematch.groups()[1])
            if rematch.group():
                thevarname=rematch.groups()[0]
                the_equation=rematch.groups()[1]
                #print('thevarname-->',thevarname)
                restr=re.search('^([a-zA-Z]\w*)',thevarname) # variable {filter}            
                #print('made search ->',restr,restr.group(),restr.groupdict(),restr.groups())
                if restr.group():                    
                    varname=str(restr.group())
                    #print('varname-->',varname)
                    forbiddenvars=self.get_dict_key_list(self.globlsparam['__builtins__'] )
                    #print('found it?-->',forbiddenvars[0])
                    if thevarname.strip()!=varname.strip():
                        log.warning('Invalid math variable Name: {}'.format(thevarname))
                        return False                      
                    if thevarname in forbiddenvars:
                        log.warning('Invalid math variable Name: {}, it is already a defined math function!'.format(thevarname))
                        return False                      
            #print('Returning True')
            return True
        except:            
            return False
    def set_math_definitions_dict(self,math_definitions):
        math_deflist=math_definitions.strip().split('|')
        self.math_definitionsvd={}
        self.math_definitionseq={}
        if self.is_list(math_deflist)==True:
            for equa in math_deflist:
                if self.has_math_equation(equa):
                    avar,the_eq=self.get_filter_math_var_name(equa)
                    try:
                        #self.eval_math_to_df
                        val=self.evaluate_equation(the_eq,self.math_definitionsvd,True)
                        self.math_definitionsvd.update({avar:val})   
                        self.math_definitionseq.update({avar:the_eq})                        
                        log.info('Additional definition {} set into math! :)'.format(avar))                        
                    except Exception as e:                        
                        log.error('Error evaluating Additional math equation: {}'.format(equa))                        
                        log.error(e) 
        
    def eval_math_to_df(self,aplot):
        ppp=self.Plot_dict[aplot]
        df=self.csv_data_original        
        try:            
            #Evaluate Math definitions first then declarations before all plots
            math_definitions=ppp['Additional']['math_definitions']
            self.set_math_definitions_dict(math_definitions)
            math_declarations=ppp['Additional']['math_declarations']
            for equa in math_declarations:
                if self.has_math_equation(equa):
                    avar,the_eq=self.get_filter_math_var_name(equa)
                    try:
                        m_df=self.eval_data_into_a_df(equa,logshow=True,use_filtered=False)
                        log.info('Additional Variable {} set into Data! :)'.format(avar))
                        self.math_definitionseq.update({avar:the_eq})
                        #add column to data to dfs
                        df[avar]=m_df
                        self.csv_data=df
                        self.csv_data_filtered=df.copy()
                    except Exception as e:                        
                        log.error('Error evaluating Additional math equation: {}'.format(equa))                        
                        log.error(e)                        
                    
            xaxis=ppp['Axis_X']['Axis_Data_Key']
            yaxis=ppp['Axis_Y']['Axis_Data_Key']
            zaxis=ppp['Axis_Z']['Axis_Data_Key']
            the_axis=[xaxis,yaxis,zaxis]
            has_math=[self.has_math_equation(xaxis),self.has_math_equation(yaxis),self.has_math_equation(zaxis)]
            for xxx_axis,hasm in zip(the_axis,has_math):            
                axis_fn,filterx=self.get_filter_var_name(xxx_axis)            
                # if in original datafield i.e in csv file
                if hasm==True:
                #if self.is_variable_in_datafield(axis_fn,use_original=True)==False and hasm==True:
                    axis_weq,filter=self.get_filter_var_name(xaxis,filtereq=False) 
                    axis_fn,the_eq=self.get_filter_math_var_name(axis_weq)                                                            
                    #evaluate eq
                    try:
                        axis_df=self.eval_data_into_a_df(axis_weq,logshow=True,use_filtered=False)
                        log.info('Variable {} set into Data! :)'.format(axis_fn))
                    except Exception as e:
                        axis_df=self.get_df_filled(df,axis_fn,zeroval=numpy.NaN,logshow=False)
                        log.error('Error evaluating math equation: {}'.format(axis_weq))                        
                        log.error(e)
                        log.warning('Variable {} set to Data! Data set to {}'.format(axis_fn,axis_df[0]))

                    #add column to data to dfs
                    df[axis_fn]=axis_df
                    self.csv_data=df
                    self.csv_data_filtered=df.copy()
                    #log.info('is_variable_in_datafield(axis_fn)={}\n data:{}'.format(self.is_variable_in_datafield(axis_fn),self.csv_data[axis_fn]))
            
        except Exception as e:
            log.error('Error evaluating math!')
            log.error(e)
            
    def eval_data_into_a_df(self,axis_weq,logshow=True,use_filtered=False):
        axis_fn,the_eq=self.get_filter_math_var_name(axis_weq)
        if self.is_variable_in_datafield(axis_fn,use_original=True)==True and axis_fn in self.initial_csv_fields: 
            axis_df=self.get_datafield_of_variable(axis_fn,zeroval=numpy.NaN,logshow=logshow)
            if logshow==True:
                log.warning('{} already defined in csv data! Values are being overritten!'.format(axis_fn))                  
                #log.warning('{} already defined in csv data! Change variable name to a non existent!'.format(axis_fn))                  
            #return axis_df 
        #else:     
        vars_dict,_,lendf=self.get_vars_dict(use_filtered,the_eq) 

        #log.info('vars_dict: {}'.format(vars_dict))
        eval_data={}    
        info=[]
        counterrors=0
        goterror=''
        for iii in range(0,lendf):
            try:
                vd=self.get_vd_from_dict(vars_dict,iii)
                theval=self.evaluate_equation(the_eq,vd,logshow=True)                
                #theval=eval(the_eq,vd)
                #log.info('vd({})={} eval={}'.format(iii,vd,theval))
                if type(theval)==type('hi'):
                    theval=float(theval)
            except Exception as e:
                counterrors=counterrors+1  
                goterror=e              
                theval=numpy.NaN  
            info.append(theval)          
        if counterrors>0:
            log.error('Made {} Errors evaluating {}: {}'.format(counterrors,axis_weq,goterror))
        eval_data.update({axis_fn:info})            
        ppp=pd.DataFrame(eval_data)            
        axis_df=ppp[axis_fn]            
        return axis_df

    def get_vars_dict(self,use_filtered,the_eq):
        vars_dict={}
        try:
            if use_filtered==True:                                     
                df=self.csv_data_filtered  
            else:
                df=self.csv_data  
            fields=self.get_fields_in_csv_data(df)
            
            lendf=len(df[fields[0]])
            for fff in fields:
                if fff in the_eq:
                    vars_dict.update({fff:df[fff].tolist()})
        except:
            pass
        return vars_dict,df,lendf

    def make_df_var_list(self,*args):
        alist=[]
        for var in args:
            vardf=self.get_datafield_of_variable(var,numpy.NaN,True)
            if vardf!=None:
                if self.is_all_NaN_values(vardf)==False:
                    alist.append(vardf.tolist())
        return alist


    def listrange(self,*args):
        #returns list with range either int or float
        try:
            return list(range(*args))
        except:
            try:
                return self.floatrange(*args)
            except:
                return []
    
    def floatrange(self,ini,end,delta=1,numrep=2000):
        #return list range with items from ini to end spaced delta, with numrep maximum size
        if ini==end:
            return []
        ddd=numpy.abs(delta)
        arange=[]
        if ini<=end:
            val=ini
            nnn=0
            while (val<=end and nnn<numrep):
                if (val<end):
                    arange.append(val)
                val=val+ddd
                nnn=nnn+1
        elif ini>end:
            val=ini
            nnn=0
            while (val>end and nnn<numrep):
                if (val>end):
                    arange.append(val)
                val=val-ddd
                nnn=nnn+1
        return arange
    
    def numrange(self,ini,delta,num_element):
        #return list range with num_element items spaced delta
        return self.listrange(ini,ini+delta*numpy.abs(num_element),delta)

    def evaluate_equation(self,atxt,vardict,logshow=False):        
        try:
            #you can declare also a local function within
             
            globlsparam = self.recursive_copy_dict(self.globlsparam)
            for avar in self.math_definitionsvd:
                globlsparam.update({avar:self.math_definitionsvd[avar]}) 
            for avar in vardict:
                globlsparam.update({avar:vardict[avar]})                        
            #globlsparam = {'__builtins__' : None}  # -> Nothing except simple math: add subtract multiply                       
            #value=eval(atxt) # -> is allowing anything to run in the line (Safety critical) -> all program functions too
            value=eval(atxt,globlsparam)             
            #print("Evaluated Value:",value)            
            #code = compile("4 / 3 * math.pi * math.pow(25, 3)", "<string>", "eval")
            #value =eval(code)
            return value
            
        except Exception as e:
            if logshow==True:
                log.error("Bad math function code: {} with {}".format(atxt),vardict)
                log.error(e)    
                functionlist=self.get_dict_key_list(globlsparam['__builtins__'])
                log.error('Available functions:\n{}\n'.format(functionlist))    
            return numpy.NaN

    def get_vd_from_dict(self,vars_dict,iii):
        vd={}
        for var in vars_dict:
            vd.update({var:vars_dict[var][iii]})
        return vd

    def get_filter_var_name(self,variable,filtereq=True):        
        try:
            rematch=re.search('(.+)\{(.+?)\}',variable) # variable {filter}            
            #print(rematch.groups())
            #print(rematch.groups()[0],'\n',rematch.groups()[1])
            if rematch.group():
                avar=rematch.groups()[0]
                afilter=rematch.groups()[1]
                if filtereq==True:
                    avar,_=self.get_filter_math_var_name(avar)
                avar=avar.strip()
            return avar,afilter 
        except:            
            return variable,''

    def is_variable_in_datafield(self,variable,use_original=False):
        if use_original==False:
            df=self.csv_data        
        else:
            #log.info('-------------------use original---------------')
            df=self.csv_data_original        
        fields=self.get_fields_in_csv_data(df)
        if variable in fields:
            return True
        else:
            return False
    
    def get_error_dxyzsized(self,errdfy,Err_Y_Use_key,plotinfo):
        #ppp=self.Plot_dict[aplot]
        allfilter=plotinfo['allfilter']                           
        df=self.csv_data_filtered
        #log.info('df len: {}'.format(len(df)))  
        xaxis=plotinfo['xaxis']
        yaxis=plotinfo['yaxis']
        zaxis=plotinfo['zaxis']
        dfxyzor=plotinfo['dfxyz']
        dfaxisignore_x=plotinfo['dfaxisignore_x']
        dfaxisignore_y=plotinfo['dfaxisignore_y']
        dfaxisignore_z=plotinfo['dfaxisignore_z']
        axis_info=plotinfo['axis_info'] 
                 
        dfxyz=[]
        dferry=[]  
        erry,_=self.get_filter_math_var_name(Err_Y_Use_key)
        dff=self.filter_data_query(df,allfilter)
        #log.info('len dff {}=len dfxyz {}? {}'.format(len(dff),len(dfxyzor),allfilter))    
        #log.info('~~~~~~until here {},{},{},axis_info{},{}'.format(xaxis,yaxis,zaxis,axis_info,erry))                
        errdfy={erry:numpy.asarray(errdfy)}
        #log.info('len errdfy->{} len df {}, len dfxyz {}'.format(len(errdfy[erry]),len(df),len(dfxyzor)))        
        if plotinfo['plot_Dim']==3:                     
            if axis_info==[1,2,3]:                
                for derry,dfx,dfy,dfz,ig_x,ig_y,ig_z in zip(errdfy[erry],df[xaxis],df[yaxis],df[zaxis],dfaxisignore_x,dfaxisignore_y,dfaxisignore_z):
                    if ig_x==False and ig_y==False and ig_z==False:
                        dfxyz.append([dfx,derry,0])
                        dferry.append(derry)
        elif plotinfo['plot_Dim']==2:                        
            if axis_info==[1,2,0]:                                
                for derry,dfx,dfy,ig_x,ig_y in zip(errdfy[erry],df[xaxis],df[yaxis],dfaxisignore_x,dfaxisignore_y):
                    if ig_x==False and ig_y==False:
                        dfxyz.append([dfx,derry,0])                        
                        dferry.append(derry)
            elif axis_info==[1,0,2]:                                                
                for derry,dfx,dfz,ig_x,ig_z in zip(errdfy[erry],df[xaxis],df[zaxis],dfaxisignore_x,dfaxisignore_z):
                    if ig_x==False and ig_z==False:                
                        dfxyz.append([dfx,derry,0])
                        dferry.append(derry)
            elif axis_info==[0,1,2]:                                  
                for derry,dfy,dfz,ig_y,ig_z in zip(errdfy[erry],df[yaxis],df[zaxis],dfaxisignore_y,dfaxisignore_z):
                    if ig_y==False and ig_z==False:
                        dfxyz.append([dfy,derry,0])
                        dferry.append(derry)
        elif plotinfo['plot_Dim']==1:                        
            if axis_info==[1,0,0]:                                
                for derry,dfx,ig_x in zip(errdfy[erry],df[xaxis],dfaxisignore_x):
                    if ig_x==False:                
                        dfxyz.append([dfx,derry,0])                       
                        dferry.append(derry)
            elif axis_info==[0,1,0]:                                
                for derry,dfy,ig_y in zip(errdfy[erry],df[yaxis],dfaxisignore_y):
                    if ig_y==False:                
                        dfxyz.append([dfy,derry,0])                      
                        dferry.append(derry)
            elif axis_info==[0,0,1]:                                
                for derry,dfz,ig_z in zip(errdfy[erry],df[zaxis],dfaxisignore_z):
                    if ig_z==False:                
                        dfxyz.append([dfz,derry,0])
                        dferry.append(derry)
        #log.info('öööööööööööö is {}=len dfxyz {}?'.format(len(dfxyz),len(dfxyzor)))        
        #use dfxyz only in 1,2,0 conf to get error message on same size
        avx,avy=self.get_xy_neovectors_fromdfxyz(dfxyz,[1,2,0],plotinfo['Reverse_Data_Series'])
        #log.info('->neo vects:{}\n{}'.format(avx,avy))
        return dferry,avx,avy  
        