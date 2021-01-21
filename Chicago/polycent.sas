/* Polycent.sas runs regressions for census tracts
   based on on various polycentric models 
   by Fahui Wang, 10-25-2013*/

/* Import the file cnty6trtpt.dbf for testing Assumptions 1 & 4 */
/* CHANGE THE LOCATION OF THE DBF FILE IN THE FOLLOWING STATEMENT TO YOUR OWN LOCATION*/
proc import datafile="c:\QuantGIS_V2\Chicago_6Cnty\cnty6trtpt.dbf" dbms=dbf out=poly1;

data poly1; set poly1;
  lnpopden=log(popden+1); /*to avoid taking log of 0 */

/*fit function based on assumption 1 */ 
/*begin with proximal area around center 1*/
data region1; set poly1; if NEAR_FID=1; /* extract tracts near center 1*/
  proc reg; model lnpopden=D_NEARC; /* linear regression on log-transform of exponential */

/* repeat the analysis on other 14 centers */
data region2; set poly1; if NEAR_FID=2; proc reg; model lnpopden=D_NEARC; 
data region3; set poly1; if NEAR_FID=3; proc reg; model lnpopden=D_NEARC; 
data region4; set poly1; if NEAR_FID=4; proc reg; model lnpopden=D_NEARC; 
data region5; set poly1; if NEAR_FID=5; proc reg; model lnpopden=D_NEARC; 
data region6; set poly1; if NEAR_FID=6; proc reg; model lnpopden=D_NEARC; 
data region7; set poly1; if NEAR_FID=7; proc reg; model lnpopden=D_NEARC; 
data region8; set poly1; if NEAR_FID=8; proc reg; model lnpopden=D_NEARC; 
data region9; set poly1; if NEAR_FID=9; proc reg; model lnpopden=D_NEARC; 
data region10; set poly1; if NEAR_FID=10; proc reg; model lnpopden=D_NEARC; 
data region11; set poly1; if NEAR_FID=11; proc reg; model lnpopden=D_NEARC; 
data region12; set poly1; if NEAR_FID=12; proc reg; model lnpopden=D_NEARC; 
data region13; set poly1; if NEAR_FID=13; proc reg; model lnpopden=D_NEARC; 
data region14; set poly1; if NEAR_FID=14; proc reg; model lnpopden=D_NEARC; 
data region15; set poly1; if NEAR_FID=15; proc reg; model lnpopden=D_NEARC; 
run;

/*fit function based on assumption 4 */
data poly1; set poly1;
  proc reg;
   model lnpopden=DIST_CBD D_NEARC;
run;


/* Import the file PolyDist.dbf for testing Assumptions 2 & 3 */
/* CHANGE THE LOCATION OF THE DBF FILE IN THE FOLLOWING STATEMENT TO YOUR OWN LOCATION*/
proc import datafile="c:\QuantGIS_V2\Chicago_6Cnty\PolyDist.dbf" dbms=dbf out=poly2;
Data poly2; set poly2;
  dcent15=DISTANCE/1000; /*converting unit to km */
  lnpopden=log(popden+1); /*to avoid taking log of 0 */
  proc sort; by INPUT_FID;

/* create data subset of distances from center No.1 */
data c1 (Keep=INPUT_FID popden lnpopden d1); set poly2;if NEAR_FID=1;
   d1=dcent15; /*which is the distances from center 1 */

/* Repeat the process to create data subset of distances from other centers*/
data c2 (Keep=INPUT_FID d2); set poly2; if NEAR_FID=2; d2=dcent15; 
data c3 (Keep=INPUT_FID d3); set poly2; if NEAR_FID=3; d3=dcent15;   
data c4 (Keep=INPUT_FID d4); set poly2; if NEAR_FID=4; d4=dcent15; 
data c5 (Keep=INPUT_FID d5); set poly2; if NEAR_FID=5; d5=dcent15; 
data c6 (Keep=INPUT_FID d6); set poly2; if NEAR_FID=6; d6=dcent15;   
data c7 (Keep=INPUT_FID d7); set poly2; if NEAR_FID=7; d7=dcent15; 
data c8 (Keep=INPUT_FID d8); set poly2; if NEAR_FID=8; d8=dcent15; 
data c9 (Keep=INPUT_FID d9); set poly2; if NEAR_FID=9; d9=dcent15;   
data c10 (Keep=INPUT_FID d10); set poly2; if NEAR_FID=10; d10=dcent15; 
data c11 (Keep=INPUT_FID d11); set poly2; if NEAR_FID=11; d11=dcent15; 
data c12 (Keep=INPUT_FID d12); set poly2; if NEAR_FID=12; d12=dcent15;   
data c13 (Keep=INPUT_FID d13); set poly2; if NEAR_FID=13; d13=dcent15; 
data c14 (Keep=INPUT_FID d14); set poly2; if NEAR_FID=14; d14=dcent15; 
data c15 (Keep=INPUT_FID d15); set poly2; if NEAR_FID=15; d15=dcent15; 

data new_dcent15; /*create data set to test assumptions 2 & 3 */
  merge c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15; by INPUT_FID;
  /*proc means; */ 

/*fit function based on assumption 2 */
proc reg; /* simple linear regression */
   model lnpopden =d1-d15; /*15 X variables (D1 through D15) used*/

/*fit function based on assumption 3 */
/* the following fits a two-center model */
proc NLIN; 
  parms a15=10000 b15=-0.05 a5=10000 b5=-0.05 ;
  model popden = a15*exp(b15*d15) +a5*exp(b5*d5);
run;
