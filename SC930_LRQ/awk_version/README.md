# SC930 Long-Running Queries (awk version)

This is an AWK script to find long-running queries from an SC930 trace file.  'Long-running' is defined by a threshold value which is specified as a number of seconds.

## To run the script

    awk -f sc930_long_qry.awk -vTHRESHOLD=30 sess_32552_402eba40

This will find queries that took longer than 30 seconds elapsed time. A query in this context is defined as an operation which is issued and followed by an EQY record. This could be an SQL query but it could also be an individual fetch of a cursor. See the discussion of EQY on SC930 Output Format

## Example Output

    $ awk -f sc930_long_qry.awk -vTHRESHOLD=30 sess_32552_402eba40
    Printing queries that take longer than 00030 secs
    --------------------------------------------------
    
    Query: select count(*) from iitables,iitables,iitables,iitables
    Begin: 1340273115/498771000
    End:   1340273162/351674000
    Time taken:     46.85secs

Note that only the query text, the begin and end timestamp and the duration are output. Use the timestamp together with the query text to search the original file for more details and context.
