#! /usr/bin/env python3
# # -*- coding: utf-8 -*-
"""
SSURGO Shoehorn
A tool to insert updated Soil Survey Areas (SSA) into an RTSD.
This tool snaps input to match adjacent SSA's, reduce excessive vertices, 
and ammend some acute vertices.

@author: Alexander Stum
@maintainer: Alexander Stum
    @title:  GIS Specialist & Soil Scientist
    @organization: National Soil Survey Center, USDA-NRCS
    @email: alexander.stum@usda.gov

@modified 3/13/2025
    @by: Alexnder Stum
@version: 2.10

# ---
Update 2.10; 3/13/2025
- Applied new XY Resolution standard of 0.0001 m
- Cleaned up formatting of script
- numpy.bool was deprecated, updated references to bool
- Explicitly defined spatial Reference for Point Geometries created by BNODES
    and BNODES2 functions
# ---
Update 2.9.3
- Added main function
- In BNodes function added search distance = to Boundary Tolerance parameter
     to select polygons that are shy of the boundary due to imperfect fit
- Changed how arcpy Arrays are packaged in ShapeUp, it wasn't pulling out 
    inner rings in Pro 2.9 and its faster to feed straight list comprehnesions
    to arcpy.Array instead of other arrays.
# ---
Update 2.9.2
- Warning message from BCore function if error in BNodes2
# ---
Update 2.9.1
- removed arc.env arguments from the BCore function, seems that causes error
    calling those in parallel environments.
# ---
Update 2.9
- modified Douglas-Peucker functions rdpi and rdps to deal with vertex rich
    single arc loops
- In Tweezer, modified so 3-vertex arcs can be generalized
# ---
Update 2.8c
- Updated handling of edit tracking fields
- Added snapping of boundary nodes to survery boundaries VERTEX 
    and EDGE for sparse areas
"""


# import modules
import arcpy
import sys
import os
import xlwt
import math
import time
import warnings  # psutil
import multiprocessing as mp
import numpy as np
import traceback
import Shoehorn_multi2_9_3
import importlib
importlib.reload(Shoehorn_multi2_9_3)
from Shoehorn_multi2_9_3 import *

warnings.filterwarnings("ignore")


#%% Functions
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


def get_install_path():
    """
    Return 64bit python install path from registry 
    (if installed and registered),
    otherwise fall back to current 32bit process install path.
    """
    if sys.maxsize > 2**32:
        return sys.exec_prefix  # We're running in a 64bit process
    # We're 32 bit so see if there's a 64bit install
    path = r'SOFTWARE\Python\PythonCore\2.7'
    from winreg import OpenKey, QueryValue
    from winreg import HKEY_LOCAL_MACHINE, KEY_READ, KEY_WOW64_64KEY
    try:
        with(
            OpenKey(HKEY_LOCAL_MACHINE, path, 0, KEY_READ | KEY_WOW64_64KEY) 
            as key):
            # We have a 64bit install, so return that.
            return QueryValue(key, "InstallPath").strip(os.sep)
    except:
        return sys.exec_prefix  # No 64bit, so return 32bit path
    # https://www.e-education.psu.edu/geog489/node/2263


def rdpi(M, epsilon=0, hopper={}):
    """Helper function for rdps function, 
    implementing Douglas-Peucker Method."""
    try:
        if not hopper:
            hopper = {0: M.shape[0] - 1}
        dump = np.ones(M.shape[0], bool)
        while hopper:
            i, f = hopper.popitem()
            start, end = M[(i, f),]
            vec = end - start
            dists = (np.absolute(np.cross(vec, start - M[i:f + 1,])) 
                     / np.linalg.norm(vec))
            imax = np.argmax(dists)
            dmax = dists[imax]
            imax += i         
            if dmax > epsilon:
                if imax - i > 1:
                    hopper[i] = imax
                if f - imax > 1:
                    hopper[imax] = f
            else:
                dump[i + 1:f,] = False
        return dump
    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        raise
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        raise
        

def rdps(M, E=1):
    """Implementation of the Douglas-Peuker Methodology."""
    try:
        close = np.ones(M.shape[0], bool)
        # offset by 2
        v = M[2:,] - M[:-2,]
        dist = (np.abs(np.cross(v, M[:-2,] - M[1:-1])) 
                / np.linalg.norm(v, axis=1))
        close[1:-1] = dist >= E
        inrow = ~(close[1:] | close[:-1])
        if inrow.any():
            contigI = np.ones(M.shape[0], bool)
            contigI[1:-1] = inrow[:-1] | inrow[1:]  # is there a neighbor?
            contig = np.where(contigI[1:-1])[0] + 1
            # realm of contiguous occurences
            neigh = set(range(contig[0] - 1, contig[-1] + 2))
            inter = neigh - set(contig)
            iS = [j for j in inter if j + 1 in contig]
            fS = [i + 1 for i in contig if i + 1 in inter]
            if (len(fS) < 2) and (fS[0] > dist.size): # if enclosed
                far = np.argmax(dist) +1
                iS.append(far)
                fS.append(far)
            iS.sort()
            fS.sort()
            dump = rdpi(M, E, dict(zip(iS, fS)))
            close[contigI] = dump[contigI]
        return M[close,]
    except arcpy.ExecuteError:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(arcpyErr(func))
        raise
    except:
        func = sys._getframe().f_code.co_name
        arcpy.AddError(pyErr(func))
        raise


def BNodes(SA_, MU, nodes, dec, sr):
    try:
        # ======= Variables  ==========
        MU_         = "in_memory/MU_outline"
        MU_o        = "MU_outer"
        MU_d        = "in_memory/MU_d"
        Point       = arcpy.Point
        PG          = arcpy.PointGeometry

        arcpy.management.SelectLayerByLocation(MU, 
                                               "INTERSECT", 
                                               SA_) 
                                               # search_distance = BT) #,
                                               # None, "SUBSET_SELECTION")
        arcpy.PolygonToLine_management(MU, MU_)
        arcpy.MakeFeatureLayer_management(MU_, MU_o, "LEFT_FID = -1")
        arcpy.management.SelectLayerByLocation(MU_o, 
                                               "INTERSECT", 
                                               SA_)
                                               # search_distance = BT) #,
                                               # None, "SUBSET_SELECTION")
        MU_d = arcpy.analysis.PairwiseDissolve(MU_o, 
                                               arcpy.Geometry(),
                                               "RIGHT_FID",
                                               None, 
                                               "MULTI_PART")
        points = {(round(p.X, dec), round(p.Y, dec))
                              for G in MU_d 
                              for P in G
                              # for the for the last and first points
                              for p in [P[0], P[-1]]}

        nodePot = tuple((PG(Point(x, y), sr) for x, y in points))
        arcpy.CopyFeatures_management(tuple(nodePot), nodes)


    except:
        arcpy.AddError("Error in BNodes function: " + 
                       str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise


def BNodes2(MU, nodes, areas, dec, pCores, sr):
    try:
        #======= Variables  ==========
        nodeS       = set() # []
        update      = nodeS.update # .append
        Point       = arcpy.Point
        PG          = arcpy.PointGeometry
        pool        = None
        result      = None
        
        arcpy.env.parallelProcessingFactor = 2  # threads
        mp.set_executable(os.path.join(get_install_path(), 'pythonw.exe'))
        pool = mp.Pool(pCores)
        result = [pool.apply_async(BCore, args=(A, MU, dec), callback=update)
                  for A in areas]
        # arcpy.AddMessage(str(result[0].get()))
        pool.close()
        pool.join()
        arcpy.env.parallelProcessingFactor = pCores
        # arcpy.AddMessage(f'New Nodes: {len(nodeS)}')
        nodePot = tuple((PG(Point(x, y), sr) for x, y in nodeS))
        # arcpy.AddMessage(f'New Nodes: {len(nodePot)}')
        arcpy.CopyFeatures_management(nodePot, nodes)

    except:
        if pool:
            pool.close()
        if result:
            arcpy.AddWarning(str(result[0].get()))
        arcpy.AddError("Error in BNodes2 function: " + 
                       str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise


def tweezer(arcs, inter, v0, MUpoly_, N, cutV, weakEggs ,min_angle, dec, polys):
    #% Tweezer: removal of acute angles
    try:

        ###Localize function calls
        frombuffer  = np.frombuffer
        arccos      = np.arccos
        concatenate = np.concatenate
        Point       = arcpy.Point
        f64         = np.float64
        Round       = np.round
        ein         = np.einsum
        sqrt        = np.sqrt

        eS = '...i,...i'
        eS2 = 'ij,ij->i'
        eS2t = 'ijk,ijk->ij'
        shapes = {}
        cut = [[], []]
        node_c = []

        v3 = np.zeros((N, 3, 2), dtype=f64)     # 2nd from coordinates

        ### Remove acute angles along arc lengths

        sCur = arcpy.da.SearchCursor(MUpoly_, ['SHAPE@', 'OID@'])
        for geom, fid in sCur:

            ((NiH, v3iH, RLiH), (NiT, v3iT, RLiT)) = arcs[fid]

            wkb = geom.WKB      # spit out coords in binary
            # Assumes single part polylines
            npGeom = Round(frombuffer(wkb[18:], dtype=f64), decimals=dec)
            npGeom = npGeom.reshape((npGeom.size//2, 2))   # pair up x,y coords

            # Ralfs law, inner1d computes cross product of an array of vectors
            # angle = arccos((v1.v2)/(|v1||v2|))
            # sqrt(ein(eS2, v1, v1)) is eqivalent to ((v1*v1).sum(axis=1))**.5
            # https://math.stackexchange.com/questions/11346/how-to-compute-the-angle-between-two-vectors-expressed-in-the-spherical-coordina # noqa
            # https://stackoverflow.com/questions/9171158/how-do-you-get-the-magnitude-of-a-vector-in-numpy # noqa
            # Create an array of vector pairs
            v1 = npGeom[:-2, ] - npGeom[1:-1, ]
            v2 = npGeom[2:, ] - npGeom[1:-1, ]
            angles = arccos(ein(eS, v1, v2) / sqrt(ein(eS2, v1, v1)) /
                            sqrt(ein(eS2, v2, v2)))
            acuteI = angles > min_angle
            # Find all vertices less than min angle
            newCore = npGeom[1:-1, ][acuteI]

            if (newCore.size // 2 > 1) or ((NiH != NiT) and newCore.size):
                if RLiT + 1:  # Not along survey boundary
                    # Snap Nodes
                    newGeom = concatenate((v0[NiH], newCore, v0[NiT]), axis=0)
                    newGeom = rdps(newGeom)
                    shapes[fid] = newGeom
                    if (~acuteI).any():
                        # the rejects
                        cut[0] += list(npGeom[1:-1, ][~acuteI])
                        cut[1] += list(angles[~acuteI])
                else:
                    # Snap Nodes
                    newGeom = concatenate(
                        (v0[NiH], npGeom[1:-1], v0[NiT]), axis=0
                    )
                    shapes[fid] = newGeom
                v3[NiH, v3iH] = newGeom[1, ]   # vertex second from start
                v3[NiT, v3iT] = newGeom[-2, ]  # vertex second from last
            elif NiH != NiT:  # only were two vertices
                newGeom = concatenate((v0[NiH], v0[NiT]), axis=0) # npGeom[1:-1]
                shapes[fid] = newGeom
                v3[NiH, v3iH] = newGeom[1, ]   # vertex second from start
                v3[NiT, v3iT] = newGeom[-2, ]  # vertex second from last
            else:   # line collapsed to point
                arcpy.AddMessage(f"fid {fid} line segment has collapsed")
                inter[NiH] = 0        # Prevent manipulation of involved Nodes
                polys[RLiH][0].remove((fid, 1))
                if not polys[RLiH][0]:
                    polys.pop(RLiH)
                    weakEggs['Tweezer'].append(str(RLiH))
                if RLiT+1:
                    polys[RLiT][0].remove((fid, -1))
                # If polygon as no other arcs, remove it
                    if not polys[RLiT][0]:
                        polys.pop(RLiT)
                        weakEggs['Tweezer'].append(str(RLiT))

        ### arc-Node position
        # Calculate Angles at Nodes 3 positions
        angles = np.zeros((N, 3, 1), dtype=np.float32)
        v3v = v3-v0

        angles[:, 0, 0] = arccos(ein(eS, v3v[:, 1, :], v3v[:, 2, :]) /
                                 sqrt(ein(eS2, v3v[:, 1, :], v3v[:, 1, :])) /
                                 sqrt(ein(eS2, v3v[:, 2, :], v3v[:, 2, :])))
        angles[:, 1, 0] = arccos(ein(eS, v3v[:, 0, :], v3v[:, 2, :]) /
                                 sqrt(ein(eS2, v3v[:, 0, :], v3v[:, 0, :])) /
                                 sqrt(ein(eS2, v3v[:, 2, :], v3v[:, 2, :])))
        angles[:, 2, 0] = arccos(ein(eS, v3v[:, 0, :], v3v[:, 1, :]) /
                                 sqrt(ein(eS2, v3v[:, 0, :], v3v[:, 0, :])) /
                                 sqrt(ein(eS2, v3v[:, 1, :], v3v[:, 1, :])))

        acute = angles < min_angle
        acute[0, :, :] = False
        ### Realign acute Nodes
        # Realign arcs incident to acute angels at Nodes

        if acute.any():
            # Where a Node is involved with only ONE acute angle and only three
            # arcs and not on border
            LookUp = (acute.sum(axis=1) == 1).reshape((N)) & (inter == 3).T
            if LookUp.any():
                acuteI = np.where(LookUp)  # Node ID's involved with acute angle
                nn = acuteI[0].shape[0]             # Number of actue angles
                # L = np.zeros((nn, 3, 1), dtype=np.float32)
                # Lengths of vectors
                # arcpy.AddMessage(str(acuteI.shape))
                # arcpy.AddMessage(str(acuteI))
                L = sqrt(
                    ein(eS2t, v3v[acuteI[0],:,:], 
                        v3v[acuteI[0],:,:])).reshape([nn, 3, 1])
                # arcpy.AddMessage(str(L.shape))

                pos = np.ones((nn, 3, 1), dtype=np.int8)*-1
                # position of the acute angle, When evaluating Nodes with 3
                # vectors, there can only be one acute angle
                back = np.argmin(angles[acuteI], axis=1)
                # vector position of back vector
                pos[range(nn), (back[:, 0])] = back
                i0 = np.where(back == 0)[0]
                i1 = np.where(back == 1)[0]
                i2 = np.where(back == 2)[0]
                # Determine longest vector forming acute angle
                pos[i0, (np.argmax(L[i0, 1:, 0], axis=1)+1), 0] = 3
                pos[i1, (np.argmax(L[i1][:, (0, 2), 0], axis=1)*2), 0] = 3
                pos[i2, (np.argmax(L[i2, : -1, 0], axis=1)), 0] = 3

                # Record acute angle
                iCur = arcpy.da.InsertCursor(cutV, ['SHAPE@', 'angle', 'type'])
                for i in acuteI[0]:
                    p = arcpy.PointGeometry(Point(*v0[i, 0, :]))
                    theta = angles[i, :, :].min()
                    if theta < min_angle:
                        deg = float(np.rad2deg(theta))
                        iCur.insertRow([p, deg, 'Node'])
                del iCur

                # for each arc involved with Nodes
                for fid, HTi in zip(*np.where(np.isin(arcs['Ni'], acuteI[0]))):
                    (Ni, v3i, RLi) = arcs[fid, HTi]
                    npGeom = shapes[fid]

                    ii = np.where(acuteI[0] == Ni)[0]  # relative index

                    if not HTi:   # If head-Node involved with acute angle
                        if pos[ii, v3i] == -1:  # short arc, remove first point
                            newGeom = npGeom[1:]
                        # long arc, remove first, add short
                        elif pos[ii, v3i] > 2:
                            # newGeom = npGeom[1:]
                            # get point from v3 and position from pos
                            yy = np.where(pos[ii] == -1)[1]
                            p = v3[Ni, yy]
                            newGeom = concatenate((p, npGeom[1:]), axis=0)
                        else:  # back arc
                            yy = np.where(pos[ii] == -1)[1]
                            p = v3[Ni, yy]
                            newGeom = concatenate((p, npGeom), axis=0)

                    else:   # If tail-Node involved with acute angle
                        if pos[ii, v3i] == -1:  # short arc, remove first point
                            newGeom = npGeom[:-1]
                        # long arc, remove first, add short
                        elif pos[ii, v3i] > 2:
                            # newGeom = npGeom[:-1]
                            # get point from v3 and position from pos
                            yy = np.where(pos[ii] == -1)[1]
                            p = v3[Ni, yy]
                            newGeom = concatenate((npGeom[:-1], p), axis=0)
                        else:
                            yy = np.where(pos[ii] == -1)[1]
                            p = v3[Ni, yy]
                            newGeom = concatenate((npGeom, p), axis=0)

                    if newGeom.shape[0] > 2 or \
                       (newGeom.shape[0] == 2 and not
                       (newGeom[0, :] == newGeom[1, :]).all()):
                        shapes[fid] = newGeom

                    else:
                        ((NiH, v3iH, RLiH), (NiT, v3iT, RLiT)) = arcs[fid]
                        polys[RLiH][0].remove((fid, 1))
                        node_c.append((NiH, NiT))
                        if not polys[RLiH][0]:
                            polys.pop(RLiH)
                            weakEggs['Tweezer'].append(str(RLiH))
                        if RLiT+1:
                            polys[RLiT][0].remove((fid, -1))
                        # If polygon as no other arcs, remove it
                            if not polys[RLiT][0]:
                                polys.pop(RLiT)
                                weakEggs['Tweezer'].append(str(RLiT))
        ### Wrap up
        if node_c:  # Snaps Node references where arcs have collapsed
            for N1, N2 in node_c:
                arcs['Ni'][arcs['Ni'] == N1] = N2
                arcs['Ni'][arcs['Ni'] == N2] = N1
        if cut:
            iCur = arcpy.da.InsertCursor(cutV, ['SHAPE@', 'angle', 'type'])
            try:
                for xy, theta in zip(cut[0], cut[1]):
                    p = arcpy.PointGeometry(Point(*xy))
                    if theta < min_angle:
                        deg = float(np.rad2deg(theta))
                        iCur.insertRow([p, deg, 'vertex'])
                del iCur
            except:
                arcpy.AddWarning('Adding to cut_vertices failed')
                arcpy.AddWarning(str(xy)+' '+str(deg)+' vertex')
                del iCur
                pass

        return (shapes, weakEggs)
    except:
        arcpy.AddError("Tweezer: Unexpected error on line: " + 
                       str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise


def Reassemble(
        iCur, arcs, polys, shapes, weakEggs, badEggs, pCores, areaSym, SFDS, 
        edit
        ):
    count = 0
    postV = 0
    newShape = []
    update = newShape.append
    arcpy.env.parallelProcessingFactor = 2  # threads
    mp.set_executable(os.path.join(get_install_path(), 'pythonw.exe'))
    pool = mp.Pool(pCores)
    ### Assemble Polygons
    try:
        for FID, [ai, mu] in polys.items():
            try:
                # subset of arcs; a sub copy more efficient that searching
                # entire arcs and they're sorted in ai order
                # a0 is tuple of arc ID's; 
                # a1 tuple of the arc position in 'arcs'
                a0, a1 = zip(*((i, (j-1)//-2) for i, j in ai))
                parcs = arcs[a0, :]
                parcs2 = arcs[a0, a1]

                pool.apply_async(ShapeUp,
                                 args=(parcs, parcs2, ai,
                                       {k: shapes[k] for k in a0}, mu, FID),
                                 callback=update)
            except:
                arcpy.AddWarning(f"Failure rassembling polygon {FID}")
                badEggs['Reassembly'].append(str(FID))
        pool.close()
        pool.join()
        arcpy.env.parallelProcessingFactor = pCores
    ### Insert Polygons
        insertRow = iCur.insertRow
        for mu, poly in newShape:
            if mu is not None:
                insertRow([areaSym, mu, poly])
                count += 1
                postV += poly.pointCount
            else:
                if poly[0] > 0:
                    weakEggs['Reassembly'].append(str(poly[0]))
                else:
                    badEggs['Reassembly'].append(str(poly[0] * -1))
        del arcs, shapes
        
        return postV, count, weakEggs, badEggs
    except:
        try:
            if newShape:
                salvage = tuple((polygon for mu, polygon in newShape if mu))
                if salvage:
                    t = str(int(time.time()))
                    salvaged = os.path.join(SFDS, 'salvaged' + t)
                    arcpy.CopyFeatures_management(salvage, salvaged)
                    arcpy.AddWarning(
                        "Something didn't working during reassembly. "
                        f"See shoehorn_FDS/{salvaged} to see how far it got."
                    )
            edit.stopOperation()
            edit.stopEditing(False)
        except:
            None
        arcpy.AddError("Unexpected error on line: " + 
                       str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        raise


# %% Main
def main():
    try:
        ######################
        #======= Parameters  ==========
        MUin = arcpy.GetParameterAsText(0)
        areaField = arcpy.GetParameterAsText(1)
        muField = arcpy.GetParameterAsText(2)
        RTSD = arcpy.GetParameterAsText(3)
        areas = arcpy.GetParameter(4)
        insert = arcpy.GetParameter(5)
        MUout = arcpy.GetParameterAsText(6)
        degrees = arcpy.GetParameter(7)
        # Needs to be xls
        excel_n = arcpy.GetParameterAsText(8).split('.')[0]
        excel_p = ("%r" % arcpy.GetParameterAsText(9)).replace("'", "")
        excel = os.path.join(excel_p, excel_n+'.xls')
        retain = arcpy.GetParameter(10)
        BT = arcpy.GetParameter(11)

        # %%% Variables
        start           = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        gdb             = os.path.dirname(RTSD)
        SFDS_n          = "shoehorn_FDS"
        SFDS            = os.path.join(gdb, SFDS_n)
        min_angle       = np.deg2rad(degrees)
        nSurvs          = len(areas)
        f               = 100/(nSurvs*3)

        SAR             = RTSD + '/SAPOLYGON'
        SAR_L           = "SAR_Layer"                       #RTSD SAPOLYGONS
        SAR_L2          = "SAR_Layer2"                       #RTSD SAPOLYGONS
        SAR_L4          = "SAR_Layer4"
        SARline         = "in_memory/SApoly"
        SARline_L       = "SARline_layer"
        SARsplit_m      = "in_memory/SARsplit_multi"
        SARsplit        = SFDS + "/SARsplit"  #delete in first round
        SARstart        = "in_memory/SARstart"
        SAmis           = "MU2SA_off"
        SA1_            = "in_memory/SA1"
        SA1_L           = "SA1_L"
        
        MUbase          = os.path.basename(MUin)
        MU              = os.path.join(RTSD, 'MUPOLYGON')
        MUR_L           = "RTSD_layer"
        survey          = "MUsurvey"

        mid             = "in_memory/mid"
        mid_L           = "mid_layer"
        nodes           = "in_memory/nodes"
        kNodes          = "in_memory/keyNodes"
        nNodes          = "in_memory/newNodes"
        bNodes          = os.path.join(SFDS,'BoundaryNodes')
        bound_L         = "Boundary_Layer"

        MUinter         = "MUinter"
        MUinter_L       = "MUinter_L"
        MUsplit         = "in_memory/MUsplit"
        MUpoly_L        = "MUpolyline_layer"

        ends            = "in_memory/End_ends"   #
        starts          = "in_memory/Start_ends"  #
        TheEnd          = "in_memory/The_Ends"
        # Nodes           = "Nodes"    #Need delete

        arcpy.env.workspace = RTSD
        if not retain:
            MUpoly          = "in_memory/MU_poly2line"
            # NodeArc         = "in_memory/Node2Arc"
            MUpoly_         = "in_memory/MU_poly2line_sp"


        else:
            TheEnd          = "The_Ends"
            MUpoly          = "MU_poly2line"
            # NodeArc         = "Node2Arc"
            MUpoly_         = "MU_poly2line_sp"
            kNodes          = "keyNodes"
            nNodes          = "newNodes"
            SARline         = "SApoly"
            MUsplit         = "musplit"
            
            if arcpy.ListFeatureClasses(kNodes):
                arcpy.Delete_management(kNodes)
            if arcpy.ListFeatureClasses(nNodes):
                arcpy.Delete_management(nNodes)


        failed          = set()
        cutV            = "amended_vertices"
        weakE           = "Collapsed"
        badE            = "polygon_errors"
        weakEggs        = {'Tweezer':[],'Reassembly':[],'Cluster Tolerance':[]}
        badEggs         = {'Exception':[],'Reassembly':[]}

        # %%% General Setup
        arcpy.AddMessage("Shoehorn Version 2.10")
        # threads = psutil.cpu_count()/psutil.cpu_count(False)
        # keep in mind this actually returns threads, not cores
        cores = os.cpu_count()
        # Leaves one physical core free, assuming two threads per core
        pCores = cores//2 - 1
        # pCores = str((cores-4)/cores*100)+'%'
        arcpy.env.parallelProcessingFactor = pCores
        arcpy.env.overwriteOutput = True

        MUin_sr = arcpy.Describe(MUin).spatialReference
        XYRin = MUin_sr.XYResolution
        XYTin = MUin_sr.XYTolerance

        fD_sr = arcpy.Describe(RTSD).spatialReference
        XYR = fD_sr.XYResolution
        XYT = fD_sr.XYTolerance
        if XYR != 0.0001:
            arcpy.AddWarning("Your RTSD was not created with current "
                              "xy-resolution standard of 0.0001 meters!")
            arcpy.AddWarning(
                "Make sure you have the most current SSURGO_QA toolbox\n."
            )
            raise
        if XYT < 0.2:
            arcpy.AddWarning("Your RTSD was not created with current "
                              "xy-tolerance standard of 0.2 meters!")
            arcpy.AddWarning(
                "Make sure you have the most current SSURGO_QA toolbox\n."
            )
            raise
        if fD_sr.name != MUin_sr.name:
            arcpy.AddWarning("Input Feature Class and output Feature Dataset "
                             "have different projections")

        arcpy.env.workspace = gdb
        sfds = arcpy.ListDatasets(SFDS_n, feature_type='Feature')
        if not sfds:
            arcpy.management.CreateFeatureDataset(gdb, SFDS_n, fD_sr)

        if arcpy.ListFeatureClasses(cutV):
            arcpy.management.Delete(cutV)
        if arcpy.ListFeatureClasses(bNodes):
            arcpy.management.Delete(bNodes)

        arcpy.CreateFeatureclass_management(
            SFDS, cutV, "POINT", '', '', '', fD_sr
        )
        cutV = os.path.join(SFDS, cutV)
        arcpy.management.AddField(cutV, 'angle', 'FLOAT')
        arcpy.management.AddField(cutV, 'type', 'TEXT', field_length=10)

        dec = int(math.log10(XYR) // - 1)

        textStyle = xlwt.easyxf(num_format_str='Text')
        intStyle = xlwt.easyxf(num_format_str='0')
        perStyle = xlwt.easyxf(num_format_str='0.0%')

        hdr = [
            'areasym', 'prePoly', 'postPoly', 'preVertex', 
            'postVertex', 'proVertex'
        ]

        wb = xlwt.Workbook()
        ws = wb.add_sheet('Diet Summary')
        for cell, hdr in enumerate(hdr):
            ws.write(0, cell, hdr, textStyle)
            
        if insert:
            mud = arcpy.Describe(MU)
            if mud.editorTrackingEnabled and mud.istimeInUTC:
                MUout = os.path.join(RTSD, 'MUPOLYGON')
                createTimeField = mud.createdAtFieldName
            else:
                createTimeField = [f.name for f in mud.Fields 
                            if ('creat' in f.name.lower()) 
                            and ('date' in f.name.lower())
                            and (f.type == 'Date')]
                if len(createTimeField) > 1:
                    t = str(int(time.time()))
                    MUout = MUbase + t
                    insert = False
                    arcpy.AddWarning(
                        "Tracking was not enabled and more than one potential "
                        "creation date field discovered and the output can't "
                        "be inserted directly into RTSD MUPOLYGON"
                    )
                    arcpy.AddWarning(
                        'The output feature will be saved as' + MUout
                    )
                elif len(createTimeField) == 0:
                    t = str(int(time.time()))
                    MUout = MUbase + t
                    insert = False
                    arcpy.AddWarning(
                        "Tracking was not enabled and a potential creation "
                        "date field was not discovered and the output can't "
                        "be inserted directly into RTSD MUPOLYGON"
                    )
                    arcpy.AddWarning(
                        'The output feature will be saved as' + MUout
                    )
                else:
                    MUout = os.path.join(RTSD, 'MUPOLYGON')
                    createTimeField = createTimeField[0]
                    arcpy.management.EnableEditorTracking(
                        MU, None, createTimeField
                    )
                    arcpy.AddWarning(
                        "Editor tracking has bee been enabled with the "
                        f"{createTimeField} field activated")
    except:
        arcpy.AddError("Failed in General Setup")
        arcpy.AddError("Unexpected error on line: " + 
                    str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        sys.exit(1)

        # %%% Boundary Nodes
    try:
        arcpy.SetProgressor('default', 'Creating Boundary Nodes')
        arcpy.env.XYResolution = XYR
        arcpy.env.XYTolerance = XYT
        T = 10 * XYR
        if not BT:
            BT = T * 2**.5

        if not insert:
            oe = arcpy.ListFeatureClasses(MUout)
            if oe:
                arcpy.AddWarning(
                    MUout + " already exists, note this tool will add "
                    "polygons to it"
                )
            else:
                arcpy.management.CreateFeatureclass(
                    SFDS, MUout, "POLYGON", '', '', '', fD_sr
                )
                arcpy.management.AddField(
                    MUout, 'AREASYMBOL', 'TEXT', field_length=20
                )
                arcpy.management.AddField(
                    MUout, 'MUSYM', 'TEXT', field_length=6
                )
        q = "AREASYMBOL IN ('"+"','".join(areas)+"')"
        q2 = "AREASYMBOL NOT IN ('"+"','".join(areas)+"')"
        # Suveys of interest
        arcpy.MakeFeatureLayer_management(SAR, SAR_L, q)
        # All surveys except of interest
        arcpy.MakeFeatureLayer_management(SAR, SAR_L2, q2)
        arcpy.SelectLayerByLocation_management(
            SAR_L2, 'BOUNDARY_TOUCHES', SAR_L, selection_type='NEW_SELECTION'
        )
        with arcpy.da.SearchCursor(SAR_L2, 'AREASYMBOL') as sCur:
            rNeigh = {a for a, in sCur}

        # Neighboirng survey areas
        q3 = "AREASYMBOL IN ('"+"','".join(rNeigh)+"')"  
        arcpy.MakeFeatureLayer_management(MU, MUR_L, q3)
        # surveys of interest and neigh
        arcpy.env.workspace = SFDS

        if int(arcpy.management.GetCount(MUR_L).getOutput(0)):
            # Get outsie outlines of the surveys of interest
            arcpy.management.PolygonToLine(SAR_L, SA1_)
            arcpy.management.MakeFeatureLayer(SA1_, SA1_L, "LEFT_FID = -1")
            # Get all oulines of neighbors and surveys of interest
            q4 = "AREASYMBOL IN ('"+"','".join(rNeigh | set(areas))+"')"
            arcpy.management.MakeFeatureLayer(SAR, SAR_L4, q4)
            arcpy.management.PolygonToLine(SAR_L4, SARline, "IGNORE_NEIGHBORS")
            
            # Boundary nodes around neighbors
            BNodes(SA1_L, MUR_L, kNodes, dec, fD_sr)
            # Boundary Nodes along input
            BNodes2(MUin, nNodes, areas, dec, pCores, fD_sr)
            # Needed to snap nodes between selected surveys
            arcpy.analysis.PairwiseIntegrate(nNodes, BT)
            arcpy.edit.Snap(nNodes, [[kNodes, 'VERTEX', BT]])
            arcpy.edit.Snap(nNodes, [[SA1_, 'VERTEX', BT]])
            arcpy.edit.Snap(nNodes, [[SA1_, 'EDGE', BT]])
            pointMerge = [kNodes, nNodes, SARstart]
        else:
            arcpy.management.PolygonToLine(SAR_L, SARline, "IGNORE_NEIGHBORS")
            BNodes2(MUin, nNodes, areas, dec, pCores, fD_sr)
            pointMerge = [nNodes, SARstart]

        # arcpy.PolygonToLine_management(SAR_L, SARline, 'IGNORE_NEIGHBORS')
        arcpy.management.FeatureVerticesToPoints(SARline, SARstart, 'START')
        arcpy.Merge_management(pointMerge, nodes)

        arcpy.analysis.PairwiseDissolve(
            nodes, bNodes, None, None, "SINGLE_PART"
        )

        arcpy.management.SplitLineAtPoint(
            SARline, bNodes, SARsplit_m, BT * 2**0.5
        )
        arcpy.management.MultipartToSinglepart(SARsplit_m, SARsplit)
        arcpy.management.Delete(MUR_L)

        arcpy.AddMessage("Processing {} surveys.".format(nSurvs))

    except:
        arcpy.AddError("Failed while creating Boundary Nodes")
        arcpy.AddError("Unexpected error on line: " + 
                    str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))
        sys.exit(1)

    # %%% By survey area
    for rowID, areaSym in enumerate(areas):
        status = rowID*3
        rowID += 2
        arcpy.AddMessage('______________________________________')
        msg = "Survey {} of {}: geoprocessing".format(status//3+1, nSurvs)
        arcpy.SetProgressor('step', msg)
        arcpy.SetProgressorPosition(int(f*status))
        arcpy.AddMessage(
            '{}: Survey {} of {}'.format(areaSym, status//3+1, nSurvs)
        )

        arcpy.management.Delete('in_memory/')
        arcpy.MakeFeatureLayer_management(MUin, survey, 
                                        areaField+" = '{}'".format(areaSym))
        ws.write(rowID, 0, areaSym, textStyle)
        ws.write(rowID, 1, int(arcpy.management.GetCount(survey)[0]), intStyle)
        # collapse slivers and self-intersections per OGC
        # arcpy.Integrate_management(survey,T)
        # %%%% Geoprocessing
        try:
            q = "AREASYMBOL = '" + areaSym + "'"
            arcpy.management.PolygonToLine(survey, MUpoly)
            arcpy.management.MakeFeatureLayer(
                MUpoly, MUpoly_L, "RIGHT_FID = -1"
            )
            if arcpy.management.GetCount(MUpoly_L).getOutput(0):
                uCur = arcpy.da.UpdateCursor(
                    MUpoly_L, ['RIGHT_FID', 'LEFT_FID']
                )
                for RF, LF in uCur:
                    uCur.updateRow([LF, -1])
                del uCur

            arcpy.management.MakeFeatureLayer(MUpoly, MUpoly_L, "LEFT_FID = -1")

            arcpy.management.MakeFeatureLayer(SARsplit, SARline_L, q)
            arcpy.management.MakeFeatureLayer(bNodes, bound_L)
            arcpy.management.SelectLayerByLocation(
                bound_L, "WITHIN_A_DISTANCE", SARline_L, T
            )
            arcpy.edit.Snap(MUpoly_L, [[bound_L, 'VERTEX', BT]])
            # arcpy.Snap_edit(MUpoly_L, [[bound_L, 'EDGE', BT]])
            arcpy.management.SplitLineAtPoint(MUpoly_L, bound_L, MUsplit, BT)

            arcpy.management.FeatureVerticesToPoints(MUsplit, mid, "MID")
            arcpy.analysis.SpatialJoin(
                SARline_L, mid , MUinter, "JOIN_ONE_TO_ONE", "KEEP_ALL", '', 
                "CLOSEST", BT
            )

            arcpy.management.MakeFeatureLayer(
                MUpoly, MUpoly_L, "LEFT_FID <> -1 AND LEFT_FID<>RIGHT_FID"
            )

            mapping=('LEFT_FID "LEFT_FID" true true false 4 Long 0 0, First, '
                     '#, MUpolyline_layer, LEFT_FID, -1, -1, '
                     'MUinter, LEFT_FID, -1, -1;'
                     'RIGHT_FID "RIGHT_FID" true true false 4 Long 0 0, First, '
                     '#,MUpolyline_layer, RIGHT_FID,-1, -1,MUinter, RIGHT_FID, '
                     '-1, -1')
            arcpy.management.Merge([MUpoly_L, MUinter], MUpoly_, mapping)

            arcpy.management.FeatureVerticesToPoints(MUpoly_, starts, "START")
            arcpy.management.FeatureVerticesToPoints(MUpoly_, ends, "END")
            arcpy.management.AddField(ends, 'tail', "SHORT")
            arcpy.management.AddField(starts, 'tail', "SHORT")
            arcpy.management.CalculateField(ends, "tail", "1")
            arcpy.management.Merge(ends+";"+starts, TheEnd)
            arcpy.edit.Snap(TheEnd, [[bound_L, 'VERTEX', BT]])

            arcpy.management.Delete(bound_L)
            arcpy.management.Delete(SARline_L)

        except:
            arcpy.AddError("Failed while Geoprocessing inputs")
            arcpy.AddError("Unexpected error on line: " + 
                    str(sys.exc_info()[-1].tb_lineno))
            arcpy.AddError("\n" + str(sys.exc_info()[0]))
            arcpy.AddError("\n" + str(sys.exc_info()[1]))
            sys.exit(1)

        # %%%%Relational Data Structures

        # Arcs collated by MUPOLYGON Ojbject ID
        try:
            sCur = arcpy.da.SearchCursor(MUpoly_, 'OID@')
            oid = {ID for ID, in sCur}
            if not oid:
                arcpy.AddWarning(f'Survey {areaSym} has no features! Skipping!')
                failed.add(areaSym)
                continue
            n = max(oid)+1
            # Row 0 of inter, v3,v0, & arcs are dummy rows 
            # as there are no FID=0.
            # Computationally leaner than FID-1
            # number of intersections (Nodes)
            N = int(arcpy.GetCount_management(TheEnd).getOutput(0))//2+1
            # indexed by MUpoly_: Node fid, 
            # v3 position (realtive intersection ID),
            # Right then Left FID, head then tail
            arcs = np.zeros((n, 2), dtype=([('Ni', '<i4'), ('v3i', '<i4'),
                                        ('RLi', '<i4')]))
            polys = {}
            # Tally of the number of intersecting arcs at a Node, 
            # used in tweezer
            inter = np.zeros((N), dtype=np.int8)
            # Node coordinates, used in tweezer
            v0 = np.zeros((N, 1, 2), dtype=np.float64)

            #### Populating the arcs array, the key relational table
            # TARGET_FID: Node ID, ORIG_FID: MUpolyline fid (arc id)
            Round = np.round
            Ndex = {}
            Nid = 1
            sCur = arcpy.da.SearchCursor(
                TheEnd, ['SHAPE@XY', 'ORIG_FID',
                'RIGHT_FID', 'LEFT_FID', 'tail']
            )
            try:
                for xy, Ai, Ri, Li, t in sCur:
                    strxy = str(xy)
                    if strxy in Ndex:
                        Ni = Ndex[strxy]
                    else:
                        Nid += 1
                        Ndex[strxy] = Nid
                        Ni = Nid
                        v0[Ni] = Round(xy, dec)
        
                    i = inter[Ni]    # number of intersections
                    # v3 index, constrained 0-2. If greater than 2, cap at 2
                    I = (abs(i) >= 2)*2 or abs(i)
                    if not t:
                        # add boolean True or demerit 1
                        inter[Ni] += i >= 0 or -1
                        arcs[Ai, 0] = (Ni, I, Ri)
                        if Ri in polys:
                            polys[Ri][0].append((Ai, 1))
                        else:
                            polys[Ri] = [[(Ai, 1)], '']
                    elif Li+1:
                        inter[Ni] += i >= 0 or -1
                        arcs[Ai, 1] = (Ni, I, Li)
                        if Li in polys:
                            polys[Li][0].append((Ai, -1))
                        else:
                            polys[Li] = [[(Ai, -1)], '']
                    else: # Node on border
                        arcs[Ai, 1] = (Ni, I, Li)
                        inter[Ni] = abs(inter[Ni])*-1
            except:
                if not Li:
                    arcpy.AddError(
                        "It is likely the input soil polygon feature is "
                        "incongruent with the transactional SAPOLYGON feature"
                    )
                    arcpy.AddError(
                        "Either amend the input soil polygon feature or update "
                        "the transactaional SAPOLYGON feature."
                    )
                    arcpy.MakeFeatureLayer_management(
                        MUinter, MUinter_L, "'LEFT_FID' IS NULL"
                    )
                    arcpy.CopyFeatures_management(MUinter_L, SAmis)
                    arcpy.AddError(
                        f"See feature {SAmis} to see where they're incongruent"
                    )
                    sys.exit(1)
            del sCur, Ndex
            N = Nid+1
            inter = inter[:N]
            v0 = v0[:N, :, :]
            sCur = arcpy.da.SearchCursor(survey, ['OID@', muField, 'SHAPE@'])
            preV = 0
            for FID, mu, shp in sCur:
                if FID in polys:
                    polys[FID][1] = mu
                else:
                    weakEggs['Cluster Tolerance'].append(str(FID))
                try: # Catch null geometries
                    preV += shp.pointCount
                except:
                    arcpy.AddMessage("Null geometries in input removed")
                    weakEggs['Cluster Tolerance'].append(str(FID))
                    polys.pop(FID)
        except:
            arcpy.AddError("Failed while setting up Relational Tabels")
            arcpy.AddError("Unexpected error on line: " + 
                        str(sys.exc_info()[-1].tb_lineno))
            arcpy.AddError("\n" + str(sys.exc_info()[0]))
            arcpy.AddError("\n" + str(sys.exc_info()[1]))
            raise
        # %%%% Msg
        msg = "Survey {} of {}: Tweezer & Diet".format(status//3+1,nSurvs)
        arcpy.SetProgressor('step',msg)
        arcpy.SetProgressorPosition(int(f*status+f))
        # shapes is a dictionary, polyline FID: polyline geometry (arc)
        shapes, weakEggs = tweezer(arcs, inter, v0, MUpoly_, N, cutV, weakEggs,
                                min_angle, dec, polys)
        # P = arcpy.Point
        # allLines = [arcpy.Polyline(arcpy.Array([P(*p) for p in line])) 
        # for line in shapes.values()]
        # arcpy.management.CopyFeatures(allLines, 'allLines')
        msg = f"Survey {status//3+1} of {nSurvs}: Reassmbling polygons"
        arcpy.SetProgressor('step', msg)
        arcpy.SetProgressorPosition(int(f * (status+2)))
    # %%%% Call Tweezer & Reassemble
        if insert:
            try:
                edit = arcpy.da.Editor(os.path.dirname(RTSD))
                edit.startEditing(True, True)
                edit.startOperation()
                iCur = arcpy.da.InsertCursor(
                    MUout, [areaField, muField, 'SHAPE@']
                )
                postV, count, weakEggs, badEggs = Reassemble(
                    iCur, arcs, polys, shapes, weakEggs, badEggs, pCores, 
                    areaSym, SFDS, edit
                )
                del iCur
                edit.stopOperation()
                edit.stopEditing(True)
            except:
                arcpy.AddError("Failed during Reassembly")
                arcpy.SetProgressorLabel("Undoing changes")
                edit.stopOperation()
                edit.stopEditing(False)
                q = "AREASYMBOL IN ('"+"','".join(areas)+"')"
                q += f" AND {createTimeField} >= timestamp '{start}'"
                arcpy.MakeFeatureLayer_management(MUout, MUR_L, q)
                arcpy.DeleteFeatures_management(MUR_L)
                arcpy.AddError("Unexpected error on line: " +
                        str(sys.exc_info()[-1].tb_lineno))
                arcpy.AddError("\n" + str(sys.exc_info()[0]))
                arcpy.AddError("\n" + str(sys.exc_info()[1]))
                raise

        else:
            iCur = arcpy.da.InsertCursor(MUout, [areaField, muField, 'SHAPE@'])
            postV, count, weakEggs, badEggs = Reassemble(
                iCur, arcs, polys, shapes, weakEggs, badEggs, pCores, 
                areaSym, SFDS, edit
            )
            del iCur

        # %%%% Msg
        arcpy.SetProgressor('step', msg)
        arcpy.SetProgressorPosition(int(f*(status+3)))
        arcpy.AddMessage("Survey completed")

        ws.write(rowID, 3, preV, intStyle)
        ws.write(rowID, 4, postV, intStyle)
        ws.write(rowID, 5, (preV-postV)/preV, perStyle)
        ws.write(rowID, 2, count, intStyle)

    # %%% Wrap-up
    try:
        # %%%% Excel
        arcpy.AddMessage('______________________________________')
        rowID += 1
        ws.write(1, 0, 'Summary', textStyle)
        ws.write(1, 1, xlwt.Formula("SUM(B3:B{})".format(rowID)), intStyle)
        ws.write(1, 2, xlwt.Formula("SUM(C3:C{})".format(rowID)), intStyle)
        ws.write(1, 3, xlwt.Formula("SUM(D3:D{})".format(rowID)), intStyle)
        ws.write(1, 4, xlwt.Formula("SUM(E3:E{})".format(rowID)), intStyle)
        ws.write(1, 5, xlwt.Formula("(D2-E2)/D2)"), perStyle)
        # %%%% Weak Eggs
        arcpy.SetProgressor('default', 'Summarizing results')
        if (weakEggs['Tweezer'] or weakEggs['Reassembly'] 
            or weakEggs['Cluster Tolerance']):
            weakE_ = weakE
            if arcpy.ListFeatureClasses(weakE_):
                arcpy.Delete_management(weakE_)
            arcpy.management.CreateFeatureclass(
                SFDS, weakE_, "POLYGON", '', '', '', fD_sr
            )
            weakE_ = os.path.join(SFDS, weakE_)
            arcpy.AddField_management(
                weakE_, 'AREASYMBOL', 'TEXT', field_length=10
            )
            arcpy.AddField_management(
                weakE_, 'function', 'TEXT', field_length=25)
            iCur = arcpy.da.InsertCursor(
                weakE_, ['SHAPE@', 'AREASYMBOL', 'function']
            )
            oid = arcpy.Describe(MUin).OIDFieldName
            if weakEggs['Tweezer']:
                q = oid + ' IN ({})'.format(','.join(weakEggs['Tweezer']))
                sCur = arcpy.da.SearchCursor(MUin, ['SHAPE@', 'AREASYMBOL'], q)
                for egg in sCur:
                    iCur.insertRow(list(egg)+['Tweezer'])
            if weakEggs['Reassembly']:
                q = oid + ' IN ({})'.format(','.join(weakEggs['Reassembly']))
                sCur = arcpy.da.SearchCursor(MUin, ['SHAPE@', 'AREASYMBOL'], q)
                for egg in sCur:
                    iCur.insertRow(list(egg)+['Reassembly'])
            if weakEggs['Cluster Tolerance']:
                q = oid + f" IN ({','.join(weakEggs['Cluster Tolerance'])})"
                sCur = arcpy.da.SearchCursor(MUin, ['SHAPE@', 'AREASYMBOL'], q)
                for egg in sCur:
                    iCur.insertRow(list(egg)+['Cluster Tolerance'])
            arcpy.AddWarning(
                "Polygon(s) collapsed, see feature class: " + weakE_
            )
            del iCur, sCur
        else:
            arcpy.AddMessage("No collapsed polygons recorded")
        # %%%% Bad Eggs
        if badEggs['Exception'] or badEggs['Reassembly']:
            badE_ = badE
            if arcpy.ListFeatureClasses(badE_):
                arcpy.Delete_management(badE_)
            arcpy.management.CreateFeatureclass(
                SFDS, badE_, "POLYGON", '', '', '', fD_sr
            )
            badE_ = os.path.join(SFDS, badE_)
            arcpy.management.AddField(
                badE_, 'AREASYMBOL', 'TEXT', field_length=10
            )
            arcpy.management.AddField(
                badE_, 'function', 'TEXT', field_length=25
            )
            iCur = arcpy.da.InsertCursor(
                badE_, ['SHAPE@', 'AREASYMBOL', 'function']
            )
            oid = arcpy.Describe(MUin).OIDFieldName
            if badEggs['Exception']:
                q = oid+' IN ({})'.format(','.join(badEggs['Exception']))
                sCur = arcpy.da.SearchCursor(MUin, ['SHAPE@', 'AREASYMBOL'], q)
                for egg in sCur:
                    iCur.insertRow(list(egg)+['Exception'])
            if badEggs['Reassembly']:
                q = oid+' IN ({})'.format(','.join(badEggs['Reassembly']))
                sCur = arcpy.da.SearchCursor(MUin, ['SHAPE@', 'AREASYMBOL'], q)
                for egg in sCur:
                    iCur.insertRow(list(egg)+['Reassembly'])
            arcpy.AddWarning(
                "Polygon(s) couldn't be reassembled: see feature class: " 
                + badE_
            )
            del iCur, sCur
        else:
            arcpy.AddMessage("All polygons were successfully reassembled")
        # %%%% Insert Survey    
        if insert:
            arcpy.SetProgressorLabel("Deleting former polygons")
            areas = set(areas) - failed
            q = "AREASYMBOL IN ('"+"','".join(areas)+"')"
            q += (f" AND ({createTimeField} <= timestamp '{start}' "
                  f"OR {createTimeField} IS NULL)")
            arcpy.MakeFeatureLayer_management(MUout, MUR_L, q)
            arcpy.DeleteFeatures_management(MUR_L)
        if not retain:
            arcpy.Delete_management(MUinter)
            arcpy.Delete_management(bNodes)
            arcpy.Delete_management(SARsplit)
        # %%%% Clean up and save
        arcpy.Delete_management('in_memory/')
        try:
            wb.save(excel)
            os.startfile(excel)
        except:
            arcpy.AddWarning(
                "Seems an excel table with that name is open. \nEither close "
                "it or use another name."
            )
            arcpy.AddWarning(
                "Otherwise, the tool ran sucessfully, "
                "you do not need run it again."
            )
            pass
        arcpy.AddMessage(" ")
        arcpy.AddMessage("* * * * * * * * * * * * * * * * * *")
    except:
        wb.save(excel)
        arcpy.AddError("Failed in Main")
        arcpy.AddError("Unexpected error on line: " + 
                    str(sys.exc_info()[-1].tb_lineno))
        arcpy.AddError("\n" + str(sys.exc_info()[0]))
        arcpy.AddError("\n" + str(sys.exc_info()[1]))


if __name__ == '__main__':
    main()