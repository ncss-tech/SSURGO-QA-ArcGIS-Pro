#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insert NATSYM and MUNAME Value
A tool for the SSURGO QA ArcGISPro arctoolbox

This tool will add the NASIS National Mapunti Symbol (NATSYM) and the SSURGO 
Mapunit Name (muname) to a user-provided spatial layer.  The NATSYM and MUNAME 
values arederived from Soil Data Access (SDA) using a couple of custom SQL 
queries written by Jason Nemecek, WI State Soil Scientist.  The query that is 
used depends on the fields in the input spatial layer.  The MUKEY field must be 
present.

In order to receive NATSYM and MUNAME values from SDA, it must be first be 
determined what fields are available.  If both AREASYMBOL and MUKEY are 
available then the following
SQL query will be used:

      'SELECT mapunit.mukey, nationalmusym, muname '\
      'FROM sacatalog ' \
      'INNER JOIN legend ON legend.areasymbol = sacatalog.areasymbol \
      'AND sacatalog.areasymbol IN (' + values + ')' \
      'INNER JOIN mapunit ON mapunit.lkey = legend.lkey'

If only MUKEY is available then the following SQL query will be used:
      SELECT m.mukey, m.nationalmusym, m.muname as natmusym from mapunit m 
      where mukey in (" + values + ")

Both queries return: ['mukey', 'natmusym','muname']

The tool will handle Shapefiles and Geodatabase feature classes.

@author: Alexander Stum
@author: Adolfo Diaz
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@created 2/21/2017
@modified 11/27/23
    @by: Alexnder Stum
@version: 1.1

# ---
Updated 11/27/2023 - Alexander Stum
- Removed functions AddMsgAndPring, errorMsg, and splitThousands
- Added functions pyError, arcpyError
- Modified findField function to use list comprehension to find key field
- Cleaned up formatting

# ---
Updated  3/23/2021 - Adolfo Diaz
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
never be
  used as independent library.
- Normal messages are no longer Warnings unnecessarily.
"""

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


def findField(lyr, ref_fld):
    """ Check table or featureclass to see if specified field exists
        If fully qualified name is found, return that name; otherwise return 
        False Set workspace before calling findField
        """

    try:
        ref_fld = ref_fld.upper()
        if arcpy.Exists(lyr):
            lyr_des = arcpy.Describe(lyr)
            fld = [f.name for f in lyr_des.fields 
                   if f.name.upper() == ref_fld]
            if fld:
                return fld[0]
            return False
        else:
            arcpy.AddMessage("\tInput layer not found")
            return False

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

## ================================================================================================================
def getUniqueValues(theInput,theField):
    """ This function creates a list of unique values from theInput using 
    theField as the source field.  If the source field is AREASYMBOL than the 
    list will be parsed into lists not exceeding 300 AREASYMBOL values.  If the 
    source field is MUKEY than the list will be parsed into lists not exceeding 
    1000 MUKEY values. This list will ultimately be passed over to an SDA query.
    """

    try:
        if not bRaster:
            featureCount = int(arcpy.GetCount_management(theInput).getOutput(0))
        else:
            featureCount = len(
                [row[0] for row in arcpy.da.SearchCursor(theInput, theField)]
            )

        # Inform the user of how the values are being compiled
        if bFGDBsapolygon:
            arcpy.AddMessage(
                f"\nCompiling a list of unique {theField} values from "
                f"{featureCount:,} polygons using SAPOLYGON feature class"
            )
        elif bFGDBmapunit:
            arcpy.AddMessage(
                f"\nCompiling a list of unique {theField} values from "
                f"{featureCount:,} polygons using mapunit table"
                )
        elif bRaster:
            arcpy.AddMessage(f"\nCompiling a list of unique {theField} values")
        else:
            arcpy.AddMessage(
                f"\nCompiling a list of unique {theField} values from "
                f"{featureCount:,} records"
                )

        # Unique value list
        valueList = list()

        # Iterate through all of the records in theInput to make a unique list
        arcpy.SetProgressor(
            "step", f"Compiling a list of unique {theField} values",
            0, featureCount, 1
        )
        if featureCount:
            with arcpy.da.SearchCursor(theInput, [theField]) as cur:
                for rec in cur:
                    if bAreaSym:
                        if not len(rec[0]) == 5:
                            arcpy.AddError(
                                f"\tf{rec[0]} is not a valid AREASYMBOL"
                            )
                            continue
                    if not rec[0] in valueList:
                        valueList.append(rec[0])

                    arcpy.SetProgressorPosition()
            del cur
            arcpy.ResetProgressor()
            arcpy.AddMessage(
                f"\tThere are {len(valueList):,} unique {theField} values"
            )
        else:
            arcpy.AddError(
                "\n\tThere are no features in layer.  Empty Geometry. EXITING")
            exit()
        if not len(valueList):
            arcpy.AddError(
                "\n\tThere were no" + theField + " values in layer. EXITING"
            )
            exit()

        # if number of Areasymbols exceed 300 than parse areasymbols
        # into lists containing no more than 300 areasymbols
        # MUKEY no more than 1000 values
        if bAreaSym:
            return parseValuesIntoLists(valueList,300)
        else:
            return parseValuesIntoLists(valueList)

    except arcpy.ExecuteError:
        arcpy.AddError(
            f"\nCould not retrieve list of unique values from {theField} field"
        )
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        exit()
    except:
        arcpy.AddError(
            f"\nCould not retrieve list of unique values from {theField} field"
        )
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        exit()


def parseValuesIntoLists(valueList,limit=1000):
    """ This function will parse values into manageable chunks that will be 
    sent to an SDaccess query.
    This function returns a list containing lists of values comprised of no 
    more than what the 'limit' is set to. Default Limit set to 1000, this will 
    be used if the value list is made up of MUKEYS.  Limit will be set to 300 
    if value list contains areasymbols
    """

    try:
        arcpy.SetProgressorLabel(
            "\nDetermining the number of requests to send to SDaccess Server"
        )

        i = 0 # Total Count
        j = 0 # Mukey count; resets whenever the 'limit' is reached.

        listOfValueStrings = list()  # List containing lists of values
        tempValueList = list()

        for value in valueList:
            i+=1
            j+=1
            tempValueList.append(str(value))

            # End of mukey list has been reached
            if i == len(valueList):
                listOfValueStrings.append(tempValueList)

            # End of mukey list NOT reached
            else:
                # max limit has been reached; reset tempValueList
                if j == limit:
                    listOfValueStrings.append(tempValueList)
                    tempValueList = []
                    j=0

        del i,j,tempValueList

        if not len(listOfValueStrings):
            arcpy.AddError("\tCould not Parse value list into manageable sets")
            exit()
        else:
            return listOfValueStrings

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        exit()
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        exit()

## ===================================================================================
def getNATMUSYM(listsOfValues, featureLayer):
    """POST request which uses urllib and JSON to send query to SDM Tabular 
    Service and returns data in JSON format.  Sends a list of values 
    (either MUKEYs or Areasymbols) and returns NATSYM and MUNAME values. 
    If MUKEYS are submitted a pair of values are returned [MUKEY,NATMUSYM].
    If areasymbols are submitted than a list of all of MUKEY,NATSYM
    pairs that pertain to that areasymbol are returned.
    Adds NATMUSYM and MUNAME field to inputFeature layer if not present and 
    populates.
    """

    try:
        arcpy.AddMessage(
            f"\nSubmitting {len(listsOfValues)} request(s) to Soil Data Access"
        )
        arcpy.SetProgressor(
            "step", "Submitting request(s) to Soil Data Access", 0,
            len(listsOfValues), 1
        )
        # Total Count of values
        iNumOfValues = 0
        iRequestNum = 1

        # master mukey:natmusym,muname dictionary
        natmusymDict = dict()

        # SDMaccess URL
        url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'

        # Iterate through lists of unique values to submit requests for natsym
        # Iterate through each list that has been parsed for no more than 
        # 1000 mukeys
        for valueList in listsOfValues:
            arcpy.SetProgressorLabel(
                f"Requesting NATSYM and MUNAME values for {len(valueList)} "
                f"{sourceField}(s). Request {iRequestNum} of "
                f"{len(listsOfValues)}"
            )

            iNumOfValues+=len(valueList)
            iRequestNum+=1

            # convert the list into a comma seperated string
            ## values = ",".join(valueList)
            values = str(valueList)[1:-1]

            # use this query if submitting request by AREASYMBOL
            if bAreaSym:
                sQuery = (
                    'SELECT mapunit.mukey, nationalmusym, muname '
                    'FROM sacatalog INNER JOIN legend ON legend.areasymbol '
                    '= sacatalog.areasymbol AND sacatalog.areasymbol IN '
                    f'({values}) '
                    'INNER JOIN mapunit ON mapunit.lkey = legend.lkey'
                )

            # use this query if submitting request by MUKEY
            else:
                sQuery = ("SELECT m.mukey, m.nationalmusym, m.muname as "
                          f"natmusym from mapunit m where mukey in ({values})")

            # Create request using JSON, return data as JSON
            dRequest = dict()
            dRequest["format"] = "JSON"
            dRequest["query"] = sQuery
            ##dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"
            jData = json.dumps(dRequest)

            # Send request to SDA Tabular service using urllib2 library
            # ArcPro Request
            jData = jData.encode('ascii')

            # Try connecting to SDaccess to read JSON response
            # First Attempt
            try:
                response = urllib.request.urlopen(url, jData)
            except:
                # Second Attempt
                try:
                    arcpy.AddMessage("\t2nd attempt at requesting data")
                    response = urllib.request.urlopen(url, jData)
                except:
                    # Last Attempt
                    try:
                        arcpy.AddMessage("\t3rd attempt at requesting data")
                        response = urllib.request.urlopen(url, jData)

                    except URLError as e:
                        arcpy.AddError("\n\n" + sQuery)
                        if hasattr(e, 'reason'):
                            arcpy.AddError(f"\n\tURL Error: {e.reason}")

                        elif hasattr(e, 'code'):
                            arcpy.AddError(
                                f"\n\t{e.msg} (errorcode {e.code})"
                            )

                        return False

                    except socket.timeout as e:
                        arcpy.AddError("\n\tServer Timeout Error")
                        return False
                    except socket.error as e:
                        arcpy.AddError(
                            f"\n\tNASIS Reports Website connection "
                            "failure"
                        )
                        return False

            jsonString = response.read()
            data = json.loads(jsonString)

            """ Sample Output:
                {u'Table': [[u'mukey', u'natmusym',u'muname'],
                [u'ColumnOrdinal=0,ColumnSize=4,NumericPrecision=10,NumericScale=255,ProviderType=Int,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt32,DataTypeName=int',
                 u'ColumnOrdinal=1,ColumnSize=6,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar'],
                [u'753571', u'2tjpl', u'Amery sandy loam, 6 to 12 percent slopes'],
                [u'753574', u'2szdz', u'Amery sandy loam, 1 to 6 percent slopes'],
                [u'2809844', u'2v3f0', u'Grayling sand, 12 to 30 percent slopes']]}"""

            # Nothing was returned from SDaccess
            if not "Table" in data:
                arcpy.AddError(
                    "\tWarning! NATMUSYM values were not returned for any of "
                    f"the {sourceField}  values.  Possibly OLD mukey values."
                )
                continue

            # Add the mukey:natmusym,muname Values to the master dictionary
            for pair in data["Table"]:
                natmusymDict[pair[0]] = (pair[1],pair[2])

            arcpy.SetProgressorPosition()
        arcpy.ResetProgressor()

        # Add NATMUSYM and MUNAME to the Feature Layer if not present
        arcpy.SetProgressorLabel(
            "Adding NATSYM and MUNAME fields if they don't exist"
        )
        if (
            not "muname" in 
            [f.name.lower() for f in arcpy.ListFields(featureLayer)]
        ):
            arcpy.AddField_management(
                featureLayer, 'MUNAME', 'TEXT', '#', '#', 175, 'Mapunit Name'
            )
            arcpy.AddMessage("Successfully Added Map Unit Name Field")

        if (
            not "natmusym" in 
            [f.name.lower() for f in arcpy.ListFields(featureLayer)]
        ):
            arcpy.AddField_management(
                featureLayer, 'NATMUSYM', 'TEXT', '#', '#', 23,
                'National MU Symbol'
            )
            arcpy.AddMessage("Successfully Added National MUSYM Field")

        if bRaster:
            mukeyField = sourceField
        else:
            mukeyField = findField(featureLayer,"MUKEY")

        # Add MUKEY Attribute Index to the Feature Layer if not present

        # Import NATSYM and MUSYM values into Feature Layer by MUKEY
        arcpy.SetProgressorLabel("Importing NATMUSYM and MUNAME values")
        arcpy.AddMessage("\nImporting NATMUSYM and MUNAME values")
        featureCount = int(arcpy.GetCount_management(featureLayer).getOutput(0))
        arcpy.SetProgressor(
            "step",
            "Importing NATMUSYM  and Mapunit Name Values into " 
            + os.path.basename(featureLayer) + " layer", 
            0, featureCount, 1
        )

        """ itereate through the feature records and update the 
            NATMUSYM and MUNAME field
            {'2809844': ('2v3f0', 'Grayling sand, 12 to 30 percent slopes'),
             '753571': ('2tjpl', 'Amery sandy loam, 6 to 12 percent slopes'),
             '753574': ('2szdz', 'Amery sandy loam, 1 to 6 percent slopes')}"""

        with arcpy.da.UpdateCursor(
            featureLayer, [mukeyField,'NATMUSYM','MUNAME']
        ) as cursor:

            for row in cursor:

                try:
                    mukey = str(row[0])
                    uNatmusym = natmusymDict[mukey][0]
                    uMuName = natmusymDict[mukey][1]
                    arcpy.SetProgressorLabel(
                        f"Importing Values: {mukey} : {uNatmusym}--" + uMuName
                    )

                    row[1] = uNatmusym
                    row[2] = uMuName
                    cursor.updateRow(row)

                    del uNatmusym,uMuName
                    arcpy.SetProgressorPosition()

                except:
                    arcpy.addError("\tInvalid MUKEY: " + mukey)
                    continue

        arcpy.ResetProgressor()

        arcpy.AddMessage(
            "\tSuccessfully populated 'NATMUSYM' and 'MUNAME' values for "
            f"{featureCount:,} records \n"
        )

        if bAreaSym:
            arcpy.AddMessage(
                f"\tThere are {len(natmusymDict):,} unique mapunits"
            )

        return True

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


# Import modules
import sys
import os
import arcpy
import traceback
import json
import socket
import urllib.request, urllib.parse, urllib.error
from urllib.request import Request, urlopen, URLError, HTTPError
from arcpy import env

if __name__ == '__main__':

    try:
        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        inputFeature = arcpy.GetParameterAsText(0)
        # SAPOLYGON will be used to summarize by Areasymbol
        bFGDBsapolygon = False
        # Areasymbol field is the source field
        bAreaSym = False
        # Mapunit table will be used to summarize by MUKEY (1 request)
        bFGDBmapunit = False
        # input is a raster
        bRaster = False
        source = inputFeature

        # Describe Data to determine the source field of the unique values
        theDesc = arcpy.da.Describe(inputFeature)
        theDataType = theDesc['dataType']
        theName = theDesc['name']
        theElementType = theDesc['dataElementType']
        # Input feature is a Shapefile or Raster
        if theElementType.lower() in ('deshapefile', 'derasterdataset'):
            # Make sure raster input has an attribute table
            if theElementType == 'DERasterDataset':
                bRaster = True
                if not arcpy.Raster(inputFeature).hasRAT:
                    arcpy.AddMessage(
                        "Building Raster Attribute Table to inventory fields"
                    )
                    try:
                        arcpy.BuildRasterAttributeTable_management(
                            inputFeature, "Overwrite"
                        )
                    except arcpy.ExecuteError:
                        arcpy.AddError(
                            "Failed to Build an Attribute table, Exiting!"
                        )
                        func = 'main 1'
                        arcpy.AddError(arcpyErr(func))
                        exit()
                    except:
                        arcpy.AddError(
                            "Failed to Build an Attribute table, Exiting!"
                        )
                        func = 'main 1'
                        arcpy.AddError(pyErr(func))
                        exit()
            if findField(inputFeature,"MUKEY"):
                sourceField = "MUKEY"

            elif findField(inputFeature,"AREASYMBOL"):
                sourceField = "AREASYMBOL"
                bAreaSym = True

            elif theElementType == 'DERasterDataset':
                rasterFlds = [f.name for f in arcpy.ListFields(inputFeature)]
                if 'Value' in rasterFlds:
                    sourceField = 'Value'
                    arcpy.AddWarning(
                        "Attempting to use Raster 'Value' field as MUKEY field"
                    )
                else:
                    arcpy.AddError(
                        "\t\"AREASYMBOL\" and \"MUKEY\" fields are missing "
                        f"from {theName} layer -- Need one or the other to "
                        "continue.  EXITING!"
                    )
                    exit()

            else:
                arcpy.AddError(
                    "\t\"AREASYMBOL\" and \"MUKEY\" fields are missing from "
                    f"{theName} layer -- Need one or the other to continue.  "
                    "EXITING!"
                )
                exit()
        # Input feature is a feature class
        elif theElementType.lower().find('featureclass') > -1:
            theFCpath = theDesc['catalogPath']
            theFGDBpath = theFCpath[:theFCpath.find(".gdb")+4]
            arcpy.env.workspace = theFGDBpath

            mukeyField = findField(theFCpath,"MUKEY")

            if not mukeyField:
                arcpy.AddError(
                    "\t\"MUKEY\" field is missing from feature class! - "
                    "EXITING!"
                )
                exit()

            # Use AREASYMBOL if available
            # RTSD Feature class with SAPOLYGON layer
            # summarize areasymbols from SAPOLYGON layer first.
            # This is the fastest method since it is the records
            if arcpy.ListFeatureClasses("SAPOLYGON", "Polygon"):
                bFGDBsapolygon = True
                source = theFGDBpath + os.sep + "SAPOLYGON"
                sourceField = "AREASYMBOL"
                bAreaSym = True

            # Regular Feature Class - NO SAPOLYGON layer
            # summarize AREASYMBOL from input feature class.
            # this method is the same as summarizing by MUKEY
            # but still preferred over MUKEY b/c of fewer
            # requests to SDA
            elif findField(inputFeature,"AREASYMBOL"):
                sourceField = "AREASYMBOL"
                bAreaSym = True

            # Use MUKEYS
            # Use mapunit table to collect MUKEYs.  This is
            # preferred way to summarize MUKEYs b/c of fewer
            # records.
            elif arcpy.ListTables("mapunit", "ALL"):
                bFGDBmapunit = True
                source = theFGDBpath + os.sep + "mapunit"
                sourceField = "MUKEY"
                bFGDBmapunit = True

            # mapunit table was not found - summarize MUKEYS from
            # input feature.  Least Ideal since it is the slowest.
            elif findField(inputFeature,"MUKEY"):
                sourceField = "MUKEY"
            else:
                arcpy.AddError(
                    "\t\"AREASYMBOL\" and \"MUKEY\" fields are missing from "
                    "feature class! -- Need one or the other to continue.  "
                    "EXITING!"
                )
                exit()

        # Input Feature data type not recognized
        else:
            arcpy.AddError("\nInvalid data type: " + theDataType.lower())
            exit()

        #  Get list of unique values from the specified source field
        uniqueValueList = getUniqueValues(source, sourceField)

        # Populate input Feature with NATMUSYM and MUNAME values
        if not getNATMUSYM(uniqueValueList, inputFeature):
            arcpy.AddError("\nFailed to update NATSYM field")

    except arcpy.ExecuteError:
        func = 'main 2'
        arcpy.AddError(arcpyErr(func))
    except:
        func = 'main 2'
        arcpy.AddError(pyErr(func))
