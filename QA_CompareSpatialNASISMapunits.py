#! /usr/bin/env python3
# # -*- coding: utf-8 -*-
"""
Compare Spatial-NASIS Mapunits

compare MUSYM values in selected featurelayer with MUSYM
values from NASIS. Adapted from Kevin Godsey's VBA tool. Sends
query to the LIMS report server.

@author: Steve Peaslee
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 02/11/2026
    @by: Alexnder Stum
@version: 1.2.2

# -- Update 1.2.2; 02/11/2026
- ArcGIS Pro <3.6 can't work with multiline f-strings. Revised these instances
# -- Update 1.2.1; 02/10/2026
- reverted use of second LIMS report and clarified language about criteria
when zero map units returned.
# -- Update 1.2; 02/10/2026
- Removed function Number_Format in-liue of f-string functionality
- Removed printmsg function replaced with arcpy print out functions
- reformatted to 80 chars
- Added backup LIMS report with pandas read html
# ---
Update 1.1; 4/05/2025
- Added Edit session enable to update mukey of features involved with 
    topologies or relationships

================================================================================
11-18-2009 Steve Peaslee, NSSC

04-01-2010 - major revision to make the script compatible with NASIS 6.0
             Also works with a table such as MAPUNIT and LEGEND as an
             alternative to NASIS.
04-19-2010 - Bug fix. Incorrect parsing of the return from NASIS skipped
             the first mapunit.
04-30-2010 - Removed references to MUKEY from documentation
06-09-2010 - Fixed a few minor problems such as featurelayer/featureclass issues

06-19-2013 - Updating to use arcpy  and da cursors
06-24-2013 - Revamped html handling for NASIS
06-24-2013 - Added exclusion for NOTCOM. It is the only mismatch allowed for now.
09-06-2013 - Major performance increase. Moved spatial mapunit list to a single function
             that stores up front the entire mapunit list by areasymbol in a Python dictionary.
09-07-2013 - Altering operation to always run against the underlying featureclass to prevent any records being skipped

10-21-2013 - Using new NASIS report that allows specification of the different MUSTATUS types
10-31-2013 - Renamed this script from 'Get_Mukey.py'...

Updated  9/3/2020 - Adolfo Diaz

- Updated and Tested for ArcGIS Pro 2.4.2 and python 3.6
- Updated urllib2 to urllib, HTMLParser to html.parser and htmlentitydefs to html.entities
- Python3 does not read the html code as a string but as a bytearray, so url read needs to
  be converted to string with decode
- Added a check to see if MUKEY field exists when using the Update MUKEY values option.
  MUKEY field will automatically be added if it doesn't exist.
- Added code to set Mapunt Status to 'Correlated' if Update MUKEY values option is turned
  on and user did not specify Mapunit Status.
- Updated workspace and report folder if input is .shp.  Prior to this, output text files for
  shapefile inputs were written to 1 directory above.
- Added code exit script if Mapunit Status or Update MUKEY Values options were not selected
- All intermediate datasets are written to "in_memory" instead of written to a FGDB and
  and later deleted.  This avoids having to check and delete intermediate data during every
  execution.
- Removed setScratchWorkspace function since it is not needed for this tool.
- All cursors were updated to arcpy.da
- Describe functions were updated to describe.da
- Updated print_exception function.  Traceback functions slightly changed for Python 3.6.
- Added parallel processing factor environment
- swithced from sys.exit() to exit()
- Updated errorMsg function to handle exit() messages
- Every function including main is in a try/except clause
- Main code is wrapped in if __name__ == '__main__': even though script will never be
  used as independent library.
- Normal messages are no longer Warnings unnecessarily.
"""
v = '1.2.1'

from html.parser import HTMLParser
# import pandas as pd

# Import modules
import sys
import os
import arcpy
import traceback
from urllib.request import urlopen, URLError, HTTPError
from arcpy import env


## =============================================================================
def errorMsg():

    try:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = ("\t"
                  f"{traceback.format_exception(exc_type, exc_value, exc_traceback)[1]}"
                      f"\n\t{traceback.format_exception(exc_type, exc_value, exc_traceback)[-1]}")

        if theMsg.find("exit") > -1:
            arcpy.AddMessage("\n\n")
            pass
        else:
            arcpy.AddError(
                "\n----------------------------------- " \
                f"ERROR Start -----------------------------------\n{theMsg}"
                "/n-------------------------------------"
                "ERROR End -----------------------------------\n"
            )

    except:
        arcpy.AddMessage("Unhandled error in print_exception method")
        pass


class MyHTMLParser(HTMLParser):
    # create an HTMLParser class, mainly designed to get the data block within
    # the html returned by the NASIS Online report.

    # initialize the data block variable

    try:
        dataDict = dict()

        def handle_data(self, data):

            if str(data).strip():
                # load the data into a dictionary

                musym, mukey = data.split()
                musym = musym.strip()
                mukey = mukey.replace(",","").strip()
                self.dataDict[musym] = mukey

    except:
        errorMsg()

## =============================================================================
def NASIS_List(theAreasymbol, theURL, theParameters, muStatus):
    # Create a dictionary of NASIS MUSYM values
    # Sometimes having problem getting first mapunit (ex. Adda in IN071)

    try:
        # Problem with NASIS 6.0. 
        # It doesn't recognize the parameter for some unknown reason
        # Seems to work if we put the entire URL and 
        # Parameter into one string and set
        # the Parameter value to None
        #
        # Use muStatus to set the mapunit status option for the report
        # 1:provisional, 2:approved, 3:correlated, 4:additional
        # In theory, should only be #3 correlated for SSURGO downloads
        #
        theURL = theURL + theParameters + theAreasymbol + muStatus
        arcpy.AddMessage(theURL)
        resp = urlopen(theURL,None)
        thePage = resp.read().decode("utf8")

        parser = MyHTMLParser()
        parser.dataDict.clear()
        parser.feed(thePage)
        parser.close()
        dNASIS = parser.dataDict

        # if len(dNASIS) == 0:
        #     arcpy.AddWarning(
        #         "Trying another LIMS report which can " \
        #         "only consider correlated map units"
        #     )
        #     url2 = ("https://nasis.sc.egov.usda.gov/NasisReportsWebSite/"
        #             "limsreport.aspx?report_name="
        #             "get_mapunit_from_NASISWebReport&p_areasymbol=" + 
        #             theAreasymbol)
        #     arcpy.AddMessage(url2)
        #     tab = pd.read_html(url2, header=0)[0]
        #     dNASIS = dict(zip(tab['musym'], tab['lmapunitiid']))

        if len(dNASIS) == 0:
            arcpy.AddError(
                "\tRetrieved zero mapunit records from NASIS online report: "
                "Perhaps there are no map units that meet the selected criteria"
            )
        else:
            arcpy.AddMessage(
                f"\n\tRetrieved {len(dNASIS)} correlated mapunits from NASIS"
            )

        return dNASIS

    except IOError:
        errorMsg()
        return dict()

    except:
        errorMsg()
        return dict()

## =============================================================================
def CompareMusym(dNASIS, musymList, theAreasymbol, dBadSurveys):
    #
    # Compare database contents with layer contents
    #
    # Save errors to a dictionary: key=Areasymbol, SpatialCount, 
    # NASISCount, Note, NASISExtra, SpatialExtra
    #
    try:
        #
        # Compare database MUSYM values with Layer MUSYM values
        #
        missingLayer = list()

        for theMUSYM in dNASIS:
            if not theMUSYM in musymList:
                #AddMsgAndPrint("\tMissing map layer musym: '" + theMUSYM + "'")
                missingLayer.append(theMUSYM)

        musymCnt = len(missingLayer)

        if musymCnt > 0:
            arcpy.AddError(
                f"\tNASIS legend for {theAreasymbol} has {musymCnt} MUSYM "
                "value(s) not present in the spatial layer:"
            )

            if musymCnt > 1:
                arcpy.AddMessage("\t" + ", ".join(missingLayer))

            else:
                arcpy.AddMessage("\t" + missingLayer[0])

        else:
            arcpy.AddMessage(
                "\n\tAll MUSYM values in NASIS legend matched those in "
                "the spatial layer"
            )


        # Compare layer MUSYM values with NASIS legend, 
        # granting an exception for NOTCOM
        #
        missingNASIS = list()

        for theMUSYM in musymList:
            if not theMUSYM in dNASIS:
                if theMUSYM.strip() == "":
                    arcpy.AddError(
                        "\tInput spatial layer contains one or more features " \
                        "with a missing MUSYM value")
                    exit()
                # Remove this if NOTCOMs are NOT excluded from the check
                elif theMUSYM != "NOTCOM":                  
                    missingNASIS.append(theMUSYM)

        dbCnt = len(missingNASIS)

        if dbCnt > 0:
            arcpy.AddError(
                f"\tSpatial layer has {dbCnt} MUSYM "
                "value(s) not present in NASIS:"
            )

            if dbCnt > 1:
                arcpy.AddMessage("\t" + ", ".join(missingNASIS))

            else:
                arcpy.AddMessage("\t" + missingNASIS[0])

        else:
            arcpy.AddMessage(
                "\n\tAll MUSYM values in spatial layer match the NASIS legend "
                "for " + theAreasymbol
            )

        if dbCnt > 0 or musymCnt > 0:
            # Save errors to a dictionary
            dBadSurveys[theAreasymbol] =(
                len(musymList), len(dNASIS), "",", ".join(missingLayer), 
                ", ".join(missingNASIS) )
            return False, dBadSurveys

        else:
            return True, dBadSurveys

    except:
        errorMsg()
        dBadSurveys[theAreasymbol] = (0, 0, None, "","")
        return False, dBadSurveys

## =============================================================================
def UpdateMukeys(theInput, dNASIS, theAreasymbol, gdb):
    # Update layer MUKEY values for the specified AREASYMBOL value

    try:
        edit = arcpy.da.Editor(gdb)
        edit.startEditing(True, True)
        edit.startOperation()
        fieldList = ["MUSYM", "MUKEY"]
        queryField = arcpy.AddFieldDelimiters(theInput, "AREASYMBOL")
        sql = ""

        if theAreasymbol != "":
            sql = queryField + " = '" + theAreasymbol + "'"

        else:
            return False

        with arcpy.da.UpdateCursor (theInput, fieldList, sql) as outCursor:

            for outRow in outCursor:
                musym = outRow[0]
                # Remove this to if NOTCOMs are NOT excluded from the check
                if musym in dNASIS:             
                    outRow[1] = dNASIS[musym]
                    outCursor.updateRow(outRow)
        edit.stopOperation()
        edit.stopEditing(True)
        del edit
        return True

    except:
        del edit
        errorMsg()
        return False

## =============================================================================
def CreateMapunitDictionary(theInput, sql):

    try:
        # Load mapunit dictionary with entire contents of 
        # input layer or featureclass
        #
        dMapunits = dict()
        fieldList = ('AREASYMBOL','MUSYM')
        arcpy.AddMessage(
            "\nGetting mapunit information from spatial layer "
            f"({os.path.basename(theInput)})"
        )
        arcpy.SetProgressorLabel(
            "Getting mapunit information from spatial layer "
            f"({os.path.basename(theInput)})"
        )
        # 30 seconds faster when only running one out of many
        with arcpy.da.SearchCursor(theInput, fieldList, sql) as cursor:  

            for row in cursor:
                #areasym = row[0].encode('ascii').strip()
                #musym = row[1].encode('ascii').strip()

                areasym = row[0]
                musym = row[1]

                if areasym in dMapunits:
                    if not musym in dMapunits[areasym]:
                        dMapunits[areasym].append(musym)

                else:
                    dMapunits[areasym] = [musym]

        return dMapunits

    except:
        errorMsg()
        return dMapunits


## ====================================== Main Body ============================


if __name__ == '__main__':

    try:
        theInput = arcpy.GetParameterAsText(0)
        asValues = arcpy.GetParameter(1)    # value list containing Areasymbol
        bUpdate = arcpy.GetParameter(2)
        mx1 = arcpy.GetParameter(3)   # provisional
        mx2 = arcpy.GetParameter(4)   # approved
        mx3 = arcpy.GetParameter(5)   # correlated
        mx4 = arcpy.GetParameter(6)   # additional

        arcpy.AddMessage(f"Compare Spatial-NASIS Mapunits {v=}")
        # Use most of the cores on the machine where ever possible
        arcpy.env.parallelProcessingFactor = "75%"

        # Describe input layer and get workspace location
        desc = arcpy.da.Describe(theInput)
        theDataType = desc['dataType'].upper()
        theCatalogPath = desc['catalogPath']

        if theCatalogPath.endswith('.shp') or theDataType == "SHAPEFILE":
            ws = os.path.dirname(theCatalogPath)
            rptFolder = ws
            arcpy.AddMessage("\nFolder for input shapefile: " + ws)

        elif theDataType in ('FEATURELAYER','FEATURECLASS'):
            # input layer is a FEATURELAYER, 
            # get featurelayer specific information
            ws = os.path.dirname(theCatalogPath)
            wDesc = arcpy.da.Describe(ws)

            if wDesc['dataType'].upper() == "FEATUREDATASET":
                ws = os.path.dirname(ws)
            #     gdb = os.path.dirname(ws)
            # else:
            #     gdb = ws

            if theDataType == 'FEATURELAYER':
                theInput = theCatalogPath

            rptFolder = os.path.dirname(ws)
            arcpy.AddMessage("\nWorkspace for input featurelayer: " + ws)

        # Hardcode NASIS-LIMS Report Webservice for retrieving MUSYM and MUKEY 
        # values for a specified AREASYMBOL
        # New NASIS report that allows user to specify any 
        # of the MUSTATUS values
        theURL = (r"https://nasis.sc.egov.usda.gov/"
                  "NasisReportsWebSite/limsreport.aspx?")
        theParameters = "report_name=WEB-MapunitsAreaMustatus&area_sym="

        if mx1 is True:
            mx1 = "1"
        else:
            mx1 = "0"

        if mx2 is True:
            mx2 = "2"
        else:
            mx2 = "0"

        if mx3 is True:
            mx3 = "3"
        else:
            mx3 = "0"

        if mx4 is True:
            mx4 = "4"
        else:
            mx4 = "0"

        # Update MUKEY values option was checked and no mapunit status was 
        # selected default to Correlated mapunit status
        if mx1 == "0" and mx2 == "0" and mx3 == "0" and mx4 == "0":
            if bUpdate is True:
                mx3 = "3"
                arcpy.AddWarning(
                    "\nMUKEY values cannot be updated without a Mapunit Status"
                )
                arcpy.AddWarning("Defaulting to Correlated Mapunit status")
            else:
                arcpy.AddError(
                    "No options were selected.  User must select a "
                    "Mapunit Status. Exiting!"
                )
                exit()

        muStatus = "&mx1=" + mx1 + "&mx2=" + mx2 + "&mx3=" + mx3 + "&mx4=" + mx4

        # Create a list of surveys that fail the test
        badSurveys = list()

        # Create a dictionary with information for surveys that fail the test
        dBadSurveys = dict()

        # Create dictionary containing list of mapunits 
        # for each soil survey area (AREASYMBOL)
        asList = list()
        for theAreasymbol in asValues:
            asList.append("'" + theAreasymbol + "'")

        sql = '"AREASYMBOL" in (' + ','.join(asList) + ')'
        iNum = len(asList)

        dMapunits = CreateMapunitDictionary(theInput, sql)

        if len(dMapunits) == 0:
            arcpy.AddError("Failed to get mapunit information from " + theInput)
            exit()

        elif len(dMapunits) > 0:
            # open a report file to dump errors to
            rptFile = os.path.join(
                rptFolder, 
                f"QA_CompareSpatialNASISMapunit_{os.path.basename(ws.replace('.','_'))}.txt"
            )

            if arcpy.Exists(rptFile):
                os.remove(rptFile)

        arcpy.ResetProgressor()
        arcpy.SetProgressor(
            "step", 
            "Comparing NASIS information with spatial layer...",  0, (iNum -1),
            1
        )
        iCnt = 0

        # Boolean to indicate whether MUKEY field exists
        bMUKEYfldExist = False

        for theAreasymbol in asValues:
            # Process each soil survey identified by Areasymbol
            arcpy.AddMessage(
                f"\n{theAreasymbol}: Comparing spatial layer and NASIS legend" 
                "for this non-MLRA soil survey..."
            )
            arcpy.AddMessage(
                "---------------------------------------------------"
                "------------------------------------"
            )
            iCnt += 1
            arcpy.SetProgressorLabel(
                f"Checking survey {theAreasymbol.upper()}  "
                f"({iCnt}) of {asList})"
            )

            # Create dictionary of MUSYM values retrieved from input layer
            musymList = dMapunits[theAreasymbol]

            if len(musymList) > 0:
                arcpy.AddMessage(
                    f"\tFound {len(musymList)} mapunits in spatial layer"
                )

                # Create dictionary of MUSYM values retrieved from NASIS
                dNASIS = NASIS_List(
                    theAreasymbol, theURL, theParameters, muStatus
                )

                if len(dNASIS) > 0:

                    # Compare MUSYM values in each dictionary
                    # bGood - True if no legend mismatches found with NASIS; 
                    # False otherwise
                    bGood, dBadSurveys = CompareMusym(
                        dNASIS, musymList, theAreasymbol, dBadSurveys
                    )

                    if bGood == False:
                        badSurveys.append(theAreasymbol)

                    # If the AREASYMBOL legend has no conflicts and Update 
                    # MUKEYs is checked on proceed to update MUKEYs
                    if bUpdate:

                        # Check if MUKEY field exists; 
                        # Add field if it doesn't exist
                        if not bMUKEYfldExist:
                            flds = [f.name for f in desc['fields']]
                            if "MUKEY" in flds:
                                bMUKEYfldExist = True
                            else:
                                arcpy.AddField_management(
                                    theInput,
                                    "MUKEY",
                                    "TEXT","#","#","30",
                                    field_alias="Mapunit Key"
                                )
                                arcpy.AddMessage(
                                    "Successfully Added MUKEY field"
                                )
                                bMUKEYfldExist = True

                        if bGood:
                            if UpdateMukeys(
                                theInput, dNASIS, theAreasymbol, ws
                                ):
                                arcpy.AddMessage(
                                    "\n\tSuccessfully Updated MUKEY values"
                                )
                            else:
                                arcpy.AddMessage(
                                    "\n\tFailed to update MUKEY values"
                                )

                        else:
                            # mismatch between NASIS and the maplayer 
                            # MUSYM values! skip the update
                            arcpy.AddWarning(
                                "\nMUKEY update cannot occur until " \
                                "legend mismatch has been fixed"
                            )

                else:
                    arcpy.AddError(
                        "\tUnable to run comparison for " + theAreasymbol
                    )
                    badSurveys.append(theAreasymbol)
                    dBadSurveys[theAreasymbol] = (
                        len(musymList), 0, 
                        "Unable to retrieve mapunit information from NASIS",
                          "",""
                    )


            else:
                arcpy.AddMessage(
                    "\nFailed to get list of mapunits from input layer for "
                    + theAreasymbol
                )
                badSurveys.append(theAreasymbol)
                dBadSurveys[theAreasymbol] = (
                    0, 0, 
                    "Unable to retrieve mapunit information from spatial layer",
                      "",""
                    )

            arcpy.SetProgressorPosition()

        arcpy.SetProgressorLabel(
            f"Processing complete for all {asList} surveys"
        )

        if len(badSurveys) > 0:
            arcpy.AddMessage(
                "\n-----------------------------------------"
                "----------------------------------------------"
            )

            if len(badSurveys) == 1:
                arcpy.AddError(
                    "The following survey has problems that must be addressed: "
                    + badSurveys[0]
                )

            else:
                arcpy.AddError(
                    "The following surveys have problems that must be " \
                    "addressed:" " " + ", ".join(badSurveys)
                )

        if len(dBadSurveys) > 0:
            arcpy.AddMessage(
                "\nWriting summary info to tab-delimited text file: " + rptFile
            )

            # sort dictionary by Areasymbol
            sortedList = dBadSurveys

            with open(rptFile, 'w') as f:
                hdr = ("SurveyID\tSPATIAL_COUNT"
                       "\tNASIS_COUNT\tNOTES\tEXTRA_SPATIAL\tEXTRA_NASIS \n")
                f.write(hdr)

                #for survey, info in dBadSurveys.items():
                for survey in badSurveys:
                    info = dBadSurveys[survey]
                    errorLine = f"{survey}\t{info[0]}\t{info[1]}\t{info[2]}\t{info[4]}\t{info[3]}\n"
                    f.write(errorLine)

        arcpy.AddMessage(
            " \n" + os.path.basename(sys.argv[0]) + " script finished \n "
        )

    except:
        errorMsg()


