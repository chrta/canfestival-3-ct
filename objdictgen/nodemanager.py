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
import xml_in, gen_cfile

from types import *
import os, re

UndoBufferLength = 20

type_model = re.compile('([\_A-Z]*)([0-9]*)')
range_model = re.compile('([\_A-Z]*)([0-9]*)\[([\-0-9]*)-([\-0-9]*)\]')
name_model = re.compile('(.*)\[(.*)\]')

def IsOfType(object, typedef):
    return type(object) == typedef

#-------------------------------------------------------------------------------
#                           Formating Name of an Entry
#-------------------------------------------------------------------------------

"""
Format the text given with the index and subindex defined
"""

def StringFormat(text, idx, sub):
    result = name_model.match(text)
    if result:
        format = result.groups()
        return format[0]%eval(format[1])
    else:
        return text

#-------------------------------------------------------------------------------
#                         Search in a Mapping Dictionary
#-------------------------------------------------------------------------------

"""
Return the index of the informations in the Object Dictionary in case of identical
indexes
"""
def FindIndex(index, mappingdictionary):
    if index in mappingdictionary:
        return index
    else:
        listpluri = [idx for idx in mappingdictionary.keys() if mappingdictionary[idx]["struct"] & OD_IdenticalIndexes]
        listpluri.sort()
        for idx in listpluri:
            nb_max = mappingdictionary[idx]["nbmax"]
            incr = mappingdictionary[idx]["incr"]
            if idx < index < idx + incr * nb_max and (index - idx)%incr == 0:
                return idx
    return None

"""
Return the index of the typename given by searching in mappingdictionary 
"""
def FindTypeIndex(typename, mappingdictionary):
    testdic = {}
    for index, values in mappingdictionary.iteritems():
        if index < 0x1000:
            testdic[values["name"]] = index
    if typename in testdic:
        return testdic[typename]
    return None

"""
Return the name of the type by searching in mappingdictionary 
"""
def FindTypeName(typeindex, mappingdictionary):
    if typeindex < 0x1000 and typeindex in mappingdictionary:
        return mappingdictionary[typeindex]["name"]
    return None

"""
Return the default value of the type by searching in mappingdictionary 
"""
def FindTypeDefaultValue(typeindex, mappingdictionary):
    if typeindex < 0x1000 and typeindex in mappingdictionary:
        return mappingdictionary[typeindex]["default"]
    return None

"""
Return the list of types defined in mappingdictionary 
"""
def FindTypeList(mappingdictionary):
    list = []
    for index in mappingdictionary.keys():
        if index < 0x1000:
            list.append((index, mappingdictionary[index]["name"]))
    return list

"""
Return the name of an entry by searching in mappingdictionary 
"""
def FindEntryName(index, mappingdictionary):
    base_index = FindIndex(index, mappingdictionary)
    if base_index:
        infos = mappingdictionary[base_index]
        if infos["struct"] & OD_IdenticalIndexes:
            return StringFormat(infos["name"], (index - base_index) / infos["incr"] + 1, 0)
        else:
            return infos["name"]
    return None

"""
Return the informations of one entry by searching in mappingdictionary 
"""
def FindEntryInfos(index, mappingdictionary):
    base_index = FindIndex(index, mappingdictionary)
    if base_index:
        copy = mappingdictionary[base_index].copy()
        if copy["struct"] & OD_IdenticalIndexes:
            copy["name"] = StringFormat(copy["name"], (index - base_index) / copy["incr"] + 1, 0)
        copy.pop("values")
        return copy
    return None

"""
Return the informations of one subentry of an entry by searching in mappingdictionary 
"""
def FindSubentryInfos(index, subIndex, mappingdictionary):
    base_index = FindIndex(index, mappingdictionary)
    if base_index:
        struct = mappingdictionary[base_index]["struct"]
        if struct & OD_Subindex:
            if struct & OD_IdenticalSubindexes:
                if struct & OD_IdenticalIndexes:
                    incr = mappingdictionary[base_index]["incr"]
                else:
                    incr = 1
                if subIndex == 0:
                    return mappingdictionary[base_index]["values"][0].copy()
                elif 0 < subIndex <= mappingdictionary[base_index]["values"][1]["nbmax"]:
                    copy = mappingdictionary[base_index]["values"][1].copy()
                    copy["name"] = StringFormat(copy["name"], (index - base_index) / incr + 1, subIndex)
                    return copy
            elif struct & OD_MultipleSubindexes and 0 <= subIndex < len(mappingdictionary[base_index]["values"]):
                return mappingdictionary[base_index]["values"][subIndex].copy()
            elif subIndex == 0:
                return mappingdictionary[base_index]["values"][0].copy()
    return None

"""
Return the list of variables that can be mapped defined in mappingdictionary 
"""
def FindMapVariableList(mappingdictionary, Manager):
    list = []
    for index in mappingdictionary.iterkeys():
        if Manager.IsCurrentEntry(index):
            for subIndex, values in enumerate(mappingdictionary[index]["values"]):
                if mappingdictionary[index]["values"][subIndex]["pdo"]:
                    infos = Manager.GetEntryInfos(mappingdictionary[index]["values"][subIndex]["type"])
                    if mappingdictionary[index]["struct"] & OD_IdenticalSubindexes:
                        values = Manager.GetCurrentEntry(index)
                        for i in xrange(len(values) - 1):
                            list.append((index, i + 1, infos["size"], StringFormat(mappingdictionary[index]["values"][subIndex]["name"],1,i+1)))
                    else:
                        list.append((index, subIndex, infos["size"], mappingdictionary[index]["values"][subIndex]["name"]))
    return list

"""
Return the list of mandatory indexes defined in mappingdictionary 
"""
def FindMandatoryIndexes(mappingdictionary):
    list = []
    for index in mappingdictionary.iterkeys():
        if index >= 0x1000 and mappingdictionary[index]["need"]:
            list.append(index)
    return list


"""
Class implementing a buffer of changes made on the current editing Object Dictionary
"""

class UndoBuffer:

    """
    Constructor initialising buffer
    """
    def __init__(self, currentstate, issaved = False):
        self.Buffer = []
        self.CurrentIndex = -1
        self.MinIndex = -1
        self.MaxIndex = -1
        # if current state is defined
        if currentstate:
            self.CurrentIndex = 0
            self.MinIndex = 0
            self.MaxIndex = 0
        # Initialising buffer with currentstate at the first place
        for i in xrange(UndoBufferLength):
            if i == 0:
                self.Buffer.append(currentstate)
            else:
                self.Buffer.append(None)
        # Initialising index of state saved
        if issaved:
            self.LastSave = 0
        else:
            self.LastSave = -1
    
    """
    Add a new state in buffer
    """
    def Buffering(self, currentstate):
        self.CurrentIndex = (self.CurrentIndex + 1) % UndoBufferLength
        self.Buffer[self.CurrentIndex] = currentstate
        # Actualising buffer limits
        self.MaxIndex = self.CurrentIndex
        if self.MinIndex == self.CurrentIndex:
            # If the removed state was the state saved, there is no state saved in the buffer
            if self.LastSave == self.MinIndex:
                self.LastSave = -1
            self.MinIndex = (self.MinIndex + 1) % UndoBufferLength
        self.MinIndex = max(self.MinIndex, 0)
    
    """
    Return current state of buffer
    """
    def Current(self):
        return self.Buffer[self.CurrentIndex]
    
    """
    Change current state to previous in buffer and return new current state
    """
    def Previous(self):
        if self.CurrentIndex != self.MinIndex:
            self.CurrentIndex = (self.CurrentIndex - 1) % UndoBufferLength
            return self.Buffer[self.CurrentIndex]
        return None
    
    """
    Change current state to next in buffer and return new current state
    """
    def Next(self):
        if self.CurrentIndex != self.MaxIndex:
            self.CurrentIndex = (self.CurrentIndex + 1) % UndoBufferLength
            return self.Buffer[self.CurrentIndex]
        return None
    
    """
    Return True if current state is the first in buffer
    """
    def IsFirst(self):
        return self.CurrentIndex == self.MinIndex
    
    """
    Return True if current state is the last in buffer
    """
    def IsLast(self):
        return self.CurrentIndex == self.MaxIndex

    """
    Note that current state is saved
    """
    def CurrentSaved(self):
        self.LastSave = self.CurrentIndex
        
    """
    Return True if current state is saved
    """
    def IsCurrentSaved(self):
        return self.LastSave == self.CurrentIndex



"""
Class which control the operations made on the node and answer to view requests
"""

class NodeManager:

    """
    Constructor
    """
    def __init__(self):
        self.LastNewIndex = 0
        self.FilePaths = []
        self.FileNames = []
        self.NodeIndex = -1
        self.CurrentNode = None
        self.UndoBuffers = []

#-------------------------------------------------------------------------------
#                         Type and Map Variable Lists
#-------------------------------------------------------------------------------

    """
    Generate the list of types defined for the current node
    """
    def GenerateTypeList(self):
        self.TypeList = ""
        self.TypeTranslation = {}
        list = self.GetTypeList()
        sep = ""
        for index, name in list:
            self.TypeList += "%s%s"%(sep,name)
            self.TypeTranslation[name] = index
            sep = ","
    
    """
    Generate the list of variables that can be mapped for the current node
    """
    def GenerateMapList(self):
        self.MapList = "None"
        self.NameTranslation = {"None" : "00000000"}
        self.MapTranslation = {"00000000" : "None"}
        list = self.GetMapVariableList()
        for index, subIndex, size, name in list:
            self.MapList += ",%s"%name
            map = "%04X%02X%02X"%(index,subIndex,size)
            self.NameTranslation[name] = map
            self.MapTranslation[map] = name
    
    """
    Return the list of types defined for the current node
    """
    def GetCurrentTypeList(self):
        return self.TypeList

    """
    Return the list of variables that can be mapped for the current node
    """
    def GetCurrentMapList(self):
        return self.MapList

#-------------------------------------------------------------------------------
#                        Create Load and Save Functions
#-------------------------------------------------------------------------------

    """
    Create a new node and add a new buffer for storing it
    """
    def CreateNewNode(self, name, id, type, profile, filepath, NMT, options):
        # Create a new node
        node = Node()
        # Try to load profile given
        result = self.LoadProfile(profile, filepath, node)
        if not IsOfType(result, StringType):
            # if success, initialising node
            self.CurrentNode = node
            self.CurrentNode.SetNodeName(name)
            self.CurrentNode.SetNodeID(id)
            self.CurrentNode.SetNodeType(type)
            AddIndexList = self.GetMandatoryIndexes()
            if NMT == "NodeGuarding":
                AddIndexList.extend([0x100C, 0x100D])
            elif NMT == "Heartbeat":
                AddIndexList.append(0x1017)
            for option in options:
                if option == "DS302":
                    # Charging DS-302 profile if choosen by user
                    if os.path.isfile("config/DS-302.prf"):
                        try:
                            Mapping = {}
                            AddMenuEntries = []
                            execfile("config/DS-302.prf")
                            self.CurrentNode.SetDS302Profile(Mapping)
                            self.CurrentNode.ExtendSpecificMenu(AddMenuEntries)
                        except:
                            return "Problem with DS-302! Syntax Error."
                    else:
                        return "Couldn't find DS-302 in 'config' folder!"
                elif option == "GenSYNC":
                    AddIndexList.extend([0x1005, 0x1006])
                elif option == "Emergency":
                    AddIndexList.append(0x1014)
                elif option == "SaveConfig":
                    AddIndexList.extend([0x1010, 0x1011, 0x1020])
                elif option == "StoreEDS":
                    AddIndexList.extend([0x1021, 0x1022])
            # Add a new buffer 
            self.AddNodeBuffer()
            self.SetCurrentFilePath("")
            # Add Mandatory indexes
            self.ManageEntriesOfCurrent(AddIndexList, [])
            # Regenerate lists
            self.GenerateTypeList()
            self.GenerateMapList()
            return True
        else:
            return result
    
    """
    Load a profile in node
    """
    def LoadProfile(self, profile, filepath, node):
        if profile != "None":
            # Try to charge the profile given
            try:
                execfile(filepath)
                node.SetProfileName(profile)
                node.SetProfile(Mapping)
                node.SetSpecificMenu(AddMenuEntries)
                return True
            except:
                return "Bad OD Profile file!\nSyntax Error."
        else:
            # Default profile
            node.SetProfileName("None")
            node.SetProfile({})
            node.SetSpecificMenu([])
            return True

    """
    Open a file and store it in a new buffer
    """
    def OpenFileInCurrent(self, filepath):
        # Open and load file
        file = open(filepath, "r")
        node = load(file)
        file.close()
        self.CurrentNode = node
        # Add a new buffer and defining current state
        self.AddNodeBuffer(self.CurrentNode.Copy(), True)
        self.SetCurrentFilePath(filepath)
        # Regenerate lists
        self.GenerateTypeList()
        self.GenerateMapList()
        return True

    """
    Save current node in  a file
    """
    def SaveCurrentInFile(self, filepath = None):
        # if no filepath given, verify if current node has a filepath defined
        if not filepath:
            filepath = self.GetCurrentFilePath()
            if filepath == "":
                return False
        # Save node in file
        file = open(filepath, "w")
        dump(self.CurrentNode, file)
        file.close()
        self.SetCurrentFilePath(filepath)
        # Update saved state in buffer
        self.UndoBuffers[self.NodeIndex].CurrentSaved()
        return True

    """
    Close current state
    """
    def CloseCurrent(self, ignore = False):
        # Verify if it's not forced that the current node is saved before closing it
        if self.UndoBuffers[self.NodeIndex].IsCurrentSaved() or ignore:
            self.RemoveNodeBuffer(self.NodeIndex)
            return True
        return False

    """
    Import a xml file and store it in a new buffer if no node edited
    """
    def ImportCurrentFromFile(self, filepath):
        # Generate node from definition in a xml file
        node = xml_in.GenerateNode(filepath, self)
        if node:
            self.CurrentNode = node
            self.GenerateTypeList()
            self.GenerateMapList()
            if len(self.UndoBuffers) == 0:
                self.AddNodeBuffer()
                self.SetCurrentFilePath("")
            self.BufferCurrentNode()
        return result
    
    """
    Build the C definition of Object Dictionary for current node 
    """
    def ExportCurrentToFile(self, filepath):
        return gen_cfile.GenerateFile(filepath, self)

#-------------------------------------------------------------------------------
#                        Add Entries to Current Functions
#-------------------------------------------------------------------------------

    """
    Add the specified number of subentry for the given entry. Verify that total
    number of subentry (except 0) doesn't exceed nbmax defined
    """
    def AddSubentriesToCurrent(self, index, number):
        # Informations about entry
        length = self.CurrentNode.GetEntry(index, 0)
        infos = self.GetEntryInfos(index)
        subentry_infos = self.GetSubentryInfos(index, 1)
        # Get default value for subindex
        if "default" in subentry_infos:
            default = subentry_infos["default"]
        else:
            default = self.GetTypeDefaultValue(subentry_infos["type"])   
        # First case entry is record
        if infos["struct"] & OD_IdenticalSubindexes:
            for i in xrange(1, min(number,subentry_infos["nbmax"]-length) + 1):
                self.CurrentNode.AddEntry(index, length + i, default)
            self.BufferCurrentNode()
        # Second case entry is array, only possible for manufacturer specific
        elif infos["struct"] & OD_MultipleSubindexes and 0x2000 <= index <= 0x5FFF:
            values = {"name" : "Undefined", "type" : 5, "access" : "rw", "pdo" : True}
            for i in xrange(1, min(number,0xFE-length) + 1):
                self.CurrentNode.AddMappingEntry(index, length + i, values = values.copy())
                self.CurrentNode.AddEntry(index, length + i, 0)
            self.BufferCurrentNode()

    """
    Remove the specified number of subentry for the given entry. Verify that total
    number of subentry (except 0) isn't less than 1
    """
    def RemoveSubentriesFromCurrent(self, index, number):
        # Informations about entry
        infos = self.GetEntryInfos(index)
        length = self.CurrentNode.GetEntry(index, 0)
        # Entry is a record, or is an array of manufacturer specific
        if infos["struct"] & OD_IdenticalSubindexes or 0x2000 <= index <= 0x5FFF and infos["struct"] & OD_IdenticalSubindexes:
            for i in xrange(min(number, length - 1)):
                self.RemoveCurrentVariable(index, length - i)
            self.BufferCurrentNode()

    """
    Add a SDO Server to current node
    """
    def AddSDOServerToCurrent(self):
        # An SDO Server is already defined at index 0x1200
        if self.CurrentNode.IsEntry(0x1200):
            indexlist = [self.GetLineFromIndex(0x1201)]
            if None not in indexlist:
                self.ManageEntriesOfCurrent(indexlist, [])
        # Add an SDO Server at index 0x1200
        else:
            self.ManageEntriesOfCurrent([0x1200], [])
        
    """
    Add a SDO Server to current node
    """
    def AddSDOClientToCurrent(self):
        indexlist = [self.GetLineFromIndex(0x1280)]
        if None not in indexlist:
            self.ManageEntriesOfCurrent(indexlist, [])

    """
    Add a Transmit PDO to current node
    """
    def AddPDOTransmitToCurrent(self):
        indexlist = [self.GetLineFromIndex(0x1800),self.GetLineFromIndex(0x1A00)]
        if None not in indexlist:
            self.ManageEntriesOfCurrent(indexlist, [])
        
    """
    Add a Receive PDO to current node
    """
    def AddPDOReceiveToCurrent(self):
        indexlist = [self.GetLineFromIndex(0x1400),self.GetLineFromIndex(0x1600)]
        if None not in indexlist:
            self.ManageEntriesOfCurrent(indexlist, [])

    """
    Add a list of entries defined in profile for menu item selected to current node
    """
    def AddSpecificEntryToCurrent(self, menuitem):
        indexlist = []
        for menu, indexes in self.CurrentNode.GetSpecificMenu():
            if menuitem == menu:
                for index in indexes:
                    indexlist.append(self.GetLineFromIndex(index))
        if None not in indexlist:
            self.ManageEntriesOfCurrent(indexlist, [])

    """
    Search the first index available for a pluri entry from base_index
    """
    def GetLineFromIndex(self, base_index):
        found = False
        index = base_index
        infos = self.GetEntryInfos(base_index)
        while index < base_index + infos["incr"]*infos["nbmax"] and not found:
            if not self.CurrentNode.IsEntry(index):
                found = True
            else:
                index += infos["incr"]
        if found:
            return index
        return None
    
    """
    Add entries specified in addinglist and remove entries specified in removinglist
    """
    def ManageEntriesOfCurrent(self, addinglist, removinglist):
        # Add all the entries in addinglist
        for index in addinglist:
            infos = self.GetEntryInfos(index)
            if infos["struct"] & OD_MultipleSubindexes:
                # First case entry is a record
                if infos["struct"] & OD_IdenticalSubindexes:
                    subentry_infos = self.GetSubentryInfos(index, 1)
                    if "default" in subentry_infos:
                        default = subentry_infos["default"]
                    else:
                        default = self.GetTypeDefaultValue(subentry_infos["type"])
                    self.CurrentNode.AddEntry(index, 1, default)
                # Second case entry is a record
                else:
                    i = 1
                    subentry_infos = self.GetSubentryInfos(index, i)
                    while subentry_infos:
                        if "default" in subentry_infos:
                            default = subentry_infos["default"]
                        else:
                            default = self.GetTypeDefaultValue(subentry_infos["type"])
                        self.CurrentNode.AddEntry(index, i, default)
                        i += 1
                        subentry_infos = self.GetSubentryInfos(index, i)
            # Third case entry is a record
            else:
                subentry_infos = self.GetSubentryInfos(index, 0)
                if "default" in subentry_infos:
                    default = subentry_infos["default"]
                else:
                    default = self.GetTypeDefaultValue(subentry_infos["type"])
                self.CurrentNode.AddEntry(index, 0, default)
        # Remove all the entries in removinglist
        for index in removinglist:
            self.RemoveCurrentVariable(index)
        self.BufferCurrentNode()

    """
    Remove an entry from current node. Analize the index to perform the correct
    method
    """
    def RemoveCurrentVariable(self, index, subIndex = None):
        Mappings = self.CurrentNode.GetMappings()
        if index < 0x1000 and subIndex == None:
            type = self.CurrentNode.GetEntry(index, 1)
            for i in Mappings[-1]:
                for value in Mappings[-1][i]["values"]:
                    if value["type"] == index:
                        value["type"] = type
            self.CurrentNode.RemoveMappingEntry(index)
            self.CurrentNode.RemoveEntry(index)
        elif index == 0x1200 and subIndex == None:
            self.CurrentNode.RemoveEntry(0x1200)
        elif 0x1201 <= index <= 0x127F and subIndex == None:
            self.CurrentNode.RemoveLine(index, 0x127F)
        elif 0x1280 <= index <= 0x12FF and subIndex == None:
            self.CurrentNode.RemoveLine(index, 0x12FF)
        elif 0x1400 <= index <= 0x15FF or 0x1600 <= index <= 0x17FF and subIndex == None:
            if 0x1600 <= index <= 0x17FF and subIndex == None:
                index -= 0x200
            self.CurrentNode.RemoveLine(index, 0x15FF)
            self.CurrentNode.RemoveLine(index + 0x200, 0x17FF)
        elif 0x1800 <= index <= 0x19FF or 0x1A00 <= index <= 0x1BFF and subIndex == None:
            if 0x1A00 <= index <= 0x1BFF:
                index -= 0x200
            self.CurrentNode.RemoveLine(index, 0x19FF)
            self.CurrentNode.RemoveLine(index + 0x200, 0x1BFF)
        else:
            found = False
            for menu,list in self.CurrentNode.GetSpecificMenu():
                for i in list:
                    iinfos = self.GetEntryInfos(i)
                    indexes = [i + incr * iinfos["incr"] for incr in xrange(iinfos["nbmax"])] 
                    if index in indexes:
                        found = True
                        diff = index - i
                        for j in list:
                            jinfos = self.GetEntryInfos(j)
                            self.CurrentNode.RemoveLine(j + diff, j + jinfos["incr"]*jinfos["nbmax"], jinfos["incr"])
            self.CurrentNode.RemoveMapVariable(index, subIndex)
            if not found:
                infos = self.GetEntryInfos(index)
                if not infos["need"]:
                    self.CurrentNode.RemoveEntry(index, subIndex)
            if index in Mappings[-1]:
                self.CurrentNode.RemoveMappingEntry(index, subIndex)
            self.GenerateMapList()

    def AddMapVariableToCurrent(self, index, name, struct, number):
        if 0x2000 <= index <= 0x5FFF:
            if not self.CurrentNode.IsEntry(index):
                self.CurrentNode.AddMappingEntry(index, name = name, struct = struct)
                if struct == var:
                    values = {"name" : name, "type" : 5, "access" : "rw", "pdo" : True}
                    self.CurrentNode.AddMappingEntry(index, 0, values = values)
                    self.CurrentNode.AddEntry(index, 0, 0)
                else:
                    values = {"name" : "Number of Entries", "type" : 2, "access" : "ro", "pdo" : False}
                    self.CurrentNode.AddMappingEntry(index, 0, values = values)
                    if struct == rec:
                        values = {"name" : name + " %d[(sub)]", "type" : 5, "access" : "rw", "pdo" : True, "nbmax" : 0xFE}
                        self.CurrentNode.AddMappingEntry(index, 1, values = values)
                        for i in xrange(number):
                            self.CurrentNode.AddEntry(index, i + 1, 0)
                    else:
                        for i in xrange(number):
                            values = {"name" : "Undefined", "type" : 5, "access" : "rw", "pdo" : True}
                            self.CurrentNode.AddMappingEntry(index, i + 1, values = values)
                            self.CurrentNode.AddEntry(index, i + 1, 0)
                self.GenerateMapList()
                self.BufferCurrentNode()
                return None
            else:
                return "Index 0x%04X already defined!"%index
        else:
            return "Index 0x%04X isn't a valid index for Map Variable!"%index

    def AddUserTypeToCurrent(self, type, min, max, length):
        index = 0xA0
        while index < 0x100 and self.CurrentNode.IsEntry(index):
            index += 1
        if index < 0x100:
            customisabletypes = self.GetCustomisableTypes()
            name, valuetype = customisabletypes[type]
            size = self.GetEntryInfos(type)["size"]
            default = self.GetTypeDefaultValue(type)
            if valuetype == 0:
                self.CurrentNode.AddMappingEntry(index, name = "%s[%d-%d]"%(name, min, max), struct = 3, size = size, default = default)
                self.CurrentNode.AddMappingEntry(index, 0, values = {"name" : "Number of Entries", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 1, values = {"name" : "Type", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 2, values = {"name" : "Minimum Value", "type" : type, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 3, values = {"name" : "Maximum Value", "type" : type, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddEntry(index, 1, type)
                self.CurrentNode.AddEntry(index, 2, min)
                self.CurrentNode.AddEntry(index, 3, max)
            elif valuetype == 1:
                self.CurrentNode.AddMappingEntry(index, name = "%s%d"%(name, length), struct = 3, size = length * size, default = default)
                self.CurrentNode.AddMappingEntry(index, 0, values = {"name" : "Number of Entries", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 1, values = {"name" : "Type", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 2, values = {"name" : "Length", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddEntry(index, 1, type)
                self.CurrentNode.AddEntry(index, 2, length)
            self.GenerateTypeList()
            self.BufferCurrentNode()
            return None
        else:
            return "Too many User Types have already been defined!"

#-------------------------------------------------------------------------------
#                      Modify Entry and Mapping Functions
#-------------------------------------------------------------------------------

    def SetCurrentEntryCallbacks(self, index, value):
        if self.CurrentNode and self.CurrentNode.IsEntry(index):
            entry_infos = self.GetEntryInfos(index)
            if "callback" not in entry_infos:
                self.CurrentNode.SetParamsEntry(index, None, callback = value)
                self.BufferCurrentNode()

    def SetCurrentEntry(self, index, subIndex, value, name, editor):
        if self.CurrentNode and self.CurrentNode.IsEntry(index):
            if name == "value":
                if editor == "map":
                    value = eval("0x%s"%self.NameTranslation[value])
                    self.CurrentNode.SetEntry(index, subIndex, value)
                elif editor == "bool":
                    value = value == "True"
                    self.CurrentNode.SetEntry(index, subIndex, value)
                elif editor == "time":
                    self.CurrentNode.SetEntry(index, subIndex, value)
                else:
                    subentry_infos = self.GetSubentryInfos(index, subIndex)
                    type = subentry_infos["type"]
                    dic = {}
                    for typeindex, typevalue in CustomisableTypes:
                        dic[typeindex] = typevalue
                    if type not in dic:
                        type = self.CurrentNode.GetEntry(type)[1]
                    if dic[type] == 0:
                        try:
                            value = eval(value, {})
                            self.CurrentNode.SetEntry(index, subIndex, value)
                        except:
                            pass
                    else:
                        self.CurrentNode.SetEntry(index, subIndex, value)
            elif name in ["comment", "save"]:
                if editor == "option":
                    value = value == "Yes"
                if name == "save":
                    self.CurrentNode.SetParamsEntry(index, subIndex, save = value)
                elif name == "comment":
                    self.CurrentNode.SetParamsEntry(index, subIndex, comment = value)
            else:
                if editor == "type":
                    value = self.TypeTranslation[value]
                    size = self.GetEntryInfos(value)["size"]
                    self.CurrentNode.UpdateMapVariable(index, subIndex, size)
                elif editor in ["access","raccess"]:
                    dic = {}
                    for abbrev,access in AccessType.iteritems():
                        dic[access] = abbrev
                    value = dic[value]
                    if editor == "raccess" and not self.CurrentNode.IsMappingEntry(index):
                        entry_infos = self.GetEntryInfos(index)
                        self.CurrentNode.AddMappingEntry(index, name = entry_infos["name"], struct = 7)
                        self.CurrentNode.AddMappingEntry(index, 0, values = self.GetSubentryInfos(index, 0, False).copy())
                        self.CurrentNode.AddMappingEntry(index, 1, values = self.GetSubentryInfos(index, 1, False).copy())
                self.CurrentNode.SetMappingEntry(index, subIndex, values = {name : value})
                if name == "name" or editor == "type":
                    self.GenerateMapList()
            self.BufferCurrentNode()

    def SetCurrentEntryName(self, index, name):
        self.CurrentNode.SetMappingEntry(index, name=name)
        self.BufferCurrentNode()

    def SetCurrentUserType(self, index, type, min, max, length):
        customisabletypes = self.GetCustomisableTypes()
        values, valuetype = self.GetCustomisedTypeValues(index)
        name, new_valuetype = customisabletypes[type]
        size = self.GetEntryInfos(type)["size"]
        default = self.GetTypeDefaultValue(type)
        if new_valuetype == 0:
            self.CurrentNode.SetMappingEntry(index, name = "%s[%d-%d]"%(name, min, max), struct = 3, size = size, default = default) 
            if valuetype == 1:
                self.CurrentNode.SetMappingEntry(index, 2, values = {"name" : "Minimum Value", "type" : type, "access" : "ro", "pdo" : False})
                self.CurrentNode.AddMappingEntry(index, 3, values = {"name" : "Maximum Value", "type" : type, "access" : "ro", "pdo" : False})
            self.CurrentNode.SetEntry(index, 1, type)
            self.CurrentNode.SetEntry(index, 2, min)
            if valuetype == 1:
                self.CurrentNode.AddEntry(index, 3, max)
            else:
                self.CurrentNode.SetEntry(index, 3, max)
        elif new_valuetype == 1:
            self.CurrentNode.SetMappingEntry(index, name = "%s%d"%(name, length), struct = 3, size = size, default = default)
            if valuetype == 0:
                self.CurrentNode.SetMappingEntry(index, 2, values = {"name" : "Length", "type" : 0x02, "access" : "ro", "pdo" : False})
                self.CurrentNode.RemoveMappingEntry(index, 3)
            self.CurrentNode.SetEntry(index, 1, type)
            self.CurrentNode.SetEntry(index, 2, length)
            if valuetype == 0:
                self.CurrentNode.RemoveEntry(index, 3)
        self.BufferCurrentNode()

#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    def BufferCurrentNode(self):
        self.UndoBuffers[self.NodeIndex].Buffering(self.CurrentNode.Copy())

    def CurrentIsSaved(self):
        return self.UndoBuffers[self.NodeIndex].IsCurrentSaved()

    def OneFileHasChanged(self):
        result = False
        for buffer in self.UndoBuffers:
            result |= not buffer.IsCurrentSaved()
        return result

    def GetBufferNumber(self):
        return len(self.UndoBuffers)

    def LoadCurrentPrevious(self):
        self.CurrentNode = self.UndoBuffers[self.NodeIndex].Previous().Copy()
    
    def LoadCurrentNext(self):
        self.CurrentNode = self.UndoBuffers[self.NodeIndex].Next().Copy()

    def AddNodeBuffer(self, currentstate = None, issaved = False):
        self.NodeIndex = len(self.UndoBuffers)
        self.UndoBuffers.append(UndoBuffer(currentstate, issaved))
        self.FilePaths.append("")
        self.FileNames.append("")

    def ChangeCurrentNode(self, index):
        if index < len(self.UndoBuffers):
            self.NodeIndex = index
            self.CurrentNode = self.UndoBuffers[self.NodeIndex].Current().Copy()
            self.GenerateTypeList()
            self.GenerateMapList()
    
    def RemoveNodeBuffer(self, index):
        self.UndoBuffers.pop(index)
        self.FilePaths.pop(index)
        self.FileNames.pop(index)
        self.NodeIndex = min(self.NodeIndex, len(self.UndoBuffers) - 1)
        if len(self.UndoBuffers) > 0:
            self.CurrentNode = self.UndoBuffers[self.NodeIndex].Current().Copy()
            self.GenerateTypeList()
            self.GenerateMapList()
        else:
            self.CurrentNode = None
    
    def GetCurrentNodeIndex(self):
        return self.NodeIndex
    
    def GetCurrentFilename(self):
        return self.GetFilename(self.NodeIndex)
    
    def GetAllFilenames(self):
        filenames = []
        for i in xrange(len(self.UndoBuffers)):
            filenames.append(self.GetFilename(i))
        return filenames
    
    def GetFilename(self, index):
        if self.UndoBuffers[index].IsCurrentSaved():
            return self.FileNames[index]
        else:
            return "~%s~"%self.FileNames[index]
    
    def SetCurrentFilePath(self, filepath):
        self.FilePaths[self.NodeIndex] = filepath
        if filepath == "":
            self.LastNewIndex += 1
            self.FileNames[self.NodeIndex] = "Unnamed%d"%self.LastNewIndex
        else:
            self.FileNames[self.NodeIndex] = os.path.splitext(os.path.basename(filepath))[0]
                
    def GetCurrentFilePath(self):
        if len(self.FilePaths) > 0:
            return self.FilePaths[self.NodeIndex]
        else:
            return ""
    
    def GetCurrentBufferState(self):
        first = self.UndoBuffers[self.NodeIndex].IsFirst()
        last = self.UndoBuffers[self.NodeIndex].IsLast()
        return not first, not last

#-------------------------------------------------------------------------------
#                         Profiles Management Functions
#-------------------------------------------------------------------------------

    def GetCurrentCommunicationLists(self):
        list = []
        for index in MappingDictionary.iterkeys():
            if 0x1000 <= index < 0x1200:
                list.append(index)
        return self.GetProfileLists(MappingDictionary, list)
    
    def GetCurrentDS302Lists(self):
        return self.GetSpecificProfileLists(self.CurrentNode.GetDS302Profile())
    
    def GetCurrentProfileLists(self):
        return self.GetSpecificProfileLists(self.CurrentNode.GetProfile())
    
    def GetSpecificProfileLists(self, mappingdictionary):
        validlist = []
        exclusionlist = []
        for name, list in self.CurrentNode.GetSpecificMenu():
            exclusionlist.extend(list)
        for index in mappingdictionary.iterkeys():
            if index not in exclusionlist:
                validlist.append(index)
        return self.GetProfileLists(mappingdictionary, validlist)
    
    def GetProfileLists(self, mappingdictionary, list):
        dictionary = {}
        current = []
        for index in list:
            dictionary[index] = (mappingdictionary[index]["name"], mappingdictionary[index]["need"])
            if self.CurrentNode.IsEntry(index):
                current.append(index)
        return dictionary, current

    def GetCurrentNextMapIndex(self):
        if self.CurrentNode:
            index = 0x2000
            while self.CurrentNode.IsEntry(index) and index < 0x5FFF:
                index += 1
            if index < 0x6000:
                return index
            else:
                return None

    def CurrentDS302Defined(self):
        if self.CurrentNode:
            return len(self.CurrentNode.GetDS302Profile()) > 0
        return False

#-------------------------------------------------------------------------------
#                         Node State and Values Functions
#-------------------------------------------------------------------------------

    def GetCurrentNodeInfos(self):
        name = self.CurrentNode.GetNodeName()
        id = self.CurrentNode.GetNodeID()
        type = self.CurrentNode.GetNodeType()
        return name, id, type
        
    def SetCurrentNodeInfos(self, name, id, type):
        self.CurrentNode.SetNodeName(name)
        self.CurrentNode.SetNodeID(id)
        self.CurrentNode.SetNodeType(type)
        self.BufferCurrentNode()

    def GetCurrentProfileName(self):
        if self.CurrentNode:
            return self.CurrentNode.GetProfileName()
        return ""

    def IsCurrentEntry(self, index):
        if self.CurrentNode:
            return self.CurrentNode.IsEntry(index)
        return False
    
    def GetCurrentEntry(self, index, subIndex = None):
        if self.CurrentNode:
            return self.CurrentNode.GetEntry(index, subIndex)
        return None
    
    def GetCurrentParamsEntry(self, index, subIndex = None):
        if self.CurrentNode:
            return self.CurrentNode.GetParamsEntry(index, subIndex)
        return None
    
    def GetCurrentValidIndexes(self, min, max):
        validindexes = []
        for index in self.CurrentNode.GetIndexes():
            if min <= index <= max:
                validindexes.append((self.GetEntryName(index), index))
        return validindexes
        
    def GetCurrentValidChoices(self, min, max):
        validchoices = []
        exclusionlist = []
        for menu, indexes in self.CurrentNode.GetSpecificMenu():
            exclusionlist.extend(indexes)
            good = True
            for index in indexes:
                good &= min <= index <= max
            if good:
                validchoices.append((menu, None))
        list = [index for index in MappingDictionary.keys() if index >= 0x1000]
        profiles = self.CurrentNode.GetMappings(False)
        for profile in profiles:
            list.extend(profile.keys())
        list.sort()
        for index in list:
            if min <= index <= max and not self.CurrentNode.IsEntry(index) and index not in exclusionlist:
                validchoices.append((self.GetEntryName(index), index))
        return validchoices
    
    def HasCurrentEntryCallbacks(self, index):
        if self.CurrentNode and self.CurrentNode.IsEntry(index):
            entry_infos = self.GetEntryInfos(index)
            if "callback" in entry_infos:
                return entry_infos["callback"]
            return self.CurrentNode.HasEntryCallbacks(index)
        return False
    
    def GetCurrentEntryValues(self, index):
        if self.CurrentNode and self.CurrentNode.IsEntry(index):
            entry_infos = self.GetEntryInfos(index)
            data = []
            editors = []
            values = self.CurrentNode.GetEntry(index)
            params = self.CurrentNode.GetParamsEntry(index)
            if type(values) == ListType:
                for i, value in enumerate(values):
                    data.append({"value" : value})
                    data[-1].update(params[i])
            else:
                data.append({"value" : values})
                data[-1].update(params)
            for i, dic in enumerate(data):
                infos = self.GetSubentryInfos(index, i)
                dic["subindex"] = "0x%02X"%i
                dic["name"] = infos["name"]
                dic["type"] = self.GetTypeName(infos["type"])
                dic["access"] = AccessType[infos["access"]]
                dic["save"] = OptionType[dic["save"]]
                editor = {"subindex" : None, "save" : "option", "callback" : "option", "comment" : "string"}
                if type(values) == ListType and i == 0:
                    editor["name"] = None
                    editor["type"] = None
                    if 0x1600 <= index <= 0x17FF or 0x1A00 <= index <= 0x1C00:
                        editor["access"] = "raccess"
                    else:
                        editor["access"] = None
                    editor["value"] = None
                else:
                    if infos["user_defined"]:
                        if entry_infos["struct"] & OD_IdenticalSubindexes:
                            editor["name"] = None
                            if i > 1:
                                editor["type"] = None
                                editor["access"] = None
                            else:
                                editor["type"] = "type"
                                editor["access"] = "access"
                        else:
                            if entry_infos["struct"] & OD_MultipleSubindexes:
                                editor["name"] = "string"
                            else:
                                editor["name"] = None
                            editor["type"] = "type"
                            editor["access"] = "access"
                    else:
                        editor["name"] = None
                        editor["type"] = None
                        editor["access"] = None
                    if index < 0x260:
                        editor["value"] = None
                        if i == 1:
                            dic["value"] = self.GetTypeName(dic["value"])
                    elif 0x1600 <= index <= 0x17FF or 0x1A00 <= index <= 0x1C00:
                        editor["value"] = "map"
                        dic["value"] = self.MapTranslation["%08X"%dic["value"]]
                    else:
                        if dic["type"].startswith("VISIBLE_STRING"):
                            editor["value"] = "string"
                        if dic["type"] in ["TIME_OF_DAY","TIME_DIFFERENCE"]:
                            editor["value"] = "time"
                        elif dic["type"] == "BOOLEAN":
                            editor["value"] = "bool"
                            dic["value"] = BoolType[dic["value"]]
                        result = type_model.match(dic["type"])
                        if result:
                            values = result.groups()
                            if values[0] in ["INTEGER", "UNSIGNED"]:
                                format = "0x%0" + str(int(values[1])/4) + "X"
                                dic["value"] = format%dic["value"]
                                editor["value"] = "string"
                            elif values[0] == "REAL":
                                editor["value"] = "float"
                            elif values[0] == "VISIBLE_STRING":
                                editor["length"] = values[0]
                        result = range_model.match(dic["type"])
                        if result:
                            values = result.groups()
                            if values[0] in ("UNSIGNED", "REAL"):
                                editor["min"] = values[2]
                                editor["max"] = values[3]
                editors.append(editor)
            return data, editors
        else:
            return None
    
#-------------------------------------------------------------------------------
#                         Node Informations Functions
#-------------------------------------------------------------------------------

    def GetCustomisedTypeValues(self, index):
        values = self.CurrentNode.GetEntry(index)
        customisabletypes = self.GetCustomisableTypes()
        return values, customisabletypes[values[1]][1]

    def GetEntryName(self, index, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindEntryName(index, NodeMappings[i])
                i += 1
        if result == None:
            result = FindEntryName(index, MappingDictionary)
        return result
    
    def GetEntryInfos(self, index, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindEntryInfos(index, NodeMappings[i])
                i += 1
        if result == None:
            result = FindEntryInfos(index, MappingDictionary)
        return result
    
    def GetSubentryInfos(self, index, subIndex, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindSubentryInfos(index, subIndex, NodeMappings[i])
                if result:
                    result["user_defined"] = i == len(NodeMappings) - 1 and index >= 0x1000
                i += 1
        if result == None:    
            result = FindSubentryInfos(index, subIndex, MappingDictionary)
            if result:
                result["user_defined"] = False
        return result
    
    def GetTypeIndex(self, typename, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindTypeIndex(typename, NodeMappings[i])
                i += 1
        if result == None:
            result = FindTypeIndex(typename, MappingDictionary)
        return result
    
    def GetTypeName(self, typeindex, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindTypeName(typeindex, NodeMappings[i])
                i += 1
        if result == None:
            result = FindTypeName(typeindex, MappingDictionary)
        return result
    
    def GetTypeDefaultValue(self, typeindex, node = True):
        result = None
        if node:
            NodeMappings = self.CurrentNode.GetMappings()
            i = 0
            while not result and i < len(NodeMappings):
                result = FindTypeDefaultValue(typeindex, NodeMappings[i])
                i += 1
        if result == None:
            result = FindTypeDefaultValue(typeindex, MappingDictionary)
        return result
    
    def GetTypeList(self, node = True):
        list = FindTypeList(MappingDictionary)
        if node:
            for NodeMapping in self.CurrentNode.GetMappings():
                list.extend(FindTypeList(NodeMapping))
        list.sort()
        return list
    
    def GetMapVariableList(self):
        list = FindMapVariableList(MappingDictionary, self)
        for NodeMapping in self.CurrentNode.GetMappings():
            list.extend(FindMapVariableList(NodeMapping, self))
        list.sort()
        return list
    
    def GetMandatoryIndexes(self, node = True):
        list = FindMandatoryIndexes(MappingDictionary)
        if node:
            for NodeMapping in self.CurrentNode.GetMappings():
                list.extend(FindMandatoryIndexes(NodeMapping))
        return list
    
    def GetCustomisableTypes(self):
        dic = {}
        for index, valuetype in CustomisableTypes:
            name = self.GetTypeName(index)
            dic[index] = [name, valuetype]
        return dic
    
    def GetCurrentSpecificMenu(self):
        if self.CurrentNode:
            return self.CurrentNode.GetSpecificMenu()
        return []

    