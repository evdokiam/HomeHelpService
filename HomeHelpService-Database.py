import mysql.connector
from mysql.connector import Error
import HomeHelpService
import databaseConfig as cfg

try:
    mySQLconnection  = mysql.connector.connect(**cfg.mysql)
    employees = "select * from Employees"
    patients = "select * from patients"
    cursor = mySQLconnection .cursor()
    cursor.execute(employees)
    recordsE = cursor.fetchall()

    E = []
    locations = {}
    for row in recordsE:
        E += [row[0]]
        locations[row[0]]= (row[6], row[7])
    cursor.execute(patients)
    recordsN = cursor.fetchall()
    N = []
    for row in recordsN:
        N += [row[0]]
        locations[row[0]]= (row[6], row[7])
    cursor.close()
    mySQLconnection.close()
    print(locations)
    HomeHelpService.makeAssignments(N, E, locations)
    # HomeHelpService.makeRandomAssignments()
except Error as e :
    print ("Error while connecting to MySQL", e)
    HomeHelpService.makeRandomAssignments()
# finally:
#     #closing database connection.
#     if(mySQLconnection.is_connected()):
#         mySQLconnection.close()
#         print("MySQL connection is closed")