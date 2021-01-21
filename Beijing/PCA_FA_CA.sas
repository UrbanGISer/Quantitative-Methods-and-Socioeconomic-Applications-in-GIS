/*PCA_FA_CA.SAS runs Principal Component Analysis, Factor Analysis & Cluster Analysis 
        for social area analysis in Beijing                                         */
/*By Fahui Wang on 11-5-2013                                                        */

/* read the attribute data */
proc import datafile="c:\QuantGIS_V2\Beijing\bjattr.csv" 
     out=bj dbms=dlm replace; 
     delimiter=', ';
     getnames=yes;
proc means; 

/* Run the principal components analysis   */
proc princomp data=bj out=pcomp(replace=yes);
   var x1-x14;
run;

/* Run factor analysis */
proc factor out=fscore(replace=yes)
  nfact=4 rotate=varimax; /* 4 factors used */
  var x1-x14; 
/*export factor score data */
proc export data=fscore dbms=csv 
     outfile="c:\QuantGIS_V2\Beijing\factscore.csv"; 
run; 

/* Run cluster analysis */
/* Factor scores are first weighted by their relative importance
   measured by variance portions accounted for (based on FA)  */
data clust; set fscore;
      factor1 = 0.3516*factor1;
      factor2 = 0.1542*factor2;
      factor3 = 0.1057*factor3;
      factor4 = 0.0922*factor4; 
proc cluster method=ward outtree=tree;
   id ref_id; var factor1-factor4; /*plot dendrogram */
proc tree out=bjclus ncl=9; /* cut the tree at 9 clusters */ 
   id ref_id;
/* export the cluster analysis result */
proc export data=bjclus dbms=csv 
   outfile="c:\QuantGIS_V2\Beijing\cluster9.csv";
run;
