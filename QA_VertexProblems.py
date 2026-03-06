#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA_VertexProblems.py
Created on: July 10, 2009

Author: Steve.Peaslee
        GIS Specialist
        National Soil Survey Center
        USDA - NRCS
e-mail: adolfo.diaz@usda.gov
phone: 608.662.4422 ext. 216

Author: Adolfo.Diaz
        GIS Specialist
        National Soil Survey Center
        USDA - NRCS
e-mail: adolfo.diaz@usda.gov
phone: 608.662.4422 ext. 216

@modified 03/06/2026
    @by: Alexnder Stum
@Version: 1.0

Identifies polygon line segments shorter than a specified length.
Calculate area statistics for each polygon and load into a table
Join table by OBJECTID to input featurelayer to spatially enable polygon statistics
Create point featurelayer marking endpoints for those polygon line segments that
are shorter than a specified distance.

07-10-2009 Original coding
05-15-2013 Renamed for SSURGO QA and converted to arcpy with da cursors (ArcGIS 10.1). Major rewrite.
06-07-2013 Problem with pre-existing join at line 240. Possibley failing to remove old join with shapefile input.
10-31-2013

==========================================================================================
# --- Update 03/06/2026; v 1.0
- Removed Number_Forma and former AddMsgAndPrint functions, leveraged 
f-strings and directly calling arcpy AddMessage, AddWarning, and AddError
functions
- cleaned some formatting of code

Updated  1/26/2021 - Adolfo Diaz

- Updated and Tested for ArcGIS Pro 2.6.1 and python 3.6
- All describe functions use the arcpy.da.Describe functionality.
- FIDSet now returns None and cannot be compared with ""
- All intermediate datasets are written to "in_memory" instead of written to a FGDB and
  and later deleted.  This avoids having to check and delete intermediate data during every
  execution.
- All cursors were updated to arcpy.da
- Added code to remove layers from an .aprx rather than simply deleting them
- Updated AddMsgAndPrint to remove ArcGIS 10 boolean and gp function
- Updated errorMsg() Traceback functions slightly changed for Python 3.6.
- Added parallel processing factor environment
- swithced from sys.exit() to exit()
- All gp functions were translated to arcpy
- Every function including main is in a try/except clause
- Main code is wrapped in if __name__ == '__main__': even though script will never be
  used as independent library.
- Normal messages are no longer Warnings unnecessarily.

"""
v = '1.0'
# ================================================================================================================
def errorMsg():
    try:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = ("\t"
                  f"{traceback.format_exception(exc_type, exc_value, exc_traceback)[1]}"
                  "\n\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[-1])

        if theMsg.find("exit") > -1:
            arcpy.AddError("\n\n")
            pass
        else:
            arcpy.AddError(theMsg)

    except:
        arcpy.AddError("Unhandled error in unHandledException method")
        pass

## ==============================================================================
def CreateWebMercaturSR():
    # Create default Web Mercatur coordinate system for instances where needed for
    # calculating the projected length of each line segment. Only works when input
    # coordinate system is GCS_NAD_1983, but then it should work almost everywhere.
    #
    try:
        # Use WGS_1984_Web_Mercator_Auxiliary_Sphere
        #theSpatialRef = 
        # arcpy.SpatialReference("USA Contiguous Albers Equal Area Conic USGS")
        theSpatialRef = arcpy.SpatialReference(3857)
        arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

        # return spatial reference string
        return theSpatialRef

    except:
        errorMsg()

## =============================================================================
def ProcessLayer(inLayer, outputSR, outLayer, minDist, iSelection):
    # All the real work is performed within this function
    # inLayer = selected featurelayer or featureclass that will be processed

    try:
        # Create table to store geometry statistics for each polygon
        # Later this table will be joined to the input layer on POLYID
        #
        arcpy.AddMessage(" \nReading polygon geometry...")

        # Create a list of coordinate pairs that have been added to the table 
        # to prevent duplicates
        #
        lSegments = []

        # create new table to store individual polygon statistics
        # POLYID,ACRES,VERTICES,AVI,MIN_DIST,MULTIPART
        statsTbl = MakeStatsTable(unitAbbrev)

        if arcpy.Exists(statsTbl):
            # open update cursor on polygon statistics table
            iCursor = arcpy.da.InsertCursor(
                statsTbl, 
                ["POLYID","ACRES","VERTICES","AVI","MIN_DIST","MULTIPART"]
            )

        else:
            return False

        # Process input featurelayer polygon geometry using search cursor
        #
        arcpy.SetProgressorLabel("Reading polygon geometry...")
        arcpy.SetProgressor(
            "step", "Reading polygon geometry...",  0, iSelection, 1
        )
        iCnt = 0
        fieldList = ["OID@","SHAPE@","SHAPE@AREA","SHAPE@LENGTH"]
        dPoints = dict()
        bHasMultiPart = False

        with arcpy.da.SearchCursor(inLayer, fieldList,"",outputSR) as sCursor:
            for fid, feat, theArea, thePerimeter in sCursor:
                # Process a polygon record. row[1] is the same as feat
                #fid, feat, theArea, thePerimeter = row 
                # do I need to worry about NULL geometry here?

                if not feat is None:
                    # check to make sure geometry object contains 
                    # a single-part polygon
                    iPartCnt = feat.partCount

                    if iPartCnt == 1:
                        iPartCnt = 0

                    elif iPartCnt == 0:
                        arcpy.AddError(f"Bad geometry for polygon #{fid}")

                    else:
                      bHasMultiPart = True

                    # get the total number of points for this polygon
                    iPnts = feat.pointCount
                    # use an arbitrarily high segment length as 
                    # the minimum for comparison
                    iSeg = 1000000  

                    for part in feat:
                        # accumulate 2 points for each segment
                        pntList = []  # initialize points list for polygon
                        pnt0 = part[0]

                        for pnt in part:
                            try:
                                pntList.append((pnt.X,pnt.Y))

                            except:
                                pass

                            if pnt:
                                # add vertice or to-node coordinates to list

                                if len(pntList) == 2:
                                    # calculate current segment length 
                                    # using 2 points
                                    dist = math.hypot(
                                        pntList[0][0] - pntList[1][0], pntList[0][1] - pntList[1][1]
                                    )
                                    #AddMsgAndPrint("\tLen: " + str(dist), 0)

                                    if dist < iSeg:
                                        iSeg = dist

                                    if dist < minDist:
                                        iCnt += 1

                                        # get midpoint of short line segment 
                                        # for vertex flag placement
                                        xm = (pntList[0][0] + pntList[1][0]) / 2.0
                                        ym = (pntList[0][1] + pntList[1][1]) / 2.0
                                        midPnt = [(xm,ym), fid, dist]

                                        # print line segment that is less than 
                                        # specified distance
                                        if fid in dPoints:
                                            # add this point to the existing 
                                            # list for this polygon
                                            dPoints[fid].append(midPnt)

                                        else:
                                            # create new dictionary entry 
                                            # for this polygon
                                            dPoints[fid] = [midPnt]
                                            arcpy.SetProgressorLabel(
                                                "Reading polygon geometry ( "
                                                f"{len(dPoints):,} "
                                                "locations flagged )..."
                                            )

                                    # then drop the first point from the list
                                    pntList.pop(0)

                                # add the next point
                                #pntList.append((pnt.X,pnt.Y))

                            else:
                                # interior ring or end of polygon encountered,
                                #AddMsgAndPrint("\tInterior Ring...", 0)
                                # reset points list for interior ring
                                pntList = []
                                break

                else:
                    # bad polygon geometry
                    arcpy.AddError(f"NULL geometry for polygon #{fid}")

                #POLYID,ACRES,VERTICES,AVI,MIN_DIST,MULTIPART
                if theUnits == "meters":
                    acres = theArea / 4046.85643

                elif theUnits == "feet_us":
                    acres = theArea / 43560.0

                else:
                    arcpy.AddError(
                        "\nFailed to calculate acre value using unit: "
                        f"{theUnits}"
                    )
                    return False

                avi = thePerimeter / iPnts
                outRow = [fid, acres,iPnts,avi,iSeg,iPartCnt]
                iCursor.insertRow(outRow)
                arcpy.SetProgressorPosition()

        del outRow
        del iCursor

        if bHasMultiPart:
            arcpy.AddError(
                "Input layer has multipart polygons "
                "that require editing (explode)"
            )

        if outLayer != "" and len(dPoints) > 0:
            # pairs of close vertices were flagged and need to be exported 
            # as midpoints in a new featureclass
            arcpy.AddWarning(
                f"\nFlagged {iCnt:,} segments shorter than {minDist} {theUnits}"
            )

            # add flagged midpoints to new points featureclass
            outLayer = MakePointsLayer(outputSR, minDist, unitAbbrev)

            arcpy.SetProgressorLabel("Saving midpoint of each short segment...")
            arcpy.SetProgressor(
                "step", "Saving midpoint of each short segment...",  0, iCnt, 1
            )

            with arcpy.da.InsertCursor(
                os.path.join(env.workspace, outLayer),
                ["SHAPE@","POLYID","LENGTH_" + unitAbbrev]
            ) as pntCursor:

                # for each value that has a reported common-point, 
                # get the list of coordinates from
                # the dDups dictionary and write to the output 
                # Common_Points featureclass
                for fid in dPoints.keys():
                    pnts = dPoints[fid]

                    for pnt in pnts:
                        pntCursor.insertRow(pnt)

                    arcpy.SetProgressorPosition()

            # create join between input polygon layer and QA_VertexStats table
            # "QA_VertexStats"
            arcpy.AddMessage(
                "\nOutput polygon statistics table: "
                f"{os.path.basename(statsTbl)} (joined to input layer)"
            )
            arcpy.AddIndex_management (
                statsTbl, "POLYID", "Indx_PolyID", "UNIQUE", "NON_ASCENDING"
            )
            arcpy.AddJoin_management (
                inLayer, fidFld, statsTbl, "POLYID", "KEEP_ALL"
            )

            # create new featurelayer from vertex flag points
            layerPath = os.path.dirname(sys.argv[0])
            layerFile = os.path.join(layerPath,"RedDot.lyrx")
            outLayerName = (f"QA Vertex Flag Points ({minDist} {unitAbbrev})")
            arcpy.MakeFeatureLayer_management(outLayer, outLayerName)
            arcpy.env.addOutputsToMap = True
            arcpy.ApplySymbologyFromLayer_management (outLayerName, layerFile)
            arcpy.SetParameter(3, outLayerName)
            arcpy.ResetProgressor()

        else:
            # no problems found
            #arcpy.Delete_management(statsTbl)
            arcpy.AddMessage(
                "\nNo short segments detected "
                f"(less than ({minDist:.3f} {theUnits}) \n "
            )
            pass

        return True

    except:
        errorMsg()
        return False

## =============================================================================
def MakePointsLayer(outputSR, minDist, unitAbbrev):
    # Create points shapefile in memory containing midpoint coordinates 
    # for short line segments.
    # Return table to ProcessLayer so that records can be added.
    #
    try:
        # Set workspace to that of the input polygon featureclass
        loc = env.workspace
        desc = arcpy.Describe(loc)
        dt = desc.dataType.upper()

        if dt == "WORKSPACE":
            ext = ""

        elif dt == "FEATUREDATASET":
            ext = ""

        elif dt == "FOLDER":
            ext = ".shp"

        else:
            arcpy.AddError(" \n" + loc + " is a " + dt + " datatype")
            return ""

        pointsLayer = "QA_VertexFlags_" + str(minDist).replace(".", "_") + ext
        arcpy.AddWarning(
            "\nOutput points layer: " + os.path.join(env.workspace,pointsLayer)
        )
        arcpy.CreateFeatureclass_management(
            env.workspace, pointsLayer, 
            "POINT", "", "DISABLED","DISABLED", outputSR
        )

        # create new fields to store objectid and minimum segment length 
        # found for each polygon
        if arcpy.Exists(pointsLayer):

            try:
                # "POLYID","SEGNO","LENGTH"
                arcpy.AddField_management(pointsLayer, "POLYID", "LONG")
                arcpy.AddField_management(
                    pointsLayer, "LENGTH" + "_" + unitAbbrev.upper(),
                    "DOUBLE", "12", "3"
                )
                # Add new field to track status of each point
                arcpy.AddField_management(
                    pointsLayer, "Status", "TEXT", "", "", 10, "Status"
                )

                try:
                    arcpy.DeleteField_management(pointsLayer, "ID")

                except:
                    pass

                return pointsLayer

            except:
                arcpy.AddError(
                    "Exception while adding shapefile fields in MakePointsLayer"
                )
                errorMsg()
                return ""

        else:
            arcpy.AddError(
                "Failed to create output shapefile in MakePointsLayer"
            )
            errorMsg()
            return ""

    except:
        errorMsg()
        return ""

## =============================================================================
def MakeStatsTable(unitAbbrev):
    # Create join table containing polygon statistics
    # At the end, this table will be joined to the input featureclass so that 
    # values can be mapped to show where the layer has issues.
    #
    try:
        thePrefix = "QA_VertexStats"

        if env.workspace.endswith(".gdb") or env.workspace.endswith(".mdb"):
            theExtension = ""

        else:
            theExtension = ".dbf"

        statsTbl = os.path.join(env.workspace, thePrefix + theExtension)

        try:
            if arcpy.Exists(statsTbl):
                arcpy.Delete_management(statsTbl)

            arcpy.CreateTable_management(
                os.path.dirname(statsTbl), os.path.basename(statsTbl)
            )

        except:
            errorMsg()
            return ""

        try:
            # POLYID,ACRES,VERTICES,AVI,MIN_DIST,MULTIPART
            arcpy.AddField_management(
                statsTbl, "POLYID", "LONG","","","", "PolygonID"
            )
            arcpy.AddField_management(
                statsTbl, "ACRES", "DOUBLE", "12", "1","", "Acres"
            )
            arcpy.AddField_management(
                statsTbl, "VERTICES", "LONG", "12","","", "Vertex Count"
            )
            arcpy.AddField_management(
                statsTbl, "AVI", "DOUBLE", 
                "12", "1", "", "Avg Segment (" + unitAbbrev + ")"
            )
            arcpy.AddField_management(
                statsTbl, "MIN_DIST", "DOUBLE", "12", "3", "", 
                "Min Segment (" + unitAbbrev + ")"
            )
            arcpy.AddField_management(
                statsTbl, "MULTIPART", "SHORT", "", "", "", "Is Multipart"
            )

            try:
                if arcpy.ListFields(statsTbl, "Field1")[0] == "Field1":
                    arcpy.AddMessage("Deleting extra FIELD1 field")
                    arcpy.DeleteField_management(statsTbl, "Field1")

            except:
                pass

        except:
            errorMsg()
            return ""

        return statsTbl

    except:
        errorMsg()
        return ""

## =============================================================================
def RemoveJoins(inputLayer, theWildcard):
    ## Remove any joined tables matching wildcard string
    # inputLayer could also be a standalone table

    try:
        theJoinList = []
        desc = arcpy.Describe(inputLayer)

        if desc.DataType.upper() == "FEATURELAYER":
            theFC = desc.Featureclass.Name.replace(".shp","")
        else:
            return True

        fieldList = desc.fields

        for theField in fieldList:
            fullName = theField.name
            nameList = arcpy.ParseFieldName(fullName).split(",")
            fieldName = nameList[3]
            tableName = fullName[0:-(len(fieldName))]

            if tableName != theFC and not tableName in theJoinList:
                # Found join, but only remove it if it matches wildcard
                if theWildcard == "" and tableName != " ":
                    theJoinList.append(tableName)
                    arcpy.AddMessage(" \nRemoving join: " + tableName)
                    arcpy.RemoveJoin_management(inLayer, tableName)

                elif tableName.startswith(theWildcard):
                    theJoinList.append(tableName)
                    arcpy.AddMessage("\nRemoving join: " + tableName)
                    arcpy.RemoveJoin_management(inLayer, tableName)

        return True

    except:
        errorMsg()
        return False


## =============================================================================
## MAIN
import sys, string, os, locale, math, operator, traceback, arcpy
from arcpy import env

if __name__ == '__main__':

    try:
        arcpy.AddMessage(f"Find Vertex Problems: {v=}")
        # Set formatting for numbers
        locale.setlocale(locale.LC_ALL, "")

        # Target Featureclass
        inLayer = arcpy.GetParameterAsText(0)

        # Line segment length below which vertices are flagged
        minDist = arcpy.GetParameter(1)

        # Projection (optional when input layer has projected coordinate system)
        outputSR = arcpy.GetParameter(2)

        # Output featurelayer containing flagged vertices 
        # (too close to neighbor)
        outLayer = arcpy.GetParameterAsText(3)

        # Check out ArcInfo license for PolygonToLine
        arcpy.SetProduct("ArcInfo")
        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # An initial description of the input is required
        # Describe input layer
        desc = arcpy.da.Describe(inLayer)
        theDataType = desc['dataType'].upper()

        # input layer needs to be a featurelayer. If it is a featureclass, 
        # do a switch.
        if theDataType in ("FEATURECLASS", "SHAPEFILE"):
            # swap out the input featureclass for a new featurelayer 
            # based upon that featureclass
            inLayer = desc['name'] + " Layer"
            arcpy.AddMessage("\nCreating new featurelayer named: " + inLayer)
            arcpy.MakeFeatureLayer_management(desc['catalogPath'], inLayer)

        # First clean up any joins from previous runs
        else:
            if not RemoveJoins(inLayer, "QA_VertexStats"):
                arcpy.AddError("Failed to remove previous table join")
                exit()

        # Setup: Get all required information from input layer
        # Describe input layer
        desc = arcpy.da.Describe(inLayer)
        theDataType = desc['dataType'].upper()
        theCatalogPath = desc['catalogPath']
        fidFld = desc['OIDFieldName']
        inputSR = desc['spatialReference']
        inputDatum = inputSR.GCS.datumName

        # Set output workspace
        if(arcpy.Describe(os.path.dirname(theCatalogPath)).dataType.upper() 
           == "FEATUREDATASET"):
            # if input layer is in a featuredataset, 
            # move up one level to the geodatabase
            env.workspace = os.path.dirname(os.path.dirname(theCatalogPath))

        else:
            env.workspace = os.path.dirname(theCatalogPath)

        arcpy.AddMessage(" \nOutput workspace set to: " + env.workspace)

        # Get total number of features for the input featureclass
        iTotalFeatures = int(
            arcpy.GetCount_management(theCatalogPath).getOutput(0)
        )

        # Get input layer information and count the number of input features
        if theDataType == "FEATURELAYER":
            # input layer is a FEATURELAYER, 
            # get featurelayer specific information
            defQuery = desc['whereClause']
            fids = desc['FIDSet']
            layerName = desc['nameString']

            # get count of number of features being processed
            if fids == None:
                # No selected features in layer
                iSelection = iTotalFeatures

                if defQuery == "":
                    # No query definition and no selection
                    iSelection = iTotalFeatures
                    arcpy.AddMessage(
                        f"\nProcessing all {iTotalFeatures:,} "
                        f"polygons in '{layerName }'..."
                    )

                else:
                    # There is a query definition, 
                    # so the only option is to use GetCount 
                    # Use selected features code
                    iSelection = int(
                        arcpy.GetCount_management(inLayer).getOutput(0))
                    arcpy.AddMessage(
                        f"\nProcessing {iSelection:,} of "
                        f"{iTotalFeatures:,} features..."
                    )

            else:
                # featurelayer has a selected set, get count using FIDSet
                iSelection = len(fids.split(";"))
                arcpy.AddMessage(
                        f"\nProcessing {iSelection:,} of "
                        f"{iTotalFeatures:,} features..."
                    )
        elif theDataType == "FEATURECLASS":
            # input layer is a featureclass, 
            # get featureclass specific information
            layerName = desc['baseName']
            defQuery = ""
            fids = ""
            iSelection = iTotalFeatures
            arcpy.AddMessage(
                f"\nProcessing all {iTotalFeatures:,} "
                f"polygons in '{layerName}'..."
            )

        # Make sure that input and output datums are the same, 
        # no transformations allowed
        if outputSR.name == '':
            outputSR = inputSR
            outputDatum = inputDatum
        else:
            outputDatum = outputSR.GCS.datumName

        if inputDatum != outputDatum:
            arcpy.AddError("Input and output datums do not match")
            exit()

        if outputSR.type.upper() != "PROJECTED":
            if inputDatum in ("D_North_American_1983","D_WGS_1984"):
                # use Web Mercatur as output projection for c
                # alculating segment length
                arcpy.AddWarning(
                    "\nInput layer coordinate system is not projected, "
                    "switching to Web Mercatur (meters)"
                )
                outputSR = CreateWebMercaturSR()

            else:
                arcpy.AddError(
                    f"Unable to handle input coordinate system: {inputSR.name}"
                    f"\n{inputDatum}"
                )

        else:
            arcpy.AddMessage(
                "\nUsing  output coordinate system: " + outputSR.name
            )

        theUnits = outputSR.linearUnitName.lower()
        theUnits = theUnits.replace("foot", "feet")
        theUnits = theUnits.replace("meter", "meters")

        if theUnits.startswith("meter"):
            unitAbbrev = "m"
        else:
            unitAbbrev = "ft"

        # run process
        bProcessed = ProcessLayer(
            inLayer, outputSR, outLayer, minDist, iSelection
        )

    except:
        errorMsg()

