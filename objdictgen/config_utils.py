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

from types import *

DicoTypes = {"BOOL":0x01, "SINT":0x02, "INT":0x03,"DINT":0x04,"LINT":0x10,
             "USINT":0x05,"UINT":0x06,"UDINT":0x07,"ULINT":0x1B,"REAL":0x08,
             "LREAL":0x11,"STRING":0x09,"BYTE":0x02,"WORD":0x03,"DWORD":0x04,
             "LWORD":0x1B,"WSTRING":0x0B}

DictLocations = {}
DictCobID = {}
DictLocationsNotMapped = {}
ListCobIDAvailable = []
SlavesPdoNumber = {}

# Constants for PDO types 
RPDO = 1
TPDO = 2
SlavePDOType = {"I" : TPDO, "Q" : RPDO}
InvertPDOType = {RPDO : TPDO, TPDO : RPDO}

DefaultTransmitType = 0x01

GenerateMasterMapping = lambda x:[None] + [(loc_infos["type"], name) for name, loc_infos in x]

TrashVariableSizes = {1 : 0x01, 8 : 0x05, 16 : 0x06, 32 : 0x07, 64 : 0x1B}


def GetSlavePDOIndexes(slave, type, parameters = False):
    indexes = []
    if type & RPDO:
        indexes.extend([idx for idx in slave.GetIndexes() if 0x1400 <= idx <= 0x15FF])
    if type & TPDO:
        indexes.extend([idx for idx in slave.GetIndexes() if 0x1800 <= idx <= 0x19FF])
    if not parameters:
        return [idx + 0x200 for idx in indexes]
    else:
        return indexes


def LE_to_BE(value, size): # Convert Little Endian to Big Endian
    data = ("%" + str(size * 2) + "." + str(size * 2) + "X") % value
    list_car = [data[i:i+2] for i in xrange(0, len(data), 2)]
    list_car.reverse()
    return "".join([chr(int(car, 16)) for car in list_car])



def SearchSlavePDOMapping(loc_infos, slave): # Search the TPDO or RPDO mapping where location is defined on the slave
    typeinfos = slave.GetEntryInfos(loc_infos["type"])
    model = (loc_infos["index"] << 16) + (loc_infos["subindex"] << 8) + typeinfos["size"]
    slavePDOidxlist = GetSlavePDOIndexes(slave, loc_infos["pdotype"])
    
    for PDOidx in slavePDOidxlist:
        values = slave.GetEntry(PDOidx)
        
        for subindex, mapping in enumerate(values):
            if subindex != 0 and mapping == model:
                return PDOidx, subindex
    return None

def GenerateMappingDCF(cobid, idx, pdomapping, mapped): # Build concise DCF
    
    # Create entry for RPDO or TPDO parameters and Disable PDO
    dcfdata = LE_to_BE(idx, 2) + LE_to_BE(0x01, 1) + LE_to_BE(0x04, 4) + LE_to_BE((0x80000000 + cobid), 4)
    
    # Set Transmit type synchrone
    dcfdata += LE_to_BE(idx, 2) + LE_to_BE(0x02, 1) + LE_to_BE(0x01, 4) + LE_to_BE(DefaultTransmitType, 1)
    
    # Re-Enable PDO
    #         ---- INDEX -----   --- SUBINDEX ----   ----- SIZE ------   ------ DATA ------
    dcfdata += LE_to_BE(idx, 2) + LE_to_BE(0x01, 1) + LE_to_BE(0x04, 4) + LE_to_BE(0x00000000 + cobid, 4)
    
    nbparams = 3
    if mapped == False and pdomapping != None:
    # Map Variables
        for subindex, (name, loc_infos) in enumerate(pdomapping):
            value = (loc_infos["index"] << 16) + (loc_infos["subindex"] << 8) + loc_infos["size"]
            dcfdata += LE_to_BE(idx + 0x200, 2) + LE_to_BE(subindex + 1, 1) + LE_to_BE(loc_infos["size"] >> 3, 4) + LE_to_BE(value, loc_infos["size"] >> 3)
            nbparams += 1
    return dcfdata, nbparams



def GetNewCobID(nodeid, type): # Return a cobid not used
    global ListCobIDAvailable, SlavesPdoNumber
    
    if len(ListCobIDAvailable) == 0:
        return None
    
    nbSlavePDO = SlavesPdoNumber[nodeid][type]
    if type == RPDO:
        if nbSlavePDO < 4:
            # For the fourth PDO -> cobid = 0x200 + ( numPdo parameters * 0x100) + nodeid
            newcobid = (0x200 + nbSlavePDO * 0x100 + nodeid)
            if newcobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(newcobid)
                return newcobid, 0x1400 + nbSlavePDO
        return ListCobIDAvailable.pop(0), 0x1400 + nbSlavePDO

    elif type == TPDO:
        if nbSlavePDO < 4:
            # For the fourth PDO -> cobid = 0x180 + (numPdo parameters * 0x100) + nodeid
            newcobid = (0x180 + nbSlavePDO * 0x100 + nodeid)
            if newcobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(newcobid)
                return newcobid, 0x1800 + nbSlavePDO
        return ListCobIDAvailable.pop(0), 0x1800 + nbSlavePDO
    
    for number in xrange(4):
        if type == RPDO:
            # For the fourth PDO -> cobid = 0x200 + ( numPdo * 0x100) + nodeid
            newcobid = (0x200 + number * 0x100 + nodeid)
        elif type == TPDO:
            # For the fourth PDO -> cobid = 0x180 + (numPdo * 0x100) + nodeid
            newcobid = (0x180 + number * 0x100 + nodeid)
        else:
            return None
        if newcobid in ListCobIDAvailable:
            ListCobIDAvailable.remove(newcobid)
            return newcobid
    return ListCobIDAvailable.pop(0)
        
        
def GenerateConciseDCF(locations, busname, nodelist):
    global DictLocations, DictCobID, DictLocationsNotMapped, ListCobIDAvailable, SlavesPdoNumber

    DictLocations = {}
    DictCobID = {}
    DictLocationsNotMapped = {}
    DictSDOparams = {}
    ListCobIDAvailable = range(0x180, 0x580)
    SlavesPdoNumber = {}
    DictNameVariable = { "" : 1, "X": 2, "B": 3, "W": 4, "D": 5, "L": 6, "increment": 0x100, 1:("__I", 0x2000), 2:("__Q", 0x4000)}
    
    # Master Node initialisation
    manager = nodelist.Manager
    manager.AddSubentriesToCurrent(0x1F22, 127)
    
    # Adding trash mappable variables for unused mapped datas
    idxTrashVariables = 0x2000 + manager.GetCurrentNodeID()
    TrashVariableValue = {}
    manager.AddMapVariableToCurrent(idxTrashVariables, "trashvariables", 3, len(TrashVariableSizes))
    for subidx, (size, typeidx) in enumerate(TrashVariableSizes.items()):
        manager.SetCurrentEntry(idxTrashVariables, subidx + 1, "TRASH%d" % size, "name", None)
        manager.SetCurrentEntry(idxTrashVariables, subidx + 1, typeidx, "type", None)
        TrashVariableValue[size] = (idxTrashVariables << 16) + ((subidx + 1) << 8) + size
    
    # Extract Master Node current empty mapping index
    masternode = manager.GetCurrentNode()
    CurrentPDOParamsIdx = {RPDO : 0x1400 + len(GetSlavePDOIndexes(masternode, RPDO)),
                           TPDO : 0x1800 + len(GetSlavePDOIndexes(masternode, TPDO))}

    
    # Get list of all Slave's CobID and Slave's default SDO server parameters
    for nodeid, nodeinfos in nodelist.SlaveNodes.items():
        node = nodeinfos["Node"]
        node.SetNodeID(nodeid)
        DictSDOparams[nodeid] = {"RSDO" : node.GetEntry(0x1200,0x01), "TSDO" : node.GetEntry(0x1200,0x02)}
        slaveRpdoIndexes = GetSlavePDOIndexes(node, RPDO, True)
        slaveTpdoIndexes = GetSlavePDOIndexes(node, TPDO, True)
        SlavesPdoNumber[nodeid] = {RPDO : len(slaveRpdoIndexes), TPDO : len(slaveTpdoIndexes)}
        for PdoIdx in slaveRpdoIndexes + slaveTpdoIndexes:
            pdo_cobid = node.GetEntry(PdoIdx, 0x01)
            if pdo_cobid > 0x600 :
                pdo_cobid -= 0x80000000
            if pdo_cobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(pdo_cobid)
    
    # Get list of locations check if exists and mappables -> put them in DictLocations
    for locationtype, name in locations:    
        if name in DictLocations.keys():
            if DictLocations[name]["type"] != DicoTypes[locationtype]:
                raise ValueError, "Conflict type for location \"%s\"" % name 
        else:
            loc = [i for i in name.split("_") if len(i) > 0]
            if len(loc) not in (4, 5):
                continue
            
            prefix = loc[0][0]
            
            # Extract and check busname
            if loc[0][1].isdigit():
                sizelocation = ""
                busnamelocation = int(loc[0][1:])
            else:
                sizelocation = loc[0][1]
                busnamelocation = int(loc[0][2:])
            if busnamelocation != busname:
                continue # A ne pas remplacer par un message d'erreur
            
            # Extract and check nodeid
            nodeid = int(loc[1])
            if nodeid not in nodelist.SlaveNodes.keys():
                continue
            node = nodelist.SlaveNodes[nodeid]["Node"]
            
            # Extract and check index and subindex
            index = int(loc[2])
            subindex = int(loc[3])
            if not node.IsEntry(index, subindex):
                continue
            subentry_infos = node.GetSubentryInfos(index, subindex)
            
            if subentry_infos and subentry_infos["pdo"]:
                if sizelocation == "X" and len(loc) > 4:
                    numbit = loc[4]
                elif sizelocation != "X" and len(loc) > 4:
                    continue
                else:
                    numbit = None
                
                locationtype = DicoTypes[locationtype]
                entryinfos = node.GetSubentryInfos(index, subindex)
                if entryinfos["type"] != locationtype:
                    raise ValueError, "Invalid type for location \"%s\"" % name
                
                typeinfos = node.GetEntryInfos(locationtype)
                DictLocations[name] = {"type":locationtype, "pdotype":SlavePDOType[prefix],
                                       "nodeid": nodeid, "index": index,"subindex": subindex, 
                                       "bit": numbit, "size": typeinfos["size"], "busname": busname, "sizelocation": sizelocation}
            
    # Create DictCobID with variables already mapped and add them in DictValidLocations
    for name, locationinfos in DictLocations.items():
        node = nodelist.SlaveNodes[locationinfos["nodeid"]]["Node"]
        result = SearchSlavePDOMapping(locationinfos, node)
        if result != None:
            index, subindex = result
            cobid = nodelist.GetSlaveNodeEntry(locationinfos["nodeid"], index - 0x200, 1)
            if cobid not in DictCobID.keys():
                DefaultNodeTransmitType = node.GetEntry(index - 0x200, 2)
                if not 1 <= DefaultNodeTransmitType <= 240:
                    result = GenerateMappingDCF(cobid, index - 0x200, None, True)
                    data, nbaddedparams = GenerateMappingDCF(cobid, index - 0x200, None, True)
                    nodeDCF = nodelist.GetMasterNodeEntry(0x1F22, locationinfos["nodeid"])
                    if nodeDCF != None and nodeDCF != '':
                        tmpnbparams = [i for i in nodeDCF[:4]]
                        tmpnbparams.reverse()
                        nbparams = int(''.join(["%2.2x"%ord(i) for i in tmpnbparams]), 16)
                        dataparams = nodeDCF[4:]
                    else:
                        nbparams = 0
                        dataparams = ""
                    dataparams += data
                    nbparams += nbaddedparams        
                    dcf = LE_to_BE(nbparams, 0x04) + dataparams
                    manager.SetCurrentEntry(0x1F22, locationinfos["nodeid"], dcf, "value", None)
                    
                mapping = [None]
                values = node.GetEntry(index)
                for value in values[1:]:
                    mapping.append(value % 0x100)
                DictCobID[cobid] = {"type" : InvertPDOType[locationinfos["pdotype"]], "mapping" : mapping}
        
            DictCobID[cobid]["mapping"][subindex] = (locationinfos["type"], name)
            
        else:
            if locationinfos["nodeid"] not in DictLocationsNotMapped.keys():
                DictLocationsNotMapped[locationinfos["nodeid"]] = {TPDO : [], RPDO : []}
            DictLocationsNotMapped[locationinfos["nodeid"]][locationinfos["pdotype"]].append((name, locationinfos))

    # Check Master Pdo parameters for cobid already used and remove it in ListCobIDAvailable
    ListPdoParams = [idx for idx in masternode.GetIndexes() if 0x1400 <= idx <= 0x15FF or  0x1800 <= idx <= 0x19FF]
    for idx in ListPdoParams:
        cobid = manager.GetCurrentEntry(idx, 0x01)
        if cobid not in DictCobID.keys():
            ListCobIDAvailable.pop(cobid)
    
    
    #-------------------------------------------------------------------------------
    #                         Build concise DCF for the others locations
    #-------------------------------------------------------------------------------
    
    for nodeid, locations in DictLocationsNotMapped.items():
        
        # Get current concise DCF
        node = nodelist.SlaveNodes[nodeid]["Node"]
        nodeDCF = nodelist.GetMasterNodeEntry(0x1F22, nodeid)
        
        if nodeDCF != None and nodeDCF != '':
            tmpnbparams = [i for i in nodeDCF[:4]]
            tmpnbparams.reverse()
            nbparams = int(''.join(["%2.2x"%ord(i) for i in tmpnbparams]), 16)
            dataparams = nodeDCF[4:]
        else:
            nbparams = 0
            dataparams = ""
        
        for pdotype in (TPDO, RPDO):
            pdosize = 0
            pdomapping = []
            for name, loc_infos in locations[pdotype]:
                pdosize += loc_infos["size"]
                # If pdo's size > 64 bits
                if pdosize > 64:
                    result = GetNewCobID(nodeid, pdotype)
                    if result:
                        SlavesPdoNumber[nodeid][pdotype] += 1
                        new_cobid, new_idx = result
                        data, nbaddedparams = GenerateMappingDCF(new_cobid, new_idx, pdomapping, False)
                        dataparams += data
                        nbparams += nbaddedparams
                        DictCobID[new_cobid] = {"type" : InvertPDOType[pdotype], "mapping" : GenerateMasterMapping(pdomapping)}
                    pdosize = loc_infos["size"]
                    pdomapping = [(name, loc_infos)]
                else:
                    pdomapping.append((name, loc_infos))
            if len(pdomapping) > 0:
                result = GetNewCobID(nodeid, pdotype)
                if result:
                    SlavesPdoNumber[nodeid][pdotype] += 1
                    new_cobid, new_idx = result
                    data, nbaddedparams = GenerateMappingDCF(new_cobid, new_idx, pdomapping, False)
                    dataparams += data
                    nbparams += nbaddedparams
                    DictCobID[new_cobid] = {"type" : InvertPDOType[pdotype], "mapping" : GenerateMasterMapping(pdomapping)}
        
        dcf = LE_to_BE(nbparams, 0x04) + dataparams
        manager.SetCurrentEntry(0x1F22, nodeid, dcf, "value", None)


    #-------------------------------------------------------------------------------
    #                         Master Node Configuration
    #-------------------------------------------------------------------------------
    
    
    # Configure Master's SDO parameters entries
    for nodeid, SDOparams in DictSDOparams.items():
        SdoClient_index = [0x1280 + nodeid]
        manager.ManageEntriesOfCurrent(SdoClient_index,[])
        if SDOparams["RSDO"] != None:
            RSDO_cobid = SDOparams["RSDO"]
        else:
            RSDO_cobid = 0x600 + nodeid 
            
        if SDOparams["TSDO"] != None:
            TSDO_cobid = SDOparams["TSDO"]
        else:
            TSDO_cobid = 0x580 + nodeid 
            
        manager.SetCurrentEntry(SdoClient_index[0], 0x01, RSDO_cobid, "value", None)
        manager.SetCurrentEntry(SdoClient_index[0], 0x02, TSDO_cobid, "value", None)
        manager.SetCurrentEntry(SdoClient_index[0], 0x03, nodeid, "value", None)

    # Configure Master's PDO parameters entries and set cobid, transmit type
    for cobid, pdo_infos in DictCobID.items():
        current_idx = CurrentPDOParamsIdx[pdo_infos["type"]]
        addinglist = [current_idx, current_idx + 0x200]
        manager.ManageEntriesOfCurrent(addinglist, [])
        manager.SetCurrentEntry(current_idx, 0x01, cobid, "value", None)
        manager.SetCurrentEntry(current_idx, 0x02, DefaultTransmitType, "value", None)
        if len(pdo_infos["mapping"]) > 2:
            manager.AddSubentriesToCurrent(current_idx + 0x200, len(pdo_infos["mapping"]) - 2)
        
        # Create Master's PDO mapping
        for subindex, variable in enumerate(pdo_infos["mapping"]):
            if subindex == 0:
                continue
            new_index = False
            
            if type(variable) != IntType:
                
                typeidx, varname = variable
                indexname = DictNameVariable[DictLocations[variable[1]]["pdotype"]][0] + DictLocations[variable[1]]["sizelocation"] + str(DictLocations[variable[1]]["busname"]) + "_" + str(DictLocations[variable[1]]["nodeid"])
                mapvariableidx = DictNameVariable[DictLocations[variable[1]]["pdotype"]][1] +  DictNameVariable[DictLocations[variable[1]]["sizelocation"]] * DictNameVariable["increment"]
                
                if not manager.IsCurrentEntry(mapvariableidx):
                    manager.AddMapVariableToCurrent(mapvariableidx, indexname, 3, 1)
                    new_index = True
                    nbsubentries = manager.GetCurrentEntry(mapvariableidx, 0x00)
                else:
                    nbsubentries = manager.GetCurrentEntry(mapvariableidx, 0x00)
                    mapvariableidxbase = mapvariableidx 
                    while mapvariableidx < (mapvariableidxbase + 0x1FF) and nbsubentries == 0xFF:
                        mapvariableidx += 0x800
                        if not manager.IsCurrentEntry(mapvariableidx):
                            manager.AddMapVariableToCurrent(mapvariableidx, indexname, 3, 1)
                            new_index = True
                        nbsubentries = manager.GetCurrentEntry(mapvariableidx, 0x00)
                if mapvariableidx < 0x6000:
                    if DictLocations[variable[1]]["bit"] != None:
                        subindexname = "_" + str(DictLocations[variable[1]]["index"]) + "_" + str(DictLocations[variable[1]]["subindex"]) + "_" + str(DictLocations[variable[1]]["bit"])
                    else:
                        subindexname = "_" + str(DictLocations[variable[1]]["index"]) + "_" + str(DictLocations[variable[1]]["subindex"])
                    if not new_index:
                        manager.AddSubentriesToCurrent(mapvariableidx, 1)
                        nbsubentries += 1
                    manager.SetCurrentEntry(mapvariableidx, nbsubentries, subindexname, "name", None)
                    manager.SetCurrentEntry(mapvariableidx, nbsubentries, typeidx, "type", None)
                    
                    # Map Variable
                    typeinfos = manager.GetEntryInfos(typeidx)
                    if typeinfos != None:
                        value = (mapvariableidx << 16) + ((nbsubentries) << 8) + typeinfos["size"]
                        manager.SetCurrentEntry(current_idx + 0x200, subindex, value, "value", None)
            else:
                manager.SetCurrentEntry(current_idx + 0x200, subindex, TrashVariableValue[variable], "value", None)
        
        CurrentPDOParamsIdx[pdo_infos["type"]] += 1

if __name__ == "__main__":
    from nodemanager import *
    from nodelist import *
    import sys
    
    manager = NodeManager(sys.path[0])
    nodelist = NodeList(manager)
    result = nodelist.LoadProject("/home/deobox/Desktop/TestMapping")
   
    if result != None:
        print result
    else:
        print "MasterNode :"
        manager.CurrentNode.Print()
        for nodeid, node in nodelist.SlaveNodes.items():
            print "SlaveNode name=%s id=0x%2.2X :"%(node["Name"], nodeid)
            node["Node"].Print()
            
    #filepath = "/home/deobox/beremiz/test_nodelist/listlocations.txt"
    filepath = "/home/deobox/Desktop/TestMapping/listlocations.txt"
    
    file = open(filepath,'r')
    locations = [location.split(' ') for location in [line.strip() for line in file.readlines() if len(line) > 0]] 
    file.close()
    GenerateConciseDCF(locations, 32, nodelist)
    print "MasterNode :"
    manager.GetCurrentNode().Print()
