import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from flask_restful import Api
from sqlalchemy import create_engine, MetaData, Table, Column, String, ForeignKey, text
import os.path
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
api = Api(app)
newLessons = []
semaphore = True


'''
login() function connects to eClass as the "server" account.
We supposes that the account we are using has access to all courses in the eClass.
We first send a get request so that necessary cookies will be created and after that we send the final post request with
the credentials.
'''
def login() :
    login_url = "https://eclass.uniwa.gr/"
    f = open("credentials.txt", 'r')
    username = f.readline()
    password = f.readline()
    f.close()

    payload = {
        "uname" : username,
        "pass" :	password,
        "submit" : "Είσοδος"
    }

    session = requests.Session()
    session.get(login_url)
    session.post(login_url, payload)

    return session


'''
pushNotification() function use's the google firebase cloud messaging api.
We first created an account to google firebase, and allow the api use of the server, a server token is required so that we can 
send notification. We actually send a post request to google fcm (firebase cloud messaging) link with specific headers and body,
the server after that serves our request by sending the notification to the client with the token we included in the body.
'''
def pushNotification(deviceToken, title, body) :
    serverToken = "yourServerToken"

    headers = {
        "Content-Type" : "application/json",
        "Authorization" : "key = " + serverToken
    }

    body = {
        "data": {
            "title" : title,
            "body" : body
        },
        "to":
            deviceToken
    }
    
    requests.post("https://fcm.googleapis.com/fcm/send", headers = headers, data = json.dumps(body))


'''
manageStudentsDB() function manage the database.
If database doesn't exist; we created it, after we check if user who made the request exist in the database, if he doesn't exist,
we insert his info and his lessons info. If the user exist then we check for any updates in the lessons (maybe new course or deleted from older one).
If user want's to remove him self from the database then we first remove his record from studentsInfoTable and after that we remove any announcements or work which
it isn't referring to any student anymore.
'''
def manageStudentsDB(inputStudentInfo, inputLessonsNames, inputLessonsLinks) :
    global newLessons
    engine = create_engine("sqlite:///eclass.db", echo = False)
    meta = MetaData()
    print(inputStudentInfo[2])


    if (not os.path.exists("eclass.db")) :
        studentsInfoTable = Table (
            "studentsInfoTable",
            meta, 
            Column("id", String, primary_key = True),
            Column("fullName", String), 
            Column("deviceToken", String), 
        )

        lessonsLinksTable = Table (
            "lessonsLinksTable", 
            meta, 
            Column("id", String, ForeignKey("studentsInfoTable.id")),
            Column("lessonName", String),
            Column("lessonLink", String),
        )

        announcementsTable = Table (
            "announcementsTable", 
            meta, 
            Column("lessonLink", String, ForeignKey("lessonsLinksTable.lessonLink")),
            Column("announcementLink", String),
            Column("announcementTitle", String),
            Column("announcementDate", String),
        )

        worksTable = Table (
            "worksTable", 
            meta, 
            Column("lessonLink", String, ForeignKey("lessonsLinksTable.lessonLink")),
            Column("workTitle", String),
            Column("workDeadLine", String),
            Column("workLink", String),
        )
        meta.create_all(engine)
    else :
        studentsInfoTable = Table (
            "studentsInfoTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        lessonsLinksTable = Table (
            "lessonsLinksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )
    conn = engine.connect()

    if (inputLessonsNames == "delete") :
        id_ = inputStudentInfo
        conn.execute(text("DELETE FROM studentsInfoTable WHERE id = :id"), id = id_)

    else :
        id_ = inputStudentInfo[0]
        studentExist = False
        for student in conn.execute(text("SELECT * FROM studentsInfoTable WHERE id = :id"), id = id_) :
            studentExist = True
        if (not studentExist) :
            conn.execute(text("INSERT INTO studentsInfoTable (id, fullName, deviceToken) VALUES (:id, :fullName, :deviceToken)"), id = id_, fullName = inputStudentInfo[1], deviceToken = inputStudentInfo[2])
        
        for (inputLessonName, inputLessonLink) in zip(inputLessonsNames, inputLessonsLinks) :
            lessonLinkExist = False
            for sqlLessonLink in conn.execute(text("SELECT * FROM lessonsLinksTable WHERE id = :id AND lessonLink = :lessonLink"), id = id_, lessonLink = inputLessonLink) :
                lessonLinkExist = True
            if (not lessonLinkExist) :
                conn.execute(text("INSERT INTO lessonsLinksTable (id, lessonName, lessonLink) VALUES (:id, :lessonName, :lessonLink)"), id = id_, lessonName = inputLessonName, lessonLink = inputLessonLink)
                newLessons.append(inputStudentInfo[2] + inputLessonLink)

    for previousLessonLink in conn.execute(text("SELECT lessonLink FROM lessonsLinksTable WHERE id = :id"), id = id_) :
        previousLessonLink = str(previousLessonLink)[2:-3]
        if (previousLessonLink not in inputLessonsLinks) :
            conn.execute(text("DELETE FROM lessonsLinksTable WHERE id = :id AND lessonLink = :lessonLink"), id = id_, lessonLink = previousLessonLink)
    
    singleLessonsLinks = []
    for lessonLinkFromAnnouncementsTable in conn.execute(text("SELECT lessonLink FROM announcementsTable")) :
        lessonLinkFromAnnouncementsTable = str(lessonLinkFromAnnouncementsTable)[2:-3]
        if (lessonLinkFromAnnouncementsTable not in singleLessonsLinks) :
            singleLessonsLinks.append(lessonLinkFromAnnouncementsTable)
            lessonExist = False
            for lessonLink in conn.execute(text("SELECT * FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = lessonLinkFromAnnouncementsTable) :
                lessonExist = True
            if (not lessonExist) :
                conn.execute(text("DELETE FROM announcementsTable WHERE lessonLink = :lessonLink"), lessonLink = lessonLinkFromAnnouncementsTable)

    singleLessonsLinks = []     
    for lessonLinkFromWorksTable in conn.execute(text("SELECT lessonLink FROM worksTable")) :
        lessonLinkFromWorksTable = str(lessonLinkFromWorksTable)[2:-3]
        if (lessonLinkFromWorksTable not in singleLessonsLinks) :
            singleLessonsLinks.append(lessonLinkFromWorksTable)
            lessonExist = False
            for lessonLink in conn.execute(text("SELECT * FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = lessonLinkFromWorksTable) :
                lessonExist = True
            if (not lessonExist) :
                conn.execute(text("DELETE FROM worksTable WHERE lessonLink = :lessonLink"), lessonLink = lessonLinkFromWorksTable)


'''
exportAnnouncements() function uses Beautiful Soup technology for web scraping the announcements of every lesson in the eClass.
We first scrap all the current announcements and save it to an array, after for every announcement (from newer to older) we check if it isn't in our database; 
if it isn't then we insert it to our database and send a push notification to the every student who is listed in the specific lesson of the announcement. Otherwise if the notification is in our database
it means that we already check it show the rest of the search stops.
Note that if the students is first time connecting to our app then we prevent pushing all the notification from the past, in other words,
the new users want get any previous notification, they will get notification only from new announcements which were created after the time the login to our app.
'''
def exportAnnouncements(session) :
    global newLessons
    engine = create_engine("sqlite:///eclass.db", echo = False)
    meta = MetaData()

    if (os.path.exists("eclass.db")) :
        studentsInfoTable = Table (
            "studentsInfoTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        lessonsLinksTable = Table (
            "lessonsLinksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        announcementsTable = Table (
            "announcementsTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )
        conn = engine.connect()

        payload = {
            "iDisplayStart" : 0,
            "iDisplayLength" : -1,
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
        }

        singleLessonsLinks = []
        for sqlLessonLink in conn.execute(text("SELECT lessonLink FROM lessonsLinksTable")) :
            sqlLessonLink = str(sqlLessonLink)[2:-3]
            if (sqlLessonLink not in singleLessonsLinks) :
                singleLessonsLinks.append(sqlLessonLink)
                currentLessonLinks = []
                currentAnnouncementsLinks = []
                currentAnnouncementsTitles = []
                currentAnnouncementsDates = []
                maybeRestOfTitle = False
                courseId = sqlLessonLink.split('/')[-2]
                response = session.get("https://eclass.uniwa.gr/modules/announcements/?course=" + courseId, headers = headers, data = payload).text.split("\'")
                announcementDateBlock = ""
                firstAnnouncementDateBlock = True
                titleOnNextLine = False
                i = 0
                for item in response :
                    announcementDateBlock += item

                    if (maybeRestOfTitle) :
                        if ("table_td_body" not in item) :
                            currentAnnouncementsTitles[-1] = currentAnnouncementsTitles[-1] + " " + item.split('<')[0][1:].replace('\\', '')
                        maybeRestOfTitle = False

                    if (titleOnNextLine) :
                        currentLessonLinks.append(sqlLessonLink)
                        currentAnnouncementsTitles.append(item.split('<')[0][1:].replace('\\', ''))
                        titleOnNextLine = False
                        maybeRestOfTitle = True

                    if ("\/modules\/announcements\/index.php" in item) :
                        currentAnnouncementsLinks.append("https://eclass.uniwa.gr" + item.replace('\\', ''))
                        titleOnNextLine = True

                        if (not firstAnnouncementDateBlock) :
                            currentAnnouncementsDates.append(announcementDateBlock.split("div")[-3].split('\"')[2])
                            announcementDateBlock = ""
                        else :
                            firstAnnouncementDateBlock = not firstAnnouncementDateBlock

                currentAnnouncementsDates.append(announcementDateBlock.split("div")[-1].split('\"')[2])

                stopSearching = False
                for currentAnnouncementLink in currentAnnouncementsLinks :
                    for sqlAnnouncementLink in conn.execute(text("SELECT * FROM announcementsTable WHERE announcementLink = :announcementLink"), announcementLink = currentAnnouncementLink) :
                        stopSearching = True
                    if (stopSearching) :
                        break
                    else :
                        conn.execute(text("INSERT INTO announcementsTable (lessonLink, announcementLink, announcementTitle, announcementDate) VALUES (:lessonLink, :announcementLink, :announcementTitle, :announcementDate)"), lessonLink = currentLessonLinks[i], announcementLink = currentAnnouncementsLinks[i], announcementTitle = currentAnnouncementsTitles[i], announcementDate = currentAnnouncementsDates[i])
                        for lessonName in conn.execute(text("SELECT lessonName FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = currentLessonLinks[i]) :
                            lessonName = str(lessonName)[2:-3]
                        page = session.get(currentAnnouncementsLinks[i])
                        soup = BeautifulSoup(page.text, "html.parser")
                        div = soup.find(class_ = "announcement-main")
                        announcementBody = currentAnnouncementsTitles[i] + "\n" + div.text
                        
                        for studentId in conn.execute(text("SELECT id FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = currentLessonLinks[i]) :
                            studentId = str(studentId)[2:-3]
                            for deviceToken in conn.execute(text("SELECT deviceToken FROM studentsInfoTable WHERE id = :id"), id = studentId) :
                                deviceToken = str(deviceToken)[2:-3]
                            if (deviceToken + currentLessonLinks[i] not in newLessons) :
                                pushNotification(deviceToken, lessonName, announcementBody)
                        i += 1


'''
exportWorks() function is pretty much same as exportAnnouncements()
We first scrap and save all the works from the eClass and check if we have any new work (if it isn't in our database), if yes we update the database with it
and send a push notification to the students who are listed in this lesson.
Same goes here the new users, the won't get notification which are older by the time the first login in to our app.
'''
def exportWorks(session) :
    global newLessons
    engine = create_engine("sqlite:///eclass.db", echo = False)
    meta = MetaData()

    if (os.path.exists("eclass.db")) :
        studentsInfoTable = Table (
            "studentsInfoTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        lessonsLinksTable = Table (
            "lessonsLinksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        worksTable = Table (
            "worksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )
        conn = engine.connect()
        
        singleLessonsLinks = []
        for sqlLessonLink in conn.execute(text("SELECT lessonLink FROM lessonsLinksTable")) :
            sqlLessonLink = str(sqlLessonLink)[2:-3]
            if (sqlLessonLink not in singleLessonsLinks) :
                singleLessonsLinks.append(sqlLessonLink)
                currentLessonLinks = []
                currentWorksTitlesAndDeadLines = []
                currentWorksLinks = []
                maybeRestOfTitle = False
                i = 0
                courseId = sqlLessonLink.split('/')[-2]
                page = session.get("https://eclass.uniwa.gr/modules/work/?course=" + courseId)
                soup = BeautifulSoup(page.text, "html.parser")
                table = soup.find_all("table", {"id": "assignment_table"})

                for item in table :
                    for tr in item.find_all("tr") :
                        firstTwoTd = 0
                        for td in tr.find_all("td") :
                            td = td.text
                            if (len(td)) :
                                if (firstTwoTd < 2) :
                                    if (maybeRestOfTitle) :
                                        currentWorksTitlesAndDeadLines[-1] = currentWorksTitlesAndDeadLines[-1] + "\n" + td
                                        maybeRestOfTitle = False
                                        currentLessonLinks.append(sqlLessonLink)
                                    else :
                                        currentWorksTitlesAndDeadLines.append(td)
                                        maybeRestOfTitle = True
                                    firstTwoTd += 1

                    for td in item.find_all(href=True) :
                        currentWorksLinks.append("https://eclass.uniwa.gr" + td["href"])

                stopSearching = False
                for currentWorkLink in currentWorksLinks :
                    for sqlWorkLink in conn.execute(text("SELECT * FROM worksTable WHERE workLink = :workLink"), workLink = currentWorkLink) :
                        stopSearching = True
                    if (stopSearching) :
                        break
                    else :
                        currentWorkTitle = currentWorksTitlesAndDeadLines[i].split("\n")[0]
                        currentWorkDeadLine = currentWorksTitlesAndDeadLines[i].split("\n")[1].split('(')[0]
                        conn.execute(text("INSERT INTO worksTable (lessonLink, workTitle, workDeadLine, workLink) VALUES (:lessonLink, :workTitle, :workDeadLine, :workLink)"), lessonLink = currentLessonLinks[i], workTitle = currentWorkTitle, workDeadLine = currentWorkDeadLine, workLink = currentWorksLinks[i])
                        for lessonName in conn.execute(text("SELECT lessonName FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = currentLessonLinks[i]) :
                            lessonName = str(lessonName)[2:-3]

                        for studentId in conn.execute(text("SELECT id FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = currentLessonLinks[i]) :
                            studentId = str(studentId)[2:-3]
                            for deviceToken in conn.execute(text("SELECT deviceToken FROM studentsInfoTable WHERE id = :id"), id = studentId) :
                                deviceToken = str(deviceToken)[2:-3]
                            if (deviceToken + currentLessonLinks[i] not in newLessons) :
                                pushNotification(deviceToken, lessonName, currentWorksTitlesAndDeadLines[i])
                        i += 1
    newLessons = []


'''
worksReminder() function if responsible for reminding to user (with push notification) for an event on specific times.
The times are :
3 days (exactly) before the deadline
1 day before
6 hours before
3 hours before
1 hour before
'''
def worksReminder() :
    engine = create_engine("sqlite:///eclass.db", echo = False)
    meta = MetaData()

    if (os.path.exists("eclass.db")) :
        studentsInfoTable = Table (
            "studentsInfoTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        lessonsLinksTable = Table (
            "lessonsLinksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )

        worksTable = Table (
            "worksTable",
            meta, 
            autoload = True,
            autoload_with = engine
        )
        conn = engine.connect()

        response = conn.execute(text("SELECT lessonLink, workTitle, workDeadLine FROM worksTable"))
        for item in response :
            lessonLink = str(item).split(',')[0].split("\'")[1]
            workTitle = str(item).split(',')[1].split("\'")[1]
            workDeadline = str(item).split(',')[2].split("\'")[1]

            dateTimeNow = datetime.now()
            dayDeadLine = workDeadline.split(' ')[0].split('-')
            hourDeadLine = workDeadline.split(' ')[1].split(':')
            deadLineDateTime = datetime(day = int(dayDeadLine[0]), month = int(dayDeadLine[1]), year = int(dayDeadLine[2]), hour = int(hourDeadLine[0]), minute = int(hourDeadLine[1]), second = int(hourDeadLine[2]))
            timeLeft = str(deadLineDateTime - dateTimeNow).split(',')
            daysLeft = timeLeft[0].split(' ')[0]
            hoursAndMinsLeft = (timeLeft[1].split(':')[0] + ':' + timeLeft[1].split(':')[1]).replace(' ', '')

            if (daysLeft == '3' or daysLeft == '1' or daysLeft == '0') :
                reminderBody = "Just to remind :\nTime left for '" + workTitle + "' :\n"
                deviceToken = ""
                for innerResponce in conn.execute(text("SELECT id, lessonName FROM lessonsLinksTable WHERE lessonLink = :lessonLink"), lessonLink = lessonLink) :
                    studentId = str(innerResponce).split(',')[0].split("\'")[1]
                    lessonName = str(innerResponce).split(',')[1].split("\'")[1]
                    for deviceToken in conn.execute(text("SELECT deviceToken FROM studentsInfoTable WHERE id = :id"), id = studentId) :
                        deviceToken = str(deviceToken)[2:-3]
                    if (daysLeft == '0') :
                        if (hoursAndMinsLeft == "6:00" or hoursAndMinsLeft == "3:00" or hoursAndMinsLeft == "1:00") :
                            reminderBody += hoursAndMinsLeft
                    else :
                        if (hoursAndMinsLeft == "6:00") :
                            reminderBody += daysLeft + " days and " + hoursAndMinsLeft + " hours."
                    pushNotification(deviceToken, lessonName, reminderBody)


'''
mainService() function purpose is to run every 1 minute, what it does is scraping for new announcements and works from all lesson in eClass
and inform the specific users. We user a "semaphore" variable to avoid any conflict in the database access.
mainService() function is allowed to access the database only if no other function is using it (like a new login from a user).
Same goes for the other functions, they are not allowed to use the database until mainService() is done.
'''
def mainService() :
    global semaphore
    if (semaphore) :
        try :
            semaphore = False
            session = login()
            exportAnnouncements(session)
            exportWorks(session)
            worksReminder()
            semaphore = True
        except :
            semaphore = True


'''
postUserData() is called from the client side with HTTPS POST request.
Clients send 3 arrays :
studentInfo (contains : id, fullName, deviceToken*)
lessonsNames (contains : the names of the lessons which its signed to)
lessonsLinks (contains : the links of the lessons which its signed to)
deviceToken* is basically a long id which is use for the push notification service.
'''
@app.route("/postUserData", methods = ["POST"])
def postUserData() :
    global semaphore
    studentInfo = request.form["studentInfo"].split(", ")
    lessonsNames = request.form["lessonsNames"].split(", ")
    lessonsLinks = request.form["lessonsLinks"].split(", ")

    while (True) :
        if (semaphore) :
            try :
                semaphore = False
                manageStudentsDB(studentInfo, lessonsNames, lessonsLinks)
                session = login()
                exportAnnouncements(session)
                exportWorks(session)
                semaphore = True
                return "All ok."
            except :
                semaphore = True
                break


'''
deleteUserData() behavior is pretty much the same as postUserData().
Client call's it with HTTPS POST method but this time the arrays are :
studentInfo (contains : only the student id)
lessonsNames (contains : the phrase "delete")
lessonsLinks (contains : the phrase "delete")
so with this data we let the manageStudentsDB() function know that the user want's to delete himself from the database.
'''
@app.route("/deleteUserData", methods = ["POST"])
def deleteUserData() :
    global semaphore
    studentInfo = request.form["studentInfo"]
    lessonsNames = request.form["lessonsNames"]
    lessonsLinks = request.form["lessonsLinks"]

    while (True) :
        if (semaphore) :
            try :
                semaphore = False
                manageStudentsDB(studentInfo, lessonsNames, lessonsLinks)
                semaphore = True
                return "All ok."
            except :
                semaphore = True
                break


# Create the BackgroundScheduler so that mainService() will now be executed every 1 minute.
scheduler = BackgroundScheduler()
scheduler.add_job(func = mainService, trigger = "interval", seconds = 60)
scheduler.start()


# Our server will run in the pc ip (0.0.0.0 means pc ip like 192.168.2.105) and in the 9999 port.
if (__name__ == "__main__") :
    app.run(host = "0.0.0.0", port = "9999")
