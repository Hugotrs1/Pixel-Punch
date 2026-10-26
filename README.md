# Pixel Punch (Combat POO)

Jeu de boxe en pixel art, en Python orienté objet avec pygame-ce. Contre l'ordi ou à deux.

Jouer en ligne : https://jeu.hugotrs.fr

## Sur PC

```bash
pip install -r requirements.txt
python main.py            # plein écran
python main.py --fenetre  # en fenêtre
```

## Version web (pygbag)

```bash
pip install pygbag
python outils/web.py test     # http://localhost:8000
python outils/web.py deploy   # build + envoi sur jeu.hugotrs.fr
```

Ce qui a été adapté pour le web :
- la boucle de jeu est `async` et rend la main au navigateur à chaque image (`await asyncio.sleep(0)`)
- `main.py` importe `pygame` directement, sinon pygbag ne le charge pas
- les sons sont en `.ogg`, le format lu par les navigateurs
- pas de plein écran dans le navigateur, le jeu remplit la page

`version_2024/` contient l'ancienne version du projet, elle n'est pas envoyée sur le web.
