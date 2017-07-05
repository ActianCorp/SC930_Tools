# SC930 Human Readable Format

This is a program to re-format SC930 trace logs into a slightly more readable format. What this means is that the timestamps are converted into a readable date format rather than seconds since 1st Jan 1970, and the line type specifier is padded to an equal number of spaces so that the output lines up.

## To compile the program

    cc -o hr_sc930 hr_sc930.c

## To run the program

    hr_sc930 sess_1234_12345678

There are two optional flags:

**-d** means output the date as part of the timestamp. By default this is omitted. 

**-nN** means output the first N digits of the nano-seconds part of the timestamp.

## Example Output

Given the file

    SESSION BEGINS(8):1286444431/318545000:(DBID=1281628453)(ingres)(                                )(                                )(SVRCL=INGRES                  )
    QRY:1286444431/318556000?set autocommit on
    AUTOCOMMIT:1286444431/318618000:
    EQY:1286444431/318644000:-1:
    QRY:1286444431/318747000?select cap_capability, cap_value from iidbcapabilities
    TDESC:65747:2:64:17
    COL:0:20:32:0
    COL:1:20:32:0
    EQY:1286444431/319458000:42:
    QRY:1286444431/328985000?CREATE PROCEDURE byte_ins( inbyt c(1000) not null) AS BEGIN UPDATE byte_test SET col1=:inbyt; END
    EQY:1286444431/364293000:-1:
    EXECUTE PROCEDURE:1286444431/375845000:(ID=0/0)(byte_ins)
    PARMEXEC:27:0(inbyt)=5b 42 40 31 61 64 63 33 30
    EQY:1286444431/376224000:-1:
    QRY:1286444431/377133000?prepare JDBC_STMT_0_0 into sqlda from SELECT HEX(col1) FROM byte_test
    TDESC:0:1:2007:1
    COL:0:-21:2007:0
    EQY:1286444431/377323000:-1:
    QRY:1286444431/379115000?open ~Q cursor for JDBC_STMT_0_0 for readonly
    PARM:30:0=0
    PARM:30:1=0
    PARM:20:2='JDBC_CRSR_0_1                                                   '
    TDESC:0:1:2007:21
    COL:0:-21:2007:0
    ADD-CURSORID:1286444431/379388000:(ID=12/3)(jdbc_crsr_0_1 )
    EQY:1286444431/379413000:-1:
    FETCH:1286444431/379520000:(ID=12/3):ROWCOUNT=4
    EQY:1286444431/379563000:0:
    CLOSE:1286444431/379651000:(ID=12/3):ROWCOUNT=4
    EQY:1286444431/379694000:-1:
    QRY:1286444431/382971000?DROP PROCEDURE byte_ins
    EQY:1286444431/384809000:-1:

the output would be

    09:40:28.648366:EQY               :-1:
    09:40:28.648514:EQY               :-1:
    09:40:31.318545:SESSION BEGINS(8) :(DBID=1281628453)(ingres                          )(                                )(                                )(SVRCL=INGRES                  )
    09:40:31.318556:QRY               ?set autocommit on
    09:40:31.318618:AUTOCOMMIT        :
    09:40:31.318644:EQY               :-1:
    09:40:31.318747:QRY               ?select cap_capability, cap_value from iidbcapabilities
                   :TDESC             :65747:2:64:17
                   :COL               :0:20:32:0
                   :COL               :1:20:32:0
    09:40:31.319458:EQY               :42:
    09:40:31.328985:QRY               ?CREATE PROCEDURE byte_ins( inbyt c(1000) not null) AS BEGIN UPDATE byte_test SET col1=:inbyt; END
    09:40:31.364293:EQY               :-1:
    09:40:31.375845:EXECUTE PROCEDURE :(ID=0/0)(byte_ins)
                   :PARMEXEC          :27:0(inbyt)=5b 42 40 31 61 64 63 33 30
    09:40:31.376224:EQY               :-1:
    09:40:31.377133:QRY               ?prepare JDBC_STMT_0_0 into sqlda from SELECT HEX(col1) FROM byte_test
                   :TDESC             :0:1:2007:1
                   :COL               :0:-21:2007:0
    09:40:31.377323:EQY               :-1:
    09:40:31.379115:QRY               ?open ~Q cursor for JDBC_STMT_0_0 for readonly
                   :PARM              :30:0=0
                   :PARM              :30:1=0
                   :PARM              :20:2='JDBC_CRSR_0_1                                                   '
                   :TDESC             :0:1:2007:21
                   :COL               :0:-21:2007:0
    09:40:31.379388:ADD-CURSORID      :(ID=12/3)(jdbc_crsr_0_1 )
    09:40:31.379413:EQY               :-1:
    09:40:31.379520:FETCH             :(ID=12/3):ROWCOUNT=4
    09:40:31.379563:EQY               :0:
    09:40:31.379651:CLOSE             :(ID=12/3):ROWCOUNT=4
    09:40:31.379694:EQY               :-1:
    09:40:31.382971:QRY               ?DROP PROCEDURE byte_ins
    09:40:31.384809:EQY               :-1:
