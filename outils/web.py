"""Version web de Pixel Punch, avec pygbag (le jeu tourne dans le navigateur grâce à WebAssembly).

    python outils/web.py test      # joue en local sur http://localhost:8000
    python outils/web.py build     # construit build/pixel-punch/build/web/
    python outils/web.py deploy    # build + envoi sur https://jeu.hugotrs.fr (alias SSH « hugotrs »)

Prérequis : pip install pygbag

On copie seulement ce dont le jeu a besoin (main.py, pixel_punch/, assets/) dans build/pixel-punch/,
sinon pygbag embarquerait aussi version_2024/ et alourdirait le téléchargement.
"""
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "build" / "pixel-punch"
SORTIE = SOURCE / "build" / "web"
CIBLE = "/srv/sites/combat-poo"


def preparer():
    shutil.rmtree(SOURCE, ignore_errors=True)
    SOURCE.mkdir(parents=True)
    shutil.copy2(RACINE / "main.py", SOURCE)
    ignorer = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(RACINE / "pixel_punch", SOURCE / "pixel_punch", ignore=ignorer)
    shutil.copytree(RACINE / "assets", SOURCE / "assets", ignore=ignorer)


def pygbag(*options: str):
    subprocess.run([sys.executable, "-m", "pygbag", *options, str(SOURCE)], check=True)


def deployer():
    ssh = lambda commande: subprocess.run(["ssh", "hugotrs", commande], check=True)
    ssh(f"rm -rf {CIBLE}.new")
    subprocess.run(["scp", "-r", "-q", str(SORTIE), f"hugotrs:{CIBLE}.new"], check=True)
    ssh(f"rm -rf {CIBLE}.old && mv {CIBLE} {CIBLE}.old && mv {CIBLE}.new {CIBLE}")
    print("En ligne sur https://jeu.hugotrs.fr")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "test"
    preparer()
    if action == "test":
        pygbag()
    elif action in ("build", "deploy"):
        pygbag("--build")
        print(f"Build prêt dans {SORTIE}")
        if action == "deploy":
            deployer()
    else:
        sys.exit(__doc__)
