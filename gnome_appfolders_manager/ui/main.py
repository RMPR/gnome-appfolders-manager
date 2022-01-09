##
#     Project: GNOME App Folders Manager
# Description: Manage GNOME Shell applications folders
#      Author: Fabio Castelli (Muflone) <muflone@muflone.com>
#   Copyright: 2016-2022 Fabio Castelli
#     License: GPL-3+
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 2 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
##

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio

from gnome_appfolders_manager.constants import (APP_NAME,
                                                FILE_SETTINGS,
                                                FILE_WINDOWS_POSITION,
                                                SCHEMA_FOLDERS)
from gnome_appfolders_manager.functions import (_,
                                                get_ui_file,
                                                get_treeview_selected_row,
                                                text)
from gnome_appfolders_manager.gtkbuilder_loader import GtkBuilderLoader
import gnome_appfolders_manager.preferences as preferences
import gnome_appfolders_manager.settings as settings

from gnome_appfolders_manager.models.appfolder_info import AppFolderInfo
from gnome_appfolders_manager.models.appfolders import ModelAppFolders
from gnome_appfolders_manager.models.application_info import ApplicationInfo
from gnome_appfolders_manager.models.applications import ModelApplications
from gnome_appfolders_manager.models.folder_info import FolderInfo

from gnome_appfolders_manager.ui.about import UIAbout
from gnome_appfolders_manager.ui.application_picker import UIApplicationPicker
from gnome_appfolders_manager.ui.create_appfolder import UICreateAppFolder
from gnome_appfolders_manager.ui.message_dialog import (show_message_dialog,
                                                        UIMessageDialogNoYes)
from gnome_appfolders_manager.ui.shortcuts import UIShortcuts

SECTION_WINDOW_NAME = 'main'


class UIMain(object):
    def __init__(self, application):
        self.application = application
        # Load settings
        settings.settings = settings.Settings(FILE_SETTINGS, False)
        settings.positions = settings.Settings(FILE_WINDOWS_POSITION, False)
        self.folders = {}
        preferences.preferences = preferences.Preferences()
        self.load_ui()
        # Prepares the models for folders and applications
        self.model_folders = ModelAppFolders(self.ui.store_folders)
        self.model_applications = ModelApplications(self.ui.store_applications)
        self.model_applications.model.set_sort_column_id(
            self.ui.treeview_column_applications.get_sort_column_id(),
            Gtk.SortType.ASCENDING)
        # Detect the AppFolders and select the first one automatically
        self.reload_folders()
        if self.model_folders.count() > 0:
            self.ui.treeview_folders.set_cursor(0)
        self.ui.treeview_folders.grab_focus()
        # Restore the saved size and position
        settings.positions.restore_window_position(
            self.ui.win_main, SECTION_WINDOW_NAME)

    def load_ui(self):
        """Load the interface UI"""
        self.ui = GtkBuilderLoader(get_ui_file('main.ui'))
        self.ui.win_main.set_application(self.application)
        self.ui.win_main.set_title(APP_NAME)
        # Initialize actions
        for widget in self.ui.get_objects_by_type(Gtk.Action):
            # Connect the actions accelerators
            widget.connect_accelerator()
            # Set labels
            label = widget.get_label()
            if not label:
                label = widget.get_short_label()
            widget.set_label(text(label))
            widget.set_short_label(label)
        # Initialize labels
        for widget in self.ui.get_objects_by_type(Gtk.Label):
            widget.set_label(text(widget.get_label()))
        # Initialize tooltips
        for widget in self.ui.get_objects_by_type(Gtk.Button):
            action = widget.get_related_action()
            if action:
                widget.set_tooltip_text(action.get_label().replace('_', ''))
        # Initialize Gtk.HeaderBar
        self.ui.header_bar.props.title = self.ui.win_main.get_title()
        self.ui.win_main.set_titlebar(self.ui.header_bar)
        for button in (self.ui.button_folder_new, self.ui.button_folder_remove,
                       self.ui.button_folder_properties,
                       self.ui.button_files_add, self.ui.button_files_remove,
                       self.ui.button_files_save, self.ui.button_about, ):
            action = button.get_related_action()
            icon_name = action.get_icon_name()
            if preferences.get(preferences.HEADERBARS_SYMBOLIC_ICONS):
                icon_name += '-symbolic'
            # Get desired icon size
            icon_size = (Gtk.IconSize.BUTTON
                         if preferences.get(preferences.HEADERBARS_SMALL_ICONS)
                         else Gtk.IconSize.LARGE_TOOLBAR)
            button.set_image(Gtk.Image.new_from_icon_name(icon_name,
                                                          icon_size))
            # Remove the button label
            button.props.label = None
            # Set the tooltip from the action label
            button.set_tooltip_text(action.get_label().replace('_', ''))
        # Set preferences button icon
        icon_name = self.ui.image_preferences.get_icon_name()[0]
        if preferences.get(preferences.HEADERBARS_SYMBOLIC_ICONS):
            icon_name += '-symbolic'
        self.ui.image_preferences.set_from_icon_name(icon_name, icon_size)
        # Load settings
        self.dict_settings_map = {
            preferences.HEADERBARS_SMALL_ICONS:
                self.ui.action_preferences_small_icons,
            preferences.HEADERBARS_SYMBOLIC_ICONS:
                self.ui.action_preferences_symbolic_icons,
            preferences.PREFERENCES_SHOW_MISSING:
                self.ui.action_preferences_show_missing_files
        }
        for setting_name, action in self.dict_settings_map.items():
            action.set_active(preferences.get(setting_name))
        # Connect signals from the glade file to the module functions
        self.ui.connect_signals(self)

    def run(self):
        """Show the UI"""
        self.ui.win_main.show_all()

    def on_win_main_delete_event(self, widget, event):
        """Save the settings and close the application"""
        settings.positions.save_window_position(
            self.ui.win_main, SECTION_WINDOW_NAME)
        settings.positions.save()
        settings.settings.save()
        self.application.quit()

    def on_action_about_activate(self, action):
        """Show the about dialog"""
        dialog = UIAbout(self.ui.win_main)
        dialog.show()
        dialog.destroy()

    def on_action_shortcuts_activate(self, action):
        """Show the shortcuts dialog"""
        dialog = UIShortcuts(self.ui.win_main)
        dialog.show()

    def on_action_quit_activate(self, action):
        """Close the application by closing the main window"""
        event = Gdk.Event()
        event.key.type = Gdk.EventType.DELETE
        self.ui.win_main.event(event)

    def reload_folders(self):
        """Reload the Application Folders"""
        self.folders = {}
        self.model_folders.clear()
        settings_folders = Gio.Settings.new(SCHEMA_FOLDERS)
        list_folders = settings_folders.get_strv('folder-children')
        for folder_name in list_folders:
            folder_info = FolderInfo(folder_name)
            appfolder = AppFolderInfo(folder_info)
            self.model_folders.add_data(appfolder)
            self.folders[folder_info.folder] = folder_info

    def on_treeview_folders_cursor_changed(self, widget):
        selected_row = get_treeview_selected_row(self.ui.treeview_folders)
        if selected_row:
            folder_name = self.model_folders.get_key(selected_row)
            # Check if the folder still exists
            # (model erased while the cursor moves through the Gtk.TreeView)
            if folder_name in self.folders:
                folder_info = self.folders[folder_name]
                # Clear any previous application icon
                self.model_applications.clear()
                # Add new application icons
                applications = folder_info.get_applications()
                for application in applications:
                    desktop_file = applications[application]
                    if desktop_file or preferences.get(
                            preferences.PREFERENCES_SHOW_MISSING):
                        application_file = applications[application]
                        application_info = ApplicationInfo(
                            application,
                            application_file.getName()
                            if desktop_file else 'Missing desktop file',
                            application_file.getComment()
                            if desktop_file else application,
                            application_file.getIcon()
                            if desktop_file else None,
                            # Always show any application, also if hidden
                            True)
                        self.model_applications.add_data(application_info)
            # Disable folder content saving
            self.ui.action_files_save.set_sensitive(False)

    def on_treeview_selection_folders_changed(self, widget):
        """Set action sensitiveness on selection change"""
        selected_row = get_treeview_selected_row(self.ui.treeview_folders)
        for widget in (self.ui.action_folders_remove,
                       self.ui.action_folders_properties,
                       self.ui.action_files_new):
            widget.set_sensitive(bool(selected_row))
        if not selected_row:
            self.ui.action_files_new.set_sensitive(False)
            self.ui.action_files_remove.set_sensitive(False)
            self.ui.action_files_save.set_sensitive(False)
            self.model_applications.clear()

    def on_action_files_new_activate(self, action):
        """Show an application picker to add to the current AppFolder"""
        dialog = UIApplicationPicker(self.ui.win_main,
                                     self.model_applications.rows.keys())
        if dialog.show() == Gtk.ResponseType.OK:
            if dialog.selected_applications:
                treeiter = None
                for application in dialog.selected_applications:
                    # Get the selected application in the application picker
                    # and add it to the current AppFolder
                    application_info = dialog.model_applications.items[
                        application]
                    self.model_applications.add_data(application_info)
                    # Automatically select the newly added application
                    filename = application_info.filename
                    treeiter = self.model_applications.rows[filename]
                if treeiter:
                    # Automatically select the last added application
                    self.ui.treeview_applications.set_cursor(
                        self.model_applications.get_path(treeiter))
                # Enable folder content saving
                self.ui.action_files_save.set_sensitive(True)
        dialog.destroy()

    def on_treeview_selection_applications_changed(self, widget):
        """Set action sensitiveness on selection change"""
        selected_row = get_treeview_selected_row(self.ui.treeview_applications)
        self.ui.action_files_remove.set_sensitive(bool(selected_row))

    def on_action_files_remove_activate(self, action):
        """Remove the selected application from the current AppFolder"""
        selected_row = get_treeview_selected_row(self.ui.treeview_applications)
        if selected_row:
            self.model_applications.remove(selected_row)
            # Enable folder content saving
            self.ui.action_files_save.set_sensitive(True)

    def on_action_files_save_activate(self, action):
        """Save the current AppFolder"""
        selected_row = get_treeview_selected_row(self.ui.treeview_folders)
        if selected_row:
            folder_name = self.model_folders.get_key(selected_row)
            folder_info = self.folders[folder_name]
            folder_info.set_applications(self.model_applications.rows.keys())
        # Disable folder content saving
        self.ui.action_files_save.set_sensitive(False)

    def on_action_folders_remove_activate(self, action):
        """Remove the current AppFolder"""
        selected_row = get_treeview_selected_row(self.ui.treeview_folders)
        if selected_row:
            folder_name = self.model_folders.get_key(selected_row)
            if show_message_dialog(class_=UIMessageDialogNoYes,
                                   parent=self.ui.win_main,
                                   message_type=Gtk.MessageType.QUESTION,
                                   title=None,
                                   msg1=_('Remove the selected folder?'),
                                   msg2=_('Are you sure you want to remove '
                                          'the folder {FOLDER}?').format(
                                       FOLDER=folder_name),
                                   is_response_id=Gtk.ResponseType.YES):
                # Remove the AppFolder from settings
                folder_info = self.folders[folder_name]
                folder_info.remove()
                self.folders.pop(folder_name)
                # Remove the folder name from the folders list
                settings_folders = Gio.Settings.new(SCHEMA_FOLDERS)
                list_folders = settings_folders.get_strv('folder-children')
                list_folders.remove(folder_name)
                settings_folders.set_strv('folder-children', list_folders)
                # Clear the applications model
                self.model_applications.clear()
                # Remove the folder from the folders model
                self.model_folders.remove(selected_row)

    def on_action_folders_new_activate(self, action):
        """Creat a new AppFolder"""
        dialog = UICreateAppFolder(self.ui.win_main,
                                   self.model_folders.rows.keys())
        if dialog.show(name='', title='') == Gtk.ResponseType.OK:
            # Create a new FolderInfo object and set its title
            folder_info = FolderInfo(dialog.folder_name)
            folder_info.set_title(dialog.folder_title)
            # Add the folder to the folders list
            settings_folders = Gio.Settings.new(SCHEMA_FOLDERS)
            list_folders = settings_folders.get_strv('folder-children')
            list_folders.append(dialog.folder_name)
            settings_folders.set_strv('folder-children', list_folders)
            # Reload folders list
            self.reload_folders()
        dialog.destroy()

    def on_action_folders_properties_activate(self, action):
        """Set the AppFolder properties"""
        selected_row = get_treeview_selected_row(self.ui.treeview_folders)
        if selected_row:
            name = self.model_folders.get_key(selected_row)
            title = self.model_folders.get_title(selected_row)
            dialog = UICreateAppFolder(self.ui.win_main,
                                       self.model_folders.rows.keys())
            if dialog.show(name=name, title=title) == Gtk.ResponseType.OK:
                folder_name = dialog.folder_name
                folder_title = dialog.folder_title
                # Update the folder title
                folder_info = self.folders[folder_name]
                folder_info.name = folder_title
                folder_info.set_title(folder_title)
                # Reload the folders list and select the folder again
                self.reload_folders()
                self.ui.treeview_folders.set_cursor(
                    self.model_folders.get_path_by_name(folder_name))
            dialog.destroy()

    def on_action_preferences_toggled(self, widget):
        """Change a preference value"""
        for setting_name, action in self.dict_settings_map.items():
            if action is widget:
                preferences.set(setting_name, widget.get_active())

    def on_action_preferences_need_restart_toggled(self, widget):
        """Show the infobar to require application restart"""
        self.ui.label_infobar.set_label(
            _('The application must be restarted to apply the settings'))
        self.ui.infobar.show()

    def on_action_preferences_show_missing_files_toggled(self, widget):
        """Show and hide the missing desktop files"""
        self.on_treeview_folders_cursor_changed(
            self.ui.treeview_folders)

    def on_treeview_folders_row_activated(self, widget, path, column):
        """Show folder properties on activation"""
        self.ui.action_folders_properties.activate()
