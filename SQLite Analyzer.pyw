from tkinter import *
import tkinter.messagebox
from tkinter.filedialog import askopenfilename
import os
import time
import re
import struct
import sqlite3

content = 0
clear = 1
records = []
user = os.getlogin()

version = "v1.2 Beta"

#Function used to clear all fields within the window
#The Table dropdown option menu created in the Analyse function is destroyed
#The contents of the listbox are deleted
def clearall():
    global tables
    try:
        tables.destroy()
    except NameError:
        pass
    loading.set("Filename:")
    file_size.set("Size:")
    validcheck.set("Valid Database Header: ")
    sqlversion.set("SQLite Version: ")
    pagesize.set("Pagefile size: ")
    numpages.set("Number of pages: ")
    dbsize.set("Database filesize: ")
    changes.set("File changes: ")
    freelists.set("Freelist Pages: ")
    columns.set("Number of columns: ")
    listbox.delete(0, END) #Delete contents of the listbox from the beginning (0) to the END
    tablebox.delete(0, END)
    return

def varint_to_int(hexinput):
    numofvalues = len(hexinput)
    this = 0
    last = (hexinput[numofvalues - 1] << 1)
    count = 2
    leftshift = 8
    while (numofvalues - count) >= 0:
        this = ((((hexinput[numofvalues - count] << 1) & 0xFF) >> 1) << leftshift)
        last = (this | last)
        count += 1
        leftshift += 7
    return (last >> 1)

def freelistinfo():
    global clear
    global freelisttrunkpage
    global fltp
    try:
        if clear: #This is needed ot prevent user from pressing the Get Freelist Info button and duplicating results
            listbox.delete(0, END)
            freelisttrunkpage = struct.unpack('>L', content[32:36])[0]    
        flplist = []
        try:
            marker = 0
            if freelisttrunkpage > 0:
                fltpoffset = (freelisttrunkpage -1) * pagefile_size
                listbox.insert(END, "Freelist trunkpage found on page " +str(freelisttrunkpage) + " at offset: " + str(fltpoffset))            
                numofpointers = struct.unpack('>L', content[fltpoffset+4:fltpoffset+8])[0]
                nextfltp = struct.unpack('>L', content[fltpoffset:fltpoffset+4])[0]
                listbox.insert(END, "Pages found in the freelist trunkpage: " +str(numofpointers))
                listbox.insert(END, '\n')
                while numofpointers:
                    marker += 4
                    flplist.append(struct.unpack('>L', content[fltpoffset+4+marker:fltpoffset+8+marker])[0])
                    numofpointers -= 1
                for i in flplist:                
                    listbox.insert(END, "Freelist page " + str(i) + " can be found at file offset: " + str((int(i) - 1) * pagefile_size))
                    numofcelllocation = ((int(i)-1) * pagefile_size) + 3
                    numberofcells = struct.unpack('>H', content[numofcelllocation:numofcelllocation+2])[0]
                    listbox.insert(END, "Number of records: " + str(numberofcells))
                    firstcelloffset = struct.unpack('>H', content[numofcelllocation+2:numofcelllocation+4])[0]
                    if firstcelloffset < pagefile_size:
                        firstcell = ((int(i) - 1) * pagefile_size) + firstcelloffset
                        listbox.insert(END, "First record at file offset: " + str(firstcell))                    
                        if content[firstcell:firstcell +1] > b'\x7F':
                            while content[firstcell:firstcell+1] > b'\x7F':
                                firstcell += 1
                        firstcell += 1
                        ROWID = struct.unpack('>B', content[firstcell:firstcell+1])[0]
                        if ROWID > 127:
                            ROWID = varint_to_int(content[firstcell:firstcell+2])
                        listbox.insert(END, 'Largest ROW ID on page: ' + str(ROWID))
                        listbox.insert(END, '\n')
                    else:
                        listbox.insert(END, 'Invalid value for record offset')
                        listbox.insert(END, '\n')
            else:
                listbox.insert(END, "There are no freelist pages in this database")
            if nextfltp > 0:
                freelisttrunkpage = nextfltp
                clear = 0
                freelistinfo()
            else:
                clear = 1
        except NameError:
            pass
    except TypeError:
        pass
    return

def open_File():
    global content
    global filename
    filename = askopenfilename(filetypes=(("Databases", "*.db;*.sqlite;*.sql"), ("All files", "*.*")), initialdir = 'C:/Users/'+user+'/Desktop')
    if filename:
        clearall()
        f = open(filename, 'rb')
        content = f.read()
        f.close()
        loading.set("Filename: " + filename)
        file_size.set("Size: " + str(len(content)))
    return

def validate():
    sqlheader = b"\x53\x51\x4C\x69\x74\x65\x20\x66\x6f\x72\x6d\x61\x74\x20\x33\x00"
    try:
        match = content[0:16]
        if sqlheader == match:            
            return True
        else:
            return False
    except TypeError:
        pass
    return

def analyze():
    global choices
    global tables
    global variable
    global freelisttrunkpage
    global freepages
    global pagefile_size
    try:
        tables.destroy()
    except NameError:
        pass
    if validate():
        version = struct.unpack('>L', content[96:100])[0]
        validcheck.set("Valid Database Header: Yes")
        sqlversion.set("SQLite Version: " + str(version))
        pagefile_size = struct.unpack('>H',content[16:18])[0]
        pagesize.set("Pagefile size: " + str(pagefile_size))
        if version >= 30070:
            number_of_pages = struct.unpack('>L', content[28:32])[0]
            numpages.set("Number of pages: " + str(number_of_pages))
            file_size = number_of_pages * pagefile_size
            dbsize.set("Database filesize: " + str(file_size) + " bytes")
        else:
            numpages.set("Number of pages: N/A (Database version < 3.7)")
            dbsize.set("Database filesize: N/A (Database version < 3.7)")
        filechanges = struct.unpack('>L', content[24:28])[0]
        changes.set("File changes: " + str(filechanges))
        freepages = struct.unpack('>L', content[36:40])[0]
        freelists.set("Freelist Pages: " + str(freepages))
        freelisttrunkpage = struct.unpack('>L', content[32:36])[0]        
        conn = sqlite3.connect(filename)
        c = conn.cursor()
        c.execute("select name from sqlite_master where type = 'table'")
        choices = []
        for row in c:
            choices.append(row[0])        
        conn.close()
        variable = StringVar(app)
        variable.set(choices[0])
        tables = OptionMenu(app, variable,  *choices)
        tables.config(fg = 'blue')
        tables.place(x = 60, y = 367)
        selection = variable.get()   
    else:
        validcheck.set("Valid Database Header: No")
    return
   
def get_tb_info():
    global columns
    tablebox.delete(0, END)
    tablelist = []
    try:
        selection = variable.get()
        conn = sqlite3.connect(filename)
        c = conn.cursor()
        try:
            c.execute('select * from ' + selection)
            row = c.fetchone()
            columns.set("Number of columns: " + str(len(row)))
            c.execute('PRAGMA table_info('+selection+')')
            for row in c:
                tablelist.append(row[1])
            tablecontents = ' | '.join(tablelist)
            tablebox.insert(END, tablecontents)                
            conn.close()
        except TypeError:
            columns.set("Number of columns: None")
    except NameError:
        pass
    return
        
def aboutMe():
    tkinter.messagebox.showinfo(title="About", message=("SQLite Database Analyzer " + version +  "\nBy James Eichbaum\nCopyright 2014"))
    return

def hexviewer(pagenum):
    viewer = Tk()
    viewer.title(pagenum)
    viewer.geometry('425x400+200+200')
    viewer.resizable(0,0)

    ov = LabelFrame(viewer, text = "Offset", padx = 5, pady = 5, width = 65, height = 390)
    ov.place(x = 5, y = 5)

    hv = LabelFrame(viewer, text = "Hex", padx = 5, pady = 5, width = 210, height = 390)
    hv.place(x = 75, y = 5)

    av = LabelFrame(viewer, text = "ASCII", padx = 5, pady = 5, width = 130, height = 390)
    av.place(x = 290, y = 5)

    o = Canvas(viewer, width = 50, height = 365)
    o.place(x = 10, y = 20)
    
    h = Canvas(viewer, width = 175, height = 365)
    h.place(x = 80, y = 20)
    
    a = Canvas(viewer, width = 75, height = 370)
    a.place(x = 295, y = 20)

    offbox = Listbox(o, width = 8, height = 23)
    offbox.pack()

    hexbox = Listbox(h, width = 32, height = 23)
    hexbox.pack()

    hexscroller = Scrollbar(a)
    hexscroller.pack(side = RIGHT, fill = BOTH)
    
    asciibox = Listbox(a, width = 16, height = 23)
    #asciibox = Listbox(a, width = 16, height = 23, yscrollcommand = treescroll.set)
    asciibox.pack()
    #hexscroller.config(command = asciibox.yview)

    offbox.insert(END, "00000000")
    hexbox.insert(END, "4E6F7420646F6E652079657421212121")
    asciibox.insert(END, "Not done yet!!!!")
  
    viewer.mainloop()
    return

def getitem():
    item = listbox.get(ACTIVE)
    if "Freelist trunkpage" in item:
        pattern = re.compile('page\s\d+')
        findpattern = re.search(pattern, item)
        pagenum = findpattern.group()
        pagenum = pagenum.upper()
        hexviewer(pagenum)
    elif "Freelist page" in item:
        pattern = re.compile('page\s\d+')
        findpattern = re.search(pattern, item)
        pagenum = findpattern.group()
        pagenum = pagenum.upper()
        hexviewer(pagenum)
    else:
        pass
    return

#Create the Window

app = Tk()
window_x = "700"
window_y = "500"
screen_x = app.winfo_screenwidth() // 2
screen_y = app.winfo_screenheight() // 2
app.title("SQLite Database Analyzer")
app.geometry(str(window_x) + "x" + str(window_y) + "+" + str(screen_x - 350) + "+" + str(screen_y - 250))
app.resizable(0,0)

#Menu Bar
menubar = Menu(app)

#File Menu
filemenu = Menu(menubar,tearoff=0)
filemenu.add_command(label = "Open", command = open_File)
#filemenu.add_command(label = "Close", command = clearall)
filemenu.add_command(label = "Quit", command=app.quit)
menubar.add_cascade(label = "File", menu=filemenu)

#Help Menu
helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_cascade(label="About", command=aboutMe)
menubar.add_cascade(label="Help", menu=helpmenu)

app.config(menu=menubar)

#Label Frames
fp = LabelFrame(app, text = "File Properties", padx = 5, pady = 5, width = 545, height = 52)
fp.place(x = 5, y = 10)

hp = LabelFrame(app, text = "SQLite Header Information", padx = 5, pady = 5, width = 275 , height = 250)
hp.place(x = 5, y = 82)

tp = LabelFrame(app, text = "Table Properties", padx = 5, pady = 5, width = int(window_x) - 10, height = 145)
tp.place(x = 5, y = 350)

flp = LabelFrame(app, text = "Freelist Properties", padx = 5, pady = 5, width = 410, height = 250)
flp.place(x = 285, y = 82)

x = Canvas(app, width = 66, height = 10)
x.place(x = 290, y = 110)

treescroll = Scrollbar(x)
treescroll.pack(side = RIGHT, fill = BOTH)

listbox = Listbox(x, width = 62, height = 10, yscrollcommand = treescroll.set)
listbox.pack()
treescroll.config(command = listbox.yview)

w = Canvas(app, width = 400, height = 25)
w.place(x = 10, y = 400)

tablescroll = Scrollbar(w)
tablescroll.pack(side=BOTTOM, fill = BOTH)

tablebox = Listbox(w, width = 112, height = 2, xscrollcommand = tablescroll.set)
tablebox.pack(fill = BOTH)
tablescroll.config(orient = HORIZONTAL, command = tablebox.xview)

#GUI Layout

#Labels and Buttons

loading = StringVar()
loading.set("Filename:")
loadinglabel = Label(app, textvariable = loading, fg = 'blue', height = 1)
loadinglabel.place(x = 10, y = 30)

file_size = StringVar()
file_size.set("Size:")
file_size_label = Label(app, textvariable = file_size, fg = 'blue', height = 1)
file_size_label.place(x = int(window_x) - 300,y = 30)

validcheck = StringVar()
validcheck.set("Valid Database Header: ")
validcheck_label = Label(app, textvariable = validcheck, height = 1)
validcheck_label.place(x = 10, y = 100)

sqlversion = StringVar()
sqlversion.set("SQLite Version: ")
sqlversion_label = Label(app, textvariable = sqlversion, height = 1)
sqlversion_label.place(x = 10, y = 125)

pagesize = StringVar()
pagesize.set("Pagefile size: ")
pagesize_label = Label(app, textvariable = pagesize, height = 1)
pagesize_label.place(x = 10, y = 150)

numpages = StringVar()
numpages.set("Number of pages: ")
numpages_label = Label(app, textvariable = numpages, height = 1)
numpages_label.place(x = 10, y = 175)

dbsize = StringVar()
dbsize.set("Database filesize: ")
dbsize_label = Label(app, textvariable = dbsize, height = 1)
dbsize_label.place(x = 10, y = 200)

changes = StringVar()
changes.set("File changes: ")
changes_label = Label(app, textvariable = changes, height = 1)
changes_label.place(x = 10, y = 225)

freelists = StringVar()
freelists.set("Freelist Pages: ")
freelists_label = Label(app, textvariable = freelists, height = 1)
freelists_label.place(x = 10, y = 250)

Tables = StringVar()
Tables.set("Table(s):")
Tables_label = Label(app, textvariable = Tables, height = 2)
Tables_label.place(x = 10, y = 365)

columns = StringVar()
columns.set("Number of columns: ")
columns_label = Label(app, textvariable = columns, height = 2)
columns_label.place(x = 10, y = 455)

find = Button(app, text = "Analyze", width = 10, command = analyze)
find.place(x = int(window_x) - 140, y = 25)

getpages = Button(app, text = "Get Freelist Info", width = 15, command = freelistinfo)
getpages.place(x = 80, y = 285)

get_table_info = Button(app, text = "Table Details", width = 13, command = get_tb_info)
get_table_info.place(x = int(window_x) - 118, y = 365)

rebuild = Button(app, text = "Rebuild", width = 13, command = None)
rebuild.place(x = int(window_x) - 118, y = 285)

viewpage = Button(app, text = "View Page", width = 13, command = getitem)
viewpage.place(x = int(window_x) - 410, y = 285)

app.mainloop()
