/* POISSON_zip.SAS runs Poisson regression models on late-stage breast cancer */
/*      at the zip code area level in 2000                                    */
/*    Explanatory variables include 2 factors, primary care access and        */
/*                                 travel time to nearest screening facility  */ 
/* By F Wang, on 2-20-2014                                                     */

/* Read DBase file associated with the zip area shapefile  */
proc import dbms=dbf datafile='c:\QuantGIS_V2\Chicago_Zip\ChiZip.dbf' out=zip;

data zip1; set zip; 
  /* only zip areas with nonzero breast cancer cases are included */ 
  if BrCancer>0;
  BrLSRate=BrCancerLS/BrCancer;
  logBrCancer=log(BrCancer);
  /* logBrCancer is used as an offset variable, i.e., a regression variable with a constant 
                          coefficient of 1 for each observation. */
  
  /* run the OLS mode to explain late-stage rate as the baseline model */
 proc reg;
  model BrLSRate= fact1 fact2 accdoc T_Msite; 

/* run the poisson model to explain late-stage counts with total cases as offset variable
       specifically, a log-linear model is fitted by defining a log link function to ensure
       that the mean number of late-stage cases is positive  */
 
proc genmod;
   model BrCancerLS = fact1 fact2 accdoc T_Msite
                  /dist = poisson link = log offset = LogBrCancer; 

/* Read DBase file associated with the newly-created regions shapefile  */
proc import dbms=dbf datafile='c:\QuantGIS_V2\Chicago_Zip\Reg_Min15.dbf' out=region;

data region; set region; 
  /* Note all regions have >= 15 breast cancer cases, thus no need to run the Poisson model */ 
  /* The dependent variable BrLSRate and related explanatory variables are predefined       */
  /* run the OLS mode to explain late-stage rate as the baseline model                      */
 logT_MSite=log(T_MSite);
 proc reg;
  model BrLSRate= fact1 fact2 accdoc T_Msite; 

run;
