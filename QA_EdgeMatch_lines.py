# ---------------------------------------------------------------------------
# QA_EdgeMatch_lines.py
# Created on:
#
# Steve Peaslee, National Soil Survey Center
# Whityn Owen, Soil Survey Region 1

# Identifies where node-to-node joins across survey boundaries do NOT occur
# Only spatial data is tested; does not check MUKEY/MUSYM
# If mis-matches are found, they will be copied to a new featureclass and added to the
# ArcMap TOC.
#
# ArcGIS 10.1 compatible
#

# ============================================================================================================
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

# ===================================================================================
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

# ===================================================================================
# This function is not currently called but is left in for future use

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
        #AddMsgAndPrint("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

# ===================================================================================
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

# Import system modules
import sys, string, os, traceback, locale, tempfile, time, arcpy

if __name__ == '__main__':

    try:

        # Script arguments...
        inLayer = arcpy.GetParameterAsText(0)       # required input soils layer with at least two survey areas to compare
        inField = arcpy.GetParameterAsText (1)      # The field containing AREASYMBOL values
        ssaList = arcpy.GetParameter(2)             # List of AREASYMBOLs from Tool Validation code
        layerName = arcpy.GetParameter(3)           # output featurelayer containing dangling points (not required)

        # Check out ArcInfo license for PolygonToLine
        arcpy.SetProduct("ArcInfo")
        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True
        arcpy.env.XYTolerance = 0
        arcpy.env.addOutputsToMap = False

        AddMsgAndPrint("\nProcessing " + inLayer +  " SSAs: " + str(ssaList))

        # Start by getting information about the input layer
        descInput = arcpy.Describe(inLayer)
        inputDT = descInput.dataType.upper()

        if inputDT == "FEATURELAYER":
            inputName = descInput.Name
            inputFC = descInput.FeatureClass.catalogPath

        elif inputDT == "FEATURECLASS":
            inputName = descInput.Name
            inputFC = descInput.catalogPath

        # Get workspace information
        theWorkspace = os.path.dirname(inputFC)
        descW = arcpy.Describe(theWorkspace)
        wkDT = descW.DataType.upper()

        if wkDT == "FEATUREDATASET":
            theWorkspace = os.path.dirname(theWorkspace)

        # Setting workspace to that of the input soils layer
        arcpy.env.workspace = theWorkspace

        # Set scratchworkspace and then proceed with processing
        if setScratchWorkspace():

            # get the first input field object
            chkFields = arcpy.ListFields(inputFC, inField + "*")

            if len(chkFields) == 1:
                chkField = chkFields[0]
                fldName = chkField.name
                fldLength = chkField.length

            else:
                AddMsgAndPrint("Problem getting field info for " + inField,2)
                exit()

            # set name and location for temporary and permanent output features
            diss_Bound = os.path.join(arcpy.env.scratchGDB, "xxDissBound") # temporary featureclass containing survey areas derived from soil poly dissolve
            soil_lines = os.path.join(arcpy.env.scratchGDB, "xxSoilLines") # temporary featureclass containing soil polys converted to lines
            misMatch = os.path.join(arcpy.env.scratchGDB, "Survey_Join_Error_p") # temporary output featureclass containing dangling vertices (join errors)
            misMatch2 = os.path.join(arcpy.env.workspace, "QA_EdgeMatch_Errors_p")
            finalFL = "QA_EdgeMatch_Errors_p"

            # set final output to shapefile if input is shapefile and make the new field name compatible with the database type
            if inputFC.endswith(".shp"):
                misMatch = misMatch + ".shp"
                fldName = fldName[0:10]

            # set output map layer name
            selSoilsFL = "Selected Soils (by " +fldName + ")"

            # Build selection query string from AREASYMBOL list (ssaList)
            try:
                i = 0
                sQuery = ""
                numOfAreas = len(ssaList)
                for area in ssaList :
                    i += 1
                    if i < numOfAreas :
                        sQuery = sQuery + arcpy.AddFieldDelimiters(inputFC, fldName) + " = '" + area + "' OR "
                    else :
                        sQuery = sQuery + arcpy.AddFieldDelimiters(inputFC, fldName) + " = '" + area + "')"
                sQuery = "(" + sQuery

            except:
                AddMsgAndPrint("Unable to build Selection Query String from Areasymbol Parameter",2)
                exit()

            # Make feature layer of selected surveys based on ssaList parameter
            ## THIS IS CREATED IN SOURCE WORKSPACE, NOT scratchWorkspace ##
            arcpy.MakeFeatureLayer_management(inputFC, selSoilsFL, sQuery)

            # Edge Matching checks start here
            try:
                # Dissolve soils to create boundaries
                arcpy.Dissolve_management(selSoilsFL, diss_Bound, inField)
                AddMsgAndPrint("Dissolved input to create boundary", 0)

                # Convert Soil polys to line for Selected surveys
                arcpy.PolygonToLine_management(selSoilsFL, soil_lines, "IDENTIFY_NEIGHBORS")
                AddMsgAndPrint("Converted Soils to lines", 0)

                # Make soil_lines a Feature Layer
                arcpy.MakeFeatureLayer_management(soil_lines, "soil_linesFL")

                # Build whereclause for Select by Attribute
                whereclause = """%s = -1""" % arcpy.AddFieldDelimiters("soil_linesFL", 'LEFT_FID')
                AddMsgAndPrint("Built where clause " + whereclause)

                # Select soil_lines cooincident with dissolved boundary layer
                arcpy.SelectLayerByLocation_management("soil_linesFL", "SHARE_A_LINE_SEGMENT_WITH", diss_Bound)
                AddMsgAndPrint("Selected lines based on boundary", 0)

                selBoundaryLines = arcpy.GetCount_management("soil_linesFL").getOutput(0)

                AddMsgAndPrint("Select by location selected " + str(selBoundaryLines) + " features")

                if int(selBoundaryLines) > 0 :
                    arcpy.SelectLayerByAttribute_management("soil_linesFL","REMOVE_FROM_SELECTION", whereclause)
                    AddMsgAndPrint("Removed perimeter lines from selection")

                    # Delete interior soil survey boundaries in soil_lines feature layer
                    arcpy.DeleteFeatures_management("soil_linesFL")
                    AddMsgAndPrint("Deleted features",0)

                    # Convert only dangling vertices to permanent feature class
                    arcpy.FeatureVerticesToPoints_management(soil_lines, misMatch,"DANGLE")
                    AddMsgAndPrint("Converted dangling vertices to points")

                else:
                    AddMsgAndPrint("Trouble selecting boundaries in soil lines layer",2)
                    exit()

                iProblems = int(arcpy.GetCount_management(misMatch).getOutput(0))
                AddMsgAndPrint("Errors found: " + str(iProblems),1)

                if iProblems > 0:
                    # Found at least one dangling node problem.
                    # Report finding, create MisMatch featureclass and display in ArcMap
                    arcpy.CopyFeatures_management(misMatch, misMatch2)
                    AddMsgAndPrint("copied to misMatch2")

                    # Add new field to track 'fixes'
                    arcpy.Delete_management(misMatch)
                    AddMsgAndPrint("Deleted misMatch", 0)

                    arcpy.AddField_management(misMatch2, "Status", "TEXT", "", "", 10, "Status")
                    AddMsgAndPrint("Added Fields")

                    try:
                        #arcpy.mapping.MapDocument("Current")
                        arcpy.MakeFeatureLayer_management(misMatch2, finalFL)
                        AddMsgAndPrint("Made feature layer")

                        arcpy.SetParameter(3, finalFL)

                        lyrFile = os.path.join(os.path.dirname(sys.argv[0]), "RedDot.lyrx")
                        AddMsgAndPrint("Made layer file")

                        arcpy.ApplySymbologyFromLayer_management(finalFL, lyrFile)
                        AddMsgAndPrint("Applied symbology")

                        AddMsgAndPrint("\n Adding 'QA_EdgeMatch_Errors_p' layer with " + str(iProblems) + " features to ArcMap", 1)
                        AddMsgAndPrint(theWorkspace + " \n ", 1)

                    except:
                        AddMsgAndPrint("Feature class 'QA_EdgeMatch_Errors_p' created in " + theWorkspace)


                else:
                    AddMsgAndPrint(" \nNo common-attribute line problems found for " + inputName, 1)
                    arcpy.Delete_management(misMatch)

            except:
                errorMsg()

        else:
            AddMsgAndPrint(" \nFailed to set scratchworkspace \n", 2)

    except:
        errorMsg()


