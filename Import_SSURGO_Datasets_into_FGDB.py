# Import_SSURGO_Datasets_into_FGDB_ArcGIS10
#
# Created 4/27/2012
#
# Adolfo Diaz, Region 10 GIS Specialist
# USDA - Natural Resources Conservation Service
# Madison, WI 53719
# adolfo.diaz@wi.usda.gov
# 608.662.4422 ext. 216
#
# Some subfunctions were modified from Steve Peaslee's "Setup_UpdateSurvey_Dev.py."
# Thanks to Steve for doing the leg work on some of these subfunctions.
#
# This script was tested using ArcGIS 10 SP4. No known issues were encountered.
#
# Purpose: Import multiple existing SSURGO datasets, spatial and tabular data, into one File Geodatabase.
#
# The "Import SSURGO Datasets into FGDB ArcGIS10" tool will import SSURGO spatial and tabular data into a File Geodatabase
# and establish the necessary relationships between tables and feature classes in order to query component and horizon
# data and spatially view the distribution of that data at the mapunit level.  The output is a File Geodatabase
# that contains a feature dataset with 6 feature classes: MUPOLYGON, MUPOINT, MULINE, SAPOLYGON, FEATLINE
# and FEATPOINT.  Acres will be calculated if the input Spatial Reference is projected and the linear units
# are feet or meters.
#
# Usage: +++++++++++++++++++++++++++++++++++++++++++++++++++++++
# 1) Name of New File Geodatabase:
#        Name of the new File Geodatabase to create. This FGDB will contain the SSURGO spatial and tabular data.
#
#        Any alphanumeric string may be entered as long as the first character is ALPHA. Special characters
#        are not allowed in the name. Blank spaces will be converted to underscores.
#
#        It is recommended that you use an intuitive name that will describe the extent of your output.
#            ex) If your FGDB will contain every SSURGO dataset in Wisconsin than a logical name would be "WI_SSURGO".
#
#        Today's date will be appended to the name of the FGDB in the form of YYYYMMDD.
#            ex) "WI_SSURGO_20120301"
#
#        If a FGDB of the same name, incuding the date, exists, then the tool will attempt to delete it.
#        If deleting fails then the tool will exit.
# 2) Ouput Location:
#        Location where the output File Geodatabase will be created. User may type in a full path in this
#        field or browse to and select a folder.
#
#        The tool will exit if the path is invalid.
# 3) Location where SSURGO datasets_reside:
#        Browse to and select the parent directory that contains the SSURGO datasets you want imported
#        into the output FGDB.
#
#        SSURGO datasets must be structured the same as when they were received from the Soil Data Mart.
#        SSURGO dataset folders that are altered will simply be skipped.
#
#        If the Import Tabular Data option is checked, the tabular folder within the SSURGO dataset folder must
#        be present. If the tabular folder is absent then ONLY the spatial data will be imported for that
#        particular dataset.
# 4) Import Tabular Data (optional)
#        When this option is selected, empty SSURGO attribute tables will be created in the output FGDB.
#        The SSURGO text files will then be directly imported into their designated FGDB table. Text files do NOT
#        need to be imported into a SSURGO Access template since the tool does not utilize a SSURGO dataset's template.
#
#        The national 2002 SSURGO MS Access template database (Template DB version 34) will be used as to provide
#        the necessary table and field parameters when creating the empty tables.
#
#        Due to necessary reformatting of some text files, read AND write permissions are necessary in the SSURGO
#        dataset parent directory.
#
#        This option will also create relationships between tables and featureclasses and will store them in the
#        output geodatabase. These can be used by ArcMap and other ArcGIS applications to query component and horizon
#        information.
#
#        Each relationship class name is prefixed by an "x" so that the listing in ArcCatalog will display tables and
#        featureclasses on top and relationship classes last.
# 5) Output Coordinate System:
#        Output Coordinate System that will define the feature dataset and, subsequently, the feature classes.
#        Currently the tool only handles the following coordinate systems:
#            NAD83 - UTM Zone
#            NAD83 - State Plane (Meters or Feet)
#            NAD83 - Geographic Coordinate System (GRS 1980.prj)
#            NAD83 - USA Contiguous Albers Equal Area Conic USGS
#        The tool does not support datum transformations. If a specific SSURGO dataset's datum differs from
#        the input coordinate system than that SSURGO dataset will simply be skipped.
# 6) Clip Boundary (optional)
#        Optional Polygon layer that will be used to clip the featureclasses in the output FGDB.
#
#        The SAPOLYGON (Survey Area Polygon) feature class will not be clipped.
#
#        The tool first determines if there is overlap between the SSURGO Soil Survey Area layer (soilsa_a_*)
#        and the clip boundary. If overlap exists then the SSURGO dataset will be clipped, if necessary, before
#        importing into the FGDB. If no overlap exists then the SSURGO dataset is simply skipped.
#
#        If a SSURGO dataset is imported into the output FGDB and the Import Tabular Data option is checked,
#        then the entire tabular data is imported, not just for the mapunits that were imported.
#
#        If the clip boundary's coordinate system is different from the output coordinate system then the clip
#        boundary will be projected. If the clip boundary contains multiple features then it will be dissolved
#        into as a single part feature. The newly projected layer and the dissolve layer will be deleted once the
#        tool has executed correctly.
#
#        Depending on the size of your Soil Data Mart Library, you may want to isolate the SSURGO datasets of interest
#        since the tool will inevitably determine if overlap exists between the clip boundary and every SSURGO dataset.
#
# UPDATED: 3/14/2012
#   * removed much of the original code to import tabular data.  Per Steve Peaslee's suggestion, I incorporate CSVreader
#     module to open and read the SSURGO Text files.
#   * Make better use of tuples and dictionaries by creating them early on and passing them thoughout the code rather
#     create them every time I loope through a table.
#
# UPDATED: 4/27/2012
#   * Add functionality to calculate acres
#   * Add better error handling.
#   * Had to remove "print" function from this script otherwise it would fail from toolbox.
#
# Updated 7/27/2012
#   * BUG was found in the importTabular function that wouldn't properly clear rows.
#     As a result, NULL values were being populated with the last value that wasn't NULL.
#     deleting row cursor was added in line 1226 to assure a new line was started and not remain in memory

# UPDATED: 8/3/2012
#    * BUG: Realized that if the extent boundary was a feature class within a feature dataset, the newly projected layer
#      could not be written to the same feature dataset b/c its projection was not the same anymore.  Modified the
#      projectLayer to reproject dependent feature classess to the same geodatbase as a single feature class.
#
# UPDATED: 11/20/2012
#       Eric Wolfbrandt was having inconsistent issues with the script.  Sometimes it would execute correctly
#       and other times it would fail.  Steve Peaslee modified some of the code within the importTabular function
#       to remove continue statements from within if statements.  So many versions were created in an effort to
#       troubleshoot this problem that I decided to print the version of the script in the log file.
#

# ==========================================================================================
# Updated  3/18/2021 - Adolfo Diaz
#
# - Rewrote the Create Table Relationships function
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
#
# Beginning of Functions

# ==========================================================================================
# Updated  10/13/2021 - Adolfo Diaz
#
# - Added csv.field_size_limit(min(sys.maxsize, 2147483646)) to the importTabularData function

## ================================================================================================================
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
    # Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line

    #print(msg)

    try:

        f = open(textFilePath,'a+')
        f.write(msg + "\n")
        f.close

        # Add a geoprocessing message (in case this is run as a tool)
        if severity == 0:
            arcpy.AddMessage(msg)

        elif severity == 1:
            arcpy.AddWarning(msg)

        elif severity == 2:
            arcpy.AddMessage("    ")
            arcpy.AddError(msg)

    except:
        pass

## ================================================================================================================
def splitThousands(someNumber):
    """ will determine where to put the thousand seperator if one is needed.
        Input is an integer.  Integer with or without thousands seperator is returned."""

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber

## ================================================================================================================
def compareDatum(fc):
    """ Return True if fc datum is either WGS84 or NAD83"""

    try:
        # Create Spatial Reference of the input fc. It must first be converted in to string in ArcGIS10
        # otherwise .find will not work.
        fcSpatialRef = str(arcpy.CreateSpatialReference_management("#",fc,"#","#","#","#"))
        FCdatum_start = fcSpatialRef.find("DATUM") + 7
        FCdatum_stop = fcSpatialRef.find(",", FCdatum_start) - 1
        fc_datum = fcSpatialRef[FCdatum_start:FCdatum_stop]

        # Create the GCS WGS84 spatial reference and datum name using the factory code
        WGS84_sr = arcpy.SpatialReference(4326)
        WGS84_datum = WGS84_sr.datumName

        NAD83_datum = "D_North_American_1983"

        # Input datum is either WGS84 or NAD83; return true
        if fc_datum == WGS84_datum or fc_datum == NAD83_datum:

            del fcSpatialRef,FCdatum_start,FCdatum_stop,fc_datum,WGS84_sr,WGS84_datum,NAD83_datum
            return True

        # Input Datum is some other Datum; return false
        else:
            del fcSpatialRef,FCdatum_start,FCdatum_stop,fc_datum,WGS84_sr,WGS84_datum,NAD83_datum
            return False

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        return False

    except:
        errorMsg()
        return False

## ================================================================================================================
def createFGDB(GDBname,outputFolder,spatialRef):
    """ This function will Create a File Geodatabase.  A Feature Dataset will be created if b_FD = True.
        6 feature classes will be created using the SSURGO schema.
        Return False if error occurs, True otherwise. """

    try:
        newFGDBpath = os.path.join(outputFolder,GDBname + ".gdb")

        if arcpy.Exists(newFGDBpath):
            arcpy.Delete_management(newFGDBpath)

        arcpy.CreateFileGDB_management(outputFolder,GDBname)

        AddMsgAndPrint("\nCreated File Geodatabase: " + newFGDBpath, 0)

        if not createFeatureClasses(newFGDBpath,spatialRef):
            return False

        return True

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        return False

    except:
        AddMsgAndPrint("Unhandled exception (createFGDB)", 2)
        errorMsg()
        return False

## ================================================================================================================
def createFeatureClasses(newFGDBpath,spatialRef):

    try:

        #------------------------------------------------- Create a blank feature class to append soils into
        arcpy.CreateFeatureclass_management(newFGDBpath,soilFC,"polygon","","DISABLED","DISABLED",spatialRef)

        arcpy.AddField_management(newFGDBpath + os.sep + soilFC,"AREASYMBOL","TEXT","#","#","20")
        arcpy.AddField_management(newFGDBpath + os.sep + soilFC,"SPATIALVER","DOUBLE","10","0")
        arcpy.AddField_management(newFGDBpath + os.sep + soilFC,"MUSYM","TEXT","#","#","6")
        arcpy.AddField_management(newFGDBpath + os.sep + soilFC,"MUKEY","TEXT","#","#","30")

        AddMsgAndPrint("\tCreated Feature Class: " + soilFC + " -----> Mapunit Polygon Layer" ,0)

        if not bSTATSGO:

            #------------------------------------------------- Create a blank feature class to append SSA boundary to
            arcpy.CreateFeatureclass_management(newFGDBpath,soilSaFC,"polygon","","DISABLED","DISABLED",spatialRef)

            arcpy.AddField_management(newFGDBpath + os.sep + soilSaFC,"AREASYMBOL","TEXT","#","#","20")
            arcpy.AddField_management(newFGDBpath + os.sep + soilSaFC,"SPATIALVER","DOUBLE","10","0")
            arcpy.AddField_management(newFGDBpath + os.sep + soilSaFC,"LKEY","TEXT","#","#","30")

            AddMsgAndPrint("\tCreated Feature Class: " + soilSaFC + " -----> Survey Boundary Layer",0)

            #------------------------------------------------- Create a blank feature class to append SSURGO point features to
            arcpy.CreateFeatureclass_management(newFGDBpath,featPointFC,"point","","DISABLED","DISABLED",spatialRef)

            arcpy.AddField_management(newFGDBpath + os.sep + featPointFC,"AREASYMBOL","TEXT","#","#","20")
            arcpy.AddField_management(newFGDBpath + os.sep + featPointFC,"SPATIALVER","DOUBLE","10","0")
            arcpy.AddField_management(newFGDBpath + os.sep + featPointFC,"FEATSYM","TEXT","#","#","3")
            arcpy.AddField_management(newFGDBpath + os.sep + featPointFC,"FEATKEY","TEXT","#","#","30")

            AddMsgAndPrint("\tCreated Feature Class: " + featPointFC + " -----> Special Feature Point Layer",0)

            #------------------------------------------------- Create a blank feature class to append SSURGO line features to
            arcpy.CreateFeatureclass_management(newFGDBpath,featLineFC,"polyline","","DISABLED","DISABLED",spatialRef)

            arcpy.AddField_management(newFGDBpath + os.sep + featLineFC,"AREASYMBOL","TEXT","#","#","20")
            arcpy.AddField_management(newFGDBpath + os.sep + featLineFC,"SPATIALVER","DOUBLE","10","0")
            arcpy.AddField_management(newFGDBpath + os.sep + featLineFC,"FEATSYM","TEXT","#","#","3")
            arcpy.AddField_management(newFGDBpath + os.sep + featLineFC,"FEATKEY","TEXT","#","#","30")

            AddMsgAndPrint("\tCreated Feature Class: " + featLineFC + "  -----> Special Feature Line Layer",0)

            #------------------------------------------------- Create a blank feature class to append SSURGO Mapunit line features to
            arcpy.CreateFeatureclass_management(newFGDBpath,muLineFC,"polyline","","DISABLED","DISABLED",spatialRef)

            arcpy.AddField_management(newFGDBpath + os.sep + muLineFC,"AREASYMBOL","TEXT","#","#","20")
            arcpy.AddField_management(newFGDBpath + os.sep + muLineFC,"SPATIALVER","DOUBLE","10","0")
            arcpy.AddField_management(newFGDBpath + os.sep + muLineFC,"MUSYM","TEXT","#","#","6")
            arcpy.AddField_management(newFGDBpath + os.sep + muLineFC,"MUKEY","TEXT","#","#","30")

            AddMsgAndPrint("\tCreated Feature Class: " + muLineFC + "    -----> Mapunit Line Layer",0)

            #------------------------------------------------- Create a blank feature class to append SSURGO Mapunit point features to
            arcpy.CreateFeatureclass_management(newFGDBpath,muPointFC,"point","","DISABLED","DISABLED",spatialRef)

            arcpy.AddField_management(newFGDBpath + os.sep + muPointFC,"AREASYMBOL","TEXT","#","#","20")
            arcpy.AddField_management(newFGDBpath + os.sep + muPointFC,"SPATIALVER","DOUBLE","10","0")
            arcpy.AddField_management(newFGDBpath + os.sep + muPointFC,"MUSYM","TEXT","#","#","6")
            arcpy.AddField_management(newFGDBpath + os.sep + muPointFC,"MUKEY","TEXT","#","#","30")

            AddMsgAndPrint("\tCreated Feature Class: " + muPointFC + "   -----> Mapunit Point Layer",0)

        return True

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        return False

    except:
        AddMsgAndPrint("Unhandled exception (createFeatureClasses)", 2)
        errorMsg()
        return False
## ===============================================================================================================
def GetTableAliases(ssurgoTemplateLoc, tblAliases):
    """ Retrieve physical and alias names from MDSTATTABS table and assigns them to a blank dictionary.
        Stores physical names (key) and aliases (value) in a Python dictionary i.e. {chasshto:'Horizon AASHTO,chaashto'}
        Fieldnames are Physical Name = AliasName,IEfilename"""

    try:

        # Open mdstattabs table containing information for other SSURGO tables
        theMDTable = "mdstattabs"
        env.workspace = ssurgoTemplateLoc

        # Establishes a cursor for searching through field rows. A search cursor can be used to retrieve rows.
        # This method will return an enumeration object that will, in turn, hand out row objects
        if arcpy.Exists(ssurgoTemplateLoc + os.sep + theMDTable):

            nameOfFields = ["tabphyname","tablabel","iefilename"]
            rows = arcpy.da.SearchCursor(ssurgoTemplateLoc + os.sep + theMDTable,nameOfFields)

            for row in rows:
                # read each table record and assign 'tabphyname' and 'tablabel' to 2 variables
                physicalName = row[0]
                aliasName = row[1]
                importFileName = row[2]

                # i.e. {chaashto:'Horizon AASHTO',chaashto}; will create a one-to-many dictionary
                # As long as the physical name doesn't exist in dict() add physical name
                # as Key and alias as Value.
                if not physicalName in tblAliases:
                    tblAliases[physicalName] = (aliasName,importFileName)

                del physicalName
                del aliasName
                del importFileName

            del theMDTable
            del nameOfFields
            del rows
            del row

            return tblAliases

        else:
            # The mdstattabs table was not found
            AddMsgAndPrint("\nMissing \"mdstattabs\" table", 2)
            return tblAliases

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        return tblAliases

    except:
        AddMsgAndPrint("Unhandled exception (GetTableAliases)", 2)
        errorMsg()
        return tblAliases

## ===============================================================================================================
def importTabularData(tabularFolder, tblAliases, queue):
    """ This function will import the SSURGO .txt files from the tabular folder.
        tabularFolder is the absolute path to the tabular folder.
        tblAliases is a list of the physical name of the .txt file along with the Alias name.
        Return False if error occurs, true otherwise.  there is a list of files that will not be
        imported under "doNotImport".  If the tabular folder is empty or there are no text files
        the survey will be skipped."""

    try:
        env.workspace = FGDBpath

        # Loops through the keys in the tblAliases dict() and puts the 2nd value
        # (iefilename) and key (tabphyname) in a list.  The list is then sorted
        # so that SSURGO text files can be imported in alphabetical sequence.
        GDBTables = tblAliases.keys()
        #GDBTables.sort()

        # Do not import the following SSURGO text files.  Most are metadata text files that are
        # used within the access template and/or SDV.  No need to import them into GDB.
##        doNotImport = ["msdomdet","msdommas","msidxdet","msidxmas","msrsdet",
##                       "msrsmas","mstab","mstabcol","version"]
        doNotImport = ["month"]

        # if the tabular directory is empty return False
        if len(os.listdir(tabularFolder)) < 1:
            AddMsgAndPrint("\t\tTabular Folder is Empty!",1)
            return False

        # Static Metadata Table that records the metadata for all columns of all tables
        # that make up the tabular data set.
        mdstattabsTable = env.workspace + os.sep + "mdstattabs"

        AddMsgAndPrint("\n\tImporting Tabular Data for: " + SSA,0)

        # set progressor object which allows progress information to be passed for every merge complete
        arcpy.SetProgressor("step", "Importing Tabular Data for " + SSA + ": " + str(queue) + ' of ' + str(total), 0, len(GDBTables), 1)

        # For each item in sorted keys
        for GDBtable in GDBTables:

            # Metadata tables only have to be imported once b/c they are national tables.
            if GDBtable.find('mds') > -1 or GDBtable.find('distinterpmd') > -1:
                if int(arcpy.GetCount_management(os.path.join(FGDBpath,GDBtable)).getOutput(0)) > 0:
                    continue

            # physicalName (tablabel,iefilename)
            # i.e. {chaashto:'Horizon AASHTO',chaashto}
            x = tblAliases[GDBtable]

            # Alias Name: tablabel field (Table Label field)
            # x[0] = Horizon AASHTO
            aliasName = x[0]

            # Import Export File Name: iefilename
            # x[1] = chaashto
            iefileName = x[1]

            if not iefileName in doNotImport:

                # Absolute Path to SSURGO text file
                txtPath = tabularFolder + os.sep + iefileName + ".txt"

                # continue if SSURGO text file exists.
                if os.path.exists(txtPath):

                    # Next 4 lines are strictly for printing formatting to figure out the spacing between.
                    # the short and full name.  8 is the max num of chars from the txt tables + 2 = 10
                    # Played around with numbers until I liked the formatting.
                    theTabLength = 20 - len(iefileName)
                    theTab = " " * theTabLength
                    theAlias = theTab + "(" + aliasName + ")"
                    theRecLength = " " * (48 - len(aliasName))

                    del theTabLength, theTab

                    # Continue if the text file contains values. Not Empty file
                    if os.path.getsize(txtPath) > 0:

                        # Put all the field names in a list; used to initiate insertCursor object
                        fieldList = arcpy.Describe(GDBtable).fields
                        nameOfFields = []
                        fldLengths = list()

                        for field in fieldList:

                            if field.type != "OID":
                                nameOfFields.append(field.name)
                                if field.type.lower() == "string":
                                    fldLengths.append(field.length)
                                else:
                                    fldLengths.append(0)

                        del fieldList, field

                        # The csv file might contain very huge fields, therefore increase the field_size_limit:
                        # Exception thrown with IL177 in legend.txt.  Not sure why, only 1 record was present
                        #csv.field_size_limit(sys.maxsize)
                        csv.field_size_limit(min(sys.maxsize, 2147483646))

                        # Number of records in the SSURGO text file
                        textFileRecords = sum(1 for row in csv.reader(open(txtPath, 'r'), delimiter='|', quotechar='"'))

                        # Initiate Cursor to add rows
                        cursor = arcpy.da.InsertCursor(GDBtable,nameOfFields)

                        # counter for number of records successfully added; used for reporting
                        numOfRowsAdded = 0
                        reader = csv.reader(open(txtPath, 'r'), delimiter='|', quotechar='"')

                        try:
                            # Return a reader object which will iterate over lines in txtPath
                            for rowInFile in reader:

                                """ Cannot use this snippet of code b/c some values have exceeded their field lengths; need to truncate"""
                                # replace all blank values with 'None' so that the values are properly inserted
                                # into integer values otherwise insertRow fails
                                # newRow = [None if value =='' else value for value in rowInFile]

                                newRow = list()  # list containing the values that make up a specific row
                                fldNo = 0        # list position to reference the field lengths in order to compare

                                for value in rowInFile:
                                    fldLen = fldLengths[fldNo]

                                    if value == '':
                                        value = None

                                    elif fldLen > 0:
                                        value = value[0:fldLen]

                                    newRow.append(value)
                                    fldNo += 1

                                cursor.insertRow(newRow)
                                numOfRowsAdded += 1

                                del newRow

                        except:
                            AddMsgAndPrint("\n\t\tError inserting record in table: " + GDBtable,2)
                            AddMsgAndPrint("\t\t\tRecord # " + str(numOfRowsAdded + 1),2)
                            AddMsgAndPrint("\t\t\tValue: " + str(newRow),2)
                            errorMsg()

                        AddMsgAndPrint("\t\t--> " + iefileName + theAlias + theRecLength + " Records Added: " + str(splitThousands(numOfRowsAdded)),0)

                        # compare the # of rows inserted with the number of valid rows in the text file.
                        if numOfRowsAdded != textFileRecords:
                            AddMsgAndPrint("\t\t\t Incorrect # of records inserted into: " + GDBtable, 2 )
                            AddMsgAndPrint("\t\t\t\t TextFile records: " + str(textFileRecords),2)
                            AddMsgAndPrint("\t\t\t\t Records Inserted: " + str(numOfRowsAdded),2)

                        del GDBtable, x, aliasName, iefileName, txtPath, theAlias, theRecLength, nameOfFields, textFileRecords, rowInFile, numOfRowsAdded, cursor, reader

                    else:
                        AddMsgAndPrint("\t\t--> " + iefileName + theAlias + theRecLength + " Records Added: 0",0)

                else:
                    AddMsgAndPrint("\t\t--> " + iefileName + " does NOT exist in tabular folder.....SKIPPING ",2)

            arcpy.SetProgressorPosition()

        # Resets the progressor back to is initial state
        arcpy.ResetProgressor()
        arcpy.SetProgressorLabel(" ")

        del GDBTables, doNotImport, mdstattabsTable

        return True

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        AddMsgAndPrint("\tImporting Tabular Data Failed for: " + SSA,2)
        return False

    except csv.Error as e:
        AddMsgAndPrint('\nfile %s, line %d: %s' % (txtPath, reader.line_num, e))
        AddMsgAndPrint("\tImporting Tabular Data Failed for: " + SSA,2)
        errorMsg()
        return False

    except IOError as e:
        errno, strerror = e.args
        AddMsgAndPrint("\nI/O error({0}): {1}".format(errno, strerror) + " File: " + txtPath + "\n",2)
        AddMsgAndPrint("\tImporting Tabular Data Failed for: " + SSA,2)
        errorMsg()
        return False

    except:
        AddMsgAndPrint("\nUnhandled exception (importTabularData) \n", 2)
        AddMsgAndPrint("\tImporting Tabular Data Failed for: " + SSA,2)
        errorMsg()
        return False

## ===============================================================================================================
def CreateTableRelationships(tblAliases):
    """ Create relationship classes between standalone attribute tables.
        Relate parameters are pulled from the mdstatrhipdet and mdstatrshipmas tables,
        thus it is required that the tables must have been copied from the template database.

        Test option of getting aliases from original template database vs. output database
        set workspace to original template database
        env.workspace = InputDB
        or
        set workspace to output database.....This script uses output database as workspace
        WAIT, take that back.  Using the GDB as a workspace creates locks.  Specifically, the
        MakeQueryTable tool creates .rd and .sr locks that are only deleted if Arc is restarted.
        Currently use the ssurgoTemplate to create a query table so that it doesn't lock the .GDB
        Subfunction is written by Steve Peaslee and modified by Adolfo Diaz. """
    #
    #Modified From Steve Peaslee's Setup_UpdateSurvey
    env.workspace = ssurgoTemplate

    AddMsgAndPrint("\n------------------------------------------------------------------------------------------------------- ")
    AddMsgAndPrint("Verifying relationships:\n")

    # set progressor object which allows progress information to be passed for every relationship complete

    if arcpy.Exists(ssurgoTemplate + os.sep + "mdstatrshipdet") and arcpy.Exists(ssurgoTemplate + os.sep + "mdstatrshipmas"):
        try:
        # Create new Table View to contain results of join between relationship metadata tables

            fld1 = "mdstatrshipmas.ltabphyname"
            fld2 = "mdstatrshipdet.ltabphyname"
            fld3 = "mdstatrshipmas.rtabphyname"
            fld4 = "mdstatrshipdet.rtabphyname"
            fld5 = "mdstatrshipmas.relationshipname"
            fld6 = "mdstatrshipdet.relationshipname"

            # GDB format
            SQLtxt = "" + fld1 + " = " + fld2 + " AND " + fld3 + " = " + fld4 + " AND " + fld5 + " = " + fld6 + ""

            # ssurgoTemplate Format (.mdb)
            #SQLtxt = "[" + fld1 + "] = [" + fld2 + "] AND [" + fld3 + "] = [" + fld4 + "] AND [" + fld5 + "] = [" + fld6 + "]"

            # Create in-memory table view to supply parameters for each relationshipclasses (using SSURGO 2.0 mdstatrshipdet and mdstatrshipmas tables)
            inputTables = [ssurgoTemplate + os.sep + "mdstatrshipdet", ssurgoTemplate + os.sep + "mdstatrshipmas"]
            queryTableName = "RelshpInfo"

            # Use this one for env.workspace = FGDBpath: includes objectID but I don't think it is needed
            #fieldsList = "mdstatrshipdet.OBJECTID OBJECTID;mdstatrshipdet.ltabphyname LTABPHYNAME;mdstatrshipdet.rtabphyname RTABPHYNAME;mdstatrshipdet.relationshipname RELATIONSHIPNAME;mdstatrshipdet.ltabcolphyname LTABCOLPHYNAME;mdstatrshipdet.rtabcolphyname RTABCOLPHYNAME;mdstatrshipmas.cardinality CARDINALITY"
            #fieldsList = "mdstatrshipdet.ltabphyname LTABPHYNAME;mdstatrshipdet.ltabcolphyname LTABCOLPHYNAME;mdstatrshipdet.rtabphyname RTABPHYNAME;mdstatrshipdet.rtabcolphyname RTABCOLPHYNAME;mdstatrshipdet.relationshipname RELATIONSHIPNAME;mdstatrshipmas.cardinality CARDINALITY"
            fieldsList = [["mdstatrshipdet.ltabphyname", 'LTABPHYNAME'],
                          ["mdstatrshipdet.ltabcolphyname", 'LTABCOLPHYNAME'],
                          ["mdstatrshipdet.rtabphyname", 'RTABPHYNAME'],
                          ["mdstatrshipdet.rtabcolphyname", 'RTABCOLPHYNAME'],
                          ["mdstatrshipdet.relationshipname", 'RELATIONSHIPNAME'],
                          ["mdstatrshipmas.cardinality", 'CARDINALITY']]

            arcpy.MakeQueryTable_management(inputTables, queryTableName, "NO_KEY_FIELD", "", fieldsList, SQLtxt)

            if not arcpy.Exists(queryTableName):
                AddMsgAndPrint("\nFailed to create metadata table required for creation of relationshipclasses",2)
                return False

            # Fields in RelshpInfo table view
            # OBJECTID, LTABPHYNAME, RTABPHYNAME, RELATIONSHIPNAME, LTABCOLPHYNAME, RTABCOLPHYNAME, CARDINALITY
            # Open table view and step through each record to retrieve relationshipclass parameters

            arcpy.SetProgressor("step", "Verifying Tabular Relationships", 0, int(arcpy.GetCount_management(ssurgoTemplate + os.sep + "mdstatrshipdet").getOutput(0)), 1)
            arcpy.SetProgressorLabel("Verifying Tabular Relationships")

            recNum = 0
            env.workspace = FGDBpath

            #['mdstatrshipdet_ltabphyname', 'mdstatrshipdet_ltabcolphyname', 'mdstatrshipdet_rtabphyname', 'mdstatrshipdet_rtabcolphyname', 'mdstatrshipdet_relationshipname', 'mdstatrshipmas_cardinality']
            queryTableFlds = [f.name for f in arcpy.ListFields(queryTableName)]
            #queryTableFlds.remove('OBJECTID')

            with arcpy.da.SearchCursor(queryTableName, queryTableFlds) as cursor:
                for row in cursor:

                    # Get relationshipclass parameters from current table row
                    # Syntax for CreateRelationshipClass_management (origin_table, destination_table,
                    # out_relationship_class, relationship_type, forward_label, backward_label,
                    # message_direction, cardinality, attributed, origin_primary_key,
                    # origin_foreign_key, destination_primary_key, destination_foreign_key)
                    #
                    #AddMsgAndPrint("Reading record " + str(recNum), 1)
                    originTable = row[0]
                    destinationTable = row[2]

                    originTablePath = FGDBpath + os.sep + originTable
                    destinationTablePath = FGDBpath + os.sep + destinationTable

                    # Use table aliases for relationship labels
                    relName = "x" + originTable.capitalize() + "_" + destinationTable.capitalize()

                    originPKey = row[1]
                    originFKey = row[3]

                    # create Forward Label i.e. "> Horizon AASHTO Table"
                    if destinationTable in tblAliases:
                        fwdLabel = "> " + tblAliases.get(destinationTable)[0] + " Table"
                    else:
                        fwdLabel = destinationTable + " Table"
                        AddMsgAndPrint("Missing key: " + destinationTable, 2)

                    # create Backward Label i.e. "< Horizon Table"
                    if originTable in tblAliases:
                        backLabel = "<  " + tblAliases.get(originTable)[0] + " Table"

                    else:
                        backLabel = "<  " + originTable + " Table"
                        AddMsgAndPrint("Missing key: " + originTable, 2)

                    theCardinality = row[5].upper().replace(" ", "_")

                    # Check if origin and destination tables exist
                    if arcpy.Exists(originTablePath) and arcpy.Exists(destinationTablePath):

                        # The following 6 lines are for formatting only
                        formatTab1 = 15 - len(originTable)
                        formatTabLength1 = " " * formatTab1 + "--> "

                        formatTab2 = 19 - len(destinationTable)
                        formatTabLength2 = " " * formatTab2 + "--> "

                        formatTab3 = 12 - len(str(theCardinality))
                        formatTabLength3 = " " * formatTab3 + "--> "

                        # relationship already exists; print out the relationship name
                        if arcpy.Exists(relName):
                            AddMsgAndPrint("\t" + originTable +  formatTabLength1 + destinationTable + formatTabLength2 + theCardinality + formatTabLength3 + relName, 0)

                        # relationship does not exist; create it and print out
                        else:
                            arcpy.CreateRelationshipClass_management(originTablePath, destinationTablePath, relName, "SIMPLE", fwdLabel, backLabel, "NONE", theCardinality, "NONE", originPKey, originFKey, "","")
                            AddMsgAndPrint("\t" + originTable +  formatTabLength1 + destinationTable + formatTabLength2 + theCardinality + formatTabLength3 + relName, 0)

                        # delete formatting variables
                        del formatTab1, formatTabLength1, formatTab2, formatTabLength2, formatTab3, formatTabLength3
                    else:
                        AddMsgAndPrint("        <-- " + relName + ": Missing input tables (" + originTable + " or " + destinationTable + ")", 0)

                    del originTable, destinationTable, originTablePath, destinationTablePath, relName, originPKey, originFKey, fwdLabel, backLabel, theCardinality

                    recNum = recNum + 1
                    arcpy.SetProgressorPosition() # Update the progressor position

            arcpy.ResetProgressor()  # Resets the progressor back to is initial state
            arcpy.SetProgressorLabel(" ")

            #del fld2, fld1, fld3, fld4, fld5, fld6, SQLtxt, inputTables, fieldsList, queryTableName, recNum

            # Establish Relationship between tables and Spatial layers
            # The following lines are for formatting only
            formatTab1 = 15 - len(soilFC)
            formatTabLength1 = " " * formatTab1 + "--> "

            AddMsgAndPrint("\nCreating Relationships between spatial feature classes and tables:")

            # Relationship between MUPOLYGON --> Mapunit Table
            if not arcpy.Exists("xSpatial_MUPOLYGON_Mapunit"):
                arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + soilFC, FGDBpath + os.sep + "mapunit", FGDBpath + os.sep + "xSpatial_MUPOLYGON_Mapunit", "SIMPLE", "> Mapunit Table", "< MUPOLYGON_Spatial", "NONE","ONE_TO_ONE", "NONE","MUKEY","mukey", "","")
            AddMsgAndPrint("\t" + soilFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Mapunit", 0)

            # Relationship between MUPOLYGON --> Mapunit Aggregate Table
            if not arcpy.Exists("xSpatial_MUPOLYGON_Muaggatt"):
                arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + soilFC, FGDBpath + os.sep + "muaggatt", FGDBpath + os.sep + "xSpatial_MUPOLYGON_Muaggatt", "SIMPLE", "> Mapunit Aggregate Table", "< MUPOLYGON_Spatial", "NONE","ONE_TO_ONE", "NONE","MUKEY","mukey", "","")
            AddMsgAndPrint("\t" + soilFC + formatTabLength1 + "muaggatt" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Muaggatt", 0)

            if not bSTATSGO:
    			# Relationship between SAPOLYGON --> Legend Table
                if not arcpy.Exists("xSpatial_SAPOLYGON_Legend"):
                    arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + soilSaFC, FGDBpath + os.sep + "legend", FGDBpath + os.sep + "xSpatial_SAPOLYGON_Legend", "SIMPLE", "> Legend Table", "< SAPOLYGON_Spatial", "NONE","ONE_TO_ONE", "NONE","LKEY","lkey", "","")
                AddMsgAndPrint("\t" + soilSaFC + formatTabLength1 + "legend" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SAPOLYGON_Legend", 0)

    			# Relationship between MULINE --> Mapunit Table
                if not arcpy.Exists("xSpatial_MULINE_Mapunit"):
                    arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + muLineFC, FGDBpath + os.sep + "mapunit", FGDBpath + os.sep + "xSpatial_MULINE_Mapunit", "SIMPLE", "> Mapunit Table", "< MULINE_Spatial", "NONE","ONE_TO_ONE", "NONE","MUKEY","mukey", "","")
                AddMsgAndPrint("\t" + muLineFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MULINE_Mapunit", 0)

    			# Relationship between MUPOINT --> Mapunit Table
                if not arcpy.Exists("xSpatial_MUPOINT_Mapunit"):
                    arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + muPointFC, FGDBpath + os.sep + "mapunit", FGDBpath + os.sep + "xSpatial_MUPOINT_Mapunit", "SIMPLE", "> Mapunit Table", "< MUPOINT_Spatial", "NONE","ONE_TO_ONE", "NONE","MUKEY","mukey", "","")
                AddMsgAndPrint("\t" + muPointFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOINT_Mapunit", 0)

    			# Relationship between FEATLINE --> Featdesc Table
                if not arcpy.Exists("xSpatial_FEATLINE_Featdesc"):
                    arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + featLineFC, FGDBpath + os.sep + "featdesc", FGDBpath + os.sep + "xSpatial_FEATLINE_Featdesc", "SIMPLE", "> Featdesc Table", "< FEATLINE_Spatial", "NONE","ONE_TO_ONE", "NONE","FEATKEY","featkey", "","")
                AddMsgAndPrint("\t" + featLineFC + formatTabLength1 + "featdesc" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_FEATLINE_Featdesc", 0)

    			# Relationship between FEATPOINT --> Featdesc Table
                if not arcpy.Exists("xSpatial_FEATPOINT_Featdesc"):
                    arcpy.CreateRelationshipClass_management(FGDBpath + os.sep + featPointFC, FGDBpath + os.sep + "featdesc", FGDBpath + os.sep + "xSpatial_FEATPOINT_Featdesc", "SIMPLE", "> Featdesc Table", "< FEATPOINT_Spatial", "NONE","ONE_TO_ONE", "NONE","FEATKEY","featkey", "","")
                AddMsgAndPrint("\t" + featPointFC + formatTabLength1 + "featdesc" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_FEATPOINT_Featdesc", 0)

            del formatTab1, formatTabLength1

            AddMsgAndPrint("\nSuccessfully Created Table Relationships", 0)
            return True

        except arcpy.ExecuteError:
            AddMsgAndPrint(arcpy.GetMessages(2),2)
            return False

        except:
            errorMsg()
            return False

    else:
        AddMsgAndPrint("\tMissing at least one of the relationship metadata tables", 2)
        return False

## ===============================================================================================================
def updateAliasNames(fgdbPath, GDBname):
    """ Update the alias name of every feature class in the RTSD including the project record.
        i.e. alias name for MUPOLYGON = Region 10 - Mapunit Polygon """

    try:

        aliasUpdate = 0

        if GDBname.rfind("_") > 0:
            aliasName = GDBname[:GDBname.rfind("_")].replace("_"," ")
        else:
            aliasName = "SSURGO"

        if arcpy.Exists(os.path.join(fgdbPath,'FEATLINE')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'FEATLINE'), aliasName + " - Special Feature Lines")  #FEATLINE
            aliasUpdate += 1

        if arcpy.Exists(os.path.join(fgdbPath,'FEATPOINT')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'FEATPOINT'), aliasName + " - Special Feature Points")  #FEATPOINT
            aliasUpdate += 1

        if arcpy.Exists(os.path.join(fgdbPath,'MUPOLYGON')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'MUPOLYGON'), aliasName + " - Mapunit Polygon")  #MUPOLYGON
            aliasUpdate += 1

        if arcpy.Exists(os.path.join(fgdbPath,'SAPOLYGON')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'SAPOLYGON'), aliasName + " - Survey Area Polygon")  #SAPOLYGON
            aliasUpdate += 1

        if arcpy.Exists(os.path.join(fgdbPath,'MULINE')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'MULINE'), aliasName + " - Mapunit Line")  #MULINE
            aliasUpdate += 1

        if arcpy.Exists(os.path.join(fgdbPath,'MUPOINT')):
            arcpy.AlterAliasName(os.path.join(fgdbPath,'MUPOINT'), aliasName + " - Mapunit Point")  #MUPOINT
            aliasUpdate += 1

        if aliasUpdate == 6:
            return True
        else:
            return False

    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)
        return False

    except:
        errorMsg()
        return False

## ===============================================================================================================
def addAttributeIndex(table,fieldList,verbose=True):
    """ Attribute indexes can speed up attribute queries on feature classes and tables.
        This function adds an attribute index(es) for the fields passed to the table that
        is passed in. This function takes in 2 parameters:
           1) Table - full path to an existing table or feature class
           2) List of fields that exist in table
        This function will make sure an existing index is not associated with that field.
        Does not return anything."""

    try:
        # Make sure table exists. - Just in case
        if not arcpy.Exists(table):
            AddMsgAndPrint("\nAttribute index cannot be created for: " + os.path.basename(table) + " TABLE DOES NOT EXIST",2)
            return False

        else:
            if verbose:
                AddMsgAndPrint("\n\tAdding Attribute Indexes to Table: " + os.path.basename(table))
                numOfFields = len(fieldList)
                arcpy.SetProgressor("step", "Adding Attribute Indexes to Table: " + os.path.basename(table), 0, numOfFields, 1)

        # iterate through every field
        for fieldToIndex in fieldList:

            if verbose:
                arcpy.SetProgressorLabel("Adding Attribute Indexes to Table: " + os.path.basename(table) + " - Field: " + fieldToIndex)

            # Make sure field exists in table - Just in case
            if not len(arcpy.ListFields(table,"*" + fieldToIndex))>0:
                if verbose:
                    AddMsgAndPrint("\t\tAttribute index cannot be created for: " + fieldToIndex + ". FIELD DOES NOT EXIST",2)
                    arcpy.SetProgressorPosition()
                    continue

            # list of indexes (attribute and spatial) within the table that are
            # associated with the field or a field that has the field name in it.
            # Important to inspect all associated fields b/c they could be using
            # a differently named index
            existingIndexes = arcpy.ListIndexes(table,"*" + fieldToIndex)
            bFieldIndexExists = False

            # check existing indexes to see if fieldToIndex is already associated
            # with an index
            if len(existingIndexes) > 0:

                # iterate through the existing indexes looking for a field match
                for index in existingIndexes:
                    associatedFlds = index.fields

                    # iterate through the fields associated with existing index.
                    # Should only be 1 field since multiple fields are not allowed
                    # in a single FGDB.
                    for fld in associatedFlds:

                        # Field is already part of an existing index - Notify User
                        if fld.name == fieldToIndex:
                            if verbose:
                                AddMsgAndPrint("\t\tAttribute Index for " + fieldToIndex + " field already exists",1)
                                arcpy.SetProgressorPosition()
                                bFieldIndexExists = True

                    # Field is already part of an existing index - Proceed to next field
                    if bFieldIndexExists:
                        break

            # Attribute field index does not exist.  Add one.
            if not bFieldIndexExists:
                newIndex = "IDX_" + fieldToIndex

                # UNIQUE setting is not used in FGDBs - comment out
                arcpy.AddIndex_management(table,fieldToIndex,newIndex,"#","ASCENDING")

                if verbose:
                    AddMsgAndPrint("\t\tSuccessfully added attribute index for " + fieldToIndex)
                    arcpy.SetProgressorPosition()

    except:
        errorMsg()
        return False

## ================================================================ Main Body ===========================================================
# Import modules
import arcpy, sys, string, os, time, datetime, re, csv, traceback, shutil
from arcpy import env

if __name__ == '__main__':

    arcpy.env.parallelProcessingFactor = "100%"
    arcpy.env.overwriteOutput = True

    """ -------------------------------------------------------------------------------------------------------------------Input Arguments"""
    # Parameter # 1: (Required) Name of new file geodatabase to create
    #GDBname = "Test"
    GDBname = arcpy.GetParameterAsText(0)

    # Parameter # 2: (Required) Input Directory where the new FGDB will be created.
    #outputFolder = r'K:\SSURGO_FY16\WSS\test'
    outputFolder = arcpy.GetParameterAsText(1)

    # Parameter # 3: (Required) Input Directory where the original SDM spatial and tabular data exist.
    #sdmLibrary = r'G:\2014_SSURGO_Region10'
    sdmLibrary = arcpy.GetParameterAsText(2)

    # Parameter # 4: list of SSA datasets to be proccessed
    #surveyList = ['soils_ia001','soils_ia005']
    surveyList = arcpy.GetParameter(3)

    # Parameter # 5: (Required) Import SSURGO tabular data into FGDB (boolean)
    #               True = Both Spatial and Tabular data will be imported to FGDB
    #               False = Only Spatial Data will be imported to FGDB
    #b_importTabularData = True
    b_importTabularData = arcpy.GetParameter(4)

    # Parameter # 6: (Optional) Input Spatial Reference. Only Spatial References with WGS84 or NAD83 Datums are allowed.
    #spatialRef = r'C:\Users\adolfo.diaz\AppData\Roaming\ESRI\Desktop10.1\ArcMap\Coordinate Systems\USA_Contiguous_Albers_Equal_Area_Conic_USGS_version.prj'
    spatialRef = arcpy.GetParameterAsText(5)

    # Parameter # 7 - Boolean indicating that STATSGO data will be appended
    bSTATSGO = arcpy.GetParameter(6)
    #bSTATSGO = True

    # SSURGO FGDB template that contains empty SSURGO Tables and relationships
    # and will be copied over to the output location
    ssurgoTemplate = os.path.dirname(sys.argv[0]) + os.sep + "SSURGO_Table_Template.gdb"

    if b_importTabularData and not os.path.exists(ssurgoTemplate):
        AddMsgAndPrint("\n SSURGO_Table_Template.gdb does not exist in " + os.path.dirname(sys.argv[0]),2)
        exit()

    from datetime import datetime
    startTime = datetime.now()
    env.overwriteOutput = True

    # --------------------------------------------------------------------------------------Set Booleans
    # Set boolean for the presence of an extent boundary; True if present, False if absent
    # Set boolean for Import Tabular Option; True to Import, False to ignore importing.

    # The entire Main code in a try statement....Let the fun begin!
    try:
        import datetime

        textFilePath = outputFolder + os.sep + GDBname + "_" + str(datetime.date.today()).replace("-","") + "_Log.txt"

        # process each selected soil survey
        AddMsgAndPrint("\nValidating " + str(len(surveyList)) + " selected surveys...", 0)

        """ ---------------------------------------------------------------------------------------------------------- Create necessary File Geodatabase"""
        # Create new File Geodatabase, Feature Dataset and Feature Classes.

        # SSURGO layer Name
        soilFC = "MUPOLYGON"
        muLineFC = "MULINE"
        muPointFC = "MUPOINT"
        soilSaFC = "SAPOLYGON"
        featPointFC = "FEATPOINT"
        featLineFC = "FEATLINE"

        FGDBpath = os.path.join(outputFolder,GDBname + ".gdb")

        # Importing tabular data was selected; Copy SSURGO Table FGDB template to output folder. Create Feature Classes
        if b_importTabularData:

            if arcpy.Exists(FGDBpath):
                arcpy.Delete_management(FGDBpath)

            arcpy.Copy_management(ssurgoTemplate,FGDBpath)
            AddMsgAndPrint("\nCreated File Geodatabase: " + FGDBpath,0)

            if not createFeatureClasses(FGDBpath,spatialRef):
                AddMsgAndPrint("\nFailed to Initiate File Geodatabase. Exiting!",2)
                exit()

            tblAliases = dict()
            tblAliases = GetTableAliases(ssurgoTemplate, tblAliases)
            #AddMsgAndPrint(str(tblAliases),1)

        # import Tabular was not selected; Create Empty FileGDB and create feature classes
        else:
            if not createFGDB(GDBname,outputFolder,spatialRef):
                AddMsgAndPrint("\nFailed to Initiate File Geodatabase. Exiting!",2)
                exit()

            if not createFeatureClasses(FGDBpath,spatialRef):
                AddMsgAndPrint("\nFailed to Initiate File Geodatabase. Exiting!",2)
                exit()

        # Set environment variables to ITRF0 if going between WGS84 and NAD1983
        env.workspace = FGDBpath
        env.outputCoordinateSystem = spatialRef

        # Parse Datum from user spatial reference; can only get datum from a GCS not a projected one
        userDatum_Start = spatialRef.find("DATUM") + 7
        userDatum_Stop = spatialRef.find(",", userDatum_Start) - 1
        userDatum = spatialRef[userDatum_Start:userDatum_Stop]

        sr = arcpy.Describe(soilFC).spatialReference

        AddMsgAndPrint("\n\tOutput Coordinate System: " + sr.name,0)
        AddMsgAndPrint("\tOutput Datum: " + userDatum,0)

        if userDatum == "D_North_American_1983":
            AddMsgAndPrint("\tGeographic Transformation: WGS_1984_(ITRF00)_To_NAD_1983",0 )
            env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"  # WKID 108190
        elif userDatum == "D_WGS_1984":
            AddMsgAndPrint("\tCoordinate System: GCS_WGS_1984",0 )
            #env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"  # WKID 108190
        else:
            AddMsgAndPrint("\nCannot handle user Datum: " + str(userDatum) + " Exiting",2)
            exit()

        """ ----------------------------------------------------------------------------------------------------------------------------- Setup the Merging Process"""

        # Dictionary containing approx center of SSA (key) and the SSURGO layer path (value)
        soilShpDict = dict() # {-4002.988250799742: 'K:\\FY2014_SSURGO_R10_download\\soils_wi063\\spatial\\soilmu_a_wi063.shp'}
        muLineShpDict = dict()
        muPointShpDict = dict()
        soilSaShpDict = dict()
        featPointShpDict = dict()
        featLineShpDict = dict()

        # lists containing SSURGO layer paths sorted according to the survey center key
        # This list will be passed over to the Merge command
        soilShpList = list() #['G:\\2014_SSURGO_Region10\\soils_ia005\\spatial\\soilmu_a_ia005.shp']
        muLineShpList = list()
        muPointShpList = list()
        soilSaShpList = list()
        featPointShpList = list()
        featLineShpList = list()

        # list containing the (Xcenter * Ycenter) for every SSURGO soil layer
        extentList = list()

        # set progressor object which allows progress information to be passed for every merge complete
        arcpy.SetProgressor("step", "Validating Each Survey", 0, len(surveyList), 1)

        for subFolder in surveyList:

            # folder is STATSGO 'wss_gmsoil_IA_[2006-07-06]'
            if subFolder.find("wss_gsmsoil_") > -1:
                SSA = subFolder[12:14].lower()

            # folder is named in WSS 3.0 format i.e. 'wss_SSA_WI063_soildb_WI_2003_[2012-06-27]'
            elif subFolder.find("SSA_") > -1:
                SSA = subFolder[subFolder.find("SSA_") + 4:subFolder.find("soildb")-1].lower()

            # folder is named according to traditional SDM format i.e. 'soil_wa001'
            elif subFolder.find("soil_") > -1:
                SSA = subFolder[-5:].lower()

            # folder is name in plural format instead of singular.  Accident!!!
            elif subFolder.find("soils_") > -1:
                SSA = subFolder[-5:].lower()

	       # folder is named with just FIPS i.e. WI001
            elif len(subFolder) == 5:

                for i in range(len(subFolder)):
                    asc = ord(subFolder[i])

        		    # First and second char must be uppercase Alpha
                    if i < 2:
                        if not asc > 64 or not asc < 91:
                            continue

                    # Last 3 characters must be Numeric
                    elif i < 4:
                        if not asc > 47 or not asc < 58:
                          continue

                    # Last character to assess.  Add to list if it is numeric
                    else:
                        if asc > 47 and asc < 58:
                            SSA = subFolder
                        else:
                            continue

            else:
                AddMsgAndPrint("\n"+ subFolder + " is not a valid SSURGO folder.....IGNORING",1)
                continue

            arcpy.SetProgressorLabel("Validating " + SSA)

            # Paths to individual SSURGO layers
            if bSTATSGO:
                soilShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "gsmsoilmu_a_" + SSA + ".shp")
                soilSaShpPath = soilShpPath
            else:
                soilShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilmu_a_" + SSA + ".shp")
                soilSaShpPath = soilShpPath

            if not bSTATSGO:
                muLineShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilmu_l_" + SSA + ".shp")
                muPointShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilmu_p_" + SSA + ".shp")
                soilSaShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilsa_a_" + SSA + ".shp")
                featPointShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilsf_p_" + SSA + ".shp")
                featLineShpPath = os.path.join( os.path.join(sdmLibrary, os.path.join(subFolder, "spatial")), "soilsf_l_" + SSA + ".shp")

            if arcpy.Exists(soilShpPath):

                # compare datum and make sure no Datum Transformation is needed
                if compareDatum(soilSaShpPath):

                    # Calculate the approximate center of a given survey
                    desc = arcpy.Describe(soilShpPath)
                    shpExtent = desc.extent
                    XCntr = (shpExtent.XMin + shpExtent.XMax) / 2.0
                    YCntr = (shpExtent.YMin + shpExtent.YMax) / 2.0
                    surveyCenter = XCntr * YCntr

                    # Assign {-4002.988250799742: 'K:\\FY2014_SSURGO_R10_download\\soils_wi063\\spatial\\soilmu_a_wi063.shp'}
                    soilShpDict[surveyCenter] = soilShpPath

                    # statsgo does not have any of these extra features
                    if not bSTATSGO:
                        muLineShpDict[surveyCenter] = muLineShpPath
                        muPointShpDict[surveyCenter] = muPointShpPath
                        soilSaShpDict[surveyCenter] = soilSaShpPath
                        featPointShpDict[surveyCenter] = featPointShpPath
                        featLineShpDict[surveyCenter] = featLineShpPath

                    extentList.append(surveyCenter)

                    del desc, shpExtent, XCntr, YCntr, surveyCenter

                else:
                    # Doesn't properly break out of this! FIX THIS Add boolean if importing shapefile worked.
                    AddMsgAndPrint("Different Datums between: " + os.path.basename(soilShpPath) + " and User-defined Datum....SKIPPING SSURGO Dataset",2)
                    continue

            else:
                AddMsgAndPrint("\nMissing soil polygon shapefile: soilmu_a_" + SSA + ".shp",2)
                continue

            try:
                del soilShpPath, muLineShpPath, muPointShpPath, soilSaShpPath, featPointShpPath, featLineShpPath
            except:
                pass

            arcpy.SetProgressorPosition()

        """ ----------------------------------------------------------------------------------------------------------------------------- Begin the Merging Process"""
        # Sort shapefiles by extent so that the drawing order is continous
        extentList.sort()

        # There should be at least 1 survey to merge into the MUPOLYGON
        if len(soilShpDict) > 0:

            # Add SSURGO paths to their designated lists according to the survey's center so that they draw continously
            # If the layer has features then add it to the merge list otherwise skip it.  This was added b/c it turns
            # out that empty mapunit point .shp are in line geometry and not point geometry
            for surveyCenter in extentList:

                soilShpList.append(soilShpDict[surveyCenter])

                if not bSTATSGO:
                    soilSaShpList.append(soilSaShpDict[surveyCenter])

                    if int(arcpy.GetCount_management(muLineShpDict[surveyCenter]).getOutput(0)) > 0:
                        muLineShpList.append(muLineShpDict[surveyCenter])

                    if int(arcpy.GetCount_management(muPointShpDict[surveyCenter]).getOutput(0)) > 0:
                        muPointShpList.append(muPointShpDict[surveyCenter])

                    if int(arcpy.GetCount_management(featPointShpDict[surveyCenter]).getOutput(0)) > 0:
                        featPointShpList.append(featPointShpDict[surveyCenter])

                    if int(arcpy.GetCount_management(featLineShpDict[surveyCenter]).getOutput(0)) > 0:
                        featLineShpList.append(featLineShpDict[surveyCenter])

        # No surveys to merge
        else:
            if arcpy.Exists(FGDBpath):
                arcpy.Delete_management(FGDBpath)

            AddMsgAndPrint("\n\n No Soil Surveys found to merge.....Exiting!",2)
            exit()

        # set progressor object which allows progress information to be passed for every merge complete
        if bSTATSGO:
            arcpy.SetProgressor("step", "Beginning the merge process...", 0, 1, 1)
        else:
            arcpy.SetProgressor("step", "Beginning the merge process...", 0, 6, 1)

        # ---------------------------------------------------------------------------------------------------- Merge Soil Mapunit Polygons
        AddMsgAndPrint("\nMerging SSURGO Spatial Datasets:")

        arcpy.SetProgressorLabel("Merging " + str(len(soilShpList)) + " SSURGO Soil Mapunit Polygon Layers")

        soilFCpath = os.path.join(FGDBpath, soilFC)
        arcpy.Merge_management(soilShpList, soilFCpath)
        AddMsgAndPrint("\tSuccessfully merged SSURGO Soil Mapunit Polygons",0)

        if not addAttributeIndex(soilFCpath,["AREASYMBOL","MUSYM"],False): pass

        arcpy.SetProgressorPosition()

        # --------------------------------------------------------------------------------------------------- Merge Soil Mapunit Lines
        if not bSTATSGO:
            if len(muLineShpList) > 0:

                arcpy.SetProgressorLabel("Merging " + str(len(muLineShpList)) + " SSURGO Soil Mapunit Line Layers")

                muLineFCpath = os.path.join(FGDBpath, muLineFC)
                arcpy.Merge_management(muLineShpList,muLineFCpath)
                #arcpy.Append_management(muLineShpList, os.path.join(FGDBpath, muLineFC), "NO_TEST")

                AddMsgAndPrint("\tSuccessfully merged SSURGO Soil Mapunit Lines",0)

                if not addAttributeIndex(muLineFCpath,["AREASYMBOL","MUSYM"],False): pass

            else:
                AddMsgAndPrint("\tNo SSURGO Soil Mapunit Lines to merge",0)

            arcpy.SetProgressorPosition()

        # --------------------------------------------------------------------------------------------------- Merge Soil Mapunit Points
        if not bSTATSGO:
            if len(muPointShpList) > 0:

                arcpy.SetProgressorLabel("Merging " + str(len(muPointShpList)) + " SSURGO Soil Mapunit Point Layers")

                muPointFCpath = os.path.join(FGDBpath, muPointFC)
                arcpy.Merge_management(muPointShpList, muPointFCpath)
                #arcpy.Append_management(muPointShpList, os.path.join(FGDBpath, muPointFC), "NO_TEST", muPointFM)

                AddMsgAndPrint("\tSuccessfully merged SSURGO Soil Mapunit Points",0)

                if not addAttributeIndex(muPointFCpath,["AREASYMBOL","MUSYM"],False): pass

            else:
                AddMsgAndPrint("\tNo SSURGO Soil Mapunit Points to merge",0)

            arcpy.SetProgressorPosition()

        # ---------------------------------------------------------------------------------------------------- Merge Soil Survey Area
        if not bSTATSGO:
            arcpy.SetProgressorLabel("Merging " + str(len(soilSaShpList)) + " SSURGO Soil Survey Area Layers")

            soilSaFCpath = os.path.join(FGDBpath, soilSaFC)
            arcpy.Merge_management(soilSaShpList,soilSaFCpath)

            AddMsgAndPrint("\tSuccessfully merged SSURGO Soil Survey Area Polygons",0)
            if not addAttributeIndex(soilSaFCpath,["AREASYMBOL"],False): pass

            arcpy.SetProgressorPosition()

        # ---------------------------------------------------------------------------------------------------- Merge Special Point Features
        if not bSTATSGO:
            if len(featPointShpList) > 0:

                arcpy.SetProgressorLabel("Merging " + str(len(featPointShpList)) + " SSURGO Special Point Feature Layers")

                featPointFCpath = os.path.join(FGDBpath, featPointFC)
                arcpy.Merge_management(featPointShpList, featPointFCpath)

                AddMsgAndPrint("\tSuccessfully merged SSURGO Special Point Features",0)
                if not addAttributeIndex(featPointFCpath,["AREASYMBOL", "FEATSYM"],False): pass

            else:
                AddMsgAndPrint("\tNo SSURGO Soil Special Point Features to merge",0)

            arcpy.SetProgressorPosition()

        # ---------------------------------------------------------------------------------------------------- Merge Special Line Features
        if not bSTATSGO:
            if len(featLineShpList) > 0:

                arcpy.SetProgressorLabel("Merging " + str(len(featLineShpList)) + " SSURGO Special Line Feature Layers")

                featLineFCpath = os.path.join(FGDBpath, featLineFC)
                arcpy.Merge_management(featLineShpList, featLineFCpath)

                AddMsgAndPrint("\tSuccessfully merged SSURGO Special Line Features",0)
                if not addAttributeIndex(featLineFCpath,["AREASYMBOL", "FEATSYM"],False): pass

            else:
                AddMsgAndPrint("\tNo SSURGO Special Line Features to merge",0)

            arcpy.SetProgressorPosition()

        # Strictly Formatting
        AddMsgAndPrint("\n-------------------------------------------------------------------------------------------------------")

        """ ----------------------------------------------------------------------------------------------------------------------------- Begin the Import Tabular Process"""
        # Import tabular data if option was selected
        if b_importTabularData:

            i = 1
            total = splitThousands(len(soilShpList))

            for survey in soilShpList:

                tabularFolder = os.path.join(os.path.dirname(os.path.dirname(survey)),"tabular")
                spatialFolder = os.path.dirname(survey)

                if os.path.exists(tabularFolder):

                    if bSTATSGO:
                        SSA = os.path.basename(survey)[12:14].upper()
                    else:
                        SSA = os.path.basename(survey)[9:14].upper()

                    # Formatting purposes
                    if i == 1:
                        AddMsgAndPrint("Processing: " + SSA + ": " + str(i) + ' of ' + str(total))
                    else: AddMsgAndPrint("\nProcessing: " + SSA + ": " + str(i) + ' of ' + str(total))

                    # Make a temp copy of the special feature description in the spatial folder and put it in the
                    # tabular folder so that it can be imported.  It will be named "featdesc"
                    specFeatDescFile = spatialFolder + os.sep + "soilsf_t_" + SSA.lower() + ".txt"

                    if os.path.exists(specFeatDescFile):
                        #os.system("copy %s %s" % (specFeatDescFile, tabularFolder + os.sep + "featdesc.txt"))
                        shutil.copy2(specFeatDescFile, tabularFolder + os.sep + "featdesc.txt")

                    # The next 6 lines will report the # of SSURGO features in each SSA dataset
                    if bSTATSGO:
                        AddMsgAndPrint("\tImported " + os.path.basename(survey)[:-4] + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(survey).getOutput(0)))),0)

                    else:
                        AddMsgAndPrint("\tImported " + os.path.basename(survey)[:-4] + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(survey).getOutput(0)))),0)
                        AddMsgAndPrint("\tImported soilmu_l_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilmu_l_" + SSA +".shp")).getOutput(0)))),0)
                        AddMsgAndPrint("\tImported soilmu_p_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilmu_p_" + SSA +".shp")).getOutput(0)))),0)
                        AddMsgAndPrint("\tImported soilsa_a_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsa_a_" + SSA +".shp")).getOutput(0)))),0)
                        AddMsgAndPrint("\tImported soilsf_p_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsf_p_" + SSA +".shp")).getOutput(0)))),0)
                        AddMsgAndPrint("\tImported soilsf_l_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsf_l_" + SSA +".shp")).getOutput(0)))),0)

                    importFailed = 0

                    # Import the text files into the FGDB tables
                    if not importTabularData(tabularFolder,tblAliases,i):
                        importFailed += 1

                    # remove the featdesc file from the tabular folder regardless of import success or not
                    try:
                        os.remove(tabularFolder + os.sep + "featdesc.txt")
                    except:
                        pass

                    del SSA, specFeatDescFile

                else:
                    AddMsgAndPrint("\t\t.....Tabular Folder is missing for: " + SSA,1)

                del tabularFolder, spatialFolder
                i += 1
            del i

            # establish relationships if mapunit Table is not empty
            if int(arcpy.GetCount_management(FGDBpath + os.sep + "mapunit").getOutput(0)) > 0:

                # Establish relationships as long as all of the surveys did not fail to import
                if not importFailed == len(soilShpDict):

                    # establish Relationships
                    if not CreateTableRelationships(tblAliases):
                        AddMsgAndPrint("\tCreateTableRelationships failed", 2)

                else:
                    AddMsgAndPrint("\nThe import tabular function failed on all surveys, Will not establish Spatial relationships.",2)

            else:
                AddMsgAndPrint("\nMapunit table is empty! Relationships will not be established.",2)

        # Import tabular data option was not chosen; simply report the # of SSURGO features in each SSA dataset
        else:
            AddMsgAndPrint("No tabular data will be imported",0)
            i = 0
            for survey in soilSaShpList:

                if bSTATSGO:
                    SSA = os.path.basename(survey)[12:14].lower()
                else:
                    SSA = os.path.basename(survey)[9:14].lower()

                spatialFolder = os.path.dirname(survey)

                AddMsgAndPrint("\nMerge Results: " + SSA.upper(),1)

                # The next 6 lines will report the # of SSURGO features in each SSA dataset
                AddMsgAndPrint("\tImported " + os.path.basename(survey)[:-4] + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(survey).getOutput(0)))),0)

                if not bSTATSGO:
                    AddMsgAndPrint("\tImported soilmu_l_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilmu_l_" + SSA +".shp")).getOutput(0)))),0)
                    AddMsgAndPrint("\tImported soilmu_p_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilmu_p_" + SSA +".shp")).getOutput(0)))),0)
                    AddMsgAndPrint("\tImported soilsa_a_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsa_a_" + SSA +".shp")).getOutput(0)))),0)
                    AddMsgAndPrint("\tImported soilsf_p_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsf_p_" + SSA +".shp")).getOutput(0)))),0)
                    AddMsgAndPrint("\tImported soilsf_l_" + SSA + ".....# of Features: " + str(splitThousands(int(arcpy.GetCount_management(os.path.join(spatialFolder,"soilsf_l_" + SSA +".shp")).getOutput(0)))),0)

                i += 1
                del SSA, spatialFolder
            del i

        # -----------------------------------------------------------------------------  Add Field Aliases to Spatial Layers -tabular already has aliases embedded.
        if updateAliasNames(FGDBpath, GDBname):
            AddMsgAndPrint("\nSuccessfully updated alias names for feature classes within " + os.path.basename(FGDBpath))
        else:
            AddMsgAndPrint("\nUnable to update alias names for feature classes within " + os.path.basename(FGDBpath),2)

        # ----------------------------------------------------------------------------- Add Attribute Index to specific tables
        if not bSTATSGO:
            arcpy.SetProgressorLabel("Adding Attribute Indexes")
            AddMsgAndPrint("\nAdding Attribute Indexes")
            if not addAttributeIndex(os.path.join(FGDBpath,"mapunit"),["musym", "muname","mukind","farmlndcl"],False): pass
            if not addAttributeIndex(os.path.join(FGDBpath,"component"),["comppct_r","compname", "compkind","majcompflag","slope_r","taxorder","taxsuborder","taxgrtgroup","taxsubgrp","taxpartsize"],False): pass
            if not addAttributeIndex(os.path.join(FGDBpath,"muaggatt"),["musym","muname","mustatus","flodfreqdcd","drclassdcd","hydgrpdcd","hydclprs"],False):pass

#         ----------------------------------------------------------------------------- Use the Following code to Add indexes to ALL fields
##            # Add attribute indexes to ALL tables and feature classes in FGDB
##            fgdbTables = arcpy.ListTables('*')
##            fgdbFCs = [fgdbTables.append(fc) for fc in arcpy.ListFeatureClasses('*')]
##
##            # Contains names of fields that could not get indexed
##            fieldsNotIndexed = dict()
##
##            AddMsgAndPrint("\nAdding Attribute Indexes")
##
##            for table in fgdbTables:
##                tablePath = os.path.join(FGDBpath,table)
##                fieldNames = []
##
##                for field in arcpy.ListFields(tablePath):
##
##                    # Had to check if text field was too large b/c index was crashing Arc.
##                    # Specifically, have some fields that are 2147483647 in length and causes
##                    # Arc to crash.  PASS or Continue doesn't work
##                    if field.type == "String" and field.length > 10000:
##
##                        if not fieldsNotIndexed.has_key(table):
##                            fieldsNotIndexed.setdefault(table,[field.name])
##                        else:
##                            fieldsNotIndexed[table].append(field.name)
##
##                    else:
##                        fieldNames.append(field.name)
##
##                if not addAttributeIndex(tablePath,fieldNames,True): continue
##
##            # Report any fields that did not get indexed
##            if fieldsNotIndexed:
##                AddMsgAndPrint("\nThe following fields could not be indexed:",1)
##
##                for rec in fieldsNotIndexed.iteritems():
##                    AddMsgAndPrint("\tTable: " + rec[0],1)
##                    for fld in rec[1]:
##                        AddMsgAndPrint("\t\t" + fld)

        # ------------------------------------------------------------------------------ Summarize output dataset
        AddMsgAndPrint("\n-------------------------------------------------------------------------------------------------------")
        AddMsgAndPrint("Total # of SSURGO Datasets Appended: " + str(splitThousands(len(soilShpList))))
        AddMsgAndPrint("\tTotal # of Mapunit Polygons: " + str(splitThousands(arcpy.GetCount_management(FGDBpath + os.sep + soilFC).getOutput(0))))

        if not bSTATSGO:
            AddMsgAndPrint("\tTotal # of Mapunit Lines: " + str(splitThousands(arcpy.GetCount_management(FGDBpath + os.sep + muLineFC).getOutput(0))))
            AddMsgAndPrint("\tTotal # of Mapunit Points: " + str(splitThousands(arcpy.GetCount_management(FGDBpath + os.sep + muPointFC).getOutput(0))))
            AddMsgAndPrint("\tTotal # of Special Feature Points: " + str(splitThousands(arcpy.GetCount_management(FGDBpath + os.sep + featPointFC).getOutput(0))))
            AddMsgAndPrint("\tTotal # of Special Feature Lines: " + str(splitThousands(arcpy.GetCount_management(FGDBpath + os.sep + featLineFC).getOutput(0))))

        from datetime import datetime
        endTime = datetime.now()
        AddMsgAndPrint("\nTotal Time: " + str(endTime - startTime),0)

    # This is where the fun ends!
    except arcpy.ExecuteError:
        AddMsgAndPrint(arcpy.GetMessages(2),2)

    except:
        errorMsg()
