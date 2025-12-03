#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add_MU_Fields_2TSD
A tool for the SSURGO QA ArcGISPro arctoolbox which adds and populates the
Map unit key (MUKEY), Map unit name (MUNAME), and National map unit symbol
(natmusym) from Soil Data Access

Created on: 9/30/2025

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 12/03/2025
    @by: Alexnder Stum
@version: 1.2

# --- version 1.2, 12/03/2025
- Try second time for connection timeouts
- Added overwrite parameter, allowing to pick up where it last left off
- Save edits of acquired surveys
# --- version 1.1.1, 12/02/2025
- Changed MUNAME schema to 240 characters
# --- version 1.1, 12/02/2025
- Improved messaging
- Fixed capitalization logic error for MUNAME and MUKEY
"""


import sys
import traceback
import requests
import pandas as pd
import arcpy
import time


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


def getRequest(ssa: str) -> pd.DataFrame:
    """Send a request to Soil Data Access to pull down the legend for the 
    requested soil survey area (ssa) with the Area Symbol, map unit symbol, 
    map unit key, national map unit symbol, and map unit name. This is 
    returned as a Pandas dataframe.

    Parameters
    ----------
    ssa : str
        The soil survey area to be queried

    Returns
    -------
    pd.DataFrame
        A dataframe with 4 columns: 
        'musym': str, 'mukey': int32, 'nationalmusym': str, 'muname': str
    """
    try:
        url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'
        # for ssa in ssa_s:
        sql_q = (
        """SELECT mapunit.musym, mapunit.mukey, nationalmusym, muname """ 
        """FROM sacatalog """
        """INNER JOIN legend ON legend.areasymbol = sacatalog.areasymbol """
        f"""AND sacatalog.areasymbol = '{ssa}' """
        """INNER JOIN mapunit ON mapunit.lkey = legend.lkey """
        """ORDER BY  legend.areasymbol, mapunit.musym""")

        dRequest = dict()
        dRequest["format"] = "XML"
        dRequest["query"] = sql_q
        
        try:
            html = requests.post(url, data=dRequest).content
        except:
            etype, exc, tb = sys.exc_info()
            exc = str(exc)
            if "ConnectTimeoutError" in exc:
                time.time(2)
                arcpy.AddMessage("\t2nd try")
                html = requests.post(url, data=dRequest).content
            else:
                arcpy.AddError(pyErr('getRequest'))
                return None

        dtype = {
            'id': object, 'element': object, 'musym': str, 'mukey': 'float64', 
            'nationalmusym': str, 'muname': str
        }
        df = pd.read_xml(html, dtype=dtype)
        df.drop(['id', 'element'], axis=1, inplace=True)
        df.dropna(inplace=True)
        # df['musym'] = df['musym'].astype(int)
        # df['musym'] = df['musym'].astype(str)
        df['mukey'] = df['mukey'].astype(int)
        del html
        return df
    except:
        arcpy.AddMessage(f"\tFailed to get {ssa}")
        arcpy.AddError(pyErr('getRequest'))
        return None


# --- Main Body
if __name__ == '__main__':
    try:
        gdb_p = arcpy.GetParameterAsText(0)
        feat_n = arcpy.GetParameterAsText(1)
        overwrite = arcpy.GetParameter(2)
        v = '1.2'
        arcpy.AddMessage(f'Version: {v}')

        feat_p = f"{gdb_p}/{feat_n}"

        # Check for fields
        check_l = ['mukey', 'natmusym', 'muname']
        d = arcpy.Describe(feat_p)
        for f in d.fields:
            #arcpy.AddMessage(f.name.lower())
            if f.name.lower() in check_l:
                check_l.remove(f.name.lower())
                arcpy.AddMessage(f"{f.name} field already present")

        field_desription = ""
        field_l = []
        if 'mukey' in check_l:
            field_desription = "MUKEY LONG # # # #;"
            field_l.append('MUKEY')
        if 'natmusym' in check_l:
            field_desription += "natmusym TEXT 'National MUSYM' 23 # #;"
            field_l.append('natmusym')
        if 'muname' in check_l:
            field_desription += "MUNAME TEXT 'Mapunit Name' 240 # #"
            field_l.append('MUNAME')
        field_desription = field_desription.rstrip(';')

        # Add Fields
        if field_desription:
            arcpy.AddMessage(f"Adding fields {field_l}")
            arcpy.management.AddFields(
                in_table=feat_p,
                    field_description=field_desription,
                    template=None
                )
        # Disable tracking
        try:
            arcpy.management.DisableEditorTracking(
                feat_p, True, True, True, True
            )
        except:
            pass
        edit = arcpy.da.Editor(gdb_p)
        edit.startEditing(True, True)
        edit.startOperation()
        # Update feature
        uCur = arcpy.da.UpdateCursor(
            feat_p, 
            ['AREASYMBOL', 'MUSYM', 'MUKEY', 'natmusym', 'MUNAME'], 
            sql_clause=(None, "ORDER BY AREASYMBOL ASC")
        )
        ssa_k = ''
        df = None
        for u_row in uCur:
            ssa = u_row[0]
            musym = u_row[1]
            mukey = u_row[2]
            natsym = u_row[3]
            muname = u_row[4]
            if not overwrite and mukey and natsym and muname:
                continue
            # cursor is sorted by SSA so request by SSA
            if ssa != ssa_k:
                arcpy.AddMessage(f"Populating {ssa}")
                ssa_k = ssa
                df = getRequest(ssa)
            
            # Get mapunit row from dataframe
            # df_row: musym, mukey, nationalmusym, muname
            df_row = list(*df[df['musym']==musym].values)
            if df_row:
                uCur.updateRow([ssa,] + df_row)
            else:
                arcpy.AddWarning(f"\tMap unit {ssa}: {musym} not retrieved.")
        del uCur
        # edit.stopOperation()
        edit.stopEditing(True)
        try: 
            arcpy.EnableEditorTracking_management(
                feat_p, 'Creator', 'Creation_Date', 'Editor',
                'Last_Edit_Date'
            )
        except:
            pass
        del edit
    except arcpy.ExecuteError:
        arcpy.AddError(arcpyErr('main'))
    except:
        arcpy.AddError(pyErr('main'))
    finally:
        try:
            del uCur
        except:
            pass
        try:
            edit.stopEditing(True)
            del edit
        except:
            pass

