import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from jinja2 import Template


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///tasks.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    todos = db.execute("SELECT task, due, priority, completed FROM todos WHERE user_id = :user_id AND completed = :completed ORDER BY due",
                        user_id = session["user_id"],
                        completed = 0)
    today = datetime.datetime.today()
    items = []
    for todo in todos:
        date = datetime.datetime.strptime(todo["due"], '%Y-%m-%d')
        if date + datetime.timedelta(days=1) < today:
            late = 1
        else:
            late = 0
        items.append({
            "task": todo["task"],
            "due": todo["due"],
            "priority": todo["priority"],
            "completed": todo["completed"],
            "late": late
        })
    return render_template("index.html", items = items, today=today)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "GET":
        return render_template("add.html")
    else:
        if not request.form.get("task") or not request.form.get("priority") or not request.form.get("due"):
            return apology("all fields must be filled out")
        due = request.form.get("due")
        date = datetime.datetime.strptime(due, '%Y-%m-%d')
        if date < date.today():
            return apology("due date must be today or after")
        # Query database for task
        rows = db.execute("SELECT * FROM todos WHERE user_id = :user_id AND task = :task",
                          task = request.form.get("task"),
                          user_id = session["user_id"])
        # Ensure task is unique
        if len(rows) == 1:
            return apology("task already added")
        db.execute("INSERT INTO todos (user_id, task, due, priority) VALUES (:user_id, :task, :due, :priority)",
                    user_id = session["user_id"],
                    task = request.form.get("task"),
                    due = request.form.get("due"),
                    priority = request.form.get("priority"))
        flash("Task added!")
        return redirect("/")

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "GET":
        tasks = db.execute("SELECT task FROM todos WHERE user_id = :user_id AND completed = :completed",
            user_id = session["user_id"],
            completed = 0)
        return render_template("edit.html", tasks = tasks)
    else:
        oldtask = request.form.get("oldtask")
        if not request.form.get("task"):
            task = db.execute("SELECT task FROM todos WHERE user_id = :user_id AND task = :oldtask",
                                user_id = session["user_id"],
                                oldtask = oldtask)[0]["task"]
        else:
            task = request.form.get("task")
        if not request.form.get("priority"):
            priority = db.execute("SELECT priority FROM todos WHERE user_id = :user_id AND task = :oldtask",
                    user_id = session["user_id"],
                    oldtask = oldtask)[0]["priority"]
        else:
            priority = request.form.get("priority")
        due = request.form.get("due")
        date = datetime.datetime.strptime(due, '%Y-%m-%d')
        if not request.form.get("due"):
            due = db.execute("SELECT due FROM todos WHERE user_id = :user_id AND task = :oldtask",
                    user_id = session["user_id"],
                    oldtask = oldtask)[0]["due"]
        elif date + datetime.timedelta(days=1) < date.today():
                return apology("due date must be today or after")
        else:
            due = request.form.get("due")
        db.execute("UPDATE todos SET task = :task, priority = :priority, due = :due WHERE user_id = :user_id AND task = :oldtask",
                    task = task,
                    priority = priority,
                    due = due,
                    user_id = session["user_id"],
                    oldtask = oldtask)
        flash("Updated!")
        return redirect("/")

@app.route("/upcoming")
@login_required
def upcoming():
    today = datetime.date.today()
    day = [today]
    for i in range(0,6):
        next_day = day[i] + datetime.timedelta(days=1)
        day.append(next_day)
    todos1 = []
    todos2 = []
    todos3 = []
    todos4 = []
    todos5 = []
    todos6 = []
    todos7 = []
    rows = db.execute("SELECT task, priority, due FROM todos WHERE user_id = :user_id AND completed = :completed",
                        user_id = session["user_id"],
                        completed = 0)
    for row in rows:
        row["due"] = datetime.datetime.strptime(row["due"], '%Y-%m-%d').date()
    for i in range(0, len(rows)):
        if rows[i]["due"] == day[0]:
            todos1.append(rows[i])
        elif rows[i]["due"] == day[1]:
            todos2.append(rows[i])
        elif rows[i]["due"] == day[2]:
            todos3.append(rows[i])
        elif rows[i]["due"] == day[3]:
            todos4.append(rows[i])
        elif rows[i]["due"] == day[4]:
            todos5.append(rows[i])
        elif rows[i]["due"] == day[5]:
            todos6.append(rows[i])
        elif rows[i]["due"] == day[6]:
            todos7.append(rows[i])
    return render_template("upcoming.html", day = day, rows = rows, todos1 = todos1, todos2 = todos2, todos3 = todos3, todos4 = todos4, todos5 = todos5, todos6 = todos6, todos7 = todos7)

@app.route("/history")
@login_required
def history():
    rows = db.execute("SELECT task, priority, due, completed, time FROM todos WHERE user_id = :user_id",
                        user_id = session["user_id"])
    return render_template("history.html", rows = rows)

@app.route("/complete", methods=["GET", "POST"])
@login_required
def complete():
    if request.method == "GET":
        rows = db.execute("SELECT task FROM todos WHERE user_id = :user_id AND completed = :completed",
                            user_id = session["user_id"],
                            completed = 0)
        return render_template("complete.html", rows = rows)
    else:
        task = request.form.get("task")
        if request.form.get("complete") == "Yes":
            db.execute("UPDATE todos SET completed = :completed WHERE user_id = :user_id AND task = :task",
                        completed = 1,
                        user_id = session["user_id"],
                        task = task)
            flash("Completed!")
        else:
            db.execute("UPDATE todos SET completed = :completed WHERE user_id = :user_id AND task = :task",
                        user_id = session["user_id"],
                        completed = 0,
                        task = task)
            flash("Task was not completed")
        return redirect("/")

@app.route("/changepwd", methods=["GET", "POST"])
@login_required
def changepwd():
    """Allow user to change password"""
    if request.method == "GET":
        return render_template("change.html")
    else:
        # Ensure all fields were submitted
        if not request.form.get("currpwd"):
            return apology("must provide current password")

        # Ensure password was submitted
        elif not request.form.get("newpwd"):
            return apology("must provide new password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE id = :id",
                          id=session["user_id"])

        # Ensure username exists and password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("currpwd")):
            return apology("current password is invalid")

        # Ensure confirmation matches
        if request.form.get("newpwd") != request.form.get("confirmation"):
            return apology("entered password and confirmation do not match")

        # Update password
        hashcode = generate_password_hash(request.form.get("newpwd"))
        db.execute("UPDATE users SET hash=:hash WHERE id=:user_id", hash=hashcode, user_id=session["user_id"])

        flash("Password changed!")
        return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        # Ensure username is available
        if len(rows) == 1:
            return apology("username already taken")
        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords did not match")
        hashcode = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hashcode)
        return redirect("/")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
