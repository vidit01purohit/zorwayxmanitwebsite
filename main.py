from flask import Flask, session, render_template, request, redirect, flash, jsonify, url_for
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore, auth
from configu import config
import os

cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)

app = Flask(__name__)

firebase = pyrebase.initialize_app(config=config)
auth_pyrebase = firebase.auth()
db = firestore.client()

app.secret_key = os.environ["secret_key"]

#User login
@app.route("/user", methods=["POST", "GET"])
def user():
    if "user" in session:
        student = db.collection("students").where("email", "==", session["user"]).get()
        student = [stu.to_dict() for stu in student][0]
        timetable = db.collection("timetables").document(student["stream"]).collection(student["branch"]).document(
            f'{student["current_sem"]}thsem').get()
        timetable = timetable.to_dict()
        print(timetable)
        total_classes = timetable["total_classes"]
        attendance = db.collection("students").document(student['scholar_no']).collection("attendence").document(
            f"{student['current_sem']}thsem").get()
        attendance = attendance.to_dict()
        return render_template("user.html", student=student, timetable=timetable, attendance=attendance,
                               total_classes=total_classes)
    return redirect("/login")

#Admin login
@app.route("/admin", methods=["POST", "GET"])
def admin():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        branch = request.form.get("sbranch")
        stream = request.form.get("sstream")
        name = request.form.get("sname")
        scholar_no = request.form.get("sscholarno")
        current_sem = request.form.get("scurrsemester")
        dob = request.form.get("sdob")
        try:
            auth_pyrebase.create_user_with_email_and_password(email=email, password=password)
            db.collection("students").document(scholar_no).set({"branch": branch,
                                                                "current_sem": current_sem,
                                                                "email": email,
                                                                "name": name,
                                                                "stream": stream,
                                                                "scholar_no": scholar_no,
                                                                "dob": dob})
        except:
            flash('A user exists with that email address.')
            return redirect("/admin")

    student_details = db.collection("students").get()
    timetables = db.collection("timetables").get()
    student_details = [student.to_dict() for student in student_details]
    timetables = [timetable.to_dict() for timetable in timetables]
    if "user" in session:
        return render_template("admin.html", student_details=student_details, timetables=timetables)
    return redirect("/login")

#login routing
@app.route("/", methods=["POST", "GET"])
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.pop("user", None)
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            auth_pyrebase.sign_in_with_email_and_password(email=email, password=password)
            session["user"] = email
        except:
            return redirect("/")

        if "admin@gmail.com" == email:
            return redirect("/admin")

        return redirect("/user")

    if "user" in session:
        email = session["user"]
        if "admin@gmail.com" == email:
            return redirect("/admin")
        return redirect("/user")

    return render_template("login.html")

#logout routing
@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect("/")

#update route which is only open for admin to edit the info of students
@app.route('/admin/update/<string:scholar_no>', methods=['GET', 'POST'])
def update(scholar_no):
    if request.method == 'POST' and "user" in session and session["user"] == "admin@gmail.com":
        flash("Updated succesfuly")
        current_sem = request.form.get("scurrsemester")
        db.collection("students").document(scholar_no).update({
                                                            "current_sem": current_sem,
                                                            })
        return redirect('/admin')

    if "user" in session and session["user"] == "admin@gmail.com":
        email = db.collection("students").document(scholar_no).get().to_dict()["email"]
        student = db.collection("students").where("email", "==", email).get()
        student = [stu.to_dict() for stu in student][0]
        return render_template('update.html', student=student)

    return "Unauthorized path"


#deleting the current student information
@app.route('/admin/delete/<string:scholar_no>', methods=['GET'])
def delete(scholar_no):
    if "user" in session and session["user"] == "admin@gmail.com":
        email = db.collection("students").document(scholar_no).get().to_dict()["email"]
        try:
            user_to_delete = auth.get_user_by_email(email)
            auth.delete_user(user_to_delete.uid)
            db.collection("students").document(scholar_no).delete()
            flash("Record Has Been Deleted Successfully")
        except:
            flash("Not able to delete info")
        finally:
            return redirect(url_for('admin'))
    return "Unauthorized path"


if __name__ == "__main__":
    app.run(port=2000)
