#*****************************************************************************************
#This script is modifed to use a funciton to perform all it used to do, so it can be called
# from another Python scrip.
#
#This script is developed based on ESRI free online "Partitioning Tools"
# Major Modifications:
# 1) Rook neighborhood is included int he considereation to mitigate the "jumping" patterns in the original script
# 2) Capacity is changed from <= to just > to accomodate practical objectives
# 3) multiple capacities are allowed.
#
#Description: 
#      This script assigns a class number to features in a feature class based on accumulated
#      attribute values, a visit order and capacity. This script is similar to the ArcInfo 
#      workstation COLLOCATE command
#Inputs:
#      1)Input feature class
#      2)The field containing the order values for the feature
#      3)The field specifying the accumulated attribute for the feature
#      4)The numeric value specifying the capacity or size of the class
#      5)The new field name which will contain the class number assigned by this tool.
#Outputs:
#      1)Input feature class as derived output with the newly added field
#*****************************************************************************************

def OneLevelClustering(inp_fc, order_item, constraint_list, capacity_list, out_class_item, isolate):

    #prints a GP message and writes the same message to a log file
    def PrintAndWriteMessages(msg,severity=0):
        if severity == 0:
            gp.AddMessage(msg)
        elif severity == 1:
            gp.AddWarning(msg)
        elif severity == 2:
            gp.AddError(msg)
        #logfile.write(msg + "\n")
        
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

    #Only run the function if there are more than 2 features.
    if long(gp.GetCount(inp_fc).GetOutput(0)) >=2:
        
        try:
            #Create a log file with messages in the same location as the script
            #logfile = open(os.path.splitext(sys.argv[0])[0] + "_log.txt","w",0)

    ##        #Get the inputs
    ##        inp_fc = gp.GetParameterAsText(0)
    ##        order_item = gp.GetParameterAsText(1)
    ##    ##    transfer_item1 = gp.GetParameterAsText(2)
    ##    ##    capacity1 = float(gp.GetParameterAsText(3))
    ##    ##    transfer_item2 = gp.GetParameterAsText(4)    #Newly added
    ##    ##    capacity2 = float(gp.GetParameterAsText(5))  #Newly added
    ##    ##    cluster_type = gp.GetParameterAsText(6)
    ##        #modified, to increase the flexibility, use two lists to input any number of constraints.
    ##        constraint_list = gp.GetParameterAsText(2)
    ##        capacity_list = gp.GetParameterAsText(3)
    ##        out_class_item = gp.GetParameterAsText(4)
    ##        isolate = gp.GetParameterAsText(5)
            
            #parse the input parameter strings to lists
            ConstraintList = constraint_list.split(';')
            CapacityList = capacity_list.split(';')

        ##    msg = "Number of constraints is " + str(len(ConstraintList))
        ##    PrintAndWriteMessages(msg,0)

            #gp.AddWarning("DataType: " + desc.DataType)
            #gp.AddWarning("DatasetType: " + desc.DatasetType)
            #gp.AddWarning("CatalogPath: " + desc.CatalogPath)
            #fc_path = desc.CatalogPath
            
        ##    #Get a feature count to set up the progressor
        ##    tot_features = long(gp.GetCount(inp_fc).GetOutput(0))
        ##    
        ##    #Create a progressor
        ##    gp.SetProgressor("step","Executing Collocate",0,tot_features + 1,1)
            
        ##    msg = "Adding the class field " + out_class_item
        ##    gp.SetProgressorLabel(msg)
        ##    PrintAndWriteMessages(msg,0)
            #Validate the output field name for the workspace
            out_class_item = gp.ValidateFieldName(out_class_item,os.path.dirname(inp_fc))
            
            #Add the new field. If the field already exists, AddField has a warning
            result = gp.AddField_management(inp_fc,out_class_item,"Double")
    ##        if result.MaxSeverity == 1:
    ##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
    ##            PrintAndWriteMessages(msg,1)
    ##        gp.SetProgressorPosition()

            #Validate the isolatte field name for the workspace
            isolate = gp.ValidateFieldName(isolate,os.path.dirname(inp_fc))
            
            #Add the new field. If the field already exists, AddField has a warning
            result = gp.AddField_management(inp_fc,isolate,"Short")
    ##        if result.MaxSeverity == 1:
    ##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
    ##            PrintAndWriteMessages(msg,1)
    ##        gp.SetProgressorPosition()
            
            gp.CalculateField(inp_fc,isolate, 0,"PYTHON_9.3","#")
            
    ##        msg = "Calculating class values for features....."
    ##        gp.SetProgressorLabel(msg)
    ##        PrintAndWriteMessages(msg,0)
            
            #Calculate the Class field
            #Get an update cursor such that values are in ascending order based on OrderItem field

            # start of new codes

        # new code, put all needed fields in a list then convert to a string
            fields = [order_item]
            for constraint in ConstraintList:
                fields.append(constraint)
            fields = ";".join(fields)
            
            # use a field to record whether a recorded in included in the cluster or not
            #Add the new field. If the field already exists, AddField has a warning
            result = gp.AddField_management(inp_fc,"included","Short")
    ##        if result.MaxSeverity == 1:
    ##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
    ##            PrintAndWriteMessages(msg,1)
    ##        gp.SetProgressorPosition()
            gp.CalculateField_management(inp_fc,"included",0,"PYTHON_9.3","#")

            where_clause = "included = 0" 
            # end of new codes        

            #Get the OID field name
            desc = gp.Describe(inp_fc)
            oid_fld = desc.OIDFieldName
        ##    msg = "oid_fld = " + oid_fld
        ##    gp.SetProgressorLabel(msg)
        ##    PrintAndWriteMessages(msg,0)

            # Start of new codes
            # Get the path and full name of the input feature class
            gp.Workspace = desc.path
            fullInp_fc = desc.BaseName + "." + desc.Extension 
        ##    msg = "The path (workspace) is " + gp.Workspace
        ##    gp.SetProgressorLabel(msg)
        ##    PrintAndWriteMessages(msg,0)
        ##    msg = "The full name is " + fullInp_fc
        ##    gp.SetProgressorLabel(msg)
        ##    PrintAndWriteMessages(msg,0)
            
    ###########***### skip this part if it's a function, since TheID is calcualted in the original feature class.
    ##        # use a field to copy FID/OID to the new integer field, because FID/OID cannot be used in GenerateSpatialWeightsMatrix
    ##        result = gp.AddField_management(inp_fc,"TheID","Short")
    ##        if result.MaxSeverity == 1:
    ##            msg = result.GetMessages(1).split(':')[1].lstrip() + ". Existing values will be overwritten."
    ##            PrintAndWriteMessages(msg,1)
    ##        gp.SetProgressorPosition()
    ##        exp = "!" + oid_fld + "!"
    ##        gp.CalculateField_management(inp_fc,"TheID", exp, "PYTHON_9.3","#")

            # Generate a spatial weight matrix
            gp.OverWriteOutput = True
            swmTab = "tmpswm.swm"
            dbfTab = "tmpswm.dbf"
            if gp.Exists(swmTab):
                gp.Delete(swmTab)
            if gp.Exists(dbfTab):
                gp.Delete(dbfTab)        
            gp.GenerateSpatialWeightsMatrix_stats(fullInp_fc, "TheID", swmTab, "CONTIGUITY_EDGES_ONLY", "EUCLIDEAN", "1", "", "","NO_STANDARDIZATION", "") 
            gp.ConvertSpatialWeightsMatrixToTable(swmTab, dbfTab)
            # end of new codes

            tot_rec = long(gp.GetCount(inp_fc).GetOutput(0))
        ##    msg = "Total count of records is " + str(tot_rec)
        ##    PrintAndWriteMessages(msg,0)

        ##    # Get the last oid 
        ##    rows = gp.SearchCursor(inp_fc,where_clause,"",fields,order_item + " A")
        ##    rows.reset()
        ##    row = rows.next()
        ##    while row:
        ##        lastoid = row.GetValue(oid_fld)
        ##        row = rows.Next()
        ##    del rows
            
            rows = gp.UpdateCursor(inp_fc,where_clause,"",fields,order_item + " A")
            rows.reset()
            row = rows.next()
            
        ##    acc_capacity1 = 0
        ##    acc_capacity2 = 0
            acc_capacity = []
            for i in range(len(ConstraintList)):
                acc_capacity.append(0)
                
            class_value = 1
            count = 0
            roundCount = 0
            newRoundCount = tot_rec
            orphanIteration = 0
            #Store the class value and the list of OIDs in that class in a dict.
            classValueDict = {class_value : []}

            while row:
                #Should use TheID instead of thisoid to search, because sometimes TheID <> thisoid
                #thisoid = row.GetValue(oid_fld)
                thisTheID = row.GetValue("TheID")
                    
                count += 1 #counter for records being processed
                roundCount += 1 #counter for this round of search
        ##        cur_capacity1 = row.GetValue(transfer_item1)
        ##        cur_capacity2 = row.GetValue(transfer_item2)
                cur_capacity = []
                for i in range(len(ConstraintList)):
                    #msg = "The current constraint is: " +  str(ConstraintList[i]) 
                    #PrintAndWriteMessages(msg,1)
                    cur_capacity.append(row.GetValue(ConstraintList[i]))
                
                ### Start of new codes
                if count == 1:
                    isRookNbr = True
                    row.SetValue("included", 1)
                    rows.UpdateRow(row)
                    
        ##            msg = "This is the first record, and the TheID is " +  str(thisTheID)      
        ##            gp.SetProgressorLabel(msg)
        ##            PrintAndWriteMessages(msg,0)
                        
                # Starting from the second polygon, make sure the new polygon is a rook neighbor (share boundary) of one of the current cluster members.
                if count > 1:
                    isRookNbr = False
                    # the first member in each new cluster is always in
                    if len(classValueDict[class_value]) == 0:
                        row.SetValue("included", 1)
                        rows.UpdateRow(row)
                        isRookNbr = True

        ##                msg = "This is the first record in cluster [" + str(class_value) + "], and the TheID is " +  str(thisTheID)      
        ##                gp.SetProgressorLabel(msg)
        ##                PrintAndWriteMessages(msg,0)
                            
                    else:
                        swmRows = gp.SearchCursor(dbfTab,"TheID = " + str(thisTheID))
                        swmRows.reset()
                        swmRow = swmRows.next()
                        
                        while swmRow:
        ##                    msg = "TheID, NID and classValueDict[" + str(class_value) + "] are " + str(thisTheID) + ", "  \
        ##                          + str(swmRow.GetValue("NID")) + ", " + '(' + ",".join(classValueDict[class_value]) + ')'      
        ##                    PrintAndWriteMessages(msg,0)
                             
                            if str(swmRow.GetValue("NID")) in classValueDict[class_value]:
        ##                        msg = "Yes, TheID = " + str(thisTheID) + " is a Rook neighbor of the current cluster. It's in."
        ##                        PrintAndWriteMessages(msg,0)

                                row.SetValue("included", 1)
                                rows.UpdateRow(row)
                                isRookNbr = True
                                break
                            del swmRow
                            swmRow = swmRows.next()
                        del swmRows

                ### End of new codes

                # new code, the "if included == 1" condition
                if row.GetValue("included") == 1:
        ##            acc_capacity1 += cur_capacity1
        ##            acc_capacity2 += cur_capacity2
                    for i in range(len(ConstraintList)):
                        acc_capacity[i] += cur_capacity[i]           
                   
                    #start of new codes
                    #Accumulate the transfer item till it is equal or just greater than capacity
                    classValueDict[class_value].append(str(row.GetValue("TheID")))
        ##            msg = "A new TheID [" + str(row.GetValue("TheID")) + "] is appended to cluster[" + str(class_value) + "]."      
        ##            PrintAndWriteMessages(msg,0)
                  
                    # modified to take more constraints.
                    satisfyAll = 1
                    for i in range(len(ConstraintList)):
                        if float(acc_capacity[i]) >= float(CapacityList[i]):
                            satisfyAll = satisfyAll * 1
        ##                    msg = "acc_capacity[" + str(i) + "]=" + str(acc_capacity[i]) + " >= CapacityList[" + str(i) + "]=" + str(CapacityList[i])      
        ##                    PrintAndWriteMessages(msg,0)
                        else:
                            satisfyAll = satisfyAll * 0
        ##                    msg = "acc_capacity[" + str(i) + "]=" + str(acc_capacity[i]) + " < CapacityList[" + str(i) + "]=" + str(CapacityList[i])      
        ##                    PrintAndWriteMessages(msg,0)                    

        ##            msg = "The count and satisfyAll are " + str(count) + " and " + str(satisfyAll)      
        ##            PrintAndWriteMessages(msg,0)
                            
                    if satisfyAll == 1 and count < tot_rec: 
                    #if acc_capacity1 >= capacity1 and acc_capacity2 >= capacity2 and count < tot_rec:
        ##                msg = "ClassValueDict[" + str(class_value) + "] are " + '(' + ",".join(classValueDict[class_value]) + ')'      
        ##                PrintAndWriteMessages(msg,0)
                        #acc_capacity1 = 0
                        #acc_capacity2 = 0
                        for i in range(len(ConstraintList)):
                            acc_capacity[i] = 0
                        class_value += 1
                        classValueDict[class_value] = []
        ##                msg = "A new cluster is initiated, ClassValueDict[" + str(class_value) + "]."      
        ##                PrintAndWriteMessages(msg,0)
                        
                    if count == tot_rec:
        ##                msg = "ClassValueDict[" + str(class_value) + "] are " + '(' + ",".join(classValueDict[class_value]) + ')'      
        ##                PrintAndWriteMessages(msg,0)
                        msg = ""      
                        PrintAndWriteMessages(msg,0)
                        
                    #update cursor and the count for the next round of search
                    rows = gp.UpdateCursor(inp_fc,where_clause,"",fields,order_item + " A")
                    rows.Reset()
                    newRoundLyr = "newroundlyr"
                    gp.MakeFeatureLayer(inp_fc,newRoundLyr,where_clause)
                    newRoundCount = long(gp.GetCount(newRoundLyr).GetOutput(0))
                    gp.Delete_management(newRoundLyr)
                    roundCount = 0
                    
                else:
                    count -= 1
        ##            msg = "The TheID, included, cur_capacity1, acc_capacity1, classvalue, count, thisTheID and isRookNbr are " + str(row.GetValue("TheID")) \
        ##                  + ", " + str(row.GetValue("included")) + ", " + str(cur_capacity1) + ", " + str(acc_capacity1) + ", " + str(class_value) \
        ##                  + ", " + str(count) + ", " + str(thisTheID) + ", " + str(isRookNbr)               
        ##            gp.SetProgressorLabel(msg)
        ##            PrintAndWriteMessages(msg,0)

                # Now, deal with "orphans" - after the first sequential search by order value, isolated units left with included = 0
                # Decide how many iterations wanted in looking for "orphans".  Pull out all included = 0 and go back to while row:
                
                #if thisoid == lastoid:
                if roundCount == newRoundCount:
                    orphanlyr = "orphanlyr"
                    gp.MakeFeatureLayer(inp_fc,orphanlyr,where_clause)
                    orphanCount = long(gp.GetCount(orphanlyr).GetOutput(0))
                    gp.Delete_management(orphanlyr)
         
                    #If the cursor is not empty, then start a new cluster
                    if orphanCount > 0:
                        orphanIteration += 1
        ##                msg = "Orphan iteration starts and the orphan count is " + str(orphanCount) + ".  The orphan iteration is " + str(orphanIteration)
        ##                PrintAndWriteMessages(msg,0)
        ##                msg = "Current class_value and length are " + str(class_value) + ", and " + str(len(classValueDict[class_value]))
        ##                PrintAndWriteMessages(msg,0)
                        if len(classValueDict[class_value]) > 0:  #if the previous cluster is not empty, then start a new cluster.
        ##                    msg = "ClassValueDict[" + str(class_value) + "] are " + '(' + ",".join(classValueDict[class_value]) + ')'      
        ##                    PrintAndWriteMessages(msg,0)
        ##                    acc_capacity1 = 0
        ##                    acc_capacity2 = 0
                            for i in range(len(ConstraintList)):
                                acc_capacity[i] = 0                    
                            class_value += 1
                            classValueDict[class_value] = []
        ##                msg = "The new cluster formed by orphans is classValueDict[" + str(class_value) + "]."
        ##                PrintAndWriteMessages(msg,0)
                        rows = gp.UpdateCursor(inp_fc,where_clause,"",fields,order_item + " A")
                        rows.Reset()
                        row = rows.Next()
                        newRoundLyr = "newroundlyr"
                        gp.MakeFeatureLayer(inp_fc,newRoundLyr,where_clause)
                        newRoundCount = long(gp.GetCount(newRoundLyr).GetOutput(0))
                        gp.Delete_management(newRoundLyr)
                        roundCount = 0
                    else:
                        del row
                        row = rows.Next()

                # keep moving if it's not the last OID
                else:
                    del row
                    row = rows.Next()
                    
        ##	#Update the progressor after processing 5% rows
        ##        if count % (int(0.05 * tot_features)) == 0:
        ##            #msg = "Completed processing %s out of %s features" % (count,tot_features)
        ##            #PrintAndWriteMessages(msg,0)
        ##            gp.SetProgressorPosition(count / 2.0)

            del rows
            
    ##        msg = "Assigning class values to features......"
    ##        gp.SetProgressorLabel(msg)
    ##        PrintAndWriteMessages(msg,0)
                    
        ##    position = tot_features / 2.0
            #Update the class values by first making a selection set and then using Calculate field.
            for k in classValueDict.keys():
                where_clause = "TheID" + " IN " + '(' + ",".join(classValueDict[k]) + ')'
                lyr = "inp_fc_lyr"
                gp.MakeFeatureLayer(inp_fc,lyr,where_clause)
                gp.CalculateField(lyr,out_class_item,k,"PYTHON_9.3","#")
                gp.Delete_management(lyr)
        ##        position += len(classValueDict[k]) /2.0
        ##        gp.SetProgressorPosition(position)

            # start of new codes
            # If a cluster has a subtotal < capacity, then merge it to an adjacent cluster to make it work.

            # Execute the Summary Statistics tool using the SUM option
            tmptb = "sum_tmp"
            if gp.Exists(tmptb):
                gp.Delete(tmptb)
            #modified to inrease flexibility of constraints.
            #StatFields = transfer_item1 + " SUM;" + transfer_item2 + " SUM"
            StatFields = ""
            for i in range(len(ConstraintList)):
                StatFields = StatFields + ConstraintList[i] + " SUM;"
            StatFields = StatFields.rstrip(';')
            gp.Statistics_analysis(inp_fc, tmptb, StatFields, out_class_item)

            # Get a list of fields from the new summary table.
            flds = gp.ListFields(tmptb)
            # Retrieve the field with the total sum value.
            fldcount = 0
            fldsum = []
            for fld in flds:
        ##        msg = "A field in the sum_tmp table is: " + fld.Name
        ##        PrintAndWriteMessages(msg,0)
                if fld.Name.__contains__("SUM_"):
                    #modified to increase flexibility of consrtaints.
                    fldsum.append(fld.Name)
                    fldcount += 1

            # Open a Search Cursor using field name.
            #where_clause3 = fld1 + " < " + str(capacity1) + " or " + fld2 + " < " + str(capacity2)
            #modified to increase flexibility of consrtaints.
            where_clause3 = ""
            for i in range(fldcount):
                where_clause3 = where_clause3 + fldsum[i] + " < " + str(CapacityList[i]) + " or "
            where_clause3 = where_clause3.rstrip(' or ')

            rows = gp.SearchCursor(tmptb, where_clause3)
            rows.Reset()
            row = rows.next()
            #clusAdjust = 0
            
            #Create an empty list to record whether a cluster needs merge or not.
            clusAdjList = []
            isoClus = []
            
            while row:                
                FoundIt = False
                foundCount = 0
                # which previous cluster is a rook neighbor to the unsatisfied cluster and has a min subtotal to reach capacities?
                currentClus = row.GetValue(out_class_item)
                theCluster = currentClus
                where_clause4 = "TheID IN " + '(' + ",".join(classValueDict[currentClus]) + ')'
                swmRows = gp.SearchCursor(dbfTab, where_clause4)
                swmRows.reset()
                swmRow = swmRows.next()
                        
                while swmRow:
                    for i in range(class_value, 0, -1):
                        #look for other clusters than itself
                        if i <> currentClus:             
                            if str(swmRow.GetValue("NID")) in classValueDict[i]:
                                # check to see if the combined capacities from the two clusters meet the criteria
                                #cap1a = row.GetValue(fld1)
                                #cap2a = row.GetValue(fld2)
                                # modified to increase constraints flexibility
                                capA = []
                                for j in range(len(ConstraintList)):
                                    capA.append(row.GetValue(fldsum[j]))

                                foundRows = gp.SearchCursor(tmptb, out_class_item + " = " + str(i))
                                foundRows.reset()
                                foundRow = foundRows.Next()
                                
                                #cap1b = foundRow.GetValue(fld1)
                                #cap2b = foundRow.GetValue(fld2)
                                # modified to increase constraints flexibility
                                capB = []
                                for j in range(len(ConstraintList)):
                                    capB.append(foundRow.GetValue(fldsum[j]))
                                
                                del foundRow
                                del foundRows

                                #newcap1 = cap1a + cap1b
                                #newcap2 = cap2a + cap2b

                                # modified to increase constraints flexibility
                                newcap = []
                                for j in range(len(ConstraintList)):
                                    newcap.append(capA[j] + capB[j])
                                    
                                newSatisfyAll = 1
                                for j in range(len(ConstraintList)):
                                    if float(newcap[j]) >= float(CapacityList[j]):
                                        newSatisfyAll = newSatisfyAll * 1
                                    else:
                                        newSatisfyAll = newSatisfyAll * 0

                                #if newcap1 >= capacity1 and newcap2 >= capacity2:
                                if newSatisfyAll == 1:        
                                    foundCount += 1
                                    if foundCount == 1:
                                        mincap = []
                                        for k in range(len(ConstraintList)):
                                            mincap.append(newcap[k])
                                        #mincap1 = newcap1
                                        #mincap2 = newcap2
                                        FoundIt = True
                                        theCluster = i
                                        break
                                    #elif foundCount > 1 and newcap1 < mincap1 and newcap2 < mincap2:
                                    elif foundCount > 1:
                                        minSatisfyAll = 1
                                        for j in range(len(ConstraintList)):
                                            if float(newcap[j]) < float(mincap[j]):
                                                minSatisfyAll = minSatisfyAll * 1
                                            else:
                                                minSatisfyAll = minSatisfyAll * 0

                                        if  minSatisfyAll == 1:    
                                            #mincap1 = newcap1
                                            #mincap2 = newcap2
                                            for k in range(len(ConstraintList)):
                                                mincap[k] = newcap[k]
                                            FoundIt = True
                                            theCluster = i
                                            break
                                    
                    del swmRow
                    swmRow = swmRows.next()
                del swmRows
               
                #for every unmet cluster
        ##        msg = "The current searched cluster is " + str(currentClus) + ", and FoundIt = " + str(FoundIt)
        ##        PrintAndWriteMessages(msg,0)

                sumvalues = ""
                for i in range(len(ConstraintList)):
                    sumvalues = sumvalues + str(row.GetValue(fldsum[i])) + ", "
                sumvalues = sumvalues.rstrip(', ')
                    
                where_clause5 = out_class_item + " = " + str(currentClus)
                lyr2 = "unmetClus_lyr"
                gp.MakeFeatureLayer(inp_fc,lyr2,where_clause5)
                    
                if FoundIt == True:              
                    #clusAdjust += 1
                    gp.CalculateField(lyr2,out_class_item, theCluster,"PYTHON_9.3","#")
                    gp.CalculateField(lyr2,isolate, 0,"PYTHON_9.3","#")
        ##            msg = "The unmet cluster [" + str(currentClus) + "]'s capacities are " + sumvalues 
        ##            PrintAndWriteMessages(msg,0)
        ##            msg = "Yes, a Rook neighbor of the unmet cluster [" + str(currentClus) + \
        ##                      "] is found in a previous cluster [" + str(theCluster) + "]." + \
        ##                   " Cluster members are adjsuted accordingly."
        ##            PrintAndWriteMessages(msg,0)
                else:
                    # previous approach
        ##            msg = "No,the unmet cluster [" + str(currentClus) + \
        ##                      "] does not have an adjacent cluster to merge and it remains 'isolated and unmet."
        ##            PrintAndWriteMessages(msg,0)
        ##            # assign a negative sign to the cluster type to indicate its "orphan" status.
        ##            exp = "- !" + cluster_type + "!"
        ##            gp.CalculateField(lyr2,cluster_type, exp,"PYTHON_9.3","#")
                    gp.CalculateField(lyr2,isolate, 1,"PYTHON_9.3","#")
                    
                    # new approach to force the cluster membership by aggregating all isolated ones or
                    # by merging to the nearest met cluster.  Record it here and process it out side of the while loop.
                    isoClus.append(currentClus)
                    
                gp.Delete_management(lyr2)    
                clusAdjList.append(FoundIt)
                del row
                row = rows.next()
            del rows

            #after the merging,  adjust all involving cluster members.  Continue to use rows generated from where_clause3
            #where_clause3 = fld1 + " < " + str(capacity1) + " or " + fld2 + " < " + str(capacity2)
            rows = gp.SearchCursor(tmptb, where_clause3)
            rows.Reset()
            row = rows.Next()
            clusAdjust = 0
            listInd = 0
            while row:
                if clusAdjList[listInd] == True:
                    where_clause6 = out_class_item + " > " + str(row.GetValue(out_class_item) - clusAdjust)
                    lyr3 = "adjClus_lyr"
                    gp.MakeFeatureLayer(inp_fc,lyr3,where_clause6)
                    exp = "!" + out_class_item + "! - 1"
            ##        msg = where_clause6 + ":  the calculation expression is " + str(out_class_item) + " = " + exp
            ##        PrintAndWriteMessages(msg,0)
                    gp.CalculateField(lyr3,out_class_item, exp,"PYTHON_9.3","#")
                    gp.Delete_management(lyr3)
                    clusAdjust += 1
                listInd += 1
                del row
                row = rows.Next()
            del rows
            
            gp.Delete(tmptb)
            gp.Delete(swmTab)
            gp.Delete(dbfTab)
            
    ##        msg = "Clustering at this level is done. After adjustment, the number of subclusters is " \
    ##              + str(class_value - clusAdjust) + " including " + str(len(isoClus)) + \
    ##              " remained unsatisfied isolated clusters."
    ##        gp.SetProgressorLabel(msg)
    ##        PrintAndWriteMessages(msg,0)
            # end of new codes
            
            #Set the output to be same as input
            #Useful to show the output when the tool is used in model builder
            #gp.SetParameterAsText(6,inp_fc)
        except:
            # Return any python specific errors as well as any errors from the geoprocessor
            tb = sys.exc_info()[2]
            tbinfo = traceback.format_tb(tb)[0]
            pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                    str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
            PrintAndWriteMessages(pymsg,2)

            msgs = "GP ERRORS:\n" + gp.GetMessages(2) + "\n"
            PrintAndWriteMessages(msgs,2)

    #If there are less than 2 features:
    else:
        msgs = "\nOne-level clustering function is not performed because the number of features is less than 2."
        PrintAndWriteMessages(msgs,1)
        
