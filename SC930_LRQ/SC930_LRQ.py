#!/usr/bin/env python

__author__ = 'Paul Mason'

# Copyright 2017 Actian Corporation

import os
import sys
import datetime

# handle user not having tk - a bit hacky but it works for now
# later I'll split the GUI from the common/CLI code 
try:
    from Tkinter import *
    import tkFileDialog
    import ScrolledText
    import tkMessageBox
    tk_avail = True
except:
    tk_avail = False
    class Frame(object):
	    pass

from optparse import OptionParser

# use ttk.Progressbar if possible (prettier)
try:
    from ttk import Progressbar
    real_pbar = True
except:
    real_pbar = False

# SC930_LRQ_VER - version for SC930_LRQ
# I intend to bump the minor version number for each checked in change.
SC930_LRQ_VER = '0.14'

# link for latest version of the code
SC930_LRQ_LNK = 'https://github.com/ActianCorp/SC930_Tools/'

# list of query begins - these are queries with a ? delimiting the SC930 timestamp from the query text
SC930_QQRY = ["QRY","QUEL","REQUEL","REQUERY"]
# list of queries which use the : delimiter
SC930_OQRY = ["ABORT", "ABSAVE", "ADD-CURSORID", "AUTOCOMMIT", "BGNTRANS", "CLOSE",
              "COMMIT", "DELETE CURSOR", "ENDTRANS", "EXECUTE", "EXECUTE PROCEDURE", "FETCH", "PREPCOMMIT",
              "QCLOSE", "QFETCH", "RLSAVE", "ROLLBACK", "SVEPOINT", "UNKNOWN", "XA_COMM", "XA_END",
              "XA_PREP", "XA_RBCK", "XA_STRT", "XA_UNKNOWN"]
# end of a query
SC930_EQY = ["EQY"]
# begin session
SC930_BEGIN = ["SESSION BEGINS"]
# record types to ignore
SC930_KEYW = ["TDESC", "COL", "QEP","PARM", "PARMEXEC","IVW"]

# ranges for the slider control - [min,max, tick, resolution]
SLIDER_RANGES = [[0,0.5,0.05,0.01],
                 [0.5,2,0.1,0.1],
                 [2,10,1,1],
                 [10,30,2,1],
                 [30,100,5,1],
                 [100,500,25,1],
                 [500,1000,100,1],
                 [1000,3600,250,1]]

# threshold number of lines above which to display a progress bar
SHOW_PROGBAR_THRESHOLD = 100000
# number of lines after which to update the progress bar
PROGBAR_STEP = 1000
pbar_step = PROGBAR_STEP
# step as a percentage (used for 'fake' progressbar)
pbar_perc_step = 1.0

# nanosecs in a second
NANO_PER_SEC=1000000000

# thresh time - in seconds
DEF_THRESH = 5.0
flt_thresh = DEF_THRESH

LRQ_sorted = LRQ_list = []
gui = False

# stuff relating to the "graph" that shows where the qry lies on the time scale
GRAPH_LENGTH = 660
First_qry = 0
Last_qry = 0

# ignore a record
def ignore():
    pass

# hit end of query record
def EndQry(qtext,begin_ts,end_ts,nano_thresh):
    global First_qry, Last_qry, database_name

    begin_nano = GetTimestamp(begin_ts)
    end_nano = GetTimestamp(end_ts)
    dur = end_nano - begin_nano
    if dur > nano_thresh:
        if First_qry == 0:
            First_qry = begin_nano
        if begin_nano < First_qry:
            First_qry = begin_nano
        if end_nano > Last_qry:
            Last_qry = end_nano

        try:
            LRQ_list.append([qtext,begin_ts,end_ts,dur,dbmspid,sessid,database_name])
        except:
            if gui:
                tkMessageBox.showerror(title='Failed to expand list',
                                       message='Failed to add an item to the LRQ list, possibly out of memory, try a higher threshold or fewer, smaller trace files' )
            else:
                print 'Failed to add an item to the LRQ list, possibly out of memory, try a higher threshold or fewer, smaller trace files'
            return False
    return True

# turn a timestamp in SC930 format into a number
def GetTimestamp(tstxt):
    t = tstxt.split('/')
    secs = int(t[0])
    nano = int(t[1])
    return ((secs * NANO_PER_SEC) + nano)

# turn a number timestamp into a nice string
def GetNiceTime(tstxt):
    t = tstxt.split('/')
    secs = int(t[0])
    nano = int(t[1])
    tsstr=datetime.datetime.utcfromtimestamp(secs).strftime('%Y-%m-%d %H:%M:%S')
    tsstr += ".%09d" % (nano)
    return tsstr

def GetNiceTime2(ntime):
    secs = ntime / NANO_PER_SEC
    nano = ntime - (secs * NANO_PER_SEC)
    tsstr=datetime.datetime.utcfromtimestamp(secs).strftime('%Y-%m-%d %H:%M:%S')
    tsstr += ".%09d" % (nano)
    return tsstr

# count the lines in a file
def scanfile(path):
    try:
        fh=open(path,'r')
    except:
        return -1
    l=len(fh.readlines())
    fh.close
    return l

# find the LRQs in a file
def FindLRQ(path,nano_thresh,Pwin,qryOnly):
    global dbmspid, sessid, LRQ_list, database_name

# get the DBMS pid and SESSION id from the file name if we can
    fpath = os.path.basename(path)
    sess_str = fpath[:5]
    dbmspid="<dbmspid>"
    sessid = "<session>"
    database_name = "<database>"
    if sess_str == "sess_":
        sess_parts = fpath.split("_")
        if len(sess_parts) == 3:
            dbmspid = sess_parts[1]
            sessid = sess_parts[2]

    start_found = False
    try:
        fh = open(path)
    except:
        if gui:
            tkMessageBox.showerror(title='Failed Opening file',
                                   message='Unable to open %s' % path)
        else:
            print "Unable to open '%s'" % path
        return 0

# scan the file
    pupdate = 0
    num_qrys = 0
    qtext = ''
    begin_ts = 0

# for each line check the record type
    for line in fh.readlines():

# see if we need to update progress bar
        if Pwin != None:
            pupdate += 1
            if pupdate == pbar_step:
                pupdate = 0
                if real_pbar:
                    Pwin.pbar.step(pbar_step)
                else:
                    pbar_pos = float(Pwin.pbar.get())+pbar_perc_step
                    Pwin.pbar.set(pbar_pos)
                Pwin.update()

# split line #1 - get everything before and after first ':'
        words = line.split(":",1)
        rectype = words[0].rstrip('\n')
        rwords = rectype.split("(",1)
        rectype = rwords[0]

        if rectype in SC930_QQRY:
# for a new query-query get the timestamp and query text
            start_found = True
            q = words[1].split('?',1)
            tstxt = q[0]
            qtext = q[1].rstrip('\n').lstrip()
            begin_ts = tstxt
        elif rectype in SC930_OQRY:
# for a new other-query get the timestamp and query text
            if not qryOnly:
                start_found = True
                qtext = rectype
                begin_ts = words[1].split(':')[0]
        elif rectype in SC930_EQY:
# for an EQY end the query
            end_ts = words[1].split(':')[0]
            if start_found:
                if not EndQry(qtext,begin_ts,end_ts,nano_thresh):
# if EndQry failed it means we probably ran out of memory so close the file and return
                    fh.close()
                    return num_qrys
                else:
                    start_found = False
                    num_qrys += 1
        elif rectype in SC930_BEGIN:
# for a SESSION BEGINS record
            sbwords = words[1].split("(")
            sver = sbwords[1].split(")")[0]
            if sver > 8:
                dname = sbwords[6]
            else:
                dname = sbwords[2]
            database_name = dname.split(")")[0].rstrip()
# for any other SC930 record type - ignore
        elif rectype in SC930_KEYW:
            pass
# anything else must be query text wrapped over lines so append it to current query text
        else:
            qtext = qtext+'\n'+rectype

    fh.close()
    return num_qrys


# launch command line version
def cli_main(argv=sys.argv):
    global LRQ_sorted, LRQ_list, options

    progname = os.path.basename(argv[0]).split('.')[0]

# set up command line args parsing

    parser = OptionParser(usage="%s [-nrq] [-t time] [file(s)]" % progname,
                                     version="%s %s" % (progname,SC930_LRQ_VER))
    parser.add_option("-n","--nosort",action="store_true",
                      dest="nosort", default=False,help="do NOT sort results (default is sort longest to shortest)")
    parser.add_option("-r",action="store_true",
                      dest="revsort", default=False,help="reverse sort (shortest to longest)")
    parser.add_option("-t","--threshold",
                      dest="thresh",default=DEF_THRESH,type=float,help="threshold time, in seconds")
    parser.add_option("-q","--qryonly",action="store_true",
                      dest="qryOnly",default=False,help="only consider query records (QRY,REQUERY,QUEL,REQUEL)")

    (options,filelist) = parser.parse_args()

# nosort and reverse sort are mutually exclusive
    if options.revsort and options.nosort:
        print "-n and -r are mutually exclusive"
        return

# bail if we have no files
    if len(filelist) == 0:
        print "No SC930 files given"
        return

# otherwise run the FindLRQ on the files
    for file in filelist:
        FindLRQ(file, NANO_PER_SEC * options.thresh,None,options.qryOnly)

    if options.nosort:
        LRQ_sorted = LRQ_list
    else:
        try:
            if options.revsort:
                LRQ_sorted = sorted(LRQ_list,key=lambda item: item[3], reverse=False)
            else:
                LRQ_sorted = sorted(LRQ_list,key=lambda item: item[3], reverse=True)
            LRQ_list = []
        except:
            print 'Failed to sort LRQ list - possibly out of memory, try a higher threshold or fewer, smaller trace files'
            print '(results will not be sorted)'

# output the results
    for lrq in LRQ_sorted:
        qtext = lrq[0]
        begin_ts = lrq[1]
        end_ts = lrq[2]
        dur = lrq[3]
        dbmspid = lrq[4]
        sessid = lrq[5]
        dbname = lrq[6]
        print "\nQuery:     ", qtext
        print "Database:   ", dbname
        print "Begin:      %s (%s)" % (GetNiceTime(begin_ts),begin_ts)
        print "End:        %s (%s)" % (GetNiceTime(end_ts),end_ts)
        print "Duration:   %020.9f secs" % (float (dur)/NANO_PER_SEC)
        print "DBMS PID:  ", dbmspid
        print "Session ID:", sessid

    if len(LRQ_sorted) == 1:
        qword = 'query'
    else:
        qword = 'queries'
    print "\nFound %d %s that took longer than %9.6f seconds" % (len(LRQ_sorted),qword,options.thresh)

# Initial window - select files to work on, set threshold and choose whether to sort
class SC930Chooser(Frame):
    global LRQ_sorted, LRQ_list

    def __init__(self, root):
        Frame.__init__(self, root, border=5)
        self.parent=root

        self.parent.title("SC930 Long Running Query Finder")
        frame = Frame(self, relief=RAISED, borderwidth=1)
        frame.grid(row=0,column=0,columnspan=4,padx=5,pady=5)

# ThreshSlider is the slider control to choose the theshold value
        self.ThreshSlider = Scale(frame,orient=HORIZONTAL,length=450,
                                  from_=0, to=10.0, resolution=1,
                                  tickinterval=1.0, command=self.scale_changed,
                                  showvalue=TRUE)
        self.ThreshSlider.grid(column=0,sticky="W")
        self.ThreshSlider.set(5.0)
# bind it to key events so we can use left and right keys to change it
        self.parent.bind('<Key>',self.slide_due_to_key)

# this is our record of what the slider value should be
# at any given time the actual slider widget may not match because we might be about to
# re-scale
        self.max_slider_val = self.ThreshSlider.cget('to')

        LongerFrame = Frame(frame)
        LongerFrame.grid(row=0,column=1)
        lb =Label(LongerFrame,text="Queries longer than:")
        lb.grid(row=0,column=0,sticky="E",padx=5,pady=5)

# threshentry is the entry field for the threshold
# we set the focusout validation command to focus_left_thresh() so we can change the
# value if someone tabs out of the field
        vcmd = (self.parent.register(self.focus_left_thresh),'%P')
        self.threshentry = Entry(LongerFrame,width=5,validate='focusout',
                                 validatecommand=vcmd)
        self.threshentry.grid(row=0,column=1,sticky="W",padx=0,pady=5)
        self.threshentry.insert(0,'5.0')
# bind the return key so we can change the value on hitting enter in the field
        self.threshentry.bind('<Return>',self.enter_pressed)
        self.enter_pressed('5.0')

        lb2 = Label(LongerFrame,text="secs")
        lb2.grid(row=0,column=2,sticky="W",padx=0,pady=5)

# ButtFrame - teehee! - seriously, it's a frame to contain buttons
        ButtFrame=Frame(frame, borderwidth=1)
        ButtFrame.grid(row=1,column=0,sticky='W',padx=5,pady=5)
        Label(ButtFrame,text="SC930 Files").grid(row=0,column=0)
        FileButton = Button(ButtFrame,text="Add",command=self.add_files)
        FileButton.grid(row=0,column=1,sticky='W',padx=5,pady=5)
        ClearButton = Button(ButtFrame,text="Clear", command=self.clear_files)
        ClearButton.grid(row=0,column=2,sticky='W',padx=5,pady=5)

# tick box for sort
        TickFrame = Frame(frame)
        TickFrame.grid(row=1,column=1)
        self.sorted = IntVar()
        self.sortTick = Checkbutton(TickFrame,text="Sort Results?",variable=self.sorted)
        self.sortTick.grid(row=0,column=0)
        self.sortTick.select()

        self.qryOnly = IntVar()
        self.qryTick = Checkbutton(TickFrame,text="Qry's only",variable=self.qryOnly)
        self.qryTick.grid(row=0,column=1,sticky='E')

# filebox is the entry field for the list of files - note set to disabled so user can't edit it
# (they can select and copy in it though)
# Also, it's over-sized so that when you expand from the initial size it grows.
        self.filebox = ScrolledText.ScrolledText(frame,height=50,width=200)
        self.filebox.grid(row=2,column=0,columnspan=4,padx=5,pady=5)
        self.filebox.configure(state='disabled')
        self.filelist = []
        self.filecount = 0

# more buttons
        quitButton = Button(self, text="Quit", command=sys.exit)
        quitButton.grid(row=1,column=3,padx=5,pady=5)
        LRQButton = Button(self, text="Find L.R.Q.s",command=self.FindLRQGo)
        LRQButton.grid(row=1,column=2, padx=5)
        InfoButton = Button(self,text="Info",command=self.display_info)
        InfoButton.grid(column=0,row=1,sticky=(W))

# this just makes sure the right bits of the window re-size and the right bits don't
        frame.columnconfigure(3,weight=1)
        frame.rowconfigure(2,weight=1)
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.pack()

# set by trial and error to smallest size where everything still fits
# YMMV, different default fonts etc
        self.parent.minsize(675,250)

# function called to react to key-press and move/adjust slider
    def slide_due_to_key(self,event):
        fw = self.parent.focus_get()

# don't do anything if we're in thresh entry or the file box
        if fw == self.threshentry or fw == self.filebox:
            return

# get the current values and adjust them
        curr_tick = self.ThreshSlider.cget('tickinterval')
        curr_slideval =  self.ThreshSlider.get()
        if event.keysym == 'Left':
            new_slideval = curr_slideval - curr_tick
            if new_slideval <= 0:
                new_slideval = 0
            self.change_thresh(new_slideval)
        if event.keysym == 'Right':
            new_slideval = curr_slideval + curr_tick
            if new_slideval > 3600:
                new_slideval = 3600
            self.change_thresh(new_slideval)

# we hit enter in the entry field
    def enter_pressed(self,event):
        self.check_scale()
        self.change_thresh(self.threshentry.get())

# check whether we need to re-scale the slider
    def check_scale(self):
        scaleval = self.ThreshSlider.get()
        if scaleval < (0.25 * self.max_slider_val):
            self.slider_rescale(scaleval)
        if scaleval == self.max_slider_val and scaleval < 3600:
            self.slider_rescale(scaleval)

# change the threshold value after leaving the threshentry field
# note we're required to return a value (this is a validation command)
# but we don't use it. But if we don't, stuff don't work!
    def focus_left_thresh(self,newtext_P):
        self.change_thresh(newtext_P)
        return newtext_P

# scale changed due to mouse sliding the slider
    def scale_changed(self,value):
        self.slider_rescale(value)
        self.change_thresh_entry(value)

# perform a rescale on the slider according to new value
    def slider_rescale(self,value):
        new_tick = self.ThreshSlider.cget('tickinterval')
        Range_found = False

# find the range that the value's in
        for r in SLIDER_RANGES:
            if float(value) >= r[0] and float(value) < r[1] and not Range_found:
                self.max_slider_val = r[1]
                new_tick = r[2]
                new_res = r[3]
                Range_found = True

# if we didn't find the range then we must be too big, so set it to the last one
        if not Range_found:
            self.max_slider_val = r[1]
            new_tick = r[2]
            new_res = r[3]

# change the slider widget itself
        self.ThreshSlider.configure(to=self.max_slider_val,
                                    resolution=new_res,
                                    tickinterval=new_tick)

# this was a show-debug-info button, I decided to keep it to display the version etc
    def display_info(self):
        msg='SC930 Long-Running-Query Finder'
        msg = msg + '\n\nby Paul Mason'
        msg = msg + '\n (c) Actian Corp 2017'
        msg = msg + '\nSee %s for latest version' % SC930_LRQ_LNK
        msg = msg + '\nThis version %s' % SC930_LRQ_VER
        tkMessageBox.showinfo(title='SC930 LRQ Finder',
                                   message=msg)

# change the value in the threshentry field
# usually this is either called because the slider changed and we want to match it or
# we need to re-set after going out of limits
    def change_thresh_entry(self,value):
        self.threshentry.delete(0,'end')
        self.threshentry.insert(0,value)

# change the threshold value - re-set to current value if the value is not a valid float
    def change_thresh(self,new_val):
        try:
            retval = float(new_val)
        except:
            retval = float(self.ThreshSlider.get())
        self.change_thresh_entry(retval)
        self.slider_rescale(retval)

        self.ThreshSlider.set(retval)
        self.ThreshSlider.cget('to')

# clear the filebox
    def clear_files(self):
        self.filebox.configure(state='normal')
        self.filebox.delete(1.0,'end')
        self.filebox.configure(state='disabled')

        self.filelist = []
        self.filecount = 0

# add files to the file box
    def add_files(self):

# select multiple files - however this can only be from one directory
        selectedfiles = tkFileDialog.askopenfilename(
            parent=None, title='Select SC930 Session file',
            filetypes=[('SC930 session files', 'sess*'),
                                                ('All Files', '*')],
            multiple = True)
        if selectedfiles:
            self.filebox.configure(state='normal')
            idx=self.filecount
            for file in selectedfiles:
                self.filelist.append(file)
                idx+=1
                pos=str(idx)+'.0'
                self.filebox.insert(pos,os.path.normpath(file)+'\n')

            self.filecount = idx
            self.filebox.configure(state='disabled')
        return

# This is the GO command behind the 'Find LRQs' button
# its main job is to call FindLRQ for each file
    def FindLRQGo(self):
        global LRQ_sorted, LRQ_list, flt_thresh

# no files means nothing to do
        if len(self.filelist) == 0:
            tkMessageBox.showerror(title='No SC930 Files',
                                   message='No SC930 Files have been selected!')
            return

        flt_thresh = float(self.threshentry.get())

# create the progress bar window
# depending on how much there is to do this will either live briefly and then disappear
# or still exist. If it's disappeared Pwin will be None
        Pwin = progress_bar(self.parent,self.filelist)

# process the files in the file list
        for file in self.filelist:
            FindLRQ(file,int(NANO_PER_SEC * flt_thresh), Pwin, bool(self.qryOnly.get()))

# if we actually have a progress bar window, remove it
        if Pwin != None:
            Pwin.grab_release()
            Pwin.destroy()

# if we didn't find any matching LRQs then say so
        if len(LRQ_list) == 0:
            tkMessageBox.showinfo(title='No LRQs',
                                   message='No queries found running longer than the threshold!')
            return

# sort if required - unlike the CLI we only sort in reverse but since the user can skip to the start
# and end of the list easily that should be OK
        if self.sorted.get() == 1:
            # FIXME: make this an option, "sort by"
            # sort by query length (original)
            LRQ_sorted = sorted(LRQ_list,key=lambda item: item[3], reverse=True)
            # sort by begin time
            # LRQ_sorted = sorted(LRQ_list,key=lambda item: item[1])
            LRQ_list = []
        else:
            LRQ_sorted = LRQ_list

# open the output window
        output_win(self.parent)
        return

# create the progress bar window
# this, potentially, lives on after this function and we return it as an object
# or None if it's closed
def progress_bar(root, filelist):
    global pbar_step, pbar_perc_step

# create the window with the initial title
    Pwin = Toplevel(root)
    Pwin.title('Scanning files...(counting lines)')
    Pwin.grab_set()
    Pwin.pbar_var = IntVar(Pwin)
# very simple window with one widget, a 400px progress bar
# max value is set to the number of files

# create a ttk Progressbar if we can, otherwise fake on with a Scale widget
    if real_pbar:
        Pwin.pbar = Progressbar(Pwin,orient='horizontal',length=400,mode='determinate',variable=Pwin.pbar_var,maximum=len(filelist))
    else:
        Pwin.pbar = Scale(Pwin,orient='horizontal',length=400,from_ = 0.0,to=float(len(filelist)), label = 'Files',
                          resolution = 1.0)
    Pwin.pbar.grid(row=0,column=0,padx=15,pady=15)
    Pwin.pbar_var.set(0)
    Pwin.update()

# count the lines in the files
# this is pretty fast, but no so fast that it's not worth keeping the progress bar visible for now
# very large files may take a few seconds, and if you have large numbers of files
    linecount=0
    for file in filelist:
       l = scanfile(file)
       if real_pbar:
            Pwin.pbar.step(1)
       else:
            pbar_pos= Pwin.pbar.get() + 1.0
            Pwin.pbar.set(pbar_pos)
       Pwin.update()
       if l != -1:
           linecount += l

# set the progress bar step amount - make it roughly 0.5% of the total
    pbar_step = int(linecount/200)
    if pbar_step < PROGBAR_STEP:
        pbar_step = PROGBAR_STEP

# this is the point where we may decide not to show the progress bar
    if linecount > SHOW_PROGBAR_THRESHOLD:
        Pwin.title('Scanning files...(checking queries)')
        if real_pbar:
            Pwin.pbar.configure(maximum=linecount)
            Pwin.pbar.start()
        else:
            Pwin.pbar.configure(to=100.0, resolution = 0.1, label = 'Progress %')
            Pwin.pbar.set(0.0)
            pbar_perc_step = (pbar_step * 100.0) / float(linecount)
        Pwin.update()
        return Pwin
    else:
        Pwin.grab_release()
        Pwin.destroy()
        return None

# display the output window
# this is a 'file-card' style interface showing one query at a time
def output_win(root):

# the number of queries and the query currently displayed
    output_win.qrynum = output_win.num_lrq = 0

# save the results to a file - i.e. create something akin to what CLI mode would have
    def write_to_file():
        outputfile = tkFileDialog.asksaveasfilename(
            parent=None, title='Select Output File',
            initialfile = 'sc930lrq.txt',
            filetypes=[('Text File', '*.txt'),
                                                ('All Files', '*')])
        try:
            of = open(outputfile,"w")
        except:
            if gui:
                tkMessageBox.showerror(title='Failed Opening file',
                                       message='Unable to open %s' % outputfile)
            else:
                print "Unable to open '%s'" % outputfile
            return

        for record in LRQ_sorted:
            of.write("Query:      %s\n" % record[0])
            of.write("Database:   %s\n" % record[6])
            of.write("Begin:      %s (%s)\n" % (GetNiceTime(record[1]),record[1]))
            of.write("End:        %s (%s)\n" % (GetNiceTime(record[2]),record[2]))
            of.write("Duration:   %020.9f secs\n" % (float(record[3])/NANO_PER_SEC))
            of.write("DBMS PID:   %s\n" % record[4])
            of.write("Session ID: %s\n\n" % record[5])

        of.write("Found %d queries that took longer than %9.4f seconds\n" % (len(LRQ_sorted),flt_thresh))

        of.close()

# close the window and give back focus to the initial window
    def quit_out():
        global LRQ_list, LRQ_sorted
        global First_qry, Last_qry

# very important - releases memory, these can be big!
        LRQ_list = []
        LRQ_sorted =[]

        First_qry = 0
        Last_qry = 0
        Owin.grab_release()
        Owin.destroy()

# set the display to query number qno - where qno is our list index (0 ... n-1)
# not the number we show the user (1...n)
    def populate(qno):
        global flt_thresh

# set the title
        title = "Long-Running Queries ( > %6.2fs): %d/%d" % (flt_thresh,qno+1,output_win.num_lrq)
        Owin.title(title)

# write to the querybox field - need to set to normal and then re-disable
        Owin.qrybox.configure(state='normal')
        Owin.qrybox.delete(1.0,'end')
        Owin.qrybox.insert(1.0,LRQ_sorted[qno][0])
        Owin.qrybox.configure(state='disabled')

# change the query no field
        Owin.qryno.delete(0,'end')
        Owin.qryno.insert(0,qno+1)

# all the other fields are actually labels, just change the text
        txt = "%s" % LRQ_sorted[qno][1]
        Owin.begin_ts.configure(text=txt)
        txt = "%s" % LRQ_sorted[qno][2]
        Owin.end_ts.configure(text=txt)
        Owin.begin_ts_nice.configure(text=GetNiceTime(LRQ_sorted[qno][1]))
        Owin.end_ts_nice.configure(text=GetNiceTime(LRQ_sorted[qno][2]))
        txt = "%18.9f" % (float(LRQ_sorted[qno][3]) /NANO_PER_SEC)
        Owin.duration.configure(text=txt)
        txt = "%s" % LRQ_sorted[qno][4]
        Owin.dbms.configure(text=txt)
        txt = "%s" % LRQ_sorted[qno][5]
        Owin.session.configure(text=txt)
        txt = "%s" % LRQ_sorted[qno][6]
        Owin.dbname.configure(text=txt)

# draw line for current query
        begin_nano = GetTimestamp(LRQ_sorted[qno][1])
        end_nano = GetTimestamp(LRQ_sorted[qno][2])

        begin_pos = (begin_nano - First_qry) * (GRAPH_LENGTH - 10)
        begin_pos =(begin_pos / (Last_qry - First_qry)) + 5
        end_pos = (end_nano - First_qry) * (GRAPH_LENGTH - 10)
        end_pos =(end_pos / (Last_qry - First_qry)) + 5

        # print "Qry: %d" % qno
        # print "Begin: %s (%s)" % (LRQ_sorted[qno][1], GetNiceTime(LRQ_sorted[qno][1]))
        # print "End:   %s (%s)" % (LRQ_sorted[qno][2], GetNiceTime(LRQ_sorted[qno][2]))
        # print "Duration: %6.2f" % (float(LRQ_sorted[qno][3]) /NANO_PER_SEC)
        # print "Range:"
        # print "Begin: %s (%s)" % (First_qry, GetNiceTime2(First_qry))
        # print "End:   %s (%s)" % (Last_qry, GetNiceTime2(Last_qry))
        # print "Duration: %6.2f" % ((Last_qry - First_qry) / NANO_PER_SEC)
        #
        # print "Bar for this query (%s - %s)" % (begin_pos, end_pos)

        Owin.graphcanv.delete(Owin.qline)
        Owin.graphcanv.delete(Owin.qbar1)
        Owin.graphcanv.delete(Owin.qbar2)
        Owin.qline = Owin.graphcanv.create_line(begin_pos, 15,end_pos,15,fill="Red", width=2)
        Owin.qbar1 = Owin.graphcanv.create_line(begin_pos, 13,begin_pos,18,fill="Red", width=2)
        Owin.qbar2 = Owin.graphcanv.create_line(end_pos, 13,end_pos,18,fill="Red",width=2)

# move to the next query - i.e. the right button
    def Right():
        if output_win.qrynum < output_win.num_lrq-1:
            output_win.qrynum += 1
            populate(output_win.qrynum)

# move to the previous query - i.e. left
    def Left():
        if output_win.qrynum > 0:
            output_win.qrynum -= 1
            populate(output_win.qrynum)

# move to first query
    def First():
        if output_win.num_lrq > 0:
            output_win.qrynum = 0
            populate(output_win.qrynum)

# move to last query
    def Last():
        if output_win.num_lrq > 0:
            output_win.qrynum = output_win.num_lrq-1
            populate(output_win.qrynum)

# we've tabbed out of the qryno field, try to jump to that query
    def focus_left_qryno(newtext_P):
        jump_to_qry()
        return newtext_P

# we've pressed enter in the qryno field, try to jump to that query
    def enter_pressed(event):
        jump_to_qry()

# jump to the query specified by the contents of the qryno field
# assuming a) it's anumber and b) in range
    def jump_to_qry():
        try:
            entered_no = int(Owin.qryno.get())
        except:
            entered_no = -1
        if entered_no > 0 and entered_no <= output_win.num_lrq:
            output_win.qrynum = entered_no - 1;
        populate(output_win.qrynum)

    def move_due_to_key(event):
        if event.keysym == 'Prior' or event.keysym == 'Up':
            First()
        if event.keysym == 'Next' or event.keysym == 'Down':
            Last()

        fw = Owin.focus_get()

# don't do anything if we're in the qryno box as user might be editing a value
        if fw == Owin.qryno:
            return

# get the current values and adjust them
        if event.keysym == 'Left':
            Left()
        if event.keysym == 'Right':
            Right()


# create the window
# note most of the fields are labels where the text is the value
# the exceptions are the qryno field and the query text box

    Owin = Toplevel(root)

    l1 = Label(Owin, text="QryNo:")
    l1.grid(row=0,column=0,sticky=(W),padx=5,pady=5)

# register the command for tabbing out of the qryno field
    vcmd = (Owin.register(focus_left_qryno),'%P')
    Owin.qryno = Entry(Owin,width=8,justify=RIGHT, validate='focusout',validatecommand=vcmd)
    Owin.qryno.grid(row=0,column=1,padx=5,pady=5,sticky=(E))

    Owin.bind('<Key>',move_due_to_key)

# bind the return key so we can react if we hit enter on the qryno field
    Owin.qryno.bind('<Return>',enter_pressed)

# set up the labels that are actually fields - note these default values should never be seen
    l2 = Label(Owin, text="Begin:")
    l2.grid(row=0,column=2,sticky=(W),padx=5)
    Owin.begin_ts = Label(Owin, text="000000/000000", bd=3, relief=RIDGE)
    Owin.begin_ts.grid(row=0,column=4,sticky=(W),pady=5,padx=5)
    Owin.begin_ts_nice = Label(Owin, text="1900-01-02 03:04:05.000000000", bd=3, relief=RIDGE)
    Owin.begin_ts_nice.grid(row=0,column=3,sticky=(E),pady=5,padx=5)

    l3 = Label(Owin, text="Duration (s):")
    l3.grid(row=1,column=0,sticky=(W),padx=5)
    Owin.duration = Label(Owin, text="0.0", bd=3, relief=RIDGE)
    Owin.duration.grid(row=1,column=1,padx=5,sticky=(E))
    l4 = Label(Owin, text="End:")
    l4.grid(row=1,column=2,sticky=(W),padx=5)
    Owin.end_ts = Label(Owin, text="000000/000000", bd=3, relief=RIDGE)
    Owin.end_ts.grid(row=1,column=4,sticky=(W),padx=5)
    Owin.end_ts_nice = Label(Owin, text="1900-01-02 03:04:05.000000000", bd=3, relief=RIDGE)
    Owin.end_ts_nice.grid(row=1,column=3,sticky=(E),pady=5,padx=5)
    l5 = Label(Owin, text="DBMS Pid:")
    l5.grid(row=2,column=0,sticky=(W),padx=5,pady=5)
    Owin.dbms = Label(Owin, text="dbms", bd=3, relief=RIDGE)
    Owin.dbms.grid(row=2,column=1,padx=5,sticky=(E))
    l6 = Label(Owin, text="Session id/DB:")
    l6.grid(row=2,column=2,sticky=(W),padx=5,pady=5)
    Owin.session = Label(Owin, text="session", bd=3, relief=RIDGE)
    Owin.session.grid(row=2,column=3,padx=5,sticky=(E))
    Owin.dbname = Label(Owin, text="dbname", bd=3, relief=RIDGE)
    Owin.dbname.grid(row=2, column=4, padx=5, sticky=(W))


# add canvas to draw graph on
    Owin.graphcanv = Canvas(Owin,width=GRAPH_LENGTH,height=25)
    Owin.graphcanv.grid(row=3,column=0, columnspan=5)

# add a line for the scale
    Owin.graphcanv.create_line(5,20,GRAPH_LENGTH - 5,20,width=2)
    Owin.graphcanv.create_line(5,20,5,15,width=2)
    Owin.graphcanv.create_line(GRAPH_LENGTH - 5,20,GRAPH_LENGTH - 5,15,width=2)

# add a query
    Owin.qline = Owin.graphcanv.create_line(100, 15,110,15)
    Owin.qbar1 = Owin.graphcanv.create_line(100, 13,100,18)
    Owin.qbar2 = Owin.graphcanv.create_line(110, 13,110,18)


# qrybox is where we display the query text. It's oversized so it expands if the window is re-sized
# and disabled so it can't be changed - though text can be selected and copied
    Owin.qrybox = ScrolledText.ScrolledText(Owin,width=250,height=50)
    Owin.qrybox.grid(row=4,column=0,padx=5,columnspan=5)
    Owin.qrybox.configure(state='disabled')

# create a frame for our navigation buttons
    ButtFrame1 = Frame(Owin,relief=SUNKEN, borderwidth=1)
    ButtFrame1.grid(row=5,column=1,padx=5,pady=5,columnspan=3)
    FirstButton = Button(ButtFrame1, text = "<<", command=First)
    FirstButton.grid(row=0,column=0,padx=5,pady=5)
    LeftButton = Button(ButtFrame1,text="<",command=Left)
    LeftButton.grid(row=0,column=1,padx=5,pady=5)
    RightButton = Button(ButtFrame1, text=">",command=Right)
    RightButton.grid(row=0,column=2,padx=5,pady=5)
    LastButton = Button(ButtFrame1, text = ">>", command=Last)
    LastButton.grid(row=0,column=3,padx=5,pady=5)

# create a frame for the other two buttown - save and close
    ButtFrame2 = Frame(Owin,relief=SUNKEN, borderwidth=1)
    ButtFrame2.grid(row=5,column=4,padx=5,pady=5,sticky=(E))
    saveButton = Button(ButtFrame2, text="save to file", command=write_to_file)
    saveButton.grid(row=0,column=0,padx=5,pady=5)
    quitButton = Button(ButtFrame2, text="close", command=quit_out)
    quitButton.grid(row=0,column=1,padx=5,pady=5)

# this all just makes sure only the qrybox changes size when we re-size the window
    Owin.columnconfigure(0,weight=0)
    Owin.columnconfigure(1,weight=0)
    Owin.columnconfigure(2,weight=0)
    Owin.columnconfigure(3,weight=0)
    Owin.columnconfigure(4,weight=1)
    Owin.rowconfigure(0,weight=0)
    Owin.rowconfigure(1,weight=0)
    Owin.rowconfigure(2,weight=0)
    Owin.rowconfigure(3,weight=0)
    Owin.rowconfigure(4,weight=1)
    Owin.rowconfigure(5,weight=0)

# don't want the user making it so the fields and buttons can't fit
# based on my screen, with my fonts on Windows - may vary elsewhere
    Owin.minsize(GRAPH_LENGTH,200)

# the number of queries in our list
    output_win.num_lrq = len(LRQ_sorted)

# set the title and initial size
    title = "Long-Running Queries: 1/"+"%d" % output_win.num_lrq
    Owin.title(title)
    Owin.geometry('700x400')

# grab focus - initial 'chooser' window will still be open but can't be used
# while we're interacting with the results window
    Owin.grab_set()

# if the user closes via the window control then quit out nicely (i.e. return focus)
    Owin.protocol("WM_DELETE_WINDOW",quit_out)

# display the first query
    if output_win.num_lrq > 0:
        populate(0)

# launch the GUI
def gui_main():
    global gui

# flag so we know if we're in the gui - means we can use message boxes rather than messages
    gui = True

# create initial 'chooser' window and begin
    root = Tk()
    root.geometry("700x250+300+300")
    SC930Chooser(root)
    root.mainloop()
    return 0

# if no arguments then launch the GUI otherwise launch the CLI
# see also comments in SC930_LRQ_gui
if __name__ == '__main__':
    if len(sys.argv) > 1 or tk_avail == False:
        sys.exit(cli_main())
    sys.exit(gui_main())
