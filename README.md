# SSURGO-QA
Official ArcGIS Pro version of the Quality Assurance tools used to certify SSURGO data  

## Current status of the ArcGIS Pro migration from ArcGIS 10.x

Toolset|Tool|ArcGIS Pro Compatible|
--------------------------------------------------|-------------------------------------------------------------------|---------------------------|
Setup|Download SSURGO by Areasymbol||
Setup|Download SSURGO by Region||
Setup|Generate Regional Transactional Geodatabase||
Setup|Import SSURGO Datasets into FGDB by Map||
Setup|Import SSURGO or STATSGO Datasets into FGDB||
Setup|Insert NATSYM and MUNAME Value||
Practice Design - Wascob Design|1. Define Area of Interest (WASCOB)|X|
Practice Design - Wascob Design|2. Create Stream Network (WASCOB)|X|
Practice Design - Wascob Design|3. Create Watershed(s) (WASCOB)|X|
Practice Design - Wascob Design|4. Watershed Attributes|X|
Practice Design - Wascob Design|5. Calculate Runoff Curve Number|X|
Practice Design - Wascob Design|6. Wascob Design Worksheet|X|
Practice Design - Wascob Design|7. Design Height & Intake Location|X|
Practice Design - Wascob Design|8. Tile Layout and Profile|X|
Practice Design - Wascob Design|9. Ridge Layout and Profile|X|
Practice Design - Wascob Design|Export Project Data for GPS|X|
Practice Design - Wascob Utilities|Add Points to Tile Profile|X|
Practice Design - Wascob Utilities|Calibrate DEM to Field Survey||
Terrain Analysis Tools|1. Define Area of Interest (Optional)|X|
Terrain Analysis Tools|2. Create Stream Network (Optional)|X|
Terrain Analysis Tools|Compound Topographic Index (CTI)|X|
Terrain Analysis Tools|Stream Power Index (SPI)|X|
Terrain Analysis Tools|Topographic Position Index (TPI)|X|
Watershed Tools - Delineation|1. Define Area of Interest|X|
Watershed Tools - Delineation|2. Create Stream Network|X|
Watershed Tools - Delineation|3. Create Watershed|X|
Watershed Tools - Delineation|4. Update Watershed Attributes|X|
Watershed Tools - Runoff Curve Number|1. Prepare Soils and Landuse|X|
Watershed Tools - Runoff Curve Number|2. Calculate Runoff Curve Number|X|
Watershed Tools - Storage|Calculate Stage Storage|X|
Watershed Tools - Storage|Create Pool at Desired Elevation|X|
Watershed Tools - Storage|Estimate Pool from Contours||
Watershed Tools - Utilities|Calculate Curve Number from NLCD|X|
Utilities|Clip/Merge Adjacent Datasets||
Utilities|Clip/Merge Adjacent DEMs||
Utilities|ElevationWebServiceClipUSERSELECTReprojectModel||
Utilities|Change Point Coordinates||
Utilities|Convert DEM Z-Units||

# 1. Setup
<ul> 
<li>Download SSURGO by Areasymbol - Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. User can a wildcard to query the database by Areasymbol or by age. </li>
<li>Download SSURGO by Region - Downloads SSURGO Soil Survey Areas that are owned by a specific region including an approximiate 2 soil survey area buffer. </li>
<li>Generate Regional Transactional Geodatabase - Used to create the Regional Transactional Spatial Database (RTSD) for SSURGO. </li>
<li>Generate SSO SSURGO Datasets - Create a SSURGO file geodatabase for a selected MLRA Soil Survey Office. </li>
<li>Import SSURGO Datasets in FGDB - This tooll will import SSURGO spatial and tabular datasets within a given location into a File Geodatabase and establish the necessary table and feature class relationships to interact with the dataset. </li>
<li>Insert NATSYM and MUNAME Value - This tool adds the National Mapunit Symbol (NATMUSYM) and the Mapunit Name (MUNAME) values to the corresponding MUKEY. An MUKEY field is required to execute. A network connection is required in order to submit a query to SDacess. </li>
<li>RTSD - Check SDJR Project Out - Designed to work with the RTSD to manage SDJR projects and export data for those projects to be sent to the MLRA SSO. </li>
</ul>

# 2. Quality Assurance

<ul>
<li> Check Attributes - Checks formatting of the selected soil attributes (normally AREASYMBOL and MUSYM). Also checks to make sure that the AREASYMBOL is present in Web Soil Survey.</li>
<li>Compare Spatial-NASIS Mapunits - Check MUSYM values in the input layer using a NASIS online report. Internet connection required for this tool. </li>
<li>Find Common Lines - Compares attributes between adjacent polygons and flags those that are the same. </li>
<li>Find Common Points - Find points where polygon with the same attribute value intersect. These are usually soil polygons that get 'pinched off'. This will also flag self-intersecting polygons.</li>
<li>Find Edge Matching Errors - Looks for locations along survey boundaries where a node-to-node match does not exist. It does NOT look at soil attribute matches. </li>
<li>Find Multipart Features - Simply reports the existence of multipart polygons. These must be exploded in an edit session if they are detected.</li>
<li>Find Slivers - Looks for slivers or gaps in a polygon layer based upon a minimum-allowed internal polygon angle. Often smaller angles are the result of snapping vertices that create slivers, zig zags or bowties. </li>
<li>Find Vertex Problems - Calculate area statistics by state or survey area from a GCS polygon featureclass and find problem vertices </li>
<li>Report Vertex Count - Simply reports the number of vertices found in the input featureclass. This tool is useful when the user wants to find out how many vertices were present 'before-and-after'. </li>
<li>Report Vertex Densisty - Calculate area statistics by state or survey area from a  polygon featureclass. Can be used to determine what surveys are potential candidates for thinning or may have vertices that are liable to contribute to snapping or other geometry problems. </li>
</ul>

# 3. Certification

<ul>
<li>Export to SSURGO Shapefile - Export geodatabase featureclasses to SSURGO shapefile format. These shapefiles are suitable for posting to the Staging Server. </li>
<li>Generate Special Feature File - Creates the feature description text file-table for SSURGO. </li>
<li>Zip SSURGO Export Folders - Zips all of the required SSURGO shapefiles and feature file for posting to the Staging Server. </li>
