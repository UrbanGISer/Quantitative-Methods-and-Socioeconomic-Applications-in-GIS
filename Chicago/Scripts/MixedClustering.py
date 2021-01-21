#*****************************************************************************************
#This script take the input with two levels of geographic unit, e.g. tract and county,
#and assign mixed-level cluster type to each basic unit, e.g. tract based on multiple constraints
#such as population (>=20000) and total cancer count (>=15).
#The results are ClusType = 1,2, 3 or 4
#Where 1 = low level clusters (tract)
#      2 = mid level clusters (county)
#      3 = high level clusters (multi-county)
#      4 = mixed low and high level clusters (tract and county)
#
#
#  Suggested citation for using this tool:
#  Lan Mu and Fahui Wang. 2015. Appendix 9B: A toolkit of the mixed-level regionalization method,
#  in Fahui Wang, Quantitative Methods and Socioeconomic Applications in GIS (2nd ed.). Boca Raton, FL: Taylor & Francis.  
#
#  Suggested citation for the mixed-level regionalization (MLR) method:
#  Mu, L. and F. Wang (2012), A Place-Oriented, Mixed-level Regionalization Method for Constructing Geographic Areas
#  in Health Data Dissemination and Analysis, 108th Annual Conference of the Association of American Geographers,
#  February 24-28, New York City, NY.
#
#  Programmed by Mu, Lan
#
#  copyright: 2012-
#*****************************************************************************************

#prints a GP message and writes the same message to a log file
def PrintAndWriteMessages(msg,severity=0):
    if severity == 0:
        gp.AddMessage(msg)
    elif severity == 1:
        gp.AddWarning(msg)
    elif severity == 2:
        gp.AddError(msg)
    #logfile.write(msg + "\n")

# Delete a field if it exists in the input feature class (or layer).
def DelAField(theFC, theField):
    flds = gp.ListFields(theFC, theField)
    for fld in flds:
        if fld:
            gp.DeleteField(theFC, theField)
            
# Add a field if it does not exist in the input feature class (or layer).
def AddAField(theFC, theField, fldType):
    class GetOutOfDef( Exception ):
        pass  
    try:
        flds = gp.ListFields(theFC, theField)
        for fld in flds:
            if fld:
                raise GetOutOfDef
        gp.AddField_management(theFC, theField, fldType)
    except GetOutOfDef:
        pass
    
#Import the modules
import arcgisscripting, sys,os, traceback

#Create the 93 geoprocessor to use native python objects returned by list methods on geoprocessor
gp = arcgisscripting.create(9.3)

#Use the lowest available license
for product in ['Engine','ArcView', 'ArcEditor', 'EngineGeoDB','ArcInfo', 'ArcServer']:
    if gp.CheckProduct(product).lower() == 'available':
        gp.SetProduct(product)
        break

gp.Overwriteoutput = True
try:
    #Create a log file with messages in the same location as the script
    #logfile = open(os.path.splitext(sys.argv[0])[0] + "_log.txt","w",0)

    #Get the inputs
    inp_fc = gp.GetParameterAsText(0)
    PeanoOrder_fld = gp.GetParameterAsText(1)   # Spatial order by Peano Curve (0-1)
    AttriOrder_fld = gp.GetParameterAsText(2)   # Aggregated weighted attributive order
    NAttriOrder_fld = gp.GetParameterAsText(3)  # Normalized attribute order (0-1)
    Order_fld = gp.GetParameterAsText(4)        # Integrated order field to be created for each one-level clustering
    Attri_list = gp.GetParameterAsText(5)
    Wt_list = gp.GetParameterAsText(6)
    Pct_Peano = float(gp.GetParameterAsText(7))

    constraint_list = gp.GetParameterAsText(8)  # List of vairables with lower limits
    capacity_list = gp.GetParameterAsText(9)    # Values of the lower limit for each constraint variable.
    out_class_item = gp.GetParameterAsText(10)   # Sub cluster membership in each one-level clustering
    isolate = gp.GetParameterAsText(11)          # Whether a cluster is nusatisfied and isoloated (0 or 1)
    
    upper_ID = gp.GetParameterAsText(12)         # string or number, field to represent the upper level unit, e.g. county
    cluster_type = gp.GetParameterAsText(13)     # short integer, new variable added to table for cluster types, "ClusType" 

    DissolveWt = gp.GetParameterAsText(14)      # Weight (a field) of calculating dissolved units
    cluster = gp.GetParameterAsText(15)         # final cluster ID field
    mixed_clusters = gp.GetParameterAsText(16)   # final feature class of mixed clusters

    Pct_Attri = 100 - Pct_Peano

    #parse the input parameter strings to lists
    ConstraintList = constraint_list.split(';')
    CapacityList = capacity_list.split(';')
    AttriList = Attri_list.split(';')
    WtList = Wt_list.split(';')

    # Get the path and full name of the input feature class
    desc = gp.Describe(inp_fc)
    gp.Workspace = desc.path
    fullInp_fc = desc.BaseName + "." + desc.Extension
    
    #Validate the output field name for the workspace
    PeanoOrder_fld = gp.ValidateFieldName(PeanoOrder_fld,os.path.dirname(inp_fc))
    AttriOrder_fld = gp.ValidateFieldName(AttriOrder_fld,os.path.dirname(inp_fc))
    NAttriOrder_fld = gp.ValidateFieldName(NAttriOrder_fld,os.path.dirname(inp_fc))
    Order_fld = gp.ValidateFieldName(Order_fld,os.path.dirname(inp_fc))
    out_class_item = gp.ValidateFieldName(out_class_item,os.path.dirname(inp_fc))
    isolate = gp.ValidateFieldName(isolate,os.path.dirname(inp_fc))
    cluster_type = gp.ValidateFieldName(cluster_type,os.path.dirname(inp_fc))

    # Execute the Simmarize Statistics tool using the SUM option and case field (e.g. county)
    msg = "\n" + "All-in-one mixed-clustering script starts to run." + \
          "\n" + "Be patient, this could take a while." + \
          "\n\n" + "Aggegate the units to the upper level to determine cluster type at the upper level." + \
          "The mixed-cluster results will have cluster type of 1,2, 3 or 4, where" + \
          "\n" + " # 1 = lower level clusters (e.g.tract)" + \
          "\n" + " # 2 = single upper level clusters (e.g. a county)" + \
          "\n" + " # 3 = multi upper level clusters (e.g. multi-county)" + \
          "\n" + " # 4 = mixed lower and upper level clusters (e.g., tract and county)"
          
    PrintAndWriteMessages(msg,0)  
    
    tmpTbUpper = "sum_upper"
    if gp.Exists(tmpTbUpper):
        gp.Delete(tmpTbUpper)

    sumfldsDscp = []
    for constraint in ConstraintList:
        sumfldsDscp.append(constraint + " sum")
    sumfldsDscp = ";".join(sumfldsDscp)
    
    gp.Statistics_analysis(inp_fc, tmpTbUpper, sumfldsDscp, upper_ID)
    
    #Add the new field to the summary table. If the field already exists, AddField has a warning
    result = gp.AddField_management(tmpTbUpper, PeanoOrder_fld, "DOUBLE")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)
##    gp.SetProgressorPosition()

    result = gp.AddField_management(tmpTbUpper, AttriOrder_fld, "DOUBLE")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)

    result = gp.AddField_management(tmpTbUpper, NAttriOrder_fld, "DOUBLE")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)

    result = gp.AddField_management(tmpTbUpper, Order_fld, "DOUBLE")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)

    result = gp.AddField_management(tmpTbUpper, out_class_item, "Short")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)

    result = gp.AddField_management(tmpTbUpper, isolate, "Short")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)

    result = gp.AddField_management(tmpTbUpper, cluster_type, "Short")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)
           
    # Get the sum fields to be used later
    flds = gp.ListFields(tmpTbUpper)
    fldSum = []
    for fld in flds:
        if fld.Name.__contains__("SUM_") or fld.Name.__contains__("sum_"):
            fldSum.append(fld.Name)
            
    # Go through every record to assign cluster type to each summarized upper unit (e.g. county).
    rows = gp.UpdateCursor(tmpTbUpper)
    rows.reset()
    row = rows.next()
    while row:
        measures = []
        for fld in fldSum:
            measures.append(row.GetValue(fld))

        # Cluster type = 1, to be disaggregated within one upper unit
        met2All = 1; metAll = 1
        for i in range(len(measures)):
            if float(measures[i]) >= 2 * float(CapacityList[i]):
                met2All = met2All * 1
            else:
                met2All = met2All * 0

            if float(measures[i]) >= float(CapacityList[i]):
                metAll = metAll * 1
            else:
                metAll = metAll * 0

        if met2All == 1:
            row.SetValue(cluster_type, 1)
            
        # Cluster type = 2, good at upper unit level
        elif metAll == 1:
            row.SetValue(cluster_type, 2)

        # Cluster type = 3, to be agrregated at upper unit level 
        else:
            row.SetValue(cluster_type, 3)

        rows.UpdateRow(row)
        del row
        row = rows.next()
    del rows

    # If cluster_type field exists in the input feature class, delete it; otherwise the following joinfield will be conflicted.   
    #Call a function
    DelAField(inp_fc, cluster_type)
            
    #joinField to join the sum table back to the original data table, and permanently add the cluster_type field
    #Usage: JoinField <in_data> <in_field> <join_table> <join_field> {fields;fields...}
    gp.JoinField(inp_fc, upper_ID, tmpTbUpper, upper_ID, cluster_type)

    #Get the OID field name
    oid_fld = desc.OIDFieldName
##    msg = "oid_fld = " + oid_fld
##    gp.SetProgressorLabel(msg)
##    PrintAndWriteMessages(msg,0)
    # use a field to copy FID/OID to the new integer field, because FID/OID cannot be used in GenerateSpatialWeightsMatrix
    result = gp.AddField_management(inp_fc,"TheID","Short")
##    if result.MaxSeverity == 1:
##        msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
##        PrintAndWriteMessages(msg,1)
        
    # A pair of "!" signs for using existing variables (attribute table) in Python expression.  
    exp = "!" + oid_fld + "!"
    gp.CalculateField_management(inp_fc,"TheID", exp, "PYTHON_9.3","#")

    # creat a list of feature class layers for inputing into clustering tool (script)
    lyr = "tmplyr"
    #ready to call the functions in other scripts
    import Func_ClusteringOrder
    import Func_OneLevelClustering

    # Scenario  1: upper unit need to be disaggregated
    msg = "\n" + "Now start processing scenario 1: an upper unit needs to be disaggregated." + \
          "\n" + "Clustering order accounting for both spatial (Peano Curve) and attributive measures " + \
          "will be calculated and then lower units will be clustered within each upper unit."       
    PrintAndWriteMessages(msg,0)
    count1 = 0
    where_clause = cluster_type + " = 1"
    rows = gp.SearchCursor(tmpTbUpper, where_clause)
    rows.reset()
    row = rows.next()
    while row:
    #while count1 <= 3:  # use a small sample for testing only
        count1 += 1
        where_clause2 = upper_ID + " = '" + row.GetValue(upper_ID) + "'"
        #msg = where_clause2 + " is the current unit and the lyr is " + lyr
        #PrintAndWriteMessages(msg,1)
        
        gp.MakeFeatureLayer(inp_fc, lyr, where_clause2)
        Func_ClusteringOrder.ClusteringOrder \
            (lyr, PeanoOrder_fld, AttriOrder_fld, NAttriOrder_fld, Order_fld, Attri_list, Wt_list, Pct_Peano)
        Func_OneLevelClustering.OneLevelClustering \
            (lyr, Order_fld, constraint_list, capacity_list, out_class_item, isolate)
        
        msg = where_clause2 + " is done. Its cluster type is 1."
        PrintAndWriteMessages(msg,1)
        
        del row
        gp.Delete(lyr)
        row = rows.next()    
    del row, rows

    # Scenario  2: upper unit is good enough to be a cluster
    msg = "\n" + "Now start processing scenario 2: an upper unit is good enough to be a cluster."
    PrintAndWriteMessages(msg,0)
    count2 = 0      
    where_clause = cluster_type + " = 2"
    rows = gp.SearchCursor(tmpTbUpper, where_clause)
    rows.reset()
    row = rows.next()
    while row:
        count2 += 1    
        where_clause2 = upper_ID + " = '" + row.GetValue(upper_ID) + "'"
        gp.MakeFeatureLayer(inp_fc, lyr, where_clause2)

        result = gp.AddField_management(lyr,"included","Short")
##        if result.MaxSeverity == 1:
##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
##            PrintAndWriteMessages(msg,1)
        gp.SetProgressorPosition()
        gp.CalculateField_management(lyr,"included",1,"PYTHON_9.3","#")
        gp.CalculateField_management(lyr,out_class_item, count2, "PYTHON_9.3","#")
        
        msg = where_clause2 + " is done. Its cluster type is 2."
        PrintAndWriteMessages(msg,1)
        
        del row
        gp.Delete(lyr)
        row = rows.next()
    del row, rows

    # Scenario  3: upper units need to be aggregated to larger unit to satisfy the clustering criteria.
    msg = "\n" + "Now start processing scenario 3: upper units need to be aggregated to " + \
          "larger units to satisfy the clustering criteria."
    PrintAndWriteMessages(msg,0)
    count3 = 0   
    where_clause = cluster_type + " = 3"
    gp.MakeFeatureLayer(inp_fc, lyr, where_clause)
    count3 = long(gp.GetCount(lyr).GetOutput(0))
    if count3 > 0:

        dissolvedUpperFC = "dissolvedUpperFC.shp"
        if gp.Exists(dissolvedUpperFC):
            gp.Delete(dissolvedUpperFC)

        # Use sumfldsDscp defined previously in this script
        # DissolveWt could be one of the contraints or NOT.
        if DissolveWt in ConstraintList:
            statFields = sumfldsDscp + "; TheID MIN"
            DissolveWtIn = 1
        else:
            statFields = sumfldsDscp + "; TheID MIN; " + DissolveWt + " SUM"
            DissolveWtIn = 0

        msg = "The field (weight) used to aggregate attributes to upper level is " + DissolveWt
        PrintAndWriteMessages(msg,1)
    ##    msg = "statFields in the dissolvedUpperFC are " + statFields
    ##    PrintAndWriteMessages(msg,1)
        
        gp.Dissolve_management(lyr, dissolvedUpperFC, upper_ID, statFields)
        gp.AddField_management(dissolvedUpperFC, cluster_type, "Short")
        gp.CalculateField_management(dissolvedUpperFC,cluster_type, "3", "PYTHON_9.3","#")

        # Get the fields of SUM or MIN to be used later
        flds = gp.ListFields(dissolvedUpperFC)
        fldSumDissolve = []; fldMin = ""; fldDissolveWt = ""
        for fld in flds:
            if fld.Name.__contains__("SUM_") or fld.Name.__contains__("sum_"):
                if DissolveWtIn == 1 or (DissolveWtIn == 0 and fld.Name.__contains__(DissolveWt[:5]) == False):
                    fldSumDissolve.append(fld.Name)
            if fld.Name.__contains__("MIN_") or fld.Name.__contains__("min_"):
                fldMin = fld.Name
            if fld.Name.__contains__(DissolveWt[:5]):
                fldDissolveWt = fld.Name         
       
        # Calculate weighted dissolved attributes, e.g. Factors 1, 2, & 3 weighted by population
        #Usage: JoinField <in_data> <in_field> <join_table> <join_field> {fields;fields...}
        DelAField(lyr, fldDissolveWt)
        gp.JoinField(lyr, upper_ID, dissolvedUpperFC, upper_ID, fldDissolveWt)

        WtAttriList = []
        for i in range(len(AttriList)):
            WtAttriList.append("W" + AttriList[i])
            gp.AddField_management(lyr, WtAttriList[i], "DOUBLE")
        
        rows = gp.UpdateCursor(lyr, fldDissolveWt + " > 0")
        rows.reset()
        row = rows.next()
        while row:
            theRatio = row.GetValue(DissolveWt) / row.GetValue(fldDissolveWt)
            for i in range(len(WtAttriList)):
                 row.SetValue(WtAttriList[i], row.GetValue(AttriList[i]) * theRatio)      
            rows.UpdateRow(row)
            del row
            row = rows.next()
        del rows

        #summarize weighted attributes by upperID, then integrate them to the dissolved table
        tmpTbSumWtAttri = "sum_attri"
        if gp.Exists(tmpTbSumWtAttri):
            gp.Delete(tmpTbSumWtAttri)

        sumAttrifldsDscp = []
        for Wtattri in WtAttriList:
            sumAttrifldsDscp.append(Wtattri + " sum")
        sumAttrifldsDscp = ";".join(sumAttrifldsDscp)

        gp.Statistics_analysis(lyr, tmpTbSumWtAttri, sumAttrifldsDscp, upper_ID)
        flds = gp.ListFields(tmpTbSumWtAttri)
        fldDissolveAttri = []
        for fld in flds:
            if fld.Name.__contains__("SUM_") or fld.Name.__contains__("sum_"):
                fldDissolveAttri.append(fld.Name)
        DissolveAttri_list = ";".join(fldDissolveAttri)        

        gp.JoinField(dissolvedUpperFC, upper_ID, tmpTbSumWtAttri, upper_ID, DissolveAttri_list)
                          
        # add a field TheID to copy MIN_TheID to the new integer field.
        result = gp.AddField_management(dissolvedUpperFC,"TheID","Short")
    ##    if result.MaxSeverity == 1:
    ##        msg = result.GetMessages(1).split(':')[1].lstrip() + " For the dissolved feature class, existing values of TheID will be overwritten."
    ##        PrintAndWriteMessages(msg,1)    
        exp = "!" + str(fldMin) + "!"
        gp.CalculateField_management(dissolvedUpperFC,"TheID", exp, "PYTHON_9.3","#")

        dissolvedUpperFlyr = "dissolvedUpperFlyr"
        gp.MakeFeatureLayer(dissolvedUpperFC, dissolvedUpperFlyr)
    ##    Func_SpatialOrder.CalcSpatialOrder(dissolvedUpperFlyr, order_fld)
    ##    Func_RevCollocate.RevisedCollocate(dissolvedUpperFlyr, order_fld, fld1, capacity1, fld2, capacity2, out_class_item, cluster_type)

        # Attri_list and Wt_list are ";" splited. Wt_list is the same as the original input,
        # but Attri_list needs to re-defined for the dissolved layer.
        # contraint_list needs to re-defined, capacity_list stays the same as the original input

        DissolveConstraint_list = ";".join(fldSumDissolve)
    ##    msg = "Constraint list to be passed onto the function is: " + DissolveConstraint_list
    ##    PrintAndWriteMessages(msg,1)
        
        Func_ClusteringOrder.ClusteringOrder \
            (dissolvedUpperFlyr, PeanoOrder_fld, AttriOrder_fld, \
             NAttriOrder_fld, Order_fld, DissolveAttri_list, Wt_list, Pct_Peano)
        if long(gp.GetCount(dissolvedUpperFlyr).GetOutput(0)) > 1:
            Func_OneLevelClustering.OneLevelClustering \
                (dissolvedUpperFlyr, Order_fld, DissolveConstraint_list, \
                 capacity_list, out_class_item, isolate)
                
        # AddJoin to join the dissolved table back to the original data table, and calculate/change field values
        desc2 = gp.Describe(dissolvedUpperFlyr)
        joinName = desc2.BaseName
        inpName = desc.BaseName

        # Call a function to ddd a field if not added previously.
        AddAField(lyr, Order_fld, "DOUBLE")
        AddAField(lyr, out_class_item, "Short")
        AddAField(lyr, "included", "Short")
        AddAField(lyr, isolate, "Short")
        
        gp.AddJoin(lyr, upper_ID, dissolvedUpperFlyr, upper_ID)     # lyr is previously defined as cluster_type = 3
        gp.CalculateField(lyr, inpName + "." + Order_fld, "!" + joinName + "." + Order_fld + "!", "PYTHON_9.3","#")
        gp.CalculateField(lyr, inpName + "." + out_class_item, "!" + joinName + "."  + out_class_item + "!", "PYTHON_9.3","#")
        gp.CalculateField(lyr, inpName + "." + "included", "!" + joinName + "." + "included" + "!", "PYTHON_9.3","#")
        gp.CalculateField(lyr, inpName + "." + isolate, "!" + joinName + "."  + isolate + "!", "PYTHON_9.3","#")
        gp.RemoveJoin(lyr, joinName)

        gp.Delete(lyr)  
        gp.Delete(dissolvedUpperFlyr)
        gp.Delete(dissolvedUpperFC)
        msg = where_clause + " is done. Its cluster type is 3."
        PrintAndWriteMessages(msg,1)

    else:
        msg = "There is no cluster type 3 in this data."
        PrintAndWriteMessages(msg,1)
        
    ### Additional codes to tackle isolated cluster at different levels.   
    # Add a new field of integrated cluster membership and dissolve all clusters at all levels.
    # format: T.UUU.S, where T = cluster type (1,2,3), UUU = upper level code (e.g. county FIPS), and S = sub cluster ID 
    msg = "\n" + "Now start tackling isolated clusters at all levels." + \
          "\n" + "Some clusters' type and membership might be changed and a new cluster type of '4' " + \
          "might be created."
    PrintAndWriteMessages(msg,0)

    lyr = "lyr"
    gp.MakeFeatureLayer(inp_fc, lyr)
    gp.AddField_management(lyr, cluster, "Text")

    lyr1_2 = "lyr1_2"
    where_clause = cluster_type + " <> 3"
    gp.MakeFeatureLayer(inp_fc, lyr1_2, where_clause)
    exp = "str(!" + cluster_type + "!) + '.'+ !" + upper_ID + "! + '.' + str(!" + out_class_item + "!)"
    gp.CalculateField(lyr1_2, cluster, exp, "PYTHON_9.3","#")
    gp.Delete(lyr1_2)

    # for multi-county cluster, the upper_id in the cluster ID is assigned as special, e.g. 000 
    lyr3 = "lyr3"
    where_clause = cluster_type + " = 3"
    gp.MakeFeatureLayer(inp_fc, lyr3, where_clause)
    if long(gp.GetCount(lyr3).GetOutput(0)) > 0:
        rows = gp.SearchCursor(lyr3)
        rows.reset()
        row = rows.next()
        firstUpperID = str(row.GetValue(upper_ID))
        del row
        del rows
        specialID = []
        for i in range(len(firstUpperID)):
            specialID.append("0")
        specialID = "".join(specialID)
        #msg = "Multi-county's upper ID is assigned as " + specialID
        #PrintAndWriteMessages(msg, 1)
        exp = "str(!" + cluster_type + "!) + '.' + str('" + specialID + "') + '.' + str(!" + out_class_item + "!)"
        gp.CalculateField(lyr3, cluster, exp, "PYTHON_9.3","#")
    gp.Delete(lyr3)

    # Dissolve all clusters at all levels according to the newly added integrated clusters.
    tmpMixedClusFC = "tmpMixedClusters.shp"
    if gp.Exists(tmpMixedClusFC):
        gp.Delete(tmpMixedClusFC)
        
    mixStatFlds = []
    for i in ConstraintList:
        mixStatFlds.append(i + " sum")
    mixStatFlds.append(cluster_type + " min")
    mixStatFlds.append(upper_ID + " first")
    mixStatFlds.append(isolate + " min")
    mixStatFlds = ";".join(mixStatFlds)
    gp.Dissolve_management(lyr, tmpMixedClusFC, cluster, mixStatFlds)

    # replace all upper units to 000 for cluster type = 3
    flds = gp.ListFields(tmpMixedClusFC)
    fldClusType = ""; fldUpID = ""; fldIso = ""; fldsCap = []
    for fld in flds:
        #msg = "A field name in the temp mixed clusters is " + fld.Name 
        #PrintAndWriteMessages(msg, 1)
        if fld.Name.__contains__(cluster_type[:6]) or fld.Name.__contains__(cluster_type[:6].upper()):
            fldClusType = fld.Name
        if fld.Name.__contains__("first_") or fld.Name.__contains__("FIRST_"):
            fldUpID = fld.Name
        if fld.Name.__contains__(isolate[:6]) or fld.Name.__contains__(isolate[:6].upper()):
            fldIso = fld.Name
        for i in range(len(CapacityList)):
            if fld.Name.__contains__(ConstraintList[i][:6]) or fld.Name.__contains__(ConstraintList[i][:6].upper()):
                fldsCap.append(fld.Name)
##    msg = "In the mixed clusters, cluster type and upperID variables are: " + fldClusType + \
##         " and " + fldUpID
##    PrintAndWriteMessages(msg, 1)
    #msg = "In the mixed clusters, capacity variables are: " + ",".join(fldsCap)
    #PrintAndWriteMessages(msg, 1)
    gp.MakeFeatureLayer(tmpMixedClusFC, "tmplyr", fldClusType + " = 3")
    if long(gp.GetCount("tmplyr").GetOutput(0)) > 0:
        gp.CalculateField("tmplyr", fldUpID, "str('" + specialID + "')", "PYTHON_9.3","#")
    gp.Delete("tmplyr")

    MixedClusLyr = "MixedClusLyr"
    gp.MakeFeatureLayer(tmpMixedClusFC, MixedClusLyr)
    
    # sub scenario 1: isolation at the lower level (tract), merge to a nearby same-level cluster, connected or not, e.g. St Martin
    # for each isolated cluster, select all sub clusters within the same upper unit.
    # There will be no adjacent cluster, simply find the min cluster.
    # Change cluster membership in original feature class (e.g. tract)
    lyr4 = "lyr4"; lyr5 = "lyr5"; lyr6 = "lyr6"; lyr7 = "lyr7"
    where_clause = fldIso + " = 1 and " + fldClusType + " = 1"
    gp.MakeFeatureLayer(tmpMixedClusFC, lyr4, where_clause)
    isoCount1 = long(gp.GetCount(lyr4).GetOutput(0))
    rows = gp.SearchCursor(lyr4)
    rows.reset()
    row = rows.next()
    while row:
        theUpID = row.GetValue(fldUpID)
        theClus = row.GetValue(cluster)
        where_clause = fldUpID + " = \'" + theUpID + "\' AND " + cluster + " <> \'" + theClus + "\'"
        gp.MakeFeatureLayer(tmpMixedClusFC, lyr5, where_clause )
        rows2 = gp.SearchCursor(lyr5)
        rows2.reset()
        row2 = rows2.next()
        count = 0
        while row2:
            count += 1
            if count == 1:
                minCap = row2.GetValue(fldsCap[0])
                minClus = row2.GetValue(cluster)
            elif row2.GetValue(fldsCap[0]) < minCap:
                minCap = row2.GetValue(fldsCap[0])
                minClus = row2.GetValue(cluster)              
            row2 = rows2.next()
        del row2, rows2

        # Go back to original file
        where_clause = cluster + " = \'" + theClus + "\'"
        gp.MakeFeatureLayer(inp_fc, lyr6, where_clause)
        exp = "\'" + minClus + "\'"
        gp.CalculateField(lyr6, cluster, exp, "PYTHON_9.3","#")
        gp.CalculateField(lyr6, isolate, "0", "PYTHON_9.3","#")
        theSubClusID = minClus.split(".")[2]
        gp.CalculateField(lyr6, out_class_item, theSubClusID, "PYTHON_9.3","#")

        row = rows.next()
    del row, rows
    if gp.Exists(lyr4):
        gp.Delete(lyr4)
    if gp.Exists(lyr5):
        gp.Delete(lyr5)
    if gp.Exists(lyr6):
        gp.Delete(lyr6)
    
    # sub scenario 2: isolation at the upper level (county), merge to nearby clusters,
    # give the priority to upper level cluster.
    # Look for all adjacent clusters, give type = 2 first priority, since it keeps upper boundary. Find min cluster
    # If there is no type2 cluster, look for min type1 cluster and merge
    # If a mixed-level 1 & 3 is needed, define and count it
    count4 = 0
    where_clause = fldIso + " = 1 and " + fldClusType + " = 3"
    gp.MakeFeatureLayer(tmpMixedClusFC, lyr4, where_clause)
    isoCount2 = long(gp.GetCount(lyr4).GetOutput(0))
##    msg = "The number of isolated type 3 clusters is " + str(isoCount2)  
##    PrintAndWriteMessages(msg, 1)
    rows = gp.SearchCursor(lyr4)
    rows.reset()
    row = rows.next()
    while row:
        theClus = row.GetValue(cluster)
        where_clause = cluster + " = \'" + theClus + "\'"
        gp.MakeFeatureLayer(tmpMixedClusFC, lyr5, where_clause)
        gp.SelectLayerByLocation(MixedClusLyr, "SHARE_A_LINE_SEGMENT_WITH", lyr5)
        where_clause = cluster + " <> \'" + theClus + "\'"
        gp.MakeFeatureLayer(MixedClusLyr, lyr6, where_clause)
##        msg = "The number of features in the selected layer is " + str(long(gp.GetCount(lyr6).GetOutput(0)))
##        PrintAndWriteMessages(msg, 1)

        rows2 = gp.SearchCursor(lyr6,fldClusType + " = 2")
        rows2.reset()
        row2 = rows2.next()
        count = 0
        while row2:
            count += 1
            if count == 1:
                minCap = row2.GetValue(fldsCap[0])
                minClus = row2.GetValue(cluster)
            elif row2.GetValue(fldsCap[0]) < minCap:
                minCap = row2.GetValue(fldsCap[0])
                minClus = row2.GetValue(cluster)
            row2 = rows2.next()
        del row2, rows2
        
        # If find a type2 cluster to merge, Go back to original file, change the previous type2 cluster
        if count >= 1:
            where_clause = cluster + " = \'" + minClus + "\'"
            gp.MakeFeatureLayer(inp_fc, lyr7, where_clause)
            exp = "\'" + theClus + "\'"
            gp.CalculateField(lyr7, cluster, exp, "PYTHON_9.3","#")
            gp.CalculateField(lyr7, isolate, "0", "PYTHON_9.3","#")
            theSubClusID = theClus.split(".")[2]
            gp.CalculateField(lyr7, out_class_item, theSubClusID, "PYTHON_9.3","#")            
            gp.CalculateField(lyr7, cluster_type, "3", "PYTHON_9.3","#")
            gp.Delete(lyr7)
        else:
            # no adjacent type2 cluster, find a minCap type 1 cluster
            rows3 = gp.SearchCursor(lyr6,fldClusType + " = 1")
            rows3.reset()
            row3 = rows3.next()
            count = 0
            while row3:
                count += 1
                if count == 1:
                    minCap = row3.GetValue(fldsCap[0])
                    minClus = row3.GetValue(cluster)
                elif row3.GetValue(fldsCap[0]) < minCap:
                    minCap = row3.GetValue(fldsCap[0])
                    minClus = row3.GetValue(cluster) 
                row3 = rows3.next()
            del row3, rows3

            # If find a type1 cluster to merge, Go back to original file, change the previous clusters
            # define and add count a new cluster type 4, means mixed level of 1 and 3
            count4 += 1
            where_clause = cluster + " = \'" + minClus + "\' or " + cluster + " = \'" + theClus + "\'"
            gp.MakeFeatureLayer(inp_fc, lyr7, where_clause)
            exp = "\'4." + specialID + "." + str(count4) + "\'"

            #temp testing, will be removed
            msg = "where_clause: " + where_clause
            PrintAndWriteMessages(msg,1)
            msg = "reassign cluster membership: " + cluster + " = " + exp
            PrintAndWriteMessages(msg,1)
            
            gp.CalculateField(lyr7, cluster, exp, "PYTHON_9.3","#")
            gp.CalculateField(lyr7, isolate, "0", "PYTHON_9.3","#")
            gp.CalculateField(lyr7, out_class_item, str(count4), "PYTHON_9.3","#")            
            gp.CalculateField(lyr7, cluster_type, "4", "PYTHON_9.3","#")
            gp.Delete(lyr7)
            
        row = rows.next()
    del row, rows
    
    if gp.Exists(lyr4):
        gp.Delete(lyr4)
    if gp.Exists(lyr5):
        gp.Delete(lyr5)
    if gp.Exists(lyr6):
        gp.Delete(lyr6)
    if gp.Exists(MixedClusLyr):
        gp.Delete(MixedClusLyr)
        
    # re-dissolved mixed clusters after isolation-removal
    MixedClusFC = mixed_clusters + ".shp"
    
    if isoCount1 >= 1 or isoCount2 >= 1:
        #oldClusters = desc.path + "\\" + tmpMixedClusFC
        #PrintAndWriteMessages(oldClusters, 1)
        gp.Delete(tmpMixedClusFC)
        PrintAndWriteMessages("Old mixed clusters have been deleted and new mixed clusters are created.", 1)
        if gp.Exists(MixedClusFC):
            gp.Delete(MixedClusFC)
        gp.Dissolve_management(lyr, MixedClusFC, cluster, mixStatFlds)
        
        # replace all upper units to 000 for cluster type = 3 or 4
        gp.MakeFeatureLayer(MixedClusFC, "tmplyr", fldClusType + " >= 3")
        if long(gp.GetCount("tmplyr").GetOutput(0)) > 0:
            gp.CalculateField("tmplyr", fldUpID, "str('" + specialID + "')", "PYTHON_9.3","#")
        gp.Delete("tmplyr")
    else:
        if gp.Exists(MixedClusFC):
            gp.Delete(MixedClusFC)
        gp.Rename(tmpMixedClusFC, MixedClusFC)
        PrintAndWriteMessages("No isolated clusters are found.", 1)
    
    # rename fields in dissolved clusters, to make them the same as the original file.
    flds = gp.ListFields(MixedClusFC)
        
    for i in range(len(CapacityList)):
        if ConstraintList[i] in flds:
            pass
        else:
            gp.AddField_management(MixedClusFC, ConstraintList[i], "Double")
            exp = "!" + fldsCap[i] + "!"
            gp.CalculateField(MixedClusFC, ConstraintList[i], exp, "PYTHON_9.3","#")
            gp.DeleteField(MixedClusFC, fldsCap[i])

    if cluster_type in flds:
        pass
    else:
        gp.AddField_management(MixedClusFC, cluster_type, "Short")
        exp = "!" + fldClusType + "!"
        gp.CalculateField(MixedClusFC, cluster_type, exp, "PYTHON_9.3","#")
        gp.DeleteField(MixedClusFC, fldClusType)

    if upper_ID in flds:
        pass
    else:
        gp.AddField_management(MixedClusFC, upper_ID, "Text")
        exp = "!" + fldUpID + "!"
        gp.CalculateField(MixedClusFC, upper_ID, str(exp), "PYTHON_9.3","#")
        gp.DeleteField(MixedClusFC, fldUpID)

    if isolate in flds:
        pass
    else:
        gp.AddField_management(MixedClusFC, isolate, "Short")
        exp = "!" + fldIso + "!"
        gp.CalculateField(MixedClusFC, isolate, exp, "PYTHON_9.3","#")
        gp.DeleteField(MixedClusFC, fldIso)
    
    gp.Delete(lyr)
    ### End of tackling isolated clusters.

    # Prepare a summary report
    # summarize each type's upper unit count in mixed clusters.
    FrqByUp = "FrqUp"
    FrqByUpType = "FrqUpType"
    FrqByType = "FrqType"
    FrqByTypeMix = "FrqTypeMix"

    if gp.Exists(FrqByUp):
        gp.Delete(FrqByUp)
    if gp.Exists(FrqByUpType):
        gp.Delete(FrqByUpType)
    if gp.Exists(FrqByType):
        gp.Delete(FrqByType)
    if gp.Exists(FrqByTypeMix):
        gp.Delete(FrqByTypeMix)

    gp.Frequency_analysis(inp_fc, FrqByUp, upper_ID)
    gp.Frequency_analysis(inp_fc, FrqByUpType, upper_ID + ";" + cluster_type)
    gp.Frequency_analysis(FrqByUpType, FrqByType, cluster_type)
    gp.Frequency_analysis(MixedClusFC, FrqByTypeMix, cluster_type)

    CountOrig = long(gp.GetCount(inp_fc).GetOutput(0))
    CountUpUnit = long(gp.GetCount(FrqByUp).GetOutput(0))
    CountMixed = long(gp.GetCount(MixedClusFC).GetOutput(0))

    rows = gp.SearchCursor(FrqByTypeMix)
    rows.reset()
    row = rows.next()
    dictTypeFrqMix = {}
    while row:
        theType = row.GetValue(cluster_type)
        theCount = row.GetValue("FREQUENCY")
        dictTypeFrqMix[theType] = theCount
        row = rows.next()
    del row, rows

    CountType1 = 0
    CountType2 = 0
    CountType3 = 0
    CountType4 = 0

    if 1 in dictTypeFrqMix:        
        CountType1 = dictTypeFrqMix[1]
    if 2 in dictTypeFrqMix:
        CountType2 = dictTypeFrqMix[2]
    if 3 in dictTypeFrqMix:
        CountType3 = dictTypeFrqMix[3]
    if 4 in dictTypeFrqMix:
        CountType4 = dictTypeFrqMix[4]

    rows = gp.SearchCursor(FrqByType)
    rows.reset()
    row = rows.next()
    dictTypeFrq = {}
    while row:
        theType = row.GetValue(cluster_type)
        theCount = row.GetValue("FREQUENCY")
        dictTypeFrq[theType] = theCount
        row = rows.next()
    del row, rows

    CntUpperT1 = 0 
    CntUpperT2 = 0
    CntUpperT3 = 0
    CntUpperT4 = 0

    if 1 in dictTypeFrq:         
        CntUpperT1 = dictTypeFrq[1]
    if 2 in dictTypeFrq:
        CntUpperT2 = dictTypeFrq[2]
    if 3 in dictTypeFrq:
        CntUpperT3 = dictTypeFrq[3]
    if 4 in dictTypeFrq:
        CntUpperT4 = dictTypeFrq[4]

    msg = "\n" + "Result summary: " + "\n" + \
          "The number of original lower-level units is " + str(CountOrig) + ".\n" \
          "The number of original upper-level units is " + str(CountUpUnit) + ".\n" \
          "The number of final mixed clusters is " + str(CountMixed) + ", including \n" + \
          " - " + str(CountType1) + " type1 clusters (single or multi lower-level units) " + \
                "from " + str(CntUpperT1) + " upper units.\n" + \
          " - " + str(CountType2) + " type2 clusters (single upper-level unit) " + \
                "from " + str(CntUpperT2) + " upper units.\n" + \
          " - " + str(CountType3) + " type3 clusters (multi upper-level units) " + \
                "from " + str(CntUpperT3) + " upper units.\n" + \
          " - " + str(CountType4) + " type4 clusters (mixed upper and lower level units) " + \
                "from " + str(CntUpperT4) + " upper units.\n"
    PrintAndWriteMessages(msg,1)

    keepPct = (float(CntUpperT1) + float(CntUpperT2)) / float(CountUpUnit) * 100
    msg = "\n" + "Mixed-level clustering is done! \n" + \
          "The boundaries of " + str(keepPct) + "% upper-level units are preserved."
    PrintAndWriteMessages(msg,1)
    
    # All three scenarios are done.
    if gp.Exists(tmpTbUpper):
        gp.Delete(tmpTbUpper)
    if gp.Exists(tmpTbSumWtAttri):
        gp.Delete(tmpTbSumWtAttri)
    if gp.Exists(FrqByUpType):
        gp.Delete(FrqByUpType)
    if gp.Exists(FrqByType):
        gp.Delete(FrqByType)
    if gp.Exists(FrqByTypeMix):
        gp.Delete(FrqByTypeMix)
    
    #Set the derived output when the script is done
    #gp.SetParameterAsText(8,lyrList)
    
except:
    # Return any python specific errors as well as any errors from the geoprocessor
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
            str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
    PrintAndWriteMessages(pymsg,2)

    msgs = "GP ERRORS:\n" + gp.GetMessages(2) + "\n"
    PrintAndWriteMessages(msgs,2)
