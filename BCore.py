# -*- coding: utf-8 -*-
"""
31 March 2021
Created by Alexander Stum, GIS Specialist South-Central SPSD USDA-NRCS

ArcGIS Pro 2.7 compatible

The BCore function finds nodes along the exterior of a polygon feature and returns
them as a set of x,y coordinate pairs

@author: Alexander.Stum
"""

import arcpy, sys

def BCore(A, MU):
    #======= Variables  ==========
    MU_l        = "MU_layer"+A
    MU_         = "in_memory/MU_outline"+A
    MU_o        = "MU_outer"+A
    
    try:
        arcpy.MakeFeatureLayer_management(MU, MU_l, f"AREASYMBOL = '{A}'")
        arcpy.PolygonToLine_management(MU_l, MU_)
        arcpy.MakeFeatureLayer_management(MU_, MU_o, "LEFT_FID = -1")
        MU_d = arcpy.analysis.PairwiseDissolve(MU_o, arcpy.Geometry(), 
                                               "RIGHT_FID", None, "MULTI_PART")
        ends = {(p.X, p.Y) 
                for G in MU_d   # for each polyline geometry
                for P in G     # for each part (Array) of geometry
                for p in [P[0], P[-1]]} # for the for the last and first points
        return {A: ends} #copy.deepcopy(ends)
    except:
        s1 =  sys.exc_info()[-1].tb_lineno
        s2 = sys.exc_info()[0]
        s3 = sys.exc_info()[1]
        return(f"BCore {A}: {s1}\n{s2}\n{s3}")
        raise