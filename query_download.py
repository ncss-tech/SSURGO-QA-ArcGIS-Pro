﻿# -*- coding: utf-8 -*-
"""
Created on Wed Apr 19 21:39:45 2023

Bulk SSURGO Download
A tool for the SSURGO QA ArcGISPro arctoolbox
Downloads soil surveys from Web Soil Survey
Created on: 04/19/2023

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 10/07/2024
    @by: Alexnder Stum
@version: 0.6

# ---
Updated 10/07/2024
- Changed main structure so it can be called by other modules
- Set max threads to 6
"""


import sys
import os
import traceback
import shutil
import zipfile
import socket
import io
from datetime import datetime
from time import sleep
import multiprocessing as mp
import concurrent.futures as cf
import itertools as it
from urllib.request import URLError
import requests
import arcpy


def arcpyErr(func):
    try:
        etype, exc, tb = sys.exc_info()
        line = tb.tb_lineno
        msgs = f"ArcPy ERRORS:\nIn function: {func} on line: {line}\n{arcpy.GetMessages(2)}\n"
        return msgs
    except:
        return "Error in arcpyErr method"

        
def pyErr(func):
    try:
        etype, exc, tb = sys.exc_info()
      
        tbinfo = traceback.format_tb(tb)[0]
        msgs = f"PYTHON ERRORS:\nTraceback info:\nIn function: {func}\n{tbinfo}\nError Info:\n{exc}"
        return msgs
    except:
        return "Error in pyErr method"
     
def removeDir(directory):
    try:
        shutil.rmtree(directory)
        if os.path.isdir(directory): # still exists, try again
            shutil.rmtree(directory)
            if os.path.isdir(directory):
                shutil.rmtree(directory)
            else:
                return (True, directory)
        else:
            return (True, directory)
        msgs = f"Failed to delete: {directory}"
        return [False, msgs]
    except PermissionError as e:
        msgs = f"Failed to delete: {directory}"
        msgs += f'\nPermission Error: {e}'
        return [False, msgs]
    except:
        msgs = f"Failed to delete: {directory}"
        func = sys._getframe(  ).f_code.co_name
        msgs += pyErr(func)
        return [False, msgs]
    


def concurrently(fn, max_concurrency, iterSets, constSets ):
    """
    Adapted from 
    https://github.com/alexwlchan/concurrently/blob/main/concurrently.py
    

    Generates (input, output) tuples as the calls to ``fn`` complete.

    See https://alexwlchan.net/2019/10/adventures-with-concurrent-futures/ 
    for an explanation of how this function works.
    
    Parameters
    ----------
    fn : function
        The function that it to be run in parallel.
        
    max_concurrency : int
        Maximum number of processes, parameter for itertools islice function.
        
    iterSets : list
        List of dictionaries that will be iterated through. The keys of the 
        dictionary must be the same for each dictionary and align with keywords 
        of the function.
        
    constSets : dict
        Dictionary of parameters that constant for each iteration of the 
        function ``fn``. Dictionary keys must align with function keywords.

    Yields
    ------
    A tuple with the original input parameters and the results from the called
    function ``fn``.
    """
    try:
        # Make sure we get a consistent iterator throughout, rather than
        # getting the first element repeatedly.
        # count = len(iterSets)
        fn_inputs = iter(iterSets)
    
        with cf.ThreadPoolExecutor() as executor:
            # initialize first set of processes
            futures = {
                executor.submit(fn, **params, **constSets): params
                for params in it.islice(fn_inputs, max_concurrency)
            }
            # Wait for a future to complete, returns sets of complete and incomplete futures
            while futures:
                done, _ = cf.wait(
                    futures, return_when = cf.FIRST_COMPLETED
                )
    
                for fut in done:
                    # once process is done clear it out, yield results and params
                    original_input = futures.pop(fut)
                    output = fut.result()
                    del fut
                    yield original_input, output
                
                # Sends another set of processes equivalent in size to those just completed
                # to executor to keep it at max_concurrency in the pool at a time,
                # to keep memory consumption down.
                futures.update({executor.submit(fn, **params, **constSets): params
                for params in it.islice(fn_inputs, len(done))
                })
    except GeneratorExit:
        raise
        # arcpy.AddError("Need to do some clean up.")
        # yield 2, 'yup'
    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        msgs = arcpyErr(func)
        yield [2, msgs]
    except:
        func = sys._getframe(  ).f_code.co_name
        msgs = pyErr(func)
        yield [2, msgs]
        
        
## ===================================================================================
def CheckExistingDataset(areaSym, surveyDate, newFolder, template_b):
    """Checks if a more current and complete download of the survey exist
    

    Parameters
    ----------
    areaSym : str
        The area symbol of current soil survey area being processed.
    surveyDate : str
        The date the soil survey area was updated on WSS.
    outFolder : str
        Path that all soil survey directories are being saved
    newFolder : str
        Path of the soil survey download.
    template_b : bool
        Whether user specified download with template database.

    Returns
    -------
    bool
        DESCRIPTION.

    """
    try:
        # file count per SSRUGO version 2.3.3   
        if template_b:
            mainN = 6
            mdbP = f"{newFolder}/soildb_US_2003.mdb"
            mdb_b = os.path.isfile(mdbP)
        else:
            mainN = 5
            mdb_b = True
        spatN = 26
        tabN = 68
        spatF = os.path.join(newFolder, 'spatial')
        tabF = os.path.join(newFolder, 'tabular')
        saCatalog = os.path.join(tabF, "sacatlog.txt")
        msgs = ['']
        msgApp = msgs.append
        
        dbDate = 0
        complete = False
        surveyDate = surveyDate.replace('-', '')
        
        # Check folders for completeness
        if (len(os.listdir(newFolder)) >= mainN) and mdb_b:
            if os.path.isdir(spatF) and len(os.listdir(spatF)) >= spatN:
                if os.path.isdir(tabF) and len(os.listdir(tabF)) >= tabN:
                    if os.path.isfile(saCatalog):
                        complete = True
                        fh = open(saCatalog, "r")
                        rec = fh.readline()
                        fh.close()
                        # Example date (which is index 3 in pipe-delimited file):  9/23/2014 6:49:27
                        vals = rec.split("|")
                        recDate = vals[3]
                        wssDate = "%m/%d/%Y %H:%M:%S"  # string date format used for SAVEREST in text file
                        intDate = "%Y%m%d"             # YYYYMMDD format for comparison
                        dateObj = datetime.strptime(recDate, wssDate)
                        dbDate = int(dateObj.strftime(intDate))
                        if int(surveyDate) <= dbDate:
                            # download_b = False
                            msgApp((f"Local dataset for {areaSym} already exists "
                                   "and is current"))
                            return (0, msgs)
                        else:
                            msgApp(f"Existing dataset out of date: {dbDate}; "
                                   "WSS date: {surveyDate};")
        if not complete:
            msgApp("Exsiting dataset was incomplete.")
        
        rmv_b, msg = removeDir(newFolder)
        if not rmv_b:
            msgApp(msg)
            return [2, msgs]
        else: 
           return (1, msgs)

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        msgApp(arcpyErr(func))
        return [2, msgs]
    except:
        func = sys._getframe(  ).f_code.co_name
        msgApp(pyErr(func))
        return [2, msgs]



## ===================================================================================
def GetDownload(areaSym, surveyDate, outFolder, newFolder, template_b):
    """download survey from Web Soil Survey URL    
    Only the version of zip file without a Template database is downloaded. The user
    must have a locale copy of the Template database that has been modified to allow
    automatic tabular imports.
    

    Parameters
    ----------
    areasym : str
        The area symbol of current soil survey area being processed.
    surveyDate : TYPE
        DESCRIPTION.
    newFolder : TYPE
        DESCRIPTION.
    outFolder : TYPE
        DESCRIPTION.

    Returns
    -------
    bool
        Successfull download.

    """
    # download survey from Web Soil Survey URL and return name of the zip file
    # want to set this up so that download will retry several times in case of error
    # return empty string in case of complete failure. Allow main to skip a failed
    # survey, but keep a list of failures
    #
    # Only the version of zip file without a Template database is downloaded. The user
    # must have a locale copy of the Template database that has been modified to allow
    # automatic tabular imports.

    # create URL string from survey string and WSS 3.0 cache URL
    baseURL = "https://websoilsurvey.sc.egov.usda.gov/DSD/Download/Cache/SSA/"
    msgs = ['']
    msgApp = msgs.append
    try: 
        if template_b:
            zipName = f"wss_SSA_{areaSym}_soildb_US_2003_[{surveyDate}].zip"
        else:
            zipName = f"wss_SSA_{areaSym}_[{surveyDate}].zip"

        zipURL = baseURL + zipName
        msgApp(f"\tDownloading survey {areaSym} from Web Soil Survey...")

        # Open request to Web Soil Survey for that zip file
        r = requests.get(zipURL)
        # Some states have their own template
        if r.status_code == 400 and template_b:
            st = areaSym[0:2]
            zipName = f"wss_SSA_{areaSym}_soildb_{st}_2003_[{surveyDate}].zip"
            zipURL = baseURL + zipName
            r = requests.get(zipURL)
        if r.status_code == 400:
            msgApp(f'Bad Request: {e}')
            msgApp(f"\n{zipURL}")
            return [2, msgs]
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(path=outFolder)
        
        # newFolder = f"{outFolder}/soil_{areaSym.lower()}"
        if not os.path.isdir(newFolder):
            # none of the subfolders within the zip file match any of the expected names
            # msgs = "Subfolder within the zip file does not match any of the standard names"
            msgApp("File did not appear to unzip successfuly")
            return [1, msgs]
        return [0, None]

    except URLError as e:
        msgApp(f'URL error: {e}')
        msgApp(f"\n{zipURL}")
        return [2, msgs]

    except requests.HTTPError as e:
        msgApp(f'HTTP Error {e}')
        return [2, msgs]

    except requests.Timeout:
        msgApp('Soil Data Access timeout error')
        return [2, msgs]

    except socket.error as e:
        msgApp(f'Socket error: {e}')
        msgApp('\nAlso possible File Explorer needs tob be closed')
        return [2, msgs]
    
    except socket.timeout as e:
        msgApp(f'Socket timeout error: {e}')
        return [2, msgs]

    except zipfile.BadZipfile:
        msgApp("Bad zip file?")
        msgApp(f"\n{zipURL}")
        return [2, msgs]
    
    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        msgApp(arcpyErr(func))
        return [2, msgs]
    
    except:
        func = sys._getframe(  ).f_code.co_name
        msgApp(pyErr(func))
        return [2, msgs]



## ===================================================================================
def ProcessSurvey(outputFolder, areaSym, surveyInfo, template_b, overwrite_b):
    """Manages the download process for each soil survey
    

    Parameters
    ----------
    outputFolder : str
        Folder location for the downloaded SSURGO datasets.

    areaSym : str
        The area symbol of current soil survey area being processed.
    surveyInfo : list
        The date the soil survey area was updated on WSS and survey name


    Returns
    -------
    str
        keywords: 'Successful', 'Skipped',or 'Failed'.

    """
    # Download and import the specified SSURGO dataset

    try:
        # get date string
        msgs = ['']
        msgApp = msgs.append
        msgExt = msgs.extend
        surveyDate = surveyInfo[0].strip()
        # get survey name
        # set standard final path and name for template database
        newFolder = f"{outputFolder}/{areaSym.upper()}"
        
        # ---- Call CheckExistingDataset
        if overwrite_b and os.path.isdir(newFolder):
            rmv_b, msg = removeDir(newFolder)
            if not rmv_b:
                msgApp(msg)
                return [2, msgs]
        elif os.path.isdir(newFolder):
            if not surveyDate:
                msgApp("No Survey Date in WSS SSA label")
                return [1, msgs] 
            # if os.path.isdir(newFolder):
            cue, msg = CheckExistingDataset(
                areaSym, surveyDate, newFolder, template_b
            )
            msgExt(msg)
            if not cue:
                # complete and current folder exists
                return [0, msgs]
            elif cue == 2:
                return [2, msgs]

        # ---- Call GetDownload
        # First attempt to download zip file
        # if download_b:
            # Does it need to specify download with .mdb file?
        dcue, _ = GetDownload(
            areaSym, surveyDate, outputFolder, newFolder, template_b)
        if dcue:
            # Try downloading zip file a second time
            sleep(5)
            dcue, msg = GetDownload(
                areaSym, surveyDate, outputFolder, newFolder, template_b)
            if dcue:
                # Failed to download
                msgExt(msg)
                return [dcue, msgs]
        msgApp('Survey successfully downloaded')
        return [0, msgs]

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        msgApp(arcpyErr(func))
        return [2, msgs]
    
    except:
        func = sys._getframe(  ).f_code.co_name
        msgApp(pyErr(func))
        return [2, msgs]


  
def main(args):
    try:
        v = 0.6
        arcpy.AddMessage(f"version {v}")

        # ---- Parameters
        outputFolder = args[0]
        surveyList = args[1]
        template_b = args[2]
        overwrite_b = args[3]
        arcpy.AddMessage(f"{type(surveyList)}: {surveyList}")

        # ---- Setup
        arcpy.AddMessage(f"\n{len(surveyList)} soil survey(s) selected for Web Soil Survey download")

        # ---- Prime For-loop
        # Create ordered list by Areasymbol
        # AREASYMBOL: Date, Survey Name, State
        paramSet = [{'areaSym': ssa,
                   'surveyInfo': s.split(',')[1:]} 
                  for s in surveyList
                  if (ssa := s.split(',')[0].strip().upper()) != 'HT600'
        ]
        
        # %%% By Area Symbol
        surveyCount = len(paramSet)
        threadCount = min(mp.cpu_count(), surveyCount, 6)
        arcpy.AddMessage(f"\tRunning on {threadCount} threads.\n")
        successCount = 0
        failList = []
        # Run import process
        # ---- Call ProcessSurvey
        constSet = {'outputFolder': outputFolder, 
                    'template_b': template_b, 
                    'overwrite_b': overwrite_b}
        for paramBack, output in concurrently(ProcessSurvey,
                                             threadCount,
                                             paramSet,
                                             constSet):
            try:
                outcome, msgs = output
                if outcome == 0:
                    arcpy.AddMessage(f"{paramBack['areaSym']}:")
                    for msg in msgs:
                        arcpy.AddMessage(f"\t{msg}")
                    successCount += 1
                elif outcome == 1:
                    arcpy.AddWarning(f"{paramBack['areaSym']}:")
                    for msg in msgs:
                        arcpy.AddWarning(f"\t{msg}")
                    failList.append(paramBack['areaSym'])
                else:
                    arcpy.AddError(f"{paramBack['areaSym']}:")
                    for msg in msgs:
                        arcpy.AddError(f"\t{msg}")
                    failList.append(paramBack['areaSym'])
            except GeneratorExit:
                pass
                       
        arcpy.SetProgressorLabel("Processing complete...")
        arcpy.AddMessage(f"\nSuccessfully downloaded {successCount} of {surveyCount} surveys.")
        if failList:
            arcpy.AddWarning(f"\n{len(failList)} surveys failed to load:")
            for ssa in failList:
                arcpy.AddWarning(f"\t{ssa}")
            return False
        return True

    except arcpy.ExecuteError:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(arcpyErr(func))
    
    except:
        func = sys._getframe(  ).f_code.co_name
        arcpy.AddError(pyErr(func))

# %% Main
if __name__ == '__main__':
    outputFolder = arcpy.GetParameterAsText(0)
    surveyList = arcpy.GetParameter(2)
    template_b = arcpy.GetParameter(4)
    overwrite_b = arcpy.GetParameter(5)
    main([outputFolder, surveyList, template_b, overwrite_b])
