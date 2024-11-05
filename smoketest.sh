#!/bin/bash

# Define the base URL for the Flask API
BASE_URL="http://localhost:5000/api"

# Flag to control whether to echo JSON output
ECHO_JSON=false

# Parse command-line arguments
while [ "$#" -gt 0 ]; do
  case $1 in
    --echo-json) ECHO_JSON=true ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done


###############################################
#
# Healthchecks
#
###############################################

# Function to check the health of the service
check_health() {
  echo "Checking health status..."
  curl -s -X GET "$BASE_URL/health" | grep -q '"status": "healthy"'
  if [ $? -eq 0 ]; then
    echo "Service is healthy."
  else
    echo "Health check failed."
    exit 1
  fi
}

# Function to check the database connection
check_db() {
  echo "Checking database connection..."
  response=$(curl -s -X GET "$BASE_URL/db-check")
  echo "$response"
  if echo "$response" | grep -q '"status": "success"'; then
    echo "Database connection is healthy."
  else
    echo "Database check failed."
    exit 1
  fi
}


##########################################################
#
# Meals Management
#
##########################################################

clear_catalog() {
  echo "Clearing the meals..."
  curl -s -X DELETE "$BASE_URL/clear-meals" | grep -q '"status": "success"'
}

create_meal() {
  meal=$1
  cuisine=$2
  price=$3
  difficulty=$4

  echo "Adding meal ($meal, $cuisine, $price, $difficulty) to the kitchen_model..."
  response=$(curl -s -X POST "$BASE_URL/create-meal" -H "Content-Type: application/json" \
    -d "{\"meal\":\"$meal\", \"cuisine\":\"$cuisine\", \"price\":$price, \"difficulty\":\"$difficulty\"}")

  if echo "$response" | grep -q '"status": "success"'; then
    echo "Meal added successfully."
  else
    echo "Failed to add meal."
    exit 1
  fi
}

delete_meal_by_id() {
  meal_id=$1

  echo "Deleting meal by ID ($songmeal_id)..."
  response=$(curl -s -X DELETE "$BASE_URL/delete-meal/$meal_id")
  echo "$response"
  if echo "$response" | grep -q '"status": "success"'; then
    echo "Meal deleted successfully by ID ($meal_id)."
  else
    echo "Failed to delete meal by ID ($meal_id)."
    exit 1
  fi
}


get_meal_by_id() {
  meal_id=$1

  echo "Getting meal by ID ($meal_id)..."
  response=$(curl -s -X GET "$BASE_URL/get-meal-by-id/$meal_id")
  if echo "$response" | grep -q '"status": "success"'; then
    echo "Meal retrieved successfully by ID ($meal_id)."
    if [ "$ECHO_JSON" = true ]; then
      echo "Meal JSON (ID $meal_id):"
      echo "$response" | jq .
    fi
  else
    echo "Failed to get meal by ID ($meal_id)."
    exit 1
  fi
}

get_meal_by_name() {
  meal_name=$1

  echo "Getting meal by name ($meal_name)..."
  response=$(curl -s -X GET "$BASE_URL/get-meal-by-name/$meal_name")
  if echo "$response" | grep -q '"status": "success"'; then
    echo "Meal retrieved successfully by name ($meal_name)."
    if [ "$ECHO_JSON" = true ]; then
      echo "Meal JSON (name $meal_name):"
      echo "$response" | jq .
    fi
  else
    echo "Failed to get meal by name ($meal_name)."
    exit 1
  fi
}


############################################################
#
# Battle
#
############################################################

battle() {
  echo "initiate a battle between the two currently prepared meals..."
  response=$(curl -s -X GET "$BASE_URL/battle")

  if echo "$response" | grep -q '"status": "success"'; then
    echo "Two current prepared meals battle successfully."
    echo "$response" | jq .
  else
    echo "Failed to prepared meals to battle."
    exit 1
  fi
}

clear_combatants() {
  echo "Clearing combatants..."
  response=$(curl -s -X POST "$BASE_URL/clear-combatants")

  if echo "$response" | grep -q '"status": "success"'; then
    echo "Combatants cleared successfully."
  else
    echo "Failed to clear combatants."
    exit 1
  fi
}

get_combatants() {
  echo "Getting all combatant in the combatants..."
  response=$(curl -s -X GET "$BASE_URL/get-combatants")
  if echo "$response" | grep -q '"status": "success"'; then
    echo "All combatants retrieved successfully."
    if [ "$ECHO_JSON" = true ]; then
      echo "combatants JSON:"
      echo "$response" | jq .
    fi
  else
    echo "Failed to get combatants."
    exit 1
  fi
}

prep_combatants() {
  meal=$1

  echo "prepare $meal to the combatants..."
  response=$(curl -s -X POST "$BASE_URL/get-combatants"\
    -H "Content-Type: application/json" \
    -d "{\"meal\": \"$meal\"}")

  if echo "$response" | grep -q '"status": "success"'; then
    echo "All combatants prepared successfully."
    if [ "$ECHO_JSON" = true ]; then
      echo "combatants JSON:"
      echo "$response" | jq .
    fi
  else
    echo "Failed to get combatants."
    exit 1
  fi
}


######################################################
#
# Leaderboard
#
######################################################

# Function to get the song leaderboard sorted by play count
get_leaderboard() {
  sort=$1
  echo "Getting leaderboard sorted by wins, battles, or win percentage..."
  response=$(curl -s -X GET "$BASE_URL/leaderboard?sort=wins"\
    -H "Content-Type: application/json" \
    -d "{\"sort\": \"$sort\"}")
  
  if echo "$response" | grep -q '"status": "success"'; then
    echo "Leaderboard retrieved successfully."
    if [ "$ECHO_JSON" = true ]; then
      echo "Leaderboard JSON (sorted by wins):"
      echo "$response" | jq .
    fi
  else
    echo "Failed to get song leaderboard."
    exit 1
  fi
}


# Health checks
check_health
check_db

# Clear the catalog
clear_catalog

# Create songs
create_meal "Meal 1" "Cuisine 1" 100.00 "MED"
create_meal "Meal 2" "Cuisine 2" 101.00 "LOW"
create_meal "Meal 3" "Cuisine 3" 102.00 "HIGH"
create_meal "Meal 4" "Cuisine 4" 103.00 "LOW"
create_meal "Meal 5" "Cuisine 5" 104.00 "HIGH"

delete_meal_by_id 1

get_meal_by_id 2
get_meal_by_name "Meal 2"

prep_combatants "Meal 3"
prep_combatants "Meal 4"

get_combatants

battle

get_leaderboard

clear_combatants

echo "All tests passed successfully!"
