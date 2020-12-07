# QA_CommonPoints.py
# Created on: 05-09-2013

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
#
#
# Last modified: 10-31-2013
# Polygon tool used to identify locations where polygons with the same attribute intersect.
# By definition this will include polygons that self intersect by looping around.
#
# ==========================================================================================
# Updated  12/03/2020 - Adolfo Diaz
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
def splitThousands(someNumber):
    """will determine where to put a thousands seperator if one is needed. Input is
       an integer.  Integer with or without thousands seperator is returned."""

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    # Format a number according to locality and given places
    import locale

    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') #use locale.format for commafication

    except locale.Error:
        locale.setlocale(locale.LC_ALL, '') #set to default locale (works on windows)

    try:

        import locale


        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)

        return theNumber

    except:
        AddMsgAndPrint("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def MakeOutLayer(inLayer, sr, inField1, inField2, fldLength):
    # Create points shapefile containing error locations
    #
    try:
        # Set workspace to that of the input polygon featureclass
        desc = arcpy.da.Describe(inLayer)
        theCatalogPath = desc['catalogPath']

        loc = os.path.dirname(theCatalogPath)
        desc = arcpy.da.Describe(loc)
        inputDT = desc['dataType'].upper()

        if inputDT == "WORKSPACE":
            env.workspace = loc
            ext = ""

        elif inputDT == "FEATUREDATASET":
            env.workspace = os.path.dirname(loc)
            ext = ""

        elif inputDT == "FOLDER":
            env.workspace = loc
            ext = ".shp"

        else:
            AddMsgAndPrint(" \nError. " + loc + " is a " + inputDT + " datatype", 2)
            return ""

        # Use input field names to create output featureclass name
        if ext == ".dbf":
            newFld1 = arcpy.ParseFieldName(inField1).split(",")[3].strip()[0:10]

        else:
            newFld1 = arcpy.ParseFieldName(inField1).split(",")[3].strip()

        if inField2 != "":
            if ext == ".dbf":
                newFld2 = arcpy.ParseFieldName(inField2).split(",")[3].strip()[0:10]

            else:
                newFld2 = arcpy.ParseFieldName(inField2).split(",")[3].strip()

            outLayer = "QA_Common_Points_" + newFld1 + "_" + newFld2 + ext

        else:
            outLayer = "QA_Common_Points_" + newFld1 + ext

        # clean up previous runs
        if arcpy.Exists(outLayer):
            arcpy.Delete_management(outLayer)

        AddMsgAndPrint("\nOutput featureclass: " + outLayer + " in " + env.workspace + " " + inputDT.lower())

        # Create output point featureclass
        arcpy.CreateFeatureclass_management(env.workspace, outLayer, "POINT", "", "DISABLED", "DISABLED", sr)

        if not arcpy.Exists(os.path.join(env.workspace, outLayer)):
            return "",""

        else:
            # create the appropriate attribute field in the common points featureclass
            #
            # begin by getting all of the original field properties
            theField = arcpy.ListFields(theCatalogPath, newFld1 + "*")[0] # get the input polygon field object
            fieldAlias = theField.aliasName
            fieldType = "TEXT"
            fieldScale = ""
            fieldPrecision = ""
            arcpy.AddField_management(os.path.join(env.workspace, outLayer), newFld1, fieldType, fieldPrecision, fieldScale, fldLength, fieldAlias)

            # Add new field to track status of each point
            arcpy.AddField_management(os.path.join(env.workspace, outLayer), "Status", "TEXT", "", "", 10, "Status")

            return outLayer, newFld1

    except:
        errorMsg()
        return "",""

# ==============================================================================================================================
def AddLayerToArcGISPro(inLayer,lyrxPath):

    def UpdateLyrxSymbology(lyrxObj):

        sym = lyrxObj.symbology

        if sym.renderer.type == 'UniqueValueRenderer':
            sym.updateRenderer('UniqueValueRenderer')

            # This is the field used to render the symbology i.e. [hydgrp]
            rendererFld = sym.renderer.fields

            # These are the values found in the FC being symbolized
            uniqueValues = list(set([row[0] for row in arcpy.da.SearchCursor(ssurgoFC,rendererFld)]))

            # Get a list of unique Values in the symbology renderer
            uniqueRendererValues = list()
            for grp in sym.renderer.groups:
                for itm in grp.items:
                    uniqueRendererValues.append(itm.values[0][0])

            # remove symbology values that are not present in the FC
            for val in uniqueValues:
                if val in uniqueRendererValues:
                    uniqueRendererValues.remove(val)

            if len(uniqueRendererValues) > 0:
                for val in uniqueRendererValues:
                    sym.renderer.removeValues({rendererFld[0]: [val]})
                    lyrxObj.symbology = sym
    # ------------------------------------------------------------------
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")

        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in datasetsBaseName:
                    maps.removeLayer(lyr)

            if arcpy.Exists(lyrxPath):
                lyrxObject = arcpy.mp.LayerFile(lyrxPath).listLayers()[0]  # create a layer object

                # Connection Property Dictionary
                # {'dataset': 'SSURGO_WCT',
                #  'workspace_factory': 'File Geodatabase',
                #  'connection_info': {'database': 'E:\\python_scripts\\GitHub\\SSURGO_WCT\\Wetland_Workspace.gdb'}}
                lyrxConnectProperties = lyrxObject.connectionProperties

                # update CP dictionary database and dataset keys
                lyrxConnectProperties['connection_info']['database'] = os.path.dirname(inLayer)
                lyrxConnectProperties['dataset'] = os.path.basename(inLayer)
                lyrxObject.updateConnectionProperties(lyrxObject.connectionProperties,lyrxConnectProperties)

            else:
                AddMsgAndPrint(lyrxPath + " is missing",1)

            # 'SSURGO Layers' group layer object
            groupLayerPath = os.path.join(scriptPath,r'SSURGO_WCT_EmptySSURGOGroupLayer.lyrx')
            groupLayerObject = arcpy.mp.LayerFile(groupLayerPath).listLayers()[0]
            groupLayerName = groupLayerObject.name  # 'SSURGO Layers'

            # Boolean to determine if 'SSURGO Layers' group exists in ArcGIS Pro Session
            bGroupLayerExists = False
            bAddedLyrxFilesToPro = False

            # This is the map object where the lyrx files were added to
            mapObject = ""

            # G
            for map in aprx.listMaps():
                for mapLyr in map.listLayers():

                    # 'SSURGO Layers' group exists in Pro Session
                    # Add the layers in lyrxToAddToArcPro list to ArcPro
                    if mapLyr.name == groupLayerName and mapLyr.isGroupLayer:
                        bGroupLayerExists = True
                        mapObject = map

                        for lyrx in lyrxToAddToArcPro:
                            map.addLayerToGroup(mapLyr,lyrx)
                            bAddedLyrxFilesToPro = True
                            AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)
                break

            # Get existing group layer object
            if not bGroupLayerExists:

                # Add group layer to ArcGIS Pro Session
                aprxMap = aprx.activeMap
                mapObject = aprxMap
                aprxMap.addLayer(groupLayerObject, 'TOP')

                # Get added group layer
                mapGroupLayer = [lyr for lyr in aprxMap.listLayers(groupLayerName)][0]

                # 'SSURGO Layers' group exists in Pro Session
                # Add the layers in lyrxToAddToArcPro list to ArcPro
                for lyrx in lyrxToAddToArcPro:
                    map.addLayerToGroup(mapGroupLayer,lyrx)
                    bAddedLyrxFilesToPro = True
                    AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)

            # Update symbology
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            for lyr in mapObject.listLayers():

                # This is the 'SSURGO Layers' Group
                # iterate through the nested layers and up
                # the symbology
                if lyr.name == groupLayerName and lyr.isGroupLayer:
                    for newLayer in lyr.listLayers():
                        UpdateLyrxSymbology(newLayer)

    except:
        errorMsg()
        AddMsgAndPrint("Couldn't Add Layers to your ArcGIS Pro Session",1)
        pass

## ===================================================================================
# Import system modules
import os, sys, traceback, collections, re
import arcpy
from arcpy import env

if __name__ == '__main__':
    try:

        inLayer = arcpy.GetParameterAsText(0)  # single polygon featurelayer as input parameter
        inField1 = arcpy.GetParameterAsText(1) # attribute column used in selection
        inField2 = arcpy.GetParameterAsText(2) # secondary attribute column (usually AREASYMBOL)

        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # open da searchcursor on featurelayer
        flds = ["OID@","SHAPE@"]
        dDups = dict()

        iSelection = int(arcpy.GetCount_management(inLayer).getOutput(0))

        # define output featureclass
        desc = arcpy.da.Describe(inLayer)
        inputDT = desc['dataType'].upper()
        sr = desc['spatialReference']
        env.workspace = os.path.dirname(desc['catalogPath'])

        # input layer needs to be a featurelayer. If it is a featureclass, do a switch.
        if inputDT == "FEATURECLASS":
            # swap out the input featureclass for a new featurelayer based upon that featureclass
            inLayer = desc['name'] + " Layer"
            AddMsgAndPrint(" \nCreating new featurelayer named: " + inLayer)
            inputFC = desc['catalogPath']
            arcpy.MakeFeatureLayer_management(inputFC, inLayer)

        elif inputDT == "FEATURELAYER":
            inputName = desc['name']
            inputFC = desc['catalogPath']

        # Use a searchcursor to create a list of unique values for the specified input field or column
        AddMsgAndPrint("\nGetting unique values for " + inField1 + "...")

        # get the first input field object
        #chkFields = arcpy.ListFields(inputFC)
        chkFields = arcpy.ListFields(inLayer)

        for fld in chkFields:
            fldLength = 0

            if fld.name.upper() == inField1.upper():
                fld1Name = fld.name
                fld1NameU = fld.baseName
                fldLength = fld.length
                #AddMsgAndPrint("Getting length for " + fld1Name + " length: " + str(fldLength))

        # get the optional second input field object
        if inField2 != "":
            for fld in chkFields:

                if fld.name.upper() == inField2.upper():
                    fld2Name = fld.name
                    fld2NameU = fld.baseName
                    fldLength += fld.length
                    #AddMsgAndPrint("Getting total length for both fields " + fld2Name + ", " + fld1Name + " length: " + str(fldLength))

        else:
            fld2Name = ""
            fld2NameU = ""

        # Create list of values
        fldList = [fld1Name]

        if inField2 == "":
            valList = [row[0] for row in arcpy.da.SearchCursor(inLayer, fldList)]

        else:
            fldList = [fld2Name, fld1Name]
            valList = [row[0] + ":" + row[1] for row in arcpy.da.SearchCursor(inLayer, fldList)]

        valUnique = set(valList)   # remove duplicate attribute values
        valList = list(valUnique)
        valList.sort()    # sort the list to control the processing order, this is not really necessary
        AddMsgAndPrint("\nFound " + splitThousands(len(valList)) + " unique values")
        iVals = len(valList)

        # Process records using a series of search cursors while tracking progress
        arcpy.SetProgressorLabel("Reading polygon geometry...")
        arcpy.SetProgressor("step", "Reading polygon geometry...",  0, iVals, 1)
        AddMsgAndPrint("\nProcessing " + splitThousands(iSelection) + " polygons in '" + inLayer + "'")

        iCnt = 0

        # Create a selection on the input featurelayer for each unique value
        for val in valList:
            #arcpy.SetProgressorLabel("Reading polygon geometry for '" + str(val) + "'...")

            if inField2 != "":
                val1, val2 = val.split(":")
                theSQL = arcpy.AddFieldDelimiters(inLayer, inField1) + " = '" + val2 + "' AND " + arcpy.AddFieldDelimiters(inLayer, inField2) + " = '" + val1 + "'" # create SQL for each value

            else:
                theSQL = arcpy.AddFieldDelimiters(inLayer, inField1) + " = '" + val + "'" # create SQL for each value

            pntList = []  # clear point list for the new value

            with arcpy.da.SearchCursor(inLayer, flds, theSQL) as cursor:
                for row in cursor:

                    for part in row[1]:

                        # look for duplicate points within each polygon part
                        bRing = True  # helps prevent from-node from being counted as a duplicate of to-node

                        for pnt in part:
                            if pnt:
                                if not bRing:
                                    # add vertice or to-node coordinates to list
                                    pntList.append((pnt.X,pnt.Y))

                                bRing = False

                            else:
                                # interior ring encountered
                                ring = pntList.pop()  # removes first node from list
                                bRing = True  # prevents island from-node from being identified as a duplicate of the to-node

                # get duplicate coordinate pairs within the list of vertices for the current attribute value
                dupList = [x for x, y in collections.Counter(pntList).items() if y > 1]

                if len(dupList) > 0:
                    # if duplicate vertices are found in this polygon, add the list to the dictionary.
                    # dictionary key is the attribute value
                    dDups[val] = dupList
                    iCnt += len(dupList)   # keep track of the total number of common-points

                    if val == " ":
                        AddMsgAndPrint(" \n\tFound common points for " + inField1 + ":  <NULL>")

                    else:
                        AddMsgAndPrint(" \n\tFound common points for " + inField1 + ":  '" + val + "'")

                    arcpy.SetProgressorLabel("Reading polygon geometry ( flagged " + splitThousands(iCnt) + " locations )...")

            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()  # completely finished reading all polygon geometry

        # if common-points were found, create a point shapefile containing the attribute value for each point
        #
        if len(dDups) > 0:
            AddMsgAndPrint("Total of " + splitThousands(iCnt) + " 'common points' found in " + inLayer, 2)

            # create output points layer to store common-point locations
            outLayer, newFld1 =  MakeOutLayer(inLayer, sr, inField1, inField2, fldLength)

            if outLayer == "":
                AddMsgAndPrint("Failed to create common-points layer",2)
                exit()

            # Process records using cursor, track progress
            arcpy.SetProgressorLabel("Opening output featureclass...")
            arcpy.SetProgressor("step", "Writing point geometry..." , 0, iCnt, 1)

            # open new output points featureclass and add common point locations
            with arcpy.da.InsertCursor(outLayer, ["SHAPE@XY", newFld1]) as cursor:
                # for each value that has a reported common-point, get the list of coordinates from
                # the dDups dictionary and write to the output Common_Points featureclass
                for val in dDups.keys():

                    for coords in dDups[val]:
                        cursor.insertRow([coords, val]) # write both geometry and the single attribute value to the output layer
                        arcpy.SetProgressorPosition()

            arcpy.ResetProgressor()
            arcpy.SetProgressorLabel("Process complete...")

            try:
                AddMsgAndPrint("A")
                AddMsgAndPrint(os.path.join(env.workspace,outLayer))
                # if this is ArcMap and if geoprocessing setting automatically adds layer, then
                # import symbology from layer fill
                arcpy.env.addOutputsToMap = True
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                aprxMap = aprx.listMaps()[0]

                layerPath = os.path.dirname(__file__)
                layerFile = os.path.join(layerPath,"GreenDot.lyr")
                AddMsgAndPrint(layerFile)

                if fld2Name != "":
                    outLayerName = "QA Common Points (" + fld2NameU.title() + ":" + fld1NameU.title() + ")"

                else:
                    outLayerName = "QA Common Points (" + fld1NameU.title() + ")"

                arcpy.MakeFeatureLayer_management(os.path.join(env.workspace,outLayer),outLayerName)
                arcpy.ApplySymbologyFromLayer_management(outLayerName, layerFile)

                aprxMap.addLayer(layerFile)
                #arcpy.SetParameterAsText(3, outLayerName)

                AddMsgAndPrint(" \nAdded " + outLayerName + " to ArcPro TOC")

            except:
                errorMsg()
                pass

        else:
            AddMsgAndPrint("\nNo common-point issues found with '" + inLayer + "' \n ")

    except:
        errorMsg()

