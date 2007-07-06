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

from gnosis.xml.pickle import *
from gnosis.xml.pickle.util import setParanoia
setParanoia(0)

from node import *
import eds_utils
import os, shutil


#-------------------------------------------------------------------------------
#                          Definition of NodeList Object
#-------------------------------------------------------------------------------


"""
Class recording a node list for a CANOpen network.
"""

class NodeList:
    
    def __init__(self, manager):
        self.Root = ""
        self.Manager = manager
        self.NetworkName = ""
        self.SlaveNodes = {}
        self.EDSNodes = {}
        self.CurrentSelected = None
    
    def GetNetworkName(self):
        return self.NetworkName
    
    def SetNetworkName(self, name):
        self.NetworkName = name
    
    def GetManager(self):
        return self.Manager
    
    def GetRoot(self):
        return self.Root
    
    def GetSlaveNumber(self):
        return len(self.SlaveNodes)
    
    def GetSlaveNames(self):
        nodes = self.SlaveNodes.keys()
        nodes.sort()
        return ["0x%2.2X %s"%(idx, self.SlaveNodes[idx]["Name"]) for idx in nodes]
    
    def GetSlaveIDs(self):
        nodes = self.SlaveNodes.keys()
        nodes.sort()
        return nodes
        
    def SetCurrentSelected(self, selected):
        self.CurrentSelected = selected
        
    def GetCurrentSelected(self):
        return self.CurrentSelected
            
    def LoadProject(self, root):
        self.SlaveNodes = {}
        self.EDSNodes = {}
        
        self.Root = root
        if not os.path.exists(self.Root):
            return "\"%s\" folder doesn't exist"%self.Root
        
        self.EDSFolder = os.path.join(self.Root, "eds")
        if not os.path.exists(self.EDSFolder):
            return "\"%s\" folder doesn't contain a \"eds\" folder"%self.Root
        
        files = os.listdir(self.EDSFolder)
        for file in files:
            result = self.LoadEDS(file)
            if result != None:
                return result
                
        result = self.LoadMasterNode()
        if result != None:
            return result
            
        result = self.LoadSlaveNodes()
        if result != None:
            return result
    
    def SaveProject(self):
        result = self.SaveMasterNode()
        if result != None:
            return result
            
        result = self.SaveNodeList()
        if result != None:
            return result
    
    def ImportEDSFile(self, edspath):
        dir, file = os.path.split(edspath)
        eds = os.path.join(self.EDSFolder, file)
        if os.path.isfile(eds):
            return "EDS file already imported"
        else:
            shutil.copy(edspath, self.EDSFolder)
            return self.LoadEDS(file)
    
    def LoadEDS(self, eds):
        edspath = os.path.join(self.EDSFolder, eds)
        node = eds_utils.GenerateNode(edspath, self.Manager.ScriptDirectory)
        if isinstance(node, Node):
            self.EDSNodes[eds] = node
            return None
        else:
            return node
    
    def AddSlaveNode(self, nodeName, nodeID, eds):
        if eds in self.EDSNodes.keys():
            slave = {"Name" : nodeName, "EDS" : eds, "Node" : self.EDSNodes[eds]}
            self.SlaveNodes[nodeID] = slave
            return None
        else:
            return "\"%s\" EDS file is not available"%eds
    
    def RemoveSlaveNode(self, index):
        if index in self.SlaveNodes.keys():
            self.SlaveNodes.pop(index)
            return None
        else:
            return "Node with \"0x%2.2X\" ID doesn't exist"
    
    def LoadMasterNode(self):
        masterpath = os.path.join(self.Root, "master.od")
        if os.path.isfile(masterpath):
            self.Manager.OpenFileInCurrent(masterpath)
        else:
            self.Manager.CreateNewNode("MasterNode", 0x00, "master", "", "None", "", "heartbeat", ["DS302"])
        return None
    
    def SaveMasterNode(self):
        masterpath = os.path.join(self.Root, "master.od")
        if self.Manager.SaveCurrentInFile(masterpath):
            return None
        else:
            return "Fail to save Master Node"
    
    def LoadSlaveNodes(self):
        cpjpath = os.path.join(self.Root, "nodelist.cpj")
        if os.path.isfile(cpjpath):
            try:
                networks = eds_utils.ParseCPJFile(cpjpath)
                if len(networks) > 0:
                    self.NetworkName = networks[0]["Name"]
                    for nodeid, node in networks[0]["Nodes"].items():
                        if node["Present"] == 1:
                            result = self.AddSlaveNode(node["Name"], nodeid, node["DCFName"])
                            if result != None:
                                return result
            except SyntaxError, message:
                return "Unable to load CPJ file\n%s"%message
        return None
    
    def SaveNodeList(self):
        cpjpath = os.path.join(self.Root, "nodelist.cpj")
        content = eds_utils.GenerateCPJContent(self)
        file = open(cpjpath, "w")
        file.write(content)
        file.close()
    
    def GetSlaveNodeEntry(self, nodeid, index, subindex = None):
        if nodeid in self.SlaveNodes.keys():
            self.SlaveNodes[nodeid]["Node"].SetNodeID(nodeid)
            return self.SlaveNodes[nodeid]["Node"].GetEntry(index, subindex)
        else:
            return "Node 0x%2.2X doesn't exist"%nodeid

    def GetMasterNodeEntry(self, index, subindex = None):
        return self.Manager.GetCurrentEntry(index, subindex)
        
    def SetMasterNodeEntry(self, index, subindex = None, value = None):
        self.Manager.SetCurrentEntry(index, subindex, value)
    
    def GetOrderNumber(self, nodeid):
        nodeindexes = self.SlaveNodes.keys()
        nodeindexes.sort()
        return nodeindexes.index(nodeid) + 1
    
    def GetNodeByOrder(self, order):
        if order > 0:
            nodeindexes = self.SlaveNodes.keys()
            nodeindexes.sort()
            print nodeindexes
            if order <= len(nodeindexes):
                return self.SlaveNodes[nodeindexes[order - 1]]["Node"]
        return None
    
    def IsCurrentEntry(self, index):
        if self.CurrentSelected != None:
            if self.CurrentSelected == 0:
                return self.Manager.IsCurrentEntry(index)
            else:
                node = self.SlaveNodes[self.CurrentSelected]["Node"]
                if node:
                    return node.IsEntry(index)
        return False
    
    def GetEntryInfos(self, index):
        if self.CurrentSelected != None:
            if self.CurrentSelected == 0:
                return self.Manager.GetEntryInfos(index)
            else:
                node = self.SlaveNodes[self.CurrentSelected]["Node"]
                if node:
                    return node.GetEntryInfos(index)
        return None

    def GetCurrentValidIndexes(self, min, max):
        if self.CurrentSelected != None:
            if self.CurrentSelected == 0:
                return self.Manager.GetCurrentValidIndexes(min, max)
            else:
                node = self.SlaveNodes[self.CurrentSelected]["Node"]
                if node:
                    validindexes = []
                    for index in node.GetIndexes():
                        if min <= index <= max:
                            validindexes.append((node.GetEntryName(index), index))
                    return validindexes
                else:
                    print "Can't find node"
        return []
    
    def GetCurrentEntryValues(self, index):
        if self.CurrentSelected != None:
            node = self.SlaveNodes[self.CurrentSelected]["Node"]
            node.SetNodeID(self.CurrentSelected)
            if node:
                return self.Manager.GetNodeEntryValues(node, index)
            else:
                print "Can't find node"
        return [], []

if __name__ == "__main__":
    from nodemanager import *
    import os, sys, shutil
    
    manager = NodeManager(sys.path[0])
    nodelist = NodeList(manager)
    #result = nodelist.LoadProject("/home/deobox/beremiz/test_nodelist")
    result = nodelist.LoadProject("/home/deobox/Desktop/TestMapping")
    if result != None:
        print result
    else:
        print "MasterNode :"
        manager.CurrentNode.Print()
        for nodeid, node in nodelist.SlaveNodes.items():
            print "SlaveNode name=%s id=0x%2.2X :"%(node["Name"], nodeid)
            node["Node"].Print()

