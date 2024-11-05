import sys  
from pathlib import Path 

# add parent to path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path)) 

from contextlib import contextmanager
import logging
import pytest

from meal_max.models.battle_model import BattleModel, get_random
from meal_max.models.kitchen_model import Meal

@pytest.fixture()
def battle_model():
    """Fixture to provide a new instance of BattleModel for each test."""
    return BattleModel()

@pytest.fixture
def mock_update_meal_stats(mocker):
    """Mock the update_meal_stats function for testing purposes."""
    return mocker.patch("meal_max.models.battle_model.update_meal_stats")

"""Fixtures providing sample meals for the tests."""
@pytest.fixture
def sample_combatant1():
    return Meal(1, "Meal Name 1", "Cuisine Name 1", 180.0, "HIGH")

@pytest.fixture
def sample_combatant2():
    return Meal(2, "Meal Name 2", "Cuisine Name 2", 120.0, "LOW")

@pytest.fixture
def sample_combatants(sample_combatant1, sample_combatant2):
    return [sample_combatant1, sample_combatant2]

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


##################################################
# prep_combatant Test Cases
##################################################

def test_prep_combatant(battle_model, sample_combatants):
    """Test prepare a combatant to the battle_model."""
    # add two sample meal to combatant
    battle_model.prep_combatant(sample_combatants[0])
    battle_model.prep_combatant(sample_combatants[1])
    assert len(battle_model.combatants) == 2
    assert battle_model.combatants[0].meal == 'Meal Name 1'

def test_prep_combatant_duplicate(battle_model, sample_combatants):
    """Test prepare a combatant to the full battle_model."""
    # add two sample meal to combatant
    battle_model.prep_combatant(sample_combatants[0])
    battle_model.prep_combatant(sample_combatants[1])
    assert len(battle_model.combatants) == 2
    assert battle_model.combatants[0].meal == 'Meal Name 1'
    with pytest.raises(ValueError, match="Combatant list is full, cannot add more combatants."):
        battle_model.prep_combatant(sample_combatants[1])

##################################################
# get_combatants Test Cases
##################################################

def test_get_combatants(battle_model, sample_combatants):
    """Test retrieve current list of combatants from the battle_model."""
    battle_model.combatants.extend(sample_combatants)

    retrieved_combatants = battle_model.get_combatants()
    assert len(battle_model.combatants) == 2
    assert retrieved_combatants[0].id == 1
    assert retrieved_combatants[0].meal == 'Meal Name 1'
    assert retrieved_combatants[0].cuisine == 'Cuisine Name 1'
    assert retrieved_combatants[0].price == 180.0
    assert retrieved_combatants[0].difficulty == 'HIGH'

##################################################
# get_battle_score Test Cases
##################################################

def test_get_combatants(battle_model, sample_combatants):
    """Test retrieve current list of combatants from the battle_model."""
    battle_model.combatants.extend(sample_combatants)
    
    actual_score = battle_model.get_battle_score(battle_model.combatants[0])
    
    # calculate the expect score for the battle combatants
    difficulty_modifier = {"HIGH": 1, "MED": 2, "LOW": 3}
    expected_score = (sample_combatants[0].price * len(sample_combatants[0].cuisine)) - difficulty_modifier[sample_combatants[0].difficulty]

    assert actual_score == expected_score, f"The battle score did not match. Expected {expected_score}, got {actual_score}."

##################################################
# battle Test Cases
##################################################

def test_battle(mock_cursor, battle_model, sample_combatants):
    """Test battle for the combatants from the battle_model."""
    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False, False]

    # prepare combatants
    battle_model.combatants.extend(sample_combatants)
    
    # call battle function to get actual winner
    actual_winner = battle_model.battle()
    
    # calculate the expect winner for the battle combatants
    difficulty_modifier = {"HIGH": 1, "MED": 2, "LOW": 3}
    expected_score1 = (sample_combatants[0].price * len(sample_combatants[0].cuisine)) - difficulty_modifier[sample_combatants[0].difficulty]
    expected_score2 = (sample_combatants[1].price * len(sample_combatants[1].cuisine)) - difficulty_modifier[sample_combatants[1].difficulty]

    # Compute the delta and normalize between 0 and 1
    delta = abs(expected_score1 - expected_score2) / 100

    # Get random number from random.org
    random_number = get_random()
    
    # Determine the winner based on the normalized delta
    if delta > random_number:
        expected_winner = sample_combatants[0].meal
        expected_loser = sample_combatants[1].meal
    else:
        expected_winner = sample_combatants[1].meal
        expected_loser = sample_combatants[0].meal
    
    assert actual_winner == expected_winner, f"The battle score did not match. Expected {expected_winner}, got {actual_winner}."

def test_battle_by_one_combatant(mock_cursor, battle_model, sample_combatants):
    """Test battle for the invalid number of combatants from the battle_model."""
    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False, False]

    # prepare combatants
    battle_model.combatants.extend([sample_combatants[0]])
    
    with pytest.raises(ValueError, match="Two combatants must be prepped for a battle."):
        actual_winner = battle_model.battle()
    
    