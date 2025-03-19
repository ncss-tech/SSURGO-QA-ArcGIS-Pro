# -*- #################
"""
Generate Local Transactional Geodatabase
A tool for the SSURGO QA ArcGISPro arctoolbox
Created on: 10/12/2018

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 3/13/2025
    @by: Alexnder Stum
@version: 3.3

# ---
Update 3.3; 3/13/2025
- Changed XY Resolution to 0.0001 Meters
- Added all RTSD features
- Added createTopology, pyErr, arcpyErr functions
# ---
3.2 Updated 11/04/2024 - Alexander Stum
- Added 'ADD_Fields' parameter to EnableEditorTracking funciton call
# ---
3.1 Updated 11/07/2023 - Alexander Stum
- Lumped the first two input string parameters into a single Local Workspace
parameter.
- Created a boolean parameter to make domain/subtypes optional
- Cleaned up formatting
# ---
3.0 Updated
Changed Feature Dataset XYResolution to 0.1 m and Cluster Tolerance to 0.2 m
Added MUNAME field and modified MUSYM values to be themselves

"""

import os
import arcpy
import sys
import re
import json
from urllib.request import urlopen, URLError
import socket
import traceback
import winsound


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
def createTopology(fd_p: str, topo_n: str) -> bool:
    """Creates a topolgy with the RTSD_FD Feature Dataset

    All official soil spatial features have topological considerations. This 
    tool properly sets those rules up.

    Parameters
    ----------
    LTSD_p : str
        Path of the Feature Dataset in the new LTSD
    topo_n : str
        Name of the topology to be created in Feature Dataset `LTSD_p`

    Returns
    -------
    bool
        Returns True if successful, otherwise False.
    """
    
    try:
        arcpy.env.workspace = fd_p
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

        arcpy.AddMessage("\tAdded 17 rules to the Topology")
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


try:
    v = '3.2'
    gdb_p = arcpy.GetParameterAsText(0)
    gdb_n = os.path.basename(gdb_p)
    path = os.path.dirname(gdb_p)
    fds_n = arcpy.GetParameterAsText(1)
    rtsd_p = arcpy.GetParameterAsText(2)   #Needs to be full path name
    surveys = re.findall(r'\w+', arcpy.GetParameter(3))
    domain_b = arcpy.GetParameter(4)

    fds_p = gdb_p + '/' + fds_n
    rtsd_sa_p = rtsd_p + '/SAPOLYGON'
    sa_lyr = 'rtsd_SAPOLY'
    ltsd_sa_p = fds_p + '/SAPOLYGON'
    
    rtsd_mup = rtsd_p + '/MUPOLYGON'
    rtsd_mu_lyr = "rtsd_MUPOLY"
    ltsd_mup = fds_p + '/MUPOLYGON'
    ltsd_mu_lyr = "ltsd_MUs"

    rtsd_mul = rtsd_p + '/MULINE'
    mul_lyr = 'rtsd_MULINE'
    ltsd_mul = fds_p + '/MULINE'

    rtsd_mupt = rtsd_p + '/MUPOINT'
    mupt_lyr = 'rtsd_MUPOINT'
    ltsd_mupt = fds_p + '/MUPOINT'

    rtsd_fl = rtsd_p + '/FEATLINE'
    fl_lyr = 'rtsd_lines'
    ltsd_fl = fds_p + '/FEATLINE'

    rtsd_fpt = rtsd_p + '/FEATPOINT'
    fpt_lyr = 'rtsd_points'
    ltsd_fpt = fds_p + '/FEATPOINT'

    rtsd_fd = rtsd_p + '/featdesc'
    ltsd_fd = gdb_p + '/featdesc'

    pr_rec = rtsd_p + '/Project_Record'
    script_p = os.path.dirname(__file__)
    template_p = f'{script_p}/LTSD_domain_template.gdb/Domain_Template'
    topo_n = fds_n + '_topology'
    topo_p = fds_p + '/' + topo_n
    url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'
    source_fld = "AREASYMBOL"
    
    arcpy.AddMessage("version " + v)
    arcpy.CreateFileGDB_management(path, gdb_n)
    arcpy.env.XYTolerance = "0.0001 Meter"
    sr = arcpy.Describe(rtsd_mup).spatialReference

    arcpy.AddMessage(f"XY Tolerance: {sr.XYTolerance}")
    arcpy.CreateFeatureDataset_management(gdb_p, fds_n, sr)
    arcpy.env.workspace = fds_p

    #verify that all 'surveys' are found in master SAPOLYGON
    SURVS = arcpy.da.FeatureClassToNumPyArray(rtsd_sa_p, 'AREASYMBOL')
    projSurvs = arcpy.da.FeatureClassToNumPyArray(pr_rec, 'AREASYMBOL')
    SURVS = set(SURVS['AREASYMBOL'])
    projSurvs = set(projSurvs['AREASYMBOL'])
    
    survs = set(surveys)
    surveys = list(survs)
    if not survs & SURVS == survs:
        notIn = list((survs & SURVS) ^ survs)
        surveys = list(survs & SURVS)
        arcpy.AddWarning('Surveys not found in Region: ' + str(notIn))

    # Copy features from RTSD
    arcpy.AddMessage('Appending features')
    #Select from master SAPLYGON and copy to new gdb_p
    joined = '\',\''.join(surveys)
    parened = f"('{joined}')"
    q = f"AREASYMBOL IN {parened}"
    # SAPOLYGON
    arcpy.management.MakeFeatureLayer(rtsd_sa_p, sa_lyr, q)
    arcpy.Append_management(sa_lyr, pr_rec, 'NO_TEST')
    arcpy.management.CopyFeatures(sa_lyr, ltsd_sa_p)
    # MUPOLYGON
    arcpy.management.MakeFeatureLayer(rtsd_mup, rtsd_mu_lyr, q)
    arcpy.management.CopyFeatures(rtsd_mu_lyr, ltsd_mup)
    # MULINE
    arcpy.management.MakeFeatureLayer(rtsd_mul, mul_lyr, q)
    arcpy.management.CopyFeatures(mul_lyr, ltsd_mul)
    # MUPOINT
    arcpy.management.MakeFeatureLayer(rtsd_mupt, mupt_lyr, q)
    arcpy.management.CopyFeatures(mupt_lyr, ltsd_mupt)
    # FEATLINE
    arcpy.management.MakeFeatureLayer(rtsd_fl, fl_lyr, q)
    arcpy.management.CopyFeatures(fl_lyr, ltsd_fl)
    # FEATPOINT
    arcpy.management.MakeFeatureLayer(rtsd_fpt, fpt_lyr, q)
    arcpy.management.CopyFeatures(fpt_lyr, ltsd_fpt)
    # featdesc
    q = f"areasymbol IN {parened}"
    arcpy.conversion.ExportTable(rtsd_fd, ltsd_fd, q)

    #Check for overlaps
    if survs & projSurvs:
        arcpy.AddWarning(
            'These surveys are already in Project Record: '
            f'{(survs & projSurvs)}'
        )

    # Add reference fields to MUPOLYGON
    arcpy.AddMessage('Updating fields')
    fields = {f.name for f in arcpy.Describe(ltsd_mup).fields}
    arcpy.CalculateField_management(
        ltsd_mup, 'Acres', "!SHAPE.area@ACRES!", field_type='FLOAT')
    if 'AreaSub' not in fields:
        arcpy.management.AddField(ltsd_mup, 'AreaSub', 'SHORT')
    if 'orig_musym' not in fields:
        arcpy.management.AddField(
            ltsd_mup, 'orig_musym', 'TEXT', field_length=6, 
            field_alias='orig MUSYM'
        )
        arcpy.CalculateField_management(ltsd_mup, 'orig_musym', "!musym!")
    if 'MUNAME' not in fields:
        arcpy.management.AddField(
            ltsd_mup, 'MUNAME', 'TEXT', field_length=175, 
            field_alias='orig MUNAME'
        )
    if 'NATMUSYM' not in fields:
        arcpy.management.AddField(
            ltsd_mup, 'NATMUSYM', 'TEXT', field_length=6, 
            field_alias='orig NATMUSYM'
        )
    if 'MUKEY' not in fields:
        arcpy.management.AddField(
            ltsd_mup, 'MUKEY', 'TEXT', field_length=30, 
            field_alias='orig MUKEY'
        )
    arcpy.AddMessage('Fields added')

    #Select from ssurgo MUPOLYGON by 'surveys'
    sQuery = ("SELECT sacatalog.areasymbol, mapunit.musym, muname, "
              "nationalmusym, mukey FROM sacatalog  INNER JOIN legend "
              "ON legend.areasymbol = sacatalog.areasymbol "
              f"AND sacatalog.areasymbol IN {parened} "
              "INNER JOIN mapunit ON mapunit.lkey = legend.lkey"
    )
    dRequest = {"format": "JSON", "query": sQuery}
    jData = json.dumps(dRequest)
    jData = jData.encode('ascii')
    fetched = True
    try:
        response = urlopen(url, jData)
    except:
        try:
            response = urlopen(url, jData)
        except URLError as e:
            fetched = False
            arcpy.AddWarning(
                "Couldn't retrieve data from SDA. "
                "Fields muname, nationalmusy, & mueky not populated"
            )
            arcpy.AddWarning("\n\n" + sQuery)
            if hasattr(e, 'reason'):
                arcpy.AddWarning("\tURL Error: " + str(e.reason))
            elif hasattr(e, 'code'):
                arcpy.AddWarning(f"\t{e.msg} (errorcode {e.code})")
        except socket.timeout as e:
            fetched = False
            arcpy.AddWarning(
                "Couldn't retrieve data from SDA. "
                "Fields muname, nationalmusy, & mueky not populated"
            )
            arcpy.AddWarning("\tServer Timeout Error")
        except socket.error as e:
            fetched = False
            arcpy.AddWarning(
                "Couldn't retrieve data from SDA. Fields muname, nationalmusy, "
                "& mueky not populated"
            )
            arcpy.AddWarning("\tNASIS Reports Website connection failure")
        except:
            fetched = False
            arcpy.AddWarning(
                "Couldn't retrieve data from SDA. Fields muname, nationalmusy, "
                "& mueky not populated"
            )
    if fetched:    
        jsonString = response.read()
        data = json.loads(jsonString)
        mudict = {f'{row[0]}_{row[1]}':row[2:] for row in data['Table']}
    
        legends = {}
        for row in data['Table']:
            if row[0] in legends:
                legends[row[0]].add((row[1], tuple(row[2:])))
            else:
                legends[row[0]] = {(row[1], tuple(row[2:]))}
        for A in legends.keys():
            legends[A] =  dict(legends[A])
        fields = ['AREASYMBOL', 'MUSYM', 'MUNAME', 'NATMUSYM', 'MUKEY']
        with arcpy.da.UpdateCursor(ltsd_mup, fields) as uCur:
            for A, mu, muname, nat, mukey in uCur:
                # Amu = f"{A}_{mu}"
                if (A in legends) and (mu in legends[A]):
                    uCur.updateRow((A, mu) + legends[A][mu])
                else:
                    arcpy.AddWarning(f"Mapunit {A}: {mu} not found on SDA")
    # Option to create musym domains and aresymbol subtype
    if domain_b:
        arcpy.SetSubtypeField_management(ltsd_mup, 'AreaSub')
        arcpy.AddMessage('Creating Domains and subtypes')
        #Create orig_MUYSUM and update_MUSYM domains ONE FOR EACH SURVEY
        arcpy.CreateDomain_management(
            gdb_p, 'surveys', 'surveys', 'SHORT', 'CODED', 'DUPLICATE'
        )
        arcpy.CreateDomain_management(
            gdb_p, 'AreaSymbol',' Area Symbols', 'TEXT', 'CODED', 'DUPLICATE'
        )

        # Create Domains and Subtype for MUPOLYGON
        for i, A in enumerate(surveys):
            arcpy.AddCodedValueToDomain_management(gdb_p, 'surveys', i, A)
            arcpy.AddCodedValueToDomain_management(gdb_p, 'AreaSymbol', A, A)
            arcpy.AddSubtype_management(ltsd_mup, i, A)

            q = f"AREASYMBOL = '{A}'"
            arcpy.management.MakeFeatureLayer(ltsd_mup, ltsd_mu_lyr, q)
            arcpy.CalculateField_management(ltsd_mu_lyr, 'AreaSub', i)
            
            DO = 'original_MU_' + A
            DC = 'current_MU_' + A
            arcpy.CreateTable_management(gdb_p, DC, template_p)
            arcpy.CreateDomain_management(
                gdb_p, DO, DO, 'TEXT', 'CODED', 'DUPLICATE'
            )
            arcpy.CreateDomain_management(
                gdb_p, DC, DC, 'TEXT', 'CODED', 'DUPLICATE'
            )
            ##Add domain to field
            with arcpy.da.InsertCursor(
                os.path.join(gdb_p, DC), ['MUSYM']
            ) as iCur:
                legend = list(legends[A].keys())
                legend.sort()
                for mu in legend:
                    iCur.insertRow([mu])

            arcpy.TableToDomain_management(
                os.path.join(gdb_p, DC), 'MUSYM', 'MUSYM', gdb_p, DO
            )
            arcpy.TableToDomain_management(
                os.path.join(gdb_p, DC), 'MUSYM', 'MUSYM', gdb_p, DC
            )
            arcpy.AssignDomainToField_management(
                ltsd_mu_lyr, 'MUSYM', DC, str(i)
            )
            arcpy.AssignDomainToField_management(
                ltsd_mu_lyr, 'orig_musym', DO, str(i)
            )
            arcpy.Delete_management(ltsd_mu_lyr)
        arcpy.AssignDomainToField_management(
            ltsd_mup, 'AREASYMBOL', 'AreaSymbol'
        )
        arcpy.AssignDomainToField_management(ltsd_mup, 'AreaSub', 'surveys')
    
    arcpy.AddMessage('Creating Topology')
    # Topology
    if createTopology(fds_p, topo_n):
        arcpy.SetProgressorLabel("Validating Topology")
        arcpy.ValidateTopology_management(topo_p)
        arcpy.AddMessage("\tValidated Topology at 0.2 meters")
    else:
        arcpy.AddError(
            "\n\tFailed to Create Topology. Create Topology Manually"
        )
    arcpy.ValidateTopology_management(topo_p)
    arcpy.Compact_management(gdb_p)

    # Enable Editor Tracking (under Fields)
    features = ['MUPOLYGON', 'MULINE', 'MUPOINT', 'FEATLINE', 'FEATPOINT']
    for fc in features:
        fc_p = f"{fds_p}/{fc}"
        arcpy.EnableEditorTracking_management(
            fc_p, 'Creator', 'Creation_Date', 'Editor',
            'Last_Edit_Date', 'ADD_FIELDS'
        )
        count = int(arcpy.GetCount_management(fc_p)[0])
        arcpy.AddMessage(
            f"Total number of {fc[0]} features: "
            f"{count:,}"
        )

    winsound.PlaySound(
        f'{script_p}/OhYeah.wav', winsound.SND_FILENAME | winsound.SND_NOWAIT
    )
except:
    arcpy.AddError("Unexpected error on line: " + 
                   str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
