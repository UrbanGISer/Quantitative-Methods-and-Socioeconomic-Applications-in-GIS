/* BJREG.sas runs regressions to test whether a factor
     conforms to a zonal or sectoral model            */
/* By Fahui Wang on 11-05-2013                        */

proc import datafile="c:\QuantGIS_V2\Beijing\bjf4score.dbf" 
     out=bjreg dbms=dbf replace; 
     proc means;
data code; set bjreg;
if ring=1 then do;
  x2=0; x3=0; x4=0;
  end;
if ring=2 then do;
  x2=1; x3=0; x4=0;
  end;
if ring=3 then do;
  x2=0; x3=1; x4=0;
  end;
if ring=4 then do;
  x2=0; x3=0; x4=1;
  end;

if sector=1 then do;
  y2=0; y3=0; y4=0;
  end;
if sector=2 then do;
  y2=1; y3=0; y4=0;
  end;
if sector=3 then do;
  y2=0; y3=1; y4=0;
  end;
if sector=4 then do;
  y2=0; y3=0; y4=1;
  end;
proc reg;
 model factor1 =  x2 x3 x4 ;
 model factor2 =  x2 x3 x4 ;
 model factor3 =  x2 x3 x4 ;
 model factor4 =  x2 x3 x4 ;
 model factor1 =  y2 y3 y4;
 model factor2 =  y2 y3 y4;
 model factor3 =  y2 y3 y4;
 model factor4 =  y2 y3 y4;
run;
