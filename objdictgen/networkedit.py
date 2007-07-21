#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of CanFestival, a library implementing CanOpen Stack. 
#
#Copyright (C): Edouard TISSERANT, Francis DUPIN and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from wxPython.wx import *
from wxPython.grid import *
import wx
from wx.lib.anchors import LayoutAnchors
import wx.grid

from types import *
import os, re, platform, sys, time, traceback, getopt

__version__ = "$Revision$"

from nodelist import *
from nodemanager import *
from subindextable import *
from commondialogs import *
from doc_index.DS301_index import *

def create(parent):
    return networkedit(parent)

def usage():
    print "\nUsage of networkedit.py :"
    print "\n   %s [Projectpath]\n"%sys.argv[0]

try:
    opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
except getopt.GetoptError:
    # print help information and exit:
    usage()
    sys.exit(2)

for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()

if len(args) == 0:
    projectOpen = None 
elif len(args) == 1:
    projectOpen = args[0]
else:
    usage()
    sys.exit(2)
ScriptDirectory = ""
for path in sys.path:
    if os.path.isfile(os.path.join(path, "networkedit.py")):
        ScriptDirectory = path

try:
    from wxPython.html import *

    wxEVT_HTML_URL_CLICK = wxNewId()

    def EVT_HTML_URL_CLICK(win, func):
        win.Connect(-1, -1, wxEVT_HTML_URL_CLICK, func)

    class wxHtmlWindowUrlClick(wxPyEvent):
        def __init__(self, linkinfo):
            wxPyEvent.__init__(self)
            self.SetEventType(wxEVT_HTML_URL_CLICK)
            self.linkinfo = (linkinfo.GetHref(), linkinfo.GetTarget())

    class wxUrlClickHtmlWindow(wxHtmlWindow):
        """ HTML window that generates and OnLinkClicked event.

        Use this to avoid having to override HTMLWindow
        """
        def OnLinkClicked(self, linkinfo):
            wxPostEvent(self, wxHtmlWindowUrlClick(linkinfo))
    
#-------------------------------------------------------------------------------
#                                Html Frame
#-------------------------------------------------------------------------------

    [wxID_HTMLFRAME, wxID_HTMLFRAMEHTMLCONTENT] = [wx.NewId() for _init_ctrls in range(2)]

    class HtmlFrame(wx.Frame):
        def _init_ctrls(self, prnt):
            # generated method, don't edit
            wx.Frame.__init__(self, id=wxID_HTMLFRAME, name='HtmlFrame',
                  parent=prnt, pos=wx.Point(320, 231), size=wx.Size(853, 616),
                  style=wx.DEFAULT_FRAME_STYLE, title='')
            self.Bind(wx.EVT_CLOSE, self.OnCloseFrame, id=wxID_HTMLFRAME)
            
            self.HtmlContent = wxUrlClickHtmlWindow(id=wxID_HTMLFRAMEHTMLCONTENT,
                  name='HtmlContent', parent=self, pos=wx.Point(0, 0),
                  size=wx.Size(-1, -1), style=wxHW_SCROLLBAR_AUTO|wxHW_NO_SELECTION)
            EVT_HTML_URL_CLICK(self.HtmlContent, self.OnLinkClick)

        def __init__(self, parent, opened):
            self._init_ctrls(parent)
            self.HtmlFrameOpened = opened
        
        def SetHtmlCode(self, htmlcode):
            self.HtmlContent.SetPage(htmlcode)
            
        def SetHtmlPage(self, htmlpage):
            self.HtmlContent.LoadPage(htmlpage)
            
        def OnCloseFrame(self, event):
            self.HtmlFrameOpened.remove(self.GetTitle())
            event.Skip()
        
        def OnLinkClick(self, event):
            url = event.linkinfo[0]
            try:
                import webbrowser
            except ImportError:
                wxMessageBox('Please point your browser at: %s' % url)
            else:
                webbrowser.open(url)
    
    Html_Window = True
except:
    Html_Window = False


[wxID_NETWORKEDIT, wxID_NETWORKEDITNETWORKNODES, 
 wxID_NETWORKEDITHELPBAR,
] = [wx.NewId() for _init_ctrls in range(3)]

[wxID_NETWORKEDITADDMENUITEMS0, wxID_NETWORKEDITADDMENUITEMS1, 
 wxID_NETWORKEDITADDMENUITEMS2, wxID_NETWORKEDITADDMENUITEMS3, 
 wxID_NETWORKEDITADDMENUITEMS4, wxID_NETWORKEDITADDMENUITEMS5, 
] = [wx.NewId() for _init_coll_AddMenu_Items in range(6)]

[wxID_NETWORKEDITFILEMENUITEMS0, wxID_NETWORKEDITFILEMENUITEMS1, 
 wxID_NETWORKEDITFILEMENUITEMS2, wxID_NETWORKEDITFILEMENUITEMS4, 
 wxID_NETWORKEDITFILEMENUITEMS5, wxID_NETWORKEDITFILEMENUITEMS6,
] = [wx.NewId() for _init_coll_FileMenu_Items in range(6)]

[wxID_NETWORKEDITNETWORKMENUITEMS0, wxID_NETWORKEDITNETWORKMENUITEMS1, 
 wxID_NETWORKEDITNETWORKMENUITEMS3, 
] = [wx.NewId() for _init_coll_AddMenu_Items in range(3)]


[wxID_NETWORKEDITEDITMENUITEMS0, wxID_NETWORKEDITEDITMENUITEMS1, 
 wxID_NETWORKEDITEDITMENUITEMS2, wxID_NETWORKEDITEDITMENUITEMS4, 
 wxID_NETWORKEDITEDITMENUITEMS6, wxID_NETWORKEDITEDITMENUITEMS7, 
 wxID_NETWORKEDITEDITMENUITEMS8, 
] = [wx.NewId() for _init_coll_EditMenu_Items in range(7)]

[wxID_NETWORKEDITHELPMENUITEMS0, wxID_NETWORKEDITHELPMENUITEMS1,
 wxID_NETWORKEDITHELPMENUITEMS2,
] = [wx.NewId() for _init_coll_HelpMenu_Items in range(3)]

class networkedit(wx.Frame):
    def _init_coll_menuBar1_Menus(self, parent):
        # generated method, don't edit

        if self.ModeSolo:
            parent.Append(menu=self.FileMenu, title='File')
        parent.Append(menu=self.NetworkMenu, title='Network')
        parent.Append(menu=self.EditMenu, title='Edit')
        parent.Append(menu=self.AddMenu, title='Add')
        parent.Append(menu=self.HelpMenu, title='Help')

    def _init_coll_EditMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS4,
              kind=wx.ITEM_NORMAL, text='Refresh\tCTRL+R')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS1,
              kind=wx.ITEM_NORMAL, text='Undo\tCTRL+Z')
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS0,
              kind=wx.ITEM_NORMAL, text='Redo\tCTRL+Y')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS6,
              kind=wx.ITEM_NORMAL, text='Node infos')
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS2,
              kind=wx.ITEM_NORMAL, text='DS-301 Profile')
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS8,
              kind=wx.ITEM_NORMAL, text='DS-302 Profile')
        parent.Append(help='', id=wxID_NETWORKEDITEDITMENUITEMS7,
              kind=wx.ITEM_NORMAL, text='Other Profile')
        self.Bind(wx.EVT_MENU, self.OnUndoMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS1)
        self.Bind(wx.EVT_MENU, self.OnRedoMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnCommunicationMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnRefreshMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS4)
        self.Bind(wx.EVT_MENU, self.OnNodeInfosMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS6)
        self.Bind(wx.EVT_MENU, self.OnEditProfileMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS7)
        self.Bind(wx.EVT_MENU, self.OnOtherCommunicationMenu,
              id=wxID_NETWORKEDITEDITMENUITEMS8)

    def _init_coll_HelpMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_NETWORKEDITHELPMENUITEMS0,
              kind=wx.ITEM_NORMAL, text='DS-301 Standard\tF1')
        self.Bind(wx.EVT_MENU, self.OnHelpDS301Menu,
              id=wxID_NETWORKEDITHELPMENUITEMS0)
        parent.Append(help='', id=wxID_NETWORKEDITHELPMENUITEMS1,
              kind=wx.ITEM_NORMAL, text='CAN Festival Docs\tF2')
        self.Bind(wx.EVT_MENU, self.OnHelpCANFestivalMenu,
              id=wxID_NETWORKEDITHELPMENUITEMS1)
        if Html_Window and self.ModeSolo:
            parent.Append(help='', id=wxID_NETWORKEDITHELPMENUITEMS2,
                  kind=wx.ITEM_NORMAL, text='About')
            self.Bind(wx.EVT_MENU, self.OnAboutMenu,
                  id=wxID_NETWORKEDITHELPMENUITEMS2)

    def _init_coll_FileMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_NETWORKEDITFILEMENUITEMS5,
              kind=wx.ITEM_NORMAL, text='New\tCTRL+N')
        parent.Append(help='', id=wxID_NETWORKEDITFILEMENUITEMS0,
              kind=wx.ITEM_NORMAL, text='Open\tCTRL+O')
        parent.Append(help='', id=wxID_NETWORKEDITFILEMENUITEMS1,
              kind=wx.ITEM_NORMAL, text='Save\tCTRL+S')
        parent.Append(help='', id=wxID_NETWORKEDITFILEMENUITEMS2,
              kind=wx.ITEM_NORMAL, text='Close\tCTRL+W')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_NETWORKEDITFILEMENUITEMS4,
              kind=wx.ITEM_NORMAL, text='Exit')
        self.Bind(wx.EVT_MENU, self.OnOpenProjectMenu,
              id=wxID_NETWORKEDITFILEMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectMenu,
              id=wxID_NETWORKEDITFILEMENUITEMS1)
        self.Bind(wx.EVT_MENU, self.OnCloseProjectMenu,
              id=wxID_NETWORKEDITFILEMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnQuitMenu,
              id=wxID_NETWORKEDITFILEMENUITEMS4)
        self.Bind(wx.EVT_MENU, self.OnNewProjectMenu,
              id=wxID_NETWORKEDITFILEMENUITEMS5)
    
    def _init_coll_NetworkMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_NETWORKEDITNETWORKMENUITEMS0,
              kind=wx.ITEM_NORMAL, text='Add Slave Node')
        parent.Append(help='', id=wxID_NETWORKEDITNETWORKMENUITEMS1,
              kind=wx.ITEM_NORMAL, text='Remove Slave Node')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_NETWORKEDITNETWORKMENUITEMS3,
              kind=wx.ITEM_NORMAL, text='Build Master Dictionary')
        self.Bind(wx.EVT_MENU, self.OnAddSlaveMenu,
              id=wxID_NETWORKEDITNETWORKMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnRemoveSlaveMenu,
              id=wxID_NETWORKEDITNETWORKMENUITEMS1)
##        self.Bind(wx.EVT_MENU, self.OnBuildMasterMenu,
##              id=wxID_NETWORKEDITNETWORKMENUITEMS3)
    
    def _init_coll_AddMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS0,
              kind=wx.ITEM_NORMAL, text='SDO Server')
        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS1,
              kind=wx.ITEM_NORMAL, text='SDO Client')
        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS2,
              kind=wx.ITEM_NORMAL, text='PDO Transmit')
        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS3,
              kind=wx.ITEM_NORMAL, text='PDO Receive')
        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS4,
              kind=wx.ITEM_NORMAL, text='Map Variable')
        parent.Append(help='', id=wxID_NETWORKEDITADDMENUITEMS5,
              kind=wx.ITEM_NORMAL, text='User Type')
        self.Bind(wx.EVT_MENU, self.OnAddSDOServerMenu,
              id=wxID_NETWORKEDITADDMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAddSDOClientMenu,
              id=wxID_NETWORKEDITADDMENUITEMS1)
        self.Bind(wx.EVT_MENU, self.OnAddPDOTransmitMenu,
              id=wxID_NETWORKEDITADDMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnAddPDOReceiveMenu,
              id=wxID_NETWORKEDITADDMENUITEMS3)
        self.Bind(wx.EVT_MENU, self.OnAddMapVariableMenu,
              id=wxID_NETWORKEDITADDMENUITEMS4)
        self.Bind(wx.EVT_MENU, self.OnAddUserTypeMenu,
              id=wxID_NETWORKEDITADDMENUITEMS5)

    def _init_coll_HelpBar_Fields(self, parent):
        # generated method, don't edit
        parent.SetFieldsCount(3)

        parent.SetStatusText(number=0, text='')
        parent.SetStatusText(number=1, text='')
        parent.SetStatusText(number=2, text='')

        parent.SetStatusWidths([100, 110, -1])

    def _init_utils(self):
        # generated method, don't edit
        self.menuBar1 = wx.MenuBar()
        self.menuBar1.SetEvtHandlerEnabled(True)
        
        if self.ModeSolo:
            self.FileMenu = wx.Menu(title='')
        
        self.NetworkMenu = wx.Menu(title='')

        self.EditMenu = wx.Menu(title='')

        self.AddMenu = wx.Menu(title='')

        self.HelpMenu = wx.Menu(title='')

        self._init_coll_menuBar1_Menus(self.menuBar1)
        if self.ModeSolo:
            self._init_coll_FileMenu_Items(self.FileMenu)
        self._init_coll_NetworkMenu_Items(self.NetworkMenu)
        self._init_coll_EditMenu_Items(self.EditMenu)
        self._init_coll_AddMenu_Items(self.AddMenu)
        self._init_coll_HelpMenu_Items(self.HelpMenu)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Frame.__init__(self, id=wxID_NETWORKEDIT, name='networkedit',
              parent=prnt, pos=wx.Point(149, 178), size=wx.Size(1000, 700),
              style=wx.DEFAULT_FRAME_STYLE, title='Networkedit')
        self._init_utils()
        self.SetClientSize(wx.Size(1000, 700))
        self.SetMenuBar(self.menuBar1)
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame, id=wxID_NETWORKEDIT)

        self.NetworkNodes = wx.Notebook(id=wxID_NETWORKEDITNETWORKNODES,
              name='NetworkNodes', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wxNB_LEFT)
        self.NetworkNodes.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
              self.OnNodeSelectedChanged, id=wxID_NETWORKEDITNETWORKNODES)

        self.HelpBar = wx.StatusBar(id=wxID_NETWORKEDITHELPBAR, name='HelpBar',
              parent=self, style=wxST_SIZEGRIP)
        self._init_coll_HelpBar_Fields(self.HelpBar)
        self.SetStatusBar(self.HelpBar)

    def __init__(self, parent, nodelist = None):
        self.ModeSolo = nodelist == None
        self._init_ctrls(parent)
        self.Parent = parent
        self.HtmlFrameOpened = []
        self.BusId = None
        
        if self.ModeSolo:
            self.Manager = NodeManager(ScriptDirectory)
            if projectOpen:
                self.NodeList = NodeList(self.Manager)
                result = self.NodeList.LoadProject(projectOpen)
                if not result:
                    self.RefreshNetworkNodes()
            else:
                self.NodeList = None
        else:
            self.NodeList = nodelist
            self.Manager = self.NodeList.GetManager()
            self.NodeList.SetCurrentSelected(0)
            self.RefreshNetworkNodes()
            self.RefreshProfileMenu()
        
        self.RefreshBufferState()
        self.RefreshTitle()
        self.RefreshMainMenu()

    def SetBusId(self, bus_id):
        self.BusId = bus_id

    def GetBusId(self):
        return self.BusId

    def GetCurrentNodeId(self):
        selected = self.NetworkNodes.GetSelection()
        # At init selected = -1
        if selected > 0:
            window = self.NetworkNodes.GetPage(selected)
            return window.GetIndex()
        else:
            return 0

    def OnCloseFrame(self, event):
        if not self.ModeSolo:
            self.Parent.CloseEditor(self.BusId)
        event.Skip()

    def GetNoteBook(self):
        return self.NetworkNodes

    def OnQuitMenu(self, event):
        self.Close()
        event.Skip()

    def OnAddSDOServerMenu(self, event):
        self.Manager.AddSDOServerToCurrent()
        self.RefreshBufferState()
        self.RefreshCurrentIndexList()
        event.Skip()
    
    def OnAddSDOClientMenu(self, event):
        self.Manager.AddSDOClientToCurrent()
        self.RefreshBufferState()
        self.RefreshCurrentIndexList()
        event.Skip()

    def OnAddPDOTransmitMenu(self, event):
        self.Manager.AddPDOTransmitToCurrent()
        self.RefreshBufferState()
        self.RefreshCurrentIndexList()
        event.Skip()

    def OnAddPDOReceiveMenu(self, event):
        self.Manager.AddPDOReceiveToCurrent()
        self.RefreshBufferState()
        self.RefreshCurrentIndexList()
        event.Skip()

    def OnAddMapVariableMenu(self, event):
        self.AddMapVariable()
        event.Skip()

    def OnAddUserTypeMenu(self, event):
        self.AddUserType()
        event.Skip()

    def OnNodeSelectedChanged(self, event):
        selected = event.GetSelection()
        # At init selected = -1
        if selected > 0:
            window = self.NetworkNodes.GetPage(selected)
            self.NodeList.SetCurrentSelected(window.GetIndex())
        self.RefreshMainMenu()
        self.RefreshStatusBar()
        event.Skip()

#-------------------------------------------------------------------------------
#                         Load and Save Funtions
#-------------------------------------------------------------------------------

    def OnNewProjectMenu(self, event):
        if self.NodeList:
            defaultpath = os.path.dirname(self.NodeList.GetRoot())
        else:
            defaultpath = os.getcwd()
        dialog = wxDirDialog(self , "Choose a project", defaultpath, wxDD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wxID_OK:
            projectpath = dialog.GetPath()
            if os.path.isdir(projectpath) and len(os.listdir(projectpath)) == 0:
                os.mkdir(os.path.join(projectpath, "eds"))
                manager = NodeManager(ScriptDirectory)
                nodelist = NodeList(manager)
                result = nodelist.LoadProject(projectpath)
                if not result:
                    self.Manager = manager
                    self.NodeList = nodelist
                    self.NodeList.SetCurrentSelected(0)
                                        
                    self.RefreshNetworkNodes()
                    self.RefreshBufferState()
                    self.RefreshTitle()
                    self.RefreshProfileMenu()
                    self.RefreshMainMenu()
                else:
                    message = wxMessageDialog(self, result, "ERROR", wxOK|wxICON_ERROR)
                    message.ShowModal()
                    message.Destroy()
        event.Skip()

    def OnOpenProjectMenu(self, event):
        if self.NodeList:
            defaultpath = os.path.dirname(self.NodeList.GetRoot())
        else:
            defaultpath = os.getcwd()
        dialog = wxDirDialog(self , "Choose a project", defaultpath, 0)
        if dialog.ShowModal() == wxID_OK:
            projectpath = dialog.GetPath()
            if os.path.isdir(projectpath):
                manager = NodeManager(ScriptDirectory)
                nodelist = NodeList(manager)
                result = nodelist.LoadProject(projectpath)
                if not result:
                    self.Manager = manager
                    self.NodeList = nodelist
                    self.NodeList.SetCurrentSelected(0)
                    
                    self.RefreshNetworkNodes()
                    self.RefreshBufferState()
                    self.RefreshTitle()
                    self.RefreshProfileMenu()
                    self.RefreshMainMenu()
                else:
                    message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                    message.ShowModal()
                    message.Destroy()
        dialog.Destroy()
        event.Skip()

    def OnSaveProjectMenu(self, event):
        result = self.NodeList.SaveProject()
        if result:
            message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
            message.ShowModal()
            message.Destroy()
        event.Skip()

    def OnCloseProjectMenu(self, event):
        if self.NodeList:
            if self.NodeList.HasChanged():
                dialog = wxMessageDialog(self, "There are changes, do you want to save?",  "Close Project", wxYES_NO|wxCANCEL|wxICON_QUESTION)
                answer = dialog.ShowModal()
                dialog.Destroy()
                if answer == wxID_YES:
                    result = self.NodeList.SaveProject()
                    if result:
                        message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                elif answer == wxID_NO:
                    self.NodeList.ForceChanged(False)
            if not self.NodeList.HasChanged():
                self.Manager = None
                self.NodeList = None
                self.RefreshNetworkNodes()
                self.RefreshTitle()
                self.RefreshMainMenu()
        event.Skip()

#-------------------------------------------------------------------------------
#                             Slave Nodes Management
#-------------------------------------------------------------------------------

    def OnAddSlaveMenu(self, event):
        dialog = AddSlaveDialog(self)
        dialog.SetNodeList(self.NodeList)
        if dialog.ShowModal() == wxID_OK:
            values = dialog.GetValues()
            result = self.NodeList.AddSlaveNode(values["slaveName"], values["slaveNodeID"], values["edsFile"])
            if not result:
                new_editingpanel = EditingPanel(self, self.NodeList, False)
                new_editingpanel.SetIndex(values["slaveNodeID"])
                idx = self.NodeList.GetOrderNumber(values["slaveNodeID"])
                self.NetworkNodes.InsertPage(idx, new_editingpanel, "")
                self.NodeList.SetCurrentSelected(idx)
                self.NetworkNodes.SetSelection(idx)
                self.RefreshBufferState()
            else:
                message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        dialog.Destroy()
        event.Skip()

    def OnRemoveSlaveMenu(self, event):
        slavenames = self.NodeList.GetSlaveNames()
        slaveids = self.NodeList.GetSlaveIDs()
        dialog = wxSingleChoiceDialog(self, "Choose a slave to remove", "Remove slave", slavenames)
        if dialog.ShowModal() == wxID_OK:
            choice = dialog.GetSelection()
            result = self.NodeList.RemoveSlaveNode(slaveids[choice])
            if not result:
                slaveids.pop(choice)
                current = self.NetworkNodes.GetSelection()
                self.NetworkNodes.DeletePage(choice + 1)
                if self.NetworkNodes.GetPageCount() > 0:
                    new_selection = min(current, self.NetworkNodes.GetPageCount() - 1)
                    self.NetworkNodes.SetSelection(new_selection)
                    if new_selection > 0:
                        self.NodeList.SetCurrentSelected(slaveids[new_selection - 1])
                    self.RefreshBufferState()
            else:
                message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()

#-------------------------------------------------------------------------------
#                             Refresh Functions
#-------------------------------------------------------------------------------

    def RefreshTitle(self):
        if self.NodeList != None:
            self.SetTitle("Networkedit - %s"%self.NodeList.GetNetworkName())
        else:
            self.SetTitle("Networkedit")

    def OnRefreshMenu(self, event):
        self.RefreshCurrentIndexList()
        event.Skip()

    def RefreshCurrentIndexList(self):
        selected = self.NetworkNodes.GetSelection()
        if selected == 0:
            window = self.NetworkNodes.GetPage(selected)
            window.RefreshIndexList()
        else:
            pass

    def RefreshNetworkNodes(self):
        if self.NetworkNodes.GetPageCount() > 0:
            self.NetworkNodes.DeleteAllPages()
        if self.NodeList:
            new_editingpanel = EditingPanel(self, self.Manager)
            new_editingpanel.SetIndex(0)
            self.NetworkNodes.AddPage(new_editingpanel, "")
            for idx in self.NodeList.GetSlaveIDs():
                new_editingpanel = EditingPanel(self, self.NodeList, False)
                new_editingpanel.SetIndex(idx)
                self.NetworkNodes.AddPage(new_editingpanel, "")

    def RefreshStatusBar(self):
        if self.HelpBar:
            window = self.NetworkNodes.GetPage(self.NetworkNodes.GetSelection())
            selection = window.GetSelection()
            if selection:
                index, subIndex = selection
                if self.NodeList.IsCurrentEntry(index):
                    self.HelpBar.SetStatusText("Index: 0x%04X"%index, 0)
                    self.HelpBar.SetStatusText("Subindex: 0x%02X"%subIndex, 1)
                    entryinfos = self.NodeList.GetEntryInfos(index)
                    name = entryinfos["name"]
                    category = "Optional"
                    if entryinfos["need"]:
                        category = "Mandatory"
                    struct = "VAR"
                    number = ""
                    if entryinfos["struct"] & OD_IdenticalIndexes:
                        number = " possibly defined %d times"%entryinfos["nbmax"]
                    if entryinfos["struct"] & OD_IdenticalSubindexes:
                        struct = "REC"
                    elif entryinfos["struct"] & OD_MultipleSubindexes:
                        struct = "ARRAY"
                    text = "%s: %s entry of struct %s%s."%(name,category,struct,number)
                    self.HelpBar.SetStatusText(text, 2)
                else:
                    for i in xrange(3):
                        self.HelpBar.SetStatusText("", i)
            else:
                for i in xrange(3):
                    self.HelpBar.SetStatusText("", i)

    def RefreshMainMenu(self):
        if self.menuBar1:
            self.NetworkMenu.Enable(wxID_NETWORKEDITNETWORKMENUITEMS3, False)
            if self.NodeList == None:
                if self.ModeSolo:
                    self.menuBar1.EnableTop(1, False)
                    self.menuBar1.EnableTop(2, False)
                    self.menuBar1.EnableTop(3, False)
                    if self.FileMenu:
                        self.FileMenu.Enable(wxID_NETWORKEDITFILEMENUITEMS1, False)
                        self.FileMenu.Enable(wxID_NETWORKEDITFILEMENUITEMS2, False)
                else:
                    self.menuBar1.EnableTop(0, False)
                    self.menuBar1.EnableTop(1, False)
                    self.menuBar1.EnableTop(2, False)
            else:
                if self.ModeSolo:
                    self.menuBar1.EnableTop(1, True)
                    if self.FileMenu:
                        self.FileMenu.Enable(wxID_NETWORKEDITFILEMENUITEMS1, True)
                        self.FileMenu.Enable(wxID_NETWORKEDITFILEMENUITEMS2, True)
                    if self.NetworkNodes.GetSelection() == 0:
                        self.menuBar1.EnableTop(2, True)
                        self.menuBar1.EnableTop(3, True)
                    else:
                        self.menuBar1.EnableTop(2, False)      
                        self.menuBar1.EnableTop(3, False)
                else:
                    self.menuBar1.EnableTop(0, True)
                    if self.NetworkNodes.GetSelection() == 0:
                        self.menuBar1.EnableTop(1, True)
                        self.menuBar1.EnableTop(2, True)
                    else:
                        self.menuBar1.EnableTop(1, False)      
                        self.menuBar1.EnableTop(2, False)

    def RefreshProfileMenu(self):
        if self.EditMenu:
            profile = self.Manager.GetCurrentProfileName()
            edititem = self.EditMenu.FindItemById(wxID_NETWORKEDITEDITMENUITEMS7)
            if edititem:
                length = self.AddMenu.GetMenuItemCount()
                for i in xrange(length-6):
                    additem = self.AddMenu.FindItemByPosition(6)
                    self.AddMenu.Delete(additem.GetId())
                if profile not in ("None", "DS-301"):
                    edititem.SetText("%s Profile"%profile)
                    edititem.Enable(True)
                    self.AddMenu.AppendSeparator()
                    for text, indexes in self.Manager.GetCurrentSpecificMenu():
                        new_id = wx.NewId()
                        self.AddMenu.Append(help='', id=new_id, kind=wx.ITEM_NORMAL, text=text)
                        self.Bind(wx.EVT_MENU, self.GetProfileCallBack(text), id=new_id)
                else:
                    edititem.SetText("Other Profile")
                    edititem.Enable(False)

#-------------------------------------------------------------------------------
#                              Buffer Functions
#-------------------------------------------------------------------------------

    def RefreshBufferState(self):
        if self.NodeList:
            nodeID = self.Manager.GetCurrentNodeID()
            if nodeID != None:
                nodename = "0x%2.2X %s"%(nodeID, self.Manager.GetCurrentNodeName())
            else:
                nodename = self.Manager.GetCurrentNodeName()
            self.NetworkNodes.SetPageText(0, nodename)
            for idx, name in enumerate(self.NodeList.GetSlaveNames()):
                self.NetworkNodes.SetPageText(idx + 1, name)
            self.RefreshTitle()

    def OnUndoMenu(self, event):
        self.Manager.LoadCurrentPrevious()
        self.RefreshCurrentIndexList()
        self.RefreshBufferState()
        event.Skip()

    def OnRedoMenu(self, event):
        self.Manager.LoadCurrentNext()
        self.RefreshCurrentIndexList()
        self.RefreshBufferState()
        event.Skip()

#-------------------------------------------------------------------------------
#                                Help Method
#-------------------------------------------------------------------------------

    def OnHelpDS301Menu(self, event):
        find_index = False
        selected = self.NetworkNodes.GetSelection()
        if selected >= 0:
            window = self.NetworkNodes.GetPage(selected)
            result = window.GetSelection()
            if result:
                find_index = True
                index, subIndex = result
                result = OpenPDFDocIndex(index, ScriptDirectory)
                if type(result) == StringType:
                    message = wxMessageDialog(self, result, "ERROR", wxOK|wxICON_ERROR)
                    message.ShowModal()
                    message.Destroy()
        if not find_index:
            result = OpenPDFDocIndex(None, ScriptDirectory)
            if type(result) == StringType:
                message = wxMessageDialog(self, result, "ERROR", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()
        
    def OnHelpCANFestivalMenu(self, event):
        #self.OpenHtmlFrame("CAN Festival Reference", os.path.join(ScriptDirectory, "doc/canfestival.html"), wx.Size(1000, 600))
        os.system("xpdf -remote CANFESTIVAL %s %d &"%(os.path.join(ScriptDirectory, "doc/manual_en.pdf"),16))
        event.Skip()

    def OnAboutMenu(self, event):
        self.OpenHtmlFrame("About CAN Festival", os.path.join(ScriptDirectory, "doc/about.html"), wx.Size(500, 450))
        event.Skip()

    def OpenHtmlFrame(self, title, file, size):
        if title not in self.HtmlFrameOpened:
            self.HtmlFrameOpened.append(title)
            window = HtmlFrame(self, self.HtmlFrameOpened)
            window.SetTitle(title)
            window.SetHtmlPage(file)
            window.SetClientSize(size)
            window.Show()

#-------------------------------------------------------------------------------
#                          Editing Profiles functions
#-------------------------------------------------------------------------------

    def OnCommunicationMenu(self, event):
        dictionary,current = self.Manager.GetCurrentCommunicationLists()
        self.EditProfile("Edit DS-301 Profile", dictionary, current)
        event.Skip()
    
    def OnOtherCommunicationMenu(self, event):
        dictionary,current = self.Manager.GetCurrentDS302Lists()
        self.EditProfile("Edit DS-301 Profile", dictionary, current)
        event.Skip()
    
    def OnEditProfileMenu(self, event):
        title = "Edit %s Profile"%self.Manager.GetCurrentProfileName()
        dictionary,current = self.Manager.GetCurrentProfileLists()
        self.EditProfile(title, dictionary, current)
        event.Skip()
    
    def EditProfile(self, title, dictionary, current):
        dialog = CommunicationDialog(self)
        dialog.SetTitle(title)
        dialog.SetIndexDictionary(dictionary)
        dialog.SetCurrentList(current)
        dialog.RefreshLists()
        if dialog.ShowModal() == wxID_OK:
            new_profile = dialog.GetCurrentList()
            addinglist = []
            removinglist = []
            for index in new_profile:
                if index not in current:
                    addinglist.append(index)
            for index in current:
                if index not in new_profile:
                    removinglist.append(index)
            self.Manager.ManageEntriesOfCurrent(addinglist, removinglist)
            self.Manager.GenerateMapList()
            self.Manager.BufferCurrentNode()
            self.RefreshBufferState()
            self.RefreshCurrentIndexList()
        dialog.Destroy()

#-------------------------------------------------------------------------------
#                         Edit Node informations function
#-------------------------------------------------------------------------------

    def OnNodeInfosMenu(self, event):
        dialog = NodeInfosDialog(self)
        name, id, type, description = self.Manager.GetCurrentNodeInfos()
        dialog.SetValues(name, id, type, description)
        if dialog.ShowModal() == wxID_OK:
            name, id, type, description = dialog.GetValues()
            self.Manager.SetCurrentNodeInfos(name, id, type, description)
            self.RefreshBufferState()
            self.RefreshProfileMenu()
            selected = self.FileOpened.GetSelection()
            if selected >= 0:
                window = self.FileOpened.GetPage(selected)
                window.RefreshTable()
        event.Skip()


#-------------------------------------------------------------------------------
#                           Add User Types and Variables
#-------------------------------------------------------------------------------
        
    def AddMapVariable(self):
        index = self.Manager.GetCurrentNextMapIndex()
        if index:
            dialog = MapVariableDialog(self)
            dialog.SetIndex(index)
            if dialog.ShowModal() == wxID_OK:
                index, name, struct, number = dialog.GetValues()
                result = self.Manager.AddMapVariableToCurrent(index, name, struct, number)
                if type(result) != StringType:
                    self.RefreshBufferState()
                    self.RefreshCurrentIndexList()
                else:
                    message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                    message.ShowModal()
                    message.Destroy()
            dialog.Destroy()
        else:
            message = wxMessageDialog(self, result, "No map variable index left!", wxOK|wxICON_ERROR)
            message.ShowModal()
            message.Destroy()
        
    def AddUserType(self):
        dialog = UserTypeDialog(self)
        dialog.SetTypeList(self.Manager.GetCustomisableTypes())
        if dialog.ShowModal() == wxID_OK:
            type, min, max, length = dialog.GetValues()
            result = self.Manager.AddUserTypeToCurrent(type, min, max, length)
            if not IsOfType(result, StringType):
                self.RefreshBufferState()
                self.RefreshCurrentIndexList()
            else:
                message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        dialog.Destroy()

#-------------------------------------------------------------------------------
#                               Exception Handler
#-------------------------------------------------------------------------------

Max_Traceback_List_Size = 20

def Display_Exception_Dialog(e_type,e_value,e_tb):
    trcbck_lst = []
    for i,line in enumerate(traceback.extract_tb(e_tb)):
        trcbck = " " + str(i+1) + ". "
        if line[0].find(os.getcwd()) == -1:
            trcbck += "file : " + str(line[0]) + ",   "
        else:
            trcbck += "file : " + str(line[0][len(os.getcwd()):]) + ",   "
        trcbck += "line : " + str(line[1]) + ",   " + "function : " + str(line[2])
        trcbck_lst.append(trcbck)
        
    # Allow clicking....
    cap = wx.Window_GetCapture()
    if cap:
        cap.ReleaseMouse()

    dlg = wx.SingleChoiceDialog(None, 
        """
An error happens.

Click on OK for saving an error report.

Please contact LOLITech at:
+33 (0)3 29 52 95 67
bugs_networkedit@lolitech.fr


Error:
""" +
        str(e_type) + " : " + str(e_value), 
        "Error",
        trcbck_lst)
    try:
        res = (dlg.ShowModal() == wx.ID_OK)
    finally:
        dlg.Destroy()

    return res

def Display_Error_Dialog(e_value):
    message = wxMessageDialog(None, str(e_value), "Error", wxOK|wxICON_ERROR)
    message.ShowModal()
    message.Destroy()

def get_last_traceback(tb):
    while tb.tb_next:
        tb = tb.tb_next
    return tb


def format_namespace(d, indent='    '):
    return '\n'.join(['%s%s: %s' % (indent, k, repr(v)[:10000]) for k, v in d.iteritems()])


ignored_exceptions = [] # a problem with a line in a module is only reported once per session

def wxAddExceptHook(path, app_version='[No version]'):#, ignored_exceptions=[]):
    
    def handle_exception(e_type, e_value, e_traceback):
        traceback.print_exception(e_type, e_value, e_traceback) # this is very helpful when there's an exception in the rest of this func
        last_tb = get_last_traceback(e_traceback)
        ex = (last_tb.tb_frame.f_code.co_filename, last_tb.tb_frame.f_lineno)
        if str(e_value).startswith("!!!"):
            Display_Error_Dialog(e_value)
        elif ex not in ignored_exceptions:
            ignored_exceptions.append(ex)
            result = Display_Exception_Dialog(e_type,e_value,e_traceback)
            if result:
                info = {
                    'app-title' : wx.GetApp().GetAppName(), # app_title
                    'app-version' : app_version,
                    'wx-version' : wx.VERSION_STRING,
                    'wx-platform' : wx.Platform,
                    'python-version' : platform.python_version(), #sys.version.split()[0],
                    'platform' : platform.platform(),
                    'e-type' : e_type,
                    'e-value' : e_value,
                    'date' : time.ctime(),
                    'cwd' : os.getcwd(),
                    }
                if e_traceback:
                    info['traceback'] = ''.join(traceback.format_tb(e_traceback)) + '%s: %s' % (e_type, e_value)
                    last_tb = get_last_traceback(e_traceback)
                    exception_locals = last_tb.tb_frame.f_locals # the locals at the level of the stack trace where the exception actually occurred
                    info['locals'] = format_namespace(exception_locals)
                    if 'self' in exception_locals:
                        info['self'] = format_namespace(exception_locals['self'].__dict__)
                
                output = open(path+os.sep+"bug_report_"+info['date'].replace(':','-').replace(' ','_')+".txt",'w')
                lst = info.keys()
                lst.sort()
                for a in lst:
                    output.write(a+":\n"+str(info[a])+"\n\n")

    #sys.excepthook = lambda *args: wx.CallAfter(handle_exception, *args)
    sys.excepthook = handle_exception

if __name__ == '__main__':
    app = wxPySimpleApp()
    wxInitAllImageHandlers()
    
    # Install a exception handle for bug reports
    wxAddExceptHook(os.getcwd(),__version__)
    
    frame = networkedit(None)

    frame.Show()
    app.MainLoop()
