import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, BoolProperty
import os
from os.path import basename, dirname
import sys

from .convert import SceneConverter
from bpy_extras.io_utils import ExportHelper, axis_conversion, orientation_helper


@orientation_helper(axis_forward='-Z', axis_up='Y')
class MitsubaFileExport(Operator, ExportHelper):
    """Export as a Mitsuba 2 scene"""
    bl_idname = "export_scene.mitsuba2"
    bl_label = "Mitsuba 2 Export"

    filename_ext = ".xml"

    use_selection: BoolProperty(
	        name = "Selection Only",
	        description="Export selected objects only",
	        default = False,
	    )

    split_files: BoolProperty(
            name = "Split File",
            description = "Split scene XML file in smaller fragments",
            default = False
    )

    export_ids: BoolProperty(
            name = "Export IDs",
            description = "Add an 'id' field for each object (shape, emitter, camera...)",
            default = False
    )

    ignore_background: BoolProperty(
            name = "Ignore Default Background",
            description = "Ignore blender's default constant gray background when exporting to Mitsuba.",
            default = True
    )

    def __init__(self):
        # addon_name must match the addon main folder name
        # Use dirname() to go up the necessary amount of folders
        addon_name = basename(dirname(dirname(__file__)))
        self.prefs = bpy.context.preferences.addons[addon_name].preferences
        self.reset()

    def reset(self):
        self.converter = SceneConverter()

    def execute(self, context):
        # Conversion matrix to shift the "Up" Vector. This can be useful when exporting single objects to an existing mitsuba scene.
        axis_mat = axis_conversion(
	            to_forward=self.axis_forward,
	            to_up=self.axis_up,
	        ).to_4x4()
        self.converter.export_ctx.axis_mat = axis_mat
        # Add IDs to all base plugins (shape, emitter, sensor...)
        self.converter.export_ctx.export_ids = self.export_ids
        #Set path to scene .xml file
        self.converter.set_filename(self.filepath, split_files=self.split_files)

        self.converter.scene_to_dict(context.evaluated_depsgraph_get())
        #write data to scene .xml file
        self.converter.dict_to_xml()
        #reset the exporter
        self.reset()
        return {'FINISHED'}
