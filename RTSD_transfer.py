#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTSD_transfer
A tool to transfer Regional Transactional Soil Databases into a new 
File Geodatabase with Feature Datasets setup with 0.0001 m XY Resolution and
inclusion of SAPOLYGON topology rules.
Created on: 3/12/2025

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 3/12/2025
    @by: Alexnder Stum
@version: 1.0

# ---

"""

import arcpy
import sys
import os
import datetime
import traceback
from arcpy import env


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


def createTopology(RTSD_p: str) -> bool:
    """Creates a topolgy with the RTSD_FD Feature Dataset

    All official soil spatial features have topological considerations. This 
    tool properly sets those rules up.

    Parameters
    ----------
    RTSD_p : str
        Path of the new RTSD FGDB

    Returns
    -------
    bool
        Returns True if successful, otherwise False.
    """
    
    try:
        fd_p = RTSD_p + '/FD_RTSD'
        env.workspace = fd_p
        topo_n = "FD_RTSD_Topology"
        topo_p = f"{fd_p}/{topo_n}"
        # # To create a unique name
        arcpy.SetProgressor("step", "Creating Topology", 0, 3, 1)

        # Create New topology
        arcpy.SetProgressorLabel("Creating Topology")
        arcpy.CreateTopology_management(fd_p, topo_n, 0.2)

        arcpy.AddMessage(
            "\nCreated Topology: FD_RTSD_Topology at 0.2m cluster tolerance"
        )
        arcpy.SetProgressorPosition()
        
        # Add feature classes to topology
        arcpy.SetProgressorLabel(
            "Creating Topology: Adding Feature Classes to Topology")
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/MUPOLYGON", 1, 1
        )
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/MUPOINT", 1, 1
        )
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/MULINE", 1, 1
        )
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/FEATPOINT", 1, 1
        )
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/FEATLINE", 1, 1
        )
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/SAPOLYGON", 1, 1
        )
        arcpy.SetProgressorPosition()

        # Add Topology Rules
        arcpy.SetProgressorLabel("Creating Topology: Adding Rules to Topology")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Area)", f"{fd_p}/MUPOLYGON"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Gaps (Area)", f"{fd_p}/MUPOLYGON"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Area)", f"{fd_p}/SAPOLYGON"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Gaps (Area)", f"{fd_p}/SAPOLYGON"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Boundary Must Be Covered By Boundary Of (Area-Area)",
            f"{fd_p}/SAPOLYGON", "", f"{fd_p}/MUPOLYGON"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Intersect (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Overlap (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Pseudo-Nodes (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Intersect (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Single Part (Line)", f"{fd_p}/FEATLINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Disjoint (Point)", f"{fd_p}/FEATPOINT"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Disjoint (Point)", f"{fd_p}/MUPOINT"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Properly Inside (Point-Area)",
            f"{fd_p}/FEATPOINT", "", f"{fd_p}/MUPOLYGON",""
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Line)", f"{fd_p}/MULINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Intersect (Line)", f"{fd_p}/MULINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Overlap (Line)", f"{fd_p}/MULINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Pseudo-Nodes (Line)", f"{fd_p}/MULINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Intersect (Line)", f"{fd_p}/MULINE"
        )
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Single Part (Line)", f"{fd_p}/MULINE"
        )

        arcpy.AddMessage("\tAdded 20 rules to the Topology")
        arcpy.SetProgressorPosition()
        arcpy.ResetProgressor()

        # Create topology for project feature
        fd_p = RTSD_p + '/ProjectRecord'
        env.workspace = fd_p
        topo_n = "ProjectRecord_Topology"
        topo_p = f"{fd_p}/{topo_n}"
        arcpy.SetProgressor("step", "Creating Topology", 0, 3, 1)

        # Create New topology
        arcpy.SetProgressorLabel("Creating Topology")
        arcpy.CreateTopology_management(fd_p, topo_n, 0.2)

        arcpy.AddMessage(
            "\nCreated Topology: ProjectRecord_Topology at 0.2m" 
             "cluster tolerance"
        )
        arcpy.SetProgressorPosition()
        
        # Add feature classes to topology
        arcpy.SetProgressorLabel(
            "Creating Topology: Adding Feature Classes to Topology")
        arcpy.AddFeatureClassToTopology_management(
            topo_p, f"{fd_p}/Project_Record", 1, 1
        )
        arcpy.SetProgressorPosition()

        # Add Topology Rules
        arcpy.SetProgressorLabel("Creating Topology: Adding Rules to Topology")

        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Area)", f"{fd_p}/Project_Record"
        )
       
        arcpy.AddMessage("\tAdded 1 rules to the Topology")
        arcpy.SetProgressorPosition()
        arcpy.ResetProgressor()
        return True

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


# --- Main Body
if __name__ == '__main__':
    v = '1.0'
    arcpy.AddMessage(f'Version: {v}')
    env.parallelProcessingFactor = "85%"
    env.overwriteOutput = True
    env.geographicTransformations = 'WGS_1984_(ITRF00)_To_NAD_1983'
    # --- Input Arguments
    # Parameter 0: input RTSD path
    gdb_p = arcpy.GetParameterAsText(0)
    # Parameter 1: output directory of RTSD
    output_p = arcpy.GetParameterAsText(1)
    RTSD_p = f"{output_p}/{os.path.basename(gdb_p)[:-4]}_MarchStd.gdb"

    try:
        # List of features
        feat_d = {
            'FD_RTSD': {'path': RTSD_p + '/FD_RTSD', 
                        'feats': ['FEATLINE', 'FEATPOINT', 'MULINE', 'MUPOINT', 
                        'MUPOLYGON']}, 
            'ProjectRecord': {'path': RTSD_p + '/ProjectRecord', 
                        'feats': ['Project_Record',]},
            'main': {'path': RTSD_p, 'feats': ['featdesc',]}
        }

        # Create Empty Regional Transactional File Geodatabase
        arcpy.env.overwriteOutput = True
        
        arcpy.AddMessage(f"Creating new FGDB {RTSD_p}")
        arcpy.management.CreateFileGDB(output_p, os.path.basename(RTSD_p))

        # Create Feature Datasets
        arcpy.env.XYResolution = 0.0001
        sr = arcpy.Describe(gdb_p + '/FD_RTSD').spatialReference
        arcpy.management.CreateFeatureDataset(RTSD_p, 'FD_RTSD', sr)
        arcpy.management.CreateFeatureDataset(RTSD_p, 'ProjectRecord', sr)

        # Copy Features
        arcpy.env.workspace = gdb_p
        arcpy.conversion.FeatureClassToGeodatabase(
            [f'{gdb_p}/FD_RTSD/{fc}' for fc in feat_d['FD_RTSD']['feats']],
            feat_d['FD_RTSD']['path']
        )
        arcpy.conversion.FeatureClassToGeodatabase(
            gdb_p + '/ProjectRecord/Project_Record',
            feat_d['ProjectRecord']['path']
        )
        arcpy.conversion.TableToGeodatabase(
            gdb_p + '/featdesc', feat_d['main']['path']
        )
        arcpy.env.workspace = RTSD_p + "/FD_RTSD"

        # Create SAPOLYGON
        arcpy.analysis.PairwiseDissolve(
            RTSD_p + '/MUPOLYGON', RTSD_p + '/FD_RTSD/SAPOLYGON', 'AREASYMBOL'
        )
        arcpy.AddMessage('All features have been transferred')

        # Create sapoint_gold feature
        arcpy.management.FeatureVerticesToPoints(
            RTSD_p + '/FD_RTSD/SAPOLYGON', 
            RTSD_p + '/ProjectRecord/sapoint_gold', "ALL"
        )
        arcpy.analysis.PairwiseDissolve(
            RTSD_p + '/FD_RTSD/SAPOLYGON',
            RTSD_p + '/ProjectRecord/saregional_gold'
        )

        # Topology
        arcpy.env.workspace = RTSD_p
        if createTopology(RTSD_p):
            arcpy.SetProgressorLabel("Validating Topology")
            arcpy.env.workspace = RTSD_p + "/FD_RTSD"
            arcpy.ValidateTopology_management(
                RTSD_p + "/FD_RTSD/FD_RTSD_Topology"
            )
            arcpy.AddMessage("\tValidated FD_RTSD_Topology")
            arcpy.env.workspace = RTSD_p + "/ProjectRecord"
            arcpy.ValidateTopology_management(
                RTSD_p + "/ProjectRecord/ProjectRecord_Topology"
            )
            arcpy.AddMessage("\tValidated ProjectRecord_Topology")
        else:
            arcpy.AddError(
                "\n\tFailed to Create Topology. Create Topology Manually"
            )
            raise

        # --- Create Relationship class between project_record and SAPOLYGON
        arcpy.SetProgressorLabel(
            "Creating Relationship Class between Project_Record & SAPOLYGON"
        )
        pr_p = f"{RTSD_p}/ProjectRecord/Project_Record"
        sa_p = f"{RTSD_p}/FD_RTSD/SAPOLYGON"
        rel_n = "xProjectRecord_SAPOLYGON"
        
        arcpy.CreateRelationshipClass_management(
            pr_p, sa_p, rel_n, "SIMPLE", "> SAPOLYGON", "< Project_Record",
            "NONE", "ONE_TO_ONE", "NONE", "AREASYMBOL", "AREASYMBOL", "", ""
        )
        arcpy.AddMessage("\nSuccessfully Created Relationship Class")

        arcpy.SetProgressorLabel("Compacting " + RTSD_p)
        arcpy.Compact_management(RTSD_p)
        arcpy.AddMessage("\nSuccessfully Compacted " + RTSD_p)

        # Rename source FGDB
        os.rename(gdb_p, gdb_p[:-4] + '_original.gdb')

        arcpy.AddMessage('***************************************************')
        # --- Enable Tracking
        for fc in feat_d['FD_RTSD']['feats']:
            fc_p = f"{feat_d['FD_RTSD']['path']}/{fc}"
            arcpy.EnableEditorTracking_management(
                fc_p, 'Creator', 'Creation_Date', 'Editor',
                'Last_Edit_Date', 'ADD_FIELDS'
            )
            count = int(arcpy.GetCount_management(fc_p)[0])
            arcpy.AddMessage(
                f"Total number of {fc} features: "
                f"{count:,}"
            )

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))