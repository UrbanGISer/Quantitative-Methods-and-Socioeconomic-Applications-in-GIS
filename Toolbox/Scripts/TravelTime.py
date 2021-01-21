import arcpy
import urllib
import time
from xml.etree.ElementTree import XML, fromstring, tostring


fromFile = arcpy.GetParameter(0)
toFile = arcpy.GetParameter(1)
Resultfile = arcpy.GetParameterAsText(2)


Result = open(Resultfile,"w")
Result.write("FromFID,toFID,TravelTime")
Result.write("\n")


fromCursor = arcpy.SearchCursor(fromFile)
toCursor = arcpy.SearchCursor(toFile)


fromRow = fromCursor.reset()
fromRow = fromCursor.next()


while (fromRow!=None):
 
  fromX = fromRow.shape.centroid.X
  fromY = fromRow.shape.centroid.Y
  fromFID = fromRow.FID
  arcpy.AddMessage(str(fromFID))


  toCursor = arcpy.SearchCursor(toFile)
  toRow = toCursor.reset()
  toRow = toCursor.next()

  while (toRow!=None):
    
    toX = toRow.shape.centroid.X
    toY = toRow.shape.centroid.Y
    toFID = toRow.FID
    arcpy.AddMessage(str(toFID))

    googletext = "http://maps.googleapis.com/maps/api/directions/xml?origin=(" + str(fromY) + "," + str(fromX) + ")&destination=(" + str(toY) + "," + str(toX) + ")&sensor=false"
    time.sleep(3)
    try:
       xmlfile = urllib.urlopen(googletext)
       xml = xmlfile.read()
    except IOError:
       arcpy.AddMessage("An error is encounted, skip this try.")
       Result.write(str(fromFID))
       Result.write(",")
       Result.write(str(toFID))
       Result.write(",")
       Result.write("NA")
       Result.write("\n")
       toRow = toCursor.next()
       continue

    value = "NA"
    dom  = fromstring(xml)
    nodelist = dom.getchildren()
    
    
    if (nodelist[0].text == "OK"):
        arcpy.AddMessage(nodelist[0].text)
        route=nodelist[1]
        leg=route.getchildren()[1]
        duration = leg.find("duration")
        value = duration .getchildren()[0].text
    else:
        arcpy.AddError(nodelist[0].text)
    Result.write(str(fromFID))
    Result.write(",")
    Result.write(str(toFID))
    Result.write(",")
    Result.write(value)
    Result.write("\n")
    toRow = toCursor.next()
  fromRow = fromCursor.next()
Result.close()
del fromCursor
del toCursor 




