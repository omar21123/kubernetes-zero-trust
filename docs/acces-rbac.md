# Identités et permissions minimales

Chaque Deployment utilise un ServiceAccount dédié. `automountServiceAccountToken: false` est défini sur les comptes et sur les pods. Le compte `default` est refusé par l'admission.

## Droit accordé

La seule Role applicative est `public-info-reader` dans `zt-app` :

```yaml
apiGroups: [""]
resources: [configmaps]
resourceNames: [public-info]
verbs: [get]
```

Elle est liée uniquement à `auditor`. Il ne peut ni lister tous les ConfigMaps ni lire `other-info`, pourtant existant dans le même namespace. Aucun RoleBinding n'est créé pour frontend, api, catalog ou probe. Les droits de découverte éventuellement donnés par les bindings par défaut du cluster restent distincts de ces droits métier.

## Jeton de l'auditor

Le pod auditor monte explicitement un volume projeté dans `/var/run/zt-kubernetes` : un jeton ServiceAccount demandé pour 600 secondes et le certificat CA `kube-root-ca.crt`. L'audience omise utilise l'audience attendue par l'API server du laboratoire. Le kubelet assure la rotation ; le programme relit le jeton à chaque exécution. La durée effective dépend aussi de la configuration de l'API server.

Le script `/app/audit.py` vérifie TLS avec la CA et réalise de vraies requêtes authentifiées. Il attend successivement un HTTP 200 et trois HTTP 403. Aucun jeton n'est copié dans un manifest, un argument de commande, un rapport ou Git.

## Permissions dangereuses

| Permission | Risque |
|---|---|
| `*` sur ressources ou verbes, `cluster-admin` | Administration étendue et propagation au cluster |
| `get/list/watch secrets` | Vol de secrets et d'identités ; `list` expose aussi leur contenu |
| `create pods`, modification des templates | Exécution sous un autre ServiceAccount du namespace et montage de ses secrets |
| `create pods/exec`, `pods/attach` | Exécution dans un conteneur existant |
| `update pods/ephemeralcontainers` | Injection d'un conteneur de débogage |
| `create serviceaccounts/token` | Émission d'un jeton pour une autre identité |
| `bind`, `escalate`, modification RBAC | Attribution de droits ou contournement des protections RBAC |
| `impersonate` | Usurpation d'utilisateurs, groupes ou comptes de service |
| Modification de NetworkPolicies, namespaces ou labels | Élargissement des flux ou usurpation de sélecteurs |
| Modification des webhooks ou ClusterPolicies | Désactivation des contrôles d'admission |

Ces permissions ne sont accordées à aucun compte applicatif. Le compte de déploiement administratif utilisé par l'opérateur reste puissant et doit être protégé séparément.

## Après vol d'identité

Voler le jeton auditor permet au maximum, selon les bindings du laboratoire, de lire `zt-app/public-info` et les informations de découverte disponibles aux utilisateurs authentifiés. Le RBAC s'applique aussi si le jeton est utilisé depuis une machine extérieure ayant accès à l'API : la NetworkPolicy du pod n'accompagne pas le jeton volé.

Compromettre frontend ne fournit pas automatiquement de jeton puisque ce workload n'en monte pas. Cette propriété n'est pas une garantie si un administrateur ajoute ultérieurement un secret ou un volume projeté. Les droits de déploiement et la revue des manifests restent nécessaires.
