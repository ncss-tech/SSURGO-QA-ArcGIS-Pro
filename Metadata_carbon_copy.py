#! /usr/bin/env python3
# # -*- coding: utf-8 -*-
"""
Metadata Carbon Copy tool
Makes copies of the source metadata file soil_metadata_<SSA>.xml 
and writes a new copy to the respective SSURGO export directory 
as a .met file.
It isn't an actual carbon copy as leading white space is stripped 
and the following header line is added: 
'<?xml version="1.0" encoding="ISO-8859-1"?>'

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@created 3/19/2025
@modified 3/19/2025
    @by: Alexnder Stum
@version: 1.0
"""


import os
import re
import sys
import traceback
import arcpy


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
    

def main():
    try:
        ssurgo_p = arcpy.GetParameterAsText(0)
        export_p = arcpy.GetParameterAsText(1)

        hdr = '<?xml version="1.0" encoding="ISO-8859-1"?>'

        source_dirs = [
            d_n for d in os.scandir(ssurgo_p) if (
                d.is_dir() and re.match(
                    r"[a-zA-Z]{2}[0-9]{3}",
                    d_n := d.name.removeprefix('soil_')
                )
                and os.path.exists(f"{d.path}/tabular")
                and os.path.exists(f"{d.path}/spatial")
                and os.path.exists(f"{d.path}/soil_metadata_{d_n.lower()}.xml")
        )]

        export_dirs = [
            d_n for d in os.scandir(export_p) if (
                d.is_dir() and re.match(
                    r"[a-zA-Z]{2}[0-9]{3}",
                    d_n := d.name.removeprefix('soil_')
                )
                and os.path.exists(f"{d.path}/tabular")
                and os.path.exists(f"{d.path}/spatial")
        )]
        
        strip = lambda l: l.lstrip() if l.lstrip()  else '\n'
        for ex_d in export_dirs:
            if ex_d in source_dirs:
                # read file
                txt = f"{ssurgo_p}/{ex_d}/soil_metadata_{ex_d.lower()}.xml"
                with open(txt, "r") as read_f:
                    txt_lines = read_f.readlines()
                # remove leading whitespace
                txt_lines = [strip(line) for line in txt_lines]
                # write file
                txt = f"{export_p}/{ex_d}/{ex_d.lower()}.met"
                with open(txt, "w") as write_f:
                    write_f.write(hdr)
                    write_f.writelines(txt_lines)
                arcpy.AddMessage(f"\tSuccessfully copied {txt}")
            else:
                arcpy.AddWarning(f"A source directory not found for {ex_d}")

    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        raise
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        raise

if __name__ == '__main__':
    main()