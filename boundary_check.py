#! /usr/bin/env python3
# # -*- coding: utf-8 -*-
"""
Boundary Check tool
This tool scans the SAPOLYGON feature for new or shifted vertices which 
indicates updates have occured along a soil survey area boudary 
and therefore adjacent surveys on either side need to be staged for 
refresh.

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@created 3/18/2025
@modified 3/18/2025
    @by: Alexnder Stum
@version: 1.0

# ---"
"""


import os
import sys
import traceback
import arcpy

def pyErr(func: str) -> str:
    """When a python exception is raised, this funciton formats the traceback
    message.

    Parameters
    ----------
    func : str
        The function that raised the python error exception

    Returns
    -------
    str
        Formatted python error message
    """
    try:
        etype, exc, tb = sys.exc_info()
        
        tbinfo = traceback.format_tb(tb)[0]
        tbinfo = '\t\n'.join(tbinfo.split(','))
        msgs = (f"PYTHON ERRORS:\nIn function: {func}"
                f"\nTraceback info:\n{tbinfo}\nError Info:\n\t{exc}")
        return msgs
    except:
        return "Error in pyErr method"


def arcpyErr(func: str) -> str:
    """When an arcpy by exception is raised, this function formats the 
    message returned by arcpy.

    Parameters
    ----------
    func : str
        The function that raised the arcpy error exception

    Returns
    -------
    str
        Formatted arcpy error message
    """
    try:
        etype, exc, tb = sys.exc_info()
        line = tb.tb_lineno
        msgs = (f"ArcPy ERRORS:\nIn function: {func}\non line: {line}"
                f"\n\t{arcpy.GetMessages(2)}\n")
        return msgs
    except:
        return "Error in arcpyErr method"
    

def main():
    try:
        gdb_p = arcpy.GetParameterAsText(0)
        pr_p = gdb_p + '/ProjectRecord'
        sa_pts = pr_p + '/sapoint_gold'
        sapoly_p = gdb_p + '/FD_RTSD/SAPOLYGON'
        sareg_p = pr_p + '/saregional_gold'
        current_pts = 'in_memory/current_pts'
        novel_pts = pr_p + '/novel_pts'
        novel_lyr = 'novel_pts_lyr'

        # Create current SAPOLYGON points
        arcpy.management.FeatureVerticesToPoints(sapoly_p, current_pts, "ALL")
        # Find novel points
        arcpy.env.XYTolerance = 0.0002
        arcpy.env.overwriteOutput = True
        arcpy.analysis.Erase(current_pts, sa_pts, novel_pts)

        if int(arcpy.management.GetCount(novel_pts).getOutput(0)):
            arcpy.AddWarning(
                "Updates have been made along SSA boundaries, "
                "(see novel_pts feature)"
            )
            # Check along regional boundary
            arcpy.management.MakeFeatureLayer(novel_pts, novel_lyr)
            arcpy.management.SelectLayerByLocation(
                novel_lyr, "BOUNDARY_TOUCHES", sareg_p
            )
            arcpy.management.SelectLayerByLocation(
                novel_lyr, "WITHIN", sareg_p, None, "ADD_TO_SELECTION", "INVERT"
            )
            if int(arcpy.management.GetCount(novel_lyr).getOutput(0)):
                arcpy.AddWarning(
                    f"Following SSA's have updates along regional boundary:"
                )
                with arcpy.da.SearchCursor(novel_lyr, 'AREASYMBOL') as sCur:
                    ssas = {ssa for ssa, in sCur}
                ssas_t = '\n\t'.join(ssas)
                arcpy.AddMessage(f"\t{ssas_t}")
            arcpy.management.SelectLayerByAttribute(
                novel_lyr, "SWITCH_SELECTION"
            )
            if int(arcpy.management.GetCount(novel_lyr).getOutput(0)):
                arcpy.AddWarning(
                f"Following SSA's have updates along a SSA boundary:"
                )
                with arcpy.da.SearchCursor(novel_lyr, 'AREASYMBOL') as sCur:
                    ssas = {ssa for ssa, in sCur}
                ssas_t = '\n\t'.join(ssas)
                arcpy.AddMessage(f"\t{ssas_t}")
        else:
            arcpy.AddMessage("No updates were discovered along SSA boudnaries")

        arcpy.management.Delete(current_pts)

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


if __name__ == '__main__':
    main()