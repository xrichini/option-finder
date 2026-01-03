# tests/test_helpers.py
import pytest
from utils.helpers import get_high_short_interest_symbols
import pandas as pd
from unittest.mock import Mock


@pytest.fixture
def mock_html_table():
    """Fixture qui retourne un HTML de test avec une table de symboles"""
    return """
    <table>
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Short Interest</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>GME</td>
                <td>25.5%</td>
            </tr>
            <tr>
                <td>AMC</td>
                <td>30.2%</td>
            </tr>
        </tbody>
    </table>
    """


def test_get_high_short_interest_symbols_success(mocker, mock_html_table):
    """Test la récupération réussie des symboles"""
    # Mock la réponse HTTP
    mock_response = Mock()
    mock_response.text = mock_html_table
    mock_response.raise_for_status.return_value = None

    # Mock requests.get pour retourner notre réponse simulée
    mocker.patch("requests.get", return_value=mock_response)

    # Mock pd.read_html pour retourner un DataFrame simulé
    mock_df = pd.DataFrame(
        {"Ticker": ["GME", "AMC"], "Short Interest": ["25.5%", "30.2%"]}
    )
    mocker.patch("pandas.read_html", return_value=[mock_df])

    # Exécute la fonction
    result = get_high_short_interest_symbols()

    # Vérifie les résultats (trié alphabétiquement)
    assert set(result) == {"GME", "AMC"}
    assert len(result) == 2


def test_get_high_short_interest_symbols_http_error(mocker):
    """Test la gestion d'une erreur HTTP"""
    # Mock requests.get pour lever une exception
    mocker.patch("requests.get", side_effect=Exception("Erreur HTTP"))

    # Exécute la fonction
    result = get_high_short_interest_symbols()

    # Vérifie que la fonction retourne une liste vide en cas d'erreur
    assert result == []


def test_get_high_short_interest_symbols_no_table(mocker):
    """Test le cas où aucune table n'est trouvée sur la page"""
    # Mock la réponse HTTP avec une page sans table
    mock_response = Mock()
    mock_response.text = "<html><body>No table here</body></html>"
    mock_response.raise_for_status.return_value = None

    mocker.patch("requests.get", return_value=mock_response)

    # Exécute la fonction
    result = get_high_short_interest_symbols()

    # Vérifie que la fonction retourne une liste vide
    assert result == []


def test_get_high_short_interest_symbols_parse_error(mocker, mock_html_table):
    """Test la gestion d'une erreur lors du parsing des données"""
    # Mock la réponse HTTP
    mock_response = Mock()
    mock_response.text = mock_html_table
    mock_response.raise_for_status.return_value = None

    mocker.patch("requests.get", return_value=mock_response)

    # Mock pd.read_html pour lever une exception
    mocker.patch("pandas.read_html", side_effect=Exception("Erreur de parsing"))

    # Exécute la fonction
    result = get_high_short_interest_symbols()

    # Vérifie que la fonction retourne une liste vide en cas d'erreur
    assert result == []
