#-------------------------------------------------------------------------------
# Name:     Create SSA Master Tables
# Purpose:
#
# Author:      Adolfo.Diaz
#
# Created:     28/10/2021
# Copyright:   (c) Adolfo.Diaz 2021
#
# This script is used to recreate the SSURGO_Soil_Survey_Area FGDB tables
# that dictate how many SSAs will be downloaded by region and which SSAs correspond
# with the buffered MLRA FGDB.
#
# It requires the path to the SSURGO_Soil_Survey_Area.gdb and the official
# soil survey area shapefile from web soil survey.  This layer should be checked
# annually to account for new SSAs or depracated SSAs.
#
# The mlra office layer is also required.  If offices change regional overshight
# then the changes need to be reflected in this layer.
#-------------------------------------------------------------------------------

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

## ================================================================================================================
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

import arcpy, os

if __name__ == '__main__':

    # Parameter #1 - SSURGO Soil Survey Area FGDB (SSURGO QA Tools)
    ssurgoQAgdb = r'E:\python_scripts\GitHub\SSURGO-QA-ArcGIS-Pro\SSURGO_Soil_Survey_Area.gdb'

    # Parameter #2 - SSA NRCS Layer - Download this from WSS and make sure it is projected the same as the MLRA offices.
    ssaLayer = r'E:\python_scripts\GitHub\SSURGO-QA-ArcGIS-Pro\SSURGO_Soil_Survey_Area.gdb\soilsa_a_nrcs'

    # Parameter #3-  MLRA Office Layer
    mlraOffices = f"{ssurgoQAgdb}\MLRA_Soil_Survey_Areas_May2020"
    mlraOfficesFld = "NEW_SSAID"
    regionOwnershipFld = "Region_Ownership"

    # Create 2 tables with fields
    arcpy.env.workspace = ssurgoQAgdb

    mlraBufferTable = f"{ssurgoQAgdb}\SSA_by_MLRA_buffer_UPDATE"
    regionBufferTable = f"{ssurgoQAgdb}\SSA_by_Region_buffer_UPDATE"

    if arcpy.Exists(mlraBufferTable):
        arcpy.Delete_management(mlraBufferTable)
        AddMsgAndPrint(f"Deleting {mlraBufferTable}")

    if arcpy.Exists(regionBufferTable):
        arcpy.Delete_management(regionBufferTable)
        AddMsgAndPrint(f"Deleting {regionBufferTable}")

    arcpy.CreateTable_management(ssurgoQAgdb,"SSA_by_MLRA_buffer_UPDATE")
    arcpy.CreateTable_management(ssurgoQAgdb,"SSA_by_Region_buffer_UPDATE")

    arcpy.AddField_management(mlraBufferTable,"AREASYMBOL","TEXT",field_length=20)
    arcpy.AddField_management(mlraBufferTable,"Region_Ownership","SHORT")  #-------------Do we need this field?
    arcpy.AddField_management(mlraBufferTable,"MLRA_CODE","TEXT",field_length=10)
    #arcpy.AddField_management(mlraBufferTable,"Region_Download","TEXT",field_length=20)
    mlraBufferFlds = ["AREASYMBOL","Region_Ownership","MLRA_CODE"]

    arcpy.AddField_management(regionBufferTable,"AREASYMBOL","TEXT",field_length=20)
    arcpy.AddField_management(regionBufferTable,"Region_Ownership","SHORT")                # Region that owns the SSA
    arcpy.AddField_management(regionBufferTable,"Region_Download","TEXT",field_length=10)  # Region that requires SSA for MLRA FGDB
    regionBufferTblFlds = [f.name for f in arcpy.ListFields(regionBufferTable,'*')][1:]

    # Make a layer out of the SSA and mlra to be able to select by location
    AddMsgAndPrint(f"Creating a layer from {os.path.basename(ssaLayer)}")
    ssaLyr = arcpy.MakeFeatureLayer_management(ssaLayer,"ssaLyr")

    AddMsgAndPrint(f"Creating a layer from {os.path.basename(mlraOffices)}")
    mlraLyr = arcpy.MakeFeatureLayer_management(mlraOffices,"mlraLyr")

    # ['2-ELK', '2-MIN', '13-FAI', '13-HOM']
    listOfOffices = [row[0] for row in arcpy.da.SearchCursor(mlraOffices,'NEW_SSAID')]

    for office in listOfOffices:

        AddMsgAndPrint(f"\nProcessing {office} office")

        # Select SSAs that intersect MLRA Office
        mlraPolygon = arcpy.SelectLayerByAttribute_management(mlraLyr,"NEW_SELECTION",f"{mlraOfficesFld} = '{office}'")
        ssaPolygons = arcpy.SelectLayerByLocation_management(ssaLyr, 'INTERSECT', mlraPolygon, selection_type='NEW_SELECTION')
        AddMsgAndPrint(f"    Total # of SSAs in {office}: {int(arcpy.GetCount_management(ssaPolygons)[0])}")

        # Increase SSA by 1 on the perimeter
        ssaPolygons_buffer = arcpy.SelectLayerByLocation_management(ssaPolygons, 'INTERSECT', ssaPolygons, selection_type='ADD_TO_SELECTION')

        # Populate SSA_by_MLRA_buffer table with the SSAs that belong to this MLRA
        cursor = arcpy.da.InsertCursor(mlraBufferTable,mlraBufferFlds)

        # Attributes from ssaLayer for the intersected MLRA SSAs
        # (OK013,6)
        mlraAttributes = [(row[0],row[1]) for row in arcpy.da.SearchCursor(ssaPolygons_buffer,["areasymbol","Region_Ownership"])]

        for attributes in mlraAttributes:
            cursor.insertRow((attributes[0],attributes[1],office))

        arcpy.SelectLayerByAttribute_management(mlraLyr,"CLEAR_SELECTION")
        arcpy.SelectLayerByAttribute_management(ssaLyr, "CLEAR_SELECTION")

        del cursor,mlraPolygon,ssaPolygons,ssaPolygons_buffer,mlraAttributes

    arcpy.Delete_management(ssaLyr)
    arcpy.Delete_management(mlraLyr)

    # List of areasymbols and their corresponding administrative region.
    areasymbolOwnershipDict = dict()
    with arcpy.da.SearchCursor(ssaLayer,['areasymbol','Region_Ownership']) as cursor:
        for row in cursor:
            areasymbolOwnershipDict[row[0]] = row[1]

    # {2, 3, 4, 5, 6, 7, 9, 10, 12, 13}
    listOfRegions = set([row[0] for row in arcpy.da.SearchCursor(mlraOffices,regionOwnershipFld)])

    # Create cursor to populate the "SSA_by_Region_buffer_UPDATE" table with the SSAs that belong to this MLRA
    cursor = arcpy.da.InsertCursor(regionBufferTable,regionBufferTblFlds)
    AddMsgAndPrint(f"\nUpdating the {os.path.basename(regionBufferTable)} table")

    # Iterate through each region and obtain a list of MLRA offices administered by that regional office
    # and then obtain a list of areasymbols associated with that MLRA office
    for region in listOfRegions:

        AddMsgAndPrint(f"    Processing Region {region}")
        totalSSAsInRegion = 0

        # '"Region_Ownership" = 6'
        expression = f"{arcpy.AddFieldDelimiters(mlraOffices, regionOwnershipFld)} = {region}"

        # Get a list of MLRA offices that are owned by the region using the mlraOffices layer
        # {'6-NOR', '6-MOR', '6-OWN', '6-MAT', '6-MIL', '6-SPR', '6-COO', '6-LON', '6-WAY', '6-CLI'}
        regionalMLRAOffices = set([row[0] for row in arcpy.da.SearchCursor(mlraOffices,mlraOfficesFld,where_clause=expression)])

        # Get a list of areasymbols from the mlraBufferTable that pertain to each office and append them to a list
        areasymRegionalList = set()

        for office in regionalMLRAOffices:

            #'"MLRA_CODE" = 6-NOR'
            officeExpression = f"{arcpy.AddFieldDelimiters(mlraBufferTable, 'MLRA_CODE')} = '{office}'"

            areasymOfficeList = set([row[0] for row in arcpy.da.SearchCursor(mlraBufferTable,'AREASYMBOL',where_clause=officeExpression)])
            areasymRegionalList.update(areasymOfficeList)

            totalSSAsInRegion += len(areasymRegionalList)
            AddMsgAndPrint(f"        MLRA Office {office}: {len(areasymOfficeList)} SSAs")

        for areasym in sorted(areasymRegionalList):
            if areasym in areasymbolOwnershipDict:
                cursor.insertRow((areasym,areasymbolOwnershipDict[areasym],f"Region {region}"))
            else:
                cursor.insertRow((areasym,"XXXXX",f"Region {region}"))
                AddMsgAndPrint(f"            MLRA Office {office}: {areasym} does not exist in ssaLayer",2)

        AddMsgAndPrint(f"    Total SSAs for Region {region}: {totalSSAsInRegion}")

    del cursor








