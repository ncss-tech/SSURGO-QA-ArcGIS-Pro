# ---------------------------------------------------------------------------
# QA_VertexCount.py.py
# Created on: May 29, 2013

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

# Input: Polygon layer
#
# Returns total vertice count for input layer

# ==========================================================================================
# Updated  1/27/2020 - Adolfo Diaz
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

# ===============================================================================================================
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

# ================================================================================================================
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
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        #locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        AddMsgAndPrint("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def ProcessPolygons(theInputLayer, bUseSelected):
    # Process either the selected set or the entire featureclass into a single set of summary statistics
    # bUseSelected determines whether the featurelayer or featureclass gets processed

    try:

        # Describe input layer
        desc = arcpy.da.Describe(theInputLayer)
        theDataType = desc['dataType'].lower()

        if theDataType == "featurelayer":
            theInputName = desc['nameString']

        else:
            theInputName = desc['baseName']

        theFC = desc['catalogPath']
        featureType = desc['shapeType'].lower()
        iVertCnt = 0
        AddMsgAndPrint(" \nProcessing input " + featureType + " " + theDataType.lower() + " '" + theInputName + "'")
        iParts = 0

        if bUseSelected:
            # Process input (featurelayer?)
            # open cursor with exploded geometry
            AddMsgAndPrint("If selected set or query definition is present, only those features will be processed")

            with arcpy.da.SearchCursor(theInputLayer, ["OID@","SHAPE@"], "","",False) as theCursor:
                for fid, feat in theCursor:

                    if not feat is None:
                        iVertCnt += feat.pointCount
                        iParts += feat.partCount

                    else:
                        AddMsgAndPrint("Empty geometry found for polygon #" + str(fid) + " \n ",2)
                        return -1


            AddMsgAndPrint(" \n" + Number_Format(iVertCnt, 0, True) + " vertices in featurelayer \n ")

        else:
            # Process all polygons using the source featureclass regardless of input datatype.
            # Don't really see a performance difference, but this way all features get counted.
            # Using 'exploded' geometry option for cursor

            with arcpy.da.SearchCursor(theFC, ["OID@","SHAPE@"], "","",False) as theCursor:
                for fid, feat in theCursor:

                    if not feat is None:
                      iVertCnt += feat.pointCount
                      iParts += feat.partCount

                    else:
                        AddMsgAndPrint("NULL geometry for polygon #" + str(fid),2)

            AddMsgAndPrint(" \n" + Number_Format(iVertCnt, 0, True) + " vertices present in the entire " + theDataType.lower() + " \n ")


        return iVertCnt

    except:
        errorMsg()
        return -1

## ===================================================================================
import sys, string, os, arcpy, locale, traceback, time, math, operator

if __name__ == '__main__':

    try:
        # Set formatting for numbers
        locale.setlocale(locale.LC_ALL, "")

        # Target FeatureLayer or Featureclass
        theInputLayer = arcpy.GetParameter(0)

        # Use all features or selected set? Boolean.
        bUseSelected = arcpy.GetParameter(1)

        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        iVertCnt = ProcessPolygons(theInputLayer, bUseSelected)

    except:
        AddMsgAndPrint("Error in Setup function",2)
        errorMsg()


