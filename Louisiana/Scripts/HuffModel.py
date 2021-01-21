# Import system modules
import arcpy

# Get input parameters
customerFL = arcpy.GetParameterAsText(0)
customerIDField = arcpy.GetParameterAsText(1)
facilityFL = arcpy.GetParameterAsText(2)
facilityIDField = arcpy.GetParameterAsText(3)
facilitySizeField = arcpy.GetParameterAsText(4)
distanceDecayFunc = arcpy.GetParameterAsText(5)
distanceDecayCoeff = arcpy.GetParameterAsText(6)
unitConversion = arcpy.GetParameterAsText(7)
scaleFactor = arcpy.GetParameterAsText(8)
outputProbIDs = arcpy.GetParameterAsText(9)
outputCustomerFC = arcpy.GetParameterAsText(10)

distanceTable = "Temp_ODMatrix"
distanceCustomerID = "INPUT_FID"
distanceFacilityID = "NEAR_FID"
distanceValue = "DISTANCE"

outputTradeArea = "FacilityID"

# Delete intermediate data if they already exist
if arcpy.Exists("Temp_ODMatrix"):
	arcpy.Delete_management("Temp_ODMatrix")

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

# Check feature layer type and convert it to centroid layer if necessary
customer_pt = customerFL
desc = arcpy.Describe(customerFL)
if desc.shapeType == "Polygon":
	customer_pt = "Temp_Customer_Pt"
	arcpy.FeatureToPoint_management(customerFL, customer_pt, "INSIDE")
	# Need to change customer id to NEW_FID for shapefile, which is FID + 1
	if customerIDField == "FID":
		fieldList = arcpy.ListFields(customerFL)
		for field in fieldList:
			if field.name == "NEW_FID":
				arcpy.DeleteField_management(customerFL, ["NEW_FID"])
		arcpy.AddField_management(customerFL, "NEW_FID", "LONG")
		arcpy.CalculateField_management(customerFL, "NEW_FID", "!FID! + 1", "PYTHON_9.3")
		customerIDField = "NEW_FID"

facility_pt = facilityFL
desc = arcpy.Describe(facilityFL)
if desc.shapeType == "Polygon":
	facility_pt = "Temp_Facility_Pt"
	arcpy.FeatureToPoint_management(facilityFL, facility_pt, "INSIDE")
	# Need to change facility id to NEW_FID for shapefile, which is FID + 1
	if facilityIDField == "FID":
		fieldList = arcpy.ListFields(facilityFL)
		for field in fieldList:
			if field.name == "NEW_FID":
				arcpy.DeleteField_management(facilityFL, ["NEW_FID"])
		arcpy.AddField_management(facilityFL, "NEW_FID", "LONG")
		arcpy.CalculateField_management(facilityFL, "NEW_FID", "!FID! + 1", "PYTHON_9.3")
		facilityIDField = "NEW_FID"

# Calculate Euclidean distance from customer to facility
arcpy.PointDistance_analysis(customer_pt, facility_pt, distanceTable)

# Scale distance value with unit conversion factor
expression0 = "!" + distanceValue + "! * " + unitConversion
arcpy.CalculateField_management(distanceTable, distanceValue, expression0, "PYTHON_9.3")

# Cleanup temporary data
if arcpy.Exists("Temp_Customer_Pt"):
	arcpy.Delete_management("Temp_Customer_Pt")
if arcpy.Exists("Temp_Facility_Pt"):
	arcpy.Delete_management("Temp_Facility_Pt")

# Check if customer layer already has the facility id field
fieldList = arcpy.ListFields(customerFL)
for field in fieldList:
	if field.name == distanceFacilityID:
		arcpy.DeleteField_management(customerFL, [distanceFacilityID])
	elif field.name == outputTradeArea:
		arcpy.DeleteField_management(customerFL, [outputTradeArea])
	elif field.name == "Probabilit":
		arcpy.DeleteField_management(customerFL, ["Probabilit"])

# Join facility layer to distance table, append facility size field
arcpy.JoinField_management(distanceTable, distanceFacilityID,
						   facilityFL, facilityIDField,
						   [facilitySizeField])

# Add a field for potential of each facility to every customer
arcpy.AddField_management(distanceTable, "Potential", "DOUBLE")

# Calculate facility potential field with distance decay
if distanceDecayFunc == "Power":
	# Check if any distance is 0
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
arcpy.AddField_management(distanceTable, "Probabilit", "DOUBLE")
arcpy.CalculateField_management(distanceTable, "Probabilit", "!Potential! / !SUM_Potential!", "PYTHON_9.3")

# Task 1: Mapping trade area
# Select records from distance table with facility potential equal to maximum potential
arcpy.TableSelect_analysis(distanceTable, "Temp_Hosp_MaxPotent", '"Potential" = "MAX_Potential"')

# Join maximum facility potential table to customer layer, append facility id
arcpy.JoinField_management(customerFL, customerIDField,
						   "Temp_Hosp_MaxPotent", distanceCustomerID,
						   [distanceFacilityID])

# Create a trade area id field for customer layer, copy over facility id
if outputTradeArea != distanceFacilityID:
	arcpy.AddField_management(customerFL, outputTradeArea, "LONG")
	if facilityIDField == "NEW_FID":
		arcpy.CalculateField_management(customerFL, outputTradeArea, "!" + distanceFacilityID + "! - 1", "PYTHON_9.3")
	else:
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
		if facilityIDField == "NEW_FID":
			arcpy.TableSelect_analysis(distanceTable, "Temp_Prob_" + facilityID, '"' + distanceFacilityID + '" = (' + facilityID + ' + 1)')
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
									   ["Probabilit"])
			# Copy over facility probability to the new field
			arcpy.CalculateField_management(customerFL, newFieldName, "!Probabilit!", "PYTHON_9.3")
			# Delete joined facility probability field from customer layer
			arcpy.DeleteField_management(customerFL, ["Probabilit"])

		# Remove temporary table
		arcpy.Delete_management("Temp_Prob_" + facilityID)

# Copy input customer layer to a new featureclass
if customerIDField == "NEW_FID":
	arcpy.DeleteField_management(customerFL, ["NEW_FID"])
arcpy.CopyFeatures_management(customerFL, outputCustomerFC)

# Delete added fields from input customer layer
arcpy.DeleteField_management(customerFL, [outputTradeArea])
if outputProbIDs != "":
	facilityIDList = outputProbIDs.split(";")
	for facilityID in facilityIDList:
		# Generate a new field name
		newFieldName = "Prob_" + facilityID
		arcpy.DeleteField_management(customerFL, [newFieldName])

# Delete added fields from input facility layer
if facilityIDField == "NEW_FID":
	arcpy.DeleteField_management(facilityFL, ["NEW_FID"])

# Cleanup intermediate data
arcpy.Delete_management("Temp_ODMatrix")
arcpy.Delete_management("Temp_Sum_Potent")
arcpy.Delete_management("Temp_Hosp_MaxPotent")
