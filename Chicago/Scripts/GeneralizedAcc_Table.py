# Name: GeneralizedAcc_Table.py
# Description: Generalized accessibility with external distance table

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
distanceDecayFunc = arcpy.GetParameterAsText(12)
distanceDecayCoeff = arcpy.GetParameterAsText(13)
outputTable = arcpy.GetParameterAsText(14)

try:

	# Delete intermediate data if they already exist
	if arcpy.Exists("MB_DistMatrix_Raw"):
		arcpy.Delete_management("MB_DistMatrix_Raw")

	if arcpy.Exists("MB_DocAvlgMatrix_Raw"):
		arcpy.Delete_management("MB_DocAvlgMatrix_Raw")

	if arcpy.Exists("MB_DistMatrix"):
		arcpy.Delete_management("MB_DistMatrix")

	if arcpy.Exists("MB_DocAvlgMatrix"):
		arcpy.Delete_management("MB_DocAvlgMatrix")

	if arcpy.Exists("MB_DistMatrix_Final"):
		arcpy.Delete_management("MB_DistMatrix_Final")

	# Assign default distance decay coefficient
	powerDecayCoeff = "1.0"
	exponentialDecayCoeff = "0.0001"
	gaussianDecayCoeff = "10000"
	# Check if user specified distance decay coefficient
	if distanceDecayCoeff != "":
		if distanceDecayFunc == "Power":
			powerDecayCoeff = distanceDecayCoeff
		elif distanceDecayFunc == "Exponential":
			exponentialDecayCoeff = distanceDecayCoeff
		else:
			gaussianDecayCoeff = distanceDecayCoeff

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

	# Add population potential field
	arcpy.AddField_management("MB_DistMatrix", "PPotent", "DOUBLE")

	# Calculate population potential field with distance decay
	if distanceDecayFunc == "Power":
		# Check if any distance is 0
		arcpy.MakeTableView_management("MB_DistMatrix", "MB_DistMatrix_View", '"' + matrixDistanceValue + '" = 0')
		cnt = int(arcpy.GetCount_management("MB_DistMatrix_View").getOutput(0))
		if cnt != 0:
			arcpy.AddWarning("Warning: distance between {0} supply-demand pair(s) is 0!\nA weight of 0 is assigned to such pair!".format(cnt))
		# Add a field for distance-decay based weights, calculate this field with codeblock
		arcpy.AddField_management("MB_DistMatrix", "Weights", "DOUBLE")
		weightsExpression = "calculateWeights(!" + matrixDistanceValue + "!)"
		codeblock = """def calculateWeights(distance):
			if distance == 0:
				return 0
			else:
				return distance ** ((-1) * """ + powerDecayCoeff + """)"""
		arcpy.CalculateField_management("MB_DistMatrix", "Weights", weightsExpression, "PYTHON_9.3", codeblock)
		# Apply weights to demand
		expression1 = "!" + demandFieldPop + "! * !Weights!"
		arcpy.CalculateField_management("MB_DistMatrix", "PPotent", expression1, "PYTHON_9.3")
	elif distanceDecayFunc == "Exponential":
		expression1 = "!" + demandFieldPop + "! * math.exp((-1) * !" + matrixDistanceValue + "! * " + exponentialDecayCoeff + ")"
		arcpy.CalculateField_management("MB_DistMatrix", "PPotent", expression1, "PYTHON_9.3")
	else:
		expression1 = "!" + demandFieldPop + "! / (math.sqrt(2 * math.pi) * " + gaussianDecayCoeff + ") * math.exp((-0.5) * !" + matrixDistanceValue + "! ** 2 / " + gaussianDecayCoeff + " ** 2)"
		arcpy.CalculateField_management("MB_DistMatrix", "PPotent", expression1, "PYTHON_9.3")

	# Summarize population potential for each supply location
	arcpy.Statistics_analysis("MB_DistMatrix", "MB_DocAvlgMatrix_Raw", [["PPotent", "SUM"]], matrixSupplyFieldId)

	# Join total population potential for each supply location with supply layer
	arcpy.JoinField_management("MB_DocAvlgMatrix_Raw", matrixSupplyFieldId, supplyFL, supplyFieldId, [supplyFieldDoc])
	# Keep only matched records
	arcpy.TableSelect_analysis("MB_DocAvlgMatrix_Raw", "MB_DocAvlgMatrix", '"' + supplyFieldDoc + '" IS NOT NULL')

	# Join distance matrix with total population potential and supply
	arcpy.JoinField_management("MB_DistMatrix", matrixSupplyFieldId, "MB_DocAvlgMatrix", matrixSupplyFieldId, ["SUM_PPotent", supplyFieldDoc])
	# Keep only matched records
	arcpy.TableSelect_analysis("MB_DistMatrix", "MB_DistMatrix_Final", '"SUM_PPotent" IS NOT NULL')

	# Add supply-to-demand ratio field
	arcpy.AddField_management("MB_DistMatrix_Final", "R", "DOUBLE")

	# Calculate supply-to-demand ratio field with distance decay
	if distanceDecayFunc == "Power":
		# Use previously calculated weights in distance table to avoid divided-by-zero issue
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) * !Weights!"
		arcpy.CalculateField_management("MB_DistMatrix_Final", "R", expression2, "PYTHON_9.3")
	elif distanceDecayFunc == "Exponential":
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) * math.exp((-1) * !" + matrixDistanceValue + "! * " + exponentialDecayCoeff + ")"
		arcpy.CalculateField_management("MB_DistMatrix_Final", "R", expression2, "PYTHON_9.3")
	else:
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) / (math.sqrt(2 * math.pi) * " + gaussianDecayCoeff + ") * math.exp((-0.5) * !" + matrixDistanceValue + "! ** 2 / " + gaussianDecayCoeff + " ** 2)"
		arcpy.CalculateField_management("MB_DistMatrix_Final", "R", expression2, "PYTHON_9.3")

	# Summarize supply-to-demand ratio for each demand location
	if demandFieldTract != "":
		arcpy.Statistics_analysis("MB_DistMatrix_Final", outputTable, [[demandFieldTract, "FIRST"], ["R", "SUM"]], matrixDemandFieldId)
	else:
		arcpy.Statistics_analysis("MB_DistMatrix_Final", outputTable, [["R", "SUM"]], matrixDemandFieldId)

	# Cleanup intermediate data
	arcpy.Delete_management("MB_DistMatrix_Raw")
	arcpy.Delete_management("MB_DocAvlgMatrix_Raw")
	arcpy.Delete_management("MB_DistMatrix")
	arcpy.Delete_management("MB_DocAvlgMatrix")
	arcpy.Delete_management("MB_DistMatrix_Final")
except Exception as e:
	print e.message
