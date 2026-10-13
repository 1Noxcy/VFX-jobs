# Veille offres jeu vidéo

Vérifie les pages carrières de studios toutes les 5 h, détecte les offres nouvelles / fermées,
alerte sur Discord, et les affiche dans `index.html`.

## Mise en route (≈10 min)
1. Crée un dépôt GitHub (public, pour que GitHub Pages soit gratuit) et envoie-y tout ce dossier.
2. Discord : Paramètres du salon → Intégrations → Webhooks → Nouveau webhook → copie l'URL.
3. GitHub : Settings → Secrets and variables → Actions → New secret : nom `DISCORD_WEBHOOK_URL`, valeur = l'URL.
4. GitHub : Settings → Pages → Branch `main` / racine → ton site sera en ligne.
5. Onglet Actions → « Veille offres » → Run workflow (premier lancement ; il ne spamme pas, 1 seul message de résumé).

## Ajouter / corriger un studio
Édite `studios.json` : `name`, `city`, `country` (FR/CA), `url` (page carrières), `ats`, `slug`.
- Lever : `"ats":"lever"` (ou `"lever_eu"`) + `"slug"` (ex. `bhvr` pour jobs.lever.co/bhvr)
- Greenhouse : `"ats":"greenhouse"` + `"slug"`
- Autre site : `"ats":"page"` et `url` = page carrières (lecture générique des liens contenant artist / vfx / qa…)
- Pas de lien : laisse `url` à `null` ; l'email de candidature spontanée peut aller dans `email`.

## Limites à connaître
- Mode « page » : détecte des liens qui ressemblent à des offres, pas toujours exact. Sites en JavaScript pur ou protégés anti-bot : erreur affichée dans la liste des studios.
- Une offre qui reste en ligne alors que le poste est pourvu n'est pas détectable (on voit sa date de 1re apparition).
- Mots-clés d'alerte : modifiables en haut de `check.py` (PRIO / SEC).
