# Name: 2SFCA.py
# Description: 2-Step Floating Cachment Area (2SFCA) without external distance table

# Import system modules
import arcpy

# Get input parameters
supplyFL = arcpy.GetParameterAsText(0)
supplyFieldId = arcpy.GetParameterAsText(1)
supplyFieldDoc = arcpy.GetParameterAsText(2)
demandFL = arcpy.GetParameterAsText(3)
demandFieldId = arcpy.GetParameterAsText(4)
demandFieldTract = arcpy.GetParameterAsText(5)
demandFieldPop = arcpy.GetParameterAsText(6)
distanceThreshold = arcpy.GetParameterAsText(7)
outputTable = arcpy.GetParameterAsText(8)

try:

	# Delete intermediate data if they already exist
	if arcpy.Exists("MB_Dist20mi"):
		arcpy.Delete_management("MB_Dist20mi")

	if arcpy.Exists("MB_DocAvl"):
		arcpy.Delete_management("MB_DocAvl")

	# Calculate distance matrix
	arcpy.PointDistance_analysis(supplyFL, demandFL, "MB_Dist20mi", distanceThreshold)

	# Join distance matrix with demand layer
	if demandFieldTract != "":
		arcpy.JoinField_management("MB_Dist20mi", "NEAR_FID", demandFL, demandFieldId, [demandFieldTract, demandFieldPop])
	else:
		arcpy.JoinField_management("MB_Dist20mi", "NEAR_FID", demandFL, demandFieldId, [demandFieldPop])

	# Summarize total demand for each supply location
	arcpy.Statistics_analysis("MB_Dist20mi", "MB_DocAvl", [[demandFieldPop, "SUM"]], "INPUT_FID")

	# Join total demand for each supply location with supply layer
	arcpy.JoinField_management("MB_DocAvl", "INPUT_FID", supplyFL, supplyFieldId, [supplyFieldDoc])

	# Add supply-to-demand ratio field
	arcpy.AddField_management("MB_DocAvl", "docpopR", "DOUBLE")

	# Calculate supply-to-demand ratio field
	expression = "1000.0 * !" + supplyFieldDoc + "! / !SUM_" + demandFieldPop + "!"
	arcpy.CalculateField_management("MB_DocAvl", "docpopR", expression, "PYTHON_9.3")

	# Join distance matrix with supply-to-demand ratio
	arcpy.JoinField_management("MB_Dist20mi", "INPUT_FID", "MB_DocAvl", "INPUT_FID", ["docpopR"])

	# Summarize supply-to-demand ratio for each demand location
	if demandFieldTract != "":
		arcpy.Statistics_analysis("MB_Dist20mi", outputTable, [[demandFieldTract, "FIRST"], ["docpopR", "SUM"]], "NEAR_FID")
	else:
		arcpy.Statistics_analysis("MB_Dist20mi", outputTable, [["docpopR", "SUM"]], "NEAR_FID")

	# Cleanup intermediate data
	arcpy.Delete_management("MB_Dist20mi")
	arcpy.Delete_management("MB_DocAvl")

except Exception as e:
	print e.message
