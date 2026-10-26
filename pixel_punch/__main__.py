"""Permet de lancer le jeu avec : python -m pixel_punch   (ajouter --fenetre pour ne pas être en plein écran)"""
import asyncio
import sys

from .interface import Jeu

asyncio.run(Jeu(plein_ecran="--fenetre" not in sys.argv).run())
