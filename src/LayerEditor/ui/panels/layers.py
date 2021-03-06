"""CanvasWidget file"""
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
from LayerEditor.leconfig import cfg
import PyQt5.QtCore as QtCore
from ..data import FractureInterface, ClickedControlType, ChangeInterfaceActions, LayerSplitType, TopologyOperations, Interface
from ..data import LayersHistory
from ..menus.layers import LayersLayerMenu, LayersInterfaceMenu, LayersFractuceMenu, LayersShadowMenu
from ..menus.layers import __COPY_BLOCK__
from ..dialogs.layers import AppendLayerDlg, SetNameDlg, SetSurfaceDlg, SplitLayerDlg, AddFractureDlg, ReportOperationsDlg

class Layers(QtWidgets.QWidget):
    """
    GeoMop Layer editor layers panel
    
    pyqtSignals:
        * :py:attr:`viewInterfacesChanged(int) <viewInterfacesChanged>`
        * :py:attr:`editInterfaceChanged(int,int) <editInterfaceChanged>`
        * :py:attr:`topologyChanged() <topologyChanged>`
        * :py:attr:`refreshArea() <refreshArea>
        
    All regions function contains history operation without label and
    must be placed after first history operation with label.
    """
    clearDiagramSelection = QtCore.pyqtSignal()
    """Signal is sent when selection needs to be cleared to prevent topology switch issues."""

    topologyChanged = QtCore.pyqtSignal()
    """Signal is sent when current selected topology or some 
    topology structure is changed."""
    
    viewInterfacesChanged = QtCore.pyqtSignal(int)
    """Signal is sent when one or more interfaces is set or unset as viwed.
    
    :param int idx: changed diagram index"""
    editInterfaceChanged = QtCore.pyqtSignal(int, int)
    """Signal is sent when edited interface is changed.
    
    :param int idx_old: old edited diagram index
    :param int idx_new: new edited diagram index"""
    refreshArea = QtCore.pyqtSignal()
    """Signal is sent when arrea shoud be refreshed."""    

    def __init__(self, parent=None):
        """
        Inicialize window

        Args:
            parent (QWidget): parent window ( empty is None)
        """
        super(Layers, self).__init__(parent)
        self.setMouseTracking(True)
        self.size = self.sizeHint()
        self._history = LayersHistory(cfg.history)
        """history"""
        
    def reload_layers(self, cfg):
        """Call if data file changed"""
        self._history = LayersHistory(cfg.history)

    def mouseMoveEvent(self, event):
        """standart mouse move widget event"""
        if cfg.layers.get_clickable_type(event.pos().x(), event.pos().y()) is not ClickedControlType.none :
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)
        
    def mousePressEvent(self, event):
        type = cfg.layers.get_clickable_type(event.pos().x(), event.pos().y())
        if type is ClickedControlType.none :
            return
        i = cfg.layers.get_clickable_idx(event.pos().x(), event.pos().y(), type) 
        if type is ClickedControlType.view or type is ClickedControlType.view2 or \
            type is ClickedControlType.fracture_view:
            self.change_viewed(i, type)
        elif type is ClickedControlType.edit or type is ClickedControlType.edit2 or \
            type is ClickedControlType.fracture_edit:
            self.change_edited(i, type)
        elif type is ClickedControlType.layer:
            if cfg.layers.layers[i].shadow:
                menu = LayersShadowMenu(self, i)
            else:
                menu = LayersLayerMenu(self, i)
            menu.exec_(self.mapToGlobal(event.pos()))
        elif type is ClickedControlType.interface:
            menu = LayersInterfaceMenu(self, i)
            menu.exec_(self.mapToGlobal(event.pos()))
        elif type is ClickedControlType.fracture:
            menu = LayersFractuceMenu(self, i)
            menu.exec_(self.mapToGlobal(event.pos()))

  #  def keyPressEvent(self, event):
  
    def change_size(self):
        """Call this function after resize layers panel.
        This function send signal to scroll"""
        cfg.layers.compute_composition()
        self.update()
        new_size = self.sizeHint()
        if new_size!=self.size:            
            self.resize(new_size)
            self.size = new_size

    def _paint_fracture(self, painter, y, x1, x2, dx, interface, font_dist):
        """Paint layer with fracture name"""
        painter.drawLine(x1-2*dx, y, interface.fracture.rect.left()-dx, y)
        old_pen = painter.pen()
        pen = QtGui.QPen(QtGui.QColor("#802020"))
        painter.setPen(pen)
        painter.drawText(interface.fracture.rect.left(), interface.fracture.rect.bottom()-font_dist, 
            interface.fracture.name)
        painter.setPen(old_pen)
        painter.drawLine(interface.fracture.rect.right()+dx, y, x2-2*dx, y)
        
    def _paint_checkbox(self, painter, rect, value):
        """Paint view checkbox"""
        painter.drawRect(rect)        
        if value:
            painter.drawLine(rect.left()+1, rect.top()+rect.height()*2/3-1,rect.left()+rect.width()/3, rect.bottom()-1)
            painter.drawLine(rect.left()+rect.width()/3+1, rect.bottom()-1, rect.right()-1, rect.top()+rect.height()/3)

    def _paint_radiobutton(self, painter, rect, value, x2):
        """Paint edit radio button width line to x2"""
        painter.drawEllipse(rect)
        line_y =  rect.top()+rect.height()/2
        painter.drawLine(rect.right(), line_y, x2, line_y)
        if value:
            d=1+rect.width()/4
            rect2 = QtCore.QRectF(rect.left()+d,  rect.top()+d, rect.width()-2*d, rect.height()-2*d)
            painter.drawEllipse(rect2)

    def sizeHint(self):
        """Overloadet QWidget sizeHint function"""
        dx = cfg.layers.x_ilabel+cfg.layers.x_ilabel_width+cfg.layers.__dx__
        if len(cfg.layers.interfaces)==0: 
            dy = cfg.layers.y_font + 2*cfg.layers.__dy_row__
        else:
            dy = cfg.layers.interfaces[-1].rect.bottom()+cfg.layers.__dy_row__
        return QtCore.QSize(dx, int(dy))
         
    def paintEvent(self, event=None):
        """Overloadet QWidget paint function"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        
        d = cfg.layers
        painter.setFont(d.font)
        painter.drawText(QtCore.QPointF(d.x_view, d.__dy_row__+d.y_font), "View")
        painter.drawText(QtCore.QPointF(d.x_edit, d.__dy_row__+d.y_font), "Edit")
        painter.drawText(QtCore.QPointF(d.x_label, d.__dy_row__+d.y_font), "Layer")
        painter.drawText(QtCore.QPointF(d.x_ilabel, d.__dy_row__+d.y_font), "Elevation")
        
        for i in range(0, len(d.interfaces)):
            # interface            
            if d.interfaces[i].y_top is None:
                if d.interfaces[i].fracture is None:
                    painter.drawLine(d.x_label-2*d.__dx__, d.interfaces[i].y, d.x_ilabel-2*d.__dx__, d.interfaces[i].y)
                else:
                    self._paint_fracture(painter, d.interfaces[i].y, d.x_label, 
                        d.x_ilabel, d.__dx__,d.interfaces[i], d.y_font/4)               
            else:
                if d.interfaces[i].fracture is None or d.interfaces[i].fracture.type != FractureInterface.top :
                    painter.drawLine(d.x_label-2*d.__dx__, d.interfaces[i].y_top, d.x_ilabel-2*d.__dx__, d.interfaces[i].y_top)
                else:    
                    self._paint_fracture(painter, d.interfaces[i].y_top, d.x_label, 
                        d.x_ilabel, d.__dx__,d.interfaces[i], d.y_font/4)
                painter.drawLine(d.x_ilabel-2*d.__dx__, d.interfaces[i].y_top, d.x_ilabel-d.__dx__, d.interfaces[i].y)
                if d.interfaces[i].fracture is not None and d.interfaces[i].fracture.type == FractureInterface.own :
                    self._paint_fracture(painter, d.interfaces[i].y, d.x_label, 
                        d.x_ilabel+d.__dx__, d.__dx__,d.interfaces[i], d.y_font/4)
                painter.drawLine(d.x_ilabel-d.__dx__, d.interfaces[i].y, d.x_ilabel-2*d.__dx__, d.interfaces[i].y_bottom)
                if d.interfaces[i].fracture is None or d.interfaces[i].fracture.type != FractureInterface.bottom :
                    painter.drawLine(d.x_label-2*d.__dx__, d.interfaces[i].y_bottom, d.x_ilabel-2*d.__dx__, d.interfaces[i].y_bottom)
                else:    
                    self._paint_fracture(painter, d.interfaces[i].y_bottom, d.x_label,
                        d.x_ilabel, d.__dx__,d.interfaces[i], d.y_font/4)                            
            if d.interfaces[i].view_rect1 is not None:
                self._paint_checkbox( painter, d.interfaces[i].view_rect1, d.interfaces[i].viewed1)
            if d.interfaces[i].view_rect2 is not None:
                self._paint_checkbox(painter, d.interfaces[i].view_rect2, d.interfaces[i].viewed2)
            if d.interfaces[i].edit_rect1 is not None:
                self._paint_radiobutton(painter, d.interfaces[i].edit_rect1, d.interfaces[i].edited1, d.x_label-2*d.__dx__)
            if d.interfaces[i].edit_rect2 is not None:
                self._paint_radiobutton(painter, d.interfaces[i].edit_rect2, d.interfaces[i].edited2, d.x_label-2*d.__dx__)
            if d.interfaces[i].fracture is not None:
                if d.interfaces[i].fracture.view_rect is not None:
                    self._paint_checkbox(painter, d.interfaces[i].fracture.view_rect, d.interfaces[i].fracture.viewed)
                if d.interfaces[i].fracture.edit_rect is not None:
                    self._paint_radiobutton(painter, d.interfaces[i].fracture.edit_rect, 
                        d.interfaces[i].fracture.edited, d.x_label-2*d.__dx__)                
            painter.drawText(d.interfaces[i].rect.left(), d.interfaces[i].rect.bottom()-d.y_font/4, 
                d.interfaces[i].str_elevation)
            #layers
            if i<len(d.layers):
                if d.layers[i].shadow:
                    old_pen = painter.pen()
                    pen = QtGui.QPen(QtGui.QColor("#808080"))
                    painter.setPen(pen)
                    painter.drawText(d.layers[i].rect.left(), d.layers[i].rect.bottom()-d.y_font/4
                        , "shadow")
                    painter.setPen(old_pen)
                else:
                    painter.drawText(d.layers[i].rect.left(), d.layers[i].rect.bottom()-d.y_font/4
                        , d.layers[i].name)
                if i+1<len(d.interfaces):
                    top = d.interfaces[i].y
                    bottom = d.interfaces[i+1].y
                    if d.interfaces[i].y_bottom is not None:
                        top = d.interfaces[i].y_bottom
                    if d.interfaces[i+1].y_top is not None:
                        bottom = d.interfaces[i+1].y_top
                    painter.drawLine(d.x_label-2*d.__dx__, top, d.x_label-2*d.__dx__, bottom)
            
    # data functions

    def append_layer(self):
        """Append layer to the end"""
        dlg = AppendLayerDlg(cfg.main_window, None, cfg.layers.interfaces[-1].elevation)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.layer_name.text()
            interface = cfg.layers.append_layer(name)
            dlg.fill_surface(interface)
            self._history.delete_layer(len(cfg.layers.layers)-1,"Append layer")
            self._history.delete_interface(len(cfg.layers.interfaces)-1)
            cfg.diagram.regions.add_layer(len(cfg.layers.layers)-1, name, TopologyOperations.none)
            self.topologyChanged.emit()
            self.refreshArea.emit()
            self.change_size()

    def prepend_layer(self):
        """Prepend layer to the start"""
        dlg = AppendLayerDlg(cfg.main_window, cfg.layers.interfaces[0].elevation, None, True)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.layer_name.text()            
            interface = cfg.layers.prepend_layer(name)            
            dlg.fill_surface(interface)
            self._history.delete_layer(0,"Prepend layer")
            self._history.delete_interface(0)
            cfg.diagram.regions.add_layer(0, name, TopologyOperations.none)
            self.topologyChanged.emit()
            self.refreshArea.emit()
            self.change_size()
            
    def add_layer_to_shadow(self, idx):
        """Prepend layer to the start"""
        dlg = AppendLayerDlg(cfg.main_window, cfg.layers.interfaces[idx+1].elevation, cfg.layers.interfaces[idx].elevation, False, True)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.layer_name.text()
            interface = Interface(None, True, 0.0)
            dlg.fill_surface(interface)
            dup = cfg.layers.get_diagram_dup_before(idx)            
            self._history.delete_diagrams(dup.insert_id, dup.count, TopologyOperations.insert, "Add layer to shadow")
            cfg.insert_diagrams_copies(dup, TopologyOperations.insert)
            layers, interfaces = cfg.layers.get_group_copy(idx, 1)
            if cfg.layers.add_layer_to_shadow(idx, name, interface, dup):                
                self._history.change_group(layers, interfaces, idx, 1, TopologyOperations.insert)
                cfg.diagram.regions.add_layer(idx, name, TopologyOperations.insert)
            else:                
                self._history.change_group(layers, interfaces, idx, 2)
                cfg.diagram.regions.copy_related(idx, name, TopologyOperations.none)
            self.topologyChanged.emit()
            self.refreshArea.emit()
            self.change_size()
    
    def change_viewed(self, i, type):
        """Change viewed interface"""
        fracture = False
        second = False        
        if type is ClickedControlType.fracture_view:
            fracture = True
        elif type is ClickedControlType.view2:
            second = True
        else:
            assert(type is ClickedControlType.view)
        viewed = cfg.layers.set_viewed_interface(i, second, fracture)
        diagram_idx =  cfg.layers.get_diagram_idx(i, second, fracture)
        if viewed:
            cfg.diagram.views.append(cfg.diagrams[diagram_idx].uid)
            if cfg.diagrams[diagram_idx].uid not in cfg.diagram.map_id:
                cfg.diagram.map_id[cfg.diagrams[diagram_idx].uid] = diagram_idx  
        else:
            cfg.diagram.views.remove(cfg.diagrams[diagram_idx].uid)
        self.update()
        self.viewInterfacesChanged.emit(diagram_idx)
        
    def change_edited(self, i, type):
        """Change edited interface"""
        fracture = False
        second = False        
        if type is ClickedControlType.fracture_edit:
            fracture = True
        elif type is ClickedControlType.edit2:
            second = True
        else:
            assert(type is ClickedControlType.edit)
        cfg.layers.set_edited_interface(i, second, fracture)
        diagram_idx = cfg.layers.get_diagram_idx(i, second, fracture)
        old = cfg.set_curr_diagram(diagram_idx)
        self.update()
        self.clearDiagramSelection.emit() # different topology selection cannot correlate to the new one
        self.topologyChanged.emit() # first update regions      
        self.editInterfaceChanged.emit(old, diagram_idx)
    
    def add_interface(self, i):
        """Split layer by new interface"""
        max = cfg.layers.interfaces[i].elevation
        min = None
        if i<len(cfg.layers.interfaces)-1:
            min = cfg.layers.interfaces[i+1].elevation
            
        dlg = SplitLayerDlg(min, max, __COPY_BLOCK__, cfg.main_window)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.layer_name.text()
            split_type = dlg.split_type.currentData()
            dup = None
            label = "Add interface"
            oper = TopologyOperations.none
            
            if split_type is LayerSplitType.editable or \
                split_type is LayerSplitType.split:
                dup = cfg.layers.get_diagram_dup(i)                
                if split_type is LayerSplitType.split:
                    dup.count = 2
                    oper = TopologyOperations.insert_next
                self._history.delete_diagrams(dup.insert_id, dup.count, oper, label)
                cfg.insert_diagrams_copies(dup, oper)                
                label = None
            layers, interfaces = cfg.layers.get_group_copy(i, 1)    
            interface = cfg.layers.split_layer(i, name, split_type, dup)
            dlg.fill_surface(interface)
            self._history.change_group(layers, interfaces, i, 2, label)
            cfg.diagram.regions.add_layer(i+1, name, oper)
            
            self.topologyChanged.emit()
            self.refreshArea.emit()
            self.change_size()

    def rename_layer(self, i):
        """Rename layer"""
        old_name = cfg.layers.layers[i].name
        dlg = SetNameDlg(old_name, "Layer", cfg.main_window)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.name.text()
            self._history.change_layer_name(old_name, i, "Rename layer")
            cfg.layers.layers[i].name = name
            cfg.diagram.regions.rename_layer(False, i, name)
            self.topologyChanged.emit()
            self.change_size()

    def remove_layer(self, i):
        """Remove layer and add shadow block instead"""
        if not cfg.layers.is_layer_removable(i):
            return
        removed_res = cfg.layers.remove_layer_changes(i)
        if removed_res[0]+removed_res[1]+removed_res[2]>0:
            messages = []
            if removed_res[0]>0:
                if removed_res[0]==1:
                    messages.append("One slice will be removed from structure")
                else:
                    messages.append("Two slices will be removed from structure")
            if removed_res[2]>0:
                if removed_res[2]==1:
                    messages.append("One fracture will be removed from structure")
                else:
                    messages.append("Two fractures will be removed from structure")
            if removed_res[1]>0:
                messages.append("One new interpolated slice will be added to structure") 
            dlg = ReportOperationsDlg("Remove Layer",messages,cfg.main_window) 
            ret = dlg.exec_()
            if ret!=QtWidgets.QMessageBox.Ok:                
                return 
        dup=None        
        if removed_res[1]==1:
            dup = cfg.layers.get_diagram_dup(i-1)
        del_layers, del_interfaces = cfg.layers.get_group_copy(i, 1)       
        diagrams, layers = cfg.layers.remove_layer(i, removed_res, dup)
        if layers==2:
            self._history.change_group([], del_interfaces[0:1], i, 2, "Remove layer")
        elif layers==0:
            self._history.change_group(del_layers[0:1], del_interfaces[0:2], i, 1, "Remove layer")
        else:
            self._history.change_group(del_layers, del_interfaces, i, 1, "Remove layer")

        if removed_res[3]:
            cfg.diagram.regions.delete_fracture(i)
            if removed_res[2]>1:
                cfg.diagram.regions.delete_fracture(i+1)
        elif removed_res[2]>0:
            cfg.diagram.regions.delete_Fracture(i+1)
        if layers==2:
            cfg.diagram.regions.delete_layer(i)
            cfg.diagram.regions.delete_layer(i)
        elif layers==0:
            cfg.diagram.regions.delete_data(i)
        else:
            cfg.diagram.regions.delete_layer(i) 
            
        for diagram in diagrams:
            if cfg.remove_and_save_diagram(diagram):
                cfg.layers.set_edited_diagram(0)
        self.topologyChanged.emit()
        self.change_size() 
                
    def remove_block(self, i):
        """Remove all block"""
        if not cfg.layers.is_block_removable(i):
            return
        removed_res = cfg.layers.remove_block_changes(i)
        (first_idx, first_slice_id, layers, fractures, slices) = removed_res
        if layers+fractures+slices:
            messages = []
            if slices>0:
                if slices==1:
                    messages.append("One slice will be removed from structure")
                else:
                    messages.append("{0} slices will be removed from structure".format(str(slices)))
            if fractures>0:
                if fractures==1:
                    messages.append("One fracture will be removed from structure")
                else:
                    messages.append("{0} fractures will be removed from structure".format(str(fractures)))
            dlg = ReportOperationsDlg("Remove Block",messages,cfg.main_window) 
            ret = dlg.exec_()
            if ret!=QtWidgets.QMessageBox.Ok:                
                return 
        del_layers, del_interfaces = cfg.layers.get_group_copy(first_idx, layers)
        diagrams = cfg.layers.remove_block(i, removed_res)         
        self._history.change_group(del_layers, del_interfaces, first_idx, 1, "Remove block")
        cfg.diagram.regions.delete_block(first_idx, layers)
        for diagram in diagrams:
            if cfg.remove_and_save_diagram(diagram):
                cfg.layers.set_edited_diagram(0)
            self._history.insert_diagrams(diagram, TopologyOperations.insert)
        self.topologyChanged.emit()
        self.change_size()
     
    def add_fracture(self, i):
        """Add fracture to interface"""
        dlg = AddFractureDlg(cfg.layers.interfaces[i].get_fracture_position(), cfg.main_window)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.fracture_name.text()
            position = None
            label = "Add fracture"
            dup = None
            if dlg.fracture_position is not None:
                position = dlg.fracture_position.currentData()
            if position is FractureInterface.own:
                dup = cfg.layers.get_diagram_dup(i)
                self._history.delete_diagrams(dup.insert_id, 1, TopologyOperations.insert, label)
                cfg.insert_diagrams_copies(dup, TopologyOperations.insert)                
                label = None
            cfg.layers.add_fracture(i, name, position, dup)            
            self._history.delete_fracture(i, position, label)
            cfg.diagram.regions.add_fracture(i, name, position is FractureInterface.own, position is FractureInterface.bottom)
            self.topologyChanged.emit()
            self.change_size()
        
    def change_interface_type(self, i, type):
        """Change interface type"""
        label = "Change interface type"
        old_interface = cfg.layers.get_interface_copy(i)
        if type is ChangeInterfaceActions.interpolated or \
            type is ChangeInterfaceActions.bottom_interpolated or \
            type is ChangeInterfaceActions.top_interpolated:
            dlg = ReportOperationsDlg("Change to interpolated", 
                ["One slice will be removed from structure"], 
                cfg.main_window)
            ret = dlg.exec_()
            if ret!=QtWidgets.QMessageBox.Ok:                
                return
        if type is ChangeInterfaceActions.split:
            dup = cfg.layers.get_diagram_dup(i)
            self._history.delete_diagrams(dup.insert_id, dup.count, TopologyOperations.insert, label)            
            cfg.insert_diagrams_copies(dup, TopologyOperations.insert)            
            label = None
            cfg.diagram.regions.move_topology(i)
            cfg.layers.split_interface(i, dup)
        elif type is ChangeInterfaceActions.interpolated or \
            type is ChangeInterfaceActions.bottom_interpolated or \
            type is ChangeInterfaceActions.top_interpolated:
            diagram = cfg.layers.change_to_interpolated(i,type)
            if diagram is not None:
                if cfg.remove_and_save_diagram(diagram):
                    cfg.layers.set_edited_diagram(0)
                self._history.insert_diagrams(diagram, TopologyOperations.insert, label)
                label = None
        elif ChangeInterfaceActions.top_editable:
            dup = cfg.layers.get_diagram_dup(i-1)
            self._history.delete_diagrams(dup.insert_id, dup.count, TopologyOperations.none, label)
            cfg.insert_diagrams_copies(dup, TopologyOperations.none)           
            label = None
            cfg.layers.change_to_editable(i,type, dup)
        else: 
            dup = cfg.layers.get_diagram_dup(i)
            self._history.delete_diagrams(dup.insert_id, dup.count, TopologyOperations.none, label)
            cfg.insert_diagrams_copies(dup, TopologyOperations.none)            
            label = None
            cfg.layers.change_to_editable(i,type, dup)
        self._history.change_interface(old_interface, i, label)
        self.topologyChanged.emit()
        self.change_size()
        
    def set_interface_surface(self, i):
        """Set interface elevation"""
        min_elevation = None
        max_elevation = None
        if i>0:
            max_elevation = cfg.layers.interfaces[i-1].elevation
        if i<len(cfg.layers.interfaces)-1:
            min_elevation = cfg.layers.interfaces[i+1].elevation
        old_surface_id = cfg.layers.interfaces[i].surface_id
        old_depth = cfg.layers.interfaces[i].elevation
        old_transform_z = cfg.layers.interfaces[i].transform_z

        dlg = SetSurfaceDlg(cfg.layers.interfaces[i], cfg.main_window, min_elevation, max_elevation)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            dlg.fill_surface(cfg.layers.interfaces[i])
            if old_surface_id!=cfg.layers.interfaces[i].surface_id and \
                old_transform_z!=cfg.layers.interfaces[i].transform_z and \
                old_depth!=cfg.layers.interfaces[i].elevation:
                self._history.change_interface_surface(old_surface_id, old_depth, old_transform_z, i, "Set interface surface")
                self.change_size()
        self.refreshArea.emit()
        
    def remove_interface(self, i):
        """Remove interface"""        
        if not cfg.layers.is_interface_removable(i):
            return
        removed_res = cfg.layers.remove_layer_changes(i)
        if removed_res[0]+removed_res[1]>0:
            messages = []
            if removed_res[0]==1:
                messages.append("One slice will be removed from structure")
            if removed_res[1]==1:
                messages.append("One fracture will be removed from structure")
            dlg = ReportOperationsDlg("Remove Layer",messages,cfg.main_window) 
            ret = dlg.exec_()
            if ret!=QtWidgets.QMessageBox.Ok:                
                return
        del_layers, del_interfaces = cfg.layers.get_group_copy(i, 2)
        diagrams = cfg.layers.remove_interface(i, removed_res)
        self._history.change_group(del_layers, del_interfaces, i, 1, "Remove interface")
        cfg.diagram.regions.delete_layer(i)
        if removed_res[1]==1:
            cfg.diagram.regions.delete_fracture(i)
        for diagram in diagrams:
            if cfg.remove_and_save_diagram(diagram):
                cfg.layers.set_edited_diagram(0)
            self._history.insert_diagrams(diagram, TopologyOperations.insert)
        self.topologyChanged.emit()
        self.change_size()

    def remove_fracture(self, i):
        """Remove fracture from interface"""
        if cfg.layers.interfaces[i].fracture.type==FractureInterface.own:
            dlg = ReportOperationsDlg("Remove Fracture", 
                ["One slice will be removed from structure"], 
                cfg.main_window)
            ret = dlg.exec_()
            if ret!=QtWidgets.QMessageBox.Ok:                
                return
        fracture = cfg.layers.interfaces[i].fracture
        self._history.add_fracture(fracture, i, fracture.type, "Remove fracture")
        diagram = cfg.layers.remove_fracture(i)
        cfg.diagram.regions.delete_fracture(i)
        if diagram is not None:
            if cfg.remove_and_save_diagram(diagram):
                cfg.layers.set_edited_diagram(0)
            self._history.insert_diagrams(i, TopologyOperations.insert)
        self.topologyChanged.emit()
        self.change_size()
        
    def rename_fracture(self, i):
        """Rename fracture"""
        old_name = cfg.layers.interfaces[i].fracture.name
        dlg = SetNameDlg(old_name, "Fracture", cfg.main_window)
        ret = dlg.exec_()
        if ret==QtWidgets.QDialog.Accepted:
            name = dlg.name.text()
            cfg.layers.interfaces[i].fracture.name = name            
            self._history.change_fracture_name(old_name, i, "Rename fracture")
            cfg.diagram.regions.rename_layer(True, i, name)
            self.topologyChanged.emit()
            self.change_size()
