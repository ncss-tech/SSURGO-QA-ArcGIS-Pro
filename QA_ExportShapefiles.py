#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""---------------------------------------------------------------------------
QA_ExportShapefiles.py
Created on: May 2013

Purpose: Export a set of geodatabase featureclasses to SSURGO shapefiles

Author: Adolfo.Diaz
e-mail: adolfo.diaz@usda.gov
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov
@modified 03/30/2026
    @by: Alexnder Stum
@Version: 1.2

# --- Update v 1.2, 03/30/2026
- Revamped GetExportLayers function to explicitly look for specifically named
features.
- Removed AddMsgAndPrint and replaced with arcpy AddError, AddWarning, and 
AddMessage functions
- Removed errorMsg function, replaced pyErr and arcpyErr functions in except
blocks
- Removed Number_Format function and implemented f-strings
- Cleaned up code formating

Soil Data Mart database used the following datum transformation methods to
move the vector layers from NAD1983 to WGS1984 using ArcGIS 9.x?:
Output Coordinate System set to "WGS 1984.prj"
  CONUS - NAD_1983_To_WGS_1984_5
  Hawaii - NAD_1983_To_WGS_1984_3
  Alaska - NAD_1983_To_WGS_1984_5
---------------------------------------------------------------------------
QA_ExportShapefiles.py
Created on: May 2013

Author: Adolfo.Diaz
        GIS Specialist
        National Soil Survey Center
        USDA - NRCS
e-mail: adolfo.diaz@usda.gov
phone: 608.662.4422 ext. 216

  Puerto Rico and U.S. Virgin Islands - NAD_1983_To_WGS_1984_1

07-24-2013 Requires all 5 SSURGO featureclasses to be present in the input 
workspace for
the export process to execute. This currently includes the 'Survey Boundary' 
which is
somewhat controversial.

07-23-2013 Removed SPATIALVER and SPATIALVERSION fields from export shapefiles
07-21-2013 All 5 exported featureclasses are checked for fully populated 
AREASYMBOLs
07-20-2013 Added shapefile schema check and attribute check for the primary 
attribute field

07-09-2013 Original coding

11/13/2013
Modified to work with Regional Spatial Geodatabase
Requires all 6 SSURGO feature classes to be present within a Feature dataset.

v 1.1 (aks)
    1) Cleaned up refernces to input featur class by hardening path so 
        the tool will no longer will pull in arbitrary MUPOLYGON features
        from map legend.
    2) Replaced FeatureClassToFeatureClass with ExportFeatures
    3) added arcpyErr and pyErr functions, but didn't replace references
        of AddMsgAndPrint
"""
v = '1.2'


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
    

## =============================================================================
def logBasicSettings():
    # record basic user inputs and settings to log file for future purposes

    import getpass, time

    f = open(textFilePath,'a+')
    f.write("\n#############################################################\n")
    f.write("Executing \"Export SSURGO Shapefiles\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tFile Geodatabase Feature Dataset: " + inLoc + "\n")
    f.write("\tExport Folder: " + outLoc + "\n")
    #f.write("\tArea of Interest: " + AOI + "\n")

    f.close
    del f

## =============================================================================
def SSURGOFieldInfo():

    # Creates a dictionary containing SSURGO shapefile field info required for
    # the Staging Server.  Dictionary will be made of the SSURGO data type (KEY) 
    # and
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

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return ssurgoFields
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return ssurgoFields

## =============================================================================
def GetExportLayers(inLoc):
    # Create and return a list of valid SSURGO featureclasses found in the 
    # workspace.
    # Ideally 6 feature classes would be returned (
    # MUPOLYGON, MUPOINT, MULINE, FEATLINE,
    # FEATPOINT, SAPOLYGON).  SAPOLYGON will be ignored since it will 
    # be regenerated and

    try:
        # list that contains valid SSURGO feature classes
        layer_d = {"SAPOLYGON": "Polygon",
                     "MUPOLYGON": "Polygon",
                     "MULINE": "Polyline",
                     "MUPOINT": "Point",
                     "FEATLINE": "Polyline",
                     "FEATPOINT": "Point"}

        env.workspace = inLoc
        missing_b = False
        for feat, gtype in layer_d.items():
            if not arcpy.ListFeatureClasses(feat, gtype):
                arcpy.AddError("Missing RTSD feature: {feat}")
                missing_b = True
        
        if missing_b:
            return []
        else:
            return ["SAPOLYGON", "MUPOLYGON", "MULINE",
                     "MUPOINT", "FEATLINE", "FEATPOINT"]

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return list()
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return list()


## =============================================================================
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
                arcpy.AddError(
                    f"\t{fc_name} is missing 'AREASYMBOL' field (GetFCName)"
                )
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
                arcpy.AddError(
                    f"\t{fc_name} is an unidentified {featType}"
                    " featureclass with an MUSYM field (GetFCName)"
                )
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
                arcpy.AddError(
                    f"\t{fc_name} is an unidentified {featType}" 
                    " featureclass with an FEATSYM field (GetFCName)"
                )
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
                arcpy.AddError(
                    f"\t{fc_name} is an unidentified {featType}"
                    " featureclass with no MUSYM or FEATSYM field (GetFCName)"
                )
                return ssurgoType, fileName

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return "", ""
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return "", ""
        

## =============================================================================
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

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

## =============================================================================
def CheckAttributes(fc_path, ssurgoType):

    # check to make sure the primary attribute fields are populated
    # with data and no NULL records exist.
    # Return False if fc contains empty records, True otherwise.

    try:
        # Set target fieldname and data type (normally text or string)

        # _a, _c, _d shapefile
        if(ssurgoType in 
           ("Map unit polygons","Map unit points","Map unit lines")):
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
                arcpy.AddError(
                    f"\tMissing {len(values)} {fldName} value(s) in "
                    f"{os.path.basename(fc_path)} layer:"
                )

                for value in values:
                    arcpy.AddError("\t\tObjectID: {0}".format(value))

                return False

            else:
                return True

        # fc has no records
        else:
            return True

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


## =============================================================================
def SetOutputCoordinateSystem(fc_path):
    # This function will compare the geographic coord sys of the inLayer to
    # the spatial reference 4326 (GCS_WGS_1984).  If they are different then
    # an ESRI datum transformation method will be applied based on the 
    # geographic
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
            arcpy.AddMessage("\nNo datum transformation required")
            #tm = ""

        else:
            arcpy.AddMessage(
                "\tUsing datum transformation method "
                "'WGS_1984_(ITRF00)_To_NAD_1983' \n "
            )

        """ TRANSFORMATION use ITRF00 """

        # Set the output coordinate system environment
        arcpy.env.outputCoordinateSystem = outputSR    # GCS_WGS_1984
        # Transformation Method
        arcpy.env.geographicTransformations =  "WGS_1984_(ITRF00)_To_NAD_1983"       
        
        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

## =============================================================================
def GetFieldInfo(fc_path, ssurgoType, oldFields):

    # Create and return FieldMapping object containing valid SSURGO fields. 
    # Fields that are not part of SSURGO will not be included.

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

            # Field object containing the properties for the field (aliasName)
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

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        fms = arcpy.FieldMappings()
        return fms
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        fms = arcpy.FieldMappings()
        return fms


        

## =============================================================================
def CheckFieldInfo(outFC, ssurgoSchema):
    # Compare the new output shapefile table design with the SSURGO standard as
    # defined in the 'SSURGOFieldInfo' function

    try:
        fields = arcpy.da.Describe(outFC)['fields']
        inSchema = []

        for fld in fields:
            inSchema.append(
                (fld.baseName, fld.length, fld.precision, fld.scale, fld.type)
            )

        if inSchema == ssurgoSchema:
            return True

        else:
            arcpy.AddError(
                "Schema mismatch problem with " + outFC + " attribute table")
            arcpy.AddError("--------------------------------------------------")
            arcpy.AddError("\tOutput ShapeFile: " + str(inSchema))
            arcpy.AddError("\n\tSSURGO Standard: " + str(ssurgoSchema))
            return False

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


## =============================================================================
def CreateSSA(fc_out,loc,AS):

    # Create Survey Area Boundary by dissolving Mapunit Polygon layer.
    # Returns False if no features were generated after the dissolve or if
    # _b layer already exists, otherwise return True.

    try:

        # path to the Soil Survey Area boundary shapefile export
        SSApath = os.path.join(loc, AS.lower() + "_b.shp")

        # return false if shapefile already exists
        if env.overwriteOutput == False and arcpy.Exists(SSApath):
            arcpy.AddError(
                f"Output shapefile ({os.path.basename(SSApath)}) already exists"
            )
            return False

        arcpy.Dissolve_management(
            fc_out, SSApath, "AREASYMBOL", "", "SINGLE_PART"
        )

        # Notify user of the amount of SSA features exported
        ssaCnt = int(arcpy.GetCount_management(SSApath).getOutput(0))

        if ssaCnt < 1:
            arcpy.AddError(
                "\n\t" + os.path.basename(SSApath) + " has no features")
            return False

        else:
            arcpy.AddMessage(
                f"\tSurvey area polygons: {ssaCnt:.0f} features exported")

        del SSApath
        del ssaCnt

        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False


## =============================================================================
def GetLayerExtent(layer):

    try:

        desc = arcpy.Describe(layer)

        layerExtent = []

        layerExtent.append(desc.extent.XMin)
        layerExtent.append(desc.extent.XMax)
        layerExtent.append(desc.extent.YMax)
        layerExtent.append(desc.extent.YMin)

        if len(layerExtent) == 4:
            arcpy.AddMessage("\tSurvey Bounding Coordinates: ")
            arcpy.AddMessage(f"\t\tWest_Bounding_Coordinate: {layerExtent[0]}")
            arcpy.AddMessage(f"\t\tEast_Bounding_Coordinate: {layerExtent[1]}")
            arcpy.AddMessage(f"\t\tNorth_Bounding_Coordinate: {layerExtent[2]}")
            arcpy.AddMessage(
                f"\t\tSouth_Bounding_Coordinate: {layerExtent[3]}\n"
            )

        else:
            return False
           
        del layerExtent
        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

## =============================================================================
def GetFolderSize(start_path):

    try:

        total_size = 0

        for dirpath, dirnames, filenames in os.walk(start_path):

            for f in filenames:

                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        return f"{float(total_size) / 1048576:.1f}"

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return 0
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return 0

## =============================================================================
def ProcessSurveyArea(inLoc, exportList, outLoc, theAS, ssurgoFields, msg):
    # Check each layer in the workspace. If it's a valid SSURGO layer, export it
    # to a WGS 1984 shapefile.
    # Skips any featureclass whose name begins with 'QA_'

    try:

        # Create final output folder for the output shapefiles, 
        # if it doesn't exist
        if not arcpy.Exists(os.path.join(outLoc, theAS.lower())):
            arcpy.CreateFolder_management(outLoc, theAS.lower())

        else:
            arcpy.AddWarning(
                f"\t{theAS.lower()} Folder Exists; "
                "Contents will be overwritten\n"
            )

        # directory path to the export folder
        surveyLoc = os.path.join(outLoc, theAS.lower())
        sQuery = '"AREASYMBOL" = ' + "'" + theAS + "'"

        # How many unique point and linear features exist
        uniqueSpecFeatureCount = 0
        uniquefeatList = list()

        # for each valid SSURGO layer in workspace export the 
        # Areasymbol as a shapefile
        layerCount = 0

        # Establish progressor object which allows progress info 
        # to be passed to dialog box.
        arcpy.SetProgressor("step", " ", 0, len(exportList), 1)

        for fc in exportList:

            arcpy.SetProgressorLabel(
                "\nExporting Soil Survey: " + theAS + " " + str(msg)
            )

            layerCount += 1
            fc_path = f"{inLoc}/{fc}"
            # Get SSURGO data type ('Mapunit Polygon') 
            # and fileName ('wi025_a.shp)
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
                    arcpy.AddError(
                        "Output shapefile (" + outFC + ") already exists"
                    )
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
                    arcpy.AddError(
                        f"Failed to create output shapefile ({outFC})"
                    )
                    return False

                # if there are features in layer check the schema 
                # and attribute field
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
                    if(ssurgoType == "Feature points" 
                       or ssurgoType == "Feature lines"):

                        fields = ["FEATSYM"]

                        with arcpy.da.SearchCursor(outFC,fields) as cursor:

                            for row in cursor:
                                if not row[0] in uniquefeatList:
                                    uniquefeatList.append(row[0])
                                    uniqueSpecFeatureCount += 1

                        del fields

                    arcpy.AddMessage(f"\t{ssurgoType} exported: {iCnt:.0f}")

                else:
                    arcpy.AddMessage(f"\t{ssurgoType} exported: {iCnt:.0f}")

                # Create survey boundary if _a layer by dissolving it
                if(ssurgoType == "Map unit polygons" 
                   and not CreateSSA(outFC,surveyLoc,theAS)):
                    # arcpy.Delete_management(surveyLoc)
                    return False

                # strictly formatting
                if layerCount == 6:
                    arcpy.AddMessage("\n")

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
            arcpy.AddMessage(
                f"\tUnique Special Feature Count: {uniqueSpecFeatureCount:.0f}"
            )

            for feat in uniquefeatList:
                arcpy.AddMessage("\t" + feat)

        # Report out extent of SAPOLYGON layer
        layer = os.path.join(surveyLoc, theAS.lower() + "_b.shp")
        if not GetLayerExtent(layer):
            arcpy.AddError(
                f"\n\tCould not determine Spatial Domain of {theAS}\n"
            )

        folderSize = GetFolderSize(surveyLoc)
        arcpy.AddMessage("\t" + "Directory Size: " + str(folderSize) + " MB")

        # remove all .xml files
        for file in os.listdir(surveyLoc):
            if file.endswith('.xml'):
                os.remove(os.path.join(surveyLoc, file))

        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
        return False
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))
        return False

# ========================================= Main Body ==========================
import os
import sys
import traceback

import arcpy
from arcpy import env

if __name__ == '__main__':
    try:
        arcpy.AddMessage(f"version: {v}")
        # 4 Script arguments...
        # input workspace or featuredataset
        inLoc = arcpy.GetParameterAsText(0) 
        # output folder where shapefiles will be placed        
        outLoc = arcpy.GetParameterAsText(1) 
        # List of Areasymbol values to beexported from the geodatabase       
        asList = arcpy.GetParameter(2)              

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

        # Make sure each valid SSURGO fc has AREASYMBOL fully populated; 
        # MUSYM/FEATSYM is checked after
        # the data has been exported.  If nulls occur there, 
        # the entire survey is deleted.
        for fc_name in exportList:
            fc_path = f"{inLoc}/{fc_name}"
            if not CheckAttributes(fc_path,"Survey area polygons"):
                arcpy.AddError("Halting export process")
                exit()

        # should have exactly 6 feature classes found
        if len(exportList) == 0:
            arcpy.AddError(
                "\tFound no required SSURGO featureclasses........"
                "Halting export process"
            )

        elif len(exportList) < 6:
            arcpy.AddError(
                "\tFailed to find all 6 required "
                "input SSURGO featureclass types"
            )
            exit()

        elif len(exportList) > 6:
            arcpy.AddError(
                "\tFound more than the 6 required "
                "input SSURGO featureclass types"
            )
            exit()

        arcpy.AddMessage(
            f"\nExporting SSURGO shapefiles for {len(asList):.0f} "
            f"survey area(s) to folder '{outLoc}"
        )

        # if featuredataset is enforced then we can set the env.coord 
        # system using any fc from within the export list
        # and not have to check transformation everytime we export 
        # an individual SSA .shp.
        # set output coordinate system env variable to (4326 - WGS84)

        bSR = False
        for fc_name in exportList:
            fc_path = f"{inLoc}/{fc_name}"
            ssurgoType, fileName = GetFCType(fc_path, "")
            if ssurgoType == "Map unit polygons":

                bSR = SetOutputCoordinateSystem(fc_path)
                break

        # Either Mapunit Polygon was not found or not able 
        # to set spatial reference
        if not bSR:
            arcpy.AddError(
                "Failed to set output spatial reference!"
                "....Halting export process"
            )
            exit()

        # Establish progressor object which allows progress info to be 
        # passed to dialog box.
        arcpy.SetProgressor(
            "step", 
            f"Exporting SSURGO shapefiles for {len(asList):.0f} "
            "soil surveys...",  
            0, 
            len(asList)
        )

        # Process each soil survey, one at a time.  If a problem occurs,
        # it will be reported but nothing will be deleted

        iCnt = 1
        for theAS in asList:

            arcpy.SetProgressorLabel(
                f"Exporting Soil Survey: {theAS} ({iCnt} of {len(asList)})"
            )
            msgString = " (" + str(iCnt) + " of " + str(len(asList)) + ")"

            arcpy.AddMessage("\nExporting Soil Survey: " + theAS)
            arcpy.AddMessage("------------------------------------------------")

            bProcessed = ProcessSurveyArea(
                inLoc, exportList, outLoc, theAS, ssurgoFields, msgString
            )
            del msgString

            if bProcessed == False:
                arcpy.AddError(
                    "\n\tSoil Survey Area " + theAS + "  will not be exported"
                )
                problemSurveys.append(theAS)

            iCnt += 1

            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()
        del iCnt

        arcpy.AddMessage("\n==================================================")

        # Report problem surveys
        if len(problemSurveys) > 0:
            arcpy.AddError(
                "The following survey(s) failed to export: "
                f'{", ".join(problemSurveys)}'
            )
            arcpy.AddError(
                f"\n{len(asList) - len(problemSurveys)} of "
                f"{len(asList)} surveys were exported to the '{outLoc}' folder"
            )

        else:
            if len(asList) > 2:
                arcpy.AddMessage(
                    f"\nAll {len(asList)} surveys successfully exported to "
                    f"the '{outLoc}' folder"
                )

            elif len(asList) == 1:
                arcpy.AddMessage(
                    f"\nSelected survey ({asList[0]}) successfully exported "
                    f"to the '{outLoc}' folder"
                )

            elif len(asList) == 2:
                arcpy.AddMessage(
                    "\nBoth selected surveys successfully exported to the '" 
                    f"{outLoc}' folder"
                )

            elif len(asList) == 0:
                arcpy.AddError("\nNo surveys were exported")

    except arcpy.ExecuteError:
        func = 'main'
        arcpy.AddError(arcpyErr(func))
 
    except:
        func = 'main'
        arcpy.AddError(pyErr(func))

