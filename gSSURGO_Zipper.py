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


# ================================================================================================================
def errorMsg():
    try:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = "\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[1] + "\n\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[-1]

        print(theMsg)

    except:
        pass


## ===================================================================================
# Import system modules
import sys, os, traceback, zipfile, glob

if __name__ == '__main__':

    try:

        # Directory containing exports
        #rootDir = arcpy.GetParameterAsText(0)
        #rootDir = r'E:\SSURGO'
        #outDirectory = r'E:\Temp\zipTest'

        rootDir = input("Enter Root Directory containing gSSURGO Datasets to Zip: ")
        outDirectory = input("Enter Root Directory where gSSURGO Datasets will be Zipped: ")

        gSSURGOList = glob.glob(f"{rootDir}\gSSURGO_*.gdb")
        successfulZips = 0

        print(f"\nThere are {len(gSSURGOList)} gSSURGO Datasets that will be zipped.")

        # Iterate through every SSA path and zip up
        for gSSURGO in gSSURGOList:
            print(f"\nCreating zip archive for {os.path.basename(gSSURGO)}")

            try:
                zipName = os.path.basename(gSSURGO).split('.')[0] + '.zip'
                zipFilePath = outDirectory + os.sep + zipName

                if os.path.exists(zipFilePath):
                    print(f"\t{zipName} Exists. Deleting file")
                    os.remove(zipFilePath)

                with zipfile.ZipFile(zipFilePath, 'w', zipfile.ZIP_DEFLATED) as outZip:
                    print(f"\tCreating: {zipName}")

                    for dirpath, dirnames, filenames in os.walk(gSSURGO):

                        for filename in filenames:
                            outZip.write(os.path.join(dirpath, filename), os.path.basename(gSSURGO) + os.sep + filename)

                        successfulZips+=1
                    print(f"\tSuccessfully Archived: {zipName}")

                outZip.close()

            except:
                print("Problems zipping up " + gSSURGO)
                errorMsg()
                continue

            if successfulZips > 0:
                print("\tSuccessfully zipped " + str(successfulZips) + " SSURGO export datasets")

        peaceOut = input("\nDone:  Hit Enter to quit")

    except:
        errorMsg()
        input("\n\nError:  Hit Enter to quit")