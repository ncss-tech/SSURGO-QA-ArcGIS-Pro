# -*- coding: utf-8 -*-
"""
Created on Tue May 26 18:30:43 2020

@author: Alexander.Stum
"""
import arcpy, sys # , copy
import numpy as np

    
def BCore(A, MU, dec):
    #======= Variables  ==========
    MU_l        = "MU_layer" + A
    MU_         = "in_memory/MU_outline" + A # "in_memory/MU_outline" # "MU_outline"
    MU_o        = "MU_outer" + A
    # MU_d        = "in_memory/MU_d"
    
    # arcpy.env.parallelProcessingFactor = 2
    arcpy.AddMessage(f"AREASYMBOL = '{A}'")
    try:
        arcpy.MakeFeatureLayer_management(MU, MU_l, f"AREASYMBOL = '{A}'")
        arcpy.PolygonToLine_management(MU_l, MU_)
        arcpy.MakeFeatureLayer_management(MU_, MU_o, "LEFT_FID = -1")
        MU_d = arcpy.analysis.PairwiseDissolve(MU_o, arcpy.Geometry(), 
                                               "RIGHT_FID", None, "MULTI_PART")
        ends = {(round(p.X, dec), round(p.Y, dec))
                for G in MU_d # for each polyline geometry
                for P in G  # for each part (Array) of gemoetry
                for p in [P[0], P[-1]]} # for the for the last and first points
        return ends
    except:
        s1 =  sys.exc_info()[-1].tb_lineno
        s2 = sys.exc_info()[0]
        s3 = sys.exc_info()[1]
        return(f"BCore {A}: {s1}\n{s2}\n{s3}")
        raise


def OuterRing(arrays):
    extAreas = []
    for array in arrays:
        x,y = zip(*[(p.X, p.Y) for p in array])
        extAreas.append((max(x) - min(x))*(min(y) - max(y)))
    return extAreas.index(max(extAreas))



def ShapeUp(parcs, parcs2, ai, shapes, mu, FID):
    try:
        complete = []#arcpy.Array()
        #fid: arc ID; FID: polygon ID; 
        ###Localize function calls
    #    compRemove = complete.removeAll
        compAdd = complete.append
        Polygon = arcpy.Polygon
        Array = arcpy.Array
        where = np.where
        cat = np.concatenate
        P = arcpy.Point
    #    outerring = OuterRing
    
        picnic = ai.copy() #set(ai)            # subset of arc id's and Head/Tail orientation: to be consumed
        nonSimp = {}     #Nodes involved with non-simple intersections
        try:
            fid, o = picnic.pop(0)         # fid represents arc id; pj is the Head/Tail orientation
        except:
            return([None, [FID]])
    
        pi = 0          # pi is the address of the arc fid within parc
        N0c, N1 = parcs['Ni'][pi, ::o]     #Ring inception
        N0 = [N0c]    #list of initiated Nodes in play
        partial = {N0c:shapes[fid][::o]}
        parcs2['Ni'][0] = 0

        while picnic:
            if N1 not in N0:    #ring not closed
                pi = where(parcs2['Ni'] == N1)[0]
                if pi.size == 1:
                    fid,o = ai[pi[0]]
                    partial[N0c]=cat((partial[N0c],shapes[fid][-1 + o or 1::o]))
                elif pi.size > 1:  #Node associated more than one ring
                    nonSimp[N0c * -1] = N1
                    partial[N0c * -1] = partial.pop(N0c)
                    N0.append(N1)
                    N0c = N1
                    fid,o = ai[pi[0]]
                    partial[N0c] = shapes[fid][::o]
                else:
                    return([None, [FID * -1]])
    
                parcs2['Ni'][pi[0]] = 0                            
                N1 = parcs['Ni'][pi[0],::o * -1][0]
                picnic.remove((fid, o))
    
            elif N1 == N0c:  #completion of simple ring
                compAdd(partial.pop(N0c))
                N0.remove(N0c)
                fid, o = picnic.pop(0)
                pi = [ai.index((fid, o))]
                N0c, N1 = parcs['Ni'][pi[0], ::o]
                N0.append(N0c)
                parcs2['Ni'][pi[0]] = 0
                partial[N0c] = shapes[fid][::o]
                
            else : #non-simple ring
                N0.remove(N1)
                nonSimp[N0c * -1] = nonSimp.pop(N1 * -1)
                if nonSimp[N0c*-1] == N0c: #non-simple complete
                    compAdd(cat((partial.pop(N0c), partial.pop(N1 * -1))))
                    N0.remove(N0c)
                    nonSimp.pop(N0c * -1)
                else:
                    partial[N0c*-1] = cat((partial.pop(N0c), partial.pop(N1 * -1)))
                fid, o = picnic.pop(0)
                pi = [ai.index((fid, o))]
                N0c, N1 = parcs['Ni'][pi[0], ::o]
                N0.append(N0c)
                parcs2['Ni'][pi[0]] = 0
                partial[N0c] = shapes[fid][::o]
        
        if N1 == N0c and partial: #if the last arc popped was a single-arc ring
            compAdd(partial.pop(N0c))
            Sc = set()
        else:
            Sc = {N0c, N1}
        
        while nonSimp and partial:
            N0a,N1a = nonSimp.popitem()
            Sa = {N0a * -1, N1a}
            if Sa==Sc:  #complete
                compAdd(cat((partial.pop(N0a), partial.pop(N0c))))
            elif N1a in Sc:
                partial[N0a] = cat((partial[N0a], partial.pop(N0c)))
                N1a = N1
                Sa = {N0a * -1, N1a}
            elif N1 in Sa:
                partial[N0c] = cat((partial.pop(N0c), partial.pop(N0a)))
                N0a = N0c
                Sa = {N0a, N1a}
            
            nsX = []
            for N0b,N1b in nonSimp.items():
                Sb = {N0b * -1, N1b}
                if Sa==Sb:  #complete
                    compAdd(cat((partial.pop(N0a), partial.pop(N0b))))
                    nsX.append(N0b)
                    continue
                elif N1a in Sb:
                    partial[N0a] = cat((partial[N0a], partial.pop(N0b)))
                    N1a = nonSimp[N0b] 
                    nsX.append(N0b)
                    Sa = {abs(N0a), N1b}
                elif N1b in Sa:
                    partial[N0b] = cat((partial[N0b], partial.pop(N0a)))
                    nsX.append(N0b)
                    Sa = {N0b * -1, N1a}
                    N0a = N0b 
                
                if Sa==Sc:  #complete
                    compAdd(cat((partial.pop(N0a), partial.pop(N0c))))
                elif N1a in Sc:
                    partial[N0a] = cat((partial[N0a], partial.pop(N0c)))
                elif N1 in Sa:
                    partial[N0c * -1] = cat((partial.pop(N0c), partial.pop(N0a)))

            list(map(nonSimp.pop, nsX))
            
        
        if partial:
            return([None, [FID * -1]])
    
        if len(complete) > 1:
            # Find the part with greatest extent range, corresponds to outside ring
            extAreas = [(array.T[0].max() - array.T[0].min()) * # delta x
                        (array.T[1].max() - array.T[1].min()) # delta y
                        for array in complete]
            oi = extAreas.index(max(extAreas)) # index of outside ring
            # convert outside ring to an Array of Points
            final = Array()
            final.append([P(*p) for p in complete.pop(oi)])
            # Add the internal rings to the Array
            for npA in complete:
                final.append([P(*p) for p in npA])

            poly = Polygon(final)
            if poly.area:
                return ([mu, poly])
            else:
                return([None, [FID]])
    
        elif complete:
            poly = Polygon(Array([P(*p) for p in complete[0]]))
            if poly.area:
                return([mu, poly])
            else:
                return([None, [FID]])
        
        else:
            return([None, [FID * -1]])
    except:
        s1 =  sys.exc_info()[-1].tb_lineno
        s2 = sys.exc_info()[0]
        s3 = sys.exc_info()[1]
        return([None, [FID * -1, list(partial.keys()), [N0c, N1], f"{s1}\n{s2}\n{s3}"]])