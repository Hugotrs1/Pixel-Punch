"""
Outils de l'interface, dessinée à la résolution réelle de l'écran (texte net),
avec des tailles proportionnelles à la hauteur de l'écran (cfg.UI).
"""
from __future__ import annotations

from functools import lru_cache

import pygame as pg

from . import config as cfg
from .animation import clamp


def u(v: float) -> int:
    """Convertit une taille pensée pour un écran de 720 px de haut."""
    return max(1, round(v * cfg.UI))


def melange(c1, c2, t: float):
    return tuple(int(a + (b - a) * clamp(t)) for a, b in zip(c1, c2))


@lru_cache(maxsize=32)
def police(taille: int, style: str = "normal") -> pg.font.Font:
    noms = {"titre": "segoeuiblack,arialblack,impact", "gras": "segoeuisemibold,segoeui,arial",
            "normal": "segoeui,arial"}[style]
    f = pg.font.SysFont(noms, u(taille), bold=style == "gras")
    return f


def panneau(w: int, h: int, alpha: int = 190, rayon: int = 16, bord=None, epaisseur: int = 2) -> pg.Surface:
    """Rectangle arrondi sombre semi-transparent, avec un liseré clair en haut."""
    s = pg.Surface((w, h), pg.SRCALPHA)
    r = u(rayon)
    pg.draw.rect(s, (10, 12, 22, alpha), s.get_rect(), border_radius=r)
    pg.draw.rect(s, (255, 255, 255, 22), s.get_rect(), 1, border_radius=r)
    if bord:
        pg.draw.rect(s, bord, s.get_rect(), u(epaisseur), border_radius=r)
    return s


def texte(surf, msg, taille, color, pos, ancre="center", style="gras", ombre=True, alpha=255, echelle=1.0,
          contour=0) -> pg.Rect:
    f = police(taille, style)
    s = f.render(msg, True, color)
    if echelle != 1.0:
        s = pg.transform.smoothscale_by(s, max(0.01, echelle))
    r = s.get_rect(**{ancre: pos})
    if contour:                                     # contour épais pour les gros titres
        c = f.render(msg, True, (15, 12, 20))
        if echelle != 1.0:
            c = pg.transform.smoothscale_by(c, max(0.01, echelle))
        c.set_alpha(alpha)
        e = u(contour)
        for ox, oy in ((-e, 0), (e, 0), (0, -e), (0, e), (-e, -e), (e, e), (-e, e), (e, -e), (0, e * 2)):
            surf.blit(c, r.move(ox, oy))
    elif ombre:
        sh = f.render(msg, True, (0, 0, 0))
        if echelle != 1.0:
            sh = pg.transform.smoothscale_by(sh, max(0.01, echelle))
        sh.set_alpha(int(alpha * 0.55))
        surf.blit(sh, r.move(u(2), u(3)))
    s.set_alpha(alpha)
    surf.blit(s, r)
    return r


def touche(surf, label: str, pos, taille=18, ancre="center", actif=False) -> pg.Rect:
    """Dessine une touche de clavier (petite capsule avec la lettre)."""
    f = police(taille, "gras")
    s = f.render(label, True, (20, 20, 30))
    w = max(s.get_width() + u(16), u(taille * 1.7))
    h = u(taille * 1.7)
    r = pg.Rect(0, 0, w, h)
    setattr(r, ancre, pos)
    pg.draw.rect(surf, (120, 95, 30) if actif else (150, 155, 175), r.move(0, u(3)), border_radius=u(7))
    pg.draw.rect(surf, cfg.OR if actif else (235, 238, 245), r, border_radius=u(7))
    surf.blit(s, s.get_rect(center=r.center))
    return r


def vignette() -> pg.Surface:
    small = pg.Surface((64, 36))
    for y in range(36):
        for x in range(64):
            d = ((x - 31.5) / 32) ** 2 + ((y - 17.5) / 18) ** 2
            v = int(255 * clamp(1 - 0.36 * d ** 1.5))
            small.set_at((x, y), (v, v, v))
    return pg.transform.smoothscale(small, (cfg.W, cfg.H))


class Sons:
    """Charge une seule fois les bruitages du dossier assets/sons.

    Les sons sont en .ogg : c'est le format lu partout, y compris dans le navigateur (version web).
    On les range par nom sans extension, donc jouer("Bell.mp3") et jouer("Bell") marchent tous les deux.
    """

    def __init__(self):
        self.sons: dict[str, pg.mixer.Sound] = {}
        self.actif = True
        try:
            pg.mixer.init()
            for f in cfg.SONS.glob("*.ogg"):
                self.sons[f.stem] = pg.mixer.Sound(f)
        except pg.error:
            pass                                    # pas de carte son : le jeu reste jouable

    def jouer(self, nom: str, volume: float = 1.0):
        nom = nom.rsplit(".", 1)[0]
        if self.actif and nom in self.sons:
            self.sons[nom].set_volume(volume)
            self.sons[nom].play()
