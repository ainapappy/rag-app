# Vendor

Placer ici les bibliothèques front **versionnées**, téléchargées depuis leur
source officielle (jamais chargées depuis un CDN à l'exécution).

## htmx.min.js

Version requise : **2.0.6**

```powershell
Invoke-WebRequest -Uri "https://unpkg.com/htmx.org@2.0.6/dist/htmx.min.js" `
    -OutFile static\vendor\htmx.min.js
# ou : curl -L -o static/vendor/htmx.min.js https://unpkg.com/htmx.org@2.0.6/dist/htmx.min.js
```

Sans ce fichier, tout le reste fonctionne ; seuls les boutons de suppression
de conversation (HTMX) restent inactifs.
