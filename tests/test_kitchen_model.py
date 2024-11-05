import sys  
from pathlib import Path 

# add parent to path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path)) 

from contextlib import contextmanager
import re
import sqlite3
import logging
import pytest

from meal_max.models.kitchen_model import (
    Meal,
    create_meal,
    clear_meals,
    delete_meal,
    get_leaderboard,  # no
    get_meal_by_id,
    get_meal_by_name,
    update_meal_stats   # no
)

######################################################
#
#    Fixtures
#
######################################################

def normalize_whitespace(sql_query: str) -> str:
    return re.sub(r'\s+', ' ', sql_query).strip()

# Mocking the database connection for tests
@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test

######################################################
#
#    Add and delete
#
######################################################

def test_create_meal(mock_cursor):
    """Test creating a new meal in the meals."""

    # Call the function to create a new meal
    create_meal(meal="Meal 1", cuisine="Cuisine 1", price=100.0, difficulty="LOW")

    expected_query = normalize_whitespace("""
        INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)

    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call (second element of call_args)
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = ("Meal 1", "Cuisine 1", 100.0, "LOW")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_create_meal_duplicate(mock_cursor):
    """Test creating a meal with a duplicate meal (should raise an error)."""

    # Simulate that the database will raise an IntegrityError due to a duplicate entry
    mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed: meals.meal")

    # Expect the function to raise a ValueError with a specific message when handling the IntegrityError
    with pytest.raises(ValueError, match="Meal with name 'Meal 1' already exists"):
        create_meal(meal="Meal 1", cuisine="Cuisine 1", price=100.0, difficulty="LOW")

def test_create_meal_invalid_price():
    """Test error when trying to create a meal with an invalid price (e.g., negative price)"""

    # Attempt to create a meal with a negative price
    with pytest.raises(ValueError, match="Invalid price: -180.0. Price must be a positive number."):
        create_meal(meal="Meal price 1", cuisine="Cuisine price 1", price=-180.0, difficulty='LOW')

    # Attempt to create a meal with a non-integer price
    with pytest.raises(ValueError, match="Invalid price: invalid. Price must be a positive number."):
        create_meal(meal="Meal price 2", cuisine="Cuisine price 2", price='invalid', difficulty='LOW')

def test_create_meal_invalid_difficulty():
    """Test error when trying to create a meal with an invalid difficulty (e.g., HIGHER or integer)."""

    # Attempt to create a meal with difficulty = HIGHER
    with pytest.raises(ValueError, match="Invalid difficulty level: invalid. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Meal diff 1", cuisine="Cuisine diff 1", price=200.0, difficulty="invalid")

    # Attempt to create a meal with a integer difficulty
    with pytest.raises(ValueError, match="Invalid difficulty level: 1.0. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Meal diff 2", cuisine="Cuisine diff 2", price=200.0, difficulty=1.0)

def test_delete_meal(mock_cursor):
    """Test soft deleting a meal from the meals by meal ID."""

    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = ([False])

    # Call the delete_meal function
    delete_meal(1)

    # Normalize the SQL for both queries (SELECT and UPDATE)
    expected_select_sql = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update_sql = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    # Access both calls to `execute()` using `call_args_list`
    actual_select_sql = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update_sql = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Ensure the correct SQL queries were executed
    assert actual_select_sql == expected_select_sql, "The SELECT query did not match the expected structure."
    assert actual_update_sql == expected_update_sql, "The UPDATE query did not match the expected structure."

    # Ensure the correct arguments were used in both SQL queries
    expected_select_args = (1,)
    expected_update_args = (1,)

    actual_select_args = mock_cursor.execute.call_args_list[0][0][1]
    actual_update_args = mock_cursor.execute.call_args_list[1][0][1]

    assert actual_select_args == expected_select_args, f"The SELECT query arguments did not match. Expected {expected_select_args}, got {actual_select_args}."
    assert actual_update_args == expected_update_args, f"The UPDATE query arguments did not match. Expected {expected_update_args}, got {actual_update_args}."

def test_delete_meal_bad_id(mock_cursor):
    """Test error when trying to delete a non-existent meal."""

    # Simulate that no meal exists with the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when attempting to delete a non-existent meal
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)

def test_delete_meal_already_deleted(mock_cursor):
    """Test error when trying to delete a meal that's already marked as deleted."""

    # Simulate that the meal exists but is already marked as deleted
    mock_cursor.fetchone.return_value = ([True])

    # Expect a ValueError when attempting to delete a meal that's already been deleted
    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        delete_meal(999)

def test_clear_meals(mock_cursor, mocker):
    """Test clearing the entire meals (removes all meals)."""

    # Mock the file reading
    mocker.patch.dict('os.environ', {'SQL_CREATE_TABLE_PATH': 'sql/create_meal_table.sql'})
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data="The body of the create statement"))

    # Call the clear_database function
    clear_meals()

    # Ensure the file was opened using the environment variable's path
    mock_open.assert_called_once_with('sql/create_meal_table.sql', 'r')

    # Verify that the correct SQL script was executed
    mock_cursor.executescript.assert_called_once()

######################################################
#
#    Get Meal
#
######################################################

def test_get_meal_by_id(mock_cursor):
    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = (1, "Meal Name", "Cuisine Name", 100.0, "MED", 0, 0, False)

    # Call the function and check the result
    result = get_meal_by_id(1)

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Meal Name", "Cuisine Name", 100.0, "MED")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_id_bad_id(mock_cursor):
    # Simulate that no meal exists for the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)
        
def test_get_meal_by_name(mock_cursor):
    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = (1, "Meal Name 1", "Cuisine Name", 100.0, "MED", 0, 0, False)

    # Call the function and check the result
    result = get_meal_by_id("Meal Name 1")

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Meal Name 1", "Cuisine Name", 100.0, "MED")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = ('Meal Name 1',)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_name_bad_name(mock_cursor):
    # Simulate that no meal exists for the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when meal is not found
    with pytest.raises(ValueError, match="Meal with name Meal Name 2 not found"):
        get_meal_by_name('Meal Name 2')

def test_get_leaderboard_sorted_by_wins(mock_cursor):
    """Test leaderboard sorted by wins."""

    # Simulate that there are multiple meals in the database
    mock_cursor.fetchall.return_value = [
        (3, "Meal Name 3", "Cuisine Name 3", 100.0, "LOW", 10, 3, False),
        (1, "Meal Name 1", "Cuisine Name 1", 180.0, "HIGH", 10, 4, False),
        (2, "Meal Name 2", "Cuisine Name 2", 120.0, "MED", 10, 3, False)
    ]

    # Call the get_leaderboard function with sort_by = True
    leaderboard = get_leaderboard(sort_by='wins')
    
    # Ensure the results are sorted by play count
    expected_result = [
        {"id": 3, "meal": "Meal Name 3", "cuisine": "Cuisine Name 3", "price": 100.0, "difficulty": "LOW", "battles": 10, "wins": 3, "win_pct": 30.0},
        {"id": 1, "meal": "Meal Name 1", "cuisine": "Cuisine Name 1", "price": 180.0, "difficulty": "HIGH", "battles": 10, "wins": 4, "win_pct": 40.0},
        {"id": 2, "meal": "Meal Name 2", "cuisine": "Cuisine Name 2", "price": 120.0, "difficulty": "MED", "battles": 10, "wins": 3, "win_pct": 30.0}
    ]

    assert leaderboard == expected_result, f"Expected {expected_result}, but got {leaderboard}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct 
        FROM meals WHERE deleted = false AND battles > 0 ORDER BY wins DESC
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])
    
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

def test_get_leaderboard_sorted_by_invalid(mock_cursor):
    """Test leaderboard sorted by invalid param, eg winss."""

    # Simulate that there are multiple meals in the database
    mock_cursor.fetchall.return_value = [
        (3, "Meal Name 3", "Cuisine Name 3", 100.0, "LOW", 10, 3, False),
        (1, "Meal Name 1", "Cuisine Name 1", 180.0, "HIGH", 10, 4, False),
        (2, "Meal Name 2", "Cuisine Name 2", 120.0, "MED", 10, 3, False)
    ]

    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Invalid sort_by parameter: winss"):
        get_leaderboard(sort_by='winss')
        
######################################################
#
#    Update Meal
#
######################################################

def test_update_meal_stats(mock_cursor):
    """Test update meal stats when result equals to win in the meals."""
    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    result = 'win'
    update_meal_stats(meal_id, result)

    # Normalize the expected SQL query
    expected_query = normalize_whitespace("""
        UPDATE meals SET battles = battles + 1, wins = wins + 1 WHERE id = ?
    """)

    # Ensure the SQL query was executed 
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]

    # Assert that the SQL query was executed with the correct arguments (meal ID, result)
    expected_arguments = (meal_id, )
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_update_meal_stats_by_invalid_result(mock_cursor):
    """Test update meal stats when result is invalid (eg wins)."""
    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    result = 'wins'
    
    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Invalid result: wins. Expected 'win' or 'loss'."):
        update_meal_stats(meal_id, result)


