import logging
from multiprocessing.sharedctypes import Value
from xmlrpc.client import boolean
from PyQt5 import QtCore, QtGui, QtWidgets
import re

# set up logging to file - see previous section for more details
log = logging.getLogger('') #root logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s',
                    datefmt='%y-%m-%d %H:%M')
# define a Handler which writes INFO messages or higher to the sys.stderr
tvconsole = logging.StreamHandler()
tvconsole.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('[%(levelname)s] (%(threadName)-10s) %(message)s')
# tell the handler to use this format
tvconsole.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(tvconsole)




class treeview_functions(QtWidgets.QWidget):   
    data_change=QtCore.pyqtSignal(list,str,str,str)   

    def Signal_Data_Change(self,track,val,valtype,subtype):
        #log.info('cTV Emmiting: {} {} {} {}'.format(track,val,valtype,subtype))
        self.data_change.emit(track,val,valtype,subtype)

    def __init__(self,treeviewobj,Plot_Struct,Plot_struct_mask,Plot_ID=None,Reftrack=[], *args, **kwargs):   
        super(treeview_functions, self).__init__(*args, **kwargs)             
        self.__name__="Treeview Functions"
        if isinstance(treeviewobj,QtWidgets.QTreeView):
            self.treeviewobj=treeviewobj
        else:
            raise Exception('TreeView object is Not a {} object'.format(type(QtWidgets.QTreeView)))        
        self.modelobj=self.Create_Plot_Model_Treeview(self.treeviewobj)
        self.Plot_struct=Plot_Struct #all info
        self.Plot_struct_mask=Plot_struct_mask
        self._last_value_selected=None
        self.Plot_ID=Plot_ID
        self.Reftrack=Reftrack
        #displayed on treeview
        self.set_show_dict()
        '''
        if len(Show_dict)==0:
            self.Show_dict=self.get_dictionary_from_structlist(self.Plot_struct,self.Plot_ID)            
        else:            
            self.Show_dict=Show_dict     
        '''
        self.Plot_struct_types=self.get_types_struct(self.Plot_struct)   
        self.Show_dict_types=self.get_types_struct(self.Show_dict)   
        self.icon_dict={}
        self.backgroundcolor_dict={}
        #print(self.Show_dict_types)
        
        self.refresh_Treeview(self.Show_dict,self.modelobj,self.treeviewobj) 
        # connect action
        self.treeviewobj.clicked.connect(self.treeview_OnClick)            
        self.treeviewobj.expanded.connect(self.treeview_Expanded)   
        self.treeviewobj.collapsed.connect(self.treeview_Expanded)
        #self.treeviewobj.expandAll()    
        self.Expand_to_Depth(1)
    
    def treeview_Expanded(self):
        self.treeviewobj.resizeColumnToContents(0)
        testtrack=['Frequency_X', 'Plots', 'P3', 'Axis_X', 'Axis_Auto_Range']
        testtrack=['Frequency_X', 'Plots']
        itm,itmindex,itmtracklist,itmindextrack=self.get_item_from_track(self.treeviewobj.model(),testtrack)
        #if itm!=None: 
        #    log.info('Test found-------------------> {} {}'.format(itm.text(),testtrack))
        #else:
        #    log.info('Test found-------------------> {} {}'.format(itm,testtrack))
        self.Set_items_Colors(self.treeviewobj.model(),testtrack,color=None)
    
    def set_show_dict(self):
        if len(self.Reftrack)==0:
            showdict=self.get_dictionary_from_structlist(self.Plot_struct,self.Plot_ID)      
            #print('From len 0 showdict:\n',showdict)      
        else:
            showdict=self.get_tracked_value_in_struct(self.Reftrack,self.Plot_struct)            
            #print('From else showdict:\n',showdict)      
        if self.is_dict(showdict)==True:
            self.Show_dict=showdict
        else:
            self.Show_dict=self.Plot_struct


    def get_types_struct(self,dict_struct):         
        if self.is_list(dict_struct)==True:
            type_Struct=[]      
            for aplot in dict_struct:
                type_Struct.append(self.get_types_struct(aplot))                                
        elif self.is_dict(dict_struct)==True:
            type_Struct={}
            for aplot in dict_struct:    
                if self.is_dict(dict_struct[aplot])==True:  
                    nts=self.get_types_struct(dict_struct[aplot])
                    type_Struct.update({aplot:nts})
                else:
                    type_Struct.update({aplot:str(type(dict_struct[aplot]))})
        else:
            type_Struct={}
            type_Struct.update({str(dict_struct):str(type(dict_struct))})
        
        return type_Struct

    def get_gentrack_from_localtrack(self,track):
        gentrack=self.Reftrack.copy()
        for iii in track:
            gentrack.append(iii)
        return gentrack    
    
    def get_localtrack_from_gentrack(self,track):
        gentrack=self.Reftrack.copy()
        trackc=track.copy()
        for iii in track:
            if track[iii]==gentrack[iii]:
                trackc.pop(0)
        return trackc   

    def get_dictionary_from_structlist(self,plot_struct,Plot_ID=None):        
        if self.is_list(plot_struct)==True:
            for adict in plot_struct:
                if adict['ID']==Plot_ID:
                    #print('get my dict Found ID',Plot_ID)
                    return adict.copy()
        elif self.is_dict(plot_struct)==True or Plot_ID==None:
            #print('get my dict nochange is dict',Plot_ID)
            return plot_struct.copy()
        else:
            return {}        
    
    def refresh_Treeview(self,dict_struct,modelobj,treeviewobj):           
        if isinstance(treeviewobj,QtWidgets.QTreeView):
            self.set_show_dict()             
            modelobj.clear()        
            modelobj=self.Create_Plot_Model_Treeview(treeviewobj)                    
            self.Plot_importData_to_Tree(dict_struct,modelobj,treeviewobj)          
            self.set_treeview_styles(treeviewobj.model())
        else:
            raise Exception('TreeView object is Not a {} object'.format(type(QtWidgets.QTreeView)))
    
    def set_treeview_styles(self,modelobj):
        #log.info('********************Entered treeview style {}'.format(modelobj.rowCount()))
        try:
            if isinstance(modelobj,QtCore.QAbstractItemModel):
                self.set_style_to_All_items(modelobj,None,None)
        except Exception as e:
            log.error('Set treeview styles: {}'.format(e))
       
    
    def set_style_to_All_items(self,modelobj,itmindex=None,parentindex=None):        
        if itmindex==None and parentindex==None:
            itmindex=modelobj.index(0, 0) #first element
        if parentindex==None:
            count=itmindex.model().rowCount(itmindex)
            parentindex=itmindex
        else:
            count=itmindex.model().rowCount(parentindex)     
        if itmindex==None:
            return                  
        for iii in range(count):            
            citmindex=itmindex.model().index(iii, 0, parentindex)               
            itm=itmindex.model().itemFromIndex(citmindex)                                                               
            self.set_item_style(itm)
            childcount=citmindex.model().rowCount(citmindex)            
            if childcount>0:
                #log.info('----------->Children {}, of {}?'.format(childcount,itm.text()))
                gcitmindex=citmindex.model().index(0, 0, citmindex)
                self.set_style_to_All_items(modelobj,gcitmindex,citmindex)

    def set_Icons(self,icondict):
        self.icon_dict=icondict 
    
    def set_BackgroundColors(self,backgroundcolor_dict):
        self.backgroundcolor_dict=backgroundcolor_dict


    def set_icon_to_item(self,itm):
        try:
            for itxt in self.icon_dict:
                if itm.text()==itxt:            
                    itm.setIcon(self.icon_dict[itxt])
        except:
            pass
    
    def set_backgroundcolor_to_item(self,itm):
        try:
            for itxt in self.backgroundcolor_dict:
                if itm.text()==itxt:                                
                    itm.setBackground(self.backgroundcolor_dict[itxt])                    
        except:
            pass
   
    def set_tooltiptext(self,index):
        reslist,resvallist,_=self.get_item_restriction_resval(index)    
        for res,resval in zip(reslist,resvallist):
            itm = index.model().itemFromIndex(index) 
            if res in ['limited_selection','is_list_item_limited_selection']:                
                itm.setToolTip('Options: {}'.format(resval))
            #else:
            #    itm.setToolTip('')

        
    def treeview_OnClick(self,index):
        #Set items editable        
        self.treeviewobj.resizeColumnToContents(0)
        indexitem=index.siblingAtColumn(0)
        itm=indexitem.model().itemFromIndex(indexitem)        
        indexvalue=index.siblingAtColumn(1)
        valueitem=indexvalue.model().itemFromIndex(indexvalue)        
        indextype=index.siblingAtColumn(2)
        typeitem=indextype.model().itemFromIndex(indextype)
        itm.setEditable(False)
        typeitem.setEditable(False)        
        self.set_icon_to_item(itm)
        self.set_tooltiptext(index)
        
        if index==indexvalue:    
            # get checkbox if boolean 
            if typeitem.text()==str(type(True)):                
                valueitem.setCheckable(True) 
                self.set_checkbox_value(valueitem)                                
            else:
                valueitem.setCheckable(False) 

            # No edits if is a dictionary type  
            if typeitem.text()==str(type({})):
                valueitem.setEditable(False)
            else:
                valueitem.setEditable(True)            
            self.edit_a_treeview_Item(index)            
            
        elif index==indextype or index==indexitem:    
            self.restore_a_treeview_Item(index)        

    def set_checkbox_value(self,valueitem):        
        if self.str_to_bool(valueitem.text())==True:
            valueitem.setCheckState (True)                     
        else:                    
            valueitem.setCheckState(False)


    def track_key_tree(self,anitem):
        track=[]
        anitemindex=anitem.index()
        indexitem=anitemindex.siblingAtColumn(0)
        track.append(indexitem.model().itemFromIndex(indexitem).text())        
        item=indexitem.model().itemFromIndex(indexitem)
        parent=item.parent()
        while parent!=None:
            try:
                track.append(parent.text())
                item=parent
                parent=item.parent()
            except:                
                pass  
        track.reverse()          
        return track  

    def edit_a_treeview_Item(self,index):    
        #print('edit_a_treeview_Item',modelobj,treeviewobj)                 
        itm = index.model().itemFromIndex(index)        
        val=itm.text()                     
        #print('edit index set:',index.data())
        self._last_value_selected=val        
        index.model().itemChanged.connect(lambda: self.Item_data_changed(index,val))        

    
    def Set_items_Colors(self,modelobj,track,color=None):
        try:
            if isinstance(modelobj,QtCore.QAbstractItemModel):
                if color==None:
                    color=QtGui.QColor(255, 0, 0, 1)                  
                itm,itmindex,_,_=self.get_item_from_track(modelobj,track)
                itm_txt=itm.text()            
                #recheck the item
                #itm = itmindex.model().itemFromIndex(itmindex)
                self.treeviewobj.childAt()
                self.treeviewobj.model().setItemData(itmindex,QtCore.Qt.ItemDataRole.BackgroundRole)
                self.treeviewobj.model().setData(itm, QtGui.QBrush(color), QtCore.Qt.ItemDataRole.BackgroundRole)                
                itm.setBackground(color)
                itm.submit()
                log.info('------------------------>Run color test: {} is colored ?'.format(track))
                #itm.setTextAlignment(QtCore.Qt.AlignRight)
                if itm_txt == track[len(track)-1] and itmindex.column()==0:
                    log.info('Set Colors-> {} =? {}'.format(itm_txt,track[len(track)-1]))
                    #modelobj.setData(itm, color, QtCore.Qt.ItemDataRole.DecorationRole)
                    #modelobj.setData(itm, QtGui.QBrush(color), QtCore.Qt.BackgroundRole)
                    #https://www.pythonguis.com/tutorials/pyqt6-qtableview-modelviews-numpy-pandas/
                    
        except:
            #if item not found then returns None itm.text() makes error
            pass
    
    def get_list_of_tracks_of_children(self,parenttrack):
        self.get_gentrack_from_localtrack


    def get_item_from_track(self,modelobj,track):
        if isinstance(modelobj,QtCore.QAbstractItemModel):
            try:
                itmtrack=[]
                itmindextrack=[]
                parent=None
                for ttt,tr in enumerate(track):                    
                    if parent==None:
                        #log.info('the size -> {}'.format(modelobj.rowCount())) 
                        for iii in range(modelobj.rowCount()):
                            itmindex=modelobj.index(iii, 0)                                 
                            itm = modelobj.itemFromIndex(itmindex)    
                            if itm!=None:                
                                #log.info('got this-> {} search for {}'.format(itm.text(),tr))
                                if tr==itm.text():
                                    break
                            else:
                                break
                        if itm==None:
                            break
                        if tr!=itm.text(): # not found
                            break
                    else:
                        #log.info('the size -> {}'.format(modelobj.rowCount(parent))) 
                        for iii in range(modelobj.rowCount(parent)):
                            itmindex=modelobj.index(iii, 0, parent)                             
                            itm = modelobj.itemFromIndex(itmindex)                        
                            if itm!=None:         
                                #log.info('parent got this-> {} search for {}'.format(itm.text(),tr))       
                                if tr==itm.text():
                                    break
                            else:                                    
                                break
                        if itm==None:
                            break
                        if tr!=itm.text(): # not found
                            break                                                                                                     
                    parent=itmindex 
                    parentitm = modelobj.itemFromIndex(parent)                     
                    if parentitm.text()=='ID':
                        parenttxt=parentitm.text()              
                        parent=None
                        continue
                    itmtrack.append(itm)
                    itmindextrack.append(itmindex)
                return itm,itmindex,itmtrack,itmindextrack
            except Exception as e:
                log.error('get item from track: {}'.format(e))
    
    def set_item_style(self,itm):
        try:            
            if itm!=None:  
                icons=self.get_dict_key_list(self.icon_dict)
                bgc=self.get_dict_key_list(self.backgroundcolor_dict)                
                if itm.text() in icons:
                    self.set_icon_to_item(itm)
                if itm.text() in bgc:
                    self.set_backgroundcolor_to_item(itm)
        except:
            pass

    def Item_data_changed(self,index,val):                
        old_value=val #self._last_value_selected        
        #print('tvf Item changed->',index.data(),' old value->',old_value)
        itm = index.model().itemFromIndex(index)         
        new_value=itm.text()       
        selindex=self.treeviewobj.selectedIndexes()           
        self.set_item_style(index.model().itemFromIndex(index.siblingAtColumn(0))) #first column item
        if new_value!=old_value and old_value!=None and index in selindex:            
            indextype=index.siblingAtColumn(2)
            typeitem=indextype.model().itemFromIndex(indextype)
            track=self.track_key_tree(index.model().itemFromIndex(index))                        
            #Here check if value is ok if yes
            valisok=self.check_item_value_for_edit(index,new_value,old_value,self.Show_dict)
            #print('class_TreeViewFunctions Datachanged-> New:',new_value,'Old:',old_value,'Track:',track,'isvalid:',valisok)
            log.info('Data changed -> New:{} Old:{} Track: {} isvalid: {}'.format(new_value,old_value,track,valisok))
            if valisok==True:
                subtype=''                
                if typeitem.text()==str(type([])):                    
                    gentrack=self.get_gentrack_from_localtrack(track)
                    subtype=self.get_listitem_subtype(gentrack)
                new_valwt=self.set_type_to_value(new_value,typeitem.text(),subtype) #Send value with correct type to dictionary                                                    
                #_=self.set_tracked_value_to_dict(gentrack,new_valwt,self.Plot_struct,subtype,False) #doing it inside
                refreshTreeview,self.Show_dict=self.set_tracked_value_to_dict(track,new_valwt,self.Show_dict,subtype)                   
                if refreshTreeview==False:
                    itm.setText(new_value)
                    if typeitem.text()==str(type(True)):
                        self.set_checkbox_value(itm)
                else:                    
                    self.refresh_Treeview(self.Show_dict,self.modelobj,self.treeviewobj) # need to refresh only if value is changed
                #Here send signal to refresh 
                valtype=typeitem.text()
                self.Signal_Data_Change(track,new_value,valtype,subtype)

            else:
                subtype=''
                typestr=typeitem.text()
                if typestr==str(type([])):        
                    gentrack=self.get_gentrack_from_localtrack(track) # <-track is local!            
                    subtype=self.get_listitem_subtype(gentrack)
                old_valwt=self.set_type_to_value(old_value,typeitem.text(),subtype) #Send value with correct type to dictionary
                refreshTreeview,self.Show_dict=self.set_tracked_value_to_dict(track,old_valwt,self.Show_dict,subtype)                
                itm.setText(old_value)
                if typeitem.text()==str(type(True)):
                    self.set_checkbox_value(itm)
        # reset old value        
        self._last_value_selected=None

    def is_item_supposed_to_be_a_list(self,itm):
        reslist,resvallist,_=self.get_item_restriction_resval(itm)    
        for res,resval in zip(reslist,resvallist):            
            if 'is_list_item_' in res or (res=='is_value_type' and resval==str(type([]))):
                return True
        return False

    def get_item_supposed_type_subtype(self,itm):
        subtype=''
        thetype=str(type(''))
        reslist,resvallist,resvalaltlist=self.get_item_restriction_resval(itm)    
        if self.is_item_supposed_to_be_a_list(itm)==False:            
            for res,resval in zip(reslist,resvallist):            
                if res=='is_value_type':
                    thetype=resval
                    break
        else:
            thetype=str(type([]))
            for res,resval in zip(reslist,resvallist):            
                if res=='is_list_item_type':
                    subtype=resval
                    break
        return thetype,subtype

    def get_listitem_subtype(self,track):        
        mask=self.get_mask_for_item(track)
        #log.info('Got for subtype: {} {}'.format(track,mask))
        for mmm in mask:
            keymmm=str(mmm)            
            if '__m__' in keymmm:
                keyval=keymmm.replace('__m__','__mv__')
                keyalt=keymmm.replace('__m__','__ma__')
                if mask[keymmm]=='is_list_item_type':
                    try:
                        malt=mask[keyalt]
                        return [mask[keyval],malt]
                    except:
                        return mask[keyval]
        return ''

    def set_type_to_value(self,val,typestr,subtype=''):        
        if typestr==str(type(1)):
            try:
                tyval=int(val)
            except:
                tyval=str(val)
        elif typestr==str(type(0.1)):
            try:
                tyval=float(val)
            except:
                tyval=str(val)
        elif typestr==str(type(True)):
            try:
                if val in ['1','True','true','yes','Yes']: 
                    tyval=True                     
                elif val in ['0','False','false','no','No']:                    
                    tyval=False
                else:
                    tyval=int(val)
            except:
                tyval=str(val)                
        elif typestr==str(type([])):
            try:
                split=self.str_to_list(val)
                if split!=None:
                    tyval=[]
                    for iii in split:    
                        if self.is_list(subtype)==True:
                            for st in subtype:
                                if st==str(type(0.1)):
                                    iiival=float(iii)
                                    break
                                elif st==str(type(0)):
                                    iiival=int(iii)
                                    break
                                elif st==str(type('')):
                                    iiival=str(iii)
                                    break
                                else:
                                    iiival=iii
                        else:        
                            if subtype==str(type(0.1)):
                                iiival=float(iii)
                            elif subtype==str(type(0)):
                                iiival=int(iii)
                            elif subtype==str(type('')):
                                iiival=str(iii)
                            else:
                                iiival=iii
                        tyval.append(iiival)                    
                else:
                    tyval=str(val)
            except:
                tyval=str(val)
        else:
            tyval=str(val)
        return tyval

    def set_tracked_value_to_dict(self,track,val,dict_struct,subtype,emitsignal=True):
        refreshtreeview=False
        trlist=track.copy()
        selected={}  
        if self.is_list(dict_struct)==True:      
            for aplot in dict_struct:
                if aplot['ID']==trlist[0]:
                    trlist.pop(0)
                    selected=aplot#.copy() #select dictionary
                    while len(trlist)>1:
                        try:
                            selected=selected[trlist[0]]
                            trlist.pop(0)
                        except:
                            break
                    #last tracked is variable
                    if len(trlist)==1:
                        selected.update({trlist[0]:val})
                        # Change title of plot special case
                        #log.debug('setvaltodict_struct Here {} set to {}'.format(trlist[0],val))
                        if trlist[0]=='ID' and len(track)==2:
                            #print('2 Here name is',self.get_tracked_value_in_struct(['Unique Name 1', 'ID'],self.Plot_struct),track,val)                              
                            refreshtreeview=True
                        if emitsignal==True:
                            trackstruct=track
                            self.Signal_Data_Change(trackstruct,str(val),str(type(val)),subtype)  #refresh on main
                        break                
        elif self.is_dict(dict_struct)==True:
            selected=dict_struct#.copy() #select dictionary
            while len(trlist)>1:
                try:
                    selected=selected[trlist[0]]
                    trlist.pop(0)
                except:
                    break
            #last tracked is variable
            if len(trlist)==1:
                selected.update({trlist[0]:val})
                #log.debug('setvaltodict_dict Here {} set to {}'.format(trlist[0],val))
                # update
                trackstruct=track.copy()
                _,self.Plot_struct=self.set_tracked_value_to_dict(trackstruct,val,self.Plot_struct,subtype)
                if emitsignal==True:
                    self.Signal_Data_Change(trackstruct,str(val),str(type(val)),subtype)  #refresh on main          
        return refreshtreeview,dict_struct            
    
    def get_track_struct_from_dict_track(self,dict_,track):
        if self.is_dict(dict_)==True:
            if self.Plot_ID!=None:
                endtrack=[self.Plot_ID].append(track) 
                #print ('ini_track->',track,'endtrack->',endtrack)
                return endtrack                   
        return track


    def check_item_value_for_edit(self,index,val,old_val,plot_struct,isok=True):
        isok=self.check_item_by_type(index,val,old_val,isok)   
        #print('bytype isok=',isok)     
        log.debug('bytype isok={}'.format(isok))     
        isok=self.check_item_by_mask(index,val,old_val,plot_struct,isok)
        #print('bymask isok=',isok)     
        log.debug('bymask isok={}'.format(isok))
        return isok

    def get_item_restriction_resval(self,index):
        itm = index.model().itemFromIndex(index) 
        track=self.track_key_tree(itm)
        itmmask=self.get_mask_for_item(track)
        if itmmask=={}:
            itmmask=self.get_mask_for_item(self.get_gentrack_from_localtrack(track))
        reslist=[]
        resvallist=[]
        resvalaltlist=[]
        if len(itmmask)>0:
            for mmm in itmmask:
                keyname=str(mmm)
                if '__m__' in keyname:                    
                    keyval=keyname.replace('__m__','__mv__')   
                    keyalt=keyname.replace('__m__','__ma__')
                    restriction=itmmask[keyname]
                    restrictionval=itmmask[keyval]      
                    reslist.append(restriction)
                    resvallist.append(restrictionval)
                    try:
                        restrictionvalalt=itmmask[keyalt]                        
                    except:
                        restrictionvalalt=None
                    resvalaltlist.append(restrictionvalalt)    
        return reslist,resvallist,resvalaltlist
                    
        

    def check_item_by_mask(self,index,val,old_val,plot_struct,isok=True):        
        #Here to add specific value ranges,formats for example like if list can have more items or if axis has to be only X or Y        
        indextype=index.siblingAtColumn(2)
        #typeitem=indextype.model().itemFromIndex(indextype)
        itm = index.model().itemFromIndex(index) 
        track=self.track_key_tree(itm)
        itmmask=self.get_mask_for_item(track)
        if itmmask=={}:
            itmmask=self.get_mask_for_item(self.get_gentrack_from_localtrack(track))
        #print(self.Plot_struct_mask)
        log.debug('Masked Track: {} Mask: {}'.format(track,itmmask))
        #value=self.get_tracked_value_in_struct(track,plot_struct)
        #print('Tracked value:',value)
        if len(itmmask)>0:
            for mmm in itmmask:
                keyname=str(mmm)
                if '__m__' in keyname:                    
                    keyval=keyname.replace('__m__','__mv__') 
                    keyalt=keyname.replace('__m__','__ma__')  
                    restriction=itmmask[keyname]
                    restrictionval=itmmask[keyval]      
                    #print('Check restriction',restriction,'---->',restrictionval)           
                    isok=self.checkitem_value_with_mask(restriction,restrictionval,val)  
                    try:
                        restrictionvalalt=itmmask[keyalt]
                        isok=isok or (self.checkitem_value_with_mask(restriction,restrictionvalalt,val))
                    except:
                        pass
                    if restriction=='is_unique' and 'ID' in track:
                        idlist=self.get_ID_list()     
                        if val in idlist:
                            isok=False
                    if isok==False:
                        log.info('{} {} returned False'.format(track,keyname))
                        break  
        return isok
    
    def get_ID_list(self):
        IDlist=[]
        for aaa in self.Plot_struct:
            IDlist.append(aaa['ID'])
        return IDlist

    def str_to_bool_or_none(self,astr):
        if self.is_bool(astr)==True:
            return astr
        elif type(astr)==type(''):
            if astr.lower() in ['true']:   
                return True
            elif astr.lower() in ['false']:   
                return False
            else:
                return None
        else:
            return None

    def str_to_bool(self,val):
        if self.is_bool(val)==True:
            return val
        else:
            if val.lower() in ['true']:   
                return True
            else:
                return False

    def checkitem_value_with_mask(self,restriction,restrictionval,value):
        isok=True
        if restriction=='is_list_item_type':            
            strlist=self.str_to_list(value)   
            #print('got value:',value,type(value),'the list:',strlist,'resval:',restrictionval)         
            try:
                for iii in strlist:
                    #print(iii)
                    if restrictionval==str(type(0)):
                        _=int(iii.strip())                                                
                        rema=re.search('^[-+]?[0-9]+$',iii.strip())
                        if rema:
                            isok=True
                        else:
                            isok=False                        
                    elif restrictionval==str(type(0.1)):
                        _=float(iii)
                    elif restrictionval==str(type(True)):
                        ans=self.str_to_bool_or_none(iii) 
                        if ans==None:
                            isok=False  
                    else:
                        isok=self.check_type(restrictionval,iii,isok)                      
            except Exception as e:
                #print(e)
                isok=False
        elif restriction=='is_list_length':
            strlist=self.str_to_list(value)
            #print('got value:',value,type(value),'the list:',strlist,'resval:',restrictionval)
            try:
                if restrictionval!=len(strlist):
                    isok=False
            except Exception as e:
                #print(e)
                isok=False
        elif restriction=='is_list_lengthGT':
            strlist=self.str_to_list(value)
            try:
                if restrictionval<=len(strlist):
                    isok=False
            except:
                isok=False
        elif restriction=='is_list_lengthLT':
            strlist=self.str_to_list(value)
            try:
                if restrictionval>=len(strlist):
                    isok=False
            except:
                isok=False
        elif restriction=='limited_selection':                        
            try:
                if value not in restrictionval:
                    isok=False
                    log.info("Selection '{}' not in permitted list: {}".format(value,restrictionval))                
            except:                
                isok=False
        elif restriction=='is_list_item_limited_selection':                        
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:
                    if aval not in restrictionval:
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))                                        
            except:                
                isok=False
        elif restriction=='is_list_item_format':                        
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:
                    if aval!='':
                        try:
                            rema=re.search(restrictionval,aval)              
                            if rema.group()!=None:
                                isok=True
                        except:
                            isok=False
                            break                                        
            except:                
                isok=False
        elif restriction=='is_list_item_value_LT':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval<=val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))                                        
            except:                
                isok=False            
        elif restriction=='is_list_item_value_GT':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval>=val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))                                        
            except:                
                isok=False            
        elif restriction=='is_list_item_value_EQ':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval==val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))                                        
            except:
                isok=False
        elif restriction=='is_list_item_value_LTEQ':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval<val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))               
            except:
                isok=False
        elif restriction=='is_list_item_value_GTEQ':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval>val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))
            except:
                isok=False
        elif restriction=='is_list_item_value_NEQ':
            try:
                if self.is_list(value)==False:
                    alist=self.str_to_list(value)
                else:
                    alist=value
                for aval in alist:                    
                    val=float(aval)            
                    if restrictionval!=val:                                      
                        isok=False
                        log.info("Selection '{}' not in permitted list: {}".format(aval,restrictionval))
            except:
                isok=False              
        elif restriction=='is_format':
            if value!='':
                try:
                    rema=re.search(restrictionval,value)              
                    if rema.group()!=None:
                        isok=True
                except:
                    isok=False
        elif restriction=='is_unique':
            isok=True #None
        elif restriction=='is_not_change':
            isok=False
        elif restriction=='is_value_LT':
            try:
                val=float(value)            
                if restrictionval<=val:                                      
                    isok=False
            except:
                isok=False
        elif restriction=='is_value_GT':
            try:
                val=float(value)                            
                if restrictionval>=val:                                        
                    isok=False
            except:
                isok=False
        elif restriction=='is_value_EQ':
            try:
                val=float(value)            
                if restrictionval==val:                                  
                    isok=False
            except:
                isok=False
        elif restriction=='is_value_LTEQ':
            try:
                val=float(value)            
                if restrictionval<val:                                       
                    isok=False
            except:
                isok=False
        elif restriction=='is_value_GTEQ':
            try:
                val=float(value)            
                if restrictionval>val:                                     
                    isok=False
            except:
                isok=False
        elif restriction=='is_value_NEQ':
            try:
                val=float(value)            
                if restrictionval!=val:                                     
                    isok=False
            except:
                isok=False                
        elif restriction=='is_value_type':
            if restrictionval==str(type(0)):
                try:
                    _=int(value.strip())                        
                    rema=re.search('^[-+]?[0-9]+$',value.strip())
                    if rema:
                        isok=True
                    else:
                        isok=False                    
                except:
                    isok=False
            elif restrictionval==str(type(0.1)):
                try:
                    _=float(value.strip())                                            
                except:
                    isok=False
            elif restrictionval==str(type(True)):
                try:
                    ans=self.str_to_bool_or_none(value.strip()) 
                    if ans==None:
                        isok=False
                except:
                    isok=False
            else:
                isok=self.check_type(restrictionval,value.strip(),isok)                      

        return isok


    def get_mask_for_item(self,track):
        maskstruct=self.Plot_struct_mask
        if len(maskstruct)==0:
            return {}
        maskdict=maskstruct[0]
        ttt_track=track.copy()
        count=0
        new_track=[]
        mask={}
        while len(ttt_track)>0:        
            if count==0: #skip plot id
                ttt_track.pop(0)
            else:   
                tr=ttt_track[0]
                ttt_track.pop(0)
                new_track.append(tr)
                try:
                    val=self.get_tracked_value_in_struct(new_track,maskdict) 
                except:
                    val=None
                    pass
                if val==None:
                    last=len(new_track)-1
                    new_track.pop(last)
                    new_track.append('__any__')
                    try:
                        val=self.get_tracked_value_in_struct(new_track,maskdict)
                    except:
                        val=None
                        pass
                    if val==None:
                        mask={}
                        break
                if type(val)==dict:
                    klist=self.get_dict_key_list(val)
                    if '__m__' in klist:
                        mask=val
                        break
            count=count+1
        return mask

    def check_item_by_type(self,index,val,old_val,isok=True):        
        indextype=index.siblingAtColumn(2)
        typeitem=indextype.model().itemFromIndex(indextype)
        the_type=typeitem.text()
        return self.check_type(the_type,val)

    def check_type(self,the_type,val,isok=True):
        if the_type==str(type(0)):
            try:
                res=int(val)
            except:
                isok=False
                pass
        elif the_type==str(type(True)):
            try:
                ans=self.str_to_bool_or_none(val)
                if ans not in [True,False]:
                    isok=False
            except:
                isok=False
                pass
        elif the_type==str(type(0.1)):
            try:
                res=float(val)
            except:
                isok=False
                pass
        elif the_type==str(type('str')):
            try:
                res=str(val)
            except:
                isok=False
                pass
        elif the_type==str(type({})):
            isok=True
        elif the_type==str(type([])):
            try:
                isok=self.is_list(self.str_to_list(val))                          
            except:
                isok=False
                pass        
        return isok
        

    def str_to_list(self,astr):        
        try:         
            rema=re.search('^\[(.+,)*(.+)?\]$',astr)              
            if rema.group()!=None:
                sss=astr.strip("[")
                sss=sss.strip("]")                
                sss=sss.replace("'","")#string quotes 
                sss=sss.replace(" ","")#spaces 
                sss=sss.strip() #spaces
                #sss=sss.strip("'")                
                splited=sss.split(",")
                return splited
        except:
            return None
        


    def restore_a_treeview_Item(self,index):
        itm = index.model().itemFromIndex(index)
        column = itm.column()
        track=self.track_key_tree(index.model().itemFromIndex(index))
        #print('restore',track)   
        val=itm.text()
    

    def Plot_importData_to_Tree(self,data, modelobj,treeviewobj):
        if isinstance(treeviewobj,QtWidgets.QTreeView):
            modelobj.setRowCount(0)        
            if self.is_list(data):
                for adict in data:            
                    newdict={}
                    try:
                        newdict.update({adict['ID']:adict})
                    except:
                        pass
                    self.dict_to_Tree(newdict,modelobj,treeviewobj,myparent=None)
                return newdict
            elif self.is_dict(data):            
                self.dict_to_Tree(data,modelobj,treeviewobj,myparent=None)  
        else:
            raise Exception('TreeView object is Not a {} object'.format(type(QtWidgets.QTreeView)))      

    
    def Create_Plot_Model_Treeview(self,treeviewparent):
        model = QtGui.QStandardItemModel(0,3,treeviewparent)
        model.setHeaderData(0,QtCore.Qt.Horizontal,"ITEM")
        model.setHeaderData(1,QtCore.Qt.Horizontal,"VALUE")
        model.setHeaderData(2,QtCore.Qt.Horizontal,"TYPE")
        treeviewparent.setModel(model)        
        return model

    def dict_to_Tree(self,adict,modelobj,treeviewobj,myparent=None):      
        if isinstance(treeviewobj,QtWidgets.QTreeView):                    
            if self.is_dict(adict)==True:                                         
                key_list=self.get_dict_key_list(adict)
                iii=0
                for akey in key_list:
                    if myparent==None:                                                            
                        parent = modelobj.invisibleRootItem()                             
                    else:                
                        parent=myparent
                    childitem = QtGui.QStandardItem(akey)  
                    emptyitem = QtGui.QStandardItem('')  
                    value = adict[akey]    
                    typeitem= QtGui.QStandardItem(str(type(value))) 
                    if self.is_dict(value)==True:   
                        parent.appendRow([childitem,emptyitem,typeitem])
                        self.dict_to_Tree(value,modelobj,treeviewobj,childitem)
                    else:                    
                        valueitem = QtGui.QStandardItem(str(value)) 
                        if self.is_bool(value)==True:   
                            valueitem.setCheckable(True)
                            self.set_checkbox_value(valueitem) 
                        else:
                            valueitem.setCheckable(False)                                 
                        parent.appendRow([childitem,valueitem,typeitem]) 
                        #Add tooltip text
                        if type(value)==type('') or self.is_list(value)==True:  
                            if valueitem.index()!=None:
                                self.set_tooltiptext(valueitem.index())     
                        self.set_icon_to_item(childitem) 
                        self.set_backgroundcolor_to_item(childitem)
                    iii=iii+1
                    treeviewobj.setFirstColumnSpanned(iii,treeviewobj.rootIndex(),True)
                    treeviewobj.resizeColumnToContents(0)
                modelobj=treeviewobj.model()
        else:
            raise Exception('TreeView object is Not a {} object'.format(type(QtWidgets.QTreeView)))

    def get_dict_key_list(self,dict):
        alist=[]
        for key in dict:
            alist.append(key)
        return alist
    
    def is_bool(self,var):
        if type(var)==type(True):
            return True            
        else:
            return False


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
    
    def get_tracked_value_in_struct(self,track,plot_struct):
        trlist=track.copy()
        selected={}
        if len(track)==0:
            return None
        if self.is_list(plot_struct)==True:
            for aplot in plot_struct:
                if aplot['ID']==trlist[0]:
                    trlist.pop(0)
                    selected=aplot #select dictionary
                    while len(trlist)>1:
                        selected=selected[trlist[0]]
                        trlist.pop(0)
                    #last tracked is variable   
                    if len(trlist)==1:                 
                        #print ('get tracked value list',trlist[0],selected[trlist[0]])             
                        return selected[trlist[0]]                    
        elif self.is_dict(plot_struct)==True:
            selected=plot_struct #select dictionary
            while len(trlist)>1:
                selected=selected[trlist[0]]
                trlist.pop(0)                
            #last tracked is variable              
            if len(trlist)==1: 
                #print ('get tracked value dict',trlist[0],selected[trlist[0]])             
                return selected[trlist[0]]            
        
        return None
    
    def get_dict_max_depth(self,adict,depth=0,maxdepth=0):         
        if self.is_dict(adict)==False and self.is_list(adict)==True and depth==0:     
            for iii in adict:       
                adepth=self.get_dict_max_depth(iii,0)
                if depth>=maxdepth:
                    maxdepth=adepth            
        else:            
            alist=self.get_dict_key_list(adict)                                     
            for item in alist:  
                '''
                astr='-'
                for iii in range(0,depth):
                    astr=astr+'+-'
                astr=astr+item+' '+str(depth)+' '+str(maxdepth)
                print(astr)
                ''' 
                resdict=adict[item]            
                if self.is_dict(resdict)==True:                
                    adepth=self.get_dict_max_depth(resdict,depth+1,maxdepth)                           
                    if adepth>=maxdepth:
                        maxdepth=adepth
                if depth>=maxdepth:
                    maxdepth=depth
        return maxdepth


    def Expand_to_Depth(self,depth):
        maxdepth=self.get_dict_max_depth(self.Show_dict)
        #print('maxdepth->',maxdepth)
        if depth<maxdepth and depth>=0:
            self.treeviewobj.expandToDepth(depth)
        elif depth>=maxdepth:
            self.treeviewobj.expandAll() 
        else:
            self.treeviewobj.collapseAll()
        






