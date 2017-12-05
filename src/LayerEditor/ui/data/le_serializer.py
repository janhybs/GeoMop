from geometry_files import GeometryFactory, LayerType, TopologyType
from .diagram_structures import Diagram
from .layers_structures import FractureInterface, Surface
import geometry_files.polygons_io as polygons_io
import geometry_files.geometry_structures as gs

class LESerializer():
    """Class for diagram data serialization"""
  
    def __init__(self, cfg):
        self.set_new(cfg)
        """Geometry faktory"""

    def set_new(self, cfg):
        """Set new file"""
        first_geometry = self._get_first_geometry()
        self.geometry_to_cfg(first_geometry, cfg)

    def cfg_reset(self, cfg):
        #TODO: move definiftion and calls to cfg
        cfg.release_all()
        cfg.diagrams = []
        cfg.layers.delete()
        cfg.diagram = None

    def _get_first_geometry(self):
        lname = "Layer 1"
        gf = GeometryFactory()
        gf.set_default()

        regions = ([], [], []) # No node, segment, polygon or regions.
        ns_top = gf.get_interface_ns(0, gf.add_interface_plane(0.0))
        ns_bot = gf.get_interpolated_ns(0, 0, gf.add_interface_plane(100.0))
        gf.add_GL(lname, LayerType.stratum, regions,
                  TopologyType.given, ns_top,
                  TopologyType.interpolated, ns_bot)
        tp_idx = gf.add_topology()
        ns_idx = gf.add_node_set(tp_idx)
        gf.geometry.supplement.last_node_set = ns_idx
        return gf.geometry

    def load(self, cfg, path):
        geometry =  gs.read_geometry(path)
        assert geometry.version == [0, 5, 0]
        self.geometry_to_cfg(geometry, cfg, path)

    def geometry_to_cfg(self, geometry, cfg, path=""):
        """Load diagram data from set file"""
        self.cfg_reset(cfg)

        curr_topology = 0
        curr_block = 0
        # curr_topology and curr_block is for mapping topology to consistent line
        gf = GeometryFactory(geometry)
        errors = gf.check_file_consistency()        
        if len(errors)>0:
            raise LESerializerException(
                "Some file consistency errors occure in {0}".format(path), errors)
        for region in gf.get_regions():
            Diagram.add_region(region.color, region.name, region.dim, region.mesh_step,
                region.boundary, region.not_used)
        for i in range(0, len(gf.geometry.node_sets)):
            new_top = gf.geometry.node_sets[i].topology_id
            if new_top != curr_topology:
                new_top == curr_topology
                curr_block += 1                
            cfg.diagrams.append(Diagram(curr_block, cfg.history))
            if len(cfg.diagrams)==1:
                cfg.diagram = cfg.diagrams[0]
            self._read_ns(cfg.diagrams[-1], i, gf)
        ns_idx = 0
        last_fracture = None
        last_stratum = None
        layer_id=0
        for i in range(0, len(gf.geometry.layers)):
            layer = gf.geometry.layers[i]
            regions = gf.get_GL_regions(i)
            if layer.layer_type is LayerType.shadow:
                cfg.add_shapes_to_region(False, layer_id, layer.name, -1, regions)
            else:
                cfg.add_shapes_to_region(layer.layer_type == LayerType.fracture, 
                    layer_id, layer.name, gf.get_gl_topology(layer), regions)            
            if layer.layer_type == LayerType.fracture:
                last_fracture = layer
                continue
            layer_id += 1
            # add interface
            surface = gf.geometry.interfaces[layer.top.interface_id]
            #surface = Surface(surface_.depth, surface_.transform_xy,
            #    surface_.transform_z, surface_.grid_file)
            if last_stratum is None:
                # first surface
                name = None
                id1 = None
                if last_fracture is not None:
                    name = last_fracture.name
                    last_fracture = None
                if layer.top_type is TopologyType.given:                
                    id1 = layer.top.nodeset_id
                cfg.layers.add_interface(surface, False, name, id1)
            elif last_stratum.bottom_type is TopologyType.interpolated and \
                layer.top_type is TopologyType.interpolated:                
                # interpolated non splitted interface
                if gf.get_gl_topology(last_stratum) == gf.get_gl_topology(layer):                    
                    if last_fracture is not None:
                        cfg.layers.add_interface(surface, False, last_fracture.name)
                        last_fracture = None
                    else:
                        cfg.layers.add_interface(surface, False)
                else:
                    if last_fracture is not None:
                        if last_fracture.top_type is TopologyType.interpolated:
                            if gf.get_gl_topology(last_stratum) == gf.get_gl_topology(last_fracture):
                                cfg.layers.add_interface(surface, True, last_fracture.name, None, None, FractureInterface.top)   
                            else:
                                cfg.layers.add_interface(surface, True, last_fracture.name, None, None, FractureInterface.bottom)   
                        else:
                            cfg.layers.add_interface(surface, True, last_fracture.name, None, None, FractureInterface.own, 
                                last_fracture.top.nodeset_id)
                        last_fracture = None    
                    else:
                        cfg.layers.add_interface(surface, True, last_fracture.name)
            elif last_stratum.bottom_type is TopologyType.given and \
                layer.top_type is TopologyType.given and \
                last_stratum.bottom.nodeset_id == layer.top.nodeset_id:
                # given non splitted interface
                if last_fracture is not None:
                    cfg.layers.add_interface(surface, False, last_fracture.name, layer.top.nodeset_id)
                    last_fracture = None
                else:
                    cfg.layers.add_interface(surface, False, None, layer.top.nodeset_id)
            else:
                # splitted surface
                fracture_name = None
                fracture_type = FractureInterface.none
                fracture_id = None
                if last_fracture is not None:
                    fracture_name = last_fracture.name
                    if last_fracture.top_type is TopologyType.interpolated:
                        if gf.get_gl_topology(last_stratum) == gf.get_gl_topology(last_fracture):
                            fracture_type = FractureInterface.top
                        else:
                            fracture_type = FractureInterface.bottom   
                    else:                        
                        if last_stratum.bottom_type is TopologyType.given and \
                            last_fracture.top.nodeset_id == last_stratum.bottom.nodeset_id:
                            fracture_type = FractureInterface.top
                        elif layer.top_type is TopologyType.given and \
                            last_fracture.top.nodeset_id == layer.top.nodeset_id:
                            fracture_type = FractureInterface.bottom
                        else:
                            fracture_id = last_fracture.top.nodeset_id
                            fracture_type = FractureInterface.own
                    last_fracture = None
                id1 = None
                id2 = None
                if last_stratum.bottom_type is TopologyType.given:
                    id1 = last_stratum.bottom.nodeset_id
                if layer.top_type is TopologyType.given:    
                    id2 = layer.top.nodeset_id
                cfg.layers.add_interface(surface, True, fracture_name, id1, id2, fracture_type, fracture_id)
            # add layer
            cfg.layers.add_layer(layer.name, layer.layer_type is LayerType.shadow) 
            last_stratum = layer
        #last interface
        surface_ = gf.geometry.surfaces[last_stratum.bottom.surface_id]
        surface = Surface(surface_.depth, surface_.transform_xy, 
                surface_.transform_z, surface_.grid_file)
        id1 = None
        if last_stratum.bottom_type is TopologyType.given:
            id1 = last_stratum.bottom.nodeset_id
        if last_fracture is not None:
            cfg.layers.add_interface(surface, False, last_fracture.name, id1)
        else:
            cfg.layers.add_interface(surface, False, None, id1)        
        if gf.geometry.supplement.last_node_set < len(gf.geometry.node_sets):
            ns_idx = gf.geometry.supplement.last_node_set        
        Diagram.area.deserialize(gf.geometry.supplement.init_area)
        Diagram.zooming.deserialize(gf.geometry.supplement.zoom)
        Diagram.shp.deserialize(gf.geometry.supplement.shps)        
        cfg.diagram = cfg.diagrams[ns_idx]         
        cfg.diagram.fix_topologies(cfg.diagrams)
        cfg.layers.compute_composition()
        cfg.layers.set_edited_diagram(ns_idx)
                
    def _read_ns(self, diagram, ns_idx, gf):
        """read  one node set from geometry file structure to diagram structure"""
        geometry = gf.geometry
        ns = geometry.node_sets[ns_idx]
        nodes = ns.nodes
        topo_id = ns.topology_id
        topology = geometry.topologies[topo_id]

        for input_id, node in enumerate(nodes):
            x, y = node
            node_id = diagram.add_point_id(x, -y)
            assert node_id == input_id

        decomp = polygons_io.deserialize(nodes, topology)
        diagram.import_decomposition(decomp)

    def save(self, cfg, path):
        geometry = self.cfg_to_geometry(cfg)
        gs.write_geometry(path, geometry)

    def cfg_to_geometry(self, cfg):
        """Save diagram data to set file"""
        gf = GeometryFactory()
        for reg in cfg.diagram.regions.regions:
            gf.add_region(reg.color, reg.name, reg.dim, reg.mesh_step, reg.boundary, reg.not_used)
        # layers
        layers_info = cfg.layers.get_first_layer_info()

        self._written_diagram_ids = set()
        self._tp_idx_to_out_tp_idx = {}
        while not layers_info.end:
            self._write_ns(layers_info.diagram_id1, cfg, gf)
            self._write_ns(layers_info.diagram_id2, cfg, gf)

            if layers_info.stype1 is TopologyType.interpolated:
                surface_idx = gf.add_surface(cfg.layers.interfaces[layers_info.layer_idx].surface)
                if layers_info.diagram_id2 is None:
                    id2 = layers_info.diagram_id1
                    surface2 = layers_info.surface1
                else:
                    id2 = layers_info.diagram_id2
                    surface2 = layers_info.surface2
                ns1 = gf.get_interpolated_ns(layers_info.diagram_id1, id2, surface_idx,
                                             layers_info.surface1, surface2)
                ns1_type = TopologyType.interpolated
            else:
                surface_idx = gf.add_surface(cfg.layers.interfaces[layers_info.layer_idx].surface)
                ns1 = gf.get_surface_ns(layers_info.diagram_id1, surface_idx)
                ns1_type = TopologyType.given

            if layers_info.stype2 is TopologyType.interpolated:
                surface_idx = gf.add_surface(cfg.layers.interfaces[layers_info.layer_idx + 1].surface)
                if layers_info.diagram_id2 is None:
                    id2 = layers_info.diagram_id1
                    surface2 = layers_info.surface1
                else:
                    id2 = layers_info.diagram_id2
                    surface2 = layers_info.surface2
                ns2 = gf.get_interpolated_ns(layers_info.diagram_id1, id2, surface_idx,
                                             layers_info.surface1, surface2)
                ns2_type = TopologyType.interpolated
            else:
                surface_idx = gf.add_surface(cfg.layers.interfaces[layers_info.layer_idx + 1].surface)
                ns2 = gf.get_surface_ns(layers_info.diagram_id2, surface_idx)
                ns2_type = TopologyType.given

            if layers_info.fracture_before is not None:
                regions = cfg.get_shapes_from_region(True, layers_info.layer_idx)
                gf.add_GL(layers_info.fracture_before.name, LayerType.fracture, regions, ns1_type, ns1)
            if layers_info.is_shadow:
                regions = [[], [], []]
                gf.add_GL("shadow", LayerType.shadow, regions, None, None)
            else:
                regions = cfg.get_shapes_from_region(False, layers_info.layer_idx)
                gf.add_GL(cfg.layers.layers[layers_info.layer_idx].name, LayerType.stratum, regions, ns1_type, ns1,
                          ns2_type, ns2)
            if layers_info.fracture_after is not None:
                regions = cfg.get_shapes_from_region(True, layers_info.layer_idx + 1)
                gf.add_GL(layers_info.fracture_after.name, LayerType.fracture, regions, ns2_type, ns2)
            if layers_info.fracture_own is not None:
                self._write_ns(layers_info.fracture_own.fracture_diagram_id, cfg, gf)
                surface_idx = gf.add_surface(cfg.layers.interfaces[layers_info.layer_idx + 1].surface)
                ns = gf.get_surface_ns(layers_info.fracture_own.fracture_diagram_id, surface_idx)
                regions = cfg.get_shapes_from_region(True, layers_info.layer_idx + 1)
                gf.add_GL(layers_info.fracture_own.name, LayerType.fracture, regions, TopologyType.given, ns)
                layers_info.block_idx += 1
            layers_info = cfg.layers.get_next_layer_info(layers_info)
        gf.geometry.supplement.last_node_set = cfg.get_curr_diagram()
        Diagram.area.serialize(gf.geometry.supplement.init_area)
        Diagram.zooming.serialize(gf.geometry.supplement.zoom)
        Diagram.shp.serialize(gf.geometry.supplement.shps)
        errors = gf.check_file_consistency()
        if len(errors) > 0:
            raise LESerializerException("Some file consistency errors occure", errors)
        return gf.geometry

    def _write_ns(self, diagram_id, cfg, gf):
        """write one node set from diagram structure to geometry file structure"""
        if diagram_id is None or diagram_id in self._written_diagram_ids:
            return
        diagram = cfg.diagrams[diagram_id]
        self._written_diagram_ids.add(diagram_id)

        decomp = diagram.po.decomposition
        nodes, topology = polygons_io.serialize(decomp)
        if diagram.topology_owner:
            out_tp_idx = gf.add_topology(topology)
            self._tp_idx_to_out_tp_idx[diagram.topology_idx] = out_tp_idx
        else:
            out_tp_idx = self._tp_idx_to_out_tp_idx[diagram.topology_idx]
        gf.add_node_set(out_tp_idx, nodes)

class LESerializerException(Exception):
    def __init__(self, message, errors):
        super(LESerializerException, self).__init__(message)
        self.errors = errors
