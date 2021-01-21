#*****************************************************************************************
#This script is modifed to use a funciton to perform all it used to do, so it can be called
# from another Python scrip.
#
#Description: 
#      This scripts implements the spatial order command from arcinfo workstation.
#      It asigns order values to features based on their x,y location. The net effect is
#      spatially sorting input features such that features that are close have similar
#      order values
#Inputs:
#      1)Input feature class
#      2)Input spatial order field name to create the new double field to store order values
#      
#Outputs:
#      1) Input feature class as derived output
#*****************************************************************************************

def ClusteringOrder(inp_fc, PeanoOrder_fld, AttriOrder_fld, NAttriOrder_fld, Order_fld, Attri_list, Wt_list, Pct_Peano):
    
    #prints a GP message and writes the same message to a log file
    def PrintAndWriteMessages(msg,severity=0):
        if severity == 0:
            gp.AddMessage(msg)
        elif severity == 1:
            gp.AddWarning(msg)
        elif severity == 2:
            gp.AddError(msg)
        #logfile.write(msg + "\n")

    #return the fractional part from a double number
    def GetFractionalPart(dbl):
        return dbl - math.floor(dbl)

    #return the peano curve coordinate for a given x,y value
    def Peano(x,y,k):
        if (k == 0 or (x==1 and y==1)):
            return 0.5
        if x <= 0.5:       
            if y <= 0.5:
                quad=0
            else: 
                quad=1
        elif y <= 0.5:
            quad = 3
        else: 
            quad = 2
        subpos = Peano(2 * abs(x - 0.5), 2 * abs(y - 0.5), k-1)
        
        if(quad == 1 or quad == 3):
            subpos = 1 - subpos
      
        return GetFractionalPart((quad + subpos - 0.5)/4.0)
        
    #Import the modules and create the geoprocessor
    import arcgisscripting, sys,os, traceback,math
    gp = arcgisscripting.create(9.3)

    #Use the lowest available license
    for product in ['Engine','ArcView', 'ArcEditor', 'EngineGeoDB','ArcInfo', 'ArcServer']:
        if gp.CheckProduct(product).lower() == 'available':
            gp.SetProduct(product)
            break
    gp.OverwriteOutput = True
    try:
        #Create a log file with messages in the same location as the script
        #logfile = open(os.path.splitext(sys.argv[0])[0] + "_log.txt","w",0)

##This part is in the standalone python script but should be removed in a function.
##        #Get the inputs
##        inp_fc = gp.GetParameterAsText(0)
##        PeanoOrder_fld = gp.GetParameterAsText(1)
##        AttriOrder_fld = gp.GetParameterAsText(2)
##        NAttriOrder_fld = gp.GetParameterAsText(3)
##        Order_fld = gp.GetParameterAsText(4)
##        Attri_list = gp.GetParameterAsText(5)
##        Wt_list = gp.GetParameterAsText(6)
##        Pct_Peano = float(gp.GetParameterAsText(7))
        Pct_Attri = 100 - Pct_Peano
                    
    ##    #Get a feature count to set up the progressor
    ##    tot_features = long(gp.GetCount(inp_fc).GetOutput(0))
    ##    
    ##    #Create a progressor
    ##    gp.SetProgressor("step","Computing Spatial Order",0,tot_features + 1,1)
        
        #Add the new field if it does not exist, else overwrite existing values
##        msg = "Adding spatial order fields " + PeanoOrder_fld + ", " + AttriOrder_fld + ", " + NAttriOrder_fld+ ", " + Order_fld
##        gp.SetProgressorLabel(msg)
##        PrintAndWriteMessages(msg,0)

        #First Validate the field name
        PeanoOrder_fld = gp.ValidateFieldName(PeanoOrder_fld,os.path.dirname(inp_fc))
        AttriOrder_fld = gp.ValidateFieldName(AttriOrder_fld,os.path.dirname(inp_fc))
        NAttriOrder_fld = gp.ValidateFieldName(NAttriOrder_fld,os.path.dirname(inp_fc))
        Order_fld = gp.ValidateFieldName(Order_fld,os.path.dirname(inp_fc))
        

    ##Don't delete previous created order_fld, so that previous values stay.  
    ##    ##Get a list of all existing fields
    ##    allFlds = [fld.Name.lower() for fld in gp.ListFields(inp_fc)]
    ##    if order_fld.lower() in allFlds:
    ##        msg = "Deleting the existing field " + order_fld 
    ##        PrintAndWriteMessages(msg,1)
    ##        gp.DeleteField(inp_fc,order_fld)
        
        #Add the double field
        result = gp.AddField(inp_fc,PeanoOrder_fld,"DOUBLE")
##        if result.MaxSeverity == 1:
##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
##            PrintAndWriteMessages(msg,1)
##        gp.SetProgressorPosition()
        
        result = gp.AddField(inp_fc,AttriOrder_fld,"DOUBLE")
##        if result.MaxSeverity == 1:
##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
##            PrintAndWriteMessages(msg,1)
##        gp.SetProgressorPosition()

        result = gp.AddField(inp_fc,NAttriOrder_fld,"DOUBLE")
##        if result.MaxSeverity == 1:
##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
##            PrintAndWriteMessages(msg,1)
##        gp.SetProgressorPosition()
        
        result = gp.AddField(inp_fc,Order_fld,"DOUBLE")
##        if result.MaxSeverity == 1:
##            msg = result.GetMessages(1).split(':')[1].lstrip() + "Existing values will be overwritten."
##            PrintAndWriteMessages(msg,1)
##        gp.SetProgressorPosition()

##        msg = "Computing the Peano curve coordinates for input features"
##        gp.SetProgressorLabel(msg)
##        PrintAndWriteMessages(msg,0)
        #Get the extent for the feature class
        desc = gp.Describe(inp_fc)
        gp.Workspace = desc.path
    ##    #use the feature class extent even if the input is a feature layer
    ##    desc = gp.Describe(desc.CatalogPath)

        #Just in case, conver the input feature class layer to feature class, so the extent will be adjusted to the right values.
        #Reason:  a feature class layer's extent always points back to the reference feature class, in spite of the fact that the layer is
        # only a subset of all the features.
        theRealFC = "theRealFC"
        gp.FeatureClassToFeatureClass(inp_fc, gp.Workspace, theRealFC)
        desc = gp.Describe(theRealFC + ".shp")
        
        extent  = desc.Extent
        xmin = extent.XMin
        ymin = extent.YMin
        xmax = extent.XMax
        ymax = extent.YMax

        #testing 
##        msg = "The current working extent of Peano curve calculation is " + str(xmin) + ", " + str(ymin) + ", " + str(xmax) + ", " + str(ymax) + ". "
##        PrintAndWriteMessages(msg,1)
        
        #compute some constants to scale the coordinates to unit square before calling Peano
        dx = xmax - xmin
        dy = ymax - ymin
        if dx >= dy:
            offsetx = 0.0
            offsety = (1.0 - dy / dx)/ 2.0
            scale = dx
        else:
            offsetx = (1.0 - dx / dy)/ 2.0
            offsety = 0.0
            scale = dy
        
        #If the input features are lines or polygons get their centroids
        useCentroids = False
        if desc.ShapeType.lower() in ['polyline','polygon']:
            useCentroids = True
            
        #Get each point and compute it's peano curve coordinate and store it back
        #Get an update cursor
        rows = gp.UpdateCursor(inp_fc)
        rows.Reset()
        row = rows.Next()
        while row:
            #Get the X,Y coordinate for each feature
            if useCentroids:
                pnt = row.shape.TrueCentroid
            else:
                pnt = row.shape.GetPart(0)
            unitx = (pnt.X - xmin) / scale + offsetx
            unity = (pnt.Y - ymin) / scale + offsety
            peanoPos = Peano(unitx, unity, 32)
            row.SetValue(PeanoOrder_fld,peanoPos)
            rows.UpdateRow(row)
            gp.SetProgressorPosition()
            row = rows.Next()
        del row, rows
        gp.Delete(theRealFC + ".shp")

        #Calculate weighted aggregated attribute scores, scale the values to 0-1, then calcualte the order values. 
        #Calculate weighted aggregated attribute scores and find min and max values.
        AggrWt = 0
        for wt in Wt_list.split(';'):
            AggrWt = AggrWt + float(wt)
            
        rows = gp.UpdateCursor(inp_fc)
        rows.Reset()
        j = 0
        row = rows.Next()
        while row:
            AggrScore = 0
            i = 0
            for attri in Attri_list.split(';'):
                wt = Wt_list.split(';')[i]
                AggrScore = AggrScore + row.GetValue(attri) * float(wt)       
                i = i + 1

            AggrScore = AggrScore / AggrWt
            row.SetValue(AttriOrder_fld,AggrScore)
            rows.UpdateRow(row)
            
            if j == 0:
                minScore = AggrScore
                maxScore = AggrScore
            else:
                if AggrScore < minScore:
                    minScore = AggrScore
                if AggrScore > maxScore:
                    maxScore = AggrScore

            gp.SetProgressorPosition()                    
            row = rows.Next()
            j = j + 1
        del row, rows

        #Normalize weighted aggregated attribute scores then calculate the final order values.
        rows = gp.UpdateCursor(inp_fc)
        rows.Reset()
        row = rows.Next()
        while row:
            #Scale the weighted aggregated atrtibute values to 0-1, the same scale as the Peano order.
            NAggrScore = (row.GetValue(AttriOrder_fld) - minScore) / (maxScore - minScore)
            row.SetValue(NAttriOrder_fld,NAggrScore)
            CombOrder = (row.GetValue(PeanoOrder_fld) * Pct_Peano + row.GetValue(NAttriOrder_fld) * Pct_Attri) / 100
            row.SetValue(Order_fld, CombOrder)
            rows.UpdateRow(row)
            gp.SetProgressorPosition()
            row = rows.Next()
        del row, rows
        
        #Set the derived output when the script is done
        #Useful to show the output when the tool is used in model builder
        #gp.SetParameterAsText(8,inp_fc)
    except:
        # Return any python specific errors as well as any errors from the geoprocessor
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
        PrintAndWriteMessages(pymsg,2)

        msgs = "GP ERRORS:\n" + gp.GetMessages(2) + "\n"
        PrintAndWriteMessages(msgs,2)
