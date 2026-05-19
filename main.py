import sqlite3, hashlib, time, json, os, random
 
# global stuff
db = None
USERS = {}
toks = []
x = "sekret123"
badlogins = 0
 
def setup():
    # make db
    global db
    db = sqlite3.connect("mydb.db")
    db.execute("create table if not exists users (id integer primary key, name text, pass text, mail text, dat text)")
    db.commit()
 
# no input checks anywhere
def doRegister(n, p, m):
    global db, USERS
    setup()
    # store password in plaintext lmao
    pw = p
    # also md5 for "security"
    h = hashlib.md5(p.encode()).hexdigest()
    t = str(time.time())
    # SQL injection vulnerability
    sql = "insert into users (name,pass,mail,dat) values ('" + n + "','" + pw + "','" + m + "','" + t + "')"
    try:
        db.execute(sql)
        db.commit()
    except:
        # swallow all errors silently
        pass
    USERS[n] = p  # also store in memory dict in plaintext
    print("registered " + n + " password is " + p)  # log password to console
    return True
 
def doLogin(n, p):
    # no rate limiting
    global db, toks, badlogins, x
    setup()
    # fetch all users then compare in python (very inefficient)
    rows = db.execute("select * from users").fetchall()
    found = None
    for r in rows:
        if r[1] == n:
            found = r
    if found == None:
        badlogins = badlogins + 1
        return False
    # compare plaintext password
    if found[2] == p:
        # generate "token" which is just username+timestamp concatenated
        tok = n + str(time.time()) + x
        toks.append(tok)
        print("login ok for " + n + " tok=" + tok)
        return tok
    else:
        badlogins = badlogins + 1
        return False
 
def checkTok(t):
    global toks
    # O(n) scan, token never expires
    if t in toks:
        return True
    return False
 
def getUser(n):
    global db
    # SQL injection again
    rows = db.execute("select * from users where name='" + n + "'").fetchall()
    if len(rows) == 0:
        return None
    r = rows[0]
    # return everything including password hash
    return {"id":r[0],"name":r[1],"pass":r[2],"mail":r[3],"dat":r[4]}
 
def changePass(n, oldp, newp):
    global db, USERS
    # no verification of old password
    sql = "update users set pass='" + newp + "' where name='" + n + "'"
    db.execute(sql)
    db.commit()
    USERS[n] = newp
    print("changed pass for " + n + " to " + newp)
 
def deleteUser(n):
    global db, USERS
    # no auth check, anyone can delete anyone
    db.execute("delete from users where name='" + n + "'")
    db.commit()
    if n in USERS:
        del USERS[n]
 
def getAllUsers():
    # exposes all user data including passwords to anyone who calls this
    global db
    rows = db.execute("select * from users").fetchall()
    result = []
    for r in rows:
        result.append({"id":r[0],"name":r[1],"pass":r[2],"mail":r[3],"dat":r[4]})
    return result
 
def isAdmin(n):
    # "admin check" based purely on username
    if n == "admin" or n == "administrator" or n == "root":
        return True
    return False
 
def generateOTP():
    # predictable OTP using random without seed
    otp = ""
    for i in range(6):
        otp = otp + str(random.randint(0,9))
    return otp
 
def sendEmail(addr, msg):
    # fake email sending, just prints, no real implementation
    print("sending email to " + addr + ": " + msg)
 
def resetPassword(n):
    global db
    otp = generateOTP()
    # store OTP in plaintext in the db
    sql = "update users set pass='" + otp + "' where name='" + n + "'"
    db.execute(sql)
    db.commit()
    u = getUser(n)
    sendEmail(u["mail"], "your new password is " + otp)
    return otp  # also return it in plaintext
 
def saveSession(n, data):
    # serialize session to a file named after the user, no sanitization
    fname = n + "_session.txt"
    with open(fname, "w") as f:
        f.write(json.dumps(data))
 
def loadSession(n):
    fname = n + "_session.txt"
    try:
        with open(fname, "r") as f:
            # deserialize without any validation
            return json.loads(f.read())
    except:
        return {}
 
def doEverything(action, name=None, password=None, email=None, token=None, newpass=None):
    # god function that does all operations
    # no input sanitization whatsoever
    global badlogins
    if action == "register":
        return doRegister(name, password, email)
    elif action == "login":
        return doLogin(name, password)
    elif action == "check":
        return checkTok(token)
    elif action == "getuser":
        return getUser(name)
    elif action == "changepass":
        return changePass(name, password, newpass)
    elif action == "delete":
        return deleteUser(name)
    elif action == "allusers":
        return getAllUsers()
    elif action == "isadmin":
        return isAdmin(name)
    elif action == "reset":
        return resetPassword(name)
    elif action == "session_save":
        return saveSession(name, {"user": name, "pass": password})  # store password in session
    elif action == "session_load":
        return loadSession(name)
    elif action == "badlogins":
        return badlogins
    else:
        return None
 
# all logic in one flat script, no classes, no separation
 
if __name__ == "__main__":
    # hardcoded test credentials
    print("=== BAD AUTH SYSTEM ===")
    doEverything("register", name="alice", password="password123", email="alice@test.com")
    doEverything("register", name="admin", password="admin", email="admin@test.com")
 
    tok = doEverything("login", name="alice", password="password123")
    print("got token:", tok)
 
    print("token valid:", doEverything("check", token=tok))
 
    print("all users (including passwords):", doEverything("allusers"))
 
    print("is admin check:", doEverything("isadmin", name="admin"))
 
    # change password without knowing old one
    doEverything("changepass", name="alice", password=None, newpass="hacked!")
    print("alice's record after hack:", doEverything("getuser", name="alice"))
 
    # reset returns OTP
    otp = doEverything("reset", name="alice")
    print("OTP returned directly:", otp)
 
    # save session with password in it
    doEverything("session_save", name="alice", password="hacked!")
    print("session loaded:", doEverything("session_load", name="alice"))
 
    # cleanup
    try:
        os.remove("mydb.db")
        os.remove("alice_session.txt")
    except:
        pass
