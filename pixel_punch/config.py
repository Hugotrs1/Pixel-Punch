"""
Constantes et dimensions de l'écran.

Le monde est dessiné en petits pixels (environ 270 x 150) puis agrandi d'un facteur
ENTIER pour que le pixel art reste net. Les menus, eux, sont dessinés directement à la
résolution de l'écran pour que le texte soit parfaitement lisible.
"""
from math import ceil
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SONS = RACINE / "assets" / "sons"
TITRE = "Pixel Punch"
FPS = 60

# Dimensions : recalculées par configurer() selon la taille de la fenêtre
W, H = 1280, 720            # écran (pixels réels)
ECHELLE = 4                 # taille d'un pixel du monde
LW, LH = 320, 180           # monde en pixel art
SOL = LH - 28               # hauteur du sol du ring
DY = SOL - 142              # décalage vertical du décor (il a été dessiné pour SOL = 142)
UI = 1.0                    # facteur d'échelle de l'interface (1.0 pour 720 px de haut)


def configurer(largeur: int, hauteur: int):
    global W, H, ECHELLE, LW, LH, SOL, DY, UI
    W, H = largeur, hauteur
    ECHELLE = max(2, round(hauteur / 150))
    LW, LH = ceil(largeur / ECHELLE), ceil(hauteur / ECHELLE)
    SOL = LH - 28
    DY = SOL - 142
    UI = hauteur / 720


# Couleurs de l'interface
OR = (255, 205, 70)
ROUGE = (240, 70, 60)
BLEU = (110, 195, 255)
VERT = (90, 220, 110)
BLANC = (255, 255, 255)
GRIS = (165, 170, 190)
CONTOUR = (22, 14, 20)
