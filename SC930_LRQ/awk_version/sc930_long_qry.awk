# Copyright 2017 Actian Corporation
#
# sc930_long_qry.awk - AWK script to extract long-running queries from an
#   SC930 output script.
#   Outputs queries which take longer than THRESHOLD seconds
#
#   To set run with:
#
#           awk -f sc930_long_qry.awk -vTHRESHOLD=300 sess_12345_98765
#
#   if not set explicitly TRHESHOLD defaults to 5
#
# 20-Jun-2012 (maspa05)
#    Created.
# 21-Jun-2012 (maspa05)
#    Add START_FOUND flag so we skip over any initial EQY without a Start.
# 09-Oct-2017 (maspa05)
#    Add GetDBName() to report database name with query
#

# GetDBName() - Return the database name from a BEGINS record
#
# Parameters:
#     InputStr - the whole record line
#
# Output:
#     Return value is database name
#
function GetDBName(InputStr)
{
    split(InputStr,a,"(");
    END_POS=index(a[2],")");
    SC930_VER=int(substr(a[2],1,END_POS-1));
    if (SC930_VER > 8) {
	    DBNAME=a[8];
    } else { 
	    DBNAME=a[3];
    }

    END_POS=index(DBNAME,")");
    DBNAME=substr(DBNAME,1,END_POS-1);
    return(DBNAME);
}

# GetTimestamp() - Return a timestamp value for an SC930 record line
#
# Parameters:
#     InputStr - the whole record line
#     EndDelim - the delimiter between the timestamp and the rest of the record,
#                either "?" or ":"
#
# Output:
#     Return value   is timestamp in nanoseconds
#     RAWTS          is set to timestamp as a string
#     RESTRECORD     is set to the rest of the record after the timestamp and
#                      delimiter
#
function GetTimestamp(InputStr,EndDelim)
{
    IND_BEG=index(InputStr,":");
    IND_MID=index(InputStr,"/");

    SECS=substr(InputStr,IND_BEG+1,IND_MID-IND_BEG-1);
    TMP=substr(InputStr,IND_MID+1,10);
    IND_END=index(TMP,EndDelim);
    NANO=substr(TMP,0,IND_END-1);
    TS=(SECS * NANO_PER_SEC) + NANO;

    IND=index(InputStr,":");
    TMP=substr(InputStr,IND+1);
    IND=index(TMP,EndDelim);
    RESTRECORD=substr(TMP,IND+1);
    RAWTS=sprintf("%d/%09d",SECS,NANO);

    return(TS);
}

# StartQry() - Set Query text and begin timestamp
#
# Parameters:
#     InputStr - the whole record line
#     EndDelim - the delimiter between the timestamp and the rest of the record,
#                either "?" or ":"
#     Prefix   - Prefix to add to the query string.
#
function StartQry(InputStr,EndDelim,Prefix)
{
    QBEGIN_TS=GetTimestamp(InputStr,EndDelim);
    QBEGIN_RAWTS=RAWTS;
    QTEXT=Prefix RESTRECORD;
    START_FOUND=1;
}

# BEGIN block - Set up NANO_PER_SEC and THRESHOLD, also print header
#
BEGIN   {

           NANO_PER_SEC=1000000000;

           if (THRESHOLD == 0)  {
                THRESHOLD=5
                }
           THRESH_NANO=THRESHOLD * NANO_PER_SEC;
           printf("Printing queries that take longer than %05d secs\n",
                      THRESHOLD);
           printf("--------------------------------------------------\n");

# SC930 traces can start mid-query so use this flag to indicate when we hit
# our first start
           START_FOUND=0;

# set an initial database name. This will be overwritten when we get to a SESSION
# BEGINS record but as the file may start in the middle of a sessions let's have
# something to use 
	   DATABASE_NAME="<unknown>";
        }

# For a SESSION BEGINS record type record the database name
# The following record types are all the start of query in one form or another.
#

/^SESSION BEGINS\(/	{ DATABASE_NAME = GetDBName($0); }

# QRY, QUERY, QUEL and REQUEL are all queries with actual query text
#   - query delimiter is ? and no need for a prefix
#
/^QRY:/         { StartQry($0,"?",""); }

/^QUEL:/        { StartQry($0,"?",""); }

/^REQUEL:/      { StartQry($0,"?",""); }

/^REQUERY:/     { StartQry($0,"?",""); }

# The following all start a new query but we need to add the record type as a
# prefix to identify the query and the delimiter is :

/^ABORT:/ { StartQry($0,":","ABORT:"); }

/^ABSAVE:/ { StartQry($0,":","ABSAVE:"); }

/^ADD-CURSORID:/ { StartQry($0,":","ADD-CURSORID:"); }

/^AUTOCOMMIT:/ { StartQry($0,":","AUTOCOMMIT:"); }

/^BGNTRANS:/ { StartQry($0,":","BGNTRANS:"); }

/^CLOSE:/ { StartQry($0,":","CLOSE:"); }

/^COMMIT:/ { StartQry($0,":","COMMIT:"); }

/^COMMIT:/ { StartQry($0,":","COMMIT:"); }

/^DELETE CURSOR:/ { StartQry($0,":","DELETE CURSOR:"); }

/^ENDTRANS:/ { StartQry($0,":","ENDTRANS:"); }

/^EXECUTE PROCEDURE:/ { StartQry($0,":","EXECUTE PROCEDURE:"); }

/^EXECUTE:/ { StartQry($0,":","EXECUTE:"); }

/^FETCH:/ { StartQry($0,":","FETCH:"); }

/^PREPCOMMIT:/ { StartQry($0,":","PREPCOMMIT:"); }

/^QCLOSE:/ { StartQry($0,":","QCLOSE:"); }

/^QFETCH:/ { StartQry($0,":","QFETCH:"); }

/^RLSAVE:/ { StartQry($0,":","RLSAVE:"); }

/^ROLLBACK:/ { StartQry($0,":","ROLLBACK:" ); }

/^SVEPOINT:/ { StartQry($0,":","SVEPOINT:"); }

/^UNKNOWN:/ { StartQry($0,":","UNKNOWN:"); }

/^XA_COMM:/ { StartQry($0,":","XA_COMM:"); }

/^XA_END:/ { StartQry($0,":","XA_END:"); }

/^XA_PREP:/ { StartQry($0,":","XA_PREP:"); }

/^XA_RBCK:/ { StartQry($0,":","XA_RBCK:"); }

/^XA_STRT:/ { StartQry($0,":","XA_STRT:"); }

/^XA_UNKNOWN:/ { StartQry($0,":","XA_UNKNOWN:"); }

# End query record
#
#  get the timestamp value, work out the duration and output if the
#  threshold value is exceeded
#
/^EQY:/ {
            if (START_FOUND == 1) {
                QEND_TS=GetTimestamp($0,":");
                QEND_RAWTS=RAWTS;
                QDUR=QEND_TS-QBEGIN_TS;
                if (QDUR > THRESH_NANO) {
                    printf("\nQuery: %s\n",QTEXT);
                    printf("Database: %s\n",DATABASE_NAME);
                    printf("Begin: %s\nEnd:   %s\n", QBEGIN_RAWTS, QEND_RAWTS);
                    printf("Time taken: %9.2fsecs\n", (QDUR/NANO_PER_SEC));
                }
            }
        }
