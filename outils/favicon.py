"""Dessine l'icône d'onglet de la version web (un gant de boxe en pixel art) : outils/favicon.png.

    python outils/favicon.py
"""
from pathlib import Path

import pygame as pg

GANT = [
    "................",
    "....hhhhhh......",
    "...hRRRRRRh.....",
    "..hRRRRRRRRR....",
    "..RRRRRRRRRRR...",
    "..RRRRRRRRRRRs..",
    "..RRRRRRRRRRRs..",
    "..sRRRRRRRRRRs..",
    "...sRRRRRRRRs...",
    "....ssssssss....",
    "....CCCCCCCC....",
    "....CCCCCCCC....",
    "....cccccccc....",
    "................",
    "................",
    "................",
]
COULEURS = {
    "R": (226, 64, 58), "h": (255, 128, 112), "s": (160, 36, 34),
    "C": (240, 240, 245), "c": (180, 184, 200),
}


def dessiner(taille: int = 64) -> pg.Surface:
    petit = pg.Surface((16, 16), pg.SRCALPHA)
    for y, ligne in enumerate(GANT):
        for x, lettre in enumerate(ligne):
            if lettre in COULEURS:
                petit.set_at((x, y + 1), COULEURS[lettre])
    icone = pg.Surface((taille, taille), pg.SRCALPHA)
    pg.draw.rect(icone, (20, 18, 32), icone.get_rect(), border_radius=taille // 5)
    icone.blit(pg.transform.scale(petit, (taille, taille)), (0, 0))
    return icone


if __name__ == "__main__":
    sortie = Path(__file__).with_name("favicon.png")
    pg.image.save(dessiner(), sortie)
    print(f"Icône écrite : {sortie}")
