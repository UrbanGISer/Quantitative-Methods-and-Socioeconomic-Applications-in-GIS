# Name: GeneralizedAcc.py
# Description: Generalized accessibility without external distance table

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
distanceDecayFunc = arcpy.GetParameterAsText(8)
distanceDecayCoeff = arcpy.GetParameterAsText(9)
outputTable = arcpy.GetParameterAsText(10)

try:

	# Delete intermediate data if they already exist
	if arcpy.Exists("MB_DistAll"):
		arcpy.Delete_management("MB_DistAll")

	if arcpy.Exists("MB_DocAvlg"):
		arcpy.Delete_management("MB_DocAvlg")

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

	# Calculate distance matrix
	if distanceThreshold != "":
		arcpy.PointDistance_analysis(supplyFL, demandFL, "MB_DistAll", distanceThreshold)
	else:
		arcpy.PointDistance_analysis(supplyFL, demandFL, "MB_DistAll")

	# Join distance matrix with demand layer
	if demandFieldTract != "":
		arcpy.JoinField_management("MB_DistAll", "NEAR_FID", demandFL, demandFieldId, [demandFieldTract, demandFieldPop])
	else:
		arcpy.JoinField_management("MB_DistAll", "NEAR_FID", demandFL, demandFieldId, [demandFieldPop])

	# Add population potential field
	arcpy.AddField_management("MB_DistAll", "PPotent", "DOUBLE")

	# Calculate population potential field with distance decay
	if distanceDecayFunc == "Power":
		# Check if any distance is 0
		arcpy.MakeTableView_management("MB_DistAll", "MB_DistAll_View", '"DISTANCE" = 0')
		cnt = int(arcpy.GetCount_management("MB_DistAll_View").getOutput(0))
		if cnt != 0:
			arcpy.AddWarning("Warning: distance between {0} supply-demand pair(s) is 0!\nA weight of 0 is assigned to such pair!".format(cnt))
		# Add a field for distance-decay based weights, calculate this field with codeblock
		arcpy.AddField_management("MB_DistAll", "Weights", "DOUBLE")
		weightsExpression = "calculateWeights(!DISTANCE!)"
		codeblock = """def calculateWeights(distance):
			if distance == 0:
				return 0
			else:
				return distance ** ((-1) * """ + powerDecayCoeff + """)"""
		arcpy.CalculateField_management("MB_DistAll", "Weights", weightsExpression, "PYTHON_9.3", codeblock)
		# Apply weights to demand
		expression1 = "!" + demandFieldPop + "! * !Weights!"
		arcpy.CalculateField_management("MB_DistAll", "PPotent", expression1, "PYTHON_9.3")
	elif distanceDecayFunc == "Exponential":
		expression1 = "!" + demandFieldPop + "! * math.exp((-1) * !DISTANCE! * " + exponentialDecayCoeff + ")"
		arcpy.CalculateField_management("MB_DistAll", "PPotent", expression1, "PYTHON_9.3")
	else:
		expression1 = "!" + demandFieldPop + "! / (math.sqrt(2 * math.pi) * " + gaussianDecayCoeff + ") * math.exp((-0.5) * !DISTANCE! ** 2 / " + gaussianDecayCoeff + " ** 2)"
		arcpy.CalculateField_management("MB_DistAll", "PPotent", expression1, "PYTHON_9.3")

	# Summarize population potential for each supply location
	arcpy.Statistics_analysis("MB_DistAll", "MB_DocAvlg", [["PPotent", "SUM"]], "INPUT_FID")

	# Join total population potential for each supply location with supply layer
	arcpy.JoinField_management("MB_DocAvlg", "INPUT_FID", supplyFL, supplyFieldId, [supplyFieldDoc])

	# Join distance matrix with total population potential and supply
	arcpy.JoinField_management("MB_DistAll", "INPUT_FID", "MB_DocAvlg", "INPUT_FID", ["SUM_PPotent", supplyFieldDoc])

	# Add supply-to-demand ratio field
	arcpy.AddField_management("MB_DistAll", "R", "DOUBLE")

	# Calculate supply-to-demand ratio field with distance decay
	if distanceDecayFunc == "Power":
		# Use previously calculated weights in distance table to avoid divided-by-zero issue
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) * !Weights!"
		arcpy.CalculateField_management("MB_DistAll", "R", expression2, "PYTHON_9.3")
	elif distanceDecayFunc == "Exponential":
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) * math.exp((-1) * !DISTANCE! * " + exponentialDecayCoeff + ")"
		arcpy.CalculateField_management("MB_DistAll", "R", expression2, "PYTHON_9.3")
	else:
		expression2 = "(1000.0 * !" + supplyFieldDoc + "! / !SUM_PPotent!) / (math.sqrt(2 * math.pi) * " + gaussianDecayCoeff + ") * math.exp((-0.5) * !DISTANCE! ** 2 / " + gaussianDecayCoeff + " ** 2)"
		arcpy.CalculateField_management("MB_DistAll", "R", expression2, "PYTHON_9.3")

	# Summarize supply-to-demand ratio for each demand location
	if demandFieldTract != "":
		arcpy.Statistics_analysis("MB_DistAll", outputTable, [[demandFieldTract, "FIRST"], ["R", "SUM"]], "NEAR_FID")
	else:
		arcpy.Statistics_analysis("MB_DistAll", outputTable, [["R", "SUM"]], "NEAR_FID")

	# Cleanup intermediate data
	arcpy.Delete_management("MB_DistAll")
	arcpy.Delete_management("MB_DocAvlg")

except Exception as e:
	print e.message
