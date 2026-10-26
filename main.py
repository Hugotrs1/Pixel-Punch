"""Pixel Punch — point d'entrée : python main.py   (ou python main.py --fenetre)"""
import sys

from pixel_punch.interface import Jeu

if __name__ == "__main__":
    Jeu(plein_ecran="--fenetre" not in sys.argv).run()
