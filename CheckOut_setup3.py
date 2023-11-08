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

@modified 11/07/2023
    @by: Alexnder Stum
@version: 3.1

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

from importlib.util import find_spec
import os
import arcpy
import sys
import re
import json
from urllib.request import urlopen, URLError
import socket
import winsound


try:
    v = '3.1'
    gdb_p = arcpy.GetParameterAsText(0)
    gdb_n = os.path.basename(gdb_p)
    path = os.path.dirname(gdb_p)
    fds_n = arcpy.GetParameterAsText(1)
    rtsd_p = arcpy.GetParameterAsText(2)   #Needs to be full path name
    surveys = re.findall(r'\w+', arcpy.GetParameter(3))
    domain_b = arcpy.GetParameter(4)

    fds_p = gdb_p + '/' + fds_n
    rtsd_sa_p = os.path.join(rtsd_p, 'SAPOLYGON')
    sa_lyr = 'selected_surveys'
    ltsd_sa_p = os.path.join(fds_p, 'SAPOLYGON')
    
    rtsd_mu_p = os.path.join(rtsd_p,'MUPOLYGON')
    rtsd_mu_lyr = "selected_tranMUs"
    ltsd_mu_p = os.path.join(fds_p,'MUPOLYGON')
    ltsd_mu_lyr = "selected_MUs"
    pr_p = os.path.join(rtsd_p,'Project_Record')
    script_p = os.path.dirname(__file__)
    template_p = f'{script_p}/LTSD_domain_template.gdb/Domain_Template'
    topo_n = fds_n + '_topology'
    topo_p = fds_p + '/' + topo_n
    url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'
    source_fld = "AREASYMBOL"
    
    arcpy.AddMessage("version " + v)
    arcpy.CreateFileGDB_management(path, gdb_n)
    arcpy.env.XYTolerance = "1 Meter"
    sr = arcpy.Describe(rtsd_mu_p).spatialReference

    arcpy.AddMessage(f"XY Tolerance: {sr.XYTolerance}")
    arcpy.CreateFeatureDataset_management(gdb_p, fds_n, sr)
    arcpy.env.workspace = fds_p

    #verify that all 'surveys' are found in master SAPOLYGON
    SURVS = arcpy.da.FeatureClassToNumPyArray(rtsd_sa_p, 'AREASYMBOL')
    projSurvs = arcpy.da.FeatureClassToNumPyArray(pr_p, 'AREASYMBOL')
    SURVS = set(SURVS['AREASYMBOL'])
    projSurvs = set(projSurvs['AREASYMBOL'])
    
    survs = set(surveys)
    surveys = list(survs)
    if not survs & SURVS == survs:
        notIn = list((survs & SURVS) ^ survs)
        surveys = list(survs & SURVS)
        arcpy.AddWarning('Surveys not found in Region: ' + str(notIn))

    arcpy.AddMessage('Appending features')
    #Select from master SAPLYGON and copy to new gdb_p
    joined = '\',\''.join(surveys)
    parened = f"('{joined}')"
    q = f"AREASYMBOL IN {parened}"
    arcpy.MakeFeatureLayer_management(rtsd_sa_p, sa_lyr, q)
    arcpy.Append_management(sa_lyr, pr_p, 'NO_TEST')
    arcpy.CopyFeatures_management(sa_lyr, ltsd_sa_p)
    arcpy.MakeFeatureLayer_management(rtsd_mu_p, rtsd_mu_lyr, q)
    arcpy.CopyFeatures_management(rtsd_mu_lyr, ltsd_mu_p)
    #Check for overlaps
    if survs & projSurvs:
        arcpy.AddWarning(
            'These surveys are already in Project Record: '
            f'{(survs & projSurvs)}'
        )

    arcpy.AddMessage('Updating fields')
    fields = {f.name for f in arcpy.Describe(ltsd_mu_p).fields}
    arcpy.CalculateField_management(
        ltsd_mu_p, 'Acres', "!SHAPE.area@ACRES!", field_type='FLOAT')
    if 'AreaSub' not in fields:
        arcpy.management.AddField(ltsd_mu_p, 'AreaSub', 'SHORT')
    if 'orig_musym' not in fields:
        arcpy.management.AddField(
            ltsd_mu_p, 'orig_musym', 'TEXT', field_length=6, 
            field_alias='orig MUSYM'
        )
        arcpy.CalculateField_management(ltsd_mu_p, 'orig_musym', "!musym!")
    if 'MUNAME' not in fields:
        arcpy.management.AddField(
            ltsd_mu_p, 'MUNAME', 'TEXT', field_length=175, 
            field_alias='orig MUNAME'
        )
    if 'NATMUSYM' not in fields:
        arcpy.management.AddField(
            ltsd_mu_p, 'NATMUSYM', 'TEXT', field_length=6, 
            field_alias='orig NATMUSYM'
        )
    if 'MUKEY' not in fields:
        arcpy.management.AddField(
            ltsd_mu_p, 'MUKEY', 'TEXT', field_length=30, 
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
        with arcpy.da.UpdateCursor(ltsd_mu_p, fields) as uCur:
            for A, mu, muname, nat, mukey in uCur:
                # Amu = f"{A}_{mu}"
                if (A in legends) and (mu in legends[A]):
                    uCur.updateRow((A, mu) + legends[A][mu])
                else:
                    arcpy.AddWarning(f"Mapunit {A}: {mu} not found on SDA")
    # Option to create musym domains and aresymbol subtype
    if domain_b:
        arcpy.SetSubtypeField_management(ltsd_mu_p, 'AreaSub')
        arcpy.AddMessage('Creating Domains and subtypes')
        #Create orig_MUYSUM and update_MUSYM domains ONE FOR EACH SURVEY
        arcpy.CreateDomain_management(
            gdb_p, 'surveys', 'surveys', 'SHORT', 'CODED', 'DUPLICATE'
        )
        arcpy.CreateDomain_management(
            gdb_p, 'AreaSymbol',' Area Symbols', 'TEXT', 'CODED', 'DUPLICATE'
        )

        for i, A in enumerate(surveys):
            arcpy.AddCodedValueToDomain_management(gdb_p, 'surveys', i, A)
            arcpy.AddCodedValueToDomain_management(gdb_p, 'AreaSymbol', A, A)
            arcpy.AddSubtype_management(ltsd_mu_p, i, A)

            q = f"AREASYMBOL = '{A}'"
            arcpy.MakeFeatureLayer_management(ltsd_mu_p, ltsd_mu_lyr, q)
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
            ltsd_mu_p, 'AREASYMBOL', 'AreaSymbol'
        )
        arcpy.AssignDomainToField_management(ltsd_mu_p, 'AreaSub', 'surveys')
    
    arcpy.AddMessage('Creating Topology')
    #Create topology
    arcpy.CreateTopology_management(arcpy.env.workspace, topo_n, sr.XYTolerance)
    arcpy.AddFeatureClassToTopology_management(topo_n, ltsd_sa_p)
    arcpy.AddFeatureClassToTopology_management(topo_n, ltsd_mu_p)
    arcpy.AddRuleToTopology_management(
        topo_p, 'Must Not Overlap (Area)', ltsd_mu_p
    )
    arcpy.AddRuleToTopology_management(
        topo_p, 'MUST Not Have Gaps (Area)', ltsd_mu_p
    )
    arcpy.AddRuleToTopology_management(
        topo_p, 'Must Cover Each Other (Area-Area)', ltsd_mu_p, '', ltsd_sa_p
    )
    arcpy.ValidateTopology_management(topo_n)
    arcpy.Compact_management(gdb_p)

    #Enable Editor Tracking (under Fields)
    arcpy.AddMessage('Setting up Edit Tracking')
    arcpy.EnableEditorTracking_management(
        ltsd_mu_p, 'Creator', 'Creation_Date', 'Editor', 'Last_Edit_Date'
    )
    arcpy.EnableEditorTracking_management(
        ltsd_sa_p, 'Creator', 'Creation_Date', 'Editor', 'Last_Edit_Date',
        'ADD_FIELDS'
    )

    winsound.PlaySound(
        f'{script_p}/OhYeah.wav', winsound.SND_FILENAME | winsound.SND_NOWAIT
    )
except:
    arcpy.AddError("Unexpected error on line: " + 
                   str(sys.exc_info()[-1].tb_lineno))
    arcpy.AddError("\n" + str(sys.exc_info()[0]))
    arcpy.AddError("\n" + str(sys.exc_info()[1]))
