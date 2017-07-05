/* Copyright 2017 Actian Corporation
**
** hr_sc930 - turn an SC930 file into a slightly more 'human-readable' one 
**/

#include <string.h>
#include <stdio.h>
#include <time.h>
#include <stdbool.h>
#include <errno.h>

#define LTYPE_SIZE 19          /* maximum length of line-type text, currently
                                  "SESSION BEGINS(NN)" */
#define DEFAULT_NS_DIGITS 6    /* default for the number nano-seconds to display
                                  on Linux, precision tends to be 6 at most 
                                  any how */

#define MAX_LINE_BUFSIZE  10000  /* Chunks to read 'rest of line' in */
                                  

int main(int argc,char **argv)
{
  FILE          *fin;                   /* file to read */
  time_t         ts;                    /* timestamp as a time_t value */
  char           ts_c[12];              /* timestamp in character form */
  char           ns_c[10];              /* nano-seconds as characters */
  char           ltype[LTYPE_SIZE+1];   /* 'line-type' string */
  char           c;                     /* a character read from trace file */
  char           ts_fmt[29];            /* timestamp as re-formatted by this 
                                           program */
  int            ns_i;                  /* nano-seconds as integer */
  int            ts_i;                  /* timestamp value as integer */
  int            k,i;                   /* used for loop counters */
  int            ns_dig=DEFAULT_NS_DIGITS;  /* number of digits of nano-seconds
                                               to display */
  int            fmt_len;               /* length of ofmt */
  bool           has_ts;                /* this line has a timestamp? */
  bool           show_dates=false;      /* show dates as part of timestamp? */
  struct tm     *ts_tm;                 /* timestamp in tm format */
  char          *rest_of_line;          /* the rest of the line after the 
                                           timestamp */
  char           buf[MAX_LINE_BUFSIZE]; /* buffer to contain rest of line */
  char          *fname;                 /* filename of trace file */
  char          *ns_digc;               /* nano-seconds digits as characters */
  char           fmt_fixed[]=":%-*s%s"; /* fixed part of ofmt */
  char           ofmt[15];              /* format specifier for timestamp */ 

  rest_of_line=buf;

  /* check the number of command line parameters */

  if (argc < 2)
  {
    printf("Usage:\n  hr_sc930 [-d] [-nN] <filename>\n"
           "\t-d\t\tinclude date in timestamp\n"
           "\t-nN\t\tuse N digits for nanoseconds (default=%d)\n",
           DEFAULT_NS_DIGITS);

    return(-1);
  }

  /* process the command line arguments */

  for (i=0;i< argc;i++)
  {
     if (argv[i][0]=='-')
     {
        switch (argv[i][1])
        {
            case 'd':
                show_dates=true;
                break;
            case 'n':
                ns_digc=argv[i]+2;
                errno=0;
                ns_dig=atoi(ns_digc);
                if (ns_dig < 0 || ns_dig>9)
                {
                    printf("%d is not in the range 0-9\n",ns_dig);
                    return(-1);
                }

                break;
            default:
                printf("Unknown option \'%c\'\n",argv[i][1]);
                return (-1);
        }
     }
     else
     {
        fname=argv[i];
     }

  }

  /* create ofmt - format specifier for timestamps */

  fmt_len=8;
  if (show_dates)
      fmt_len+=11;

  if (ns_dig>0)
      fmt_len=fmt_len+ns_dig+1;
  
  sprintf(ofmt,"%%-%ds%s",fmt_len,fmt_fixed);

  /* open the trace file */
  fin=fopen(fname,"r");
  if (!fin)
  {
    printf("Unable to open \"%s\" \n",fname);
    return(-2);
  }

  while( !feof(fin))
  {
      /* start processing next line */

      /* first get the line-type - everything up to first : */
      i=0;
      ltype[0]='\0';
      c='\0';
      has_ts=true;

      while ((i < LTYPE_SIZE) && (!feof(fin))
                  && (c != ':'))
      {
         c=fgetc(fin);
         if (c!=':')
         {
             ltype[i++]=c;
         }
      }
      ltype[i]='\0';

      if (!feof(fin))
      {
          /* check for line-types which don't have time-stamps */

          if (strncmp(ltype,"PARM",4)==0)
                  has_ts=false;
        
          if (has_ts && (strcmp(ltype,"TDESC")==0))
                  has_ts=false;
        
          if (has_ts && (strcmp(ltype,"COL")==0))
                  has_ts=false;
    
          if (has_ts && (strcmp(ltype,"QEP")==0))
                  has_ts=false;
    
          i=0;
          ts_c[0]='\0';
          ts_i=0;
    
          /* for timestamp-ed lines get everything up to '/' this
           * is the seconds-since-1970 part of the timestamp */
          if (has_ts)
          {
              if (!feof(fin))
                 c=fgetc(fin);
    
              while ((i < 10) && (!feof(fin))
                          && (c != '/'))
              {
                 if (c!='/')
                 {
                     ts_c[i++]=c;
                 }
                 if (!feof(fin))
                    c=fgetc(fin);
              }
              ts_c[i]='\0';

              /* convert to integer then to tm structure */
              ts_i=atoi(ts_c);
              ts=(time_t) ts_i;
              ts_tm=gmtime(&ts);

              /* next part is the nano-seconds which is everything up to
               * ':' or '?' */
              i=0;
              ns_c[0]='\0';
              while ((i < 9) && (!feof(fin))
                          && (c != ':')
                          && (c != '?'))
              {
    
                 c=fgetc(fin);
                 if ((c!=':') && (c!='?'))
                 {
                     ns_c[i++]=c;
                 }
              }
              ns_c[i]='\0';
              ns_i=atoi(ns_c);

              /* format a nice readable timestamp */

              if (show_dates)
                  sprintf(ts_fmt,"%4d-%02d-%02d %02d:%02d:%02d",
                         ts_tm->tm_year+1900,
                         ts_tm->tm_mon,
                         ts_tm->tm_mday,
                         ts_tm->tm_hour,
                         ts_tm->tm_min,
                         ts_tm->tm_sec,
                         ns_i);
              else
                  sprintf(ts_fmt,"%02d:%02d:%02d",
                         ts_tm->tm_hour,
                         ts_tm->tm_min,
                         ts_tm->tm_sec,
                         ns_i);

              /* format the nanoseconds part */
              if (ns_dig > 0)
              {
                  i=strlen(ts_fmt)-1;
                  sprintf(ns_c,"%09d",ns_i);

                  ts_fmt[++i]='.';
                  for (k=0;k<=ns_dig;k++)
                      ts_fmt[++i]=ns_c[k];
                  ts_fmt[i]='\0';
              }
    
          }
          else  
          {
              /* no time-stamp */

              sprintf(ts_fmt,"");
          }
    
          /* if i<9 here it means we got to the ':' or '?' before reading 9
           * characters for the nanoseconds. 
           * In which case make the last character we read the first character
           * of our rest_of_line string */
          if (i < 9)
          {
              rest_of_line[0]=c;
              rest_of_line++;
          }

          /* everything else is the rest of the line */
          if (!feof(fin))
              rest_of_line=fgets(rest_of_line,MAX_LINE_BUFSIZE,fin);
    
          rest_of_line=buf;
    
          /* and output the line */
          
          printf(ofmt,ts_fmt,LTYPE_SIZE,ltype,rest_of_line);

          /* for any really long lines loop around until we've output
           * all of the input line */

          while (!feof(fin) && strlen(buf) > MAX_LINE_BUFSIZE-2 )
          {
              rest_of_line=fgets(rest_of_line,MAX_LINE_BUFSIZE,fin);
              printf("%s",buf);
          }

      }
  }

  /* close file and exit cleanly */

  fclose(fin);
  return(0);

}
