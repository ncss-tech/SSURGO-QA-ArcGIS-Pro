# QA_MultipartPolygons.py
# Created 11-05-2013
#
# Adapted from Vertex Report tool

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

# ==========================================================================================
# Updated  1/6/2020 - Adolfo Diaz
#
# - Updated and Tested for ArcGIS Pro 2.5.2 and python 3.6
# - All describe functions use the arcpy.da.Describe functionality.
# - All intermediate datasets are written to "in_memory" instead of written to a FGDB and
#   and later deleted.  This avoids having to check and delete intermediate data during every
#   execution.
# - All cursors were updated to arcpy.da
# - Added code to remove layers from an .aprx rather than simply deleting them
# - Updated AddMsgAndPrint to remove ArcGIS 10 boolean and gp function
# - Updated errorMsg() Traceback functions slightly changed for Python 3.6.
# - Added parallel processing factor environment
# - swithced from sys.exit() to exit()
# - All gp functions were translated to arcpy
# - Every function including main is in a try/except clause
# - Main code is wrapped in if __name__ == '__main__': even though script will never be
#   used as independent library.
# - Normal messages are no longer Warnings unnecessarily.


# ==============================================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:

        #print(msg)

        if severity == 0:
            arcpy.AddMessage(msg)

        elif severity == 1:
            arcpy.AddWarning(msg)

        elif severity == 2:
            arcpy.AddError("\n" + msg)

    except:
        errorMsg()
        pass

# ==============================================================================================================================
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

# ===================================================================================
def ProcessLayer(inLayer, areaSym):
    # Create a summary for each soil survey
    #
    # inLayer = selected featurelayer or featureclass that will be processed
    try:

        # number of multipart features
        iMultipart = 0

        fieldList = ["OID@","SHAPE@"]

        # where clause
        sql = '"AREASYMBOL" = ' + "'" + areaSym + "'"

        # List containing bad IDs
        polyList = list()
        desc = arcpy.Describe(inLayer)
        oidName = desc.OIDFieldName

        # Select polgyons with the current attribute value and process the geometry for each
        with arcpy.da.SearchCursor(inLayer, fieldList, sql) as sCursor:
            for row in sCursor:

                # Process a polygon record. row[1] is the same as feat or SHAPE
                fid, feat = row

                if not feat is None:
                    iPartCnt = feat.partCount

                    if iPartCnt > 1:
                        iMultipart += 1
                        polyList.append(fid)

                else:
                    AddMsgAndPrint("NULL geometry for polygon #" + str(fid),1)

        if iMultipart > 0:
            AddMsgAndPrint("\t" + areaSym + " has " + splitThousands(iMultipart) + " multipart polygons: " + '"' + oidName + '"' + " IN (" + str(polyList)[1:-1] + ")",1)

        else:
            AddMsgAndPrint("\n" + "\t" + areaSym + " has no multipart polygons")

        return iMultipart, polyList

    except:
        errorMsg()
        return -1, idList

# ===================================================================================
def splitThousands(someNumber):
    """will determine where to put a thousands seperator if one is needed. Input is
       an integer.  Integer with or without thousands seperator is returned."""

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber

# ===================================================================================
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed seconds
        eTotal = end - start

        # day = 86400 seconds
        # hour = 3600 seconds
        # minute = 60 seconds

        eMsg = ""

        # calculate elapsed days
        eDay1 = eTotal / 86400
        eDay2 = math.modf(eDay1)
        eDay = int(eDay2[1])
        eDayR = eDay2[0]

        if eDay > 1:
          eMsg = eMsg + str(eDay) + " days "
        elif eDay == 1:
          eMsg = eMsg + str(eDay) + " day "

        # Calculated elapsed hours
        eHour1 = eDayR * 24
        eHour2 = math.modf(eHour1)
        eHour = int(eHour2[1])
        eHourR = eHour2[0]

        if eDay > 0 or eHour > 0:
            if eHour > 1:
                eMsg = eMsg + str(eHour) + " hours "
            else:
                eMsg = eMsg + str(eHour) + " hour "

        # Calculate elapsed minutes
        eMinute1 = eHourR * 60
        eMinute2 = math.modf(eMinute1)
        eMinute = int(eMinute2[1])
        eMinuteR = eMinute2[0]

        if eDay > 0 or eHour > 0 or eMinute > 0:
            if eMinute > 1:
                eMsg = eMsg + str(eMinute) + " minutes inLayer"
            else:
                eMsg = eMsg + str(eMinute) + " minute "

        # Calculate elapsed secons
        eSeconds = "%.1f" % (eMinuteR * 60)

        if eSeconds == "1.00":
            eMsg = eMsg + eSeconds + " second "
        else:
            eMsg = eMsg + eSeconds + " seconds "

        return eMsg

    except:
        errorMsg()
        return ""

## ===================================================================================
import sys, string, os, re, locale, time, math, traceback, collections, arcpy
from arcpy import env

if __name__ == '__main__':

    try:
        # Set formatting for numbers
        #locale.setlocale(locale.LC_ALL, "")

        # Target Featureclass
        inLayer = arcpy.GetParameter(0)

        # Target surveys
        asList = arcpy.GetParameter(1)

        # survey id
        inFieldName = "AREASYMBOL"

        # Check out ArcInfo license for PolygonToLine
        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # Start timer
        #begin = time.time()
        #eMsg = elapsedTime(begin)

        # Setup: Get all required information from input layer
        #
        # Describe input layer
        desc = arcpy.Describe(inLayer)
        theDataType = desc.dataType.upper()
        theCatalogPath = desc.catalogPath

        if theDataType == "FEATURELAYER":
            # input layer is a FEATURELAYER, get featurelayer specific information
            fc = desc.catalogPath
            AddMsgAndPrint(" \nLooking for multipart polygons in featurelayer " + desc.name + "...", 0)

        elif theDataType in ["FEATURECLASS", "SHAPEFILE"]:
            # input layer is a featureclass, get featureclass specific information
            AddMsgAndPrint(" \nLooking for multipart polygons in featureclass " + desc.name + "...", 0)
            fc = inLayer

        # run process
        errorList = list()
        problemList = list() # List of Areasymbols with multipart features
        goodList = list()    # List of Areasymbols with no errors
        idList = list()      # List of Bad ID's

        for areaSym in asList:

            #saList = list()

            if theDataType == "FEATURELAYER":
                iMultiPart, saList = ProcessLayer(fc, areaSym)
                idList.extend(saList)

            elif theDataType in ["FEATURECLASS", "SHAPEFILE"]:
                iMultiPart, saList = ProcessLayer(inLayer, areaSym)
                idList.extend(saList)

            if iMultiPart == -1:
                errorList.append(areaSym)

            elif iMultiPart > 0:
                problemList.append(areaSym)

            else:
                goodList.append(areaSym)

        AddMsgAndPrint(str(idList))

        if len(problemList) > 0:
            AddMsgAndPrint("The following surveys have multipart polygons: " + ", ".join(problemList) + "\n",1)

            # Select the polygons that are multipart
            oidFld = [f.name for f in arcpy.ListFields(inLayer,"*","OID")][0]
            sql = oidFld + " IN (" + str(idList)[1:-1] + ")"

            if theDataType == "FEATURELAYER":
                arcpy.SelectLayerByAttribute_management(inLayer, "NEW_SELECTION", sql)
                iSel = int(arcpy.GetCount_management(inLayer).getOutput(0))

                if iSel == 1:
                    AddMsgAndPrint("\n" + "Selecting the polygon in the featurelayer that is a multipart" + "\n")
                else:
                    AddMsgAndPrint("\n" + "Selecting all " + splitThousands(iSel) + " polygons in the featurelayer that are multipart \n")

            else:
                inLayer = desc.name + " MultiPolygons"
                arcpy.MakeFeatureLayer_management(fc, inLayer, sql)

            stringOfIDs = [str(id) for id in idList]
            AddMsgAndPrint("The following " + oidFld + "'s have multipart features: (" + ", ".join(stringOfIDs) + ")" + "\n",1)

        if len(errorList) > 0:
            AddMsgAndPrint("The following surveys failed during testing: " + ", ".join(errorList) + "\n ", 1)

    except:
        errorMsg()
