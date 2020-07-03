# Convert 2D legacy model file to 3D JSON formatted model file
# Discards non-IMPERMEABLE_STRUCTURE cells
# Takes files of the format: X,Y=concentration,type,counter

import json
import sys

# Check to ensure an appropriate number of arguments is given
if (len(sys.argv) > 2):
    print("Usage: python3 parse.py [<config file>]")
    sys.exit(0)

configFile = "config.json"
if (len(sys.argv) == 2):
    configFile = sys.argv[1]

# Load configuration from file
config = ""
with open(configFile, "r") as f:
    config = f.read()
config = json.loads(config)

LENGTH = config["shape"][0]
WIDTH = config["shape"][1]
HEIGHT = config["shape"][2]

# Get the initial information to set up the JSON
data = {
    "scenario" : {
        "shape" : config["shape"],
        "wrapped" : False,
        "default_delay" : "transport",
        "default_cell_type" : "CO2_cell",
        "default_state" : {
            "counter": -1,
            "concentration" : 500,
            "type" : -100
        },
    "default_config" : {
            "CO2_cell" : {
                "conc_increase" : 143.2,
                "base" : 500,
                "resp_time" : 5,
                "window_conc" : 400,
                "vent_conc" : 300
            }
        },
        "neighborhood": [
            {
                "type" : config["neighbourhood"],
                "range" : config["range"]
            }
        ]
    },
    "cells" : []
}

# Creates and retruns an IMPERMEABLE_STRUCTURE cell with the given coordinates
def makeCell (coords, concentration, cellType, counter):
    return {
        "cell_id": coords,
        "state" : {
            "concentration" : concentration,
            "type" : cellType,
            "counter" : counter
        }
    }

# A function to parse a line of the file
# Returns a dictionary containing cell information
def parseCell (line):
    coords = []
    location = line.find(",")
    coords.append(int(line[:location]))  # append X
    line = line[location + 1:]
    location = line.find("=")
    coords.append(int(line[:location]))  # append Y
    line = line[location + 1:]
    location = line.find(",")
    conc = int(line[:location])  # get concentration
    line = line[location + 1:]
    location = line.find(",")
    cellType = int(line[:location])  # get cell type
    line = line[location + 1:]
    counter = int(line)  # get counter

    # Returns the coords and the type of cell
    return {"coords" : coords, "conc" : conc, "type" : cellType, "counter" : counter}

# Determines if a cell with the given coordinates is already in the dictionary
def containsCell (data, coords):
    for cell in data["cells"]:
        if (cell["cell_id"] == coords):
            return True
    return False

# Get the heights at which to place each cell type
# Returns a list where the first element is the lowest cell it may appear in and
# the second element is one above the highest cell it may appear in
def getHeights (cellType):
    # WALL
    if (cellType == -300):
        return [1, HEIGHT - 2]  # keep in mind that HEIGHT is dirived from the shape
    
    # DOOR
    elif (cellType == -400):
        return [1, config["heights"]["door_top"]]

    # WINDOW
    elif (cellType == -500):
        return [config["heights"]["window"]["bottom"], config["heights"]["window"]["top"]]

    # VENTILATION
    elif (cellType == -600):
        return [config["heights"]["vent"], config["heights"]["vent"]]

    # WORKSTATION
    elif (cellType == -700):
        return [config["heights"]["workstation"], config["heights"]["workstation"]]

    # Otherwise
    else:
        return [0, 0]  # for loop does no iterations

# Read the data to be converted from the file
fileData = []
with open(config["files"]["input"], "r") as f:
    fileData = f.readlines()

# Extent each coordinate in the positive Z direction
# This brings the 2D model into 3D space
coords = []
for line in fileData:
    currCoord = parseCell(line)

    # Add given cells at appropriate heights
    if (config["walls_only"] and currCoord["type"] != -300):
        continue

    heights = getHeights(currCoord["type"])

    # Go through all Z values (floor and ceiling included)
    for z in range(0, HEIGHT):
        # If Z value is within cell's permitted values, add wall cell at that coordinate
        if (z in range(heights[0], heights[1] + 1)):
            coords.append({"coords" : currCoord["coords"] + [z],
                           "conc" : currCoord["conc"],
                           "type" : currCoord["type"],
                           "counter" : currCoord["counter"]})
        # If Z value is not within cell's permitted values AND that cell requires walls
        # above/below (DOOR and WINDOW), add wall cell at that coordinate
        elif (currCoord["type"] == -400 or currCoord["type"] == -500):
            coords.append({"coords" : currCoord["coords"] + [z],
                           "conc" : 0,
                           "type" : -300,
                           "counter" : -1})

# Turn the modified coordinates into its JSON representations and add them to the main dictionary
for coord in coords:
    data["cells"].append(makeCell(coord["coords"], coord["conc"], coord["type"], coord["counter"]))

# Add a floor and ceiling
# This is fairly simple as it just fills in the entire
# length by width rectangle at the floor and ceiling levels
for l in range (0, LENGTH):
    for w in range (0, WIDTH):
        if (not containsCell(data, [l, w, 0])):
            data["cells"].append(makeCell([l, w, 0], 0, -300, -1))  # floor
        if (not containsCell(data, [l, w, HEIGHT - 1])):
            data["cells"].append(makeCell([l, w, HEIGHT - 1], 0, -300, -1))  # ceiling

# Convert the Python dictionary to a JSON string
stringData = json.dumps(data, indent=4)

# Output the JSON string
with open(config["files"]["output"], "w") as f:
    f.write(stringData)

print("Complete (JSON string stored in \"{0}\")".format(config["files"]["output"]))