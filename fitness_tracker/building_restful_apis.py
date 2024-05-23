
from flask import Flask, jsonify, request # imports the Flask class that gives us a bunch of tasty flask functionality
from flask_marshmallow import Marshmallow #create schema objects - determine the shape of the data we're sending and receiving
from marshmallow import fields, ValidationError # the necessary fields that we're accepting and the data types for those fields
# ValidationError is going to give us information on why our post or put wasn't successfully
# checking the incoming json data against our schema
import mysql.connector
from mysql.connector import Error

app = Flask(__name__) # creates a Flask app object that we store to the app variable
# we pass in the current file as the app location
ma = Marshmallow(app) #creates a marshmallow object that we can build schemas from

# creating a schema for customer data
# defining the shape of the json data that is coming in
# there are certain fields and types of those fields that need to be adhered to
class MembersSchema(ma.Schema): 
    # we define the types of the fields for the incoming data
    # set constraints for that data - whether its required to pass the schema check or not
    name = fields.String(required=True) 
    email = fields.String(required=True)
    phone_number = fields.String(required=True)

    class Meta:
        fields = ("name", "email", "phone") #the fields that we're grabbing information from the incoming data

# instantiating our CustomerSchema
member_schema = MembersSchema() #checking one single customer
members_schema = MembersSchema(many=True)#handling several rows of customer data

db_name = "fitness_tracker"
user = "root"
password = "Chima1964!"
host = "localhost"

def get_db_connection():
    try:
        # attempt to make a connection
        conn = mysql.connector.connect(
            database=db_name,
            user=user,
            password=password,
            host=host
        )
        # check for a connection
        if conn.is_connected():
            print("Connected to db successfully (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧")
            return conn
        
    except Error as e:
        # handling any errors specific to our Database
        print(f"Error: {e}")
        return None


# define the home page route
# @something <- decorator - provides additional functionality to any function immediately below it
@app.route('/') #a url location
# defining the functionality for that specific route
def home():
    return "Hello there! Welcome to Gym Membership App"
# return in functions within a flask route is what gets rendered to the browser

# url location in route always needs to be a string
@app.route("/about")
def about():
    return "This app tracks the members and the training they're using."

# make sure the endpoint names make sense. The location in the url is relevant to what functionality is being applied
# creating a route for a GET method
# HTTP Methods - GET, POST, PUT, DELETE
#           route location      HTTP method for that location
@app.route("/members")
def retrieve_members():
# establish our db connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # we're handling python dictionaries that are converted from json data
    # gives a list of dictionaries

    # SQL query to retrieve all customer data from our database
    query = "SELECT * FROM Members"

    # executing query
    cursor.execute(query)

    # fetch results and prepare them for the JSON response
    members = cursor.fetchall()
    print(members)

    # closing the db connection
    cursor.close()
    conn.close()

    # use Marshmallow to format our json response
    return members_schema.jsonify(members)


@app.route('/members', methods=["POST"])
def add_member():
    # validate and deserialize th using Marshmallow 
    # deserialize - making readable to python as dictionary
    member_data = member_schema.load(request.json)
    # taking the request to this route, grabbing the json data, and turning into a python dictionary
    print(member_data)
    
# connect to our db
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # create new customer details to send to our db
    # the json data above
    # setting variables from our dictionary
    name = member_data['name']
    email = member_data['email']
    phone_number = member_data['phone']

    # new_customer tuple to insert into our db
    new_member = (name, email, phone_number)
    print(new_member)
    # #SQL Query to insert data into our DB
    query = "INSERT INTO Members(name, email, phone) VALUES (%s, %s, %s)"
    # executing the query
    cursor.execute(query, new_member)
    conn.commit()

    # successfully addition of the new customer
    cursor.close()
    conn.close()
    return jsonify({"message": "New member was added successfully"}), 201 #resources successfully created


# using flask's dynamic routing to receive paramters through the url
@app.route("/members/<int:id>", methods=["PUT"]) # PUT replace already existing data (or resource)
def update_member(id):
    try: 
        # validating incoming data to make sure it adheres to our schema
        member_data = member_schema.load(request.json)
    except ValidationError as e:
        print(f"Error: {e}")
        return jsonify(e.messages), 400 #bad request - the information we're sending doesnt meet the application standards
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500 #server error - when it doesnt know how to handle the error
        cursor = conn.cursor()

        # updated customer information
        name = member_data['name']
        email = member_data["email"]
        phone_number = member_data["phone"]

        # query to update customer info with the id passed from the URL
        query = "UPDATE Members SET name = %s, email = %s, phone = %s WHERE member_id = %s"
        updated_member = (name, email, phone_number, id)
        cursor.execute(query, updated_member)
        conn.commit()

        # successfully update a new customer
        return jsonify({"message": "Member details updated successfully"}), 200 #successful connection

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal Server Error"}), 500 # server error - issue connecting to the server that the server cannot handle
    
    finally:
        # closing connection and cursor
        if conn and conn.is_connected():
            cursor.close()
            conn.close()



# delete customer
@app.route("/members/<int:id>", methods=["DELETE"])
def delete_member(id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500 #server error - when it doesn't know how to handle the error
        cursor = conn.cursor()
        member_to_remove = (id,)

        # sql query to to check if customer exists
        query = "SELECT * FROM Members WHERE member_id = %s"
        cursor.execute(query, member_to_remove)
        member = cursor.fetchone() #retrieving one record
        # even the customer_id is a unique identifier so we'll only end up with one row regardless
        if not member:
            return jsonify({"message": "Member not found"}), 404 #not found - trying to delete a customer that does not exist
        
        # query to check if customer has an order
        query = "SELECT * FROM workouts WHERE member_id = %s"
        cursor.execute(query, member_to_remove)
        workouts = cursor.fetchall()
        if workouts:
            return jsonify({"message": "Member has associated workouts, cannot delete"}), 400 #bad request - requesting to delete a customer that has associated orders
        # FINALLY If the customer exists and they dont have assoiciated orders we can delete them
        query = "DELETE FROM Members WHERE member_id = %s"
        cursor.execute(query, member_to_remove)
        conn.commit()

        # Successful deletion
        return jsonify({"message": "Member Removed Successfully"}), 200
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
        
class WorkoutSchema(ma.Schema):
    workout_id = fields.Int(dump_only=True)        
    member_id = fields.Int(required=True)        
    date = fields.Date(required=True)

    class Meta:
        fields = ("workout_id", "customer_id", "date")  
workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True)  

@app.route('/members', methods=["POST"])


# CREATE TWO Orders Routes
# route for adding an order using POST - consider how many orders you're creating or getting
# route for getting ALL orders using GET - to decide which schema to use


@app.route('/workouts', methods=['POST'])
def schedule_workout():
    try:
        # Validate and deserialize input
        workout_data = workout_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        query = "INSERT INTO Workouts (date, member_id) VALUES (%s, %s)"
        cursor.execute(query, (workout_data['date'], workout_data['member_id']))
        conn.commit()
        return jsonify({"message": "Workout added successfully"}), 201

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# GET route for all orders
@app.route('/workouts', methods=['GET'])
def view_workouts():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Workouts")
    workouts = cursor.fetchall()
    cursor.close()
    conn.close()
    return workouts_schema.jsonify(workouts) 

# UPDATE ORDER
@app.route("/workouts/<int:workout_id>", methods=["PUT"])
def update_workout(workout_id):
    try:
        # validating json data through the request
        workout_data = workout_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"error": f"{err.messages}"}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database Connection Failed"}), 500
    
    try:
        cursor = conn.cursor()
        query = "UPDATE Workouts SET date = %s, member_id = %s WHERE workout_id = %s"
        date = workout_data["date"]
        member_id = workout_data["member_id"]
        updated_member = (date, member_id, workout_id)
        cursor.execute(query, updated_member)
        conn.commit()
        return jsonify({'message': "Workout was updated successfully"}), 200
    
    except Error as e:
        return jsonify({"error": f"{e}"}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/workouts/<int:workout_id>', methods=["DELETE"])
def delete_workouts(workout_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        query = "DELETE FROM Workouts WHERE workout_id = %s"
        cursor.execute(query, (workout_id,))
        conn.commit()
        return jsonify({"message": "Workout successfully deleted!"}), 200
    
    except Error as e:
        return jsonify({"error": f"{e}"}), 500
    
    finally:
        cursor.close()
        conn.close()
    





if __name__ == "__main__": #making sure only app.py can run the flask application
    app.run(debug=True) #runs flask when we run the python file
    # and opens the debugger - robust information on errors within our application