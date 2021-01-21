/*PCA_FA.SAS runs Principal Component Analysis, Factor Analysis for Case Study 8C   */
/*By Fahui Wang on 11-13-2013                                                        */

/* read the attribute data */
Data chicity;
  infile 'c:\QuantGIS_V2\Chicago_City\cityattr.txt' lrecl=106; 
  input cntybna $1-7 @10 x1 @20 x2 @30 x3 @40 x4 @50 x5 @60 x6 @70 x7 @80 x8 @90 x9 @100 X10; 
proc sort; by cntybna;     
proc means; 
run;

/* Run the principal components analysis   */
proc princomp data=chicity out=pcomp(replace=yes);
   var x1-x10;
run;

/* Run factor analysis */
proc factor out=fscore(replace=yes)
  nfact=3 rotate=varimax; /* 4 factors used */
  var x1-x10; 
/*export factor score data */

data fscore1 (keep=cntybna x1-x10 factor1-factor3); set fscore;
proc export data=fscore1 dbms=dbf 
     outfile="c:\QuantGIS_V2\Chicago_City\factscore.dbf"; 
run; 
