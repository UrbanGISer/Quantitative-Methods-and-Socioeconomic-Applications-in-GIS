# Import system modules
import arcpy

# Get input parameters
customerFL = arcpy.GetParameterAsText(0)
customerIDField = arcpy.GetParameterAsText(1)
facilityFL = arcpy.GetParameterAsText(2)
facilityIDField = arcpy.GetParameterAsText(3)
facilitySizeField = arcpy.GetParameterAsText(4)
distanceTable = arcpy.GetParameterAsText(5)
distanceCustomerID = arcpy.GetParameterAsText(6)
distanceFacilityID = arcpy.GetParameterAsText(7)
distanceValue = arcpy.GetParameterAsText(8)
distanceDecayFunc = arcpy.GetParameterAsText(9)
distanceDecayCoeff = arcpy.GetParameterAsText(10)
scaleFactor = arcpy.GetParameterAsText(11)
outputProbIDs = arcpy.GetParameterAsText(12)
outputCustomerFC = arcpy.GetParameterAsText(13)

outputTradeArea = "FacilityID"

# Delete intermediate data if they already exist
if arcpy.Exists("Temp_Dist_Table"):
	arcpy.Delete_management("Temp_Dist_Table")

if arcpy.Exists("Temp_Sum_Potent"):
	arcpy.Delete_management("Temp_Sum_Potent")

if arcpy.Exists("Temp_Hosp_MaxPotent"):
	arcpy.Delete_management("Temp_Hosp_MaxPotent")

if arcpy.Exists(outputCustomerFC):
	arcpy.Delete_management(outputCustomerFC)

# Assign default distance decay coefficient
powerDecayCoeff = "3.0"
exponentialDecayCoeff = "0.03"
gaussianDecayCoeff = "80"
# Check if user specified distance decay coefficient
if distanceDecayCoeff != "":
	if distanceDecayFunc == "Power":
		powerDecayCoeff = distanceDecayCoeff
	elif distanceDecayFunc == "Exponential":
		exponentialDecayCoeff = distanceDecayCoeff
	else:
		gaussianDecayCoeff = distanceDecayCoeff

# Copy distance table into geodatabase
if ".dbf" in distanceTable:
	arcpy.CopyRows_management(distanceTable, "Temp_Dist_Table")
	distanceTable = "Temp_Dist_Table"

# Check if distance table already has the following fields:
# facility size, potential, probability
fieldList = arcpy.ListFields(distanceTable)
for field in fieldList:
	if field.name == facilitySizeField:
		arcpy.DeleteField_management(distanceTable, [facilitySizeField])
	elif field.name == "Potential":
		arcpy.DeleteField_management(distanceTable, ["Potential"])
	elif field.name == "Weight":
		arcpy.DeleteField_management(distanceTable, ["Weight"])
	elif field.name == "MAX_Potential":
		arcpy.DeleteField_management(distanceTable, ["MAX_Potential"])
	elif field.name == "SUM_Potential":
		arcpy.DeleteField_management(distanceTable, ["SUM_Potential"])
	elif field.name == "Probability":
		arcpy.DeleteField_management(distanceTable, ["Probability"])

# Check if customer layer already has the facility id field
fieldList = arcpy.ListFields(customerFL)
for field in fieldList:
	if field.name == distanceFacilityID:
		arcpy.DeleteField_management(customerFL, [distanceFacilityID])
	elif field.name == outputTradeArea:
		arcpy.DeleteField_management(customerFL, [outputTradeArea])
	elif field.name == "Probability":
		arcpy.DeleteField_management(customerFL, ["Probability"])

# Join facility layer to distance table, append facility size field
arcpy.JoinField_management(distanceTable, distanceFacilityID,
						   facilityFL, facilityIDField,
						   [facilitySizeField])

# Add a field for potential of each facility to every customer
arcpy.AddField_management(distanceTable, "Potential", "DOUBLE")

# Calculate facility potential field with distance decay
if distanceDecayFunc == "Power":
	# Check if any distance is 0
	if ".mdb" in distanceTable:
		arcpy.MakeTableView_management(distanceTable, "Temp_DistanceView", "[" + distanceValue + "] = 0")
	else:
		arcpy.MakeTableView_management(distanceTable, "Temp_DistanceView", '"' + distanceValue + '" = 0')
	cnt = int(arcpy.GetCount_management("Temp_DistanceView").getOutput(0))
	if cnt != 0:
		arcpy.AddWarning("Warning: distance between {0} customer-facility pair(s) is 0!\nA weight of 0 is assigned to such pair!".format(cnt))
	# Add a field for distance-decay based weights, calculate this field with codeblock
	arcpy.AddField_management(distanceTable, "Weight", "DOUBLE")
	weightExpression = "calculateWeight(!" + distanceValue + "!)"
	codeblock = """def calculateWeight(distance):
		if distance == 0:
			return 0
		else:
			return distance ** ((-1) * """ + powerDecayCoeff + """) * """ + scaleFactor
	arcpy.CalculateField_management(distanceTable, "Weight", weightExpression, "PYTHON_9.3", codeblock)
	# Calculate facility potential by applying weight to facility size
	expression1 = "!" + facilitySizeField + "! * !Weight!"
	arcpy.CalculateField_management(distanceTable, "Potential", expression1, "PYTHON_9.3")
	# Delete weight field from distance table
	arcpy.DeleteField_management(distanceTable, ["Weight"])
elif distanceDecayFunc == "Exponential":
	expression1 = scaleFactor + " * !" + facilitySizeField + "! * math.exp((-1) * !" + distanceValue + "! * " + exponentialDecayCoeff + ")"
	arcpy.CalculateField_management(distanceTable, "Potential", expression1, "PYTHON_9.3")
else:
	expression1 = scaleFactor + " * !" + facilitySizeField + "! / (math.sqrt(2 * math.pi) * " + gaussianDecayCoeff + ") * math.exp((-0.5) * !" + distanceValue + "! ** 2 / " + gaussianDecayCoeff + " ** 2)"
	arcpy.CalculateField_management(distanceTable, "Potential", expression1, "PYTHON_9.3")

# Summarize maximum and total facility potentials by each customer
arcpy.Statistics_analysis(distanceTable, "Temp_Sum_Potent", [["Potential", "MAX"], ["Potential", "SUM"]], distanceCustomerID)

# Join summary table to distance table, append maximum and total potentials
arcpy.JoinField_management(distanceTable, distanceCustomerID,
						   "Temp_Sum_Potent", distanceCustomerID,
						   ["MAX_Potential", "SUM_Potential"])

# Calculate probability of customer visiting a facility
arcpy.AddField_management(distanceTable, "Probability", "DOUBLE")
arcpy.CalculateField_management(distanceTable, "Probability", "!Potential! / !SUM_Potential!", "PYTHON_9.3")

# Task 1: Mapping trade area
# Select records from distance table with facility potential equal to maximum potential
if ".mdb" in distanceTable:
	arcpy.TableSelect_analysis(distanceTable, "Temp_Hosp_MaxPotent", "[Potential] = [MAX_Potential]")
else:
	arcpy.TableSelect_analysis(distanceTable, "Temp_Hosp_MaxPotent", '"Potential" = "MAX_Potential"')

# Join maximum facility potential table to customer layer, append facility id
arcpy.JoinField_management(customerFL, customerIDField,
						   "Temp_Hosp_MaxPotent", distanceCustomerID,
						   [distanceFacilityID])

# Create a trade area id field for customer layer, copy over facility id
if outputTradeArea != distanceFacilityID:
	arcpy.AddField_management(customerFL, outputTradeArea, "LONG")
	arcpy.CalculateField_management(customerFL, outputTradeArea, "!" + distanceFacilityID + "!", "PYTHON_9.3")
	# Delete joined facility id field from customer layer
	arcpy.DeleteField_management(customerFL, [distanceFacilityID])

# Task 2: Mapping probability surface
if outputProbIDs != "":
	facilityIDList = outputProbIDs.split(";")
	for facilityID in facilityIDList:
		# Generate a new field name
		newFieldName = "Prob_" + facilityID
		# Check if this field already exists in customer layer
		fieldList = arcpy.ListFields(customerFL)
		for field in fieldList:
			if field.name == newFieldName:
				arcpy.DeleteField_management(customerFL, [newFieldName])
		# Select records from distance table with facility id equal to user-specified value
		if ".mdb" in distanceTable:
			arcpy.TableSelect_analysis(distanceTable, "Temp_Prob_" + facilityID, "[" + distanceFacilityID + "] = " + facilityID)
		else:
			arcpy.TableSelect_analysis(distanceTable, "Temp_Prob_" + facilityID, '"' + distanceFacilityID + '" = ' + facilityID)

		# Check if table is empty
		arcpy.MakeTableView_management("Temp_Prob_" + facilityID, "Temp_ProbView_" + facilityID)
		cnt = int(arcpy.GetCount_management("Temp_ProbView_" + facilityID).getOutput(0))
		if cnt == 0:
			arcpy.AddWarning("Warning: {0} is not a valid ID in facility layer!".format(facilityID))
		else:
			# Add new field to customer layer
			arcpy.AddField_management(customerFL, newFieldName, "DOUBLE")
			# Join facility visiting probability to customer layer, append probability
			arcpy.JoinField_management(customerFL, customerIDField,
									   "Temp_Prob_" + facilityID, distanceCustomerID,
									   ["Probability"])
			# Copy over facility probability to the new field
			arcpy.CalculateField_management(customerFL, newFieldName, "!Probability!", "PYTHON_9.3")
			# Delete joined facility probability field from customer layer
			arcpy.DeleteField_management(customerFL, ["Probability"])

		# Remove temporary table
		arcpy.Delete_management("Temp_Prob_" + facilityID)

# Copy input customer layer to a new featureclass
arcpy.CopyFeatures_management(customerFL, outputCustomerFC)

# Delete added fields from input customer layer
arcpy.DeleteField_management(customerFL, [outputTradeArea])
if outputProbIDs != "":
	facilityIDList = outputProbIDs.split(";")
	for facilityID in facilityIDList:
		# Generate a new field name
		newFieldName = "Prob_" + facilityID
		arcpy.DeleteField_management(customerFL, [newFieldName])

# Cleanup intermediate data
arcpy.Delete_management("Temp_Dist_Table")
arcpy.Delete_management("Temp_Sum_Potent")
arcpy.Delete_management("Temp_Hosp_MaxPotent")
