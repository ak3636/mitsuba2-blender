import bpy
from .export_context import ExportContext
from .materials import export_world
from .geometry import GeometryExporter
from .lights import export_light
from .camera import export_camera


class SceneConverter:
    '''
    Converts a blender scene to a Mitsuba-compatible dict.
    Either save it as an XML or load it as a scene.
    '''
    def __init__(self):
        self.export_ctx = ExportContext()
        self.geometry_exporter = GeometryExporter()
        self.use_selection = False # Only export selection
        self.ignore_background = True

    def set_filename(self, name, split_files=False):
        from mitsuba.python.xml import WriteXML
        # Ideally, this should only be created if we want to write a scene.
        # For now we need it to save meshes and packed textures.
        # TODO: get rid of all writing to disk when creating the dict
        self.xml_writer = WriteXML(name, split_files)
        # Give the path to the export context, for saving meshes and files
        self.export_ctx.directory = self.xml_writer.directory
        # Temporary workaround for exporting packed textures
        self.export_ctx.textures_folder = self.xml_writer.textures_folder

    def scene_to_dict(self, depsgraph):
        # Switch to object mode before exporting stuff, so everything is defined properly
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        b_scene = depsgraph.scene #TODO: what if there are multiple scenes?
        integrator = {
            'type':'path',
            'max_depth': b_scene.cycles.max_bounces
            }
        self.export_ctx.data_add(integrator)

        export_world(self.export_ctx, b_scene.world, self.ignore_background)

        # Main export loop
        for object_instance in depsgraph.object_instances:
            if self.use_selection:
                #skip if it's not selected or if it's an instance and the parent object is not selected
                if not object_instance.is_instance and not object_instance.object.original.select_get():
                    continue
                if object_instance.is_instance and not object_instance.object.parent.original.select_get():
                    continue

            evaluated_obj = object_instance.object
            object_type = evaluated_obj.type
            #type: enum in [‘MESH’, ‘CURVE’, ‘SURFACE’, ‘META’, ‘FONT’, ‘ARMATURE’, ‘LATTICE’, ‘EMPTY’, ‘GPENCIL’, ‘CAMERA’, ‘LIGHT’, ‘SPEAKER’, ‘LIGHT_PROBE’], default ‘EMPTY’, (readonly)
            if evaluated_obj.hide_render or object_instance.is_instance and evaluated_obj.parent.original.hide_render:
                self.export_ctx.log("Object: {} is hidden for render. Ignoring it.".format(evaluated_obj.name), 'INFO')
                continue#ignore it since we don't want it rendered (TODO: hide_viewport)
            if object_type in {'MESH', 'FONT', 'SURFACE', 'META'}:
                self.geometry_exporter.export_object(object_instance, self.export_ctx)
            elif object_type == 'CAMERA':
                export_camera(object_instance, b_scene, self.export_ctx)
            elif object_type == 'LIGHT':
                export_light(object_instance, self.export_ctx)
            else:
                self.export_ctx.log("Object: %s of type '%s' is not supported!" % (evaluated_obj.name_full, object_type), 'WARN')

    def dict_to_xml(self):
        self.xml_writer.process(self.export_ctx.scene_data)

    def dict_to_scene(self):
        from mitsuba.core.xml import load_dict
        return load_dict(self.export_ctx.scene_data)
