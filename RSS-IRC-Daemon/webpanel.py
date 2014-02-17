from flask import Flask
from flask import render_template
from config import DB
from db_layer import MyDataBaseLayer
#####################################################################
DB_Conn = 0


app = Flask(__name__)

@app.route("/")
def app_root():
    global DB_Conn
    return render_template("root.html",name=123)
    

def run_webpanel(dbobj):
    global DB_Conn
    DB_Conn = dbobj
    app.run()