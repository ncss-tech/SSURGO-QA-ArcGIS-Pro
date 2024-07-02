# -*- coding: utf-8 -*-
"""
Edgematch v. 1.1
31 March 2021
Created by Alexander Stum, GIS Specialist South-Central SPSD USDA-NRCS

ArcGIS Pro 2.7 compatible

This tool is part of the SSURGO QA toolbox
It finds Edge Match Errors, that is soil polygon nodes along soil survey boundaries
without a coincident node in the adjoining survey and vice a versa.

This tool can use feature layers or feature classes as inputs
It does honor the selected set of the input SAPOLYGON layer, but not from other features
All inputs must have the same field name for the AREASYMBOL

# Requires BCore.py module

@author: Alexander.Stum

1.1
    1) Removed Install_Version function
    2) Removed arcpy.env.parallelProcessingFactor from BCore function
    3) mp.set_executable now calls python.exe
    4) Capped number of processes to no more than number of survey areas
"""

import arcpy
import sys
import os
# import math
import time
import warnings  # psutil
import multiprocessing as mp
import BCore
import importlib
importlib.reload(BCore)
from BCore import BCore

warnings.filterwarnings("ignore")

# %% Fucntions
def BNodes(SA_, MU, nodes):
    try:
        # ======= Variables  ==========
        MU_         = "in_memory/MU_outline"
        MU_o        = "MU_outer"
        MU_d        = "in_memory/MU_d"
        MU_inter    = "in_memory/MU_inter"
        Point       = arcpy.Point
        PG          = arcpy.PointGeometry

        arcpy.management.SelectLayerByLocation(MU, "INTERSECT" , SA_) #, BOUNDARY_TOUCHES
                                               # None, "SUBSET_SELECTION")
        arcpy.PolygonToLine_management(MU, MU_)
        arcpy.MakeFeatureLayer_management(MU_, MU_o, "LEFT_FID = -1")
        arcpy.PairwiseIntersect_analysis([MU_o, SA_], MU_inter)
        # arcpy.management.SelectLayerByLocation(MU_o, "INTERSECT", SA_) #, BOUNDARY_TOUCHES
                                               # None, "SUBSET_SELECTION")
        MU_d = arcpy.analysis.PairwiseDissolve(MU_inter, arcpy.Geometry(),
                                               "RIGHT_FID", None, "MULTI_PART")
        ends = {(p.X, p.Y) 
                for G in MU_d   # for each polyline geometry
                for P in G     # for each part (Array) of geometry
                for p in [P[0], P[-1]]} # for the for the last and first points
        
        if nodes and ends:
            nodePot = tuple((PG(Point(x, y)) for x, y in ends))
            arcpy.CopyFeatures_management(nodePot, nodes)
        return ends

    except:
        arcpy.AddError("Error in BNodes function: " + str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise
        
        
def BNodes2(MU, nodes, areas):
    try:
        #======= Variables  ==========
        boundDict    = {}
        update      = boundDict.update
        Point       = arcpy.Point
        PG          = arcpy.PointGeometry
        
        arcpy.env.parallelProcessingFactor = 2  # threads
        mp.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
        pCores = min(os.cpu_count() - 2, len(areas))
        pool = mp.Pool(pCores)
        result = [pool.apply_async(BCore, args=(A, MU), callback=update)
                  for A in areas]

        pool.close()
        pool.join()
        arcpy.env.parallelProcessingFactor = pCores
        # for res in result: # useful to capture errors from bCore
        #     arcpy.AddMessage(res.get())
        if nodes and boundDict:
            nodePot = tuple(PG(Point(x, y)) 
                             for nodeL in list(boundDict.values())
                             for x, y in nodeL)
            arcpy.CopyFeatures_management(nodePot, nodes)
        
        return boundDict

    except:
        # pool.close()
        # PrintMsg(str(l))
        arcpy.AddError("Error in BNodes2 function: " + str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise


##############################
# %% Main
try:
    ######################
    #======= Parameters  ==========
    MUin = arcpy.GetParameter(0)
    SAin = arcpy.GetParameter(1)
    AREASYMBOL = arcpy.GetParameterAsText(2)
    areas_L = arcpy.GetParameter(3)
    MUcomp = arcpy.GetParameter(4)
    SAcomp = arcpy.GetParameter(5)


    # %%% Variables
    arcpy.AddMessage("Edgemath version 1.1")
    start           = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    MUin_d          = arcpy.Describe(MUin)
    SAin_d          = arcpy.Describe(SAin)
    MUcomp_d        = arcpy.Describe(MUcomp)
    SAcomp_d        = arcpy.Describe(SAcomp)
    
    inputPath            = MUin_d.path
    
    # if MUin_d.dataType == "FeatureClass":
    MUin = MUin_d.catalogPath
    if SAin_d.dataType == "FeatureClass":
        SAin = SAin_d.catalogPath
    # if MUcomp_d.dataType == "FeatureClass":
        
    if arcpy.Describe(inputPath).dataType == 'FeatureDataset':
        gdb         = os.path.dirname(inputPath)
    else:
        gdb         = inputPath
    
    if not areas_L:
        with arcpy.da.SearchCursor(SAin, AREASYMBOL) as sCur:
            areas = {a for a, in sCur}
    elif type(areas_L).__name__ == 'str':
        areas = set([areas_L])
    else:
        areas = set(areas_L)
    SAin = SAin_d.catalogPath
    # if SAcomp_d.dataType == "FeatureClass":
    #     SAcomp = SAcomp_d.catalogPath
    if not arcpy.GetParameterAsText(4): # or not arcpy.GetParameterAsText(5):
        MUcomp = MUin
        SAcomp = SAin
    else:
        MUcomp = MUcomp_d.catalogPath
        SAcomp = SAcomp_d.catalogPath
        if MUcomp_d.spatialReference.name != MUin_d.spatialReference.name:
            arcpy.AddError("The input and comparison datasets have differing spatial reference systems")
            arcpy.AddError(f"input: {MUin_d.spatialReference.name}")
            arcpy.AddError(f"comparison: {MUcomp_d.spatialReference.name}")
            sys.exit(1)

    nSurvs          = len(areas)

    SA_L            = "SA_Layer"                       #RTSD SAPOLYGONS
    SA_L2           = "SA_Layer2"                       #RTSD SAPOLYGONS
    SA_L3           = "SA_Layer3"
    
    SAin_           = "in_memory/SAin"
    SAin_Lin        = "SAin_in"
    SAin_Lout       = "SAin_out"
    
    SA_             = "in_memory/SA_"
    SA_out          = "in_memory/SA_out"
    SA_2            = "in_memory/SA_2"
    
    MUin_L          = "MUin_L"
    MUR_L           = "comp_layer"
    
    kNodes          = None
    nNodes          = None
    oNodes          = None
    mismatch_n      = 'QA_EdgeMatch_Errors_p'
    mismatch          = os.path.join(inputPath, mismatch_n)
    
    arcpy.env.workspace = gdb
    retain = False
    if retain:
        kNodes          = "keyNodes"
        nNodes          = "newNodes"
        oNodes          = "outNodes"
        
        if arcpy.ListFeatureClasses(kNodes):
             arcpy.Delete_management(kNodes)
        if arcpy.ListFeatureClasses(nNodes):
             arcpy.Delete_management(nNodes)
             
    Geom                = arcpy.Geometry

    # %%% General Setup
    arcpy.AddMessage("Finding Edge Match Errors")

    cores = os.cpu_count()
    pCores = cores-1  # -threads  #Leaves one physical core free
#    pCores = str((cores-4)/cores*100)+'%'
    arcpy.env.parallelProcessingFactor = pCores
    arcpy.env.overwriteOutput = True

    MUD = arcpy.Describe(MUin).spatialReference
    # XYRin = MUD.XYResolution
    # XYTin = MUD.XYTolerance

    # fD = arcpy.Describe(inputPath)
    # XYR = fD.spatialReference.XYResolution
    # XYT = fD.spatialReference.XYTolerance

  
    if arcpy.ListFeatureClasses(mismatch_n):
        arcpy.Delete_management(mismatch_n)


except:
    arcpy.AddError("Failed in General Setup")
    arcpy.AddError("Unexpected error on line: "+str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
    
# %%%Node Discovery
try:
    arcpy.env.workspace = inputPath
    arcpy.SetProgressor('default', 'Creating Boundary Nodes')

    # Surveys being checked
    q = AREASYMBOL + " IN ('"+"','".join(areas)+"')"
    arcpy.MakeFeatureLayer_management(SAin, SA_L, q)   # Suveys of interest
    arcpy.PolygonToLine_management(SA_L, SAin_)
    with arcpy.da.SearchCursor(SA_L, ['OID@', AREASYMBOL]) as sCur:
        fid2sym = dict(sCur)
    arcpy.MakeFeatureLayer_management(SAin_, SAin_Lout, "LEFT_FID = -1")
    
    # # Neighboring surveys
    q2 = AREASYMBOL + " NOT IN ('"+"','".join(areas)+"')"
    arcpy.MakeFeatureLayer_management(SAcomp, SA_L2, q2)
    arcpy.SelectLayerByLocation_management(SA_L2, 'BOUNDARY_TOUCHES', SA_L) #,
    #                                        # selection_type='SUBSET_SELECTION')

    with arcpy.da.SearchCursor(SA_L2, AREASYMBOL) as sCur:
        rNeigh = {a for a, in sCur}
    # Soil polygons from neighboring surveys
    q3 = AREASYMBOL + " IN ('"+"','".join(rNeigh)+"')"  # Neighboirng survey areas
    arcpy.MakeFeatureLayer_management(MUcomp, MUR_L, q3)
    
    # neighbors = int(arcpy.GetCount_management(MUR_L).getOutput(0))
    if len(rNeigh):
        arcpy.AddMessage(f"Working with neighbors {rNeigh}")
        
        # All surveys
        allSurvs = areas | rNeigh
        q4 = AREASYMBOL + " IN ('"+"','".join(allSurvs)+"')"
        arcpy.MakeFeatureLayer_management(SAcomp, SA_L3, q4)
        arcpy.PolygonToLine_management(SA_L3, SA_)
        
        with arcpy.da.SearchCursor(SA_, ['RIGHT_FID'], "LEFT_FID = -1") as sCur:
            outFids = {f for f, in sCur}  
         
        # Find the Nodes
        setDict = BNodes2(MUin, nNodes, areas)
        setDict['zext'] = BNodes(SAin_Lout, MUR_L, kNodes) #SAcommon
        # arcpy.AddMessage(f"neighbor nodes: {len(setDict['zext'])}")
        # Set up survey proximity matrix
        fid2sym[-1] = 'zext'
        neighSet = set()
        inFids = set()
        with arcpy.da.SearchCursor(SAin_, ['RIGHT_FID', 'LEFT_FID']) as sCur:
            for right, left in sCur:
                inFids.add(right)
                inFids.add(left)
                Neigh = [fid2sym[right], fid2sym[left]]
                Neigh.sort()
                neighSet.add(tuple(Neigh))
        inFids.remove(-1)
        nakedFids = inFids & outFids
        if nakedFids:
            arcpy.AddMessage("Outward facing boundary")
            nakedSyms = {fid2sym[f] for f in nakedFids}
            q5 = AREASYMBOL + " IN ('"+"','".join(nakedSyms)+"')"
            arcpy.MakeFeatureLayer_management(MUin, MUin_L, q5)
            arcpy.PolygonToLine_management(SA_L2, SA_2, "IGNORE_NEIGHBORS")
            arcpy.PairwiseErase_analysis(SAin_, SA_2, SA_out)
            
            outside = BNodes(SA_out, MUin_L, oNodes)
            arcpy.AddMessage("outward done")
        else:
            outside = set()
    else:
        arcpy.AddMessage("No external neighbors")
        arcpy.MakeFeatureLayer_management(MUin, MUin_L, q)
        setDict = BNodes2(MUin, nNodes, areas)
        outside = BNodes(SAin_Lout, MUin_L, oNodes)
        # Remove vertices 
        # Set up survey proximity matrix
        neighSet = set()
        arcpy.MakeFeatureLayer_management(SAin_, SAin_Lin, "LEFT_FID <> -1")
        SA_ = SAin_Lin
        with arcpy.da.SearchCursor(SAin_Lin, ['RIGHT_FID', 'LEFT_FID']) as sCur:
            for right, left in sCur:
                Neigh = [fid2sym[right], fid2sym[left]]
                Neigh.sort()
                neighSet.add(tuple(Neigh))
    
    # (a | b | c) - ((a & b) | (a & c) | (b & c))
    exclusive = set()
    inclusive = set()
    inclusive = inclusive.union(*list(setDict.values()))
    
    for aSet, bSet in neighSet:
        exclusive.update(setDict[aSet] & setDict[bSet])

    offSet = inclusive - exclusive

    #Find survey area intersections
    SA_d = arcpy.analysis.PairwiseDissolve(SA_, Geom(), None, None, "SINGLE_PART")
    if SA_d:
        SA_ends = arcpy.management.FeatureVerticesToPoints(SA_d, Geom(), "BOTH_ENDS")
        setSA = {(p.X, p.Y) 
                    for G in SA_ends   # for each point geometry
                    for p in G}     # for point each in point geometry
        #Exclude survey area intersections
        offSet.difference_update(setSA | outside)

    Point       = arcpy.Point
    PG          = arcpy.PointGeometry
    if offSet:
        misSet = tuple(PG(Point(x, y)) for x, y in offSet)
        arcpy.CopyFeatures_management(misSet, mismatch) # allNodes)

        errorCount = len(misSet)
        if errorCount:
            arcpy.AddWarning(f"{errorCount} Edge match errors found, see feature {mismatch_n}")
    else:
        arcpy.AddMessage("No edge match errors found")
    
except:
    arcpy.AddError("Failed while creating Boundary Nodes")
    arcpy.AddError("Unexpected error on line: "+str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
    raise