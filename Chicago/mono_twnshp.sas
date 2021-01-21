/* Monocent.sas runs linear, nonlinear & weighted regressions for townships
   based on various monocentric models 
   by Fahui Wang on 10-25-2013*/

/* Import data from the DBF file */
/* CHANGE THE LOCATION OF THE DBF FILE IN THE FOLLOWING STATEMENT TO YOUR OWN LOCATION*/
proc import datafile="c:\QuantGIS_V2\Chicago_6Cnty\twnshppt.dbf" dbms=dbf out=mono;

data mono; set mono;
  DIST=NEAR_DIST/1000;
  popden=twnshp_pop;
  area_km2=twnshp_S_1/1000000;
  LnDIST=log(DIST); 
  lnpopden=log(popden); /*no need to use log(popden+1) as no twnshp has popden=0 */
  DIST_sq=DIST**2;
/* the following codes variables used in the Cubic spline model 
   by assigning arbitrary x0, x1, x2 &x3*/
   x0=1.0; x1=5.0; x2=10.0; x3=15.0;
   z1=0; z2=0; z3=0;
   if DIST > x1 then z1=1;
   if DIST > x2 then z2=1;
   if DIST > x3 then z3=1;
   v1=DIST-x0; v2=(DIST-x0)**2; v3=(DIST-x0)**3;
   v4=z1*(DIST-x1)**3; v5=z2*(DIST-x2)**3; v6=z3*(DIST-x3)**3;
 proc means;
 run;

proc reg; /* simple OLS linear regressions */
   model popden = DIST; /*linear model */
   model popden = LnDIST; /*logarithmic model */ 
   model lnpopden = LnDIST; /*power model*/
   model lnpopden = DIST; /*exponential model */
   model lnpopden = DIST_sq; /*Tanner-Sherratt model */
   model lnpopden = DIST DIST_sq;  /*Newling's model */
   model popden = v1 v2 v3 v4 v5 v6; /*Cubic spline model */

proc reg; /* OLS weighted regressions */
   model popden = DIST; /*linear model */
   model popden = LnDIST; /*logarithmic model */ 
   model lnpopden = LnDIST; /*power model*/
   model lnpopden = DIST; /*exponential model */
   model lnpopden = DIST_sq; /*Tanner-Sherratt model */
   model lnpopden = DIST DIST_sq;  /*Newling's model */
   model popden = v1 v2 v3 v4 v5 v6; /*Cubic spline model */
weight area_km2;

proc NLIN;  /* nonlinear regression on power func */
   parameters a=30000 b=0.0; /*assign starting values */
   model popden = a*DIST**b; /*code power function */

proc NLIN; /* nonlinear regression on exponential func */
   parameters a=30000 b=0.0;
   model popden = a*exp(b*DIST);
   
proc NLIN;  /* nonlinear regression on Tanner-Sherratt */
   parameters a=30000 b=0.0;
   model popden = a*exp(b*DIST_sq);
   
proc NLIN;  /* nonlinear regression on Newling's */
   parameters a=30000 b1=0.0 b2=0.0;
   model popden = a*exp(b1*DIST+b2*DIST_sq);
   
run;
