# Name: 2SFCA_Table.py
# Description: 2-Step Floating Cachment Area (2SFCA) with external distance table

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
matrixTable = arcpy.GetParameterAsText(7)
matrixSupplyFieldId = arcpy.GetParameterAsText(8)
matrixDemandFieldId = arcpy.GetParameterAsText(9)
matrixDistanceValue = arcpy.GetParameterAsText(10)
distanceThreshold = arcpy.GetParameterAsText(11)
outputTable = arcpy.GetParameterAsText(12)

try:

	# Delete intermediate data if they already exist
	if arcpy.Exists("MB_DistMatrix_Raw"):
		arcpy.Delete_management("MB_DistMatrix_Raw")

	if arcpy.Exists("MB_DocAvlMatrix_Raw"):
		arcpy.Delete_management("MB_DocAvlMatrix_Raw")

	if arcpy.Exists("MB_DistMatrix"):
		arcpy.Delete_management("MB_DistMatrix")

	if arcpy.Exists("MB_DocAvlMatrix"):
		arcpy.Delete_management("MB_DocAvlMatrix")

	if arcpy.Exists("MB_DistMatrix_Final"):
		arcpy.Delete_management("MB_DistMatrix_Final")

	# Copy distance matrix and select records with distance threshold
	if distanceThreshold != "":
		if ".mdb" in matrixTable:
			where_clause = '[' + matrixDistanceValue + '] <= ' + distanceThreshold
			arcpy.TableSelect_analysis(matrixTable, "MB_DistMatrix_Raw", where_clause)
		else:
			where_clause = '"' + matrixDistanceValue + '" <= ' + distanceThreshold
			arcpy.TableSelect_analysis(matrixTable, "MB_DistMatrix_Raw", where_clause)
	else:
		arcpy.TableSelect_analysis(matrixTable, "MB_DistMatrix_Raw")

	# Join distance matrix with demand layer
	if demandFieldTract != "":
		arcpy.JoinField_management("MB_DistMatrix_Raw", matrixDemandFieldId, demandFL, demandFieldId, [demandFieldTract, demandFieldPop])
	else:
		arcpy.JoinField_management("MB_DistMatrix_Raw", matrixDemandFieldId, demandFL, demandFieldId, [demandFieldPop])
	# Keep only matched records
	arcpy.TableSelect_analysis("MB_DistMatrix_Raw", "MB_DistMatrix", '"' + demandFieldPop + '" IS NOT NULL')

	# Summarize total demand for each supply location
	arcpy.Statistics_analysis("MB_DistMatrix", "MB_DocAvlMatrix_Raw", [[demandFieldPop, "SUM"]], matrixSupplyFieldId)

	# Join total demand for each supply location with supply layer
	arcpy.JoinField_management("MB_DocAvlMatrix_Raw", matrixSupplyFieldId, supplyFL, supplyFieldId, [supplyFieldDoc])
	# Keep only matched records
	arcpy.TableSelect_analysis("MB_DocAvlMatrix_Raw", "MB_DocAvlMatrix", '"' + supplyFieldDoc + '" IS NOT NULL')

	# Add supply-to-demand ratio field
	arcpy.AddField_management("MB_DocAvlMatrix", "docpopR", "DOUBLE")

	# Calculate supply-to-demand ratio field
	expression = "1000.0 * !" + supplyFieldDoc + "! / !SUM_" + demandFieldPop + "!"
	arcpy.CalculateField_management("MB_DocAvlMatrix", "docpopR", expression, "PYTHON_9.3")

	# Join distance matrix with supply-to-demand ratio
	arcpy.JoinField_management("MB_DistMatrix", matrixSupplyFieldId, "MB_DocAvlMatrix", matrixSupplyFieldId, ["docpopR"])
	# Keep only matched records
	arcpy.TableSelect_analysis("MB_DistMatrix", "MB_DistMatrix_Final", '"docpopR" IS NOT NULL')

	# Summarize supply-to-demand ratio for each demand location
	if demandFieldTract != "":
		arcpy.Statistics_analysis("MB_DistMatrix_Final", outputTable, [[demandFieldTract, "FIRST"], ["docpopR", "SUM"]], matrixDemandFieldId)
	else:
		arcpy.Statistics_analysis("MB_DistMatrix_Final", outputTable, [["docpopR", "SUM"]], matrixDemandFieldId)

	# Cleanup intermediate data
	arcpy.Delete_management("MB_DistMatrix_Raw")
	arcpy.Delete_management("MB_DocAvlMatrix_Raw")
	arcpy.Delete_management("MB_DistMatrix")
	arcpy.Delete_management("MB_DocAvlMatrix")
	arcpy.Delete_management("MB_DistMatrix_Final")

except Exception as e:
	print e.message
