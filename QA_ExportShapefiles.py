# ---------------------------------------------------------------------------
# QA_ExportShapefiles.py
# Created on: May 2013

# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216
#
# Purpose: Export a set of geodatabase featureclasses to SSURGO shapefiles
#
# Soil Data Mart database used the following datum transformation methods to
# move the vector layers from NAD1983 to WGS1984 using ArcGIS 9.x?:
# Output Coordinate System set to "WGS 1984.prj"
#   CONUS - NAD_1983_To_WGS_1984_5
#   Hawaii - NAD_1983_To_WGS_1984_3
#   Alaska - NAD_1983_To_WGS_1984_5
# ---------------------------------------------------------------------------
# QA_ExportShapefiles.py
# Created on: May 2013

# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216
#
#   Puerto Rico and U.S. Virgin Islands - NAD_1983_To_WGS_1984_1
#
# 07-24-2013 Requires all 5 SSURGO featureclasses to be present in the input workspace for
# the export process to execute. This currently includes the 'Survey Boundary' which is
# somewhat controversial.
#
# 07-23-2013 Removed SPATIALVER and SPATIALVERSION fields from export shapefiles
# 07-21-2013 All 5 exported featureclasses are checked for fully populated AREASYMBOLs
# 07-20-2013 Added shapefile schema check and attribute check for the primary attribute field
#
# 07-09-2013 Original coding
#
# 11/13/2013
# Modified to work with Regional Spatial Geodatabase
# Requires all 6 SSURGO feature classes to be present within a Feature dataset.

# v 1.1 (aks)
    # 1) Cleaned up refernces to input featur class by hardening path so 
        # the tool will no longer will pull in arbitrary MUPOLYGON features
        # from map legend.
    # 2) Replaced FeatureClassToFeatureClass with ExportFeatures
    # 3) added arcpyErr and pyErr functions, but didn't replace references
        # of AddMsgAndPrint
# ===============================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:
        f = open(textFilePath,'a+')
        f.write(msg + "\n")
        f.close

        del f

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


def arcpyErr(func):
    try:
        etype, exc, tb = sys.exc_info()
        line = tb.tb_lineno
        msgs = (
            f"ArcPy ERRORS:\nIn function: {func} on line: "
            f"{line}\n{arcpy.GetMessages(2)}\n"
        )
        return msgs
    except:
        return "Error in arcpyErr method"


def pyErr(func):
    try:
        etype, exc, tb = sys.exc_info()
      
        tbinfo = traceback.format_tb(tb)[0]
        msgs = (
            "PYTHON ERRORS:\nTraceback info:\nIn function: "
            f"{func}\n{tbinfo}\nError Info:\n{exc}"
        )
        return msgs
    except:
        return "Error in pyErr method"
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

## ================================================================================================================
def logBasicSettings():
    # record basic user inputs and settings to log file for future purposes

    import getpass, time

    f = open(textFilePath,'a+')
    f.write("\n################################################################################################################\n")
    f.write("Executing \"Export SSURGO Shapefiles\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tFile Geodatabase Feature Dataset: " + inLoc + "\n")
    f.write("\tExport Folder: " + outLoc + "\n")
    #f.write("\tArea of Interest: " + AOI + "\n")

    f.close
    del f

## ===================================================================================
def SSURGOFieldInfo():

    # Creates a dictionary containing SSURGO shapefile field info required for
    # the Staging Server.  Dictionary will be made of the SSURGO data type (KEY) and
    # field attribute information (VALUES).  The dictionary will be returned.
    # No errors should occur.

    # Not sure
    try:
        # establish dictionary
        ssurgoFields = dict()

        # --- MUPOLYGON dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        fldDesc.append(("MUSYM",6,0,0,"String"))
        #fldDesc.append(("MUKEY",30,0,0,"String"))
        ssurgoFields["Map unit polygons"] = fldDesc

        # --- SAPOLYGON dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        #fldDesc.append(("LKEY",30,0,0,"String"))
        ssurgoFields["Survey area polygons"] = fldDesc

        # --- MUPOINT dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        fldDesc.append(("MUSYM",6,0,0,"String"))
        #fldDesc.append(("MUKEY",30,0,0,"String"))
        ssurgoFields["Map unit points"] = fldDesc

        # --- MULINE dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        fldDesc.append(("MUSYM",6,0,0,"String"))
        #fldDesc.append(("MUKEY",30,0,0,"String"))
        ssurgoFields["Map unit lines"] = fldDesc

        # --- FEATLINE dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        fldDesc.append(("FEATSYM",3,0,0,"String"))
        #fldDesc.append(("FEATKEY",30,0,0,"String"))
        ssurgoFields["Feature lines"] = fldDesc

        # --- FEATPOINT dict ----
        fldDesc = list()
        fldDesc.append(("FID",4,0,0,"OID"))
        fldDesc.append(("Shape",0,0,0,"Geometry"))
        fldDesc.append(("AREASYMBOL",20,0,0,"String"))
        fldDesc.append(("FEATSYM",3,0,0,"String"))
        #fldDesc.append(("FEATKEY",30,0,0,"String"))
        ssurgoFields["Feature points"] = fldDesc

        return ssurgoFields

    except:
        errorMsg()
        return ssurgoFields

## ===================================================================================
def GetExportLayers(inLoc):
    # Create and return a list of valid SSURGO featureclasses found in the workspace.
    # Ideally 6 feature classes would be returned (MUPOLYGON, MUPOINT, MULINE, FEATLINE,
    # FEATPOINT, SAPOLYGON).  SAPOLYGON will be ignored since it will be regenerated and

    try:

        # list that contains valid SSURGO feature classes
        exportList = list()

        desc = arcpy.da.Describe(inLoc)
        env.workspace = inLoc

        # ?????? I think we should force input workspace to be feature dataset!!!!
        # List all the feature classes if input is a feature dataset. Typical case
        if desc['dataType'].upper() == "FEATUREDATASET":

            # set workspace environment to the geodatabase instead of FD
            env.workspace = os.path.dirname(inLoc)
            listFC = arcpy.ListFeatureClasses("*","All",desc['baseName'])

        # feature classes are independent ----  May want to get rid of this one!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        else:
            listFC = arcpy.ListFeatureClasses("*")

        AddMsgAndPrint("\nChecking input featureclasses for " + inLoc + " ("+ desc['dataType'] + ")")

        # feature classes found in workspace
        if len(listFC) > 0:

            # Look at each featureclass in the workspace.
            # Check each featureclass to make sure there is only one instance of each SSURGO type
            dCount = {'Map unit polygons':'0','Map unit points':'0','Map unit lines':'0','Feature lines':'0','Feature points':'0','Survey area polygons':'0'}

            # list that contains missing SSURGO feature classes
            missingList = list()

            # Go through each fc in the workspace and determine what SSURGO layer it is
            for fc in listFC:

                # ignore any feature class that begins with "QA_".  These are outputs of the QA tools.
                if fc[0:3] != "QA_":

                    # Get SSURGO data type and fileName ('_a.shp, _b.shp, _l.shp...) fileName is not used here.
                    ssurgoType, fileName = GetFCType(f"{inLoc}/{fc}", "")

                    if ssurgoType in dCount:

                        # switch the 0 to a 1 for the ssurgo layer in the dCount dictionary
                        dCount[ssurgoType] = int(dCount[ssurgoType]) + 1

                        # add the fc to the export list
                        exportList.append(fc)

                    else:
                        # Not a standard SSURGO data layer, skip it
                        pass

            # Check each SSURGO dataType in dictionary to make sure that there are no duplicates or omissisions
            for lyr, iCnt in dCount.items():

                # SSURGO layer is missing
                if int(iCnt) == 0:
                    AddMsgAndPrint("\tMissing input featureclass for " + lyr, 2)
                    missingList.append(lyr)

                # There are duplicate SSURGO layers
                elif int(iCnt) > 1:
                    AddMsgAndPrint("\tInput workspace contains " + str(iCnt) + " possible duplicate featureclasses for '" + lyr + "'", 2)
                    return list()  # return blank list

            if len(missingList) > 0:
                AddMsgAndPrint("\tMissing the following SSURGO data layers: "  + ",".join(missingList), 2)
                return list()  # return blank list

            else:
                if len(exportList) == 6:

                    layerList = ("SAPOLYGON","MUPOLYGON","MULINE","MUPOINT","FEATLINE","FEATPOINT")

                    for layer in exportList:
                        if not layer in layerList:
                            return exportList

                    return layerList

                else:
                    return exportList

        else:
            # No input featureclasses found in the selected workspace
            # This shouldn't happen if the tool validation code is working

            AddMsgAndPrint("\n\tNo featureclasses found in " + inLoc, 2)
            return list()

    except:
        errorMsg()
        return list()

## ===================================================================================
def GetFCType(fc_path, theAS):

    # Determine SSURGO layer name using featuretype and table fields
    # Return string identifying SSURGO data type and shapefilename prefix
    #       ssurgoType = Mapunit Polygon
    #       fileName = "wi025_a.shp"
    # Return two empty strings in case of error

    try:
        featureType = ""
        ssurgoType = ""
        fileName = ""
        fc_name = os.path.basename(fc_path)
        # 2nd measure to exclude layers that begin with "QA_"
        if fc_name[0:3] != "QA_":
            theDescription = arcpy.da.Describe(fc_path)
            featType = theDescription['shapeType']

            # Look for AREASYMBOL field, must be present
            if not FindField(fc_path, "AREASYMBOL"):
                AddMsgAndPrint("\t" + fc_name + " is missing 'AREASYMBOL' field (GetFCName)", 2)
                return ssurgoType, fileName

         # Look for MUSYM field
        if FindField(fc_path, "MUSYM"):

            hasMusym = True

            # fc is MUPOLYGON
            if featType == "Polygon":
                ssurgoType = "Map unit polygons"
                fileName = theAS + "_a.shp"
                return ssurgoType, fileName

            # fc is MULINE
            elif featType == "Polyline" or featType == "Line":
                ssurgoType = "Map unit lines"
                fileName = theAS + "_c.shp"
                return ssurgoType, fileName

            # fc is MUPOINT
            elif featType == "Point" or featType == "Multipoint":
                ssurgoType = "Map unit points"
                fileName = theAS + "_d.shp"
                return ssurgoType, fileName

            # fc has MUSYM but not valid SSURGO layer
            else:
                AddMsgAndPrint("\t" + fc_name + " is an unidentified " + featType + " featureclass with an MUSYM field (GetFCName)",2)
                return ssurgoType, fileName

        else:
            hasMusym = False

        # Look for FEATSYM field
        if FindField(fc_path, "FEATSYM"):

            hasFeatsym = True

            # fc is FEATLINE
            if featType in ("Polyline", "Line"):
                ssurgoType = "Feature lines"
                fileName = theAS + "_l.shp"
                return ssurgoType, fileName

            # fc is FEATPOINT
            elif featType in ("Point", "Multipoint"):
                ssurgoType = "Feature points"
                fileName = theAS + "_p.shp"
                return ssurgoType, fileName

            # fc has featsym but not valid SSURGO layer
            else:
                AddMsgAndPrint("\t" + fc_name + " is an unidentified " + featType + " featureclass with an FEATSYM field (GetFCName)",2)
                return ssurgoType, fileName

        else:
            hasFeatsym = False

        # Survey Area Boundary
        if not (hasMusym) and not (hasFeatsym):

            # No MUSYM present, no FEATSYM present and Polygon, must be SAPOLYGON
            if featType == "Polygon":

                ssurgoType = "Survey area polygons"
                fileName = theAS + "_b.shp"
                return ssurgoType, fileName

            else:
                AddMsgAndPrint("\t" + fc_name + " is an unidentified " + featType + " featureclass with no MUSYM or FEATSYM field (GetFCName)", 2)
                return ssurgoType, fileName

    except:
        errorMsg()
        return "", ""

## ===================================================================================
def FindField(fc_path, fldName):
    # Look for specified attribute field (fldName) in target featureclass (fc)
    # return True if attribute field was found
    # return False if attribute field was not found

    try:

        bFound = False
        desc = arcpy.da.Describe(fc_path)
        fldList = desc['fields']

        for fld in fldList:

            if fld.baseName.upper() == fldName.upper():
                bFound = True
                break

        return bFound

    except:

        errorMsg()
        return False

## ===================================================================================
def CheckAttributes(fc_path, ssurgoType):

    # check to make sure the primary attribute fields are populated
    # with data and no NULL records exist.
    # Return False if fc contains empty records, True otherwise.

    try:
        # Set target fieldname and data type (normally text or string)

        # _a, _c, _d shapefile
        if ssurgoType in ("Map unit polygons","Map unit points","Map unit lines"):
            fldName = "MUSYM"

        # _p, _l shapefile
        elif ssurgoType in ("Feature points","Feature lines"):
            fldName = "FEATSYM"

        # _b shapefile
        elif ssurgoType == "Survey area polygons":
            fldName = "AREASYMBOL"

        # if fc has features, check for NULLS or spaces
        if int(arcpy.GetCount_management(fc_path).getOutput(0)) > 0:

            # Adds field delimiters to a field name to use in SQL queries
            qFld = arcpy.AddFieldDelimiters(fc_path, fldName)

            # query to filter blank or NULL values
            sQuery = qFld + " IS NULL OR TRIM(LEADING ' ' FROM " + qFld + ") = '' OR " + qFld + " LIKE '% %'"

            # return a list of OIDs for features that are blank/NULL
            fields = ["OID@"]
            values = [row[0] for row in arcpy.da.SearchCursor(fc_path, (fields), sQuery)]

            # Report any blank values
            if len(values) > 0:
                AddMsgAndPrint("\tMissing " + str(len(values)) + " " + fldName + " value(s) in " + os.path.basename(fc_path) + " layer:",2)

                for value in values:
                    AddMsgAndPrint("\t\tObjectID: {0}".format(value),2)

                return False

            else:
                return True

        # fc has no records
        else:
            return True

    except:
        errorMsg()
        return False

#### ===================================================================================
##def CheckAreasymbol(fc):
##    # Make sure that the input featureclass has fully populated AREASYMBOL
##
##    try:
##        # evaluate fc if it has features
##        if int(arcpy.GetCount_management(fc).getOutput(0)) > 0:
##
##            # Adds field delimiters to a field name to for use in SQL queries
##            qFld = arcpy.AddFieldDelimiters(fc, "AREASYMBOL")
##
##            # query to filter blank or NULL values
##            sQuery = qFld + "IS NULL OR TRIM(LEADING ' ' FROM " + qFld + ") = ''"
##
##            # return a list of OIDs for features that are blank/NULL
##            fields = ["OID@"]
##            values = [row[0] for row in arcpy.da.SearchCursor(fc, (fields), sQuery)]
##
##            # Report any blank values
##            if len(values) > 0:
##                AddMsgAndPrint("\tMissing AREASYMBOL value(s) in " + os.path.basename(fc) + " layer:",2)
##
##                for value in values:
##                    print("\t\tObjectID: {0}".format(value))
##
##                return False
##
##            else:
##                return True
##
##        # fc has no records
##        else:
##            return True
##
##    except:
##        errorMsg()
##        return False

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    # returns a formatted number according to current locality and given places
    # commas will be inserted if bCommas is True
    # returns the input num if error is raised

    try:

        #locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()
        return num

## ===================================================================================
def SetOutputCoordinateSystem(fc_path):
    # This function will compare the geographic coord sys of the inLayer to
    # the spatial reference 4326 (GCS_WGS_1984).  If they are different then
    # an ESRI datum transformation method will be applied based on the geographic
    # extent the user chose.  The output coordinate system (4326) and geographic
    # transformation environment variable will be set. Return True if everything
    # worked, False otherwise.
    #
    #   CONUS - NAD_1983_To_WGS_1984_5
    #   Hawaii - NAD_1983_To_WGS_1984_3
    #   Alaska - NAD_1983_To_WGS_1984_5
    #   Puerto Rico and U.S. Virgin Islands - NAD_1983_To_WGS_1984_1
    #   Other  - NAD_1983_To_WGS_1984_1 (shouldn't run into this case)

    try:
        #---------- Gather Spatial Reference info ----------------------------
        # Create the GCS WGS84 spatial reference using the factory code
        outputSR = arcpy.SpatialReference(4326)

        # Name of geographic coordinate system GCS_WGS_1984
        outputGCS = outputSR.GCS.name
        # input spatial reference
        desc = arcpy.da.Describe(fc_path)
        dType = desc['dataType']
        sr = desc['spatialReference']
        srType = sr.type.upper()
        inputGCS = sr.GCS.name

        # Print name of input layer and dataype
        if dType.upper() == "FEATURELAYER":
            inputName = desc['nameString']

        elif dType.upper() == "FEATURECLASS":
            inputName = desc['baseName']

        else:
            inputName = desc['name']

        # -----------
        # input and output geographic coordinate systems are the same
        # no datum transformation method required
        if outputGCS == inputGCS:
            AddMsgAndPrint("\nNo datum transformation required")
            #tm = ""

        else:
            AddMsgAndPrint("\tUsing datum transformation method 'WGS_1984_(ITRF00)_To_NAD_1983' \n ")

        """   COMMENTED THIS OUT AND HARD CODED THE TRANSFORMATION TO ITRF00 """
##
##        # More than likely input will be GCS_North_American_1983 and will
##        # require datum transformation.  Select datum transformation based
##        # on user input.
##        else:
##
##            if AOI == "CONUS":
##                tm = "NAD_1983_To_WGS_1984_5"
##
##            elif AOI == "Alaska":
##                tm = "NAD_1983_To_WGS_1984_5"
##
##            elif AOI == "Hawaii":
##                tm = "NAD_1983_To_WGS_1984_3"
##
##            elif AOI == "Puerto Rico and U.S. Virgin Islands":
##                tm = "NAD_1983_To_WGS_1984_5"
##
##            elif AOI == "Other":
##                tm = "NAD_1983_To_WGS_1984_1"
##                AddMsgAndPrint("\nWarning! No coordinate shift is being applied", 0)
##
##            else:
##                raise MyError, "Invalid geographic region (" + AOI + ")"

        # Set the output coordinate system environment
        arcpy.env.outputCoordinateSystem = outputSR    # GCS_WGS_1984
        arcpy.env.geographicTransformations =  "WGS_1984_(ITRF00)_To_NAD_1983"       # Transformation Method

        # Prompt user of the datum transformation being used
        #if tm != "":
        #AddMsgAndPrint("\n\tUsing datum transformation method 'WGS_1984_(ITRF00)_To_NAD_1983' \n ", 1)

        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

## ===================================================================================
def GetFieldInfo(fc_path, ssurgoType, oldFields):

    # Create and return FieldMapping object containing valid SSURGO fields. Fields
    # that are not part of SSURGO will not be included.

    try:
        # Dictionary containing valid fields for SSURGO layers
        dFieldInfo = dict()

        dFieldInfo["Map unit polygons"] = ['AREASYMBOL','MUSYM']
        dFieldInfo["Map unit points"] = ['AREASYMBOL','MUSYM']
        dFieldInfo["Map unit lines"] = ['AREASYMBOL','MUSYM']
        dFieldInfo["Feature lines"] = ['AREASYMBOL','FEATSYM']
        dFieldInfo["Feature points"] = ['AREASYMBOL','FEATSYM']
        dFieldInfo["Survey area polygons"] = ['AREASYMBOL']

        # assign fields based on the ssurgoType (i.e. "Map unit points")
        outFields = dFieldInfo[ssurgoType]

        # Create required FieldMappings object and add the fc table as a
        # FieldMap object
        fms = arcpy.FieldMappings()
        fms.addTable(fc_path)

        # loop through each field in FieldMappings object
        for fm in fms.fieldMappings:

            # Field object containing the properties for the field (aliasName...)
            outFld = fm.outputField

            # Name of the field
            fldName = outFld.name

            # remove field from FieldMapping object if it is 'OID' or 'Geometry'
            # or not in dFieldInfo dictionary (SSURGO schema)
            if not fldName in outFields:
                fms.removeFieldMap(fms.findFieldMapIndex(fldName))

        for fldName in outFields:
            newFM = fms.getFieldMap(fms.findFieldMapIndex(fldName))
            fms.removeFieldMap(fms.findFieldMapIndex(fldName))
            fms.addFieldMap(newFM)

        return fms

    except:
        errorMsg()
        fms = arcpy.FieldMappings()
        return fms

## ===================================================================================
def CheckFieldInfo(outFC, ssurgoSchema):
    # Compare the new output shapefile table design with the SSURGO standard as
    # defined in the 'SSURGOFieldInfo' function

    try:
        fields = arcpy.da.Describe(outFC)['fields']
        inSchema = []

        for fld in fields:
            inSchema.append((fld.baseName, fld.length, fld.precision, fld.scale, fld.type))

        if inSchema == ssurgoSchema:
            return True

        else:
            AddMsgAndPrint("Schema mismatch problem with " + outFC + " attribute table", 2)
            AddMsgAndPrint("-----------------------------------------------------",2)
            AddMsgAndPrint("\tOutput ShapeFile: " + str(inSchema), 2)
            AddMsgAndPrint("\n\tSSURGO Standard: " + str(ssurgoSchema), 2)
            return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSSA(fc_out,loc,AS):

    # Create Survey Area Boundary by dissolving Mapunit Polygon layer.
    # Returns False if no features were generated after the dissolve or if
    # _b layer already exists, otherwise return True.

    try:

        # path to the Soil Survey Area boundary shapefile export
        SSApath = os.path.join(loc, AS.lower() + "_b.shp")

        # return false if shapefile already exists
        if env.overwriteOutput == False and arcpy.Exists(SSApath):
            AddMsgAndPrint("Output shapefile (" + os.path.basename(SSApath) + ") already exists", 2)
            return False

        arcpy.Dissolve_management(
            fc_out, SSApath, "AREASYMBOL", "", "SINGLE_PART"
        )

        # Notify user of the amount of SSA features exported
        ssaCnt = int(arcpy.GetCount_management(SSApath).getOutput(0))

        if ssaCnt < 1:
            AddMsgAndPrint("\n\t" + os.path.basename(SSApath) + " has no features",2)
            return False

        else:
            AddMsgAndPrint("\tSurvey area polygons: " + Number_Format(ssaCnt, 0, True) + " features exported", 0)

        del SSApath
        del ssaCnt

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def GetLayerExtent(layer):

    try:

        desc = arcpy.Describe(layer)

        layerExtent = []

        layerExtent.append(desc.extent.XMin)
        layerExtent.append(desc.extent.XMax)
        layerExtent.append(desc.extent.YMax)
        layerExtent.append(desc.extent.YMin)

        if len(layerExtent) == 4:
            #arcpy.AddMessage(" ")
            AddMsgAndPrint("\tSurvey Bounding Coordinates: ",0)
            AddMsgAndPrint("\t\tWest_Bounding_Coordinate: " + str(layerExtent[0]),0)
            AddMsgAndPrint("\t\tEast_Bounding_Coordinate: " + str(layerExtent[1]),0)
            AddMsgAndPrint("\t\tNorth_Bounding_Coordinate: " + str(layerExtent[2]),0)
            AddMsgAndPrint("\t\tSouth_Bounding_Coordinate: " + str(layerExtent[3]) + "\n ",0)

        else:
            return False
            #AddMsgAndPrint("\n\tCould not determine Spatial Domain of " + os.path.basename(layer)

        del layerExtent
        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def GetFolderSize(start_path):

    try:

        total_size = 0

        for dirpath, dirnames, filenames in os.walk(start_path):

            for f in filenames:

                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        return Number_Format(float(total_size)/1048576,1,False)

    except:
        errorMsg()
        return 0

## ===================================================================================
def ProcessSurveyArea(inLoc, exportList, outLoc, theAS, ssurgoFields, msg):
    # Check each layer in the workspace. If it's a valid SSURGO layer, export it
    # to a WGS 1984 shapefile.
    # Skips any featureclass whose name begins with 'QA_'

    try:

        # Create final output folder for the output shapefiles, if it doesn't exist
        if not arcpy.Exists(os.path.join(outLoc, theAS.lower())):
            arcpy.CreateFolder_management(outLoc, theAS.lower())

        else:
            AddMsgAndPrint("\t" + theAS.lower() + " Folder Exists; Contents will be overwritten\n",1)

        # directory path to the export folder
        surveyLoc = os.path.join(outLoc, theAS.lower())
        sQuery = '"AREASYMBOL" = ' + "'" + theAS + "'"

        # How many unique point and linear features exist
        uniqueSpecFeatureCount = 0
        uniquefeatList = list()

        # for each valid SSURGO layer in workspace export the Areasymbol as a shapefile
        layerCount = 0

        # Establish progressor object which allows progress info to be passed to dialog box.
        arcpy.SetProgressor("step", " ", 0, len(exportList), 1)

        for fc in exportList:

            arcpy.SetProgressorLabel("\nExporting Soil Survey: " + theAS + " " + str(msg))

            layerCount += 1
            fc_path = f"{inLoc}/{fc}"
            # Get SSURGO data type ('Mapunit Polygon') and fileName ('wi025_a.shp)
            ssurgoType, fileName = GetFCType(fc_path, theAS.lower())

            oldFields = arcpy.Describe(fc_path).fields

            # ++++++++++++++++++++++++++
            # Do not export the SSA from the fc layer. The SSA boundary
            # will instead be dissolved from the Mapunit Polygon Layer
            # Comment out next 2 lines if SSA is ever exported directly
            # from Survey Area Boundary Layer
            if ssurgoType == "Survey area polygons":
                continue

            # evaluate and return only valid SSURGO fields
            fldInfo = GetFieldInfo(fc_path, ssurgoType, oldFields)

            # process if more than 1 field was returned
            if fldInfo.fieldCount > 0:

                # path to the export shapefile
                outFC = os.path.join(surveyLoc, fileName)

                # return false if shapefile already exists
                if env.overwriteOutput == False and arcpy.Exists(outFC):
                    AddMsgAndPrint("Output shapefile (" + outFC + ") already exists", 2)
                    return False

                # Convert areasymbol selection to a shapefile
                arcpy.conversion.ExportFeatures(
                    fc_path,
                    f"{surveyLoc}/{fileName}",
                    sQuery,
                    field_mapping=fldInfo
                )

                # Failed to export shapefile
                if not arcpy.Exists(outFC):
                    AddMsgAndPrint("Failed to create output shapefile (" + outFC + ")", 2)
                    return False

                # if there are features in layer check the schema and attribute field
                iCnt = int(arcpy.GetCount_management(outFC).getOutput(0))
                if iCnt > 0:

                    # Check output shapefile schema
                    if not CheckFieldInfo(outFC, ssurgoFields[ssurgoType]):
                        # arcpy.Delete_management(surveyLoc)
                        return False


                    # Check primary attribute field for missing values
                    if not CheckAttributes(outFC, ssurgoType):
                        # arcpy.Delete_management(surveyLoc)
                        return False

                    # Tally and gather unique special feature points and line
                    if ssurgoType == "Feature points" or ssurgoType == "Feature lines":

                        fields = ["FEATSYM"]

                        with arcpy.da.SearchCursor(outFC,fields) as cursor:

                            for row in cursor:
                                if not row[0] in uniquefeatList:
                                    uniquefeatList.append(row[0])
                                    uniqueSpecFeatureCount += 1

                        del fields

                    AddMsgAndPrint("\t" + ssurgoType + " exported: " + Number_Format(iCnt, 0, True), 0)

                else:
                    AddMsgAndPrint("\t" + ssurgoType + " exported: " + Number_Format(iCnt, 0, True), 0)
                    #arcpy.Delete_management(outFC)

                # Create survey boundary if _a layer by dissolving it
                if ssurgoType == "Map unit polygons" and not CreateSSA(outFC,surveyLoc,theAS):
                    # arcpy.Delete_management(surveyLoc)
                    return False

                # strictly formatting
                if layerCount == 6:
                    AddMsgAndPrint("\n",0)

                del outFC, iCnt

            # failed to get field info
            else:
                return False

            del ssurgoType, fileName, oldFields, fldInfo

            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()

        # Report the # of unique features and list them if there are any
        uniquefeatList.sort()

        if uniqueSpecFeatureCount > 0:
            #arcpy.AddMessage(" ")
            AddMsgAndPrint("\t" + "Unique Special Feature Count: " + Number_Format(uniqueSpecFeatureCount, 0, True))

            for feat in uniquefeatList:
                AddMsgAndPrint("\t" + feat)

        # Report out extent of SAPOLYGON layer
        if not GetLayerExtent(os.path.join(surveyLoc,theAS.lower() + "_b.shp")):
            AddMsgAndPrint("\n\tCould not determine Spatial Domain of " + os.path.basename(layer) + "\n",2)

        folderSize = GetFolderSize(surveyLoc)
        AddMsgAndPrint("\t" + "Directory Size: " + str(folderSize) + " MB",0)

        # remove all .xml files
        for file in os.listdir(surveyLoc):
            if file.endswith('.xml'):
                os.remove(os.path.join(surveyLoc, file))

        return True

    except:
        errorMsg()
        return False

# ========================================= Main Body ================================================
import string, os, sys, traceback, locale, arcpy
from arcpy import env

if __name__ == '__main__':

    try:
        v = '1.1'
        arcpy.AddMessage(f"version: {v}")
        # 4 Script arguments...
        inLoc = arcpy.GetParameterAsText(0)         # input workspace or featuredataset
        outLoc = arcpy.GetParameterAsText(1)        # output folder where shapefiles will be placed
        asList = arcpy.GetParameter(2)              # List of Areasymbol values to beexported from the geodatabase

        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # path to textfile that will log messages
        textFilePath = outLoc + os.sep + "SSURGO_export.txt"

        # record basic user inputs and settings to log file for future purposes
        logBasicSettings()

        # Set workspace to the input geodatabase or featuredataset
        env.workspace = inLoc

        # list containing any problem ssurveys
        problemSurveys = []

        # Create dictionary of field information for SSURGO shapefiles
        # This will be used to check the output shapefiles for correct schema
        ssurgoFields = SSURGOFieldInfo()

        # Get a list of valid SSURGO featureclasses found in the input workspace
        exportList = GetExportLayers(inLoc)

        # Make sure each valid SSURGO fc has AREASYMBOL fully populated; MUSYM/FEATSYM is checked after
        # the data has been exported.  If nulls occur there, the entire survey is deleted.
        for fc_name in exportList:
            fc_path = f"{inLoc}/{fc_name}"
            if not CheckAttributes(fc_path,"Survey area polygons"):
                AddMsgAndPrint("Halting export process",2)
                exit()

        # should have exactly 6 feature classes found
        if len(exportList) == 0:
            AddMsgAndPrint("\tFound no required SSURGO featureclasses........Halting export process",2)

        elif len(exportList) < 6:
            AddMsgAndPrint("\tFailed to find all 6 required input SSURGO featureclass types",2)
            exit()

        elif len(exportList) > 6:
            AddMsgAndPrint("\tFound more than the 6 required input SSURGO featureclass types",2)
            exit()

        AddMsgAndPrint("\nExporting SSURGO shapefiles for " + Number_Format(len(asList), 0, True) + " survey area(s) to folder '" + outLoc + "'")

        # if featuredataset is enforced then we can set the env.coord system using any fc from within the export list
        # and not have to check transformation everytime we export an individual SSA .shp.
        # set output coordinate system env variable to (4326 - WGS84)

        bSR = False
        for fc_name in exportList:
            fc_path = f"{inLoc}/{fc_name}"
            ssurgoType, fileName = GetFCType(fc_path, "")
            if ssurgoType == "Map unit polygons":

                bSR = SetOutputCoordinateSystem(fc_path)
                break

        # Either Mapunit Polygon was not found or not able to set spatial reference
        if not bSR:
            AddMsgAndPrint("Failed to set output spatial reference!....Halting export process",2)
            exit()

        # Establish progressor object which allows progress info to be passed to dialog box.
        arcpy.SetProgressor("step", "Exporting SSURGO shapefiles for " + Number_Format(len(asList), 0, True) + " soil surveys...",  0, len(asList))

        # Process each soil survey, one at a time.  If a problem occurs,
        # it will be reported but nothing will be deleted

        iCnt = 1
        for theAS in asList:

            arcpy.SetProgressorLabel("Exporting Soil Survey: " + theAS + " (" + str(iCnt) + " of " + str(len(asList)) + ")")
            msgString = " (" + str(iCnt) + " of " + str(len(asList)) + ")"

            AddMsgAndPrint("\nExporting Soil Survey: " + theAS)
            AddMsgAndPrint("-------------------------------------------------------")

            bProcessed = ProcessSurveyArea(inLoc, exportList, outLoc, theAS, ssurgoFields, msgString)
            del msgString

            if bProcessed == False:
                AddMsgAndPrint("\n\tSoil Survey Area " + theAS + "  will not be exported",2)
                problemSurveys.append(theAS)

            iCnt += 1

            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()
        del iCnt

        AddMsgAndPrint("\n=======================================================")

        # Report problem surveys
        if len(problemSurveys) > 0:
            AddMsgAndPrint("The following survey(s) failed to export: " + ", ".join(problemSurveys),2)
            AddMsgAndPrint("\n" + Number_Format(len(asList) - len(problemSurveys), 0, True) + " of " + Number_Format(len(asList), 0, True) + " surveys were exported to the '" + outLoc + "' folder")

        else:
            if len(asList) > 2:
                AddMsgAndPrint("\nAll " + Number_Format(len(asList), 0, True) + " surveys successfully exported to the '" + outLoc + "' folder")

            elif len(asList) == 1:
                AddMsgAndPrint("\nSelected survey (" + asList[0] + ") successfully exported to the '" + outLoc + "' folder")

            elif len(asList) == 2:
                AddMsgAndPrint("\nBoth selected surveys successfully exported to the '" + outLoc + "' folder")

            elif len(asList) == 0:
                AddMsgAndPrint("\nNo surveys were exported",2)

    except:
        errorMsg()
