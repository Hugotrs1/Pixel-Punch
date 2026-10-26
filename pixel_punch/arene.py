"""L'arène en pixel art : salle, public qui réagit, ring, projecteurs, particules."""
from __future__ import annotations

import math
import random

import pygame as pg

from . import config as cfg

PEAUX = [(150, 88, 52), (238, 182, 140), (200, 140, 100), (110, 70, 45), (245, 205, 170)]
HABITS = [(200, 60, 60), (60, 90, 170), (230, 200, 80), (70, 150, 90), (160, 90, 160), (220, 220, 225),
          (60, 60, 70), (240, 140, 60)]


def _sombre(c, k=0.55):
    return tuple(int(v * k) for v in c)


class Particules:
    def __init__(self):
        self.p: list[list] = []        # x, y, vx, vy, vie, couleur, taille, gravité

    def jet(self, x, y, n, couleurs, vitesse=60, gravite=180, taille=1, vie=0.5, rng=random):
        for _ in range(n):
            a = rng.uniform(0, math.tau)
            v = rng.uniform(0.3, 1) * vitesse
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v - vitesse * 0.3, rng.uniform(vie * 0.5, vie),
                           rng.choice(couleurs), taille, gravite])

    def confettis(self, n, rng=random):
        for _ in range(n):
            self.p.append([rng.uniform(0, cfg.LW), rng.uniform(-40, -2), rng.uniform(-10, 10), rng.uniform(15, 40),
                           rng.uniform(3, 6), rng.choice(HABITS), rng.choice((1, 2)), 4])

    def maj(self, dt):
        for q in self.p:
            q[2] *= 1 - dt * 1.5
            q[3] += q[7] * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] -= dt
            if q[1] > cfg.SOL + 4 and q[7] > 50:            # rebond sur le ring
                q[1], q[3] = cfg.SOL + 4, -q[3] * 0.3
        self.p = [q for q in self.p if q[4] > 0 and q[1] < cfg.LH + 5]

    def dessiner(self, surf):
        for x, y, _, _, _, col, taille, _ in self.p:
            surf.fill(col, (round(x), round(y), taille, taille))


class Arene:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.excitation = 0.2
        self.flashs: list[list] = []
        self.construire()

    def construire(self):
        """(Re)fabrique les décors, à appeler si la taille de l'écran change."""
        lw, dy, rng = cfg.LW, cfg.DY, self.rng
        rangs = max(4, (dy + 72 - 26) // 10)
        self.public = [(x + rng.uniform(-2, 2), dy + 66 - rang * 10 + rng.uniform(-1, 1), rng.choice(PEAUX),
                        rng.choice(HABITS), rng.uniform(0, math.tau))
                       for rang in reversed(range(rangs)) for x in range(4 + (rang % 2) * 4, lw, 8)]
        self.fond = self._fond()
        self.ring = self._ring()
        self.cones = self._cones()

    def _fond(self):
        lw, lh = cfg.LW, cfg.LH
        s = pg.Surface((lw, lh))
        for y in range(lh):
            k = y / lh
            s.fill((int(48 - 20 * k), int(30 - 12 * k), int(44 - 14 * k)), (0, y, lw, 1))
        for i in range(lw // 37 + 1):                    # projecteurs
            x = 18 + i * 37
            pg.draw.rect(s, (40, 40, 48), (x - 6, 2, 12, 6))
            pg.draw.circle(s, (255, 250, 225), (x, 8), 3)
        return s

    def _ring(self):
        lw, lh, dy = cfg.LW, cfg.LH, cfg.DY
        s = pg.Surface((lw, lh), pg.SRCALPHA)
        pg.draw.rect(s, (30, 20, 30), (0, dy + 72, lw, 10))                   # barrière devant le public
        pg.draw.rect(s, (58, 40, 54), (0, dy + 72, lw, 2))
        pg.draw.polygon(s, (0, 168, 228), [(14, dy + 120), (lw - 14, dy + 120), (lw, dy + 160), (0, dy + 160)])
        pg.draw.polygon(s, (20, 190, 245), [(40, dy + 128), (lw - 40, dy + 128), (lw - 24, dy + 150), (24, dy + 150)])
        pg.draw.rect(s, (0, 110, 170), (0, dy + 160, lw, lh - 160 - dy))      # tablier
        pg.draw.line(s, (0, 80, 130), (0, dy + 160), (lw, dy + 160), 2)
        for k, col in enumerate(((220, 40, 45), (245, 245, 245), (40, 70, 200))):          # cordes
            y = dy + 84 + k * 11
            pg.draw.line(s, col, (20, y), (lw - 20, y), 2)
            pg.draw.line(s, col, (20, y), (0, y + 22 + k * 4), 2)
            pg.draw.line(s, col, (lw - 20, y), (lw, y + 22 + k * 4), 2)
        for x, col in ((20, (210, 35, 40)), (lw - 20, (235, 235, 235))):                    # poteaux
            pg.draw.rect(s, cfg.CONTOUR, (x - 4, dy + 76, 8, 48))
            pg.draw.rect(s, col, (x - 3, dy + 77, 6, 46))
            pg.draw.rect(s, (255, 255, 255), (x - 2, dy + 78, 1, 40))
        return s

    def _cones(self):
        lw, lh = cfg.LW, cfg.LH
        s = pg.Surface((lw, lh))
        for f in (0.2, 0.5, 0.8):
            x = lw * f
            cible = lw / 2 + (x - lw / 2) * 0.3
            for k in range(8):
                v = 6 + k * 2
                w = 34 - k * 4
                pg.draw.polygon(s, (v, v, int(v * 0.9)), [(x - 3, 8), (x + 3, 8), (cible + w, cfg.SOL + 6),
                                                          (cible - w, cfg.SOL + 6)])
        petit = pg.transform.smoothscale(s, (max(1, lw // 6), max(1, lh // 6)))
        return pg.transform.smoothscale(petit, (lw, lh))

    def acclamer(self, force: float, flashs: int = 0):
        self.excitation = min(1.0, self.excitation + force)
        for _ in range(flashs):
            self.flashs.append([self.rng.uniform(0, cfg.LW), self.rng.uniform(cfg.DY + 26, cfg.DY + 66), 0.12])

    def maj(self, dt):
        self.excitation += (0.2 - self.excitation) * min(1, dt * 0.8)
        if self.rng.random() < dt * (0.8 + self.excitation * 10):
            self.flashs.append([self.rng.uniform(0, cfg.LW), self.rng.uniform(cfg.DY + 26, cfg.DY + 66), 0.1])
        for f in self.flashs:
            f[2] -= dt
        self.flashs = [f for f in self.flashs if f[2] > 0]

    def dessiner(self, surf, temps):
        surf.blit(self.fond, (0, 0))
        amp = 0.4 + self.excitation * 3.2
        vitesse = 4 + self.excitation * 8
        for x, y, peau, habit, ph in self.public:
            saut = abs(math.sin(temps * vitesse + ph)) * amp
            yy = round(y - saut)
            surf.fill(_sombre(habit), (round(x) - 3, yy + 3, 7, 8))
            pg.draw.circle(surf, _sombre(peau), (round(x), yy), 3)
            if self.excitation > 0.55 and math.sin(temps * vitesse + ph) > 0.3:      # bras levés
                surf.fill(_sombre(peau), (round(x) - 4, yy - 4, 1, 4))
                surf.fill(_sombre(peau), (round(x) + 4, yy - 4, 1, 4))
        for x, y, _ in self.flashs:                                                  # appareils photo
            pg.draw.circle(surf, (255, 255, 240), (round(x), round(y)), 2)
            surf.fill((255, 255, 255), (round(x) - 4, round(y), 9, 1))
            surf.fill((255, 255, 255), (round(x), round(y) - 4, 1, 9))
        surf.blit(self.ring, (0, 0))

    def lumieres(self, surf):
        """Cônes des projecteurs, ajoutés par-dessus la scène (mélange additif)."""
        surf.blit(self.cones, (0, 0), special_flags=pg.BLEND_RGB_ADD)
