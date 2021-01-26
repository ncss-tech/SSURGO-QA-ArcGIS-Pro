# ---------------------------------------------------------------------------
# QA_VertexReport.py
# Created on: May 20, 2013
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

# Identifies polygon line segments shorter than a specified length.
# Calculate area statistics for each polygon and load into a table
# Join table by OBJECTID to input featurelayer to spatially enable polygon statistics
# Create point featurelayer marking endpoints for those polygon line segments that
# are shorter than a specified distance.
#
# Issue with shapefile input. Script may fail if selected fieldname is longer than 8 characters.
#
# Fixed issue where the optional attribute field was not set. Uses OBJECTID field now.

# 07-22-2013 Found issue with ArcSDE workspace, need to fix problem with MakeStatsTable function

# 07-22-2013 Found apparent problem with using a selected set and MUSYM on SDM. Appears to get a list
# of MUSYM values within the selected set, but then queries the entire layer to process each individual value.
# Maybe it's just slow, but I need to make sure that the script is using a subset of the original selection as it loops through
# the unique values.
#
# 10-31-2013

# ==========================================================================================
# Updated  1/26/2021 - Adolfo Diaz
#
# - Updated and Tested for ArcGIS Pro 2.6.1 and python 3.6
# - All describe functions use the arcpy.da.Describe functionality.
# - FIDSet now returns None and cannot be compared with ""
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

# ===============================================================================================================
def setScratchWorkspace():
    """ This function will set the scratchWorkspace for the interim of the execution
        of this tool.  The scratchWorkspace is used to set the scratchGDB which is
        where all of the temporary files will be written to.  The path of the user-defined
        scratchWorkspace will be compared to existing paths from the user's system
        variables.  If there is any overlap in directories the scratchWorkspace will
        be set to C:\TEMP, assuming C:\ is the system drive.  If all else fails then
        the packageWorkspace Environment will be set as the scratchWorkspace. This
        function returns the scratchGDB environment which is set upon setting the scratchWorkspace"""

##        This is a printout of my system environmmental variables - Windows 10
##        -----------------------------------------------------------------------------------------
##        ESRI_OS_DATADIR_LOCAL_DONOTUSE-- C:\Users\Adolfo.Diaz\AppData\Local\
##        ESRI_OS_DIR_DONOTUSE-- C:\Users\ADOLFO~1.DIA\AppData\Local\Temp\ArcGISProTemp22096\
##        ESRI_OS_DATADIR_ROAMING_DONOTUSE-- C:\Users\Adolfo.Diaz\AppData\Roaming\
##        TEMP-- C:\Users\ADOLFO~1.DIA\AppData\Local\Temp\ArcGISProTemp22096\
##        LOCALAPPDATA-- C:\Users\Adolfo.Diaz\AppData\Local
##        PROGRAMW6432-- C:\Program Files
##        COMMONPROGRAMFILES-- C:\Program Files\Common Files
##        APPDATA-- C:\Users\Adolfo.Diaz\AppData\Roaming
##        USERPROFILE-- C:\Users\Adolfo.Diaz
##        PUBLIC-- C:\Users\Public
##        SYSTEMROOT-- C:\windows
##        PROGRAMFILES-- C:\Program Files
##        COMMONPROGRAMFILES(X86)-- C:\Program Files (x86)\Common Files
##        ALLUSERSPROFILE-- C:\ProgramData
##        HOMEPATH-- \
##        HOMESHARE-- \\usda.net\NRCS\home\WIMA2\NRCS\Adolfo.Diaz
##        ONEDRIVE-- C:\Users\Adolfo.Diaz\OneDrive - USDA
##        ARCHOME-- c:\program files\arcgis\pro\
##        ARCHOME_USER-- c:\program files\arcgis\pro\
##        ------------------------------------------------------------------------------------------

    try:

        def setTempFolderAsWorkspace(sysDriveLetter):
            tempFolder = sysDrive + os.sep + "TEMP"

            if not os.path.exists(tempFolder):
                os.makedirs(tempFolder,mode=777)

            arcpy.env.scratchWorkspace = tempFolder
            AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)
            return arcpy.env.scratchGDB


        AddMsgAndPrint("\nSetting Scratch Workspace")
        scratchWK = arcpy.env.scratchWorkspace

        # -----------------------------------------------
        # Scratch Workspace is defined by user or default is set
        if scratchWK is not None:

            # dictionary of system environmental variables
            envVariables = os.environ

            # get the root system drive i.e C:
            if 'SYSTEMDRIVE' in envVariables:
                sysDrive = envVariables['SYSTEMDRIVE']
            else:
                sysDrive = None

            varsToSearch = ['HOMEDRIVE','HOMEPATH','HOMESHARE','ONEDRIVE','ARCHOME','ARCHOME_USER',
                            'ESRI_OS_DATADIR_LOCAL_DONOTUSE','ESRI_OS_DIR_DONOTUSE','ESRI_OS_DATADIR_MYDOCUMENTS_DONOTUSE',
                            'ESRI_OS_DATADIR_ROAMING_DONOTUSE','TEMP','LOCALAPPDATA','PROGRAMW6432','COMMONPROGRAMFILES','APPDATA',
                            'USERPROFILE','PUBLIC','SYSTEMROOT','PROGRAMFILES','COMMONPROGRAMFILES(X86)','ALLUSERSPROFILE']

            bSetTempWorkSpace = False

            """ Iterate through each Environmental variable; If the variable is within the 'varsToSearch' list
                above then check their value against the user-set scratch workspace.  If they have anything
                in common then switch the workspace to something local  """
            for var in envVariables:

                if not var in varsToSearch:
                    continue

                # make a list from the scratch and environmental paths
                varValueList = (envVariables[var].lower()).split(os.sep)          # ['C:', 'Users', 'adolfo.diaz', 'AppData', 'Local']
                scratchWSList = (scratchWK.lower()).split(os.sep)                 # [u'C:', u'Users', u'adolfo.diaz', u'Documents', u'ArcGIS', u'Default.gdb', u'']

                # remove any blanks items from lists
                varValueList = [val for val in varValueList if not val == '']
                scratchWSList = [val for val in scratchWSList if not val == '']

                # Make sure env variables were populated
                if len(varValueList)>0 and len(scratchWSList)>0:

                    # Home drive is being used as scrathcworkspace
                    if scratchWSList[0].lower() == envVariables['HOMEDRIVE'].lower():
                        bSetTempWorkSpace = True

                    # First element is the drive letter; remove it if they are they same.
                    if varValueList[0] == scratchWSList[0]:
                        varValueList.remove(varValueList[0])
                        scratchWSList.remove(scratchWSList[0])
                    else:
                        continue

                # Compare the values of 2 lists; order is significant
                common = [i for i, j in zip(varValueList, scratchWSList) if i == j]

                # There is commonality between the scrathWS and some env variable
                # Proceed with creating a temp path.
                if len(common) > 0:
                    bSetTempWorkSpace = True
                    break

            # The current scratch workspace shares 1 or more directory paths with the
            # system env variables.  Create a temp folder at root
            if bSetTempWorkSpace:
                AddMsgAndPrint("\tCurrent Workspace: " + scratchWK)

                if sysDrive:
                    return setTempFolderAsWorkspace(sysDrive)

                # This should never be the case.  Every computer should have a system drive (C:\)
                # packageWorkspace is set to "IN_MEMORY"
                else:
                    packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                    if arcpy.env[packageWS[0]]:
                        arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                        AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)
                    else:
                        AddMsgAndPrint("\tCould not set any scratch workspace",2)
                        return False

            # user-set workspace does not violate system paths; Check for read/write
            # permissions; if write permissions are denied then set workspace to TEMP folder
            else:
                arcpy.env.scratchWorkspace = scratchWK
                arcpy.env.scratchGDB

                if arcpy.env.scratchGDB == None:
                    AddMsgAndPrint("\tCurrent scratch workspace: " + scratchWK + " is READ only!")

                    if sysDrive:
                        return setTempFolderAsWorkspace(sysDrive)

                    else:
                        packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                        if arcpy.env[packageWS[0]]:
                            arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                            AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)
                            return arcpy.env.scratchGDB

                        else:
                            AddMsgAndPrint("\tCould not set any scratch workspace",2)
                            return False

                else:
                    AddMsgAndPrint("\tUser-defined scratch workspace is set to: "  + arcpy.env.scratchGDB)
                    return arcpy.env.scratchGDB

        # No workspace set (Very odd that it would go in here unless running directly from python)
        else:
            AddMsgAndPrint("\tNo user-defined scratch workspace ")
            sysDrive = os.environ['SYSTEMDRIVE']

            if sysDrive:
                return setTempFolderAsWorkspace(sysDrive)

            else:
                packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                if arcpy.env[packageWS[0]]:
                    arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                    AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)
                    return arcpy.env.scratchGDB

                else:
                    AddMsgAndPrint("\tCould not set scratchWorkspace. Not even to default!",2)
                    return False

    except:
        errorMsg()

## ===================================================================================
def CreateWebMercaturSR():
    # Create default Web Mercatur coordinate system for instances where needed for
    # calculating the projected length of each line segment. Only works when input
    # coordinate system is GCS_NAD_1983, but then it should work almost everywhere.
    #
    try:
        # Use WGS_1984_Web_Mercator_Auxiliary_Sphere
        #theSpatialRef = arcpy.SpatialReference("USA Contiguous Albers Equal Area Conic USGS")
        theSpatialRef = arcpy.SpatialReference(3857)
        arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

        # return spatial reference string
        return theSpatialRef

    except:
        errorMsg()

## ===================================================================================
def ProcessLayer(inLayer, inField, outputSR):
    # Create a single summary for the entire layer
    #
    # inLayer = selected featurelayer or featureclass that will be processed
    try:

        # create new table to store individual polygon statistics
        # no input field so specify

        statsTbl = MakeStatsTable(inField, unitAbbrev)

        if arcpy.Exists(statsTbl):
            # open update cursor on polygon statistics table
            fieldList = ["ACRES","VERTICES","AVI","MIN_DIST","MULTIPART"]
            iCursor = arcpy.da.InsertCursor(statsTbl, fieldList )

        else:
            return False

        statsTbl = MakeStatsTable(inField, unitAbbrev)

        # Add QA_VertexReport table to ArcMap TOC
        arcpy.SetParameter(3, statsTbl)
        iCnt = int(arcpy.GetCount_management(inLayer).getOutput(0))

        arcpy.SetProgressorLabel("Reading polygon geometry...")
        arcpy.SetProgressor("step", "Reading polygon geometry...",  0, iCnt, 1)

        # initialize summary variables for entire dataset
        polygonTotal = 0
        totalArea = 0
        totalAcres = 0
        pointTotal = 0
        totalPerimeter = 0
        minDist = 1000
        bHasMultiPart = False

        fieldList = ["OID@","SHAPE@","SHAPE@AREA","SHAPE@LENGTH"]
        formatList = (15,15,15,15,15,20)
        hdrList = ["Polygons","Acres","Vertices","Avg_Length","Min_Length","IsMultiPart"]
        dashedLine = "    |------------------------------------------------------------------------------------------|"

        newHdr = ""

        for i in range(6):
            newHdr = newHdr + (" " * (formatList[i] - len(hdrList[i])) + hdrList[i])

        AddMsgAndPrint(" \n" + newHdr)
        AddMsgAndPrint(dashedLine)

        #AddMsgAndPrint(" \nSummarizing polygon statistics for " + inField.name + " value: '" + val + "'", 1)
        # initialize variables for the current value (eg. NE109)
        iSeg = 1000000  # use an arbitrarily high segment length to initialize segment length
        polygonCnt = 0
        sumArea = 0
        sumAcres = 0
        pointCnt = 0
        sumPerimeter = 0

        with arcpy.da.SearchCursor(inLayer, fieldList, "", outputSR) as sCursor:
            # Select polgyons with the current attribute value and process the geometry for each
            iPartCnt = 0

            for row in sCursor:
                # Process a polygon record. row[1] is the same as feat or SHAPE
                fid, feat, theArea, thePerimeter = row # do I need to worry about NULL geometry here?

                if not feat is None:
                    polygonCnt += 1
                    iPnts = feat.pointCount
                    pointCnt += iPnts
                    iPartCnt = feat.partCount

                    if feat.partCount > 1:
                        iPartCnt += 1
                        bHasMultiPart = True

                    elif iPartCnt == 0:
                        # bad polygon
                        AddMsgAndPrint("Bad geometry for polygon #" + str(fid),2)

                    sumArea += theArea
                    sumPerimeter += thePerimeter

                    for part in feat:
                        # accumulate 2 points for each segment
                        pntList = []  # initialize points list for polygon

                        for pnt in part:
                            if pnt:
                                # add vertice or to-node coordinates to list

                                if len(pntList) == 2:
                                    # calculate current segment length using 2 points
                                    dist = math.hypot(pntList[0][0] - pntList[1][0], pntList[0][1] - pntList[1][1] )

                                    if dist < iSeg:
                                        iSeg = dist

                                    # then drop the first point from the list
                                    pntList.pop(0)

                                # add the next point
                                pntList.append((pnt.X,pnt.Y))

                            else:
                                # interior ring encountered
                                #AddMsgAndPrint("\t\t\tInterior Ring...")
                                pntList = []  # reset points list for interior ring

                else:
                    AddMsgAndPrint("NULL geometry for polygon #" + str(fid),2)

                # convert mapunit area to acres
                if theUnits == "meters":
                    sumAcres = sumArea / 4046.85643

                elif theUnits == "feet_us":
                    sumAcres = sumArea / 43560.0

                else:
                    AddMsgAndPrint(" \nFailed to calculate acre value using unit: " + theUnits, 2)
                    return False

                # calculate average vertex interval for this polygon
                avi = sumPerimeter / pointCnt

                if iSeg < minDist:
                    minDist = iSeg

                #outRow = [sumAcres, pointCnt,avi,iSeg,iPartCnt]

                #iCursor.insertRow(outRow)

                arcpy.SetProgressorPosition()

            # calculate average vertex interval for the current value
            avgInterval = sumPerimeter / pointCnt
            polygonTotal += polygonCnt
            totalAcres += sumAcres
            pointTotal += pointCnt
            totalPerimeter += sumPerimeter

            #"ACRES","VERTICES","AVI","MIN_DIST","MULTIPART"
            outRow = [totalAcres, pointTotal,avgInterval,minDist,iPartCnt]
            iCursor.insertRow(outRow)

        # calculate average vertex interval for entire dataset
        # if the cursor selection fails, this will throw a divide-by-zero error
        if pointTotal > 0:
            avgInterval = totalPerimeter / pointTotal

        else:
            avgInterval = -1

        # get minimum segment length for entire dataset
        if iSeg < minDist:
            minDist = iSeg


        # print final summary statistics for entire dataset
        if bHasMultiPart:
            totalMsg = [Number_Format(polygonCnt, 0, True), Number_Format(sumAcres, 1, True), Number_Format(pointCnt, 0, True), Number_Format(avgInterval, 3, True), Number_Format(minDist, 3, True), "Has Multipart!"]

        else:
            totalMsg = [Number_Format(polygonCnt, 0, True), Number_Format(sumAcres, 1, True), Number_Format(pointCnt, 0, True), Number_Format(avgInterval, 3, True), Number_Format(minDist, 3, True), "No Multipart"]

        newTotal = ""

        for i in range(6):
            newTotal = newTotal + (" " * (formatList[i] - len(totalMsg[i])) + totalMsg[i])

        AddMsgAndPrint(newTotal)

        if bHasMultiPart:
            AddMsgAndPrint("Input layer has multipart polygons that require editing (explode)", 2)

        # Add QA_VertexReport table to ArcMap TOC
        AddMsgAndPrint(" \nPolygon statistics saved to " + statsTbl)
        arcpy.SetParameter(3, statsTbl)

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def ProcessLayerBySum(inLayer, inField, outputSR):
    # All the real work is performed within this function
    # inLayer = selected featurelayer or featureclass that will be processed
    # if it is a featureclass, then a featurelayer must be substituted to allow  a selection

    try:
        # Create table to store geometry statistics for each polygon
        # Later this table will be joined to the input layer on POLYID
        #
        # Create a list of coordinate pairs that have been added to the table to prevent duplicates
        #
        # create new table to store individual polygon statistics
        statsTbl = MakeStatsTable(inField, unitAbbrev)

        if arcpy.Exists(statsTbl):
            # open update cursor on polygon statistics table

            newFieldName = arcpy.ParseFieldName(inField.name).split(",")[3].strip()
            fieldList = [newFieldName,"ACRES","VERTICES","AVI","MIN_DIST","MULTIPART"]
            iCursor = arcpy.da.InsertCursor(statsTbl, fieldList )

        else:
            return False

        # Create a list of unique values for the inField
        fieldList = [inField.name]
        fldType = inField.type
        valList = [row[0] for row in arcpy.da.SearchCursor(inLayer, fieldList)]
        uniqueList = list(set(valList))
        uniqueList.sort()
        del valList

        if len(uniqueList) > 0:

            # only proceed if list contains unique values to be processed
            AddMsgAndPrint(" \nFound " + Number_Format(len(uniqueList), 0, True) + " unique values for " + inFieldName + " \n ")

            # if the input is a featurelayer, need to see if there is a selection set or definition query that needs to be maintained
            #
            # initialize summary variables for entire dataset
            polygonTotal = 0
            totalArea = 0
            totalAcres = 0
            pointTotal = 0
            totalPerimeter = 0
            minDist = 1000000
            bHasMultiPart = False
            maxV = 100000  # set a polygon-vertex limit that will trigger a warning
            bigPolyList = list()  # add the polygon id to this list if it exceeds the limit

            fieldList = ["OID@","SHAPE@","SHAPE@AREA","SHAPE@LENGTH"]
            newFieldName = arcpy.ParseFieldName(inField.name).split(",")[3].strip()

            formatList = (20,15,15,15,15,15,15)
            hdrList = [newFieldName.capitalize(),"Polygons","Acres","Vertices","Avg_Length","Min_Length","IsMultiPart"]
            dashedLine = "    |----------------------------------------------------------------------------------------------------------|"
            newHdr = ""

            for i in range(7):
                newHdr = newHdr + (" " * (formatList[i] - len(hdrList[i])) + hdrList[i])

            AddMsgAndPrint(newHdr)
            AddMsgAndPrint(dashedLine)

            for val in uniqueList:
                arcpy.SetProgressorLabel("Reading polygon geometry for " + inField.name + " value:  " + str(val)  + "...")

                #if fldType != "OID":
                theSQL = arcpy.AddFieldDelimiters(inLayer, inField.name) + " = '" + val + "'"

                #else:
                #    theSQL =  inField.name  + " = " + str(val)

                arcpy.SelectLayerByAttribute_management(inLayer, "NEW_SELECTION", theSQL)

                iCnt = int(arcpy.GetCount_management(inLayer).getOutput(0))
                arcpy.SetProgressor("step", "Reading polygon geometry for " + inField.name + " value:  " + str(val)  + "...",  0, iCnt, 1)

                if val.strip() == "":
                    # if some values aren't populated, insert string 'NULL' into report table
                    val = "<NULL>"

                #AddMsgAndPrint(" \nSummarizing polygon statistics for " + inField.name + " value: '" + val + "'", 1)
                # initialize variables for the current value (eg. NE109)
                iSeg = 1000000  # use an arbitrarily high segment length to initialize segment length
                polygonCnt = 0
                sumArea = 0
                sumAcres = 0
                pointCnt = 0
                sumPerimeter = 0

                with arcpy.da.SearchCursor(inLayer, fieldList, "", outputSR) as sCursor:

                    # Select polgyons with the current attribute value and process the geometry for each
                    iPartCnt = 0

                    for row in sCursor:
                        # Process a polygon record. row[1] is the same as feat
                        fid, feat, theArea, thePerimeter = row # do I need to worry about NULL geometry here?

                        if not feat is None:
                            polygonCnt += 1

                            if feat.partCount > 1:
                                iPartCnt += 1
                                bHasMultiPart = True

                            elif feat.partCount == 0:
                                AddMsgAndPrint("Bad geometry for polygon #" + str(fid),2)

                            iPnts = feat.pointCount

                            if iPnts > maxV:
                                bigPolyList.append(str(fid))

                            pointCnt += iPnts
                            sumArea += theArea
                            sumPerimeter += thePerimeter

                            for part in feat:
                                # accumulate 2 points for each segment
                                pntList = []  # initialize points list for polygon

                                for pnt in part:
                                    if pnt:
                                        # add vertice or to-node coordinates to list

                                        if len(pntList) == 2:
                                            # calculate current segment length using 2 points
                                            dist = math.hypot(pntList[0][0] - pntList[1][0], pntList[0][1] - pntList[1][1] )

                                            if dist < iSeg:
                                                iSeg = dist

                                            # then drop the first point from the list
                                            pntList.pop(0)

                                        # add the next point
                                        pntList.append((pnt.X,pnt.Y))

                                    else:
                                        # interior ring encountered
                                        #AddMsgAndPrint("\t\t\tInterior Ring...")
                                        pntList = []  # reset points list for interior ring

                            arcpy.SetProgressorPosition()

                        else:
                            AddMsgAndPrint("Null geometry for polygon #" + str(fid),2)

                    # convert mapunit area to acres
                    if theUnits == "meters":
                        sumAcres = sumArea / 4046.85643

                    elif theUnits == "feet_us":
                        sumAcres = sumArea / 43560.0

                    else:
                        AddMsgAndPrint(" \nFailed to calculate acre value using unit: " + theUnits, 2)
                        return False

                    # calculate average vertex interval for this polygon
                    avi = sumPerimeter / pointCnt

                    if iSeg < minDist:
                        minDist = iSeg

                    if inFieldName != "":
                        outRow = [val, sumAcres, pointCnt,avi,iSeg,iPartCnt]

                    else:
                        outRow = [sumAcres, pointCnt,avi,iSeg,iPartCnt]

                    iCursor.insertRow(outRow)

                    arcpy.ResetProgressor()

                # calculate average vertex interval for the current value
                avgInterval = sumPerimeter / pointCnt
                polygonTotal += polygonCnt
                totalAcres += sumAcres
                pointTotal += pointCnt
                totalPerimeter += sumPerimeter

                # print statistics to console window
                #
                # column headers: newFieldName.capitalize(), "Polygons", "Acres","Vertices","Avg_Length","Min_Length","IsMultiPart"
                # format message string into a fixed set of columns
                statsMsg =  [val, Number_Format(polygonCnt, 0, True), Number_Format(sumAcres, 1, True), Number_Format(pointCnt, 0, True), Number_Format(avgInterval, 3, True), Number_Format(iSeg, 3, True), str(iPartCnt)]
                newMsg = ""

                for i in range(7):
                    newMsg = newMsg + (" " * (formatList[i] - len(statsMsg[i])) + statsMsg[i])

                AddMsgAndPrint(newMsg)

                #arcpy.SetProgressorPosition()

        else:
            AddMsgAndPrint(" \nFailed to create list of unique " + inFieldName + " values", 2)
            return False

        arcpy.ResetProgressor()

        # calculate average vertex interval for entire dataset
        # if the cursor selection fails, this will throw a divide-by-zero error
        if pointTotal > 0:
            avgInterval = totalPerimeter / pointTotal

        else:
            avgInterval = -1

        # get minimum segment length for entire dataset
        if iSeg < minDist:
            minDist = iSeg

        # print final summary statistics for entire dataset
        if bHasMultiPart:
            totalMsg = ["",Number_Format(polygonTotal, 0, True), Number_Format(totalAcres, 1, True), Number_Format(pointTotal, 0, True), Number_Format(avgInterval, 3, True), Number_Format(minDist, 3, True), "Has Multipart!"]

        else:
            totalMsg = ["",Number_Format(polygonTotal, 0, True), Number_Format(totalAcres, 1, True), Number_Format(pointTotal, 0, True), Number_Format(avgInterval, 3, True), Number_Format(minDist, 3, True), "No Multipart"]

        newTotal = ""

        for i in range(6):
            newTotal = newTotal + (" " * (formatList[i] - len(totalMsg[i])) + totalMsg[i])

        AddMsgAndPrint(dashedLine)
        AddMsgAndPrint(newTotal)

        if bHasMultiPart:
            AddMsgAndPrint("Input layer has multipart polygons that require editing (explode)", 2)

        if len(bigPolyList) > 0:
            AddMsgAndPrint("Warning! Input layer has " + str(len(bigPolyList)) + " polygons exceeding the " + Number_Format(maxV) + " vertex limit: " + ", ".join(bigPolyList), 2)

        # Add QA_VertexReport table to ArcMap TOC
        AddMsgAndPrint(" \nPolygon statistics saved to " + statsTbl)
        arcpy.SetParameter(3, statsTbl)
        arcpy.SelectLayerByAttribute_management(inLayer, "CLEAR_SELECTION")

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def MakeStatsTable(inField, unitAbbrev):
    # Create join table containing polygon statistics
    # If AREASYMBOL is the chosen field, this table could be joined to the SAPOLYGON
    # featureclass so that values can be mapped to show which surveys have general issues.
    #
    # Assumption is that the workspace has been set to the geodatabase or folder
    # If workspace is a featuredataset, the script will fail

    try:
        thePrefix = "QA_VertexReport"

        if env.workspace.endswith(".gdb") or env.workspace.endswith(".mdb"):
            theExtension = ""
            statsTbl = os.path.join(env.workspace, thePrefix + theExtension)

        elif env.workspace.endswith(".sde"):
            theExtension = ".dbf"
            statsTbl = os.path.join(env.scratchFolder, thePrefix + theExtension)

        else:
            theExtension = ".dbf"
            statsTbl = os.path.join(env.workspace, thePrefix + theExtension)

        try:
            if arcpy.Exists(statsTbl):
                arcpy.Delete_management(statsTbl)

            arcpy.CreateTable_management(os.path.dirname(statsTbl), os.path.basename(statsTbl))
            #AddMsgAndPrint("Created polygon stats table (" + statsTbl + ")", 1)

        except:
            errorMsg()
            return ""

        try:
            # inField,ACRES,VERTICES,AVI,MIN_DIST,MULTIPART
            # make sure new field is less than 10 characters if output format is .DBF

            if inFieldName != "":
                if theExtension == ".dbf":
                    # A dbf cannot have field names greater than 10 characters
                    newFieldName = arcpy.ParseFieldName(inField.name).split(",")[3].strip()[0:10]

                else:
                    newFieldName = arcpy.ParseFieldName(inField.name).split(",")[3].strip()

                arcpy.AddField_management(statsTbl, newFieldName, inField.type, inField.precision,inField.scale,inField.length, inField.aliasName)

            # Add fields to the stats table
            # Field aliases cannot be set in a .dbf
            arcpy.AddField_management(statsTbl, "ACRES", "DOUBLE", "12", "1","", field_alias="Acres")
            arcpy.AddField_management(statsTbl, "VERTICES", "LONG", "12","","", field_alias="Vertex Count")
            arcpy.AddField_management(statsTbl, "AVI", "DOUBLE", "12", "1", "", field_alias="Avg Segment (" + unitAbbrev + ")")
            arcpy.AddField_management(statsTbl, "MIN_DIST", "DOUBLE", "12", "3", "", field_alias="Min Segment (" + unitAbbrev + ")")
            arcpy.AddField_management(statsTbl, "MULTIPART", "SHORT", "", "", "", field_alias="Is Multipart?")

            try:
                allFields = arcpy.ListFields(statsTbl)

                for badField in allFields:
                    #AddMsgAndPrint("\tBadFields: " + badField.name)
                    if badField.name.upper() == "FIELD1":
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
        errorMsg()
        return num

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
## MAIN
import sys, string, os, locale, time, math, operator, traceback, collections, arcpy
from arcpy import env

if __name__ == '__main__':

    try:

        # Set formatting for numbers
        locale.setlocale(locale.LC_ALL, "")

        # Script parameters

        # Target Featureclass
        inLayer = arcpy.GetParameter(0)

        # Target field (restricted to TEXT by the ArcTool validator)
        inFieldName = arcpy.GetParameterAsText(1)

        # Projection (optional when input layer has projected coordinate system)
        outputSR = arcpy.GetParameter(2)

        # Start timer
        #begin = time.time()
        #eMsg = elapsedTime(begin)

        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # reset field parameter to a field object so that the properties can be determined
        if inFieldName != "":
            fldList = arcpy.ListFields(inLayer)
            inField = None

            for fld in fldList:
                if fld.name == inFieldName:
                    inField = fld

        # Setup: Get all required information from input layer
        # Describe input layer
        desc = arcpy.da.Describe(inLayer)
        theDataType = desc['dataType'].upper()
        theCatalogPath = desc['catalogPath']
        fidFld = desc['OIDFieldName']
        inputSR = desc['spatialReference']
        inputDatum = inputSR.GCS.datumName

        # Set output workspace
        if arcpy.Describe(os.path.dirname(theCatalogPath)).dataType.upper() == "FEATUREDATASET":
            # if input layer is in a featuredataset, move up one level to the geodatabase
            env.workspace = os.path.dirname(os.path.dirname(theCatalogPath))

        else:
            env.workspace = os.path.dirname(theCatalogPath)

        AddMsgAndPrint("\nOutput workspace set to: " + env.workspace)

        # Get total number of features for the input featureclass
        iTotalFeatures = int(arcpy.GetCount_management(theCatalogPath).getOutput(0))

        # Get input layer information and count the number of input features
        if theDataType == "FEATURELAYER":
            # input layer is a FEATURELAYER, get featurelayer specific information
            defQuery = desc['whereClause']
            fids = desc['FIDSet']
            fidList = list()
            #AddMsgAndPrint(" \nSaved FIDSet: '" + str(fids) + "'")

            if fids != None:
                # save list of feature ids in original selection
                fidList1 = list(fids.split("; "))

                if len(fidList1) > 0:
                    #AddMsgAndPrint(" \nFound " + str(len(fidList1)) + " fids  in list '" + str(fidList1) + "'")
                    for fid in fidList1:
                        fidList.append(int(fid))

                    del fidList1

            layerName = desc['nameString']

            # get count of number of features being processed
            if len(fidList) == 0:
                # No selected features in layer
                iSelection = iTotalFeatures

                if defQuery == "":
                    # No query definition and no selection
                    iSelection = iTotalFeatures
                    AddMsgAndPrint(" \nProcessing all " + Number_Format(iTotalFeatures, 0, True) + " polygons in '" + layerName + "'...")

                else:
                    # There is a query definition, so the only option is to use GetCount
                    iSelection = int(arcpy.GetCount_management(inLayer).getOutput(0))  # Use selected features code
                    AddMsgAndPrint("\nSearching " + Number_Format(iSelection, 0, True) + " of " + Number_Format(iTotalFeatures, 0, True) + " features...")

            else:
                # featurelayer has a selected set, get count using FIDSet
                iSelection = len(fidList)
                AddMsgAndPrint(" \nProcessing " + Number_Format(iSelection, 0, True) + " of " + Number_Format(iTotalFeatures, 0, True) + " features...")

        elif theDataType in ("FEATURECLASS", "SHAPEFILE"):
            # input layer is a featureclass, get featureclass specific information
            layerName = desc['baseName'] + " Layer"
            defQuery = ""
            fids = ""
            fidList = list()

            iSelection = iTotalFeatures
            AddMsgAndPrint(" \nProcessing all " + Number_Format(iTotalFeatures, 0, True) + " polygons in '" + layerName + "'...")


            # still need to create a featurelayer if the user wants to summarize on the basis of some attribute value
            AddMsgAndPrint(" \nCreating featurelayer '" + layerName + "' from featureclass: '" + theCatalogPath + "'")
            arcpy.MakeFeatureLayer_management(theCatalogPath, layerName)
            inLayer = layerName

        # Make sure that input and output datums are the same, no transformations allowed
        if outputSR.name == '':
            outputSR = inputSR
            outputDatum = inputDatum
            #AddMsgAndPrint(" \nSetting output CS to same as input: " + outputSR.name + " \n" + outputDatum + " \n ", 1)

        else:
            outputDatum = outputSR.GCS.datumName
            #AddMsgAndPrint(" \nOutput datum: '" + outputDatum + "'")

        if inputDatum != outputDatum:
            AddMsgAndPrint("Input and output datums do not match",2)

        if outputSR.type.upper() != "PROJECTED":
            if inputDatum in ("D_North_American_1983","D_WGS_1984"):
                # use Web Mercatur as output projection for calculating segment length
                AddMsgAndPrint(" \nInput layer coordinate system is not projected, switching to Web Mercatur (meters)", 1)
                outputSR = CreateWebMercaturSR()

            else:
                AddMsgAndPrint("Unable to handle output coordinate system: " + outputSR.name + " \n" + outputDatum,2)

        else:
            AddMsgAndPrint("\nOutput coordinate system: " + outputSR.name)

        theUnits = outputSR.linearUnitName.lower()
        theUnits = theUnits.replace("foot", "feet")
        theUnits = theUnits.replace("meter", "meters")

        if theUnits.startswith("meter"):
            unitAbbrev = "m"
        else:
            unitAbbrev = "ft"

        if inFieldName == "":
            bProcessed = ProcessLayer(inLayer, fidFld, outputSR)
        else:
            bProcessed = ProcessLayerBySum(inLayer, inField, outputSR)

        # if there was a previous selection on the input layer, reapply
        if theDataType == "FEATURELAYER":
            if len(fidList) > 0:
                if len(fidList) == 1:
                    fidList ="(" + str(fidList[0]) + ")"

                else:
                    fidList = str(tuple(fidList))

                sql = arcpy.AddFieldDelimiters(inLayer, fidFld) + " in " + fidList
                arcpy.SelectLayerByAttribute_management(inLayer, "NEW_SELECTION", sql)

            else:
                arcpy.SelectLayerByAttribute_management(inLayer, "CLEAR_SELECTION")

        if bProcessed:
            if inFieldName == "":
                AddMsgAndPrint("\nProcessing complete \n ")

            else:
                AddMsgAndPrint("\nProcessing complete, join table to the appropriate spatial layer on " + inFieldName + " to create a status map \n ")

    except:
        errorMsg()
