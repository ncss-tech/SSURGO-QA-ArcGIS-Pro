# ---------------------------------------------------------------------------
# SSURGO_Zipper.py
# Created on: May 10, 2013

# Author: Charles.Ferguson
#         Soil Scientist
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
#-------------------------------------------------------------------------------


# ===============================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:

        #print(msg)
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
# Import system modules
import sys, os, traceback, zipfile, arcpy

if __name__ == '__main__':

    try:

        # Directory containing exports
        rootDir = arcpy.GetParameterAsText(0)
        #rootDir = r'E:\SSURGO\export'

        # Input SSA list to zip up
        ssaList = arcpy.GetParameter(1)
        #ssaList = ['ia005', 'ia015', 'ia059', 'ia061', 'ia151', 'ia187', 'wi113', 'wi119']

        # Directory Path of valid SSAs to zip up
        ssaToZipUp = list()

        for ssa in ssaList:

            ssaPath = os.path.join(rootDir,ssa)

            # Itereate through each file and determine if if is a legit SSA
            if os.path.isdir(ssaPath) and len(ssa) == 5 and ssa[:2].isalpha() and ssa[2:].isdigit():

                # Get a list of export files to determine if they correct
                exportFiles = os.listdir(ssaPath)
                validFiles = [ssa + "_a.shp", ssa + "_b.shp", ssa + "_c.shp",ssa + "_d.shp",
                              ssa + "_l.shp", ssa + "_p.shp", 'feature', ssa + ".met"]
                validCnt=0

                for item in validFiles:
                    if not item in exportFiles:
                        AddMsgAndPrint(ssa + " is missing " + item + " file; " + ssa + " will not be zipped",1)
                        break
                    else:
                        validCnt+=1

                if validCnt == 8:
                    ssaToZipUp.append(ssaPath)

        ssaCnt = len(ssaList)
        ssaZipCnt = len(ssaToZipUp)
        successfulZips = 0

        arcpy.SetProgressor('step', 'Creating Archives...', 0, len(ssaToZipUp), 1)

        # Iterate through every SSA path and zip up
        for SSA in ssaToZipUp:
            AddMsgAndPrint('\n-------- ' + 'Creating zip archive for ' + os.path.basename(SSA) + '\n')
            arcpy.SetProgressorLabel('Archiving: ' + os.path.basename(SSA))

            try:
                zipFilePath = SSA.lower() + '.zip'

                if os.path.exists(zipFilePath):
                    AddMsgAndPrint(os.path.basename(SSA) + ".zip" + " Exists. Overwriting file",1)

                with zipfile.ZipFile(zipFilePath, 'w', zipfile.ZIP_DEFLATED) as outZip:
                    AddMsgAndPrint("Archive Path: " + zipFilePath)

                    for dirpath, dirnames, filenames in os.walk(SSA):
                        #outZip.write(dirpath)

                        for filename in filenames:
                            outZip.write(os.path.join(dirpath, filename), os.path.basename(SSA.lower()) + os.sep + filename)
                            #AddMsgAndPrint(os.path.join(dirpath, filename) + "---------" +  os.path.basename(SSA.lower()) + os.sep + filename)
                        successfulZips+=1

                outZip.close()

            except:
                AddMsgAndPrint("Problems zipping up " + SSA,2)
                errorMsg()
                continue

            if successfulZips > 0:
                AddMsgAndPrint("Successfully zipped " + str(successfulZips) + " SSURGO export datasets")

            arcpy.SetProgressorPosition()

    except:
        errorMsg()