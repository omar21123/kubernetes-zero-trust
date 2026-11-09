# Rapport du mini-projet

## Problématique

Dans un cluster partagé, la proximité réseau d'un pod ne signifie pas que son origine est fiable. Des communications ouvertes, des identités surdotées et des workloads privilégiés peuvent transformer une faille applicative locale en compromission de plusieurs services ou du cluster.

L'objectif est de rendre chaque accès justifiable et vérifiable : quelle identité, quelle destination, quelle opération et quelle configuration autorise-t-on ?

## Choix de conception

La solution repose sur trois points de contrôle complémentaires : le réseau avec un CNI capable d'appliquer les NetworkPolicies, l'API Kubernetes avec RBAC et l'admission des workloads avec Kyverno. Hubble observe les décisions réseau du CNI déjà présent.

Les namespaces représentent des domaines de responsabilité ; les identités restent distinctes à l'intérieur d'un même domaine. Les communications autorisées suivent un chemin frontend → api → catalog. Un workload d'audit expose un cas minimal d'accès à l'API : une seule lecture sur un ConfigMap nommé.

## Correspondance avec le sujet

| Exigence | Réalisation | Preuve prévue |
|---|---|---|
| Namespaces et composants | Quatre namespaces, trois services et deux workloads de test | Diagramme et manifests |
| Frontières et identités | SA dédié par workload, séparation plan applicatif / contrôle | Architecture et absence de jeton sur les applications |
| RBAC minimal | GET sur `zt-app/public-info` uniquement pour auditor | Requêtes 200/403 depuis le pod et `auth can-i` |
| Permissions dangereuses | Analyse secrets, exec, création de pods, token, bind/escalate, impersonate | Documentation RBAC et contrôles négatifs |
| Default Deny | Ingress et egress sur les quatre namespaces | Refus Service et PodIP |
| Flux nécessaires | Deux communications applicatives, DNS et exception auditor | Appel complet et tests DNS |
| Admission | Restricted PSS, identité explicite, racine immuable, budgets | Dry-run serveur sûr et dix configurations dangereuses |
| Kyverno | Intégration comme moteur unique d'admission | Nom de politique dans le rejet |
| Cilium | CNI, exception API par identité et option L7 | Filtrage L4 et test HTTP 403 en L7 |
| Hubble | Relay et UI installés | Captures de flux autorisés et refusés |
| Compromission | Analyse des accès directs et des chemins transitifs | Tableau du blast radius et scénario frontend compromis |

## Résultats et méthode

Les contrôles hors cluster vérifient le fonctionnement de la chaîne applicative, le traitement des erreurs et la cohérence structurelle des manifests. Les contrôles d'intégration doivent être exécutés sur un vrai cluster (EKS sur AWS, ou k3s dans la CI GitHub) pour attester le comportement réel du réseau, de RBAC et de l'admission. L'état effectivement constaté est consigné dans [validation.md](validation.md) et ne doit pas être confondu avec les résultats attendus de la soutenance.

Les tests utilisent des contrôles positifs : une cible doit répondre à son appelant autorisé, et la résolution DNS doit fonctionner avant d'interpréter un échec. Le refus RBAC est un vrai HTTP 403 après une requête autorisée ; le refus d'admission doit citer Kyverno. Hubble complète l'attribution d'un blocage réseau.

## Comment appliquer Zero Trust sans multiplier les mécanismes ?

Définir d'abord les besoins réels, puis utiliser un point de contrôle par responsabilité. Kubernetes fournit les identités et RBAC. Un seul CNI, Cilium, applique les politiques réseau. Une seule baseline Kyverno contrôle les configurations. Hubble exploite la télémétrie du même CNI.

Le socle reste court : pas de jeton inutile, un droit GET précis, deux flux applicatifs, une exception DNS et une exception API, puis un refus par défaut. Les politiques sont déclaratives, revues dans Git et vérifiées par des tests qui restent alignés sur les flux métier.

Un service mesh n'est pas nécessaire pour démontrer ce périmètre. Il devient pertinent si l'on exige une identité cryptographique par connexion, mTLS ou des contrôles applicatifs plus élaborés. Un contrôle L7 est proposé séparément pour montrer sa valeur et son coût opérationnel. Ajouter un mécanisme doit répondre à une menace ou une obligation explicite.

## Limites

Le laboratoire ne sécurise pas un nœud compromis, n'implémente pas mTLS, ne protège pas les données qu'une application doit légitimement transmettre et n'élimine pas les risques d'exfiltration DNS. Les quotas ne remplacent pas un contrôle de débit. Les labels réseau supposent que les workloads ne peuvent pas modifier leur identité de déploiement. Les versions figées doivent être actualisées pour une exploitation réelle.
