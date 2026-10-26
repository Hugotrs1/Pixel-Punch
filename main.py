"""Pixel Punch : point d'entrée.

Sur PC :   python main.py   (ou python main.py --fenetre)
Sur le web : ce même fichier est lancé par pygbag dans le navigateur (voir outils/web.py).
"""
import asyncio
import sys

import pygame  # noqa: F401  (pygbag lit les imports de main.py pour savoir quels modules charger)

from pixel_punch.interface import Jeu

# Dans le navigateur, sys.platform vaut « emscripten » : pas de plein écran, le jeu remplit la page.
WEB = sys.platform == "emscripten"


async def main():
    await Jeu(plein_ecran=not WEB and "--fenetre" not in sys.argv).run()


asyncio.run(main())
