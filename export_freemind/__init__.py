"""

    KeepNote
    Export FreeMind Extension

"""

#
#  KeepNote - Export FreeMind Extension
#  Copyright (c) 2011 James Brotchie
#  Author: James Brotchie <brotchie@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.
#

# TODO: 
#   - Support images within HTML (embedded?).

# python imports
import os
import time
from StringIO import StringIO

# keepnote imports
from keepnote import unicode_gtk
from keepnote.notebook import NoteBookError
from keepnote import notebook as notebooklib
from keepnote import tasklib
from keepnote.gui import extension, FileChooserDialog

# lxml imports
from lxml import etree

# pygtk imports
try:
    import pygtk
    pygtk.require('2.0')
    from gtk import gdk
    import gtk.glade
    import gobject
except ImportError:
    # do not fail on gtk import error,
    # extension should be usable for non-graphical uses
    pass

FREEMIND_VERSION = "0.9.0"

class Extension(extension.Extension):
    def __init__(self, app):
        """Initialize extension"""
        super(Extension, self).__init__(app)
        self.app = app

    def get_depends(self):
        return [("keepnote", ">=", (0, 7, 1))]

    def on_add_ui(self, window):
        """Initialize extension for a particular window"""

        # add menu options
        self.add_action(window, "Export FreeMind", "_FreeMind...",
                        lambda w: self.on_export_notebook(
                window, window.get_notebook()))
        
        self.add_ui(window,
            """
            <ui>
            <menubar name="main_menu_bar">
               <menu action="File">
                  <menu action="Export">
                     <menuitem action="Export FreeMind"/>
                  </menu>
               </menu>
            </menubar>
            </ui>
            """)

    def on_export_notebook(self, window, notebook):
        """Callback from gui for exporting a notebook"""
        
        if notebook is None:
            return

        dialog = FileChooserDialog("Export Notebook", window, 
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=("Cancel", gtk.RESPONSE_CANCEL,
                     "Export", gtk.RESPONSE_OK),
            app=self.app,
            persistent_path="archive_notebook_path")


        basename = time.strftime(os.path.basename(notebook.get_path()) +
                                 "-%Y-%m-%d")

        path = self.app.get_default_path("archive_notebook_path")
        if path and os.path.exists(path):
            filename = notebooklib.get_unique_filename(
                path, basename, "", ".")
        else:
            filename = basename
        filename += '.mm'
        dialog.set_current_name(os.path.basename(filename))
        
        response = dialog.run()

        if response == gtk.RESPONSE_OK and dialog.get_filename():
            filename = unicode_gtk(dialog.get_filename())
            dialog.destroy()
            self.export_notebook(notebook, filename, window=window)
        else:
            dialog.destroy()

    def export_notebook(self, notebook, filename, window=None):

        if notebook is None:
            return

        if window:
            task = tasklib.Task(lambda task:
                                export_notebook(notebook, filename, task))

            window.wait_dialog("Exporting to '%s'..." %
                               os.path.basename(filename),
                               "Beginning export...",
                               task)

            # check exceptions
            try:
                ty, error, tracebk = task.exc_info()
                if error:
                    raise error
                window.set_status("Notebook exported")
                return True

            except NoteBookError, e:
                window.set_status("")
                window.error("Error while exporting notebook:\n%s" % e.msg, e,
                             tracebk)
                return False

            except Exception, e:
                window.set_status("")
                window.error("unknown error", e, tracebk)
                return False

        else:
            export_notebook(notebook, filename, None)

def export_notebook(notebook, filename, task):
    """
    Exports notebook to FreeMind .mm XML file.

    filename -- destination filename.

    """

    if task is None:
        # create dummy task if needed
        task = tasklib.Task()

    if os.path.exists(filename):
        raise NoteBookError("File '%s' already exists" % filename)

    # make sure all modifications are saved first
    try:
        notebook.save()
    except Exception, e:
        raise NoteBookError("Could not save notebook before exporting", e)

    # first count # of files
    nnodes = [0]
    def walk(node):
        nnodes[0] += 1
        for child in node.get_children():
            walk(child)
    walk(notebook)

    task.set_message(("text", "Exporting %d notes..." % nnodes[0]))
    nnodes2 = [0]

    def clean_etree(root):
        # HTML parser in freemind doesn't support - characters in
        # attribute names. We find any nodes with - containing
        # attribute and remove them.
        tofix = root.xpath('descendant::*[contains(name(@*), "-")]')
        for node in tofix:
            for key in node.attrib:
                if '-' in key:
                    del node.attrib[key]
        return root

    def export_node(node):
        # report progresss
        nnodes2[0] += 1
        task.set_message(("detail", node.get_attr('title')))

        element = etree.Element('node', TEXT=node.get_attr('title'))

        # Non-leaf nodes start folded.
        if node.get_children():
            element.attrib['folded'] = 'true'

        if node.get_attr("content_type") == "text/xhtml+xml":
            html_path = os.path.join(node.get_path(), node.get_page_file())
            if os.path.exists(html_path):
                # Process NoteBook html content, handling nbsp.
                html_content = file(html_path, 'r').read()
                html_content = html_content.replace('&nbsp;', '')
                html_etree = clean_etree(etree.parse(StringIO(html_content)))

                # Create a richcontent Note for FreeMind.
                richcontent = etree.Element('richcontent', TYPE='note')
                richcontent.append(html_etree.getroot())
                element.append(richcontent)
        
        for child in node.get_children():
            element.append(export_node(child))

        return element

    # Create and populate mindmap element tree.
    root = etree.Element('map', version=FREEMIND_VERSION)
    root.append(export_node(notebook))

    # Write element tree to destination filename.
    output = file(filename, 'w+')
    output.write(etree.tostring(root))
    output.close()

    task.set_message(("text", "Closing export..."))
    task.set_message(("detail", ""))
    
    if task:
        task.finish()
