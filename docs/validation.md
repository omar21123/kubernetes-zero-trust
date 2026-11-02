# État de validation

Date de création : **2 novembre 2026**.

## Exécuté sur la machine de création

- Huit tests Python réussis : chaîne frontend/API/catalog via HTTP local, routes de santé, 404, erreur amont 502 et robustesse des sondes de sécurité.
- Contrôle structurel réussi sur **40 ressources** applicatives et politiques : YAML lisible, ressources sans doublon, identités dédiées, RBAC borné, isolation des quatre namespaces, DNS UDP/TCP et contexts de sécurité.
- Tests du moteur **Kyverno CLI 1.15.2** réussis : 60 résultats attendus conformes, dont 51 évaluations de règles et 9 exclusions de Services non ciblés. Cela couvre les Pods conformes, dix types de configurations dangereuses, les cinq Deployments applicatifs et un Deployment privilégié rejeté par les règles auto-générées.
- Diagnostic des prérequis : Python disponible ; **Docker, kind, kubectl et Helm absents du PATH**.

Les sockets HTTP locaux ont nécessité une exécution autorisée hors de l'isolation réseau de l'outil. PyYAML 6.0.3 a servi aux vérifications, sans ajouter de dépendance tierce aux conteneurs applicatifs.

Le système refuse la création de `.git/HEAD.lock` dans le dossier de travail initial. La publication GitHub est donc effectuée depuis une copie temporaire des fichiers du projet, avec un commit initial sur `main`. Le dépôt distant est [omar21123/kubernetes-zero-trust](https://github.com/omar21123/kubernetes-zero-trust), privé. Les métadonnées Git du dossier initial ne sont pas synchronisées ; pour poursuivre avec un dépôt local complet, utiliser la commande de clonage indiquée dans [exploitation.md](exploitation.md).

## Non exécuté ici

La création du cluster, l'installation des charts, le traitement par les webhooks Kyverno, l'application des règles par Cilium, les captures Hubble et l'exécution distante GitHub Actions n'ont pas été réalisés dans cet environnement. Aucun rapport d'intégration positif ni capture Hubble n'est fourni artificiellement.

La CI et les commandes de laboratoire sont préparées pour produire ces preuves. Des ajustements d'environnement ou d'intégration peuvent être nécessaires avant le premier passage complet ; une validation structurelle seule ne garantit pas la réussite du déploiement.

## Reproduire les vérifications

```console
python -m pip install -r requirements-dev.txt
python tools/validate.py
python -m unittest discover -s tests -v
kyverno test tests/kyverno --remove-color
python tools/lab.py doctor
python tools/lab.py up
python tools/lab.py test
python tools/lab.py l7-on
python tools/lab.py test --l7
```

Après exécution, joindre les rapports générés sous `artifacts/`, relever les versions et compléter ce document avec le résultat réel. Conserver les échecs dans les preuves, puis documenter les corrections et la nouvelle exécution.
