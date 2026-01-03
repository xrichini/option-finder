# tests/conftest.py
import sys
import os

# Ajoute le répertoire racine au PYTHONPATH pour que les imports fonctionnent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
