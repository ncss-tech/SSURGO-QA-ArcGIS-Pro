#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create_Regional_Transactional_FGDB
A tool for the SSURGO QA ArcGISPro arctoolbox
Created on: 1/16/2014

@author: Alexander Stum
@author: Adolfo Diaz
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 11/03/2023
    @by: Alexnder Stum
@version: 2.2

# ---
Updated 11/03/2023 - Alexander Stum
- Instead of erroring out if a survey is not in the ssurgo source folder, it 
calls the query_download module and downloads that survey to the source folder.
- Added getDownloadString function to facilitate the query_download call. 
Requires sending a query to SDA to get SSA stage date to form url.

# ---
Updated 10/11/2023 - Alexander Stum
- Message that featdesc has been populated, even when importFeatdesc
returns an Error, fixed.
- Fixed bugs in createTopology function, requires explicit paths of features
when adding rules.
- Fixed references to xml files

# ---
Updated  09/30/2023 - Alexander Stum
- Rewrote getRegionalAreaSymbolList function to dynamically get soil survey 
legend assignment from a LIMs report validates whether valide downloads exist; 
and renamed it getSSARegionDict
- Added appendFeature function and removed all functionality in main related
to spatial sorting and appending features.
- Updated createFGDB function with new regional nomenclature, cleaned it up
- Added pyErr function to format error messages raised by python exceptions.
- Added arcpyErr function to format errors raised by arcpy exceptions.
- And removed errorMsg
- Rewrote updateAliasNames
- cleaned up createTopology function
- Added concurrently function to run functions in parallel
- Removed parseDatumAndProjection function as it is obsolete.
- Removed validateSSAs as that fuctionality is assumed by
- Removed splitThousands function and use f"{value:,}" instead
- Removed AddMsgAndPrint and replaced with arcpy AddMessage, AddWarning, and
AddError
- Replace function ImportFeatureFiles with importFeatdesc
getRegionalAreaSymbolDict

# ---
Updated  10/5/2021 - Adolfo Diaz
Updated XML workspaces to reflect new coordinate systems.

# ---
Updated  3/17/2020 - Adolfo Diaz
- Updated and Tested for ArcGIS Pro 2.5.2 and python 3.6
- All describe functions use the arcpy.da.Describe functionality.
- All intermediate datasets are written to "in_memory" instead of written to a 
FGDB and
  and later deleted.  This avoids having to check and delete intermediate data 
  during every
  execution.
- All cursors were updated to arcpy.da
- Added code to remove layers from an .aprx rather than simply deleting them
- Updated AddMsgAndPrint to remove ArcGIS 10 boolean and gp function
- Updated errorMsg() Traceback functions slightly changed for Python 3.6.
- Added parallel processing factor environment
- swithced from sys.exit() to exit()
- All gp functions were translated to arcpy
- Every function including main is in a try/except clause
- Main code is wrapped in if __name__ == '__main__': even though script will 
never be used as independent library.
- Normal messages are no longer Warnings unnecessarily.
"""

import arcpy
import sys
import os
import datetime
import re
import traceback
import csv
import requests
import json
import pandas as pd
from arcpy import env
from datetime import datetime
import concurrent.futures as cf
import itertools as it
from urllib.request import urlopen
from importlib import reload
import query_download
reload(query_download)


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
    
def concurrently(fn, max_concurrency, iterSets, constSets ):
    """
    Adapted from 
    https://github.com/alexwlchan/concurrently/blob/main/concurrently.py
    

    Generates (input, output) tuples as the calls to ``fn`` complete.

    See https://alexwlchan.net/2019/10/adventures-with-concurrent-futures/ 
    for an explanation of how this function works.
    
    Parameters
    ----------
    fn : function
        The function that it to be run in parallel.
        
    max_concurrency : int
        Maximum number of processes, parameter for itertools islice function.
        
    iterSets : list
        List of dictionaries that will be iterated through. The keys of the 
        dictionary must be the same for each dictionary and align with keywords 
        of the function.
        
    constSets : dict
        Dictionary of parameters that constant for each iteration of the 
        function ``fn``. Dictionary keys must align with function keywords.

    Yields
    ------
    A tuple with the original input parameters and the results from the called
    function ``fn``.
    """
    try:
        # Make sure we get a consistent iterator throughout, rather than
        # getting the first element repeatedly.
        # count = len(iterSets)
        fn_inputs = iter(iterSets)

        with cf.ThreadPoolExecutor() as executor:
            # initialize first set of processes
            futures = {
                executor.submit(fn, **params, **constSets): params
                for params in it.islice(fn_inputs, max_concurrency)
            }
            # Wait for a future to complete, returns sets of complete and 
            # incomplete futures
            while futures:
                done, _ = cf.wait(
                    futures, return_when = cf.FIRST_COMPLETED
                )

                for fut in done:
                    # once process is done clear it out, yield results 
                    # and params
                    original_input = futures.pop(fut)
                    output = fut.result()
                    del fut
                    yield original_input, output

                # Sends another set of processes equivalent in size to those 
                # just completed to executor to keep it at max_concurrency in 
                # the pool at a time, to keep memory consumption down.
                futures.update({
                    executor.submit(fn, **params, **constSets): params
                    for params in it.islice(fn_inputs, len(done))
                })
    except GeneratorExit:
        raise
        # arcpy.AddError("Need to do some clean up.")
        # yield 2, 'yup'
    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        msgs = arcpyErr(func)
        yield [2, msgs]
    except:
        func = sys._getframe(  ).f_code.co_name
        msgs = pyErr(func)
        yield [2, msgs]


def getDownloadString(ssa_l: list[str]) -> list[str]:
    """Generates a string with the soil survey Areasymbol and date of most 
    recent available from WSS. This string is needed to create url to 
    download the zipped SSURGO file. This function sends a query to SDA and
    requires and internest connection.

    Parameters
    ----------
    ssa_l : list[str]
        List of areasymbols

    Returns
    -------
    list[str]
        formatted strings with the Areasymbol, Date it was staged, survey area
        name. Returns and empty list if it fails
    """
    try:
        tail = " ORDER BY AREASYMBOL"
        trunk = ("SELECT AREASYMBOL, AREANAME, CONVERT(varchar(10), "
                "[SAVEREST], 126) AS SAVEREST FROM SASTATUSMAP WHERE "
                f"AREASYMBOL LIKE '{ssa_l[0]}'")
        for ssa in ssa_l[1:]:
            trunk += f" OR AREASYMBOL LIKE '{ssa}'"
        sQuery = trunk + tail

        url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'
        # Create request using JSON, return data as JSON
        dRequest = dict()
        dRequest["format"] = "JSON"
        dRequest["query"] = sQuery
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service using urllib2 library
        jData = jData.encode('ascii')
        response = urlopen(url, jData)
        jsonString = response.read()

        # Convert the returned JSON string into a Python dictionary.
        data = json.loads(jsonString)
        del jsonString, jData, response

        # Find data section (key='Table')
        valList = []
        if "Table" in data:
            # Data as a list of lists. All values come back as string.
            dataList = data["Table"]
            # Iterate through dataList, reformat to create the menu choicelist
            for rec in dataList:
                areasym, areaname, date = rec
                if not date is None:
                    date = date.split(" ")[0]
                else:
                    date = "None"
                valList.append(f"{areasym},  {date},  {areaname}")
        return valList
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return []


def getSSARegionList(ssurgo_p: str, region_opt: str) -> list[str]:
    """Creates a dictionary of Soil Survey Areas by specified Region.
    
    This function pulls a LIMs report to determine the current Regional
    ownership  per NASIS NASIS Site Name of official legends. It also considers 
    island area subdivisions of these Regions that have special projection
    considerations.

    Parameters
    ----------
    ssurgo_p : str
        Path of the directory with downloaded SSURGO datasets.
    region_opt : str
        The Region, a subdivision of the Soil and Plant Science Division 
        soil operations, for which to build an RTSD gdb for.

    Returns
    -------
    list[str]
        list the soil survey area symbols to be included in the RTSD gdb.
        Returns and empty list if it failed.
    """
    try:
        hi = ('HI',)
        pac = ('GU', 'FM', 'MH', 'MP', 'PW')
        sam = ('AS',)
        prv = ('PR', 'VI')

        if ':' in region_opt:
            region, region_sub = region_opt.split(':')
        else:
            region = region_opt
            region_sub = None
        # New regional: legacy region it was collasced to
        region_d = {
            'Alaska': 'MLRA13_Wasilla', 'Northeast': 'MLRA12_Amherst',
            'Northwest': 'MLRA04_Bozeman', 'North Central': 'MLRA10_StPaul',
            'Southeast': 'MLRA03_Raleigh', 'Southwest': 'MLRA02_Davis',
            'South Central': 'MLRA09_Temple'
            }
        # Lims report that provides official legend ownership
        url = ('https://nasis.sc.egov.usda.gov/NasisReportsWebSite/'
        'limsreport.aspx?report_name=WEB-Official%20Non-MLRA%20SSA')
        html = requests.get(url).content
        # Read table into pandas dataframe
        df = pd.read_html(html)[0]
        # NASIS Sites
        region_s = set(df['NASIS Site Name'])
        # Get current Region key
        region_n = region_s.intersection({region, region_d[region]}).pop()
        ssa_l = list(df['Area Symbol'][df['NASIS Site Name'] == region_n])
        # exclude 'MXNL001'
        if 'MXNL001' in ssa_l:
            ssa_l.remove('MXNL001')
        # Remove Islands sets from Southeast and Southwest or vice a versa
        # or Remove Islands and AK from CONUS
        if region_sub == ' HI':
            ssa_s = {s for s in ssa_l if s[0:2] in hi}
        elif region_sub == ' PacBasin':
            ssa_s = {s for s in ssa_l if s[0:2] in pac}
        elif region_sub == ' AmSamoa':
            ssa_s = {s for s in ssa_l if s[0:2] in sam}
        elif region == 'Southwest':
            ssa_s = {s for s in ssa_l if s[0:2] not in hi + pac + sam}
        elif region_sub == ' PRUSVI':
            ssa_s = {s for s in ssa_l if s[0:2] in prv}
        elif region == 'Southeast':
            ssa_s = {s for s in ssa_l if s[0:2] not in prv}
        elif region == 'CONUS':
            ssa_s = {s for s in ssa_l if s[0:2] not in hi + pac + sam + prv}
        elif region not in region_d:
            arcpy.AddError(
                f"{region_opt} does not seem to be a valid region choice"
                )
            return []
        # otherwise `ssa_l` is the same
        else:
            ssa_s = set(ssa_l)

        # Verify that all surveys have valid download in `ssurgo_p` directory
        ssa_dir = {d.name.removeprefix('soil_').upper()
                for d in os.scandir(ssurgo_p)
                if (d.is_dir()
                    and re.match(
                        r"[a-zA-Z]{2}[0-9]{3}",
                        d.name.removeprefix('soil_')
                        )
                    and os.path.exists(f"{d.path}/tabular")
                    and os.path.exists(f"{d.path}/spatial")
                    )}
        # keys = set(ssa_d.keys())
        not_downloaded = ssa_s - ssa_dir
        if not_downloaded:
            arcpy.AddWarning(
                f"Not all soil surveys for {region_opt} are "
                f"found in {ssurgo_p}.\nWill now download: {not_downloaded}"
            )
            ssa_info = getDownloadString(list(not_downloaded))
            complete = query_download.main([
                 ssurgo_p, ssa_info, False, True
            ])
            if not complete:
                arcpy.AddError('Not all surveys could be downloaded.')
                return []

        return list(ssa_s)
    
    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return []
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return []


def createFGDB(region_opt: str, output_p: str) -> str:
    """Create the RTSD File Geodatabase for Regional GIS Specialist

    Creates the RTSD File Geodatabase by importing an XML workspace schema 
    specific to the Region or sub-region
    Schema includes 2 feature datasets: FD_RTSD & Project Record. 
    Six feature classes are created within FD_RTSD the Feature Dataset.
    One feature class within the ProjectRecord Feature Dataset.

    Parameters
    ----------
    region_opt : str
        The Region, a subdivision of the Soil and Plant Science Division 
        soil operations, for which to build an RTSD gdb for.
    output_p : str
        The directory the new FGDB will be created in

    Returns
    -------
    str
        Name of the newly created FGDB, otherwise an empty string if it failed.
    """

    try:
        # New fiscal year if month October, November and December
        month = int(datetime.now().strftime("%m"))
        if month > 9 and month < 13:
            FY = f"FY{int(datetime.now().strftime('%y')) + 1}"
        else:
            FY = f"FY{datetime.now().strftime('%y')}"
        # {datetime.strftime(datetime.now(),'%Y%m%d%H%M%S')}

        newName = f"RTSD_{region_opt.replace(':', '_')}_{FY}.gdb"
        # Space ' ' in region_opt was removed in main
        # Alaska =  NAD83 / Alaska Albers (EPSG 3338)
        if region_opt == 'Alaska':
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_Alaska.xml")
        # Hawaii - Hawaii_Albers_Equal_Area_Conic WGS84
        elif region_opt == 'Southwest:HI':
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_Hawaii.xml")
        # PBSamoa - Hawaii_Albers_Equal_Area_Conic WGS84
        elif region_opt == "Southwest:AmSamoa":
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_Hawaii.xml")
        # Pacific Basin - Western Pacific Albers Equal Area Conic WGS84
        # Only PB630
        elif region_opt == "Southwest:PacBasin":
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_PacBasin.xml")
        # Puerto Rico US Virgin Islands - NAD83
        # Puerto Rico & Virgin Is. EPSG 32161
        elif region_opt == "Southeast:PRUSVI":
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_PRUSVI.xml")
        # CONUS - NAD83 / CONUS Albers (EPSG 5070)
        else:
            xmlFile = (os.path.dirname(sys.argv[0])
                       + "/RTSD_XMLWorkspace_CONUS.xml")

        # Return false if xml file is not found and delete targetGDB
        if not os.path.exists(xmlFile):
            arcpy.AddError(os.path.basename(xmlFile) + " was not found")
            return False

        # Create new FGDB with RTSD name
        fgdb_p = os.path.join(output_p, newName)
        # if Transactional Spatial Database exists delete it
        if arcpy.Exists(fgdb_p):
            arcpy.AddMessage(f"{newName} already exists, deleting")
            arcpy.Delete_management(fgdb_p)
        arcpy.CreateFileGDB_management(output_p, newName)
        arcpy.ImportXMLWorkspaceDocument_management(
            fgdb_p, xmlFile, "SCHEMA_ONLY", "DEFAULTS"
            )
        arcpy.AddMessage(f"Successfully Created RTSD File GDB: {fgdb_p}")

        return newName

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return ''
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return ''


def importFeatdesc(
        ssa_l: list[str],
        input_p: str,
        gdb_p: str
        ) -> str:
    """Runs through each SSURGO download folder and imports the rows into the 
    specified ``table`` . These tables have unique information from each 
    survey area.

    Parameters
    ----------
    ssa_l : list[str]
        List of soil surveys
    input_p : str
        Path to the SSRUGO downloads
    gdb_p : str
        Path of the SSURGO geodatabase

    Returns
    -------
    str
        An empty string if successful, otherwise and error message.
    """
    try:
        txt = txt = 'soilsf_t_{ssa}'
        cols = ['areasymbol', 'featsym', 'featname', 'featdesc']
        iCur = arcpy.da.InsertCursor(f'{gdb_p}/featdesc', cols)

        for ssa in ssa_l:
            txt_p = f"'{input_p}/{ssa.upper()}/spatial/{txt}.txt'"
            # in some instances // can create special charaters with eval
            txt_p = txt_p.replace('\\', '/')
            # convert latent f strings
            txt_p = eval("f" + txt_p)
            
            if not os.path.exists(txt_p):
                # Try SDM labeling
                txt_p = f"'{input_p}/soil_{ssa.lower()}/spatial/{txt}.txt'"
                # in some instances // can create special charaters with eval
                txt_p = txt_p.replace('\\', '/')
                # convert latent f strings
                txt_p = eval("f" + txt_p)
                if not os.path.exists(txt_p):
                    return f"{txt_p} does not exist"
            csvReader = csv.reader(
                open(txt_p, 'r'), 
                delimiter='|', 
                quotechar='"'
                )
            for row in csvReader:
                # replace empty sets with None; exclude feature key
                row = list(None if not v else v for v in row)[:-1]
                row.pop(1)
                iCur.insertRow(row)
        del iCur
        return ''

    except arcpy.ExecuteError:
        try:
            del iCur
        except:
            pass
        func = sys._getframe().f_code.co_name
        return arcpy.AddError(arcpyErr(func))
    except:
        try:
            del iCur
        except:
            pass
        func = sys._getframe().f_code.co_name
        return arcpy.AddError(pyErr(func))


def createTopology(fd_p: str) -> bool:
    """Creates a topolgy with the RTSD_FD Feature Dataset

    All official soil spatial features have topological considerations. This 
    tool properly sets those rules up.

    Parameters
    ----------
    fd_p : str
        Path to the RTSD_FD feature dataset where MUPOLYOGN, etc. are found.

    Returns
    -------
    bool
        Returns True if successful, otherwise False.
    """
    
    try:
        env.workspace = fd_p
        topo_n = "FD_RTSD_Topology"
        topo_p = f"{fd_p}/{topo_n}"
        arcpy.SetProgressor("step", "Creating Topology", 0, 3, 1)

        # Create New topology
        arcpy.SetProgressorLabel("Creating Topology")
        arcpy.CreateTopology_management(fd_p, topo_n, 0.2)

        arcpy.AddMessage(
            "\nCreated Topology: FD_RTSD_Topology at 0.2m cluster tolerance")
        arcpy.SetProgressorPosition()
        
        # Add feature classes to topology
        arcpy.SetProgressorLabel(
            "Creating Topology: Adding Feature Classes to Topology")
        arcpy.AddFeatureClassToTopology_management(
            topo_n, f"{fd_p}/MUPOLYGON", 1, 1)
        arcpy.AddFeatureClassToTopology_management(
            topo_n, f"{fd_p}/MUPOINT", 1, 1)
        arcpy.AddFeatureClassToTopology_management(
            topo_n, f"{fd_p}/MULINE", 1, 1)
        arcpy.AddFeatureClassToTopology_management(
            topo_n, f"{fd_p}/FEATPOINT", 1, 1)
        arcpy.AddFeatureClassToTopology_management(
            topo_n, f"{fd_p}/FEATLINE", 1, 1)
        arcpy.SetProgressorPosition()

        # Add Topology Rules
        arcpy.SetProgressorLabel("Creating Topology: Adding Rules to Topology")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Area)", f"{fd_p}/MUPOLYGON")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Gaps (Area)", f"{fd_p}/MUPOLYGON")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Intersect (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Overlap (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Pseudo-Nodes (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Intersect (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Single Part (Line)", f"{fd_p}/FEATLINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Disjoint (Point)", f"{fd_p}/FEATPOINT")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Disjoint (Point)", f"{fd_p}/MUPOINT")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Properly Inside (Point-Area)",
            f"{fd_p}/FEATPOINT", "", f"{fd_p}/MUPOLYGON","")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Overlap (Line)", f"{fd_p}/MULINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Intersect (Line)", f"{fd_p}/MULINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Overlap (Line)", f"{fd_p}/MULINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Have Pseudo-Nodes (Line)", f"{fd_p}/MULINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Not Self-Intersect (Line)", f"{fd_p}/MULINE")
        arcpy.AddRuleToTopology_management(
            topo_p, "Must Be Single Part (Line)", f"{fd_p}/MULINE")

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


def appendFeatures(fd_p: str, 
                   feat: tuple[str], 
                   input_f: str, 
                   ssa_l: list[str],
                   )-> dict[list[str]]:  
    """Appends SSURGO spatial features 
    
    Appends from each SSURGO download to the respective SSURGO feature. Note 
    that SAPOLYGON should be appeneded first to aid with spatial indexing by 
    setting append order from NW extent of survey set. While this function 
    could be run in parallel, the arcpy environmental setting for 
    Geographic Transformations is not honored and could not be set within the 
    indiviudal instances.

    Parameters
    ----------
    gdb : str
        The path of the new SSURGO geodatabase.
    feat : tuple(str)
        Contains two strings. The first string is the SSURGO feature name, the 
        second string is the shapefile name.
    input_f str
        Folder with the unzipped SSURGO donwloads.
    ssa_l : list[str]
        List of soil survey areas to be appended.

    Returns
    -------
    dict[list[str]]
        If successful retrun dictionary with the key 'surveys' and value with 
        the list of soil survey areas. When the input feature is 
        SAPOLYGON the list is spatially sorted. If unsuccessful, it 
        returns dictionary with the 'error' key with an error message.

    """
    try:
        feat_gdb = feat[0]
        feat_shp = feat[1]
        env.geographicTransformations = 'WGS_1984_(ITRF00)_To_NAD_1983'
        sf = ('PROJCS["NAD_1983_Contiguous_USA_Albers"'
              ',GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983"'
              ',SPHEROID["GRS_1980",6378137.0,298.257222101]],'
              'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
              'PROJECTION["Albers"],PARAMETER["False_Easting",0.0],'
              'PARAMETER["False_Northing",0.0],'
              'PARAMETER["Central_Meridian",-96.0],'
              'PARAMETER["Standard_Parallel_1",29.5],'
              'PARAMETER["Standard_Parallel_2",45.5],'
              'PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]')
        tran = 'WGS_1984_(ITRF00)_To_NAD_1983'
        # if SAPOLYGON, set up temp file to append a spatially indexed version
        if (feat_gdb != 'SAPOLYGON') or (len(ssa_l) == 1):
            feat_p = f"{fd_p}/{feat_gdb}"
        else:
            feat_p = "memory/SAPOLYGON"
        count = 0 # total count of features
        # feat_d = {} # path, count; for log file
        feat_l = []
        for ssa in ssa_l:
            shp = f"{input_f}/{ssa.upper()}/spatial/{feat_shp}_{ssa}.shp"
            if not os.path.exists(shp):
                # Try SDM labeling
                shp = f"{input_f}/soil_{ssa.lower()}/spatial/{feat_shp}_{ssa}.shp"
                if not os.path.exists(shp):
                    arcpy.AddError()
                    return {'error': f"{shp} does not exist."}
            cnt = int(arcpy.GetCount_management(shp).getOutput(0))
            count += cnt
            if cnt > 0:
                feat_l.append(shp)

        if feat_l:
            # arcpy.SetProgressorLabel(f"\tAppending features to {feat_gdb}")
            if feat_p != "memory/SAPOLYGON":
                with arcpy.EnvManager(
                    outputCoordinateSystem=sf,
                    geographicTransformations=tran
                ):
                    arcpy.Append_management(feat_l, feat_p, "NO_TEST")
                cnt = int(arcpy.GetCount_management(feat_p).getOutput(0))
            else:
                # Make virtual copy of template SAPOLYOGN to preserve metadata
                arcpy.CopyFeatures_management(f"{fd_p}/{feat_gdb}", feat_p)
                with arcpy.EnvManager(
                    outputCoordinateSystem=sf,
                    geographicTransformations=tran
                ):
                    arcpy.Append_management(feat_l, feat_p, "NO_TEST")
                feat_temp = feat_p
                feat_p = f"{fd_p}/{feat_gdb}"
                feat_desc = arcpy.Describe(feat_p)
                shp_fld = feat_desc.shapeFieldName
                # Spatially sort fron NW extent
                arcpy.management.Sort(feat_temp, feat_p, shp_fld, "UR")
                sCur = arcpy.da.SearchCursor(feat_p, "areasymbol", )
                sort_l = tuple(ssa for ssa, in sCur)
                del sCur
                arcpy.Delete_management(feat_temp)
                arcpy.Delete_management("memory")
                return {'surveys': sort_l}

            if cnt == count:
                arcpy.management.AddSpatialIndex(feat_p)
                arcpy.management.AddIndex(
                    feat_p,
                    "AREASYMBOL",
                    "Indx_MupolyAreasymbol"
                    )
                # arcpy.AddMessage(f"\t{cnt} features were appended to "
                #                  f"{feat_gdb}")
            else:
                msg = (f"\tOnly {cnt} of {count} features were "
                               f"appended to {feat_gdb}")
                return {'error': msg}
        
        elif (feat_gdb == 'SAPOLYGON') or (feat_gdb == 'MUPOLYGON'):
            msg = f"\tThere were no features appended to {feat_gdb}"
            return [msg]
        else: # No MUPOINT, MULINE, or special features
            # ---- LOG
            pass
        return {'surveys': ssa_l}
            
    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        msg = arcpyErr(func)
        return {'error': msg}
    except:
        func = sys._getframe().f_code.co_name
        msg = pyErr(func)
        return {'error': msg}


def updateAliasNames(region: str, gdb_p: str) -> bool:
    """Create and Region specific alieas for each spatial feature

    Parameters
    ----------
    region : str
        Region otption selected by user
    gdb_p : str
        Path of the RTSD geodatabase

    Returns
    -------
    bool
        Returns True if successful, otherwise False
    """
    try:
        region_d = {
            'Alaska': 'AK', 'Northest': 'NE',
            'Northwest': 'NW', 'North Central': 'NC',
            'Southeast': 'SE', 'Southeast: PRUSVI': 'PV', 'Southwest': 'SW',
            'Southwest: HI': 'HI', 'Southwest: AmSamoa':'AS',
            'Southwest: PacBasin': 'PB', 'South Central': 'SC'
            }
        aliasUpdate = 0
        if region == 'CONUS':
            alias_n = "CONUS"
        else:
            alias_n = "RTSD " + region_d[region]

        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/FEATLINE', alias_n + " - Special Feature Lines")
        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/FEATPOINT', alias_n + " - Special Feature Points")
        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/MUPOLYGON', alias_n + " - Mapunit Polygon")
        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/SAPOLYGON', alias_n + " - Survey Area Polygon")
        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/MULINE', alias_n + " - Mapunit Line")
        arcpy.AlterAliasName(
            f'{gdb_p}/FD_RTSD/MUPOINT', alias_n + " - Mapunit Point")
        arcpy.AlterAliasName(
            f'{gdb_p}/ProjectRecord/Project_Record',
            alias_n + " - Project Record")
        
        return True

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


def addAttributeIndex(table: str, fieldList: list[str], verbose=True) -> bool:
    """Creates attribute indices for all feature classes and tables

Attribute indexes can speed up attribute queries on feature classes and tables.
This function adds an attribute indices for the fields passed to the table that
is passed in.
  1) Table - 
  2) 
This function will make sure an existing index is not associated with that field.
Does not return anything.

    Parameters
    ----------
    table : _type_
        Full path to an existing table or feature class
    fieldList : _type_
        List of fields that exist in table
    verbose : bool, optional
        Whether to print out all messages, by default True

    Returns
    -------
    bool
        Returns True if successful, otherwise False.
    """
# 

    try:
        # Make sure table exists. - Just in case
        if not arcpy.Exists(table):
            arcpy.AddError(
                "Attribute index cannot be created for: "
                f"{os.path.basename(table)} TABLE DOES NOT EXIST")
            return False

        else:
            if verbose: 
                arcpy.AddMessage(
                    "Adding Indexes to Table: " + os.path.basename(table))

        # iterate through every field
        for fieldToIndex in fieldList:

            # Make sure field exists in table - Just in case
            if not len(arcpy.ListFields(table,"*" + fieldToIndex))>0:
                if verbose:
                    arcpy.AddError(
                        "\tAttribute index cannot be created for: "
                        f"{fieldToIndex}. FIELD DOES NOT EXIST")
                    continue

            # list of indexes (attribute and spatial) within the table that are
            # associated with the field or a field that has the field name in 
            # it. Important to inspect all associated fields b/c they could be 
            # using a differently named index
            existingIndexes = arcpy.ListIndexes(table,"*" + fieldToIndex)
            bFieldIndexExists = False

            # check existing indexes to see if fieldToIndex is already 
            # associated with an index
            if len(existingIndexes) > 0:

                # iterate through the existing indexes looking for a field match
                for index in existingIndexes:
                    associatedFlds = index.fields

                    # iterate through the fields associated with existing index.
                    # Should only be 1 field since multiple fields are not 
                    # allowed in a single FGDB.
                    for fld in associatedFlds:

                        # Field is already part of an existing index
                        if fld.name == fieldToIndex:
                            if verbose:
                                arcpy.AddWarning(
                                    f"\tAttribute Index for {fieldToIndex} "
                                    "field already exists")
                                bFieldIndexExists = True

                    # Field is already part of an existing index
                    # Proceed to next field
                    if bFieldIndexExists:
                        break

            # Attribute field index does not exist.  Add one.
            if not bFieldIndexExists:
                newIndex = "IDX_" + fieldToIndex

                # UNIQUE setting is not used in FGDBs - comment out
                arcpy.AddIndex_management(
                    table,fieldToIndex,newIndex,"#","ASCENDING")

                if verbose:
                    arcpy.AddMessage(
                        "\tSuccessfully added attribute index for "
                        f"{fieldToIndex}")

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
    v = '2.2'
    arcpy.AddMessage(f'Version: {v}')
    env.parallelProcessingFactor = "85%"
    env.overwriteOutput = True
    env.geographicTransformations = 'WGS_1984_(ITRF00)_To_NAD_1983'
    # --- Input Arguments
    # Parameter 0: Regional selection
    region_opt = arcpy.GetParameterAsText(0)

    # Parameter 1: Input Directory where the new FGDB will be created.
    output_p = arcpy.GetParameterAsText(1)

    # Parameter 2: Input Directory where the 
    # original SDM spatial and tabular data exist.
    ssurgo_p = arcpy.GetParameterAsText(2)

    startTime = datetime.now()

    try:
        # Generate dictionary {soil survey areas: directroy path}
        ssa_l = getSSARegionList(ssurgo_p, region_opt)
        # Exit if dictionary is empty
        if not ssa_l:
            exit()
        arcpy.AddMessage(f"{len(ssa_l)} surveys are in {region_opt}")

        # Create Empty Regional Transactional File Geodatabase
        RTSD_n = createFGDB(region_opt.replace(' ', ''), output_p)
        if not RTSD_n:
            exit()
        # Path to Regional FGDB
        gdb_p = f"{output_p}/{RTSD_n}"
        fd_p = f"{gdb_p}/FD_RTSD"

        # --- Import Feature descriptions
        msg = importFeatdesc(ssa_l, ssurgo_p, gdb_p)
        if msg:
            arcpy.AddError(msg)
        else:
            arcpy.AddMessage('\nThe featdesc table has been populated.')
        arcpy.SetProgressorLabel('Appending spatial features')
        # Path to feature dataset that contains SSURGO feature classes
        features = [('SAPOLYGON', 'soilsa_a'),
                    ('MUPOLYGON', 'soilmu_a'),
                    ('MULINE', 'soilmu_l'),
                    ('MUPOINT', 'soilmu_p'),
                    ('FEATLINE', 'soilsf_l'),
                    ('FEATPOINT', 'soilsf_p')]
        # for feat in features:
        # SAPOLYGON must be run first to sort `survey_l`
        output = appendFeatures(fd_p, features[0], ssurgo_p, ssa_l)
        if 'surveys' in output:
            survey_l = output['surveys']
            arcpy.AddMessage("\nSuccessfully appended SAPOLYGON")
        else:
            arcpy.AddError("Failed to append SAPOLYGON")
            arcpy.AddError(output['error'])
            exit()
        for feat in features[1:]:
            msg = appendFeatures(fd_p, feat, ssurgo_p, ssa_l)
            if 'surveys' in msg:
                arcpy.AddMessage(f"Successfully appended {feat[0]}")
            else:
                arcpy.AddError(f"Failed to append {feat[0]}")
                arcpy.AddError(msg['error'])
                exit()
        # paramSet = [{'feat': feat} for feat in features[1:]]
        # constSet = {'ssa_l': ssa_l, 'input_f': ssurgo_p, 'fd_p': fd_p}
        # threadCount = 4
        # for paramBack, output in concurrently(appendFeatures,
        #                                      threadCount,
        #                                      paramSet,
        #                                      constSet):
        #     try:
        #         if 'surveys' in output:
        #             arcpy.AddMessage(
        #                 f"Successfully appended {paramBack['feat'][0]}")
        #         else:
        #             arcpy.AddError(f"Failed to append {paramBack['feat'][0]}")
        #             arcpy.AddError(output['error'])
        #             exit()
        #     except GeneratorExit:
        #         pass

        # ---------------------------------------------------------------------------------------------------------- Setup Topology
        # Validate Topology with a cluster of 0.1 meters
        if createTopology(fd_p):
            arcpy.SetProgressorLabel("Validating Topology")
            arcpy.ValidateTopology_management(os.path.join(fd_p,"FD_RTSD_Topology"))
            arcpy.AddMessage("\tValidated Topology at 0.1 meters")

        else:
            arcpy.AddError(
                "\n\tFailed to Create Topology. Create Topology Manually")

        # --- Create Relationship class between project_record and SAPOLYGON
        arcpy.SetProgressorLabel("Creating Relationship Class between "
                                 "Project_Record & SAPOLYGON")
        pr_p = f"{gdb_p}/ProjectRecord/Project_Record"
        sa_p = f"{fd_p}/SAPOLYGON"
        rel_n = "xProjectRecord_SAPOLYGON"
        env.workspace = gdb_p
        arcpy.CreateRelationshipClass_management(
            pr_p, sa_p, rel_n, "SIMPLE", "> SAPOLYGON", "< Project_Record",
            "NONE", "ONE_TO_ONE", "NONE", "AREASYMBOL", "AREASYMBOL", "", "")
        arcpy.AddMessage("\nSuccessfully Created Relationship Class")

        arcpy.SetProgressorLabel("Compacting " + RTSD_n)
        arcpy.Compact_management(gdb_p)
        arcpy.AddMessage("\nSuccessfully Compacted " + RTSD_n)

        # ---  Add Aliases to Spatial Features
        if updateAliasNames(region_opt, gdb_p):
            arcpy.AddMessage(
                "\nSuccessfully updated Alias Names of the Spatial Features")
        else:
            arcpy.AddWarning(
                "\nFailed to update Alias Names of the Spatial Features")

        arcpy.AddMessage('***************************************************')
        # --- Enable Tracking
        for fc in features[1:]:
            fc_p = f"{fd_p}/{fc[0]}"
            arcpy.EnableEditorTracking_management(
                fc_p, 'Creator', 'Creation_Date', 'Editor',
                'Last_Edit_Date', 'ADD_FIELDS')
            count = int(arcpy.GetCount_management(fc_p)[0])
            arcpy.AddMessage(
                f"Total number of {fc[0]} features: "
                f"{count:,}")

        endTime = datetime.now()
        arcpy.AddMessage("\nTotal Time: " + str(endTime - startTime))

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))