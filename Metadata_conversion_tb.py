# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 08:00:28 2023

@author: Alexander.Stum
"""

#%% Convert metadata text files to .met formatted files into export folders
# list of metadata files
import os
import arcpy
import subprocess as sp

def metaTool(metaP, exportP, mpPath):
    metas = os.listdir(metaP)
    os.chdir(mpPath)
    exports = {i for i in os.listdir(exportP) if '.' not in i}
    # outputs = []
    for m in metas:
        txtF = f'{metaP}/{m}'
        meta_b = m[-9:-4]
        metF = f'{exportP}/{meta_b}/{meta_b}.met'
    
        runCmd = "mp.exe " + txtF + " -x " + metF
        # out = os.system(runCmd)
        out = sp.check_output(runCmd, stderr=sp.STDOUT, text=True)
        exports.remove(m[-9:-4])
        arcpy.AddMessage(f"\n{meta_b}\n{out}")
        # out = sub.Popen(runCmd, stdout=sub.PIPE)
        # outputs.append(out.stdout.read())
        # if 'No errors' in out:
        #     exports.remove(m[-9:-4])
    
    if exports:
        for e in exports:
            arcpy.AddError(f"Metadata for exports not processed, folder: {e}")
    return


# https://geology.usgs.gov/tools/metadata/tools/doc/mp.html
# https://pro.arcgis.com/en/pro-app/latest/arcpy/metadata/migrating-from-arcmap-to-arcgis-pro.htm



# This is used to execute code if the file was run but not imported
if __name__ == '__main__':

    # Tool parameter accessed with GetParameter or GetParameterAsText
    param0 = arcpy.GetParameterAsText(0)
    param1 = arcpy.GetParameterAsText(1)
    param2 = arcpy.GetParameterAsText(2)
    
    metaTool(param0, param1, param2)