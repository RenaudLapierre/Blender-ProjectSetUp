bl_info = {
    "name": "Project Utility",
    "author": "Renaud Lapierre",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > UI > Tool",
    "description": "Set Up Project",
    "category": "Tools",
}

import bpy
import os
import subprocess
import shutil
from pathlib import Path

DEFAULT_FOLDER_NAMES = ["Blender", "Geo", "Painter", "Photoshop", "References", "Renders", "Textures"]

# Define a custom property to store the list of folders
bpy.types.Scene.folder_list = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)

# Define a property to store the active folder index
bpy.types.Scene.active_folder_index = bpy.props.IntProperty()

# Define a property to store the directory path
bpy.types.Scene.directory_path = bpy.props.StringProperty(
    name="Directory Path",
    subtype='DIR_PATH',
    default="",
    description="Choose a directory path"
)

# Define a property to store the file path of the .Pur
bpy.types.Scene.pure_ref_path = bpy.props.StringProperty(
    name="pure_ref_path",
    description="File path of the .pur",
    default="",
    subtype='FILE_PATH'
)

#Define a property to store name of .blend file
bpy.types.Scene.blend_name = bpy.props.StringProperty(
    name="Blend Name",
    subtype='FILE_NAME',
    default="",
    description="Set the name of the .blend file"
)

# Define a property to store custom folder names
bpy.types.Scene.custom_folder_names = bpy.props.StringProperty(
    name="Custom Folder Names",
    description="Enter custom folder names as a comma-separated list",
    default=""
)


class UpdateFolderPreferencesOperator(bpy.types.Operator):
    bl_idname = "scene.update_folder_preferences"
    bl_label = "Update Folder Preferences"
    bl_description = "Update the default folder structure in preferences"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        # Save the custom folder names to preferences
        prefs.default_folder_names = context.scene.custom_folder_names
        self.report({'INFO'}, "Folder preferences updated.")
        return {'FINISHED'}



class AddDefaultFolderOperator(bpy.types.Operator):
    bl_idname = "scene.add_default_folder"
    bl_label = "Add Default Folders"
    bl_description = "Add the default folders"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        prefs = context.preferences.addons[__name__].preferences

        # Clear existing folders in the scene
        scene.folder_list.clear()

        # Get default folder names from preferences
        default_folder_names = [name.strip() for name in prefs.default_folder_names.split(',')]

        # Add default folders
        for name in default_folder_names:
            folder = scene.folder_list.add()
            folder.name = name

        return {'FINISHED'}



# Define an operator to add NEW folders to the list
class AddNewFolderOperator(bpy.types.Operator):
    bl_idname = "scene.add_new_folder"
    bl_label = "Add Folder"
    bl_description = "Add a new folders"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        folder = scene.folder_list.add()
        folder.name = "New Folder"  # Set a default folder name here
        return {'FINISHED'}

# Define an operator to remove selected folders
class RemoveFolderOperator(bpy.types.Operator):
    bl_idname = "scene.remove_folder"
    bl_label = "Remove Folder"
    bl_description = "Remove selected folder"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        if context.scene.folder_list and context.scene.active_folder_index >= 0:
            scene.folder_list.remove(context.scene.active_folder_index)
            context.scene.active_folder_index = -1  # Reset active index
        return {'FINISHED'}

class CreateProjectOperator(bpy.types.Operator):
    bl_idname = "scene.create_project"
    bl_label = "Create Project"
    bl_description = "Create the project directory"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        directory_path = Path(scene.directory_path).resolve()

        if not os.path.exists(directory_path):
            self.report({'ERROR'}, "Directory does not exist.")
            return {'CANCELLED'}

        # Get folder names from the scene's folder_list
        folder_names = [folder.name for folder in scene.folder_list]

        for name in folder_names:
            folder_path = directory_path / name
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                self.report({'ERROR'}, f"Error creating folder: {str(e)}")
                return {'CANCELLED'}

        self.report({'INFO'}, "Project folders created successfully.")
        return {'FINISHED'}


class SetBlendFileOperator(bpy.types.Operator):
    bl_idname = "scene.set_blend_file"
    bl_label = "Set Blend File"
    bl_description = "Set the name of the .blend file and save inside the Blender folder"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene

        # Get the directory path and blend file name
        directory_path = Path(scene.directory_path).resolve()
        blend_name = scene.blend_name

        # Ensure the directory path ends with a slash
        if not directory_path.as_posix().endswith('/'):
            directory_path /= ''  # This ensures that the path ends with a separator

        # Construct the path to the Blender folder
        blender_folder_path = directory_path / "Blender"

        # Ensure the Blender folder exists
        if not blender_folder_path.exists():
            self.report({'ERROR'}, "Blender folder does not exist.")
            return {'CANCELLED'}

        # Construct the full file path with ".blend" extension inside the Blender folder
        save_path = blender_folder_path / f"{blend_name}.blend"

        # Save the blend file
        bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
        
        self.report({'INFO'}, f"Blend file saved to {save_path}")
        return {'FINISHED'}

class UpdateProjectOperator(bpy.types.Operator):
    bl_idname = "scene.update_project"
    bl_label = "Update Project"
    bl_description = "Update the project directory based on the current list"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        directory_path = Path(scene.directory_path).resolve()

        if not os.path.exists(directory_path):
            self.report({'ERROR'}, "Directory does not exist.")
            return {'CANCELLED'}

        # Gather current Blender folder names
        blender_folder_names = {folder.name for folder in scene.folder_list}

        # Check folders in the directory
        existing_folders = set(os.listdir(directory_path))

        # Folders to be added and removed
        folders_to_add = blender_folder_names - existing_folders
        folders_to_remove = existing_folders - blender_folder_names

        try:
            # Add new folders
            for folder_name in folders_to_add:
                folder_path = directory_path / folder_name
                os.mkdir(folder_path)

            # Remove folders
            for folder_name in folders_to_remove:
                folder_path = directory_path / folder_name
                shutil.rmtree(folder_path)

            self.report({'INFO'}, "Project folders updated successfully.")
            return {'FINISHED'}
        except FileExistsError as e:
            self.report({'INFO'}, f"Folder '{e.filename}' already exists. Skipping creation.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error updating project folders: {str(e)}")
            return {'CANCELLED'}

        self.report({'INFO'}, "Project folders updated successfully.")
        return {'FINISHED'}

class OpenPureRefOperator(bpy.types.Operator):
    bl_idname = "rockhelper.open_pureref"
    bl_label = "Open PureRef Board"
    bl_description = "Open the specified PureRef project file"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pure_ref_path = context.scene.pure_ref_path

        if pure_ref_path and pure_ref_path.lower().endswith(".pur"):
            try:
                # Convert the path to an absolute path
                absolute_path = bpy.path.abspath(pure_ref_path)
                
                if os.path.isfile(absolute_path):
                    with open(absolute_path, 'rb') as file:
                        subprocess.Popen([absolute_path], shell=True)
                else:
                    self.report({'ERROR'}, f"PureRef project file not found: {absolute_path}")
            except Exception as e:
                self.report({'ERROR'}, f"Error opening PureRef: {str(e)}")
        else:
            self.report({'ERROR'}, "Please specify a valid PureRef project file.")

        return {'FINISHED'}

#Preferences
class ProjectSetUpPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    github_url: bpy.props.StringProperty(
        name="GitHub URL",
        description="https://github.com/RenaudLapierre/Blender-ProjectSetUp",
        default="https://github.com/RenaudLapierre/Blender-ProjectSetUp",
    )

    sketchfab_url: bpy.props.StringProperty(
        name="Sketchfab URL",
        description="https://sketchfab.com/renaudlapierre",
        default="https://sketchfab.com/renaudlapierre",
    )

    # Define the property for custom folder names as a string
    default_folder_names: bpy.props.StringProperty(
        name="Default Folder Names",
        description="Enter custom folder names as a comma-separated list",
        default="Blender,Geo,Painter,Photoshop,References,Renders,Textures"
    )


    def draw(self, context):
        layout = self.layout
        row = layout.row()

        row.operator("wm.url_open", text="GitHub Page", icon="LINK_BLEND").url = self.github_url
        row.operator("wm.url_open", text="Buy me a coffee", icon="FUND").url = self.sketchfab_url

        layout.label(text="If you'd like to change the default list, you can do so here:")
        layout.label(text="Necessary Folder Name: Blender")
        layout.prop(self, "default_folder_names", text="Default Folder Names")

        layout.label(text="If you have any ideas, please reach out!")

class VIEW3D_PT_project_setup_panel(bpy.types.Panel):
    bl_label = "Project Setup"
    bl_idname = "VIEW3D_PT_project_setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box=layout.box()

        # Add an input field to choose a directory path
        col = box.column(align=True)
        col.label(text="Project Folder:")
        col.prop(context.scene, "directory_path", text="")

        # Input filed for blend file name
        col = box.column(align=True)
        col.label(text=".Blend Name:")
        col.prop(context.scene, "blend_name", text="")

        # Add a button to add DEFAULT folders to the list
        box.operator("scene.add_default_folder", text="Add Default Folders", icon="NEWFOLDER")

        # Add a button to create the project
        box.operator("scene.create_project", icon="FILE_FOLDER")

        box.operator("scene.set_blend_file", icon="FILE_TICK", text="Save Blend File")

        box.label(text="Project Structure:")

        # Use split() to create vertical space
        split = box.split(factor=0.9, align=True)

        # Display the list of folders using a template_list
        col = split.column()
        col.template_list("UI_UL_list", "folder_list", scene, "folder_list", scene, "active_folder_index", type='DEFAULT', rows=3)

        # Create a column for the buttons
        col = split.column()
        col.operator("scene.add_new_folder", text="", icon="ADD")
        col.operator("scene.remove_folder", text="", icon="REMOVE")

        box.operator("scene.update_project", text="Update Folder", icon="FILE_REFRESH")

        box=layout.box()
        box.label(text="PureRef File:")
        # Add the PureRef file path
        box.prop(context.scene, "pure_ref_path", text="")
        # Add Open PureRef Board Button
        box.operator("rockhelper.open_pureref", icon="IMAGE_DATA", text="Open PureRef Board")
        
classes = (
    VIEW3D_PT_project_setup_panel,
    AddDefaultFolderOperator,
    AddNewFolderOperator,
    RemoveFolderOperator,
    CreateProjectOperator,
    SetBlendFileOperator,
    UpdateProjectOperator,
    OpenPureRefOperator,
    ProjectSetUpPreferences,
    UpdateFolderPreferencesOperator,
)
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
