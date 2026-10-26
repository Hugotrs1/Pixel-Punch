"""
Un boxeur en pixel art, entièrement dessiné par le code.

Le dessin part d'un squelette (hanche, épaules, coudes, poings, genoux, pieds) calculé
à partir d'une Pose : c'est de la cinématique directe. Chaque membre est ensuite tracé
avec un contour sombre, comme dans les jeux rétro.

Le Boxeur ne connaît pas les règles : il observe un Combattant du modèle et choisit
l'animation qui correspond à ce qu'il fait.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame as pg

from . import animation as anim
from . import config as cfg
from .animation import GARDE, GARDE_HAUTE, Animation, Pose
from .modele import Combattant, Coup

BRAS = 8.5          # longueur du bras et de l'avant-bras (pixels)


@dataclass(frozen=True)
class Tenue:
    peau: tuple
    cheveux: tuple
    coiffure: str               # "bandeau" ou "crete"
    short: tuple
    liseré: tuple
    gants: tuple
    bottes: tuple
    bandeau: tuple = (225, 40, 45)


# Le cogneur au bandeau rouge, contre le blond à crête aux gants dorés
TENUE_P1 = Tenue(peau=(150, 88, 52), cheveux=(28, 20, 18), coiffure="bandeau", short=(38, 36, 46),
                 liseré=(230, 45, 50), gants=(220, 38, 44), bottes=(36, 34, 42))
TENUE_P2 = Tenue(peau=(240, 186, 145), cheveux=(250, 214, 92), coiffure="crete", short=(40, 100, 220),
                 liseré=(250, 210, 70), gants=(245, 190, 45), bottes=(245, 245, 250))
BANDE = (240, 240, 235)         # bandes de poignet


def _ombre(c, k=0.78):
    return tuple(int(v * k) for v in c)


def _clair(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c)


def _entre(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _dir(angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return math.cos(a), -math.sin(a)


class Boxeur:
    def __init__(self, x: float, sens: int, tenue: Tenue):
        self.x = x
        self.sens = sens
        self.tenue = tenue
        self.anim: Animation | None = None
        self.pose = GARDE
        self.temps = 0.0
        self.repos = GARDE
        self.marche = 0
        self.elan = 1.0             # multiplie l'élan des coups pour que le poing arrive au contact
        self.fige = False           # reste dans la dernière pose (K.O.)

    # -- animation ---------------------------------------------------------
    def jouer(self, etapes, depart: Pose | None = None, boucle: bool = False):
        self.anim = Animation(depart or self.pose, etapes, boucle)

    def attaquer(self, coup: Coup, distance: float):
        """Lance l'animation du coup en réglant l'élan pour toucher pile l'adversaire."""
        frappe = anim.attaque(coup)[1][1]
        self.elan = 1.0
        poing = self.squelette(frappe)["av_poing"][0]
        voulu = frappe.dx + (distance - 6) - poing
        self.elan = max(0.0, min(3.0, voulu / frappe.dx))
        self.jouer(anim.attaque(coup))

    def suivre(self, c: Combattant):
        """Recopie la position et l'état du combattant du modèle."""
        self.x, self.sens, self.marche = c.x, c.sens, c.marche
        self.repos = GARDE_HAUTE if c.etat == "garde" else GARDE

    def maj(self, dt: float):
        self.temps += dt
        if self.anim:
            self.pose = self.anim.avancer(dt)
            if self.anim.finie:
                self.anim = None
                self.elan = 1.0
        elif not self.fige:
            cible = anim.respiration(self.repos, self.temps, self.marche)
            self.pose = self.pose.vers(cible, min(1.0, dt * 18))

    # -- squelette -----------------------------------------------------------
    def squelette(self, p: Pose) -> dict[str, tuple[float, float]]:
        """Positions des articulations, dans un repère où le boxeur regarde vers +x."""
        dx = p.dx * self.elan if p.dx > 0 else p.dx
        hanche = (dx, -19 + p.genou + p.dy)
        b = math.radians(p.buste)
        haut = (math.sin(b), -math.cos(b))
        epaule = (hanche[0] + haut[0] * 14, hanche[1] + haut[1] * 14)
        t = math.radians(p.buste + p.tete)
        tete = (epaule[0] + math.sin(t) * 6.5, epaule[1] - math.cos(t) * 6.5)
        pts = {"hanche": hanche, "epaule": epaule, "tete": tete}
        for cote, decal, ep, co in (("av", 1.5, p.av_epaule, p.av_coude), ("ar", -1.5, p.ar_epaule, p.ar_coude)):
            sx, sy = epaule[0] + decal, epaule[1] + 1.5
            d1, d2 = _dir(ep), _dir(ep + co)
            coude = (sx + d1[0] * BRAS, sy + d1[1] * BRAS)
            pts[f"{cote}_epaule"] = (sx, sy)
            pts[f"{cote}_coude"] = coude
            pts[f"{cote}_poing"] = (coude[0] + d2[0] * BRAS, coude[1] + d2[1] * BRAS)
        for cote, pied_x in (("av", dx + p.ecart * 0.55 + 2), ("ar", dx - p.ecart)):
            pied = (pied_x, 0.0)
            mx, my = (hanche[0] + pied[0]) / 2, (hanche[1] + pied[1]) / 2
            pts[f"{cote}_genou"] = (mx + 1.5 + p.genou * 0.7, my)
            pts[f"{cote}_pied"] = pied
        return pts

    def vers_monde(self, pts, p: Pose):
        """Applique la chute (rotation autour de la hanche, qui descend au sol) et le sens du regard."""
        phi = math.radians(-90 * p.chute)
        c, s = math.cos(phi), math.sin(phi)
        px, py = pts["hanche"]
        sol = py + (-4 - py) * p.chute
        out = {}
        for k, (x, y) in pts.items():
            x0, y0 = x - px, y - py
            rx, ry = x0 * c - y0 * s + px, x0 * s + y0 * c + sol
            out[k] = (round(self.x + rx * self.sens), round(cfg.SOL + ry))
        return out

    def point(self, nom: str) -> tuple[float, float]:
        return self.vers_monde(self.squelette(self.pose), self.pose)[nom]

    # -- dessin ----------------------------------------------------------------
    def dessiner(self, surf: pg.Surface):
        p = self.pose
        j = self.vers_monde(self.squelette(p), p)
        t = self.tenue
        ombre_w = 22 + int(p.chute * 16)
        cx = (j["av_pied"][0] + j["ar_pied"][0]) / 2 if not p.chute else (j["hanche"][0] + j["av_pied"][0]) / 2
        pg.draw.ellipse(surf, (0, 95, 150), (cx - ombre_w / 2, cfg.SOL - 2, ombre_w, 5))

        def membre(a, b, w, col):
            return [("l", j[a], j[b], w, col), ("c", j[b], w / 2, col)]

        def bras(cote, peau, gant):
            poignet = _entre(j[f"{cote}_coude"], j[f"{cote}_poing"], 0.62)
            return (membre(f"{cote}_epaule", f"{cote}_coude", 4, peau) + membre(f"{cote}_coude", f"{cote}_poing", 4, peau)
                    + [("c", poignet, 2.4, BANDE), ("c", j[f"{cote}_poing"], 3.9, gant)])

        def jambe(cote, peau, botte):
            pied = j[f"{cote}_pied"]
            tige = _entre(pied, j[f"{cote}_genou"], 0.5)          # bottes montantes de boxe
            return (membre("hanche", f"{cote}_genou", 5, peau) + membre(f"{cote}_genou", f"{cote}_pied", 4, peau)
                    + [("l", pied, tige, 5, botte), ("c", tige, 2.5, botte), ("l", pied, self._orteil(pied, p), 3, botte)])

        arriere = bras("ar", _ombre(t.peau), _ombre(t.gants)) + jambe("ar", _ombre(t.peau), _ombre(t.bottes))
        corps = jambe("av", t.peau, t.bottes)
        corps += [("l", j["hanche"], j["epaule"], 9, t.peau), ("c", j["epaule"], 4.5, t.peau)]
        corps += self._short(j)
        crane = t.cheveux if t.coiffure == "bandeau" else _ombre(t.peau, 0.86)
        corps += [("c", j["tete"], 5.5, crane)]
        avant = bras("av", t.peau, t.gants)

        for groupe in (arriere, corps):
            self._groupe(surf, groupe)
        self._details(surf, j)
        self._tete(surf, j, p)
        self._groupe(surf, avant)                           # le bras avant passe devant le visage
        gx, gy = j["av_poing"]
        surf.fill(_clair(t.gants, 0.6), (gx - 2, gy - 2, 2, 1))   # reflet sur le gant

    def _groupe(self, surf, groupe):
        for forme in groupe:                                # 1) contours
            self._forme(surf, forme, 2, cfg.CONTOUR)
        for forme in groupe:                                # 2) remplissage
            self._forme(surf, forme, 0, forme[-1])

    def _details(self, surf, j):
        """Reflets et ombres des muscles, bande du short."""
        t = self.tenue
        hx, hy = j["hanche"]
        ex, ey = j["epaule"]
        lg = math.hypot(ex - hx, ey - hy) or 1
        ux, uy = (ex - hx) / lg, (ey - hy) / lg                 # vers le haut du buste
        nx, ny = -uy * self.sens, ux * self.sens                # vers l'avant
        clair, sombre = _clair(t.peau, 0.22), _ombre(t.peau, 0.82)
        pg.draw.line(surf, clair, (hx + nx * 2.5 + ux * 4, hy + ny * 2.5 + uy * 4),
                     (ex + nx * 2.5 - ux * 1, ey + ny * 2.5 - uy * 1), 2)                      # reflet
        pg.draw.line(surf, sombre, (ex - ux * 3 - nx * 1, ey - uy * 3 - ny * 1),
                     (ex - ux * 3 + nx * 3, ey - uy * 3 + ny * 3))                              # pectoraux
        for k in (6, 8.5):                                                                      # abdos
            surf.fill(sombre, (round(hx + ux * k + nx * 1.5), round(hy + uy * k + ny * 1.5), 1, 1))
        pg.draw.line(surf, t.liseré, (hx + ux * 2 - nx * 1, hy + uy * 2 - ny * 1),
                     (hx - ux * 4 - nx * 1.5, hy - uy * 4 - ny * 1.5))                          # bande du short

    def _tete(self, surf, j, p):
        t = self.tenue
        hx, hy = j["tete"]
        b = math.radians(p.buste + p.tete) * (1 - p.chute) + math.radians(-90) * p.chute
        fx, fy = math.cos(b) * self.sens, math.sin(b)            # vers l'avant du visage
        upx, upy = self.sens * fy, -self.sens * fx               # vers le haut du crâne

        def pt(f, up):
            return hx + fx * f + upx * up, hy + fy * f + upy * up

        def pixel(f, up, col, w=1, h=1):
            x, y = pt(f, up)
            surf.fill(col, (round(x), round(y), w, h))

        pg.draw.circle(surf, t.peau, pt(1.3, -0.8), 4.3)                         # visage
        pixel(-0.6, -0.6, _ombre(t.peau, 0.8))                                   # oreille
        pixel(4.6, -0.6, _ombre(t.peau, 0.85))                                   # nez
        pixel(3.0, -2.6, (120, 40, 40))                                          # bouche
        if p.yeux > 0.5:
            pixel(2.8, 0.4, (20, 20, 25), 1, 2)
        else:
            pixel(2.3, -0.4, (20, 20, 25), 2, 1)
        pixel(2.2, 1.8, _ombre(t.cheveux, 0.5) if t.coiffure == "bandeau" else _ombre(t.cheveux, 0.7), 2, 1)  # sourcil

        if t.coiffure == "bandeau":
            pg.draw.line(surf, t.bandeau, pt(-4.5, 2.6), pt(3.6, 3.1), 2)
            for k in (0, 1):                                                     # pans qui flottent
                debut = pt(-4.8, 2.4 - k * 1.4)
                onde = math.sin(self.temps * 14 + k * 1.7) * 1.3
                fin = (debut[0] - fx * (5 + k) - upx * (1 + k - onde), debut[1] - fy * (5 + k) - upy * (1 + k - onde))
                pg.draw.line(surf, _ombre(t.bandeau, 0.85 if k else 1), debut, fin, 2 - k)
        else:
            # crête blonde en dents de scie, d'un seul tenant (sinon le contour mange tout)
            crete = [pt(3.0, 3.2), pt(2.2, 7.5), pt(0.6, 5.6), pt(-0.6, 8.3), pt(-2.0, 5.8), pt(-3.6, 7.6),
                     pt(-4.4, 4.6), pt(-4.6, 2.6)]
            pg.draw.polygon(surf, cfg.CONTOUR, crete, 2)
            pg.draw.polygon(surf, t.cheveux, crete)
            pg.draw.line(surf, _clair(t.cheveux, 0.5), pt(1.6, 5.4), pt(-3.2, 5.6))

    def _orteil(self, pied, p):
        if p.chute:
            return pied[0], pied[1] - 3
        return pied[0] + 3 * self.sens, pied[1]

    def _short(self, j):
        hx, hy = j["hanche"]
        ex, ey = j["epaule"]
        ux, uy = (ex - hx) / 14, (ey - hy) / 14
        nx, ny = -uy, ux
        haut = (hx + ux * 3, hy + uy * 3)
        bas = (hx - ux * 4, hy - uy * 4)
        pts = [(haut[0] + nx * 5, haut[1] + ny * 5), (haut[0] - nx * 5, haut[1] - ny * 5),
               (bas[0] - nx * 6, bas[1] - ny * 6), (bas[0] + nx * 6, bas[1] + ny * 6)]
        ceinture = [(haut[0] + nx * 5, haut[1] + ny * 5), (haut[0] - nx * 5, haut[1] - ny * 5)]
        return [("p", pts, self.tenue.short), ("l", *ceinture, 2, self.tenue.liseré)]

    @staticmethod
    def _forme(surf, forme, bord, col):
        kind = forme[0]
        if kind == "l":
            _, a, b, w, _ = forme
            pg.draw.line(surf, col, a, b, int(w + bord))
        elif kind == "c":
            _, c, r, _ = forme
            pg.draw.circle(surf, col, c, r + bord / 2)
        else:
            _, pts, _ = forme
            pg.draw.polygon(surf, col, pts)
            if bord:
                pg.draw.polygon(surf, col, pts, 2)
