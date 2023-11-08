# -*- coding: utf-8 -*-
"""
Created on Mon Sep 28 14:09:01 2020

@author: Alexander.Stum

Version 1.1
 1) strip white space from symbols read from crosswalk
"""

import arcpy
import os
import sys

try:    
    FCin        = arcpy.GetParameter(0)        # MUPOLYGON to be modified
    FCas        = arcpy.GetParameterAsText(1)  # AREASYMBOL field
    FCmu        = arcpy.GetParameterAsText(2)  # MUSYM field (to be modified)
    FCan        = arcpy.GetParameterAsText(3)  # Ancillary field
    q           = arcpy.GetParameterAsText(4)  # Query to create selected set
    crosswalk   = arcpy.GetParameterAsText(5)  # Input crossalk table
    CWas        = arcpy.GetParameterAsText(6)  # AREASYMBOL field
    CWmuI       = arcpy.GetParameterAsText(7)  # current MUSYM field
    CWmuR       = arcpy.GetParameterAsText(8)  # replacement MUSYM field
    CWan        = arcpy.GetParameterAsText(9)
    
    fcp = arcpy.Describe(FCin).catalogPath
    gdb = os.path.dirname(fcp)
    if arcpy.Describe(gdb).dataType=='FeatureDataset':
        gdb = os.path.dirname(gdb)
    
    if CWan: inFields = [CWas, CWmuI, CWmuR, CWan]
    else: inFields = [CWas, CWmuI, CWmuR]
    with arcpy.da.SearchCursor(crosswalk, inFields) as sCur:
        MUdict = {}
        crossCheck = set()
        listed = set()
        if not CWan:
            for AS, muI, muR in sCur: #csvR:
                # complete entry and list for area already started
                AS = AS.strip()
                muI = muI.strip()
                muR = muR.strip()
                if (AS and muI and muR) and (AS in MUdict):
                    if not muI in MUdict[AS]:
                        MUdict[AS][muI] = muR
                        crossCheck.add((AS, muR))
                        listed.add((AS, muI))
                    else:
                        arcpy.AddError("_____________________________________________")
                        arcpy.AddError(f"More than one entry found for {AS}: '{muI}'.")
                        raise
                # complete entry
                elif AS and muI and muR:
                    MUdict[AS] = {muI: muR}
                    crossCheck.add((AS, muR))
                    listed.add((AS, muI))
                # an incomplete entry
                elif AS or muI or muR:
                    arcpy.AddError("_____________________________________________")
                    arcpy.AddError(f"An incomplete entry\n AREASYMBOL: {AS or '<empty>'}")
                    arcpy.AddError(f"current MUSYM: {muI or '<empty>'}\n replacement MUSYM: {muR or '<empty>'}")
                    raise
                else: # blank entry
                    continue
        else:
            for AS, muI, muR, An in sCur: #csvR:
                AS = AS.strip()
                muI = muI.strip()
                muR = muR.strip()
                muI_ = muI + str(An)
                # complete entry and list for area already started
                if (AS and muI and muR) and (AS in MUdict):
                    if not muI_ in MUdict[AS]:
                        MUdict[AS][muI_] = muR
                        crossCheck.add((AS, muR))
                        listed.add((AS, muI_))
                    else:
                        arcpy.AddError("_____________________________________________")
                        arcpy.AddError(f"More than one entry found for {AS}: '{muI}'.")
                        raise
                # complete entry
                elif AS and muI and muR:
                    MUdict[AS] = {muI_: muR}
                    crossCheck.add((AS, muR))
                    listed.add((AS, muI_))
                # an incomplete entry
                elif AS or muI or muR:
                    arcpy.AddError("_____________________________________________")
                    arcpy.AddError(f"An incomplete entry\n AREASYMBOL: {AS or '<empty>'}")
                    arcpy.AddError(f"current MUSYM: {muI or '<empty>'}\n replacement MUSYM: {muR or '<empty>'}")
                    raise
                else: # blank entry
                    continue
except:
    arcpy.AddError("Failed while reading in crosswalk")
    arcpy.AddError("Unexpected error on line: "+str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
    raise

try:
    used = set()
    actual = set()
    arcpy.env.workspace = gdb
    edit = arcpy.da.Editor(gdb)
    edit.startEditing(True, True)
    edit.startOperation()
    if FCan and CWan:
        uCur = arcpy.da.UpdateCursor(FCin, [FCas, FCmu, FCan], q)
        for AS, mu, an in uCur:
            try:
                mucat = f"{mu}{an}"
                newMU = MUdict[AS][mucat]
                uCur.updateRow([AS, newMU, an])
                used.add((AS, newMU))
                actual.add((AS ,mucat))
            except:
                continue
    else:
        uCur = arcpy.da.UpdateCursor(FCin, [FCas, FCmu], q)
        for AS,mu in uCur:
            try:
                newMU = MUdict[AS][mu]
                uCur.updateRow([AS, newMU])
                used.add((AS, newMU))
                actual.add((AS, mu))
            except:
                continue
    
    del uCur
    edit.stopOperation()
    edit.stopEditing(True)
except:
    edit.stopOperation()
    edit.stopEditing(False)
    arcpy.AddError("Failed while updating {arcpy.Describe(FCin).name}")
    arcpy.AddError("Unexpected error on line: "+str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
    raise

if crossCheck-used:
    arcpy.AddWarning("_____________________________________________")
    arcpy.AddWarning("Not all replacement MUSYMs were used")
    for AS, mu in crossCheck-used:
        arcpy.AddWarning(f"{AS}: '{mu}'")
if listed-actual:
    arcpy.AddWarning("_____________________________________________")
    arcpy.AddWarning("Crosswalk included musyms not found in feature class")
    for AS, mu in listed-actual:
        arcpy.AddWarning(f"{AS}: {mu.split('|')}")