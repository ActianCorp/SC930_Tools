-- Create table to load SC930 format data from CSV file output:

--CREATE TABLE queries
--(
--    querytext      VARCHAR(16000)               WITH NULL WITH DEFAULT,
--    begintimestamp TIMESTAMP WITHOUT TIME ZONE     WITH NULL WITH DEFAULT,
--    endtimestamp   TIMESTAMP WITHOUT TIME ZONE     WITH NULL WITH DEFAULT,
--    duration       FLOAT8                       WITH NULL WITH DEFAULT,
--    dbmspid        BIGINT                       WITH NULL WITH DEFAULT,
--    sessionid      VARCHAR(8)                   WITH NULL WITH DEFAULT,
--    userid         VARCHAR(32)                  WITH NULL WITH DEFAULT,
--    databasename   VARCHAR(32)                  WITH NULL WITH DEFAULT,
--    querytexthash  CHAR(40)                     WITH NULL WITH DEFAULT
--)
--WITH NOPARTITION;
--commit;


SELECT  date_format(begintimestamp, '%d %H') as "Date and hour",
        count(*) as "Total Queries" ,
        avg(duration) as mean_time,
        min(duration) as min_time,
        max(duration) as max_time,
        stddev_pop(duration) as "Std Dev of Duration",
        max(b.qtime_pct) as "99% of queries in this time block took less than (s)"

FROM revenue_queries a, (
        SELECT  hour,
                max(duration) as qtime_pct
        FROM (SELECT date_format(begintimestamp, '%d %H') as hour,
                     duration,
                     ntile(100) over (partition by date_format(begintimestamp, '%d %H') order by duration) as percentile
              FROM revenue_queries
             ) X
        GROUP BY hour, percentile
        HAVING percentile = 99
) b
WHERE date_format(begintimestamp, '%d %H') = b.hour
GROUP BY 1
ORDER BY  "Date and hour"
;
commit;

select min(begintimestamp), max(begintimestamp)
from revenue_queries;

select first 1000 * from revenue_queries
order by duration desc;

SELECT COUNT (*) as unique_executions,
        min(duration) as min_duration,
        max(duration) as max_duration,
        querytexthash
FROM revenue_queries
GROUP BY querytexthash
HAVING count(*) > 1
ORDER BY 1 DESC
;