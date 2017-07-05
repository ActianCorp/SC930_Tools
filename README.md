# SC930 Tools

Tools for use with Ingres Query Trace files. These are files created by
SET SERVER_TRACE or SET SESSION_TRACE (Ingres 11.0) or SET TRACE POINT SC930
(prior versions)

## SC930_LRQ - Long-Running Queries

This uses the query trace files to look for Long-running queries. The query
trace files have a start and end timestamp for each query which can be used
to calculate the running time of the query.

There are two versions of this tool - an awk script and a Python program. The
later has a simple GUI written in Tkinter. 

## SC930_HR - Human Readable Formatter

The query file format is optimized so that it can be produced with as little
overhead as possible. This tool reformats the files to make them more readable
In particular it aligns the fields and formats the timestamps in date time
format.
