/* LP.sas minimizes total commute time in Columbus, Ohio.
   By Fahui Wang on 4-14-2005                            */

/* Input the data of resident workers & jobs             */
data study;
  infile 'c:\gis_quant_book\projects\columbus\urbtaz.txt';
  input taz $1-6 work emp; /*TAZ codes, # Workers, # jobs*/
  proc sort; by taz;
data work; set study (rename=(taz=tazr)); if work>0;
   oindex+1;	/*Create an index for origin TAZs        */
data emp; set study (rename=(taz=tazw)); if emp>0;
   dindex+1;    /*Create an index for destination TAZs   */

/* Input the data of O-D commute time                    */
data netdist0;
  infile 'c:\gis_quant_book\projects\columbus\odtime.txt';
  input tazr $1-6 tazw $9-14 @15 d; /*from_taz, to_taz, time*/
  proc sort; by tazw;
data netdist1;    /*attach index for destination taz      */
  merge emp(in=a) netdist0; by tazw; if a;
  proc sort; by tazr;
data netdist2;    /*attach index for origin taz           */
  merge work(in=a) netdist1; by tazr; if a;
  route=oindex*1000+dindex; /*Create unique code for a route*/
  proc sort; by route;

/* Build the LP model in sparse format                    */
data model;
  length _type_ $8 _row_ $8 _col_ $8;
  keep _type_ _row_ _col_ _coef_;  /*four variables needed */
NI=812;  /*total number of origin TAZs */
NJ=931;  /*total number of destination TAZs */

/* Create the Constraints on Jobs */
Do j=1 to NJ; set emp;
/* 1st entry defines the upper bound (#jobs) for a TAZ */
  _row_='EMP'||put(j,3.); /* Increase the space limit "3" if >999 TAZs */
  _type_='LE';
  _col_='_RHS_';
  _coef_=emp;
  output;
/* the following defines variables & coefficients in the same row */
  _type_=' ';
  Do I=1 to NI;
    if emp~=. then do; /* for non-zero emp TAZs only */ 
    _col_='X'||put(i,3.)||put(j,3.);  /* Xij */
    _coef_=1.0;  /* all coefficients are 1 */
    output;
    end;
  end;
end;

/* Create the Constraints on Resident Workers */
Do i=1 to Ni;
  set work;
  _row_='WRK'||put(i,3.);
  _type_='EQ';  /* All resident workers must be assigned */
                /* Note total resident workers < total jobs */
  _col_='_RHS_';
  _coef_=work;
  output;
  _type_=' ';
  Do j=1 to Nj;
    if work~=. then do;
    _col_='X'||put(i,3.)||put(j,3.);
    _coef_=1.0;
    output;
    end;
  end;
end;

/* Create the objective function */
_row_='OBJ';
Do I=1 to NI;
  Do J= 1 to NJ;
    _type_='  ';
    set netdist2;
    if d~=. then do;
    _col_='X'||put(i,3.)||put(j,3.);
    _coef_=D;
    output;
    end;
  end;
end;
_type_='MIN';
_col_=' ';
_coef_=.;
output;

/* Run the LP Problem */
proc lp sparsedata
   primalout=result noprint time=60000 maxit1=5000 maxit2=50000;
   reset time=60000 maxit1=5000 maxit2=50000;

data result; set result;
   if _value_>0 and _price_>0;
/* Save the result to an external file for review     */
data _null_; set result;
   file 'c:\gis_quant_book\projects\columbus\junk.txt';
   put _var_ _value_;

/* convert the X variable to From_TAZ and To_TAZ index codes */
data junk;
 infile 'c:\gis_quant_book\projects\columbus\junk.txt';
 input oindex 2-4 dindex 5-7 Ncom ;
 route=oindex*1000+dindex;
 proc sort; by route;

/* attach the From_TAZ and To_TAZ codes, #commuters and time 
      and save the result to an external file                */
data f;
  merge netdist2 junk(in=a); by route; if a;
  file 'c:\gis_quant_book\projects\columbus\min_com.txt';
  put tazr $1-6 tazw $8-13 Ncom 15-21 @23 d 12.5;
run;
