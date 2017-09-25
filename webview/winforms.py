# -*- coding: utf-8 -*-

"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
from ctypes import windll

import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Threading")
import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.localization import localization
from webview.win32_shared import set_ie_mode


logger = logging.getLogger(__name__)


class BrowserView:
    class BrowserForm(WinForms.Form):
        def __init__(self, title, url, width, height, resizable, fullscreen, min_size,
                     confirm_quit, background_color, webview_ready, flags=64, x=0, y=0):
            #self.Text = title
            self.Text = None
            self.ClientSize = Size(width, height)
            self.MinimumSize = Size(min_size[0], min_size[1])
            self.BackColor = ColorTranslator.FromHtml(background_color)
            self.flags = flags
            self.Location.X = x
            self.Location.Y = y
            self.TopMost = True

            if not resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            self.FormBorderStyle = 0
            # Application icon
            handle = windll.kernel32.GetModuleHandleW(None)
            icon_handle = windll.shell32.ExtractIconW(handle, sys.executable, 0)

            if icon_handle != 0:
                self.Icon = Icon.FromHandle(IntPtr.op_Explicit(Int32(icon_handle))).Clone()

            windll.user32.DestroyIcon(icon_handle)

            self.webview_ready = webview_ready

            self.web_browser = WinForms.WebBrowser()
            self.web_browser.Dock = WinForms.DockStyle.Fill
            self.web_browser.ScriptErrorsSuppressed = True
            self.web_browser.IsWebBrowserContextMenuEnabled = False
            self.web_browser.WebBrowserShortcutsEnabled = False
            self.web_browser.Visible = False
            self.first_load = True

            self.cancel_back = False
            self.web_browser.PreviewKeyDown += self.on_preview_keydown
            self.web_browser.Navigating += self.on_navigating
            self.web_browser.DocumentCompleted += self.on_document_completed

            if url:
                self.web_browser.Navigate(url)

            self.Controls.Add(self.web_browser)
            self.is_fullscreen = False
            self.Shown += self.on_shown

            if confirm_quit:
                self.FormClosing += self.on_closing

            if fullscreen:
                self.toggle_fullscreen()

        def on_shown(self, sender, args):
            self.webview_ready.set()

        def on_closing(self, sender, args):
            result = WinForms.MessageBox.Show(localization["global.quitConfirmation"], self.Text,
                                              WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

            if result == WinForms.DialogResult.Cancel:
                args.Cancel = True

        def on_preview_keydown(self, sender, args):
            if args.KeyCode == WinForms.Keys.Back:
                self.cancel_back = True
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.C:
                self.web_browser.Document.ExecCommand("Copy", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.X:
                self.web_browser.Document.ExecCommand("Cut", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.V:
                self.web_browser.Document.ExecCommand("Paste", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.Z:
                self.web_browser.Document.ExecCommand("Undo", False, None)

        def on_navigating(self, sender, args):
            if self.cancel_back:
                args.Cancel = True
                self.cancel_back = False

        def on_document_completed(self, sender, args):
            if self.first_load:
                self.web_browser.Visible = True
                self.first_load = False

        def toggle_fullscreen(self):
            if not self.is_fullscreen:
                self.old_size = self.Size
                self.old_state = self.WindowState
                self.old_style = self.FormBorderStyle
                self.old_location = self.Location

                screen = WinForms.Screen.FromControl(self)

                #self.TopMost = True
                self.FormBorderStyle = 0  # FormBorderStyle.None
                self.Bounds = WinForms.Screen.PrimaryScreen.Bounds
                self.WindowState = WinForms.FormWindowState.Maximized
                self.is_fullscreen = True

                windll.user32.SetWindowPos(self.Handle.ToInt32(), None, screen.Bounds.X, screen.Bounds.Y, screen.Bounds.Width, screen.Bounds.Height, self.flags)
            else:
                #self.TopMost = False
                self.Size = self.old_size
                self.WindowState = self.old_state
                self.FormBorderStyle = self.old_style
                self.Location = self.old_location
                self.is_fullscreen = False

        def set_window_pos(self, x, y):
            #print ("x", x, "y", y)
            windll.user32.SetWindowPos(self.Handle.ToInt32(), None, x, y, self.Size.Width, self.Size.Height, self.flags)

        def get_window_pos(self):
            return [self.Location.X, self.Location.Y] 

        def set_topmost(self, topmost):
            if self.TopMost != topmost:
                self.TopMost = topmost


    instance = None

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, confirm_quit, background_color, webview_ready, flags=64, x=0, y=0):
        BrowserView.instance = self
        self.title = title
        self.url = url
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.confirm_quit = confirm_quit
        self.webview_ready = webview_ready
        self.background_color = background_color
        self.flags = flags
        self.browser = None
        self.x = x
        self.y = y

    def show(self):
        def start():
            app = WinForms.Application
            self.browser = BrowserView.BrowserForm(self.title, self.url, self.width,self.height, self.resizable,
                                                   self.fullscreen, self.min_size, self.confirm_quit, 
                                                   self.background_color, self.webview_ready, self.flags, self.x, self.y)
            #self.browser.set_window_pos(0,0)
            app.Run(self.browser)

        thread = Thread(ThreadStart(start))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    def destroy(self):
        self.browser.Close()

    def get_current_url(self):
        return self.browser.web_browser.Url.AbsoluteUri

    def load_url(self, url):
        self.url = url
        self.browser.web_browser.Navigate(url)

    def load_html(self, content):
        def _load_html():
            self.browser.web_browser.DocumentText = content

        if self.browser.web_browser.InvokeRequired:
            self.browser.web_browser.Invoke(Func[Type](_load_html))
        else:
            _load_html()


    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if not directory:
            directory = os.environ["HOMEPATH"]

        try:
            if dialog_type == FOLDER_DIALOG:
                dialog = WinForms.FolderBrowserDialog()
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = (dialog.SelectedPath,)
                else:
                    file_path = None
            elif dialog_type == OPEN_DIALOG:
                dialog = WinForms.OpenFileDialog()

                dialog.Multiselect = allow_multiple
                dialog.InitialDirectory = directory
                dialog.Filter = localization["windows.fileFilter.allFiles"] + " (*.*)|*.*"
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = tuple(dialog.FileNames)
                else:
                    file_path = None

            elif dialog_type == SAVE_DIALOG:
                dialog = WinForms.SaveFileDialog()
                dialog.Filter = localization["windows.fileFilter.allFiles"] + " (*.*)|"
                dialog.InitialDirectory = directory
                dialog.RestoreDirectory = True
                dialog.FileName = save_filename

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = dialog.FileName
                else:
                    file_path = None

            return file_path

        except:
            logger.exception("Error invoking {0} dialog".format(dialog_type))
            return None

    def toggle_fullscreen(self):
        self.browser.toggle_fullscreen()

    def set_window_pos(self, x, y):
        self.browser.set_window_pos(x, y)

    def get_window_pos(self):
        return self.browser.get_window_pos()

    def set_topmost(self, topmost):
        self.browser.set_topmost(topmost)

def create_window(title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, webview_ready, flags=64, x=0, y=0):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen,
                               min_size, confirm_quit, background_color, webview_ready, flags, x, y)
    browser_view.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def get_current_url():
    return BrowserView.instance.get_current_url()


def load_url(url):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri):
    BrowserView.instance.load_html(content)


def toggle_fullscreen():
    BrowserView.instance.toggle_fullscreen()


def destroy_window():
    BrowserView.instance.destroy()

def set_window_pos(x, y):
    BrowserView.instance.set_window_pos(x, y)

def get_window_pos():
    return BrowserView.instance.get_window_pos()

def set_topmost(topmost):
    BrowserView.instance.set_topmost(topmost)