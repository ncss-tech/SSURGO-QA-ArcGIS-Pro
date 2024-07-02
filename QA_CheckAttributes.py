# QA_CheckAttributes.py

# Author: Steve.Peaslee
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216

# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216

# ArcMap 10.1, arcpy
#
# Check all spatial AREASYMBOL and other specified attribute values for correct formatting
# Check all spatial AREASYMBOL values to confirm that they exist in Web Soil Survey
#
# Last Modified: 2/8/2017 to Convert the SOAP request to POST-REST request to SDaccess. -- AD
# Only 1 Post-rest request was needed.  TEST

# ==========================================================================================
# Upated 4/6/2108 by Adolfo Diaz
# converted dictionary keys "FORMAT" and "QUERY" to lower case in the JSON request.
# Also updated the tool to exclude non-SSURGO valid fields using the validation code.

# ==========================================================================================
# Updated  12/1/2020 - Adolfo Diaz
#
# - Updated and Tested for ArcGIS Pro 2.4.3 and python 3.6
# - Updated urllib2 to urllib, HTMLParser to html.parser and htmlentitydefs to html.entities
# - Python3 does not read the html code as a string but as a bytearray, so url read needs to
#   be converted to string with decode
# - Added code exit script if Mapunit Status or Update MUKEY Values options were not selected
# - All intermediate datasets are written to "in_memory" instead of written to a FGDB and
#   and later deleted.  This avoids having to check and delete intermediate data during every
#   execution.
# - All cursors were updated to arcpy.da
# - Describe functions were updated to describe.da
# - Updated print_exception function.  Traceback functions slightly changed for Python 3.6.
# - Added parallel processing factor environment
# - swithced from sys.exit() to exit()
# - Updated errorMsg function to handle exit() messages
# - Every function including main is in a try/except clause
# - Main code is wrapped in if __name__ == '__main__': even though script will never be
#   used as independent library.
# - Normal messages are no longer Warnings unnecessarily.
# - Removed bValidate - Not sure what the point of this is
# - Removed bValid - it is populated only once and never checked
# - Removed ascii encoding of Areasymbol values b/c it was throwing an HTTP error.
# - Completely rewrote the processLayer function (Now the checkSSURGOAttributesFormat function)

# ==========================================================================================
# Updated  5/16/2022 - Adolfo Diaz
#
# - There was an error with the checkSSURGOAttributeFormat function with NULLS in the
#   AREASYMBOL field.  Error occurred with NULL areasymbos so I updated code to find
#   Nulls to "val in [None, '', ' ', 'Null']:"

# ==============================================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:

        print(msg)
        #for string in msg.split('\n'):
            #Add a geoprocessing message (in case this is run as a tool)
        if severity == 0:
            arcpy.AddMessage(msg)

        elif severity == 1:
            arcpy.AddWarning(msg)

        elif severity == 2:
            arcpy.AddError("\n" + msg)

    except:
        pass

## ===================================================================================
def errorMsg():
    try:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = "\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[1] + "\n\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[-1]

        if theMsg.find("exit") > -1:
            AddMsgAndPrint("\n\n")
            pass
        else:
            AddMsgAndPrint(theMsg,2)

    except:
        AddMsgAndPrint("Unhandled error in unHandledException method", 2)
        pass

## ===================================================================================
def CheckAreasymbols(asList):
    # Query SDM (SD Access Service which requires internet access)
    # Compare local spatial areasymbols with those in Web Soil Survey
    # Please note that surveys with a new AREASYMBOL may exist in NASIS, but not
    # in Web Soil Survey. These will be flagged incorrectly.

    try:
        # Part of a SOAP request
        # import httplib
        # import xml.etree.cElementTree as ET
        # Handle choice list according to the first two parameter values

        # select by list of Areasymbols only
        sQuery = "SELECT AREASYMBOL FROM SASTATUSMAP WHERE AREASYMBOL IN (" + str(asList)[1:-1] + ") AND SAPUBSTATUSCODE = 2 ORDER BY AREASYMBOL"

        #theURL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest"
        url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'

        # Create request using JSON, return data as JSON
        dRequest = dict()
        dRequest["format"] = "JSON"
        dRequest["query"] = sQuery
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service using urllib library for ArcGIS Pro
        jData = jData.encode('ascii')
        resp = urllib.request.urlopen(url,jData)
        jsonString = resp.read()      # {"Table":[["MT605"],["MT610"],["MT612"]]}

        # Convert the returned JSON string into a Python dictionary.
        data = json.loads(jsonString)  # {u'Table': [[u'MT605'], [u'MT610'], [u'MT612']]}

        valList = list()
        #valList.append(data['Table'][0][0])

        for areaSym in data.get('Table'):
            valList.append(areaSym[0])

        if len(valList) > 0:
            # Got at least one match back from Soil Data Access
            # Loop through and compare to the original list from the spatial
            if len(asList) > len(valList):
                # Incomplete match, look at each to find the problem(s)
                missingList = [x for x in asList if not x in valList]
                AddMsgAndPrint(".\n\tThe following Areasymbol(s) do not match in Web Soil Survey: " + ", ".join(missingList), 1)
                return False

            else:
                # Number of areasymbols match, should be good
                AddMsgAndPrint(".\tAll areasymbol values in spatial data have a match in Web Soil Survey")
                return True

        else:
            # Failed to find a match for any surveys
            AddMsgAndPrint(".\nFailed to find a match for any of the input Areasymbols",2)
            return False

    except:
        errorMsg()
        return False

## ===================================================================================
def checkSSURGOAttributesFormat(inLayer, inFields):
    # inLayer = selected featurelayer or featureclass that will be processed
    #
    # length of 5
    # Check for [0:2] is text and [2:5] is integer
    # Check for uppercase
    # Check for spaces or other non-printable characters
    # string.letters, string.punctuation and string.digits.

    # valid format

    try:
        bAreaSymError = False
        bFldValueErrors = False

        validText = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        validNum = "0123456789"
        validMusym = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-+._"
        fieldList = ["OID@"]

        for fld in inFields:
            if fld not in fieldList:
                fieldList.append(fld.upper())

        badAreaSymbolList = list() # list of polygon ids that have erroneous areasymbol
        badFldValueList = list()   # list of polygon ids that have bad musyms
        asList = list()       # List of unique areasymbols

        iCnt = int(arcpy.GetCount_management(inLayer).getOutput(0))
        arcpy.SetProgressor("step", "Checking Attributes", 0, iCnt, 1)

        with arcpy.da.SearchCursor(inLayer, fieldList) as sCursor:

            for row in sCursor:
                fid = row[0]  # polygon ID

                # iterate through fields skipping the first field which is OID
                for i in range(1, len(fieldList)):

                    fldName = fieldList[i]
                    val = row[i]

                    # Handle Areasymbol differently because it has more specific criteria
                    if fldName == "AREASYMBOL":

                        # Areasymbol record is Null
                        if val in [None, '', ' ', 'Null']:
                            badAreaSymbolList.append([fid,"NULL"])

                        # Areasymbol is not 5 characters
                        elif not len(val) == 5:
                            if len(val.strip()) == 0:
                                badAreaSymbolList.append([fid,"NULL"])
                            else:
                                badAreaSymbolList.append([fid,val])
                            continue

                        # First 2 characters should be text if not assign Bad Format (BF)
                        elif not val[0] in validText or not val[1] in validText:
                            badAreaSymbolList.append([fid,val])

                        # Last 3 characters should be integer if not assign Bad Format (BF)
                        elif not val[2] in validNum or not val[3] in validNum or not val[3] in validNum:
                            badAreaSymbolList.append([fid,val])

                        # Must be uppercase if not assign wrong case (C)
                        elif val.upper() != val:
                            badAreaSymbolList.append([fid,val])

                        else:
                            # areasymbol value is correctly formatted
                            if not val in asList:
                                asList.append(val)

                    # Check other attribute (MUSYM or MUKEY)
                    # All we know is it is text field, don't know specifics
                    else:
                        # record is Null
                        if val in [None, '', ' ', 'Null'] or len(val) < 1:
                            badFldValueList.append([fid,fldName,"NULL"])

                        # Value cannot have spaces
                        elif len(val) > len(val.strip()):
                            badFldValueList.append([fid,fldName,val])

                        # All characters must be valid
                        else:
                            for char in val:
                                if not char in validMusym:
                                    #AddMsgAndPrint("\tBad MUSYM for polygon " + str(fid) + ":  '" + str(muSym) + "'")
                                    badFldValueList.append([fid,fldName,val])
                                    break

                arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()

        # Report errors with Areasymbol values
        if badAreaSymbolList:
            AddMsgAndPrint("\nThe following Polygon IDs have AREASYMBOL formatting errors:",2)
            AddMsgAndPrint("Polygon ID - Areasymbol",2)
            AddMsgAndPrint("----------   ----------",2)

            # Didn't wound up using
            col_width = max(len(str(word)) for error in badAreaSymbolList for word in error) + 3

            for row in badAreaSymbolList:
                AddMsgAndPrint("".join(str(word).ljust(13) for word in row),1)

        # Report errors with bad field values
        if badFldValueList:
            AddMsgAndPrint("\nThe following Polygon IDs have invalid characters:",2)
            AddMsgAndPrint("Polygon ID - Field Name - Attribute",2)
            AddMsgAndPrint("----------   ----------   ---------",2)
            for row in badFldValueList:
                AddMsgAndPrint("".join(str(word).ljust(13) for word in row),1)

        # Validate AREASYMBOLs against WSS if it was one of the fields
        # What about Initial Soil Surveys with a new AREASYMBOL?
        if "AREASYMBOL" in fieldList and len(asList):
            AddMsgAndPrint(".\nValidating " + str(len(asList)) + " Areasymbol(s) against Web Soil Survey")
            bValid = CheckAreasymbols(asList)

        if len(badAreaSymbolList) > 0 or len(badFldValueList) > 0:
            return False
        else:
            return True

    except:
        errorMsg()
        bFldValueErrors = False

## ===================================================================================
import sys, os, traceback, collections, arcpy, json, urllib.request, urllib.parse, urllib.error
from urllib.request import urlopen, URLError, HTTPError
from arcpy import env

if __name__ == '__main__':

    try:
        # Script parameters
        inLayer = arcpy.GetParameter(0)  # Target Layer
        inFields = arcpy.GetParameter(1) # Python list of fields

        arcpy.env.parallelProcessingFactor = "75%"

        # Setup: Get all required information from input layer
        # Describe input layer
        descInput = arcpy.da.Describe(inLayer)
        inputDT = descInput['dataType'].upper()
        theCatalogPath = descInput['catalogPath']
        inputName = descInput['name']

        if inputDT == "FEATURELAYER":
            # input layer is a FEATURELAYER, get featurelayer specific information
            fc = theCatalogPath

        elif inputDT in ["FEATURECLASS", "SHAPEFILE"]:
            # input layer is a featureclass, get featureclass specific information
            fc = inLayer

        AddMsgAndPrint(".\nLooking for attribute value problems in layer: " + inputName)
        bGood = checkSSURGOAttributesFormat(fc, inFields)

        if bGood:
            AddMsgAndPrint(".\nProcessing complete with no attribute formatting errors found")
        else:
            AddMsgAndPrint(".\nProcessing complete, but attribute formatting errors were found",2)

    except:
        errorMsg()
