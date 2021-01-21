data_od<-read.table("C:/QuantGIS_V2/Columbus/ODTime.csv",header=T,sep=',')
#This step reads data from ODTime.csv into a data frame
data_od<-data_od[order(data_od[,"OBJECTID_1"],data_od[,"OBJECTID_2"]),]
#Sort data first based on origin TAZ code, second based on destination TAZ code
vec_time<-data_od[,"NetwTime"]
vec_time<-t(vec_time)
#Then convert the od time to a vector
costs<-matrix(vec_time,nrow=812,ncol=931,byrow=T)
#Convert the above vector to a matrix for later use
data<-read.table("C:/QuantGIS_V2/Columbus/restaz.txt",header=T,sep=',')
#Read resident works constraints from restaz.txt into a data frame
data<-data[order(data[,"OBJECTID"]),]
#Sort data based on origin TAZ code
vec_res<-data[,"WORK"]
vec_res<-t(vec_res)
#Convert the number of resident workers to vectors
data<-read.table("C:/QuantGIS_V2/Columbus/emptaz.txt",header=T,sep=',')
#Read job constraints from emptaz.txt into a data frame
data<-data[order(data[,"OBJECTID"]),]
#Sort data based on destination TAZ code
vec_emp<-data[,"EMP"]
vec_emp<-t(vec_emp)
#Convert the number of jobs to vectors
row.signs<-rep("=",812)
row.rhs<-vec_res
col.signs<-rep("<=",931)
col.rhs<-vec_emp
#Set up constraint signs and right-hand sides
lp.transport(costs,"min",row.signs,row.rhs,col.signs,col.rhs)
#Run to measure wasteful commuting
result<-data.frame(data_od,as.vector(t(lp.transport(costs,"min",row.signs,row.rhs,col.signs,col.rhs)$solution)),row.names=NULL)
colnames(result)<-c("Oid","Did","Time","Flow")
write.csv(result,file="C:/QuantGIS_V2/Columbus/min_com.csv")
#Write solution to a csv file