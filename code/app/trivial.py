from flask import render_template
from app import webapp

import mysql.connector



@webapp.route('/trivial',methods=['GET'])
# Display an HTML list of all product.
def trivial():

    cnx = mysql.connector.connect(user='ece1779', 
                                  password='secret',
                                  host='127.0.0.1',
                                  database='estore')

    cursor = cnx.cursor()
    query = "SELECT * FROM customer"
    cursor.execute(query)
    view = render_template("trivial.html",title="Customer Table", cursor=cursor)
    cnx.close()
    return view 

